"""Energy calculator and termination logic for conversation dynamics."""

import re
from typing import Dict, List, Optional, Tuple

from colloquip.config import EnergyConfig
from colloquip.models import AgentStance, EnergySource, EnergyUpdate, Post


class EnergyCalculator:
    """Calculate conversation energy from post dynamics."""

    def __init__(self, config: Optional[EnergyConfig] = None, num_agents: int = 6):
        self.config = config or EnergyConfig()
        self.num_agents = num_agents

    def _compute_energy_and_components(
        self, posts: List[Post]
    ) -> Tuple[float, Dict[str, float]]:
        """Core computation: returns (energy, components).

        Used by both calculate_energy() and calculate_energy_update()
        to avoid duplicating work.
        """
        window = self.config.window
        recent = posts[-window:]
        if not recent:
            return 1.0, {
                "novelty": 0.0,
                "disagreement": 0.0,
                "questions": 0.0,
                "staleness": 0.0,
            }

        novelty = self._calculate_novelty_component(recent)
        disagreement = self._calculate_disagreement_component(recent)
        questions = self._calculate_question_component(recent, posts)
        staleness = self._calculate_staleness_penalty(recent, posts)

        weights = self.config.weights
        # Normalize positive weights so they sum to 1.0
        positive_sum = sum(v for k, v in weights.items() if k != "staleness")
        if positive_sum > 0:
            energy = (
                (weights["novelty"] / positive_sum) * novelty
                + (weights["disagreement"] / positive_sum) * disagreement
                + (weights["questions"] / positive_sum) * questions
            )
        else:
            energy = 0.0

        # Staleness is always a penalty (negative contribution)
        energy += weights["staleness"] * staleness

        energy = max(0.0, min(1.0, energy))

        return energy, {
            "novelty": novelty,
            "disagreement": disagreement,
            "questions": questions,
            "staleness": staleness,
        }

    def calculate_energy(self, posts: List[Post]) -> float:
        """Calculate current energy level (0.0 - 1.0)."""
        energy, _ = self._compute_energy_and_components(posts)
        return energy

    def calculate_energy_update(self, posts: List[Post], turn: int) -> EnergyUpdate:
        """Calculate energy and return a full EnergyUpdate with component breakdown."""
        energy, components = self._compute_energy_and_components(posts)
        return EnergyUpdate(turn=turn, energy=energy, components=components)

    def should_terminate(
        self, posts: List[Post], energy_history: List[float]
    ) -> Tuple[bool, str]:
        """Determine if deliberation should end."""
        # Guard: minimum posts before allowing termination
        if len(posts) < self.config.min_posts:
            return False, ""

        # Condition 1: Energy below threshold for N consecutive turns
        rounds = self.config.low_energy_rounds
        if len(energy_history) >= rounds:
            recent_energy = energy_history[-rounds:]
            if all(e < self.config.energy_threshold for e in recent_energy):
                return True, (
                    f"low_energy: energy < {self.config.energy_threshold} "
                    f"for {rounds} rounds"
                )

        # Condition 2: Maximum posts reached (hard cap)
        if len(posts) >= self.config.max_posts:
            return True, f"max_posts: reached {self.config.max_posts}"

        # Condition 3: All agents contributed and energy declining
        unique_agents = len(set(p.agent_id for p in posts))
        if unique_agents >= self.num_agents and len(energy_history) >= 3:
            trend = energy_history[-1] - energy_history[-3]
            if trend < -0.2 and energy_history[-1] < 0.4:
                return True, "declining_energy: all agents contributed, energy declining"

        return False, ""

    def inject_energy(self, source: EnergySource, current_energy: float) -> float:
        """Inject energy from an external source."""
        boost = self.config.injection.get(source.value, 0.0)
        return min(current_energy + boost, 1.0)

    def _calculate_novelty_component(self, recent: List[Post]) -> float:
        """Novelty component from novelty scores."""
        if not recent:
            return 0.0

        avg_novelty = sum(p.novelty_score for p in recent) / len(recent)

        novel_connections = sum(
            1 for p in recent if p.stance == AgentStance.NOVEL_CONNECTION
        )
        connection_bonus = min(
            novel_connections * self.config.novelty_bonus_per_connection,
            self.config.max_novelty_bonus,
        )

        return min(avg_novelty + connection_bonus, 1.0)

    def _calculate_disagreement_component(self, recent: List[Post]) -> float:
        """Disagreement component from stance distribution."""
        if not recent:
            return 0.0

        stances = [p.stance for p in recent]
        critical = sum(1 for s in stances if s == AgentStance.CRITICAL)
        total = len(stances)

        disagreement_rate = critical / total

        # Optimal range peaks at ~40% disagreement
        if disagreement_rate < 0.2:
            return 0.5 * disagreement_rate / 0.2
        elif disagreement_rate < 0.5:
            return 0.5 + 0.5 * (disagreement_rate - 0.2) / 0.3
        else:
            return 1.0 - 0.5 * (disagreement_rate - 0.5) / 0.5

    def _calculate_question_component(
        self, recent: List[Post], all_posts: List[Post]
    ) -> float:
        """Open questions component."""
        recent_questions: List[Tuple[Post, str]] = []
        for post in recent:
            # Split on sentence boundaries (period/exclamation/question + space)
            sentences = re.split(r"(?<=[.!?])\s+", post.content)
            for sentence in sentences:
                if "?" in sentence:
                    recent_questions.append((post, sentence))

        if not recent_questions:
            return 0.0

        unanswered = 0
        for q_post, question in recent_questions:
            try:
                q_index = all_posts.index(q_post)
            except ValueError:
                continue
            subsequent = all_posts[q_index + 1:]

            # Strip punctuation from keywords for matching
            q_keywords = set(re.sub(r"[^\w\s]", "", question.lower()).split())
            answered = False
            for post in subsequent:
                p_keywords = set(re.sub(r"[^\w\s]", "", post.content.lower()).split())
                # Adaptive threshold: at least half of question keywords matched
                threshold = max(2, len(q_keywords) // 2)
                if len(q_keywords & p_keywords) >= threshold:
                    answered = True
                    break

            if not answered:
                unanswered += 1

        return min(unanswered / self.config.max_open_questions, 1.0)

    def _calculate_staleness_penalty(
        self, recent: List[Post], all_posts: List[Post]
    ) -> float:
        """Staleness penalty for repetition and circular arguments."""
        if len(recent) < 3:
            return 0.0

        penalties = []

        # Penalty 1: Posts since last high-novelty post
        posts_since_novel = 0
        for post in reversed(all_posts):
            if post.novelty_score > 0.7:
                break
            posts_since_novel += 1
        novelty_penalty = min(
            posts_since_novel / self.config.posts_since_novel_threshold, 1.0
        )
        penalties.append(novelty_penalty)

        # Penalty 2: Semantic repetition
        repetition_penalty = self._detect_repetition(recent)
        penalties.append(repetition_penalty)

        # Penalty 3: Agent participation stagnation
        unique_agents = len(set(p.agent_id for p in recent))
        total_agents = len(set(p.agent_id for p in all_posts))
        if total_agents > 0:
            participation_penalty = 1.0 - (unique_agents / total_agents)
        else:
            participation_penalty = 0.0
        penalties.append(participation_penalty)

        return sum(penalties) / len(penalties)

    def _detect_repetition(self, posts: List[Post]) -> float:
        """Detect semantic repetition using keyword overlap."""
        if len(posts) < 3:
            return 0.0

        post_keywords = []
        for post in posts:
            words = post.content.lower().split()
            post_keywords.append(set(words))

        overlaps = []
        for i in range(len(post_keywords)):
            for j in range(i + 1, len(post_keywords)):
                intersection = len(post_keywords[i] & post_keywords[j])
                union = len(post_keywords[i] | post_keywords[j])
                if union > 0:
                    overlaps.append(intersection / union)

        if not overlaps:
            return 0.0

        avg_overlap = sum(overlaps) / len(overlaps)
        return min(avg_overlap * self.config.repetition_weight, 1.0)

"""Energy calculator and termination logic for conversation dynamics."""

from typing import Dict, List, Optional, Tuple

from colloquip.config import EnergyConfig
from colloquip.models import AgentStance, EnergySource, EnergyUpdate, Post


class EnergyCalculator:
    """Calculate conversation energy from post dynamics."""

    def __init__(self, config: Optional[EnergyConfig] = None):
        self.config = config or EnergyConfig()

    def calculate_energy(self, posts: List[Post]) -> float:
        """Calculate current energy level (0.0 - 1.0)."""
        window = self.config.window
        recent = posts[-window:]
        if not recent:
            return 1.0  # Full energy at start

        novelty = self._calculate_novelty_component(recent)
        disagreement = self._calculate_disagreement_component(recent)
        questions = self._calculate_question_component(recent, posts)
        staleness = self._calculate_staleness_penalty(recent, posts)

        weights = self.config.weights
        energy = (
            weights["novelty"] * novelty
            + weights["disagreement"] * disagreement
            + weights["questions"] * questions
            + abs(weights["staleness"]) * (-staleness)
        )

        return max(0.0, min(1.0, energy))

    def calculate_energy_update(self, posts: List[Post], turn: int) -> EnergyUpdate:
        """Calculate energy and return a full EnergyUpdate with component breakdown."""
        window = self.config.window
        recent = posts[-window:]

        if not recent:
            return EnergyUpdate(
                turn=turn,
                energy=1.0,
                components={"novelty": 1.0, "disagreement": 0.0, "questions": 0.0, "staleness": 0.0},
            )

        novelty = self._calculate_novelty_component(recent)
        disagreement = self._calculate_disagreement_component(recent)
        questions = self._calculate_question_component(recent, posts)
        staleness = self._calculate_staleness_penalty(recent, posts)

        energy = self.calculate_energy(posts)

        return EnergyUpdate(
            turn=turn,
            energy=energy,
            components={
                "novelty": novelty,
                "disagreement": disagreement,
                "questions": questions,
                "staleness": staleness,
            },
        )

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

        # Condition 2: Maximum turns reached (hard cap)
        if len(posts) >= self.config.max_posts:
            return True, f"max_posts: reached {self.config.max_posts}"

        # Condition 3: All agents contributed and energy declining
        unique_agents = len(set(p.agent_id for p in posts))
        if unique_agents >= 6 and len(energy_history) >= 3:
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
            sentences = post.content.split(".")
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
            subsequent = all_posts[q_index + 1 :]

            q_keywords = set(question.lower().split())
            answered = False
            for post in subsequent:
                p_keywords = set(post.content.lower().split())
                if len(q_keywords & p_keywords) > 3:
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
        participation_penalty = 1.0 - (unique_agents / 6)
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


# Module-level convenience type alias
Tuple = tuple  # noqa: just to satisfy the type hint used above

"""Observer agent for phase detection via conversation metrics."""

from typing import List, Optional

from colloquip.config import ObserverConfig
from colloquip.energy import EnergyCalculator
from colloquip.models import (
    AgentStance,
    ConversationMetrics,
    Phase,
    PhaseSignal,
    Post,
)


class ObserverAgent:
    """Meta-agent that detects phases from conversation dynamics.

    Does NOT participate in scientific discussion.
    ONLY observes dynamics and broadcasts phase state.
    """

    def __init__(
        self,
        energy_calculator: EnergyCalculator,
        config: Optional[ObserverConfig] = None,
    ):
        self.energy_calculator = energy_calculator
        self.config = config or ObserverConfig()
        self.current_phase = Phase.EXPLORE
        self.pending_phase: Optional[Phase] = None
        self.pending_count: int = 0
        self._observation_count: int = 0
        self._turn_count: int = 0

    def detect_phase(self, posts: List[Post]) -> PhaseSignal:
        """Detect current phase from post dynamics."""
        self._turn_count += 1
        metrics = self.calculate_metrics(posts)
        detected = self._detect_phase_from_metrics(metrics)
        self._apply_hysteresis(detected)
        confidence = self._calculate_confidence(detected)
        observation = self._generate_observation(metrics)

        return PhaseSignal(
            current_phase=self.current_phase,
            confidence=confidence,
            metrics=metrics,
            observation=observation,
        )

    def calculate_metrics(self, posts: List[Post]) -> ConversationMetrics:
        """Calculate conversation metrics from post list."""
        window = self.config.window_size
        recent = posts[-window:]

        return ConversationMetrics(
            question_rate=self._question_rate(recent),
            disagreement_rate=self._disagreement_rate(recent),
            topic_diversity=self._topic_diversity(recent),
            citation_density=self._citation_density(recent),
            novelty_avg=self._novelty_average(recent),
            energy=self.energy_calculator.calculate_energy(posts),
            posts_since_novel=self._posts_since_novel(posts),
        )

    def _question_rate(self, recent: List[Post]) -> float:
        if not recent:
            return 0.0
        questions = sum(1 for p in recent if "?" in p.content)
        return questions / len(recent)

    def _disagreement_rate(self, recent: List[Post]) -> float:
        if not recent:
            return 0.0
        critical = sum(1 for p in recent if p.stance == AgentStance.CRITICAL)
        return critical / len(recent)

    def _topic_diversity(self, recent: List[Post]) -> float:
        if not recent:
            return 0.0
        unique_agents = len(set(p.agent_id for p in recent))
        return min(unique_agents / 6, 1.0)  # 6 scientist agents, capped

    def _citation_density(self, recent: List[Post]) -> float:
        if not recent:
            return 0.0
        total_citations = sum(len(p.citations) for p in recent)
        return min(total_citations / (len(recent) * 3), 1.0)

    def _novelty_average(self, recent: List[Post]) -> float:
        if not recent:
            return 0.0
        return sum(p.novelty_score for p in recent) / len(recent)

    def _posts_since_novel(self, posts: List[Post], threshold: float = 0.7) -> int:
        count = 0
        for post in reversed(posts):
            if post.novelty_score > threshold:
                break
            count += 1
        return count

    def _detect_phase_from_metrics(self, metrics: ConversationMetrics) -> Optional[Phase]:
        """Simple rule-based phase detection. Order matters."""
        cfg = self.config

        # EXPLORE: High questions + diverse participation
        if (
            metrics.question_rate > cfg.explore_question_rate_min
            and metrics.topic_diversity > cfg.explore_topic_diversity_min
        ):
            return Phase.EXPLORE

        # DEBATE: High disagreement + evidence-heavy
        if (
            metrics.disagreement_rate > cfg.debate_disagreement_rate_min
            and metrics.citation_density > cfg.debate_citation_density_min
        ):
            return Phase.DEBATE

        # DEEPEN: Focused (low diversity) + high novelty
        if (
            metrics.topic_diversity < cfg.deepen_topic_diversity_max
            and metrics.novelty_avg > cfg.deepen_novelty_avg_min
        ):
            return Phase.DEEPEN

        # CONVERGE: Low energy + stagnating
        if (
            metrics.energy < cfg.converge_energy_max
            and metrics.posts_since_novel > cfg.converge_posts_since_novel_min
        ):
            return Phase.CONVERGE

        return None  # No clear signal

    def _apply_hysteresis(self, detected: Optional[Phase]) -> None:
        """Update phase with hysteresis to prevent oscillation."""
        if detected is None or detected == self.current_phase:
            self.pending_phase = None
            self.pending_count = 0
            return

        if detected == self.pending_phase:
            self.pending_count += 1
            if self.pending_count >= self.config.hysteresis_threshold:
                self.current_phase = detected
                self.pending_phase = None
                self.pending_count = 0
        else:
            self.pending_phase = detected
            self.pending_count = 1

    def _calculate_confidence(self, detected: Optional[Phase]) -> float:
        """Confidence in current phase assessment."""
        if detected is None or detected == self.current_phase:
            return 0.9

        progress = self.pending_count / self.config.hysteresis_threshold
        return max(0.5, 0.9 - (progress * 0.3))

    def _generate_observation(self, metrics: ConversationMetrics) -> Optional[str]:
        """Generate rare meta-observation when patterns are notable."""
        # Rate-limit observations
        if self._turn_count > 0:
            obs_rate = self._observation_count / self._turn_count
            if obs_rate >= self.config.observation_frequency:
                return None

        observation = None

        if metrics.posts_since_novel > 8:
            observation = (
                "The conversation appears to be circling. "
                "Consider introducing new evidence or perspectives."
            )
        elif metrics.disagreement_rate > 0.6:
            observation = (
                "Significant disagreement detected. "
                "The points of contention may warrant focused analysis."
            )
        elif metrics.novelty_avg > 0.7:
            observation = (
                "High novelty in recent posts. "
                "Cross-domain connections may be emerging."
            )
        elif metrics.topic_diversity < 0.3 and metrics.energy > 0.5:
            observation = (
                "Discussion is focused but energetic. "
                "Deep analysis of this thread may be valuable."
            )

        if observation:
            self._observation_count += 1

        return observation

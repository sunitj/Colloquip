"""Trigger evaluator for agent self-selection."""

from typing import Dict, List, Optional, Tuple

from colloquip.config import TriggerConfig
from colloquip.models import AgentStance, Phase, Post


class TriggerEvaluator:
    """Evaluate trigger rules for an agent to decide if it should respond."""

    def __init__(
        self,
        agent_id: str,
        domain_keywords: List[str],
        knowledge_scope: List[str],
        is_red_team: bool = False,
        config: Optional[TriggerConfig] = None,
    ):
        self.agent_id = agent_id
        self.domain_keywords = domain_keywords
        self.knowledge_scope = knowledge_scope
        self.is_red_team = is_red_team
        self.config = config or TriggerConfig()

    def evaluate(self, posts: List[Post], phase: Phase) -> Tuple[bool, List[str]]:
        """Evaluate all trigger rules. Returns (should_respond, triggered_rules)."""
        # Seed phase: everyone responds
        if not posts:
            return True, ["seed_phase"]

        # Refractory period check
        if self._in_refractory_period(posts):
            return False, []

        phase_config = self._get_phase_config(phase)
        triggered: List[str] = []

        if self._check_relevance(posts, phase_config):
            triggered.append("relevance")
        if self._check_disagreement(posts):
            triggered.append("disagreement")
        if self._check_question(posts):
            triggered.append("question")
        if self._check_silence_breaking(posts, phase_config):
            triggered.append("silence_breaking")
        if self._check_bridge_opportunity(posts):
            triggered.append("bridge_opportunity")
        if self._check_uncertainty_response(posts):
            triggered.append("uncertainty_response")

        # Red Team inverted rules
        if self.is_red_team:
            if self._check_consensus_forming(posts):
                triggered.append("consensus_forming")
            if self._check_criticism_gap(posts):
                triggered.append("criticism_gap")
            if self._check_premature_convergence(posts, phase):
                triggered.append("premature_convergence")

        return len(triggered) > 0, triggered

    def _in_refractory_period(self, posts: List[Post]) -> bool:
        """Check if agent posted too recently."""
        min_gap = self.config.refractory_period
        if len(posts) < min_gap:
            return False
        recent = posts[-min_gap:]
        return any(p.agent_id == self.agent_id for p in recent)

    def _get_phase_config(self, phase: Phase) -> Dict:
        """Get phase-modulated configuration."""
        phase_key = phase.value
        return {
            "relevance_threshold": self.config.relevance_phase_modulation.get(
                phase_key, self.config.relevance_min_keyword_matches
            ),
            "silence_max": self.config.silence_phase_modulation.get(
                phase_key, self.config.silence_max
            ),
            "window": self.config.window,
        }

    def _check_relevance(self, posts: List[Post], phase_config: Dict) -> bool:
        """Check if recent posts mention this agent's domain."""
        window = phase_config["window"]
        threshold = phase_config["relevance_threshold"]
        recent = posts[-window:]
        if not recent:
            return False

        combined_text = " ".join(p.content.lower() for p in recent)
        matches = sum(1 for kw in self.domain_keywords if kw.lower() in combined_text)
        return matches >= threshold

    def _check_disagreement(self, posts: List[Post]) -> bool:
        """Check if recent posts make strong claims in this agent's domain."""
        window = self.config.window
        recent = posts[-window:]

        assertion_indicators = [
            "clearly", "definitely", "certainly", "must be",
            "is proven", "demonstrates that", "shows that",
            "without doubt", "obviously",
        ]

        for post in recent:
            if post.agent_id == self.agent_id:
                continue

            content_lower = post.content.lower()
            is_my_domain = any(kw.lower() in content_lower for kw in self.domain_keywords)
            if not is_my_domain:
                continue

            has_strong_claim = any(ind in content_lower for ind in assertion_indicators)
            if has_strong_claim:
                return True

        return False

    def _check_question(self, posts: List[Post]) -> bool:
        """Check for unanswered questions in this agent's domain."""
        window = self.config.window
        recent = posts[-window:]

        for post in recent:
            if post.agent_id == self.agent_id:
                continue
            if "?" not in post.content:
                continue

            sentences = post.content.split(".")
            for sentence in sentences:
                if "?" not in sentence:
                    continue
                is_my_domain = any(
                    kw.lower() in sentence.lower() for kw in self.domain_keywords
                )
                if is_my_domain and not self._is_answered(posts, sentence):
                    return True

        return False

    def _is_answered(self, posts: List[Post], question: str) -> bool:
        """Check if this agent already answered a similar question."""
        q_keywords = set(question.lower().split())
        for post in posts:
            if post.agent_id != self.agent_id:
                continue
            p_keywords = set(post.content.lower().split())
            if len(q_keywords & p_keywords) > 3:
                return True
        return False

    def _check_silence_breaking(self, posts: List[Post], phase_config: Dict) -> bool:
        """Check if agent has been silent too long."""
        min_conv_length = self.config.silence_min_conversation_length
        max_silence = phase_config["silence_max"]

        if len(posts) < min_conv_length:
            return False

        last_post_index = -1
        for i, post in enumerate(posts):
            if post.agent_id == self.agent_id:
                last_post_index = i

        if last_post_index == -1:
            return True  # Never posted

        posts_since_last = len(posts) - last_post_index - 1
        if posts_since_last < max_silence:
            return False

        # Check if recent discussion is still relevant
        recent = posts[-max_silence:]
        combined_text = " ".join(p.content.lower() for p in recent)
        return any(kw.lower() in combined_text for kw in self.domain_keywords)

    def _check_bridge_opportunity(self, posts: List[Post]) -> bool:
        """Check if agent can bridge concepts from different agents."""
        window = self.config.window
        recent = posts[-window:]

        posts_by_agent: Dict[str, List[Post]] = {}
        for post in recent:
            if post.agent_id != self.agent_id:
                posts_by_agent.setdefault(post.agent_id, []).append(post)

        if len(posts_by_agent) < self.config.bridge_min_agents:
            return False

        agents = list(posts_by_agent.keys())
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                if self._find_bridge(
                    posts_by_agent[agents[i]], posts_by_agent[agents[j]]
                ):
                    return True
        return False

    def _find_bridge(self, posts_a: List[Post], posts_b: List[Post]) -> bool:
        """Find a bridging concept between two sets of posts."""
        text_a = " ".join(p.content.lower() for p in posts_a)
        text_b = " ".join(p.content.lower() for p in posts_b)

        a_touches = any(kw.lower() in text_a for kw in self.domain_keywords)
        b_touches = any(kw.lower() in text_b for kw in self.domain_keywords)

        if not (a_touches and b_touches):
            return False

        bridge_patterns = [
            ("mechanism", "application"),
            ("target", "compound"),
            ("efficacy", "safety"),
            ("preclinical", "clinical"),
            ("pathway", "drug"),
        ]

        for concept_a, concept_b in bridge_patterns:
            if (concept_a in text_a and concept_b in text_b) or (
                concept_b in text_a and concept_a in text_b
            ):
                return True
        return False

    def _check_uncertainty_response(self, posts: List[Post]) -> bool:
        """Check if recent posts express uncertainty in this agent's domain."""
        window = self.config.window
        recent = posts[-window:]

        uncertainty_indicators = [
            "unclear", "uncertain", "unknown", "not sure",
            "might be", "could be", "possibly", "perhaps",
            "needs more evidence", "insufficient data",
            "open question", "remains to be seen",
            "we don't know", "further research needed",
        ]

        for post in recent:
            if post.agent_id == self.agent_id:
                continue

            content_lower = post.content.lower()
            has_uncertainty = any(ind in content_lower for ind in uncertainty_indicators)
            if not has_uncertainty:
                continue

            is_my_domain = any(kw.lower() in content_lower for kw in self.domain_keywords)
            if is_my_domain:
                return True

        return False

    # --- Red Team inverted rules ---

    def _check_consensus_forming(self, posts: List[Post]) -> bool:
        """Red Team: trigger when consensus is forming."""
        window = self.config.window
        recent = posts[-window:]
        supportive = sum(1 for p in recent if p.stance == AgentStance.SUPPORTIVE)
        return supportive >= self.config.red_team_consensus_threshold

    def _check_criticism_gap(self, posts: List[Post]) -> bool:
        """Red Team: trigger when no recent criticism."""
        window = self.config.window
        recent = posts[-window:]
        critical = sum(1 for p in recent if p.stance == AgentStance.CRITICAL)
        return critical == 0 and len(recent) >= self.config.red_team_criticism_gap

    def _check_premature_convergence(self, posts: List[Post], phase: Phase) -> bool:
        """Red Team: trigger during CONVERGE if debate was insufficient."""
        if phase != Phase.CONVERGE:
            return False
        if len(posts) < self.config.red_team_min_debate_posts:
            return True
        critical_posts = [p for p in posts if p.stance == AgentStance.CRITICAL]
        return len(critical_posts) < 3

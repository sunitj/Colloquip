"""Base deliberation agent."""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from colloquip.agents.prompts import build_system_prompt, build_user_prompt
from colloquip.llm.interface import LLMInterface
from colloquip.models import AgentConfig, AgentDependencies, Citation, Phase, Post
from colloquip.triggers import TriggerEvaluator

logger = logging.getLogger(__name__)


class BaseDeliberationAgent:
    """Base class for all deliberation agents."""

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMInterface,
        trigger_evaluator: Optional[TriggerEvaluator] = None,
        prompt_version: str = "v1",
        phase_max_tokens: Optional[Dict[str, int]] = None,
    ):
        self.config = config
        self.llm = llm
        self.prompt_version = prompt_version
        self.phase_max_tokens = phase_max_tokens
        # Token counts from the last LLM call (used by engine for cost tracking)
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.trigger_evaluator = trigger_evaluator or TriggerEvaluator(
            agent_id=config.agent_id,
            domain_keywords=config.domain_keywords,
            knowledge_scope=config.knowledge_scope,
            is_red_team=config.is_red_team,
        )

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def display_name(self) -> str:
        return self.config.display_name

    def should_respond(self, posts: List[Post], phase: Phase) -> Tuple[bool, List[str]]:
        """Evaluate trigger rules to decide if agent should respond."""
        return self.trigger_evaluator.evaluate(posts, phase)

    async def generate_post(self, deps: AgentDependencies) -> Post:
        """Generate a post given current context."""
        system_prompt = build_system_prompt(self.config, deps.phase, self.prompt_version)
        user_prompt = build_user_prompt(
            hypothesis=deps.session.hypothesis,
            posts=deps.posts,
            phase_observation=deps.phase_signal.observation,
        )

        try:
            phase_tokens = (
                self.phase_max_tokens.get(deps.phase.value) if self.phase_max_tokens else None
            )
            result = await self.llm.generate(system_prompt, user_prompt, max_tokens=phase_tokens)
            self.last_input_tokens = getattr(result, "input_tokens", 0)
            self.last_output_tokens = getattr(result, "output_tokens", 0)
            # Convert raw citation dicts from LLMResult to Citation models
            post_citations = [Citation(**c) for c in getattr(result, "citations", [])]
            return Post(
                id=uuid4(),
                session_id=deps.session.id,
                agent_id=self.agent_id,
                content=result.content,
                stance=result.stance,
                citations=post_citations,
                key_claims=result.key_claims,
                questions_raised=result.questions_raised,
                connections_identified=result.connections_identified,
                novelty_score=result.novelty_score,
                phase=deps.phase,
                triggered_by=[],  # Filled by engine
            )
        except Exception as e:
            logger.error("Agent %s failed to generate post: %s", self.agent_id, e)
            return self._fallback_post(deps)

    def _fallback_post(self, deps: AgentDependencies) -> Post:
        """Generate a minimal fallback post when LLM fails."""
        from colloquip.models import AgentStance

        return Post(
            id=uuid4(),
            session_id=deps.session.id,
            agent_id=self.agent_id,
            content=(
                f"As the {self.display_name} expert, I note the discussion "
                f"and will contribute further analysis when more data is available."
            ),
            stance=AgentStance.NEUTRAL,
            novelty_score=0.1,
            phase=deps.phase,
            triggered_by=["fallback"],
        )

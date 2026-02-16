"""Main deliberation engine orchestrating the emergent loop."""

import asyncio
import logging
from collections import Counter, defaultdict
from typing import AsyncIterator, Dict, List, Union

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.agents.prompts import build_synthesis_prompt
from colloquip.energy import EnergyCalculator
from colloquip.llm.interface import LLMInterface
from colloquip.models import (
    AgentDependencies,
    AgentStance,
    ConsensusMap,
    ConversationMetrics,
    DeliberationSession,
    EnergySource,
    EnergyUpdate,
    HumanIntervention,
    Phase,
    PhaseSignal,
    Post,
    SessionStatus,
)
from colloquip.observer import ObserverAgent

logger = logging.getLogger(__name__)


class EmergentDeliberationEngine:
    """Main engine for emergent deliberation.

    Replaces hardcoded phase sequence with:
    - Observer-based phase detection
    - Trigger-based agent selection
    - Energy-based termination
    """

    def __init__(
        self,
        agents: Dict[str, BaseDeliberationAgent],
        observer: ObserverAgent,
        energy_calculator: EnergyCalculator,
        llm: LLMInterface,
        max_turns: int = 30,
        min_posts: int = 12,
        cost_tracker=None,
        session_id=None,
    ):
        self.agents = agents
        self.observer = observer
        self.energy_calculator = energy_calculator
        self.llm = llm
        self.max_turns = max_turns
        self.min_posts = min_posts
        self._cost_tracker = cost_tracker
        self._session_id = session_id

    async def run_deliberation(
        self,
        session: DeliberationSession,
        hypothesis: str,
    ) -> AsyncIterator[Union[Post, PhaseSignal, EnergyUpdate, ConsensusMap]]:
        """Run emergent deliberation, yielding events as they occur."""
        posts: List[Post] = []
        energy_history: List[float] = []
        turn = 0

        session.status = SessionStatus.RUNNING
        session.phase = Phase.EXPLORE

        # --- Seed phase: all agents produce initial posts ---
        logger.info("Starting seed phase for session %s", session.id)
        seed_posts = await self._run_seed_phase(session, hypothesis, posts)
        for post in seed_posts:
            posts.append(post)
            yield post

        # Initial energy
        energy_update = self.energy_calculator.calculate_energy_update(posts, turn)
        energy_history.append(energy_update.energy)
        yield energy_update

        # --- Main loop ---
        while turn < self.max_turns:
            turn += 1

            # 1. Observer detects phase
            phase_signal = self.observer.detect_phase(posts)
            session.phase = phase_signal.current_phase
            yield phase_signal

            # 2. Termination check
            should_stop, reason = self.energy_calculator.should_terminate(posts, energy_history)
            if should_stop:
                logger.info("Terminating: %s", reason)
                break

            # 3. Trigger evaluation — find responding agents
            responding = self._evaluate_triggers(posts, phase_signal.current_phase)

            if not responding:
                logger.debug("No agents triggered on turn %d", turn)
                # If no one triggers and we're past min_posts, energy decays
                if len(posts) >= self.min_posts:
                    energy_update = self.energy_calculator.calculate_energy_update(posts, turn)
                    energy_history.append(energy_update.energy)
                    yield energy_update
                # Yield control so CancelledError can be delivered
                await asyncio.sleep(0)
                continue

            # 4. Generate posts concurrently
            new_posts = await self._generate_posts(responding, session, phase_signal, posts)

            for post in new_posts:
                posts.append(post)
                yield post

            # 5. Update energy
            energy_update = self.energy_calculator.calculate_energy_update(posts, turn)
            energy_history.append(energy_update.energy)
            yield energy_update

            # 6. Energy injection for novel posts (at most one boost per turn)
            max_novelty = max((p.novelty_score for p in new_posts), default=0.0)
            if max_novelty > 0.7:
                boosted = self.energy_calculator.inject_energy(
                    EnergySource.NOVEL_POST, energy_history[-1]
                )
                energy_history[-1] = boosted
                # Re-yield updated energy so display stays consistent
                yield EnergyUpdate(
                    turn=turn,
                    energy=boosted,
                    components=energy_update.components,
                )

        # --- Synthesis ---
        session.phase = Phase.SYNTHESIS
        consensus = await self._run_synthesis(session, hypothesis, posts)
        session.status = SessionStatus.COMPLETED
        yield consensus

    async def handle_intervention(
        self,
        session: DeliberationSession,
        intervention: HumanIntervention,
        posts: List[Post],
        energy_history: List[float],
    ) -> List[Post]:
        """Handle human intervention mid-deliberation.

        Returns a list of posts: the human post followed by agent responses.
        """
        # Energy injection
        if intervention.type == "terminate":
            energy_history.append(0.0)
            return []

        if intervention.type in ("question", "data", "redirect"):
            current_e = energy_history[-1] if energy_history else 0.5
            boosted = self.energy_calculator.inject_energy(
                EnergySource.HUMAN_INTERVENTION, current_e
            )
            energy_history.append(boosted)

        # Create a human post
        human_post = Post(
            session_id=session.id,
            agent_id="human",
            content=intervention.content,
            stance=AgentStance.NEUTRAL,
            novelty_score=0.5,
            phase=session.phase,
            triggered_by=["human_intervention"],
        )
        posts.append(human_post)

        # Get responses from triggered agents
        phase_signal = self.observer.detect_phase(posts)
        responding = self._evaluate_triggers(posts, phase_signal.current_phase)
        new_posts = await self._generate_posts(responding, session, phase_signal, posts)
        return [human_post] + new_posts

    async def _run_seed_phase(
        self,
        session: DeliberationSession,
        hypothesis: str,
        posts: List[Post],
    ) -> List[Post]:
        """All agents produce initial posts."""
        seed_signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
            observation=None,
        )

        deps = AgentDependencies(
            session=session,
            phase=Phase.EXPLORE,
            phase_signal=seed_signal,
            posts=list(posts),  # snapshot for concurrent agents
        )

        tasks = []
        for agent in self.agents.values():
            tasks.append(self._safe_generate(agent, deps, ["seed_phase"]))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        seed_posts = []
        for result in results:
            if isinstance(result, Post):
                seed_posts.append(result)
            elif isinstance(result, Exception):
                logger.error("Seed phase agent failure: %s", result)

        return seed_posts

    def _evaluate_triggers(
        self,
        posts: List[Post],
        phase: Phase,
    ) -> Dict[str, List[str]]:
        """Evaluate triggers for all agents, return {agent_id: triggered_rules}."""
        from colloquip.metrics import agent_triggers_total

        responding: Dict[str, List[str]] = {}
        for agent_id, agent in self.agents.items():
            should_respond, rules = agent.should_respond(posts, phase)
            if should_respond:
                responding[agent_id] = rules
                for rule in rules:
                    agent_triggers_total.labels(
                        agent_id=agent_id, trigger_type=rule
                    ).inc()
        return responding

    async def _generate_posts(
        self,
        responding: Dict[str, List[str]],
        session: DeliberationSession,
        phase_signal: PhaseSignal,
        posts: List[Post],
    ) -> List[Post]:
        """Generate posts from responding agents concurrently."""
        deps = AgentDependencies(
            session=session,
            phase=phase_signal.current_phase,
            phase_signal=phase_signal,
            posts=list(posts),  # snapshot for concurrent agents
        )

        tasks = []
        agent_rules = []
        for agent_id, rules in responding.items():
            agent = self.agents[agent_id]
            tasks.append(self._safe_generate(agent, deps, rules))
            agent_rules.append(rules)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_posts = []
        for i, result in enumerate(results):
            if isinstance(result, Post):
                result.triggered_by = agent_rules[i]
                new_posts.append(result)
            elif isinstance(result, Exception):
                logger.error("Agent generation failure: %s", result)

        return new_posts

    def _record_cost(self, agent: BaseDeliberationAgent):
        """Record the last LLM call's cost from the agent."""
        if self._cost_tracker and self._session_id:
            input_t = getattr(agent, "last_input_tokens", 0)
            output_t = getattr(agent, "last_output_tokens", 0)
            if input_t or output_t:
                model = getattr(self.llm, "model", "unknown")
                self._cost_tracker.record(self._session_id, input_t, output_t, model)

        # Always record agent-level token metrics
        from colloquip.metrics import agent_tokens_total

        input_t = getattr(agent, "last_input_tokens", 0)
        output_t = getattr(agent, "last_output_tokens", 0)
        if input_t:
            agent_tokens_total.labels(agent_id=agent.agent_id, direction="input").inc(input_t)
        if output_t:
            agent_tokens_total.labels(agent_id=agent.agent_id, direction="output").inc(output_t)

    async def _safe_generate(
        self,
        agent: BaseDeliberationAgent,
        deps: AgentDependencies,
        rules: List[str],
    ) -> Post:
        """Generate post with error handling — always returns a Post."""
        try:
            post = await agent.generate_post(deps)
            post.triggered_by = rules
            self._record_cost(agent)

            from colloquip.metrics import (
                agent_citations_total,
                agent_novelty_score,
                agent_posts_total,
            )

            agent_posts_total.labels(
                agent_id=agent.agent_id,
                stance=post.stance.value,
                phase=post.phase.value,
            ).inc()
            agent_novelty_score.labels(agent_id=agent.agent_id).observe(post.novelty_score)
            if post.citations:
                agent_citations_total.labels(agent_id=agent.agent_id).inc(len(post.citations))

            return post
        except Exception as e:
            logger.error("Agent %s failed: %s", agent.agent_id, e)
            try:
                return agent._fallback_post(deps)
            except Exception as fallback_err:
                logger.error("Agent %s fallback also failed: %s", agent.agent_id, fallback_err)
                return Post(
                    session_id=deps.session.id,
                    agent_id=agent.agent_id,
                    content="[Agent encountered an error and could not respond]",
                    stance=AgentStance.NEUTRAL,
                    novelty_score=0.0,
                    phase=deps.phase,
                    triggered_by=rules,
                )

    async def _run_synthesis(
        self,
        session: DeliberationSession,
        hypothesis: str,
        posts: List[Post],
    ) -> ConsensusMap:
        """Generate final ConsensusMap from deliberation."""
        if not posts:
            return ConsensusMap(
                session_id=session.id,
                summary="No posts were generated during deliberation.",
            )

        prompt = build_synthesis_prompt(hypothesis, posts)

        try:
            # Snapshot token counts before synthesis call
            pre_input = getattr(self.llm, "_total_input_tokens", 0)
            pre_output = getattr(self.llm, "_total_output_tokens", 0)

            summary = await self.llm.generate_synthesis(
                system_prompt=(
                    "You are a deliberation synthesizer. "
                    "Summarize the multi-agent deliberation into a structured consensus."
                ),
                user_prompt=prompt,
            )

            # Record synthesis cost
            if self._cost_tracker and self._session_id:
                post_input = getattr(self.llm, "_total_input_tokens", 0)
                post_output = getattr(self.llm, "_total_output_tokens", 0)
                model = getattr(self.llm, "model", "unknown")
                self._cost_tracker.record(
                    self._session_id,
                    post_input - pre_input,
                    post_output - pre_output,
                    model,
                )
        except Exception as e:
            logger.error("Synthesis generation failed: %s", e)
            summary = "Synthesis generation failed. Please review the deliberation posts."

        # Extract final stances from last post per agent
        final_stances: Dict[str, AgentStance] = {}
        for post in reversed(posts):
            if post.agent_id not in final_stances and post.agent_id != "human":
                final_stances[post.agent_id] = post.stance

        return ConsensusMap(
            session_id=session.id,
            summary=summary,
            agreements=self._extract_agreements(posts),
            disagreements=self._extract_disagreements(posts),
            minority_positions=self._extract_minority_positions(posts),
            serendipity_connections=self._extract_connections(posts),
            final_stances=final_stances,
        )

    def _extract_agreements(self, posts: List[Post]) -> List[str]:
        """Extract points of agreement from posts."""
        supportive_claims = []
        for post in posts:
            if post.stance == AgentStance.SUPPORTIVE:
                supportive_claims.extend(post.key_claims)
        seen = set()
        unique = []
        for claim in supportive_claims:
            if claim not in seen:
                seen.add(claim)
                unique.append(claim)
        return unique[:5]

    def _extract_disagreements(self, posts: List[Post]) -> List[str]:
        """Extract points of disagreement."""
        critical_claims = []
        for post in posts:
            if post.stance == AgentStance.CRITICAL:
                critical_claims.extend(post.key_claims)
        seen = set()
        unique = []
        for claim in critical_claims:
            if claim not in seen:
                seen.add(claim)
                unique.append(claim)
        return unique[:5]

    def _extract_minority_positions(self, posts: List[Post]) -> List[str]:
        """Extract minority positions worth preserving.

        A minority position is one held by fewer than half the agents.
        """
        # Determine each agent's dominant stance
        agent_stance_counts: Dict[str, Counter] = defaultdict(Counter)
        for post in posts:
            if post.agent_id != "human":
                agent_stance_counts[post.agent_id][post.stance] += 1

        agent_dominant: Dict[str, AgentStance] = {}
        for agent_id, counts in agent_stance_counts.items():
            agent_dominant[agent_id] = counts.most_common(1)[0][0]

        # Count how many agents hold each dominant stance
        stance_agent_count = Counter(agent_dominant.values())
        total_agents = len(agent_dominant)

        # A minority stance is one held by fewer than half the agents
        minority_stances = {
            stance for stance, count in stance_agent_count.items() if count < total_agents / 2
        }

        # Collect claims from agents whose dominant stance is a minority
        minority: List[str] = []
        for post in posts:
            if (
                post.agent_id in agent_dominant
                and agent_dominant[post.agent_id] in minority_stances
            ):
                for claim in post.key_claims:
                    if claim not in minority:
                        minority.append(claim)
        return minority[:3]

    def _extract_connections(self, posts: List[Post]) -> List[Dict]:
        """Extract serendipitous connections."""
        connections = []
        for post in posts:
            if post.stance == AgentStance.NOVEL_CONNECTION:
                for conn in post.connections_identified:
                    connections.append(
                        {
                            "agent": post.agent_id,
                            "connection": conn,
                        }
                    )
        return connections[:5]

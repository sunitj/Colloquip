"""Autoresearch loop — Karpathy-style iterate/evaluate/commit-or-reset.

The loop owns a mutable ``scratchpad`` (the "work file") and iterates up to
``AutoresearchConfig.max_steps`` times. Each step:

1. Proposes an action (search/read_memory/reflect) — currently the action
   schedule is deterministic so the loop runs without an LLM step-proposer.
2. Executes the action via the shared :class:`ToolRegistry` when applicable.
3. Evaluates the metric delta for the candidate scratchpad.
4. Commits the step if the delta exceeds the threshold; otherwise reverts.
5. Stops early after two sub-threshold steps or when budgets are exhausted.

An :class:`AutoresearchRun` audit record is returned regardless of outcome.
A hard cap of :data:`MAX_AUTORESEARCH_TOKENS_PER_RUN` is enforced even if the
config requests more, to protect against runaway cost.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, List, Optional

from colloquip.autoresearch.metrics import AutoresearchMetric, get_metric
from colloquip.models import (
    MAX_AUTORESEARCH_TOKENS_PER_RUN,
    AgentDependencies,
    AutoresearchActionType,
    AutoresearchConfig,
    AutoresearchRun,
    AutoresearchStatus,
    AutoresearchStep,
    Citation,
)

logger = logging.getLogger(__name__)


class AutoresearchLoop:
    """The shared autoresearch capability invoked from any agent.

    Parameters
    ----------
    tool_registry:
        Optional shared :class:`ToolRegistry`. When None, the loop degrades
        gracefully to reflect-only steps so unit tests and the mock path
        don't require tool plumbing.
    """

    def __init__(self, tool_registry: Optional[Any] = None):
        self._tool_registry = tool_registry

    async def run(
        self,
        deps: AgentDependencies,
        agent_id: str,
        config: Optional[AutoresearchConfig] = None,
    ) -> AutoresearchRun:
        config = config or AutoresearchConfig()
        metric: AutoresearchMetric = get_metric(config.metric)
        scratchpad = ""
        steps: List[AutoresearchStep] = []
        citations: List[Citation] = []

        run = AutoresearchRun(
            thread_id=deps.session.id,
            agent_id=agent_id,
            subreddit_id=deps.subreddit_id,
            config=config,
            metric_name=metric.name,
            metric_start=metric.evaluate("", scratchpad),
            status=AutoresearchStatus.RUNNING,
        )
        started_wall = time.monotonic()
        consecutive_nogain = 0

        try:
            for step_index in range(max(0, config.max_steps)):
                # Wallclock budget
                if time.monotonic() - started_wall > config.max_wallclock_seconds:
                    run.status = AutoresearchStatus.BUDGET_EXCEEDED
                    break
                # Token budget (hard cap always wins)
                total_tokens = run.input_tokens + run.output_tokens
                token_cap = min(config.max_tokens, MAX_AUTORESEARCH_TOKENS_PER_RUN)
                if total_tokens >= token_cap:
                    run.status = AutoresearchStatus.BUDGET_EXCEEDED
                    break

                action = self._pick_action(step_index, config)
                step = AutoresearchStep(
                    step_index=step_index,
                    action=action,
                    rationale=self._rationale_for(action, deps),
                    metric_before=metric.evaluate("", scratchpad),
                )
                try:
                    added_text, step_citations, tokens_in, tokens_out = await self._execute_step(
                        action, deps, scratchpad
                    )
                except Exception as exc:  # noqa: BLE001
                    step.error = str(exc)
                    step.committed = False
                    steps.append(step)
                    consecutive_nogain += 1
                    if consecutive_nogain >= 2:
                        break
                    continue

                step.tokens_in = tokens_in
                step.tokens_out = tokens_out
                step.summary = added_text.strip()[:500]
                step.query = self._last_query(action, deps)

                candidate = (scratchpad + "\n\n" + added_text).strip() if added_text else scratchpad
                step.metric_after = metric.evaluate("", candidate)
                step.delta = step.metric_after - step.metric_before
                if step.delta > config.threshold:
                    scratchpad = candidate
                    step.committed = True
                    citations.extend(step_citations)
                    consecutive_nogain = 0
                else:
                    step.committed = False
                    consecutive_nogain += 1

                # Always count tokens, even when uncommitted — they were spent
                run.input_tokens += tokens_in
                run.output_tokens += tokens_out
                steps.append(step)

                if consecutive_nogain >= 2:
                    break

            if run.status == AutoresearchStatus.RUNNING:
                run.status = AutoresearchStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            logger.exception("Autoresearch loop failed: %s", exc)
            run.status = AutoresearchStatus.FAILED
        finally:
            run.steps = steps
            run.scratchpad = scratchpad
            run.citations = citations
            run.metric_end = metric.evaluate("", scratchpad)
            run.finished_at = datetime.now(timezone.utc)

        return run

    # ---- Overridable hooks for subclasses / mocks ----

    def _pick_action(
        self,
        step_index: int,
        config: AutoresearchConfig,
    ) -> AutoresearchActionType:
        """Deterministic action scheduler: cycles through the allowed list.

        Subclasses can override with an LLM-driven policy.
        """
        allowed = config.allowed_actions or [AutoresearchActionType.REFLECT]
        return allowed[step_index % len(allowed)]

    def _rationale_for(self, action: AutoresearchActionType, deps: AgentDependencies) -> str:
        hypothesis = deps.session.hypothesis if deps.session else ""
        return f"step action={action.value} for hypothesis={hypothesis[:80]!r}"

    def _last_query(self, action: AutoresearchActionType, deps: AgentDependencies) -> str:
        if deps.session:
            return deps.session.hypothesis[:200]
        return ""

    async def _execute_step(
        self,
        action: AutoresearchActionType,
        deps: AgentDependencies,
        scratchpad: str,
    ) -> tuple[str, List[Citation], int, int]:
        """Execute a single action and return (text, citations, input_tokens, output_tokens)."""
        if action == AutoresearchActionType.REFLECT:
            return await self._reflect(deps, scratchpad)
        if action == AutoresearchActionType.READ_MEMORY:
            return await self._read_memory(deps, scratchpad)
        if action in (
            AutoresearchActionType.SEARCH_PUBMED,
            AutoresearchActionType.SEARCH_WEB,
            AutoresearchActionType.QUERY_COMPANY_DOCS,
        ):
            return await self._tool_search(action, deps, scratchpad)
        return "", [], 0, 0

    async def _reflect(
        self,
        deps: AgentDependencies,
        scratchpad: str,
    ) -> tuple[str, List[Citation], int, int]:
        """Pure reflection — no external calls.

        Without an LLM hook in place (Phase 6 MVP), reflection synthesizes a
        lightweight "observation" from the session state so the scratchpad
        grows deterministically. This is intentionally cheap; richer reflect
        steps can plug in an LLM later.
        """
        hypothesis = deps.session.hypothesis if deps.session else ""
        # Build a mini observation we haven't added before.
        mission_hint = (deps.subreddit_mission or "").strip().split("\n", 1)[0][:100]
        line = f"- Reflection: revisit hypothesis {hypothesis[:80]!r}" + (
            f"; mission: {mission_hint}" if mission_hint else ""
        )
        if line in scratchpad:
            # Vary so the scratchpad grows
            line = line + f" (pass {scratchpad.count('Reflection:') + 1})"
        return line, [], 80, 40

    async def _read_memory(
        self,
        deps: AgentDependencies,
        scratchpad: str,
    ) -> tuple[str, List[Citation], int, int]:
        # Without a memory store plumbed through, return a placeholder block.
        # Real integration can inject a MemoryStore via subclass.
        line = "- Memory: no prior syntheses matched this hypothesis yet."
        return line, [], 40, 20

    async def _tool_search(
        self,
        action: AutoresearchActionType,
        deps: AgentDependencies,
        scratchpad: str,
    ) -> tuple[str, List[Citation], int, int]:
        if self._tool_registry is None:
            # Degrade to reflect when no tools are available.
            return await self._reflect(deps, scratchpad)
        # Placeholder: most ToolRegistry implementations need an async
        # search via a specific tool_id. Subclasses can route the action
        # to the correct tool. For Phase 6 MVP we fall through to reflect.
        return await self._reflect(deps, scratchpad)


class MockAutoresearchLoop(AutoresearchLoop):
    """Deterministic mock for tests — no tool_registry, predictable scratchpad."""

    def __init__(self):
        super().__init__(tool_registry=None)

    async def _execute_step(
        self,
        action: AutoresearchActionType,
        deps: AgentDependencies,
        scratchpad: str,
    ) -> tuple[str, List[Citation], int, int]:
        idx = scratchpad.count("\n- Finding")
        # Make each step add a distinctly novel finding
        added = (
            f"- Finding {idx}: action={action.value} "
            f"novel-{idx}-token token-{idx * 7} insight-{idx * 11}"
        )
        citations: List[Citation] = []
        # Give each call a predictable token budget
        return added, citations, 200, 100

"""FastAPI application factory and session management."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from uuid import UUID

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.config import EnergyConfig
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentConfig,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    HumanIntervention,
    Phase,
    PhaseSignal,
    Post,
    SessionStatus,
)
from colloquip.observer import ObserverAgent

logger = logging.getLogger(__name__)

# Max events queued per subscriber before dropping
_SUBSCRIBER_QUEUE_SIZE = 256


class SessionManager:
    """Manages active deliberation sessions and their state.

    Keeps in-memory state for real-time streaming plus optional
    database persistence for durability across restarts.
    """

    def __init__(self, db_session_factory: Optional[Callable] = None):
        # In-memory state (always present)
        self.sessions: Dict[UUID, DeliberationSession] = {}
        self.posts: Dict[UUID, list] = {}
        self.energy_history: Dict[UUID, list] = {}  # List[float] for engine use
        self.engines: Dict[UUID, EmergentDeliberationEngine] = {}
        self.events: Dict[UUID, list] = {}
        self.subscribers: Dict[UUID, list[asyncio.Queue]] = {}
        self._running_tasks: Dict[UUID, asyncio.Task] = {}
        self._session_locks: Dict[UUID, asyncio.Lock] = {}
        # Community context for memory creation after deliberation
        self._session_context: Dict[UUID, Dict[str, Any]] = {}
        # Optional database factory
        self._db_factory = db_session_factory
        # Load phase_max_tokens from config
        self._phase_max_tokens = self._load_phase_max_tokens()

    @staticmethod
    def _load_phase_max_tokens() -> Dict[str, int]:
        from pathlib import Path

        from colloquip.config import load_config

        config = load_config(engine_path=Path("config/engine.yaml"))
        return config.engine.phase_max_tokens

    def create_session(
        self,
        hypothesis: str,
        mode: str = "mock",
        seed: int = 42,
        model: Optional[str] = None,
        max_turns: int = 30,
        community_name: Optional[str] = None,
        platform_manager: Optional[Any] = None,
        session_id: Optional[str] = None,
        memory_store: Optional[Any] = None,
    ) -> DeliberationSession:
        """Create a new deliberation session."""
        if session_id:
            session = DeliberationSession(id=UUID(session_id), hypothesis=hypothesis)
        else:
            session = DeliberationSession(hypothesis=hypothesis)
        self.sessions[session.id] = session
        self.posts[session.id] = []
        self.energy_history[session.id] = []
        self.events[session.id] = []
        self.subscribers[session.id] = []
        self._session_locks[session.id] = asyncio.Lock()

        # Store community context for memory creation later
        subreddit_id = None
        subreddit_name = community_name or ""
        if community_name and platform_manager:
            sub = platform_manager.get_subreddit_by_name(community_name)
            if sub:
                subreddit_id = sub["id"]
        self._session_context[session.id] = {
            "subreddit_id": subreddit_id,
            "subreddit_name": subreddit_name,
            "memory_store": memory_store,
            "platform_manager": platform_manager,
            "thread_id": session_id or str(session.id),
        }

        # Create engine components
        llm = self._create_llm(mode, seed, model)
        agents = self._create_agents_from_community(llm, community_name, platform_manager)
        num_agents = len(agents)

        energy_config = EnergyConfig()
        energy_calc = EnergyCalculator(config=energy_config, num_agents=num_agents)
        observer = ObserverAgent(energy_calculator=energy_calc, num_agents=num_agents)

        # Wire cost tracker from platform manager
        cost_tracker = getattr(platform_manager, "cost_tracker", None) if platform_manager else None

        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=observer,
            energy_calculator=energy_calc,
            llm=llm,
            max_turns=max_turns,
            min_posts=12,
            cost_tracker=cost_tracker,
            session_id=session.id,
        )
        self.engines[session.id] = engine

        return session

    def get_session(self, session_id: UUID) -> Optional[DeliberationSession]:
        return self.sessions.get(session_id)

    def get_posts(self, session_id: UUID) -> list:
        """Return a snapshot copy of the posts list."""
        return list(self.posts.get(session_id, []))

    def get_energy_history(self, session_id: UUID) -> list:
        """Return energy history as full EnergyUpdate dicts for the API."""
        events = self.events.get(session_id, [])
        return [e["data"] for e in events if e.get("type") == "energy_update"]

    def get_events(self, session_id: UUID) -> list:
        """Return a snapshot copy of the events list."""
        return list(self.events.get(session_id, []))

    def subscribe(self, session_id: UUID) -> asyncio.Queue:
        """Subscribe to real-time events for a session."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_SIZE)
        if session_id not in self.subscribers:
            self.subscribers[session_id] = []
        self.subscribers[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: UUID, queue: asyncio.Queue):
        """Remove a subscriber."""
        if session_id in self.subscribers:
            try:
                self.subscribers[session_id].remove(queue)
            except ValueError:
                pass

    def cancel_if_no_subscribers(self, session_id: UUID):
        """Cancel the deliberation task if no subscribers remain."""
        if not self.subscribers.get(session_id):
            task = self._running_tasks.get(session_id)
            if task and not task.done():
                task.cancel()
                logger.info("Cancelled deliberation for session %s (no subscribers)", session_id)

    async def _broadcast(self, session_id: UUID, event: dict):
        """Broadcast an event to all subscribers of a session."""
        if session_id in self.events:
            self.events[session_id].append(event)
        for queue in self.subscribers.get(session_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping event")

    async def start_deliberation(self, session_id: UUID):
        """Start the deliberation loop for a session."""
        session = self.sessions.get(session_id)
        engine = self.engines.get(session_id)
        if not session or not engine:
            raise ValueError(f"Session {session_id} not found")

        if session.status == SessionStatus.RUNNING:
            raise ValueError(f"Session {session_id} is already running")

        # Guard against a completed task that hasn't been cleaned up yet
        existing_task = self._running_tasks.get(session_id)
        if existing_task and not existing_task.done():
            raise ValueError(f"Session {session_id} already has a running task")

        # Set status BEFORE creating the task to prevent race conditions
        session.status = SessionStatus.RUNNING

        # Start cost tracking timer
        cost_tracker = getattr(engine, "_cost_tracker", None)
        if cost_tracker:
            cost_tracker.start_tracking(session_id)

        task = asyncio.create_task(self._run_deliberation(session_id))
        self._running_tasks[session_id] = task

    def _update_platform_thread(self, session_id: UUID, **kwargs) -> None:
        """Push status/phase/post_count changes to PlatformManager."""
        ctx = self._session_context.get(session_id, {})
        pm = ctx.get("platform_manager")
        thread_id = ctx.get("thread_id")
        if pm and thread_id and hasattr(pm, "update_thread_status"):
            pm.update_thread_status(thread_id, **kwargs)

    async def _run_deliberation(self, session_id: UUID):
        """Internal deliberation runner that broadcasts events."""
        session = self.sessions.get(session_id)
        try:
            engine = self.engines[session_id]
            posts = self.posts[session_id]
            lock = self._session_locks[session_id]

            async for event in engine.run_deliberation(session, session.hypothesis):
                if isinstance(event, Post):
                    async with lock:
                        posts.append(event)
                    post_count = len(posts)
                    # First post: mark thread as active
                    if post_count == 1:
                        self._update_platform_thread(
                            session_id, status="active", post_count=post_count
                        )
                    else:
                        self._update_platform_thread(session_id, post_count=post_count)
                    await self._broadcast(
                        session_id,
                        {
                            "type": "post",
                            "data": event.model_dump(mode="json"),
                        },
                    )
                    await self._persist_post(event)
                elif isinstance(event, PhaseSignal):
                    self._update_platform_thread(session_id, phase=event.current_phase.value)
                    await self._broadcast(
                        session_id,
                        {
                            "type": "phase_change",
                            "data": event.model_dump(mode="json"),
                        },
                    )
                elif isinstance(event, EnergyUpdate):
                    # Store float for engine use; broadcast full dict for frontend
                    self.energy_history[session_id].append(event.energy)
                    await self._broadcast(
                        session_id,
                        {
                            "type": "energy_update",
                            "data": event.model_dump(mode="json"),
                        },
                    )
                    await self._persist_energy(session_id, event)
                elif isinstance(event, ConsensusMap):
                    self._update_platform_thread(session_id, status="completed", phase="synthesis")
                    await self._broadcast(
                        session_id,
                        {
                            "type": "session_complete",
                            "data": event.model_dump(mode="json"),
                        },
                    )
                    await self._persist_consensus(event)
                    await self._extract_memory(session_id, event)

            await self._broadcast(session_id, {"type": "done", "data": None})
            await self._persist_session_status(session_id)
        except asyncio.CancelledError:
            logger.info("Deliberation cancelled for session %s", session_id)
            if session and session.status != SessionStatus.COMPLETED:
                session.status = SessionStatus.PAUSED
                self._update_platform_thread(session_id, status="paused")
            elif session:
                # Already completed; keep the correct status
                self._update_platform_thread(session_id, status="completed")
            await self._persist_session_status(session_id)
        except Exception as e:
            logger.error("Deliberation error for session %s: %s", session_id, e)
            if session:
                session.status = SessionStatus.FAILED
            self._update_platform_thread(session_id, status="failed")
            await self._broadcast(
                session_id,
                {
                    "type": "error",
                    "data": {"message": str(e)},
                },
            )
            await self._persist_session_status(session_id)
        finally:
            self._running_tasks.pop(session_id, None)

    async def intervene(self, session_id: UUID, intervention: HumanIntervention) -> list:
        """Handle human intervention in an active session."""
        session = self.sessions.get(session_id)
        engine = self.engines.get(session_id)
        if not session or not engine:
            raise ValueError(f"Session {session_id} not found")

        if session.status != SessionStatus.RUNNING:
            raise ValueError(
                f"Session {session_id} is not running (status: {session.status.value})"
            )

        lock = self._session_locks[session_id]
        async with lock:
            posts = self.posts[session_id]
            energy_history = self.energy_history[session_id]
            result_posts = await engine.handle_intervention(
                session, intervention, posts, energy_history
            )

        for post in result_posts:
            await self._broadcast(
                session_id,
                {
                    "type": "post",
                    "data": post.model_dump(mode="json"),
                },
            )
            await self._persist_post(post)
        return result_posts

    # ---- Database persistence (optional) ----

    @asynccontextmanager
    async def _db_repo(self) -> AsyncIterator:
        """Yield a SessionRepository if DB is configured, committing on success."""
        from colloquip.db.repository import SessionRepository

        async with self._db_factory() as db:
            repo = SessionRepository(db)
            yield repo
            await repo.commit()

    async def persist_session(self, session: DeliberationSession) -> None:
        """Persist a session to the database (if configured)."""
        if not self._db_factory:
            return
        try:
            async with self._db_repo() as repo:
                await repo.save_session(session)
        except Exception as e:
            logger.error("Failed to persist session: %s", e)

    async def _persist_post(self, post: Post) -> None:
        if not self._db_factory:
            return
        try:
            async with self._db_repo() as repo:
                await repo.save_post(post)
        except Exception as e:
            logger.error("Failed to persist post: %s", e)

    async def _persist_energy(self, session_id: UUID, update: EnergyUpdate) -> None:
        if not self._db_factory:
            return
        try:
            async with self._db_repo() as repo:
                await repo.save_energy_update(session_id, update)
        except Exception as e:
            logger.error("Failed to persist energy update: %s", e)

    async def _persist_consensus(self, consensus: ConsensusMap) -> None:
        if not self._db_factory:
            return
        try:
            async with self._db_repo() as repo:
                await repo.save_consensus(consensus)
        except Exception as e:
            logger.error("Failed to persist consensus: %s", e)

    async def _persist_session_status(self, session_id: UUID) -> None:
        if not self._db_factory:
            return
        session = self.sessions.get(session_id)
        if not session:
            return
        try:
            async with self._db_repo() as repo:
                await repo.update_session_status(session_id, session.status, session.phase)
        except Exception as e:
            logger.error("Failed to persist session status: %s", e)

    async def load_historical_sessions(self, limit: int = 50) -> List[DeliberationSession]:
        """Load past sessions from the database."""
        if not self._db_factory:
            return []
        try:
            async with self._db_repo() as repo:
                return await repo.list_sessions(limit=limit)
        except Exception as e:
            logger.error("Failed to load sessions: %s", e)
            return []

    async def load_session_data(self, session_id: UUID) -> Optional[dict]:
        """Load full session data from the database (posts, energy, consensus)."""
        if not self._db_factory:
            return None
        try:
            async with self._db_repo() as repo:
                session = await repo.get_session(session_id)
                if not session:
                    return None
                posts = await repo.get_posts(session_id)
                energy = await repo.get_energy_history(session_id)
                consensus = await repo.get_consensus(session_id)
                return {
                    "session": session,
                    "posts": posts,
                    "energy_history": energy,
                    "consensus": consensus,
                }
        except Exception as e:
            logger.error("Failed to load session data: %s", e)
            return None

    def _create_llm(self, mode: str, seed: int, model: Optional[str]):
        if mode == "mock":
            return MockLLM(behavior=MockBehavior.MIXED, seed=seed)
        from colloquip.llm.anthropic import AnthropicLLM

        return AnthropicLLM(model=model or "claude-opus-4-6")

    def _create_agents_from_community(
        self,
        llm,
        community_name: Optional[str],
        platform_manager: Optional[Any],
    ) -> Dict[str, BaseDeliberationAgent]:
        """Create agents from community members, falling back to defaults."""
        if community_name and platform_manager:
            sub = platform_manager.get_subreddit_by_name(community_name)
            if sub:
                members = platform_manager.get_subreddit_members(sub["id"])
                if members:
                    agents: Dict[str, BaseDeliberationAgent] = {}
                    for member in members:
                        agent_uuid = UUID(member["agent_id"])
                        identity = platform_manager.registry.get_agent(agent_uuid)
                        if not identity:
                            continue
                        # Convert BaseAgentIdentity -> AgentConfig
                        phase_mandates = {}
                        for k, v in identity.phase_mandates.items():
                            try:
                                phase_mandates[Phase(k)] = v
                            except ValueError:
                                pass
                        config = AgentConfig(
                            agent_id=identity.agent_type,
                            display_name=identity.display_name,
                            persona_prompt=identity.persona_prompt,
                            phase_mandates=phase_mandates,
                            domain_keywords=identity.domain_keywords,
                            knowledge_scope=identity.knowledge_scope,
                            evaluation_criteria=identity.evaluation_criteria,
                            is_red_team=identity.is_red_team,
                        )
                        agents[config.agent_id] = BaseDeliberationAgent(
                            config=config, llm=llm, phase_max_tokens=self._phase_max_tokens
                        )
                    if agents:
                        logger.info(
                            "Created %d agents from community '%s'",
                            len(agents),
                            community_name,
                        )
                        return agents
        # Fall back to hardcoded defaults
        return self._create_default_agents(llm)

    def _create_default_agents(self, llm) -> Dict[str, BaseDeliberationAgent]:
        from colloquip.cli import create_default_agents

        return create_default_agents(llm, phase_max_tokens=self._phase_max_tokens)

    async def _extract_memory(self, session_id: UUID, consensus: ConsensusMap) -> None:
        """Extract and store a synthesis memory after deliberation completes."""
        ctx = self._session_context.get(session_id, {})
        memory_store = ctx.get("memory_store")
        subreddit_id = ctx.get("subreddit_id")
        subreddit_name = ctx.get("subreddit_name", "")
        if not memory_store or not subreddit_id:
            return

        session = self.sessions.get(session_id)
        if not session:
            return

        try:
            from colloquip.embeddings.mock import MockEmbeddingProvider
            from colloquip.memory.extractor import SynthesisMemoryExtractor
            from colloquip.models import Synthesis

            posts = self.posts.get(session_id, [])
            agent_ids = sorted({p.agent_id for p in posts})

            # Build a Synthesis object from consensus + posts
            sections = {
                "executive_summary": consensus.summary,
                "key_findings": "\n".join(f"- {a}" for a in consensus.agreements),
                "disagreements": "\n".join(f"- {d}" for d in consensus.disagreements),
                "minority_positions": "\n".join(f"- {m}" for m in consensus.minority_positions),
            }
            synthesis = Synthesis(
                thread_id=session_id,
                template_type="assessment",
                sections=sections,
                metadata={"agents_involved": agent_ids},
            )

            extractor = SynthesisMemoryExtractor(MockEmbeddingProvider())
            memory = await extractor.extract(
                synthesis=synthesis,
                topic=session.hypothesis,
                subreddit_id=UUID(subreddit_id),
                subreddit_name=subreddit_name,
                agents_involved=agent_ids,
            )
            await memory_store.save(memory)
            logger.info("Extracted and stored memory %s for session %s", memory.id, session_id)
        except Exception as e:
            logger.error("Failed to extract memory for session %s: %s", session_id, e)


def create_session_manager() -> SessionManager:
    """Factory for the global session manager."""
    return SessionManager()

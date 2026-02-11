"""FastAPI application factory and session management."""

import asyncio
import logging
from typing import Callable, Dict, List, Optional
from uuid import UUID

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.config import EnergyConfig, ObserverConfig
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    HumanIntervention,
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
        # Optional database factory
        self._db_factory = db_session_factory

    def create_session(
        self,
        hypothesis: str,
        mode: str = "mock",
        seed: int = 42,
        model: Optional[str] = None,
        max_turns: int = 30,
    ) -> DeliberationSession:
        """Create a new deliberation session."""
        session = DeliberationSession(hypothesis=hypothesis)
        self.sessions[session.id] = session
        self.posts[session.id] = []
        self.energy_history[session.id] = []
        self.events[session.id] = []
        self.subscribers[session.id] = []
        self._session_locks[session.id] = asyncio.Lock()

        # Create engine components
        llm = self._create_llm(mode, seed, model)
        agents = self._create_agents(llm)
        num_agents = len(agents)

        energy_config = EnergyConfig()
        energy_calc = EnergyCalculator(config=energy_config, num_agents=num_agents)
        observer = ObserverAgent(energy_calculator=energy_calc, num_agents=num_agents)

        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=observer,
            energy_calculator=energy_calc,
            llm=llm,
            max_turns=max_turns,
            min_posts=12,
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

        # Set status BEFORE creating the task to prevent race conditions
        session.status = SessionStatus.RUNNING

        task = asyncio.create_task(self._run_deliberation(session_id))
        self._running_tasks[session_id] = task

    async def _run_deliberation(self, session_id: UUID):
        """Internal deliberation runner that broadcasts events."""
        session = self.sessions.get(session_id)
        try:
            engine = self.engines[session_id]
            posts = self.posts[session_id]
            lock = self._session_locks.get(session_id)

            async for event in engine.run_deliberation(session, session.hypothesis):
                if isinstance(event, Post):
                    if lock:
                        async with lock:
                            posts.append(event)
                    else:
                        posts.append(event)
                    await self._broadcast(session_id, {
                        "type": "post",
                        "data": event.model_dump(mode="json"),
                    })
                    await self._persist_post(event)
                elif isinstance(event, PhaseSignal):
                    await self._broadcast(session_id, {
                        "type": "phase_change",
                        "data": event.model_dump(mode="json"),
                    })
                elif isinstance(event, EnergyUpdate):
                    # Store float for engine use; broadcast full dict for frontend
                    self.energy_history[session_id].append(event.energy)
                    await self._broadcast(session_id, {
                        "type": "energy_update",
                        "data": event.model_dump(mode="json"),
                    })
                    await self._persist_energy(session_id, event)
                elif isinstance(event, ConsensusMap):
                    await self._broadcast(session_id, {
                        "type": "session_complete",
                        "data": event.model_dump(mode="json"),
                    })
                    await self._persist_consensus(event)

            await self._broadcast(session_id, {"type": "done", "data": None})
            await self._persist_session_status(session_id)
        except asyncio.CancelledError:
            logger.info("Deliberation cancelled for session %s", session_id)
            if session:
                session.status = SessionStatus.PAUSED
            await self._persist_session_status(session_id)
        except Exception as e:
            logger.error("Deliberation error for session %s: %s", session_id, e)
            if session:
                session.status = SessionStatus.COMPLETED
            await self._broadcast(session_id, {
                "type": "error",
                "data": {"message": str(e)},
            })
            await self._persist_session_status(session_id)
        finally:
            self._running_tasks.pop(session_id, None)

    async def intervene(
        self, session_id: UUID, intervention: HumanIntervention
    ) -> list:
        """Handle human intervention in an active session."""
        session = self.sessions.get(session_id)
        engine = self.engines.get(session_id)
        if not session or not engine:
            raise ValueError(f"Session {session_id} not found")

        if session.status != SessionStatus.RUNNING:
            raise ValueError(
                f"Session {session_id} is not running (status: {session.status.value})"
            )

        lock = self._session_locks.get(session_id)
        if lock:
            async with lock:
                posts = self.posts[session_id]
                energy_history = self.energy_history[session_id]
                result_posts = await engine.handle_intervention(
                    session, intervention, posts, energy_history
                )
        else:
            posts = self.posts[session_id]
            energy_history = self.energy_history[session_id]
            result_posts = await engine.handle_intervention(
                session, intervention, posts, energy_history
            )

        for post in result_posts:
            await self._broadcast(session_id, {
                "type": "post",
                "data": post.model_dump(mode="json"),
            })
            await self._persist_post(post)
        return result_posts

    # ---- Database persistence (optional) ----

    async def persist_session(self, session: DeliberationSession) -> None:
        """Persist a session to the database (if configured)."""
        if not self._db_factory:
            return
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                await repo.save_session(session)
                await repo.commit()
        except Exception as e:
            logger.error("Failed to persist session: %s", e)

    async def _persist_post(self, post: Post) -> None:
        if not self._db_factory:
            return
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                await repo.save_post(post)
                await repo.commit()
        except Exception as e:
            logger.error("Failed to persist post: %s", e)

    async def _persist_energy(self, session_id: UUID, update: EnergyUpdate) -> None:
        if not self._db_factory:
            return
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                await repo.save_energy_update(session_id, update)
                await repo.commit()
        except Exception as e:
            logger.error("Failed to persist energy update: %s", e)

    async def _persist_consensus(self, consensus: ConsensusMap) -> None:
        if not self._db_factory:
            return
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                await repo.save_consensus(consensus)
                await repo.commit()
        except Exception as e:
            logger.error("Failed to persist consensus: %s", e)

    async def _persist_session_status(self, session_id: UUID) -> None:
        if not self._db_factory:
            return
        session = self.sessions.get(session_id)
        if not session:
            return
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                await repo.update_session_status(session_id, session.status, session.phase)
                await repo.commit()
        except Exception as e:
            logger.error("Failed to persist session status: %s", e)

    async def load_historical_sessions(self, limit: int = 50) -> List[DeliberationSession]:
        """Load past sessions from the database."""
        if not self._db_factory:
            return []
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
                return await repo.list_sessions(limit=limit)
        except Exception as e:
            logger.error("Failed to load sessions: %s", e)
            return []

    async def load_session_data(self, session_id: UUID) -> Optional[dict]:
        """Load full session data from the database (posts, energy, consensus)."""
        if not self._db_factory:
            return None
        try:
            from colloquip.db.repository import SessionRepository
            async with self._db_factory() as db:
                repo = SessionRepository(db)
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
        return AnthropicLLM(model=model or "claude-sonnet-4-5-20250929")

    def _create_agents(self, llm) -> Dict[str, BaseDeliberationAgent]:
        from colloquip.cli import create_default_agents
        return create_default_agents(llm)


def create_session_manager() -> SessionManager:
    """Factory for the global session manager."""
    return SessionManager()

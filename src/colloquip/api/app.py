"""FastAPI application factory and session management."""

import asyncio
import logging
from typing import Dict, Optional
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
    """Manages active deliberation sessions and their state."""

    def __init__(self):
        self.sessions: Dict[UUID, DeliberationSession] = {}
        self.posts: Dict[UUID, list] = {}
        self.energy_history: Dict[UUID, list] = {}
        self.engines: Dict[UUID, EmergentDeliberationEngine] = {}
        self.events: Dict[UUID, list] = {}
        self.subscribers: Dict[UUID, list[asyncio.Queue]] = {}
        self._running_tasks: Dict[UUID, asyncio.Task] = {}

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

        # Create engine components
        llm = self._create_llm(mode, seed, model)
        agents = self._create_agents(llm)
        num_agents = len(agents)

        energy_config = EnergyConfig()
        energy_calc = EnergyCalculator(config=energy_config)
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
        """Return a snapshot copy of the energy history."""
        return list(self.energy_history.get(session_id, []))

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
        try:
            session = self.sessions[session_id]
            engine = self.engines[session_id]
            posts = self.posts[session_id]

            async for event in engine.run_deliberation(session, session.hypothesis):
                if isinstance(event, Post):
                    posts.append(event)
                    await self._broadcast(session_id, {
                        "type": "post",
                        "data": event.model_dump(mode="json"),
                    })
                elif isinstance(event, PhaseSignal):
                    await self._broadcast(session_id, {
                        "type": "phase_change",
                        "data": event.model_dump(mode="json"),
                    })
                elif isinstance(event, EnergyUpdate):
                    self.energy_history[session_id].append(event.energy)
                    await self._broadcast(session_id, {
                        "type": "energy_update",
                        "data": event.model_dump(mode="json"),
                    })
                elif isinstance(event, ConsensusMap):
                    await self._broadcast(session_id, {
                        "type": "session_complete",
                        "data": event.model_dump(mode="json"),
                    })

            await self._broadcast(session_id, {"type": "done", "data": None})
        except asyncio.CancelledError:
            logger.info("Deliberation cancelled for session %s", session_id)
            session = self.sessions.get(session_id)
            if session:
                session.status = SessionStatus.PAUSED
        except Exception as e:
            logger.error("Deliberation error for session %s: %s", session_id, e)
            await self._broadcast(session_id, {
                "type": "error",
                "data": {"message": str(e)},
            })
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
        return result_posts

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

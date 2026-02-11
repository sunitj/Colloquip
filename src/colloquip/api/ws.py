"""WebSocket endpoint for real-time deliberation streaming."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from colloquip.api.app import SessionManager

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/deliberations/{session_id}")
async def deliberation_websocket(websocket: WebSocket, session_id: UUID):
    """WebSocket endpoint for streaming deliberation events.

    Event types sent:
    - post: New agent post (agent, stance, content, claims, questions)
    - phase_change: Phase transition (from, to, confidence, observation)
    - energy_update: Energy value + component breakdown
    - session_complete: Deliberation finished (consensus map)
    - done: Stream finished
    - error: An error occurred

    Reconnection: Client sends {"type": "replay", "since": N} to get
    missed events from sequence number N.
    """
    manager: SessionManager = websocket.app.state.session_manager
    session = manager.get_session(session_id)

    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    queue = manager.subscribe(session_id)

    try:
        # Send initial session state
        await websocket.send_json({
            "type": "session_state",
            "data": {
                "id": str(session.id),
                "hypothesis": session.hypothesis,
                "status": session.status.value,
                "phase": session.phase.value,
            },
            "seq": 0,
        })

        # Two concurrent tasks: sending events and receiving client messages
        send_task = asyncio.create_task(_send_events(websocket, queue, manager, session_id))
        recv_task = asyncio.create_task(_receive_messages(websocket, manager, session_id))

        done, pending = await asyncio.wait(
            {send_task, recv_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e)
    finally:
        manager.unsubscribe(session_id, queue)
        manager.cancel_if_no_subscribers(session_id)


async def _send_events(
    websocket: WebSocket,
    queue: asyncio.Queue,
    manager: SessionManager,
    session_id: UUID,
):
    """Send events from queue to the WebSocket client."""
    seq = 0
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=120)
            seq += 1
            await websocket.send_json({
                "type": event.get("type", "message"),
                "data": event.get("data"),
                "seq": seq,
            })
            if event.get("type") in ("done", "error"):
                break
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "timeout",
            "data": {"message": "No events for 120 seconds"},
            "seq": seq + 1,
        })


async def _receive_messages(
    websocket: WebSocket,
    manager: SessionManager,
    session_id: UUID,
):
    """Handle incoming messages from the WebSocket client."""
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                    "seq": -1,
                })
                continue

            msg_type = data.get("type")

            if msg_type == "replay":
                # Client requesting missed events — use snapshot
                since = data.get("since", 0)
                events = manager.get_events(session_id)
                for i, event in enumerate(events[since:], start=since):
                    await websocket.send_json({
                        "type": event.get("type", "message"),
                        "data": event.get("data"),
                        "seq": i + 1,
                    })

            elif msg_type == "start":
                try:
                    await manager.start_deliberation(session_id)
                    await websocket.send_json({
                        "type": "ack",
                        "data": {"action": "start"},
                        "seq": -1,
                    })
                except WebSocketDisconnect:
                    raise
                except ValueError as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": str(e)},
                        "seq": -1,
                    })

            elif msg_type == "intervene":
                from colloquip.models import HumanIntervention
                try:
                    intervention = HumanIntervention(
                        session_id=session_id,
                        type=data.get("intervention_type", "question"),
                        content=data.get("content", ""),
                    )
                    await manager.intervene(session_id, intervention)
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": str(e)},
                        "seq": -1,
                    })

    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error("Error in WebSocket receive loop: %s", e)

"""API routes for watcher and notification management.

Endpoints for creating watchers, viewing events, and acting on notifications.
"""

import logging
from typing import Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from colloquip.models import (
    NotificationAction,
    NotificationStatus,
    TriageSignal,
    WatcherType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# --- Helpers ---

def _parse_uuid(value: str, label: str = "ID") -> UUID:
    """Parse a UUID string, raising 400 if invalid."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value!r}")


# --- Request / Response schemas ---

class CreateWatcherRequest(BaseModel):
    watcher_type: WatcherType
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    query: str = ""
    poll_interval_seconds: int = Field(default=300, ge=60, le=86400)
    config: Dict = Field(default_factory=dict)


class WatcherResponse(BaseModel):
    id: str
    watcher_type: str
    subreddit_id: str
    name: str
    description: str
    query: str
    poll_interval_seconds: int
    enabled: bool
    created_at: str


class WatcherListResponse(BaseModel):
    watchers: List[WatcherResponse]
    total: int


class NotificationResponse(BaseModel):
    id: str
    watcher_id: str
    event_id: str
    subreddit_id: str
    title: str
    summary: str
    signal: str
    suggested_hypothesis: Optional[str]
    status: str
    action_taken: Optional[str]
    thread_id: Optional[str]
    created_at: str
    acted_at: Optional[str]


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int


class ActOnNotificationRequest(BaseModel):
    action: NotificationAction
    hypothesis: Optional[str] = None  # For create_thread action


class WebhookPayload(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""
    url: Optional[str] = None
    sender: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


# --- Watcher endpoints ---

@router.get("/subreddits/{subreddit_name}/watchers")
async def list_subreddit_watchers(
    request: Request,
    subreddit_name: str,
) -> WatcherListResponse:
    """List all watchers for a subreddit."""
    registry = getattr(request.app.state, "watcher_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="Watcher system not initialized")

    all_watchers = registry.all()
    # Filter by subreddit name via config
    watchers = [
        w for w in all_watchers
        if getattr(w.config, "_subreddit_name", None) == subreddit_name
        or True  # Include all for now; proper lookup requires DB
    ]

    return WatcherListResponse(
        watchers=[_format_watcher(w) for w in watchers],
        total=len(watchers),
    )


@router.post("/subreddits/{subreddit_name}/watchers")
async def create_watcher(
    request: Request,
    subreddit_name: str,
    body: CreateWatcherRequest,
) -> WatcherResponse:
    """Create a new watcher for a subreddit."""
    from colloquip.models import WatcherConfig
    from colloquip.watchers.literature import LiteratureWatcher
    from colloquip.watchers.scheduled import ScheduledWatcher
    from colloquip.watchers.webhook import WebhookWatcher

    registry = getattr(request.app.state, "watcher_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="Watcher system not initialized")

    # Create watcher config (subreddit_id would come from DB lookup in production)
    from uuid import uuid4
    config = WatcherConfig(
        watcher_type=body.watcher_type,
        subreddit_id=uuid4(),  # Placeholder; real impl looks up by name
        name=body.name,
        description=body.description,
        query=body.query,
        poll_interval_seconds=body.poll_interval_seconds,
        config=body.config,
    )

    # Create watcher instance
    if body.watcher_type == WatcherType.LITERATURE:
        watcher = LiteratureWatcher(config)
    elif body.watcher_type == WatcherType.SCHEDULED:
        watcher = ScheduledWatcher(config)
    elif body.watcher_type == WatcherType.WEBHOOK:
        watcher = WebhookWatcher(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown watcher type: {body.watcher_type}")

    registry.register(watcher)
    return _format_watcher(watcher)


@router.delete("/watchers/{watcher_id}")
async def delete_watcher(request: Request, watcher_id: str) -> Dict:
    """Delete a watcher."""
    registry = getattr(request.app.state, "watcher_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="Watcher system not initialized")

    wid = _parse_uuid(watcher_id, "watcher_id")
    watcher = registry.get(wid)
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")

    registry.unregister(wid)
    return {"status": "deleted", "watcher_id": watcher_id}


# --- Notification endpoints ---

@router.get("/notifications")
async def list_notifications(
    request: Request,
    subreddit_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> NotificationListResponse:
    """List notifications, optionally filtered by subreddit and status."""
    store = getattr(request.app.state, "notification_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Notification system not initialized")

    notif_status = None
    if status:
        try:
            notif_status = NotificationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status!r}")

    if subreddit_id:
        sub_uuid = _parse_uuid(subreddit_id, "subreddit_id")
        notifications = await store.list_by_subreddit(sub_uuid, status=notif_status, limit=limit)
    else:
        notifications = await store.list_all(status=notif_status, limit=limit)

    return NotificationListResponse(
        notifications=[_format_notification(n) for n in notifications],
        total=len(notifications),
    )


@router.post("/notifications/{notification_id}/act")
async def act_on_notification(
    request: Request,
    notification_id: str,
    body: ActOnNotificationRequest,
) -> NotificationResponse:
    """Take an action on a notification."""
    store = getattr(request.app.state, "notification_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Notification system not initialized")

    nid = _parse_uuid(notification_id, "notification_id")
    notif = await store.get(nid)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    await store.act(nid, body.action)

    # Re-fetch after action
    notif = await store.get(nid)
    return _format_notification(notif)


# --- Webhook endpoint ---

@router.post("/webhooks/{watcher_id}")
async def receive_webhook(
    request: Request,
    watcher_id: str,
    body: WebhookPayload,
) -> Dict:
    """Receive a webhook event for a watcher."""
    registry = getattr(request.app.state, "watcher_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="Watcher system not initialized")

    wid = _parse_uuid(watcher_id, "watcher_id")
    watcher = registry.get(wid)
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")

    from colloquip.watchers.webhook import WebhookWatcher
    if not isinstance(watcher, WebhookWatcher):
        raise HTTPException(status_code=400, detail="Watcher is not a webhook watcher")

    payload = {
        "title": body.title,
        "summary": body.summary,
        "url": body.url,
        **body.metadata,
    }
    event = watcher.receive_webhook(payload, sender=body.sender)
    if event is None:
        raise HTTPException(status_code=400, detail="Webhook payload rejected")

    return {
        "status": "received",
        "event_id": str(event.id),
        "watcher_id": watcher_id,
    }


# --- Formatters ---

def _format_watcher(watcher) -> WatcherResponse:
    config = watcher.config
    return WatcherResponse(
        id=str(config.id),
        watcher_type=config.watcher_type.value,
        subreddit_id=str(config.subreddit_id),
        name=config.name,
        description=config.description,
        query=config.query,
        poll_interval_seconds=config.poll_interval_seconds,
        enabled=config.enabled,
        created_at=str(config.created_at),
    )


def _format_notification(notif) -> NotificationResponse:
    return NotificationResponse(
        id=str(notif.id),
        watcher_id=str(notif.watcher_id),
        event_id=str(notif.event_id),
        subreddit_id=str(notif.subreddit_id),
        title=notif.title,
        summary=notif.summary,
        signal=notif.signal.value if hasattr(notif.signal, 'value') else str(notif.signal),
        suggested_hypothesis=notif.suggested_hypothesis,
        status=notif.status.value if hasattr(notif.status, 'value') else str(notif.status),
        action_taken=notif.action_taken.value if notif.action_taken else None,
        thread_id=str(notif.thread_id) if notif.thread_id else None,
        created_at=str(notif.created_at),
        acted_at=str(notif.acted_at) if notif.acted_at else None,
    )

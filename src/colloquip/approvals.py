"""Paperclip-style human-in-loop approval queue.

An :class:`ApprovalQueue` collects pending high-impact actions — watcher
auto-thread requests when policy thresholds aren't yet earned, budget
overrides from agents, tool calls that require human confirmation, etc. —
and exposes list/approve/deny operations.

Kept intentionally simple:

- In-memory state (optionally mirrored to DB by the caller via
  :class:`colloquip.db.repository.SessionRepository.save_approval_request`).
- Subscriber callbacks for WebSocket broadcast.
- No automatic expiration yet — the schema records ``ttl_seconds`` for future
  sweep jobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from uuid import UUID

from colloquip.models import ApprovalRequest, ApprovalRequestType, ApprovalStatus

ApprovalCallback = Callable[[str, ApprovalRequest], None]


class ApprovalQueue:
    """In-memory approval queue with optional subscribers."""

    def __init__(self):
        self._requests: Dict[UUID, ApprovalRequest] = {}
        self._subscribers: List[ApprovalCallback] = []

    # ---- Mutation ----

    def enqueue(
        self,
        subreddit_id: UUID,
        request_type: ApprovalRequestType,
        initiator: str = "",
        target_ref: Optional[str] = None,
        payload: Optional[dict] = None,
        reason: str = "",
        estimated_cost_usd: float = 0.0,
        ttl_seconds: Optional[int] = None,
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            subreddit_id=subreddit_id,
            request_type=request_type,
            initiator=initiator,
            target_ref=target_ref,
            payload=payload or {},
            reason=reason,
            estimated_cost_usd=estimated_cost_usd,
            ttl_seconds=ttl_seconds,
        )
        self._requests[req.id] = req
        self._notify("created", req)
        return req

    def resolve(
        self,
        request_id: UUID,
        status: ApprovalStatus,
        decided_by: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        req = self._requests.get(request_id)
        if not req:
            return None
        req.status = status
        req.decided_at = datetime.now(timezone.utc)
        req.decided_by = decided_by
        self._notify("resolved", req)
        return req

    # ---- Query ----

    def get(self, request_id: UUID) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def list_for_subreddit(
        self,
        subreddit_id: str,
        status: Optional[ApprovalStatus] = None,
    ) -> List[ApprovalRequest]:
        sid_str = str(subreddit_id)
        results = [req for req in self._requests.values() if str(req.subreddit_id) == sid_str]
        if status is not None:
            results = [r for r in results if r.status == status]
        results.sort(key=lambda r: r.requested_at, reverse=True)
        return results

    def pending_for_subreddit(self, subreddit_id: str) -> List[ApprovalRequest]:
        return self.list_for_subreddit(subreddit_id, status=ApprovalStatus.PENDING)

    # ---- Subscribers (for WS broadcast) ----

    def subscribe(self, callback: ApprovalCallback) -> None:
        self._subscribers.append(callback)

    def _notify(self, event: str, req: ApprovalRequest) -> None:
        for cb in list(self._subscribers):
            try:
                cb(event, req)
            except Exception:  # noqa: BLE001 — subscribers must not break the queue
                continue

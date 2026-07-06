"""Phase 6 approval queue tests.

Drives the implementation of colloquip.approvals.ApprovalQueue — an in-memory
Paperclip-style approval queue that optionally persists to DB via the
repository. The existing AutoDeliberationPolicy can wrap it so that denied
watcher auto-threads are routed for human approval instead of silently dropped.
"""

from uuid import uuid4

from colloquip.approvals import ApprovalQueue
from colloquip.models import ApprovalRequestType, ApprovalStatus


class TestApprovalQueueInMemory:
    def test_empty_queue_starts_empty(self):
        queue = ApprovalQueue()
        assert queue.pending_for_subreddit(str(uuid4())) == []

    def test_enqueue_creates_pending_request(self):
        queue = ApprovalQueue()
        subreddit_id = uuid4()
        req = queue.enqueue(
            subreddit_id=subreddit_id,
            request_type=ApprovalRequestType.BUDGET_OVERRIDE,
            initiator="agent:alpha",
            reason="Needs more tokens",
            estimated_cost_usd=0.75,
            payload={"extra": 0.5},
        )
        assert req.status == ApprovalStatus.PENDING
        assert req.request_type == ApprovalRequestType.BUDGET_OVERRIDE
        assert req.initiator == "agent:alpha"
        assert req.payload == {"extra": 0.5}
        pending = queue.pending_for_subreddit(str(subreddit_id))
        assert len(pending) == 1
        assert pending[0].id == req.id

    def test_approve_and_deny_update_status(self):
        queue = ApprovalQueue()
        subreddit_id = uuid4()
        req_a = queue.enqueue(
            subreddit_id=subreddit_id,
            request_type=ApprovalRequestType.THREAD_SPAWN,
            initiator="watcher:1",
        )
        req_b = queue.enqueue(
            subreddit_id=subreddit_id,
            request_type=ApprovalRequestType.TOOL_CALL,
            initiator="agent:beta",
        )
        queue.resolve(req_a.id, ApprovalStatus.APPROVED, decided_by="user:admin")
        queue.resolve(req_b.id, ApprovalStatus.DENIED, decided_by="user:admin")

        loaded_a = queue.get(req_a.id)
        loaded_b = queue.get(req_b.id)
        assert loaded_a.status == ApprovalStatus.APPROVED
        assert loaded_b.status == ApprovalStatus.DENIED
        assert loaded_a.decided_by == "user:admin"
        assert loaded_a.decided_at is not None

        assert queue.pending_for_subreddit(str(subreddit_id)) == []
        all_reqs = queue.list_for_subreddit(str(subreddit_id))
        assert len(all_reqs) == 2

    def test_list_filters_by_status(self):
        queue = ApprovalQueue()
        subreddit_id = uuid4()
        req_a = queue.enqueue(subreddit_id=subreddit_id, request_type=ApprovalRequestType.TOOL_CALL)
        queue.enqueue(subreddit_id=subreddit_id, request_type=ApprovalRequestType.TOOL_CALL)
        queue.resolve(req_a.id, ApprovalStatus.APPROVED)

        approved = queue.list_for_subreddit(str(subreddit_id), status=ApprovalStatus.APPROVED)
        pending = queue.list_for_subreddit(str(subreddit_id), status=ApprovalStatus.PENDING)
        assert len(approved) == 1
        assert len(pending) == 1


class TestApprovalQueueCallbacks:
    def test_subscribe_callback_fires_on_enqueue_and_resolve(self):
        queue = ApprovalQueue()
        events = []
        queue.subscribe(lambda event, req: events.append((event, req.id)))
        subreddit_id = uuid4()
        req = queue.enqueue(subreddit_id=subreddit_id, request_type=ApprovalRequestType.TOOL_CALL)
        queue.resolve(req.id, ApprovalStatus.APPROVED)
        kinds = [e[0] for e in events]
        assert "created" in kinds
        assert "resolved" in kinds

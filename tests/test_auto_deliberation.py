"""Tests for auto-deliberation policy."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from colloquip.watchers.auto_deliberation import AutoDeliberationPolicy


class TestAutoDeliberationPolicy:
    @pytest.fixture
    def policy(self):
        return AutoDeliberationPolicy(
            min_events=20,
            min_useful_rate=0.70,
            max_threads_per_hour=5,
        )

    def test_not_approved(self, policy):
        watcher_id = uuid4()
        check = policy.can_auto_create(watcher_id)
        assert not check.allowed
        assert "Not approved" in check.reason

    def test_not_enough_events(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(5):
            policy.record_event(watcher_id)
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert not check.allowed
        assert "5/20 events" in check.reason

    def test_low_useful_rate(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
        # Only 5 useful out of 25 = 20%
        for _ in range(5):
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert not check.allowed
        assert "Useful rate 20%" in check.reason

    def test_all_criteria_met(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
        for _ in range(20):
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert check.allowed
        assert "All criteria met" in check.reason

    def test_rate_limit(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
            policy.record_useful_outcome(watcher_id)

        now = datetime.now(timezone.utc)
        # Record 5 auto-threads in the last hour
        for i in range(5):
            policy.record_auto_thread(
                watcher_id, now=now - timedelta(minutes=i * 5)
            )

        check = policy.can_auto_create(watcher_id, now=now)
        assert not check.allowed
        assert "Rate limit" in check.reason

    def test_rate_limit_old_threads_dont_count(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
            policy.record_useful_outcome(watcher_id)

        now = datetime.now(timezone.utc)
        # Record threads >1 hour ago
        for i in range(5):
            policy.record_auto_thread(
                watcher_id, now=now - timedelta(hours=2, minutes=i)
            )

        check = policy.can_auto_create(watcher_id, now=now)
        assert check.allowed

    def test_revoke_approval(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
            policy.record_useful_outcome(watcher_id)

        assert policy.can_auto_create(watcher_id).allowed

        policy.revoke_watcher(watcher_id)
        assert not policy.can_auto_create(watcher_id).allowed

    def test_get_stats(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(10):
            policy.record_event(watcher_id)
        for _ in range(7):
            policy.record_useful_outcome(watcher_id)

        stats = policy.get_stats(watcher_id)
        assert stats["approved"] is True
        assert stats["events_processed"] == 10
        assert stats["useful_outcomes"] == 7
        assert abs(stats["useful_rate"] - 0.7) < 0.01

    def test_check_is_truthy_when_allowed(self, policy):
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert bool(check) is True

    def test_check_is_falsy_when_denied(self, policy):
        check = policy.can_auto_create(uuid4())
        assert bool(check) is False

    def test_multiple_denial_reasons(self, policy):
        watcher_id = uuid4()
        # Not approved, not enough events, no useful outcomes
        check = policy.can_auto_create(watcher_id)
        assert len(check.reasons) >= 2

    def test_custom_thresholds(self):
        policy = AutoDeliberationPolicy(
            min_events=5,
            min_useful_rate=0.5,
            max_threads_per_hour=2,
        )
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(6):
            policy.record_event(watcher_id)
        for _ in range(4):
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert check.allowed

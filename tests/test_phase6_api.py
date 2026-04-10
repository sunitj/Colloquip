"""Phase 6 API route tests: mission + budget endpoints."""

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from colloquip.api import create_app

    app = create_app()
    return TestClient(app)


def _ensure_subreddit(client, name: str = "mission_test_sub"):
    client.post("/api/platform/init")
    resp = client.post(
        "/api/subreddits",
        json={
            "name": name,
            "display_name": "Mission Test Sub",
            "description": "For mission + budget testing",
            "thinking_type": "assessment",
            "required_expertise": ["molecular_biology"],
            "primary_domain": "drug_discovery",
            "tool_ids": [],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestSubredditMissionAPI:
    def test_get_mission_empty_initially(self, client):
        _ensure_subreddit(client, "mission_empty")
        resp = client.get("/api/subreddits/mission_empty/mission")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mission_md"] is None
        assert data["objectives"] == []
        assert data["version"] == 1

    def test_put_mission_parses_objectives(self, client):
        _ensure_subreddit(client, "mission_put")
        md = (
            "# Mission\n\n"
            "Reduce false claims in oncology deliberations.\n\n"
            "## Objective: Verify every citation\n"
            "- metric: citation_verification_rate\n"
            "- target: 0.85\n\n"
            "## Objective: Surface novel mechanisms\n"
            "- metric: novelty_avg\n"
            "- target: 0.5\n"
        )
        resp = client.put(
            "/api/subreddits/mission_put/mission",
            json={"mission_md": md},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mission_md"] == md
        assert len(data["objectives"]) == 2
        titles = {o["title"] for o in data["objectives"]}
        assert "Verify every citation" in titles
        assert "Surface novel mechanisms" in titles
        assert data["version"] == 2  # bumped from 1

        # Round-trip
        resp2 = client.get("/api/subreddits/mission_put/mission")
        assert resp2.status_code == 200
        assert resp2.json()["version"] == 2

    def test_put_mission_explicit_objectives_override(self, client):
        _ensure_subreddit(client, "mission_explicit")
        resp = client.put(
            "/api/subreddits/mission_explicit/mission",
            json={
                "mission_md": "# Mission",
                "objectives": [
                    {
                        "id": "custom-1",
                        "title": "Custom objective",
                        "metric": "custom_metric",
                        "target": 1.0,
                    }
                ],
                "regenerate_objectives": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["objectives"]) == 1
        assert data["objectives"][0]["title"] == "Custom objective"


class TestBudgetAPI:
    def test_get_budgets_initial(self, client):
        sub = _ensure_subreddit(client, "budget_initial")
        resp = client.get("/api/subreddits/budget_initial/budgets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subreddit_id"] == sub["id"]
        assert data["max_cost_per_thread_usd"] == 5.0
        assert len(data["members"]) >= 1
        for m in data["members"]:
            assert m["max_cost_per_thread_usd"] is None
            assert m["monthly_budget_usd"] is None

    def test_update_member_budget(self, client):
        sub = _ensure_subreddit(client, "budget_update")
        members_resp = client.get("/api/subreddits/budget_update/members").json()
        first_agent_id = members_resp["members"][0]["agent_id"]

        resp = client.patch(
            f"/api/subreddits/budget_update/members/{first_agent_id}/budget",
            json={"max_cost_per_thread_usd": 1.25, "monthly_budget_usd": 10.0},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["max_cost_per_thread_usd"] == 1.25
        assert payload["monthly_budget_usd"] == 10.0

        budgets = client.get("/api/subreddits/budget_update/budgets").json()
        matching = [m for m in budgets["members"] if m["agent_id"] == first_agent_id]
        assert len(matching) == 1
        assert matching[0]["max_cost_per_thread_usd"] == 1.25

    def test_unknown_subreddit_404(self, client):
        client.post("/api/platform/init")
        assert client.get("/api/subreddits/ghost/mission").status_code == 404
        assert client.get("/api/subreddits/ghost/budgets").status_code == 404


class TestApprovalQueueAPI:
    def test_enqueue_list_and_resolve(self, client):
        _ensure_subreddit(client, "approval_flow")

        # Initially empty
        resp = client.get("/api/subreddits/approval_flow/approvals")
        assert resp.status_code == 200
        assert resp.json()["approvals"] == []

        # Enqueue a budget override request
        resp = client.post(
            "/api/subreddits/approval_flow/approvals",
            json={
                "request_type": "budget_override",
                "initiator": "agent:alpha",
                "reason": "Needs more tokens",
                "estimated_cost_usd": 0.75,
                "payload": {"extra_usd": 0.5},
            },
        )
        assert resp.status_code == 200, resp.text
        created = resp.json()
        assert created["status"] == "pending"
        request_id = created["id"]

        # It shows up as pending
        pending = client.get("/api/subreddits/approval_flow/approvals?status=pending").json()[
            "approvals"
        ]
        assert len(pending) == 1
        assert pending[0]["id"] == request_id

        # Approve it
        resolve_resp = client.post(
            f"/api/approvals/{request_id}/resolve",
            json={"status": "approved", "decided_by": "user:admin"},
        )
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["status"] == "approved"
        assert resolved["decided_by"] == "user:admin"

        # No longer pending
        pending_after = client.get("/api/subreddits/approval_flow/approvals?status=pending").json()[
            "approvals"
        ]
        assert pending_after == []
        all_after = client.get("/api/subreddits/approval_flow/approvals").json()["approvals"]
        assert len(all_after) == 1

    def test_resolve_unknown_request_404(self, client):
        client.post("/api/platform/init")
        bogus_id = "11111111-1111-1111-1111-111111111111"
        resp = client.post(
            f"/api/approvals/{bogus_id}/resolve",
            json={"status": "approved"},
        )
        assert resp.status_code == 404

    def test_bad_status_query_400(self, client):
        _ensure_subreddit(client, "approval_bad_status")
        resp = client.get("/api/subreddits/approval_bad_status/approvals?status=bogus")
        assert resp.status_code == 400

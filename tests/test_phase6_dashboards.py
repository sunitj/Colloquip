"""Phase 6 dashboards backend tests: org chart + goal progress measurement.

Drives the implementation of:
- PlatformManager.get_subreddit_org_chart — builds a graph of agents with
  edges derived from DBPost.triggered_by (and optional reports_to overrides)
- colloquip.subreddit_mission.measure_objectives — scores each objective
  against observed metrics aggregated from recent posts/synthesis.
"""

from uuid import uuid4

import pytest

from colloquip.models import (
    MissionObjective,
    Phase,
    Post,
)
from colloquip.subreddit_mission import measure_objectives


class TestMeasureObjectives:
    def _mk_post(self, agent_id: str, novelty: float, claims=None, citations=None) -> Post:
        from colloquip.models import AgentStance

        return Post(
            session_id=uuid4(),
            agent_id=agent_id,
            content="",
            stance=AgentStance.NEUTRAL,
            novelty_score=novelty,
            phase=Phase.EXPLORE,
            key_claims=claims or [],
            citations=citations or [],
        )

    def test_empty_objectives_returns_empty(self):
        assert measure_objectives([], []) == []

    def test_novelty_avg_objective(self):
        posts = [
            self._mk_post("alpha", 0.5),
            self._mk_post("beta", 0.7),
            self._mk_post("gamma", 0.3),
        ]
        objective = MissionObjective(
            id="obj-1", title="Improve novelty", metric="novelty_avg", target=0.4
        )
        progress = measure_objectives([objective], posts)
        assert len(progress) == 1
        p = progress[0]
        assert p.objective_id == "obj-1"
        assert p.metric == "novelty_avg"
        assert p.measured_value is not None
        assert 0.49 <= p.measured_value <= 0.51  # avg of 0.5, 0.7, 0.3 = 0.5
        assert p.sample_size == 3
        assert p.status == "met"

    def test_novelty_avg_below_target_is_not_met(self):
        posts = [self._mk_post("alpha", 0.1), self._mk_post("beta", 0.2)]
        objective = MissionObjective(
            id="obj-1", title="Improve novelty", metric="novelty_avg", target=0.5
        )
        progress = measure_objectives([objective], posts)
        assert progress[0].status == "not_met"
        assert progress[0].measured_value == pytest.approx(0.15)

    def test_objective_without_metric_is_qualitative(self):
        posts = [self._mk_post("alpha", 0.5)]
        objective = MissionObjective(id="obj-1", title="Build trust")
        progress = measure_objectives([objective], posts)
        assert len(progress) == 1
        assert progress[0].qualitative is True
        assert progress[0].measured_value is None
        assert progress[0].status == "open"

    def test_citation_density_metric(self):
        from colloquip.models import Citation

        cite = Citation(document_id="1", title="Study", excerpt="", relevance=0.9)
        posts = [
            self._mk_post("alpha", 0.5, citations=[cite, cite]),
            self._mk_post("beta", 0.5, citations=[cite]),
        ]
        objective = MissionObjective(
            id="obj-1",
            title="More citations",
            metric="citation_density",
            target=1.0,
        )
        progress = measure_objectives([objective], posts)
        assert progress[0].measured_value == pytest.approx(1.5)  # 3 citations / 2 posts
        assert progress[0].status == "met"

    def test_unknown_metric_is_qualitative(self):
        posts = [self._mk_post("alpha", 0.5)]
        objective = MissionObjective(
            id="obj-1", title="Unknown metric", metric="bogus_metric", target=0.5
        )
        progress = measure_objectives([objective], posts)
        assert progress[0].qualitative is True


class TestOrgChart:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from colloquip.api import create_app

        app = create_app()
        return TestClient(app)

    def _make_sub(self, client, name: str = "orgchart_sub"):
        client.post("/api/platform/init")
        resp = client.post(
            "/api/subreddits",
            json={
                "name": name,
                "display_name": "Org chart sub",
                "description": "Test",
                "thinking_type": "assessment",
                "required_expertise": ["molecular_biology"],
                "primary_domain": "drug_discovery",
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_org_chart_has_nodes_for_each_member(self, client):
        self._make_sub(client, "orgchart_nodes")
        resp = client.get("/api/subreddits/orgchart_nodes/org-chart")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 1
        for node in data["nodes"]:
            assert "agent_id" in node
            assert "display_name" in node
            assert "role" in node

    def test_org_chart_404_unknown_subreddit(self, client):
        client.post("/api/platform/init")
        resp = client.get("/api/subreddits/ghost/org-chart")
        assert resp.status_code == 404


class TestGoalProgressRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from colloquip.api import create_app

        app = create_app()
        return TestClient(app)

    def test_empty_progress_when_no_mission(self, client):
        client.post("/api/platform/init")
        resp = client.post(
            "/api/subreddits",
            json={
                "name": "goalprog_empty",
                "display_name": "Goal progress empty",
                "description": "",
                "thinking_type": "assessment",
                "required_expertise": ["molecular_biology"],
                "primary_domain": "drug_discovery",
            },
        )
        assert resp.status_code == 200
        resp = client.get("/api/subreddits/goalprog_empty/mission/progress")
        assert resp.status_code == 200
        assert resp.json() == {"objectives": []}

    def test_progress_after_mission_set(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "goalprog_set",
                "display_name": "Goal progress set",
                "description": "",
                "thinking_type": "assessment",
                "required_expertise": ["molecular_biology"],
                "primary_domain": "drug_discovery",
            },
        )
        client.put(
            "/api/subreddits/goalprog_set/mission",
            json={
                "mission_md": (
                    "## Objective: Improve novelty\n- metric: novelty_avg\n- target: 0.4\n"
                    "## Objective: Qualitative goal\nSome prose.\n"
                )
            },
        )
        resp = client.get("/api/subreddits/goalprog_set/mission/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "objectives" in data
        assert len(data["objectives"]) == 2
        titles = {o["title"] for o in data["objectives"]}
        assert "Improve novelty" in titles
        assert "Qualitative goal" in titles

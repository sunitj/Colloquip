"""Tests for job API routes."""

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient

from colloquip.api import create_app
from colloquip.jobs.executor import MockNextflowExecutor
from colloquip.jobs.manager import JobManager
from colloquip.jobs.pipeline_builder import PipelineBuilder
from colloquip.models import (
    ChannelSpec,
    NextflowProcess,
    ParamSpec,
    ResourceSpec,
)


def _make_app_with_manager():
    """Create a FastAPI app with a job manager configured."""
    app = create_app()

    proc = NextflowProcess(
        process_id="fold",
        name="Fold",
        description="Predict structure",
        category="structure_prediction",
        input_channels=[ChannelSpec(name="fasta", data_type="fasta", description="Input")],
        output_channels=[ChannelSpec(name="structure", data_type="pdb", description="Output")],
        parameters=[ParamSpec(name="model", param_type="string", description="Model")],
        container="test:latest",
        resource_requirements=ResourceSpec(),
    )
    builder = PipelineBuilder()
    builder.set_catalog([proc])
    executor = MockNextflowExecutor()
    manager = JobManager(
        executor=executor,
        pipeline_builder=builder,
        work_dir=tempfile.mkdtemp(),
    )
    app.state.job_manager = manager
    return app, manager


# =========================================================================
# NF Process Routes
# =========================================================================


class TestNFProcessRoutes:
    def test_list_processes_yaml_fallback(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/nf-processes")
        assert resp.status_code == 200
        assert "processes" in resp.json()

    def test_get_process_not_found(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/nf-processes/nonexistent")
        assert resp.status_code == 404

    def test_list_processes_with_manager(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.get("/api/nf-processes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["processes"]) == 1

    def test_get_process_with_manager(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.get("/api/nf-processes/fold")
        assert resp.status_code == 200
        assert resp.json()["process_id"] == "fold"


# =========================================================================
# Job Routes
# =========================================================================


class TestJobRoutes:
    def test_list_jobs_no_manager(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/jobs")
        assert resp.status_code == 503

    def test_list_jobs_empty(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert resp.json()["jobs"] == []

    def test_create_job(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.post(
            "/api/jobs",
            json={
                "session_id": str(uuid4()),
                "agent_id": "bio_agent",
                "pipeline_name": "test",
                "steps": [
                    {
                        "process_id": "fold",
                        "step_name": "fold1",
                        "input_mappings": {"fasta": "params.fasta"},
                    }
                ],
                "parameters": {"fasta": "/input.fasta"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "submitted"
        assert data["job_id"] is not None

    def test_get_job(self):
        app, manager = _make_app_with_manager()
        client = TestClient(app)
        # Create a job first
        create_resp = client.post(
            "/api/jobs",
            json={
                "session_id": str(uuid4()),
                "agent_id": "bio_agent",
                "pipeline_name": "test",
                "steps": [
                    {
                        "process_id": "fold",
                        "step_name": "fold1",
                        "input_mappings": {"fasta": "params.fasta"},
                    }
                ],
                "parameters": {"fasta": "/input.fasta"},
            },
        )
        job_id = create_resp.json()["job_id"]
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id

    def test_get_job_not_found(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.get(f"/api/jobs/{uuid4()}")
        assert resp.status_code == 404


# =========================================================================
# Proposal Routes
# =========================================================================


class TestProposalRoutes:
    def test_list_proposals_no_manager(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get(f"/api/proposals?session_id={uuid4()}")
        assert resp.status_code == 503

    def test_list_proposals_empty(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.get(f"/api/proposals?session_id={uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["proposals"] == []


# =========================================================================
# Data Connection Routes
# =========================================================================


class TestDataConnectionRoutes:
    def test_create_and_list(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        sub_id = str(uuid4())

        # Create
        resp = client.post(
            f"/api/subreddits/{sub_id}/data-connections",
            json={
                "name": "test_db",
                "description": "Test database",
                "db_type": "postgresql",
                "connection_string": "postgresql://localhost/test",
                "read_only": True,
            },
        )
        assert resp.status_code == 200
        conn_id = resp.json()["id"]

        # List
        resp = client.get(f"/api/subreddits/{sub_id}/data-connections")
        assert resp.status_code == 200
        conns = resp.json()["connections"]
        assert len(conns) == 1
        assert conns[0]["name"] == "test_db"

    def test_delete_connection(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        sub_id = str(uuid4())

        resp = client.post(
            f"/api/subreddits/{sub_id}/data-connections",
            json={
                "name": "to_delete",
                "connection_string": "sqlite:///test.db",
            },
        )
        conn_id = resp.json()["id"]

        resp = client.delete(f"/api/subreddits/{sub_id}/data-connections/{conn_id}")
        assert resp.status_code == 200

    def test_delete_nonexistent(self):
        app, _ = _make_app_with_manager()
        client = TestClient(app)
        resp = client.delete(f"/api/subreddits/{uuid4()}/data-connections/{uuid4()}")
        assert resp.status_code == 404

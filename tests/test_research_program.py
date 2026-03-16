"""Tests for research program feature (Phase 1)."""

import pytest

from colloquip.agents.prompts import build_v3_system_prompt
from colloquip.models import Phase


class TestResearchProgramPromptInjection:
    """Test that research programs are injected into agent prompts."""

    def test_research_program_included_in_prompt(self):
        program = "# KRAS G12C Research\n## Focus\n- Binding affinity optimization"
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            research_program=program,
        )
        assert "## Research Program" in prompt
        assert "Binding affinity optimization" in prompt

    def test_research_program_appears_before_phase_mandate(self):
        program = "# My Research Program"
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            phase_mandate="Explore broadly.",
            research_program=program,
        )
        program_idx = prompt.index("## Research Program")
        # Phase mandate from v2 defaults includes "EXPLORATION"
        mandate_idx = prompt.index("Explore broadly.")
        assert program_idx < mandate_idx

    def test_research_program_appears_after_role(self):
        program = "# My Research Program"
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            role_prompt="Focus on target identification.",
            research_program=program,
        )
        role_idx = prompt.index("Your Role in This Community")
        program_idx = prompt.index("## Research Program")
        assert role_idx < program_idx

    def test_no_research_program_section_when_none(self):
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
        )
        assert "## Research Program" not in prompt

    def test_no_research_program_section_when_empty(self):
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            research_program="",
        )
        assert "## Research Program" not in prompt


class TestResearchProgramAPI:
    """Test research program API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from colloquip.api import create_app

        app = create_app()
        client = TestClient(app)
        # Initialize platform
        client.post("/api/platform/init")
        return client

    def test_get_research_program_empty(self, client):
        # Create a subreddit first
        client.post(
            "/api/subreddits",
            json={
                "name": "test_rp",
                "display_name": "Test RP",
                "description": "Test subreddit for research programs",
            },
        )
        resp = client.get("/api/subreddits/test_rp/research-program")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subreddit_name"] == "test_rp"
        assert data["content"] is None
        assert data["version"] == 0

    def test_update_research_program(self, client):
        client.post(
            "/api/subreddits",
            json={
                "name": "test_rp_update",
                "display_name": "Test RP Update",
                "description": "Testing research program updates",
            },
        )
        resp = client.put(
            "/api/subreddits/test_rp_update/research-program",
            json={"content": "# My Research\n## Focus\n- Drug discovery"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert "Drug discovery" in data["content"]

        # Second update increments version
        resp2 = client.put(
            "/api/subreddits/test_rp_update/research-program",
            json={"content": "# Updated Program"},
        )
        assert resp2.json()["version"] == 2

    def test_get_research_program_after_update(self, client):
        client.post(
            "/api/subreddits",
            json={
                "name": "test_rp_get",
                "display_name": "Test RP Get",
                "description": "Test",
            },
        )
        client.put(
            "/api/subreddits/test_rp_get/research-program",
            json={"content": "# Persistent Program"},
        )
        resp = client.get("/api/subreddits/test_rp_get/research-program")
        assert resp.status_code == 200
        assert "Persistent Program" in resp.json()["content"]

    def test_update_research_program_not_found(self, client):
        resp = client.put(
            "/api/subreddits/nonexistent/research-program",
            json={"content": "# Test"},
        )
        assert resp.status_code == 404

    def test_get_research_program_not_found(self, client):
        resp = client.get("/api/subreddits/nonexistent/research-program")
        assert resp.status_code == 404

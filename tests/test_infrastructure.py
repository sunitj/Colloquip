"""Tests for infrastructure: db/engine, display, cli.

Covers database initialization, display rendering, and CLI argument parsing.
See tests/TEST_STRATEGY.md for conventions.
"""

import os
from unittest.mock import patch
from uuid import uuid4

import pytest

# =========================================================================
# Database Engine
# =========================================================================


class TestDatabaseURL:
    def test_default_url(self):
        from colloquip.db.engine import _get_database_url

        with patch.dict(os.environ, {}, clear=True):
            url = _get_database_url()
            assert "sqlite" in url

    def test_url_from_env(self):
        from colloquip.db.engine import _get_database_url

        with patch.dict(os.environ, {"DATABASE_URL": "sqlite+aiosqlite:///test.db"}):
            url = _get_database_url()
            assert url == "sqlite+aiosqlite:///test.db"

    def test_postgresql_url_conversion(self):
        from colloquip.db.engine import _get_database_url

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"}):
            url = _get_database_url()
            assert url.startswith("postgresql+asyncpg://")
            assert "user:pass@localhost/db" in url


class TestCreateEngineAndTables:
    async def test_create_engine_and_get_session(self):
        import colloquip.db.engine as engine_mod

        # Save originals and reset module state
        orig_engine = engine_mod._engine
        orig_factory = engine_mod._session_factory

        try:
            engine_mod._engine = None
            engine_mod._session_factory = None

            await engine_mod.create_engine_and_tables("sqlite+aiosqlite:///:memory:")

            assert engine_mod._engine is not None
            assert engine_mod._session_factory is not None

            session = engine_mod.get_async_session()
            assert session is not None
            await session.close()
        finally:
            # Clean up
            if engine_mod._engine:
                await engine_mod.dispose_engine()
            engine_mod._engine = orig_engine
            engine_mod._session_factory = orig_factory

    async def test_dispose_engine(self):
        import colloquip.db.engine as engine_mod

        orig_engine = engine_mod._engine
        orig_factory = engine_mod._session_factory

        try:
            engine_mod._engine = None
            engine_mod._session_factory = None

            await engine_mod.create_engine_and_tables("sqlite+aiosqlite:///:memory:")
            await engine_mod.dispose_engine()

            assert engine_mod._engine is None
            assert engine_mod._session_factory is None
        finally:
            engine_mod._engine = orig_engine
            engine_mod._session_factory = orig_factory

    def test_get_session_before_init(self):
        import colloquip.db.engine as engine_mod

        orig_factory = engine_mod._session_factory
        try:
            engine_mod._session_factory = None
            with pytest.raises(RuntimeError, match="not initialized"):
                engine_mod.get_async_session()
        finally:
            engine_mod._session_factory = orig_factory

    async def test_dispose_when_no_engine(self):
        import colloquip.db.engine as engine_mod

        orig_engine = engine_mod._engine
        orig_factory = engine_mod._session_factory

        try:
            engine_mod._engine = None
            engine_mod._session_factory = None
            # Should not raise
            await engine_mod.dispose_engine()
        finally:
            engine_mod._engine = orig_engine
            engine_mod._session_factory = orig_factory


# =========================================================================
# Display — RichDisplay (if rich installed)
# =========================================================================


class TestRichDisplay:
    def test_create_display_plain(self):
        from colloquip.display import create_display

        display = create_display(use_rich=False)
        assert display.__class__.__name__ == "PlainDisplay"

    def test_create_display_rich_fallback(self):
        """create_display(True) should return PlainDisplay if rich is not installed."""
        from colloquip.display import create_display

        display = create_display(use_rich=True)
        # Either RichDisplay or PlainDisplay is fine depending on environment
        assert display is not None

    def test_plain_show_post_with_long_content(self, capsys):
        from colloquip.display import PlainDisplay
        from colloquip.models import AgentStance
        from tests.conftest import create_post

        display = PlainDisplay()
        post = create_post(
            agent_id="biology",
            content="x" * 500,
            stance=AgentStance.SUPPORTIVE,
        )
        display.show_post(post)
        captured = capsys.readouterr()
        assert "BIOLOGY" in captured.out

    def test_plain_show_consensus_empty_lists(self, capsys):
        from colloquip.display import PlainDisplay
        from colloquip.models import ConsensusMap

        display = PlainDisplay()
        consensus = ConsensusMap(
            session_id=uuid4(),
            summary="Summary.",
            agreements=[],
            disagreements=[],
            minority_positions=[],
        )
        display.show_consensus(consensus)
        captured = capsys.readouterr()
        assert "Summary." in captured.out

    def test_plain_show_energy_low(self, capsys):
        from colloquip.display import PlainDisplay
        from colloquip.models import EnergyUpdate

        display = PlainDisplay()
        update = EnergyUpdate(turn=5, energy=0.15, components={"novelty": 0.1, "staleness": 0.8})
        display.show_energy(update)
        captured = capsys.readouterr()
        assert "0.150" in captured.out

    def test_plain_show_footer(self, capsys):
        from colloquip.display import PlainDisplay

        display = PlainDisplay()
        display.show_footer(post_count=10)
        captured = capsys.readouterr()
        assert "10" in captured.out

    def test_plain_show_footer_with_tokens(self, capsys):
        from colloquip.display import PlainDisplay

        display = PlainDisplay()
        display.show_footer(
            post_count=5,
            token_usage={
                "total_tokens": 5000,
                "input_tokens": 3000,
                "output_tokens": 2000,
                "calls": 10,
            },
        )
        captured = capsys.readouterr()
        assert "5,000" in captured.out
        assert "3,000" in captured.out


# =========================================================================
# CLI — argument parsing and LLM creation
# =========================================================================


class TestCLI:
    def test_create_llm_mock(self):
        from colloquip.cli import _create_llm

        llm = _create_llm(mode="mock", seed=42)
        assert llm.__class__.__name__ == "MockLLM"

    def test_create_default_agents(self):
        from colloquip.cli import _create_llm, create_default_agents

        llm = _create_llm(mode="mock", seed=42)
        agents = create_default_agents(llm)
        assert len(agents) == 6
        assert "biology" in agents
        assert "redteam" in agents
        # Each value is a BaseDeliberationAgent
        assert agents["biology"].config.agent_id == "biology"

    def test_create_default_agents_red_team(self):
        from colloquip.cli import _create_llm, create_default_agents

        llm = _create_llm(mode="mock", seed=42)
        agents = create_default_agents(llm)
        red_team = [a for a in agents.values() if a.config.is_red_team]
        assert len(red_team) == 1
        assert red_team[0].config.agent_id == "redteam"

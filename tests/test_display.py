"""Tests for display module."""

import pytest

from colloquip.display import PlainDisplay, create_display
from colloquip.models import AgentStance, ConsensusMap, EnergyUpdate, Phase, PhaseSignal

from tests.conftest import create_post, create_metrics


class TestPlainDisplay:
    def test_show_header(self, capsys):
        display = PlainDisplay()
        display.show_header("Test hypothesis")
        captured = capsys.readouterr()
        assert "COLLOQUIP" in captured.out
        assert "Test hypothesis" in captured.out

    def test_show_post(self, capsys):
        display = PlainDisplay()
        post = create_post(
            agent_id="biology",
            content="Test content here.",
            stance=AgentStance.SUPPORTIVE,
        )
        post.triggered_by = ["relevance", "question"]
        display.show_post(post)
        captured = capsys.readouterr()
        assert "BIOLOGY" in captured.out
        assert "SUPPORTIVE" in captured.out
        assert "relevance" in captured.out

    def test_show_phase_transition(self, capsys):
        display = PlainDisplay()
        metrics = create_metrics()
        signal = PhaseSignal(
            current_phase=Phase.DEBATE,
            confidence=0.85,
            metrics=metrics,
            observation="High disagreement detected.",
        )
        display.show_phase_transition(signal)
        captured = capsys.readouterr()
        assert "DEBATE" in captured.out
        assert "0.85" in captured.out
        assert "High disagreement" in captured.out

    def test_no_duplicate_phase_transition(self, capsys):
        display = PlainDisplay()
        metrics = create_metrics()
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,  # Default phase
            confidence=0.9,
            metrics=metrics,
        )
        display.show_phase_transition(signal)
        captured = capsys.readouterr()
        assert captured.out == ""  # No output for same phase

    def test_show_energy(self, capsys):
        display = PlainDisplay()
        update = EnergyUpdate(turn=1, energy=0.75, components={})
        display.show_energy(update)
        captured = capsys.readouterr()
        assert "Energy" in captured.out
        assert "0.750" in captured.out

    def test_show_consensus(self, capsys):
        from uuid import uuid4
        display = PlainDisplay()
        consensus = ConsensusMap(
            session_id=uuid4(),
            summary="Test summary.",
            agreements=["Point A"],
            disagreements=["Point B"],
            minority_positions=["Point C"],
        )
        display.show_consensus(consensus)
        captured = capsys.readouterr()
        assert "SYNTHESIS" in captured.out
        assert "Test summary" in captured.out
        assert "Point A" in captured.out
        assert "Point B" in captured.out
        assert "Point C" in captured.out

    def test_show_footer(self, capsys):
        display = PlainDisplay()
        display.show_footer(25)
        captured = capsys.readouterr()
        assert "25 posts" in captured.out

    def test_show_footer_with_tokens(self, capsys):
        display = PlainDisplay()
        display.show_footer(10, {"total_tokens": 5000, "input_tokens": 3000, "output_tokens": 2000})
        captured = capsys.readouterr()
        assert "5,000" in captured.out


class TestCreateDisplay:
    def test_fallback_to_plain(self):
        display = create_display(use_rich=False)
        assert isinstance(display, PlainDisplay)

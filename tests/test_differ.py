"""Tests for the deliberation differ."""

from uuid import uuid4

import pytest

from colloquip.memory.differ import DeliberationDiff, MockDeliberationDiffer
from colloquip.memory.store import SynthesisMemory

SUB_A = uuid4()


def make_memory(
    topic="Test topic",
    key_conclusions=None,
    citations_used=None,
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=SUB_A,
        subreddit_name="test_sub",
        topic=topic,
        synthesis_content="Content",
        key_conclusions=key_conclusions or [],
        citations_used=citations_used or [],
    )


class TestMockDeliberationDiffer:
    @pytest.fixture
    def differ(self):
        return MockDeliberationDiffer()

    def test_new_conclusions(self, differ):
        earlier = make_memory(key_conclusions=["A is true"])
        later = make_memory(key_conclusions=["A is true", "B is also true"])
        diff = differ.diff(earlier, later)
        assert "B is also true" in diff.new_evidence

    def test_dropped_conclusions(self, differ):
        earlier = make_memory(key_conclusions=["A is true", "B is true"])
        later = make_memory(key_conclusions=["A is true"])
        diff = differ.diff(earlier, later)
        assert len(diff.changed_conclusions) == 1
        assert "B is true" in diff.changed_conclusions[0]

    def test_stable_trajectory(self, differ):
        earlier = make_memory(key_conclusions=["A is true"])
        later = make_memory(key_conclusions=["A is true"])
        diff = differ.diff(earlier, later)
        assert diff.overall_trajectory == "stable"

    def test_expanding_trajectory(self, differ):
        earlier = make_memory(key_conclusions=["A"])
        later = make_memory(key_conclusions=["A", "B", "C"])
        diff = differ.diff(earlier, later)
        assert diff.overall_trajectory == "expanding"

    def test_narrowing_trajectory(self, differ):
        earlier = make_memory(key_conclusions=["A", "B", "C"])
        later = make_memory(key_conclusions=["A"])
        diff = differ.diff(earlier, later)
        assert diff.overall_trajectory == "narrowing"

    def test_new_citations_detected(self, differ):
        earlier = make_memory(
            key_conclusions=["A"],
            citations_used=["PUBMED:111"],
        )
        later = make_memory(
            key_conclusions=["A"],
            citations_used=["PUBMED:111", "PUBMED:222"],
        )
        diff = differ.diff(earlier, later)
        assert any("PUBMED:222" in e for e in diff.new_evidence)

    def test_empty_memories(self, differ):
        earlier = make_memory()
        later = make_memory()
        diff = differ.diff(earlier, later)
        assert diff.overall_trajectory == "stable"


class TestDeliberationDiffFormatting:
    def test_format_for_prompt(self):
        diff = DeliberationDiff(
            earlier_memory_id=uuid4(),
            later_memory_id=uuid4(),
            new_evidence=["New finding X"],
            changed_conclusions=["Y was revised"],
            overall_trajectory="expanding",
        )
        text = diff.format_for_prompt()
        assert "New Evidence" in text
        assert "New finding X" in text
        assert "Changed Conclusions" in text
        assert "expanding" in text

    def test_format_empty_diff(self):
        diff = DeliberationDiff(
            earlier_memory_id=uuid4(),
            later_memory_id=uuid4(),
        )
        text = diff.format_for_prompt()
        assert "Changes Since Previous" in text

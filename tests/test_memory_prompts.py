"""Tests for memory-augmented prompt building (Phase 3 RAG)."""

from datetime import datetime, timezone
from uuid import uuid4

from colloquip.agents.prompts import build_memory_context, build_v3_system_prompt
from colloquip.memory.retriever import RetrievedMemories
from colloquip.memory.store import SynthesisMemory
from colloquip.models import Phase


def _make_memory(
    topic: str = "GLP-1 agonists",
    subreddit_name: str = "target_validation",
    key_conclusions: list | None = None,
    confidence_level: str = "high",
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=uuid4(),
        subreddit_name=subreddit_name,
        topic=topic,
        synthesis_content=f"Full synthesis about {topic}",
        key_conclusions=key_conclusions or [f"Key conclusion about {topic}"],
        confidence_level=confidence_level,
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


class TestBuildMemoryContext:
    def test_empty_memories_returns_empty(self):
        memories = RetrievedMemories()
        result = build_memory_context(memories)
        assert result == ""

    def test_arena_memories_formatted(self):
        mem = _make_memory(
            topic="BRCA1 validation",
            key_conclusions=["Strong genetic evidence", "IC50 data supports"],
        )
        memories = RetrievedMemories(arena=[mem])
        result = build_memory_context(memories)

        assert "This Subreddit" in result
        assert "BRCA1 validation" in result
        assert "Strong genetic evidence" in result
        assert "IC50 data supports" in result

    def test_global_memories_formatted(self):
        mem = _make_memory(
            topic="CDK4 analysis",
            subreddit_name="oncology",
            key_conclusions=["Promising target"],
        )
        memories = RetrievedMemories(global_results=[mem])
        result = build_memory_context(memories)

        assert "Other Subreddits" in result
        assert "[oncology]" in result
        assert "CDK4 analysis" in result

    def test_invalid_input_returns_empty(self):
        assert build_memory_context(None) == ""
        assert build_memory_context("not a RetrievedMemories") == ""


class TestV3SystemPromptWithMemory:
    def test_prompt_includes_memory_context(self):
        mem = _make_memory(key_conclusions=["Prior finding: X works well"])
        memories = RetrievedMemories(arena=[mem])
        memory_text = build_memory_context(memories)

        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            prior_deliberations=memory_text,
        )

        assert "Prior finding: X works well" in prompt
        assert "Instructions for Using Prior Deliberation Context" in prompt
        assert "REFERENCE prior conclusions" in prompt
        assert "FLAG any contradictions" in prompt

    def test_prompt_without_memory_has_no_memory_section(self):
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
        )

        assert "Prior Deliberation" not in prompt
        assert "Instructions for Using Prior" not in prompt

    def test_prompt_empty_string_memory_has_no_memory_section(self):
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            prior_deliberations="",
        )

        assert "Instructions for Using Prior" not in prompt

    def test_memory_positioned_before_phase_mandate(self):
        mem = _make_memory(key_conclusions=["MEMORY_MARKER_TEXT"])
        memories = RetrievedMemories(arena=[mem])
        memory_text = build_memory_context(memories)

        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            prior_deliberations=memory_text,
        )

        memory_pos = prompt.index("MEMORY_MARKER_TEXT")
        mandate_pos = prompt.index("EXPLORATION")
        assert memory_pos < mandate_pos

    def test_all_layers_present(self):
        mem = _make_memory(key_conclusions=["Prior conclusion here"])
        memories = RetrievedMemories(arena=[mem])
        memory_text = build_memory_context(memories)

        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.DEBATE,
            subreddit_context="## Community: r/test_sub\nDescription here",
            role_prompt="You are a member of this community.",
            prior_deliberations=memory_text,
            tool_descriptions=["PubMed search tool"],
        )

        # All layers present in order
        assert "biology expert" in prompt
        assert "r/test_sub" in prompt
        assert "member of this community" in prompt
        assert "Prior conclusion here" in prompt
        assert "DEBATE" in prompt
        assert "Citation Requirements" in prompt
        assert "PubMed search tool" in prompt
        assert "Response Format" in prompt

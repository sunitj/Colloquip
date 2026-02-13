"""Tests for synthesis memory extraction."""

from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.extractor import (
    SynthesisMemoryExtractor,
    extract_agents_involved,
    extract_citations,
    extract_key_conclusions,
)
from colloquip.models import AuditChain, Synthesis

# --- extract_citations ---


class TestExtractCitations:
    def test_pubmed_citations(self):
        text = "This is supported by [PUBMED:12345678] and [PUBMED:87654321]."
        result = extract_citations(text)
        assert result == ["PUBMED:12345678", "PUBMED:87654321"]

    def test_internal_citations(self):
        text = "See internal data [INTERNAL:assay-2024-001] for details."
        result = extract_citations(text)
        assert result == ["INTERNAL:assay-2024-001"]

    def test_web_citations(self):
        text = "According to [WEB:https://example.com/paper]."
        result = extract_citations(text)
        assert result == ["WEB:https://example.com/paper"]

    def test_mixed_citations(self):
        text = (
            "Evidence from [PUBMED:111] and [INTERNAL:rec-1] supports this. "
            "Also see [WEB:https://x.com]."
        )
        result = extract_citations(text)
        assert len(result) == 3
        assert "PUBMED:111" in result
        assert "INTERNAL:rec-1" in result

    def test_no_citations(self):
        text = "No citations here."
        assert extract_citations(text) == []

    def test_empty_text(self):
        assert extract_citations("") == []


# --- extract_key_conclusions ---


class TestExtractKeyConclusions:
    def test_from_executive_summary_bullets(self):
        sections = {
            "executive_summary": (
                "Overview of findings:\n"
                "- BRCA1 shows strong genetic evidence for target validation\n"
                "- Compound X demonstrates IC50 of 5nM against the target\n"
                "- Safety profile requires further investigation"
            ),
        }
        result = extract_key_conclusions(sections)
        assert len(result) == 3
        assert "BRCA1 shows strong genetic evidence" in result[0]

    def test_from_key_findings(self):
        sections = {
            "key_findings": "- Finding one is significant\n- Finding two is also important",
        }
        result = extract_key_conclusions(sections)
        assert len(result) == 2

    def test_max_conclusions_respected(self):
        sections = {
            "executive_summary": "\n".join(
                f"- Conclusion number {i} with enough detail" for i in range(10)
            ),
        }
        result = extract_key_conclusions(sections, max_conclusions=3)
        assert len(result) == 3

    def test_fallback_to_first_sentences(self):
        sections = {
            "evidence_against": (
                "The data suggests significant challenges with the approach. "
                "More investigation needed."
            ),
        }
        result = extract_key_conclusions(sections)
        assert len(result) >= 1
        assert "significant challenges" in result[0]

    def test_empty_sections(self):
        assert extract_key_conclusions({}) == []

    def test_skips_short_bullets(self):
        sections = {
            "key_findings": "- Too short\n- This bullet is long enough to be meaningful",
        }
        result = extract_key_conclusions(sections)
        assert len(result) == 1

    def test_deduplicates(self):
        sections = {
            "executive_summary": "- Same conclusion appears here\n- Same conclusion appears here",
            "key_findings": "- Same conclusion appears here",
        }
        result = extract_key_conclusions(sections)
        assert len(result) == 1

    def test_asterisk_bullets(self):
        sections = {
            "key_findings": "* Asterisk bullet with enough content\n* Another asterisk bullet here",
        }
        result = extract_key_conclusions(sections)
        assert len(result) == 2


# --- extract_agents_involved ---


class TestExtractAgentsInvolved:
    def test_from_audit_chains(self):
        chains = [
            AuditChain(
                claim="test",
                dissenting_agents=["chemistry", "biology"],
            ),
            AuditChain(
                claim="test2",
                dissenting_agents=["admet"],
            ),
        ]
        result = extract_agents_involved(chains, {})
        assert set(result) == {"admet", "biology", "chemistry"}

    def test_from_metadata_list(self):
        result = extract_agents_involved(
            [],
            {"agents_involved": ["biology", "chemistry"]},
        )
        assert set(result) == {"biology", "chemistry"}

    def test_from_metadata_string(self):
        result = extract_agents_involved(
            [],
            {"agents_involved": "biology, chemistry, admet"},
        )
        assert set(result) == {"admet", "biology", "chemistry"}

    def test_combined_sources(self):
        chains = [AuditChain(claim="x", dissenting_agents=["regulatory"])]
        metadata = {"agents_involved": ["biology"]}
        result = extract_agents_involved(chains, metadata)
        assert set(result) == {"biology", "regulatory"}

    def test_empty(self):
        assert extract_agents_involved([], {}) == []

    def test_sorted_output(self):
        chains = [AuditChain(claim="x", dissenting_agents=["z_agent", "a_agent"])]
        result = extract_agents_involved(chains, {})
        assert result == ["a_agent", "z_agent"]


# --- SynthesisMemoryExtractor ---


class TestSynthesisMemoryExtractor:
    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.fixture
    def extractor(self, provider):
        return SynthesisMemoryExtractor(embedding_provider=provider)

    _DEFAULT_SECTIONS = {
        "executive_summary": (
            "Overview:\n"
            "- GLP-1 agonists show promise for cognitive function\n"
            "- Evidence from [PUBMED:12345678] supports mechanism"
        ),
        "evidence_for": (
            "- Receptor binding data confirms activity [PUBMED:87654321]\n"
            "- Internal assay data [INTERNAL:assay-001] shows IC50 of 5nM"
        ),
        "key_risks": "Cardiac safety remains a concern.",
    }

    _DEFAULT_METADATA = {
        "confidence_level": "moderate",
        "evidence_quality": "moderate-high",
    }

    def _make_synthesis(self, sections=None, metadata=None):
        return Synthesis(
            thread_id=uuid4(),
            template_type="assessment",
            sections=self._DEFAULT_SECTIONS if sections is None else sections,
            metadata=self._DEFAULT_METADATA if metadata is None else metadata,
            audit_chains=[
                AuditChain(
                    claim="GLP-1 mechanism is valid",
                    dissenting_agents=["red_team", "admet"],
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_basic_extraction(self, extractor):
        synthesis = self._make_synthesis()
        subreddit_id = uuid4()

        memory = await extractor.extract(
            synthesis=synthesis,
            topic="GLP-1 agonists and cognitive function",
            subreddit_id=subreddit_id,
            subreddit_name="target_validation",
        )

        assert memory.thread_id == synthesis.thread_id
        assert memory.subreddit_id == subreddit_id
        assert memory.subreddit_name == "target_validation"
        assert memory.topic == "GLP-1 agonists and cognitive function"
        assert memory.template_type == "assessment"
        assert memory.confidence_level == "moderate"
        assert memory.evidence_quality == "moderate-high"

    @pytest.mark.asyncio
    async def test_key_conclusions_extracted(self, extractor):
        synthesis = self._make_synthesis()
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert len(memory.key_conclusions) > 0
        assert any("GLP-1" in c for c in memory.key_conclusions)

    @pytest.mark.asyncio
    async def test_citations_extracted(self, extractor):
        synthesis = self._make_synthesis()
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert "PUBMED:12345678" in memory.citations_used
        assert "PUBMED:87654321" in memory.citations_used
        assert "INTERNAL:assay-001" in memory.citations_used

    @pytest.mark.asyncio
    async def test_citations_deduplicated(self, extractor):
        synthesis = self._make_synthesis(
            sections={
                "section_a": "See [PUBMED:111] for details.",
                "section_b": "Also [PUBMED:111] confirms this.",
            },
        )
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert memory.citations_used.count("PUBMED:111") == 1

    @pytest.mark.asyncio
    async def test_agents_from_audit_chains(self, extractor):
        synthesis = self._make_synthesis()
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert "red_team" in memory.agents_involved
        assert "admet" in memory.agents_involved

    @pytest.mark.asyncio
    async def test_explicit_agents_override(self, extractor):
        synthesis = self._make_synthesis()
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
            agents_involved=["biology", "chemistry", "clinical"],
        )

        assert memory.agents_involved == ["biology", "chemistry", "clinical"]

    @pytest.mark.asyncio
    async def test_embedding_generated(self, extractor):
        synthesis = self._make_synthesis()
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="test topic",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert len(memory.embedding) == 64
        assert any(v != 0.0 for v in memory.embedding)

    @pytest.mark.asyncio
    async def test_empty_synthesis(self, extractor):
        synthesis = self._make_synthesis(sections={}, metadata={})
        memory = await extractor.extract(
            synthesis=synthesis,
            topic="empty topic",
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
        )

        assert memory.topic == "empty topic"
        assert memory.key_conclusions == []
        assert memory.citations_used == []
        assert memory.confidence_level == ""
        assert len(memory.embedding) == 64

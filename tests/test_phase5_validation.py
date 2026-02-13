"""Phase 5 validation: end-to-end tests for cross-subreddit refs and feedback."""

from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.feedback.calibration import AgentCalibration
from colloquip.feedback.outcome import InMemoryOutcomeTracker, OutcomeReport
from colloquip.memory.cross_references import CrossReferenceDetector, extract_entities
from colloquip.memory.differ import DeliberationDiff, MockDeliberationDiffer
from colloquip.memory.store import InMemoryStore, SynthesisMemory

SUB_A = uuid4()
SUB_B = uuid4()
SUB_C = uuid4()


def make_memory(
    topic: str,
    subreddit_id=None,
    subreddit_name="sub_a",
    key_conclusions=None,
    synthesis_content="",
    citations_used=None,
    embedding=None,
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=subreddit_id or SUB_A,
        subreddit_name=subreddit_name,
        topic=topic,
        synthesis_content=synthesis_content,
        key_conclusions=key_conclusions or [],
        citations_used=citations_used or [],
        embedding=embedding or [],
    )


class TestPhase5CrossSubredditPipeline:
    """Validate cross-subreddit reference detection end-to-end."""

    @pytest.mark.asyncio
    async def test_cross_reference_pipeline(self):
        """Full pipeline: store memories, detect cross-references."""
        provider = MockEmbeddingProvider(dimension=64)
        store = InMemoryStore()

        # Create memories in different subreddits with shared entities
        emb_a = await provider.embed("BRCA1 PMID:55555 drug target validation")
        mem_a = make_memory(
            topic="BRCA1 target validation with PMID:55555",
            subreddit_id=SUB_A,
            subreddit_name="oncology",
            key_conclusions=["BRCA1 is a viable PMID:55555 target"],
            synthesis_content="Study PMID:55555 validates BRCA1 as target.",
            embedding=emb_a,
        )

        emb_b = await provider.embed("BRCA1 PMID:55555 drug chemistry")
        mem_b = make_memory(
            topic="BRCA1 inhibitor chemistry PMID:55555",
            subreddit_id=SUB_B,
            subreddit_name="medicinal_chemistry",
            key_conclusions=["BRCA1 inhibitors show promise PMID:55555"],
            synthesis_content="PMID:55555 guides BRCA1 inhibitor design.",
            embedding=emb_b,
        )

        await store.save(mem_a)
        await store.save(mem_b)

        detector = CrossReferenceDetector(
            memory_store=store,
            embedding_provider=provider,
            similarity_threshold=0.3,  # Low for testing with mock embeddings
        )

        refs = await detector.detect_for_memory(mem_a)
        # Should find cross-reference due to shared PMID and BRCA1
        assert len(refs) >= 1
        ref = refs[0]
        assert ref.target_subreddit_name == "medicinal_chemistry"
        assert any("PMID:55555" in e for e in ref.shared_entities)

    @pytest.mark.asyncio
    async def test_diff_between_deliberations(self):
        """Diff identifies changes between related syntheses."""
        earlier = make_memory(
            topic="GLP-1 assessment v1",
            key_conclusions=["Conclusion A", "Conclusion B"],
            citations_used=["PUBMED:111"],
        )
        later = make_memory(
            topic="GLP-1 assessment v2",
            key_conclusions=["Conclusion A", "Conclusion C"],
            citations_used=["PUBMED:111", "PUBMED:222"],
        )

        differ = MockDeliberationDiffer()
        diff = differ.diff(earlier, later)

        assert "Conclusion C" in diff.new_evidence
        assert any("Conclusion B" in c for c in diff.changed_conclusions)
        assert any("PUBMED:222" in e for e in diff.new_evidence)

    @pytest.mark.asyncio
    async def test_diff_format_for_prompt(self):
        """Diff can be formatted for prompt injection."""
        diff = DeliberationDiff(
            earlier_memory_id=uuid4(),
            later_memory_id=uuid4(),
            new_evidence=["New finding about BRCA1"],
            changed_conclusions=["Previous claim about EGFR was revised"],
            overall_trajectory="evolving",
        )
        text = diff.format_for_prompt()
        assert "New Evidence" in text
        assert "BRCA1" in text
        assert "evolving" in text


class TestPhase5FeedbackPipeline:
    """Validate outcome tracking and calibration end-to-end."""

    @pytest.mark.asyncio
    async def test_outcome_to_calibration_pipeline(self):
        """Report outcomes, then compute meaningful calibration."""
        tracker = InMemoryOutcomeTracker()

        # Report 10+ outcomes
        for i in range(12):
            outcome = OutcomeReport(
                thread_id=uuid4(),
                subreddit_id=SUB_A,
                outcome_type="confirmed" if i % 3 != 0 else "contradicted",
                summary=f"Outcome {i}",
                agent_assessments={
                    "biology": "correct" if i % 2 == 0 else "incorrect",
                    "chemistry": "correct" if i % 3 == 0 else "partial",
                },
            )
            await tracker.save_outcome(outcome)

        outcomes = await tracker.list_all()
        assert len(outcomes) == 12

        calibration = AgentCalibration()
        overview = calibration.compute_overview(outcomes)

        assert overview.total_outcomes == 12
        assert overview.agents_with_data == 2
        assert overview.agents_calibrated == 2  # Both have 12 evaluations

        # Check individual agent reports
        bio_report = next(r for r in overview.agent_reports if r.agent_id == "biology")
        assert bio_report.is_meaningful
        assert bio_report.total_evaluations == 12
        assert bio_report.correct + bio_report.incorrect == 12

    @pytest.mark.asyncio
    async def test_domain_specific_calibration(self):
        """Calibration surfaces domain-specific accuracy differences."""
        tracker = InMemoryOutcomeTracker()

        # Agent correct in oncology, incorrect in chemistry
        for _ in range(5):
            await tracker.save_outcome(
                OutcomeReport(
                    thread_id=uuid4(),
                    subreddit_id=SUB_A,
                    outcome_type="confirmed",
                    summary="Oncology outcome",
                    agent_assessments={"agent_x": "correct"},
                )
            )
        for _ in range(5):
            await tracker.save_outcome(
                OutcomeReport(
                    thread_id=uuid4(),
                    subreddit_id=SUB_B,
                    outcome_type="contradicted",
                    summary="Chemistry outcome",
                    agent_assessments={"agent_x": "incorrect"},
                )
            )

        outcomes = await tracker.list_all()
        calibration = AgentCalibration()
        subreddit_names = {SUB_A: "oncology", SUB_B: "chemistry"}
        report = calibration.compute_calibration(
            "agent_x", outcomes, subreddit_names=subreddit_names
        )

        assert report.domain_accuracy["oncology"] == 1.0
        assert report.domain_accuracy["chemistry"] == 0.0
        assert report.is_meaningful

    @pytest.mark.asyncio
    async def test_entity_extraction_comprehensive(self):
        """Entity extraction works across different formats."""
        text = """
        According to PMID:12345, the BRCA1 gene plays a role in cancer.
        Compound GLP-123 targets the EGFR pathway. See also PMID 67890.
        """
        entities = extract_entities(text)
        assert "PMID:12345" in entities
        assert "PMID:67890" in entities
        # At least some gene entities should be found
        gene_entities = [e for e in entities if e.startswith("GENE:")]
        assert len(gene_entities) > 0

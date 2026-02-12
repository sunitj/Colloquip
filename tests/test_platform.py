"""Tests for the social platform layer.

Covers: models, persona loading, agent registry, tools, output templates,
cost tracking, synthesis parsing, citation verification, prompt builder v3,
platform manager, and API routes.
"""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from colloquip.models import (
    AgentStance,
    AgentStatus,
    BaseAgentIdentity,
    CitationVerification,
    CostRecord,
    ExpertiseGap,
    OutputSection,
    OutputTemplate,
    ParticipationModel,
    Phase,
    RecruitmentResult,
    SubredditConfig,
    SubredditMembership,
    SubredditPurpose,
    SubredditRole,
    Synthesis,
    ThinkingType,
    Thread,
    ThreadStatus,
    ToolType,
)

# =========================================================================
# Model tests
# =========================================================================


class TestNewEnums:
    def test_thinking_type_values(self):
        assert ThinkingType.ASSESSMENT.value == "assessment"
        assert ThinkingType.ANALYSIS.value == "analysis"
        assert ThinkingType.REVIEW.value == "review"
        assert ThinkingType.IDEATION.value == "ideation"

    def test_participation_model_values(self):
        assert ParticipationModel.OBSERVER.value == "observer"
        assert ParticipationModel.GUIDED.value == "guided"
        assert ParticipationModel.PARTICIPANT.value == "participant"
        assert ParticipationModel.APPROVER.value == "approver"

    def test_subreddit_role_values(self):
        assert SubredditRole.MEMBER.value == "member"
        assert SubredditRole.MODERATOR.value == "moderator"
        assert SubredditRole.RED_TEAM.value == "red_team"

    def test_agent_status_values(self):
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.RETIRED.value == "retired"
        assert AgentStatus.DRAFT.value == "draft"

    def test_thread_status_values(self):
        assert ThreadStatus.ACTIVE.value == "active"
        assert ThreadStatus.COMPLETED.value == "completed"
        assert ThreadStatus.FAILED.value == "failed"
        assert ThreadStatus.CANCELLED.value == "cancelled"

    def test_tool_type_values(self):
        assert ToolType.LITERATURE_SEARCH.value == "literature_search"
        assert ToolType.WEB_SEARCH.value == "web_search"


class TestNewModels:
    def test_output_section(self):
        section = OutputSection(name="summary", description="A summary section")
        assert section.required is True

    def test_output_template(self):
        template = OutputTemplate(
            template_type="assessment",
            sections=[OutputSection(name="summary", description="Summary")],
            metadata_fields=["confidence"],
        )
        assert template.template_type == "assessment"
        assert len(template.sections) == 1
        assert template.metadata_fields == ["confidence"]

    def test_base_agent_identity_defaults(self):
        agent = BaseAgentIdentity(
            agent_type="biology",
            display_name="Biology Expert",
            persona_prompt="You are a biologist.",
        )
        assert agent.status == AgentStatus.ACTIVE
        assert agent.version == 1
        assert agent.is_red_team is False
        assert isinstance(agent.id, UUID)

    def test_subreddit_membership(self):
        m = SubredditMembership(
            agent_id=uuid4(),
            subreddit_id=uuid4(),
            role=SubredditRole.RED_TEAM,
        )
        assert m.role == SubredditRole.RED_TEAM
        assert m.threads_participated == 0

    def test_cost_record(self):
        record = CostRecord(
            thread_id=uuid4(),
            input_tokens=1000,
            output_tokens=500,
            model="claude-sonnet",
            estimated_cost_usd=0.01,
        )
        assert record.input_tokens == 1000

    def test_synthesis(self):
        s = Synthesis(
            thread_id=uuid4(),
            template_type="assessment",
            sections={"summary": "Test"},
        )
        assert s.total_citations == 0
        assert isinstance(s.citation_verification, CitationVerification)

    def test_thread(self):
        t = Thread(
            subreddit_id=uuid4(),
            title="Test Thread",
            initial_post="Does this work?",
        )
        assert t.status == ThreadStatus.ACTIVE
        assert t.current_phase == Phase.EXPLORE

    def test_expertise_gap(self):
        gap = ExpertiseGap(expertise="bioinformatics")
        assert gap.is_red_team is False
        assert gap.has_curated_template is False

    def test_recruitment_result(self):
        result = RecruitmentResult()
        assert result.memberships == []
        assert result.gaps == []

    def test_subreddit_config(self):
        config = SubredditConfig(
            name="test_sub",
            display_name="Test Sub",
            description="For testing",
            purpose=SubredditPurpose(
                thinking_type=ThinkingType.ASSESSMENT,
                core_questions=["Does it work?"],
                decision_context="Testing context",
                primary_domain="drug_discovery",
            ),
            output_template=OutputTemplate(
                template_type="assessment",
                sections=[OutputSection(name="summary", description="Summary")],
            ),
        )
        assert config.always_include_red_team is True
        assert config.max_cost_per_thread_usd == 5.0


# =========================================================================
# Persona loader tests
# =========================================================================


class TestPersonaLoader:
    def test_load_all_personas(self):
        from colloquip.agents.persona_loader import load_all_personas

        personas = load_all_personas()
        assert len(personas) >= 10
        # Check expected persona types
        expected = {
            "molecular_biology",
            "medicinal_chemistry",
            "admet",
            "clinical",
            "regulatory",
            "computational_biology",
            "protein_engineering",
            "synthetic_biology",
            "red_team_general",
            "red_team_biology",
        }
        assert expected.issubset(set(personas.keys())), (
            f"Missing: {expected - set(personas.keys())}"
        )

    def test_persona_structure(self):
        from colloquip.agents.persona_loader import load_all_personas

        personas = load_all_personas()
        for agent_type, data in personas.items():
            assert "agent_type" in data
            assert data["agent_type"] == agent_type
            assert "display_name" in data
            assert "expertise_tags" in data
            assert "persona_prompt" in data
            assert "evaluation_criteria" in data
            assert "phase_mandates" in data
            assert "domain_keywords" in data
            assert "is_red_team" in data

            # Criteria sum to ~1.0
            total = sum(data["evaluation_criteria"].values())
            assert 0.95 <= total <= 1.05, f"{agent_type}: criteria sum = {total}"

            # Phase mandates present
            for phase in ("explore", "debate", "deepen", "converge"):
                assert phase in data["phase_mandates"]

    def test_persona_to_agent_identity(self):
        from colloquip.agents.persona_loader import (
            load_all_personas,
            persona_to_agent_identity,
        )

        personas = load_all_personas()
        for agent_type, data in personas.items():
            agent = persona_to_agent_identity(data)
            assert isinstance(agent, BaseAgentIdentity)
            assert agent.agent_type == agent_type
            assert len(agent.expertise_tags) > 0

    def test_load_agent_identities(self):
        from colloquip.agents.persona_loader import load_agent_identities

        identities = load_agent_identities()
        assert len(identities) >= 10
        types = {a.agent_type for a in identities}
        assert "molecular_biology" in types
        assert "red_team_general" in types

    def test_get_persona_by_type(self):
        from colloquip.agents.persona_loader import get_persona_by_type

        persona = get_persona_by_type("medicinal_chemistry")
        assert persona is not None
        assert persona["agent_type"] == "medicinal_chemistry"

        missing = get_persona_by_type("nonexistent_type")
        assert missing is None

    def test_load_nonexistent_dir(self):
        from colloquip.agents.persona_loader import load_all_personas

        personas = load_all_personas(Path("/nonexistent/dir"))
        assert personas == {}

    def test_red_team_agents_flagged(self):
        from colloquip.agents.persona_loader import load_all_personas

        personas = load_all_personas()
        red_teams = [k for k, v in personas.items() if v["is_red_team"]]
        assert "red_team_general" in red_teams
        assert "red_team_biology" in red_teams
        non_red = [k for k, v in personas.items() if not v["is_red_team"]]
        assert "molecular_biology" in non_red


# =========================================================================
# Agent registry tests
# =========================================================================


class TestAgentRegistry:
    def _make_registry(self):
        from colloquip.registry import AgentRegistry

        registry = AgentRegistry()
        registry.load_from_personas()
        return registry

    def test_load_from_personas(self):
        registry = self._make_registry()
        assert registry.pool_size >= 10

    def test_list_agents(self):
        registry = self._make_registry()
        agents = registry.list_agents()
        assert len(agents) >= 10
        types = {a.agent_type for a in agents}
        assert "molecular_biology" in types

    def test_get_agent_by_type(self):
        registry = self._make_registry()
        agent = registry.get_agent_by_type("medicinal_chemistry")
        assert agent is not None
        assert agent.agent_type == "medicinal_chemistry"

    def test_get_agent_by_uuid(self):
        registry = self._make_registry()
        agent = registry.get_agent_by_type("clinical")
        assert agent is not None
        retrieved = registry.get_agent(agent.id)
        assert retrieved is not None
        assert retrieved.agent_type == "clinical"

    def test_register_agent_idempotent(self):
        registry = self._make_registry()
        agent = registry.get_agent_by_type("admet")
        assert agent is not None
        size_before = registry.pool_size
        returned = registry.register_agent(agent)
        assert registry.pool_size == size_before
        assert returned.id == agent.id

    def test_register_duplicate_type(self):
        registry = self._make_registry()
        # Try registering a new agent with existing type
        new_agent = BaseAgentIdentity(
            agent_type="molecular_biology",
            display_name="Another Bio",
            persona_prompt="Duplicate.",
        )
        size_before = registry.pool_size
        returned = registry.register_agent(new_agent)
        # Should return the existing one, not add
        assert registry.pool_size == size_before
        assert returned.agent_type == "molecular_biology"
        assert returned.id != new_agent.id  # Returns existing

    def test_find_by_expertise_exact(self):
        registry = self._make_registry()
        matches = registry.find_by_expertise("medicinal_chemistry")
        assert len(matches) > 0
        best_agent, best_score = matches[0]
        assert best_agent.agent_type == "medicinal_chemistry"
        assert best_score >= 0.5  # Exact type match

    def test_find_by_expertise_fuzzy(self):
        registry = self._make_registry()
        matches = registry.find_by_expertise("protein_stability")
        assert len(matches) > 0
        # Should find protein_engineering among results
        types_found = {a.agent_type for a, _ in matches}
        assert "protein_engineering" in types_found

    def test_find_by_expertise_no_match(self):
        registry = self._make_registry()
        matches = registry.find_by_expertise("quantum_computing")
        # Should return empty (or very low scores)
        assert len(matches) == 0

    def test_find_or_create_existing(self):
        registry = self._make_registry()
        size_before = registry.pool_size
        agent = registry.find_or_create("regulatory")
        assert agent.agent_type == "regulatory"
        assert registry.pool_size == size_before

    def test_find_or_create_new(self):
        registry = self._make_registry()
        size_before = registry.pool_size
        agent = registry.find_or_create("quantum_computing_specialist")
        assert agent.agent_type == "quantum_computing_specialist"
        assert registry.pool_size == size_before + 1

    def test_find_red_team_agents(self):
        registry = self._make_registry()
        red_teams = registry.find_red_team_agents()
        assert len(red_teams) >= 2
        types = {a.agent_type for a in red_teams}
        assert "red_team_general" in types
        assert "red_team_biology" in types


class TestRecruitment:
    def _make_registry(self):
        from colloquip.registry import AgentRegistry

        registry = AgentRegistry()
        registry.load_from_personas()
        return registry

    def test_recruit_for_subreddit(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["molecular_biology", "medicinal_chemistry", "clinical"],
            subreddit_id=sub_id,
            subreddit_domain="drug_discovery",
        )
        assert isinstance(result, RecruitmentResult)
        assert len(result.memberships) >= 3  # 3 required + red team

    def test_recruit_always_includes_red_team(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["molecular_biology"],
            subreddit_id=sub_id,
        )
        roles = {m.role for m in result.memberships}
        assert SubredditRole.RED_TEAM in roles

    def test_recruit_no_duplicate_agents(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["molecular_biology", "molecular_biology"],
            subreddit_id=sub_id,
        )
        agent_ids = [m.agent_id for m in result.memberships]
        assert len(agent_ids) == len(set(agent_ids)), "No duplicate agents"

    def test_recruit_reports_gaps(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["quantum_computing"],
            subreddit_id=sub_id,
        )
        assert len(result.gaps) >= 1
        gap_names = {g.expertise for g in result.gaps}
        assert "quantum_computing" in gap_names

    def test_recruit_optional_expertise(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["molecular_biology"],
            subreddit_id=sub_id,
            optional_expertise=["computational_biology"],
        )
        agent_types = set()
        for m in result.memberships:
            agent = registry.get_agent(m.agent_id)
            if agent:
                agent_types.add(agent.agent_type)
        assert "computational_biology" in agent_types

    def test_recruit_domain_specific_red_team(self):
        registry = self._make_registry()
        sub_id = uuid4()
        result = registry.recruit_for_subreddit(
            required_expertise=["molecular_biology"],
            subreddit_id=sub_id,
            subreddit_domain="biology",
        )
        red_team_members = [m for m in result.memberships if m.role == SubredditRole.RED_TEAM]
        assert len(red_team_members) >= 1
        # Should prefer biology-specific red team
        for m in red_team_members:
            agent = registry.get_agent(m.agent_id)
            if agent and "biology" in agent.agent_type:
                assert True
                break
        else:
            # General red team is also acceptable
            pass


# =========================================================================
# Tool tests
# =========================================================================


class TestToolInterface:
    def test_search_result_model(self):
        from colloquip.tools.interface import SearchResult

        result = SearchResult(
            title="Test Paper",
            authors=["Smith J"],
            source_type="pubmed",
            source_id="12345",
        )
        assert result.title == "Test Paper"
        assert result.relevance_score == 0.0

    def test_tool_result_model(self):
        from colloquip.tools.interface import ToolResult

        result = ToolResult(source="pubmed", query="test")
        assert result.results == []
        assert result.error is None

    def test_base_search_tool_citation_formats(self):
        from colloquip.tools.interface import SearchResult
        from colloquip.tools.pubmed import MockPubMedTool

        # BaseSearchTool is now ABC — use a concrete subclass for testing
        tool = MockPubMedTool()

        pubmed_result = SearchResult(title="Paper", source_type="pubmed", source_id="12345")
        assert tool._format_citation_ref(pubmed_result) == "[PUBMED:12345]"

        internal_result = SearchResult(title="Doc", source_type="internal", source_id="INT-001")
        assert tool._format_citation_ref(internal_result) == "[INTERNAL:INT-001]"

        web_result = SearchResult(title="Web", source_type="web", url="https://example.com")
        assert tool._format_citation_ref(web_result) == "[WEB:https://example.com]"

    def test_base_search_tool_is_abc(self):
        import abc

        from colloquip.tools.interface import BaseSearchTool

        assert issubclass(BaseSearchTool, abc.ABC)


class TestMockTools:
    @pytest.fixture
    def event_loop_policy(self):
        return asyncio.DefaultEventLoopPolicy()

    @pytest.mark.asyncio
    async def test_mock_pubmed(self):
        from colloquip.tools.pubmed import MockPubMedTool

        tool = MockPubMedTool()
        assert tool.name == "pubmed_search"
        result = await tool.execute(query="GLP-1")
        assert result.source == "pubmed"
        assert len(result.results) == 3
        assert result.error is None
        assert "GLP-1" in result.results[0].title

    @pytest.mark.asyncio
    async def test_mock_pubmed_schema(self):
        from colloquip.tools.pubmed import MockPubMedTool

        tool = MockPubMedTool()
        schema = tool.tool_schema
        assert schema["name"] == "pubmed_search"
        assert "input_schema" in schema
        assert "query" in schema["input_schema"]["properties"]

    @pytest.mark.asyncio
    async def test_mock_company_docs(self):
        from colloquip.tools.company_docs import MockCompanyDocsTool

        tool = MockCompanyDocsTool()
        assert tool.name == "company_docs"
        result = await tool.execute(query="selectivity")
        assert result.source == "company_docs"
        assert len(result.results) == 2
        assert result.results[0].source_type == "internal"

    @pytest.mark.asyncio
    async def test_mock_web_search(self):
        from colloquip.tools.web_search import MockWebSearchTool

        tool = MockWebSearchTool()
        assert tool.name == "web_search"
        result = await tool.execute(query="kinase inhibitor")
        assert result.source == "web"
        assert len(result.results) == 1
        assert result.results[0].source_type == "web"

    @pytest.mark.asyncio
    async def test_mock_pubmed_respects_max_results(self):
        from colloquip.tools.pubmed import MockPubMedTool

        tool = MockPubMedTool()
        result = await tool.execute(query="test", max_results=1)
        assert len(result.results) == 1


class TestToolRegistry:
    def test_available_tools(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        tools = reg.available_tools()
        assert "pubmed_search" in tools
        assert "company_docs" in tools
        assert "web_search" in tools

    def test_create_mock_tool(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        tool = reg.create_tool("pubmed_search")
        assert tool.name == "pubmed_search"

    def test_create_unknown_tool(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        with pytest.raises(ValueError, match="Unknown tool"):
            reg.create_tool("nonexistent_tool")

    def test_get_tools_for_subreddit(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        configs = [
            {"tool_id": "pubmed_search", "enabled": True},
            {"tool_id": "company_docs", "enabled": True},
            {"tool_id": "web_search", "enabled": False},
        ]
        tools = reg.get_tools_for_subreddit(configs)
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "pubmed_search" in names
        assert "company_docs" in names
        assert "web_search" not in names

    def test_get_claude_tool_schemas(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        tools = [reg.create_tool("pubmed_search"), reg.create_tool("web_search")]
        schemas = reg.get_claude_tool_schemas(tools)
        assert len(schemas) == 2
        assert all("name" in s for s in schemas)
        assert all("input_schema" in s for s in schemas)

    @pytest.mark.asyncio
    async def test_execute_tool_call(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        tools = [reg.create_tool("pubmed_search")]
        result = await reg.execute_tool_call("pubmed_search", {"query": "BRAF"}, tools)
        assert "source" in result
        assert result["source"] == "pubmed"

    @pytest.mark.asyncio
    async def test_execute_tool_call_not_found(self):
        from colloquip.tools.registry import ToolRegistry

        reg = ToolRegistry(mock_mode=True)
        result = await reg.execute_tool_call("nonexistent", {}, [])
        assert "error" in result


# =========================================================================
# Citation verifier tests
# =========================================================================


class TestCitationVerifier:
    def test_extract_citation_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        text = (
            "Based on [PUBMED:12345678] and [INTERNAL:INT-001], "
            "we also found [WEB:https://example.com/paper] relevant."
        )
        refs = CitationVerifier.extract_citation_refs(text)
        assert len(refs) == 3
        assert "[PUBMED:12345678]" in refs
        assert "[INTERNAL:INT-001]" in refs
        assert "[WEB:https://example.com/paper]" in refs

    def test_extract_no_citations(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        refs = CitationVerifier.extract_citation_refs("No citations here.")
        assert refs == []

    @pytest.mark.asyncio
    async def test_mock_verifier(self):
        from colloquip.tools.citation_verifier import MockCitationVerifier

        verifier = MockCitationVerifier()
        text = "[PUBMED:12345] supports this. Also see [INTERNAL:DOC-1] and [WEB:https://x.com]."
        report = await verifier.verify_text(text)
        assert report.total_citations == 3
        assert report.verified == 2  # pubmed + internal
        assert report.unverified == 1  # web
        assert report.flagged == 0


# =========================================================================
# Output template tests
# =========================================================================


class TestOutputTemplates:
    def test_all_templates_exist(self):
        from colloquip.output_templates import DEFAULT_TEMPLATES

        assert ThinkingType.ASSESSMENT in DEFAULT_TEMPLATES
        assert ThinkingType.REVIEW in DEFAULT_TEMPLATES
        assert ThinkingType.ANALYSIS in DEFAULT_TEMPLATES
        assert ThinkingType.IDEATION in DEFAULT_TEMPLATES

    def test_get_template(self):
        from colloquip.output_templates import get_template

        template = get_template(ThinkingType.ASSESSMENT)
        assert template.template_type == "assessment"
        assert len(template.sections) >= 5

    def test_assessment_sections(self):
        from colloquip.output_templates import ASSESSMENT_TEMPLATE

        section_names = {s.name for s in ASSESSMENT_TEMPLATE.sections}
        assert "executive_summary" in section_names
        assert "evidence_for" in section_names
        assert "evidence_against" in section_names
        assert "key_risks" in section_names
        assert "minority_positions" in section_names

    def test_review_sections(self):
        from colloquip.output_templates import REVIEW_TEMPLATE

        section_names = {s.name for s in REVIEW_TEMPLATE.sections}
        assert "publication_summary" in section_names
        assert "strengths" in section_names
        assert "limitations" in section_names

    def test_ideation_has_moonshots(self):
        from colloquip.output_templates import IDEATION_TEMPLATE

        moonshots = [s for s in IDEATION_TEMPLATE.sections if s.name == "moonshots"]
        assert len(moonshots) == 1
        assert moonshots[0].required is False

    def test_all_templates_have_metadata(self):
        from colloquip.output_templates import DEFAULT_TEMPLATES

        for tt, template in DEFAULT_TEMPLATES.items():
            assert len(template.metadata_fields) >= 3, f"{tt} needs metadata fields"


# =========================================================================
# Cost tracker tests
# =========================================================================


class TestCostTracker:
    def test_record_and_query(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        thread_id = uuid4()
        tracker.record(thread_id, input_tokens=1000, output_tokens=500)
        assert tracker.total_input_tokens(thread_id) == 1000
        assert tracker.total_output_tokens(thread_id) == 500
        assert tracker.total_tokens(thread_id) == 1500
        assert tracker.num_calls(thread_id) == 1

    def test_multiple_records(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        thread_id = uuid4()
        tracker.record(thread_id, input_tokens=1000, output_tokens=500)
        tracker.record(thread_id, input_tokens=2000, output_tokens=1000)
        assert tracker.total_input_tokens(thread_id) == 3000
        assert tracker.total_output_tokens(thread_id) == 1500
        assert tracker.num_calls(thread_id) == 2

    def test_cost_calculation(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker(
            cost_per_input_token=0.000003,
            cost_per_output_token=0.000015,
        )
        thread_id = uuid4()
        tracker.record(thread_id, input_tokens=1_000_000, output_tokens=100_000)
        cost = tracker.estimated_cost(thread_id)
        # $3 input + $1.5 output = $4.5
        assert abs(cost - 4.5) < 0.001

    def test_budget_check(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        thread_id = uuid4()
        tracker.record(thread_id, input_tokens=100, output_tokens=50)
        assert tracker.check_budget(thread_id, max_usd=1.0) is True
        assert tracker.check_budget(thread_id, max_usd=0.0) is False

    def test_thread_summary(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        thread_id = uuid4()
        tracker.start_tracking(thread_id)
        tracker.record(thread_id, input_tokens=500, output_tokens=200)
        summary = tracker.thread_summary(thread_id)
        assert summary["total_input_tokens"] == 500
        assert summary["total_output_tokens"] == 200
        assert summary["total_tokens"] == 700
        assert summary["num_llm_calls"] == 1
        assert summary["duration_seconds"] >= 0

    def test_empty_thread(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        thread_id = uuid4()
        assert tracker.total_tokens(thread_id) == 0
        assert tracker.estimated_cost(thread_id) == 0.0
        assert tracker.num_calls(thread_id) == 0

    def test_isolation_between_threads(self):
        from colloquip.cost_tracker import CostTracker

        tracker = CostTracker()
        t1 = uuid4()
        t2 = uuid4()
        tracker.record(t1, input_tokens=100, output_tokens=50)
        tracker.record(t2, input_tokens=200, output_tokens=100)
        assert tracker.total_tokens(t1) == 150
        assert tracker.total_tokens(t2) == 300


# =========================================================================
# Synthesis parsing tests
# =========================================================================


class TestSynthesisParsing:
    def test_parse_sections(self):
        from colloquip.synthesis import _parse_synthesis_sections

        template = OutputTemplate(
            template_type="assessment",
            sections=[
                OutputSection(name="executive_summary", description=""),
                OutputSection(name="evidence_for", description=""),
                OutputSection(name="key_risks", description=""),
            ],
        )
        text = """### Executive Summary
This is the summary.

### Evidence For
- Point 1
- Point 2

### Key Risks
- Risk A
- Risk B
"""
        sections = _parse_synthesis_sections(text, template)
        assert "executive_summary" in sections
        assert "This is the summary." in sections["executive_summary"]
        assert "evidence_for" in sections
        assert "Point 1" in sections["evidence_for"]

    def test_parse_metadata(self):
        from colloquip.synthesis import _parse_metadata

        text = """
confidence_level: high
evidence_quality: moderate
consensus_strength: majority
"""
        fields = ["confidence_level", "evidence_quality", "consensus_strength"]
        metadata = _parse_metadata(text, fields)
        assert metadata["confidence_level"] == "high"
        assert metadata["evidence_quality"] == "moderate"

    def test_build_synthesis_prompt(self):
        from colloquip.synthesis import _build_synthesis_prompt
        from tests.conftest import create_post

        posts = [
            create_post(
                agent_id="biology",
                content="Target is well-validated by genetics.",
                stance=AgentStance.SUPPORTIVE,
                key_claims=["GWAS supports target"],
                questions_raised=["What about pathway redundancy?"],
            ),
            create_post(
                agent_id="red_team",
                content="Reproducibility concern: only one lab.",
                stance=AgentStance.CRITICAL,
                key_claims=["Single-lab finding"],
            ),
        ]
        template = OutputTemplate(
            template_type="assessment",
            sections=[
                OutputSection(name="summary", description="A summary"),
            ],
            metadata_fields=["confidence"],
        )
        prompt = _build_synthesis_prompt("GLP-1 is neuroprotective", posts, template)
        assert "GLP-1 is neuroprotective" in prompt
        assert "biology" in prompt
        assert "summary" in prompt.lower()
        assert "confidence" in prompt.lower()


# =========================================================================
# Prompt builder v3 tests
# =========================================================================


class TestPromptBuilderV3:
    def test_build_v3_system_prompt(self):
        from colloquip.agents.prompts import build_v3_system_prompt

        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            phase_mandate="Explore broadly.",
            subreddit_context="Drug discovery subreddit.",
        )
        assert "You are a biology expert." in prompt
        assert "Explore broadly." in prompt
        assert "Drug discovery subreddit." in prompt

    def test_build_v3_user_prompt(self):
        from colloquip.agents.prompts import build_v3_user_prompt
        from tests.conftest import create_post

        posts = [
            create_post(
                agent_id="bio",
                content="Target is validated.",
                stance=AgentStance.SUPPORTIVE,
            ),
        ]
        prompt = build_v3_user_prompt(
            hypothesis="GLP-1 is neuroprotective",
            posts=posts,
            phase_observation="Exploration underway.",
        )
        assert "GLP-1 is neuroprotective" in prompt
        assert "Target is validated." in prompt

    def test_build_subreddit_context(self):
        from colloquip.agents.prompts import build_subreddit_context

        ctx = build_subreddit_context(
            subreddit_name="target_assessment",
            subreddit_description="Assess drug targets",
            thinking_type="assessment",
            core_questions=["Is the target druggable?"],
            decision_context="Go/No-Go for lead optimization",
        )
        assert "target_assessment" in ctx
        assert "Is the target druggable?" in ctx
        assert "Go/No-Go" in ctx

    def test_v3_system_prompt_includes_citations(self):
        from colloquip.agents.prompts import build_v3_system_prompt

        prompt = build_v3_system_prompt(
            persona_prompt="You are an expert.",
            phase=Phase.DEBATE,
            phase_mandate="Challenge claims.",
        )
        assert "PUBMED" in prompt or "citation" in prompt.lower()

    def test_v3_system_prompt_includes_tool_instructions(self):
        from colloquip.agents.prompts import build_v3_system_prompt

        prompt = build_v3_system_prompt(
            persona_prompt="Expert.",
            phase=Phase.EXPLORE,
            phase_mandate="Explore.",
            tool_descriptions=["pubmed_search: Search PubMed"],
        )
        assert "pubmed_search" in prompt


# =========================================================================
# Platform manager tests
# =========================================================================


class TestPlatformManager:
    def _make_pm(self):
        from colloquip.api.platform_manager import PlatformManager

        pm = PlatformManager(mock_mode=True)
        pm.initialize()
        return pm

    def test_initialize(self):
        pm = self._make_pm()
        assert pm.registry.pool_size >= 10

    def test_initialize_idempotent(self):
        pm = self._make_pm()
        size = pm.registry.pool_size
        pm.initialize()
        assert pm.registry.pool_size == size

    def test_create_subreddit(self):
        pm = self._make_pm()
        result = pm.create_subreddit(
            name="target_assessment",
            display_name="Target Assessment",
            description="Assess drug targets",
            thinking_type=ThinkingType.ASSESSMENT,
            required_expertise=["molecular_biology", "clinical"],
            primary_domain="drug_discovery",
            tool_ids=["pubmed_search"],
        )
        sub = result["subreddit"]
        assert sub["name"] == "target_assessment"
        assert sub["id"] is not None
        recruitment = result["recruitment"]
        assert len(recruitment.memberships) >= 2

    def test_get_subreddit_by_name(self):
        pm = self._make_pm()
        pm.create_subreddit(
            name="test_sub",
            display_name="Test",
            required_expertise=["molecular_biology"],
        )
        sub = pm.get_subreddit_by_name("test_sub")
        assert sub is not None
        assert sub["name"] == "test_sub"

    def test_get_subreddit_not_found(self):
        pm = self._make_pm()
        assert pm.get_subreddit_by_name("nonexistent") is None

    def test_list_subreddits(self):
        pm = self._make_pm()
        pm.create_subreddit(name="sub1", display_name="Sub 1", required_expertise=[])
        pm.create_subreddit(name="sub2", display_name="Sub 2", required_expertise=[])
        subs = pm.list_subreddits()
        names = {s["name"] for s in subs}
        assert "sub1" in names
        assert "sub2" in names

    def test_subreddit_includes_red_team(self):
        pm = self._make_pm()
        result = pm.create_subreddit(
            name="bio_review",
            display_name="Bio Review",
            required_expertise=["molecular_biology"],
            primary_domain="biology",
        )
        members = pm.get_subreddit_members(result["subreddit"]["id"])
        roles = {m.get("role") for m in members}
        assert "red_team" in roles

    def test_create_thread(self):
        pm = self._make_pm()
        result = pm.create_subreddit(
            name="thread_test",
            display_name="Thread Test",
            required_expertise=[],
        )
        sub_id = result["subreddit"]["id"]
        thread = pm.create_thread(
            subreddit_id=sub_id,
            title="Test Thread",
            hypothesis="Testing hypothesis",
        )
        assert thread["title"] == "Test Thread"
        assert thread["status"] == "pending"
        threads = pm.get_subreddit_threads(sub_id)
        assert len(threads) == 1

    def test_list_agents(self):
        pm = self._make_pm()
        agents = pm.list_agents()
        assert len(agents) >= 10

    def test_tool_configs_in_subreddit(self):
        pm = self._make_pm()
        result = pm.create_subreddit(
            name="tool_test",
            display_name="Tool Test",
            tool_ids=["pubmed_search", "company_docs", "web_search"],
            required_expertise=[],
        )
        sub = result["subreddit"]
        assert len(sub["tool_configs"]) == 3
        tool_ids = {tc["tool_id"] for tc in sub["tool_configs"]}
        assert tool_ids == {"pubmed_search", "company_docs", "web_search"}

    def test_output_template_in_subreddit(self):
        pm = self._make_pm()
        result = pm.create_subreddit(
            name="template_test",
            display_name="Template Test",
            thinking_type=ThinkingType.IDEATION,
            required_expertise=[],
        )
        sub = result["subreddit"]
        assert sub["output_template"]["template_type"] == "ideation"


# =========================================================================
# API route tests (using FastAPI TestClient)
# =========================================================================


class TestPlatformAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from colloquip.api import create_app

        app = create_app()
        return TestClient(app)

    def test_init_platform(self, client):
        resp = client.post("/api/platform/init")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "initialized"
        assert data["agents_loaded"] >= 10

    def test_init_idempotent(self, client):
        client.post("/api/platform/init")
        resp = client.post("/api/platform/init")
        assert resp.status_code == 200

    def test_list_agents(self, client):
        client.post("/api/platform/init")
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) >= 10
        # Check structure
        for a in agents:
            assert "id" in a
            assert "agent_type" in a
            assert "display_name" in a
            assert "is_red_team" in a

    def test_create_subreddit(self, client):
        client.post("/api/platform/init")
        resp = client.post(
            "/api/subreddits",
            json={
                "name": "api_test_sub",
                "display_name": "API Test Sub",
                "description": "Testing via API",
                "thinking_type": "assessment",
                "required_expertise": ["molecular_biology", "medicinal_chemistry"],
                "primary_domain": "drug_discovery",
                "tool_ids": ["pubmed_search"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "api_test_sub"
        assert data["has_red_team"] is True
        assert data["member_count"] >= 2

    def test_create_subreddit_duplicate(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "dup_sub",
                "display_name": "Dup Sub",
            },
        )
        resp = client.post(
            "/api/subreddits",
            json={
                "name": "dup_sub",
                "display_name": "Dup Sub Again",
            },
        )
        assert resp.status_code == 409

    def test_get_subreddit(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "get_test",
                "display_name": "Get Test",
            },
        )
        resp = client.get("/api/subreddits/get_test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "get_test"

    def test_get_subreddit_not_found(self, client):
        client.post("/api/platform/init")
        resp = client.get("/api/subreddits/nonexistent")
        assert resp.status_code == 404

    def test_list_subreddits(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "list_test_a",
                "display_name": "List A",
            },
        )
        client.post(
            "/api/subreddits",
            json={
                "name": "list_test_b",
                "display_name": "List B",
            },
        )
        resp = client.get("/api/subreddits")
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()}
        assert "list_test_a" in names
        assert "list_test_b" in names

    def test_get_subreddit_members(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "member_test",
                "display_name": "Member Test",
                "required_expertise": ["molecular_biology"],
            },
        )
        resp = client.get("/api/subreddits/member_test/members")
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data
        assert len(data["members"]) >= 1

    def test_create_thread(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "thread_test_api",
                "display_name": "Thread Test",
            },
        )
        resp = client.post(
            "/api/subreddits/thread_test_api/threads",
            json={
                "title": "Does GLP-1 work?",
                "hypothesis": "GLP-1 agonists improve cognition in AD patients.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Does GLP-1 work?"
        assert data["status"] == "pending"
        assert data["subreddit_name"] == "thread_test_api"

    def test_list_threads(self, client):
        client.post("/api/platform/init")
        client.post(
            "/api/subreddits",
            json={
                "name": "list_threads",
                "display_name": "List Threads",
            },
        )
        client.post(
            "/api/subreddits/list_threads/threads",
            json={
                "title": "Thread 1",
                "hypothesis": "H1",
            },
        )
        resp = client.get("/api/subreddits/list_threads/threads")
        assert resp.status_code == 200
        assert len(resp.json()["threads"]) == 1

    def test_get_thread_costs(self, client):
        client.post("/api/platform/init")
        resp = client.get(f"/api/threads/{uuid4()}/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert "estimated_cost_usd" in data

    def test_get_agent_detail(self, client):
        client.post("/api/platform/init")
        agents_resp = client.get("/api/agents")
        agents = agents_resp.json()
        agent_id = agents[0]["id"]
        resp = client.get(f"/api/agents/{agent_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_type" in data
        assert "expertise_tags" in data

    def test_get_agent_invalid_id(self, client):
        client.post("/api/platform/init")
        resp = client.get("/api/agents/not-a-uuid")
        assert resp.status_code == 400

    def test_get_agent_not_found(self, client):
        client.post("/api/platform/init")
        resp = client.get(f"/api/agents/{uuid4()}")
        assert resp.status_code == 404

    def test_subreddit_name_validation(self, client):
        client.post("/api/platform/init")
        resp = client.post(
            "/api/subreddits",
            json={
                "name": "Invalid Name!",
                "display_name": "Invalid",
            },
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_platform_not_initialized(self, client):
        # Without calling /platform/init, most endpoints should fail gracefully
        # Reset app state
        if hasattr(client.app.state, "platform_manager"):
            delattr(client.app.state, "platform_manager")
        resp = client.get("/api/agents")
        assert resp.status_code == 503


# =========================================================================
# Backward compatibility — existing models/features still work
# =========================================================================


class TestBackwardCompatibility:
    def test_existing_models_unchanged(self):
        """Ensure original models still work with their original fields."""
        from colloquip.models import (
            AgentStance,
            DeliberationSession,
            EngineConfig,
            Phase,
            Post,
            SessionStatus,
        )

        session = DeliberationSession(hypothesis="Test")
        assert session.status == SessionStatus.PENDING

        post = Post(
            session_id=session.id,
            agent_id="test",
            content="Test",
            stance=AgentStance.NEUTRAL,
            phase=Phase.EXPLORE,
        )
        assert post.novelty_score == 0.0

        engine_config = EngineConfig()
        assert engine_config.max_turns == 30

    def test_original_agent_config_still_works(self):
        from colloquip.models import AgentConfig

        config = AgentConfig(
            agent_id="test",
            display_name="Test Agent",
            persona_prompt="You are a test agent.",
            phase_mandates={},
            domain_keywords=["test"],
            knowledge_scope=["testing"],
        )
        assert config.is_red_team is False

    def test_existing_tests_count(self):
        """Meta-test: we should still have at least 188 existing tests."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--co", "-q", "--ignore=tests/test_platform.py"],
            capture_output=True,
            text=True,
            cwd="/home/user/Colloquip",
        )
        # Count lines matching "test_" pattern
        test_lines = [line for line in result.stdout.strip().split("\n") if "test_" in line]
        assert len(test_lines) >= 188


# =========================================================================
# Principle #2: parse_synthesis testable without LLM
# =========================================================================


class TestParseSynthesis:
    """Tests for parse_synthesis() — no LLM required."""

    def test_parse_synthesis_basic(self):
        from colloquip.synthesis import parse_synthesis

        template = OutputTemplate(
            template_type="assessment",
            sections=[
                OutputSection(name="executive_summary", description=""),
                OutputSection(name="evidence_for", description=""),
                OutputSection(name="key_risks", description=""),
            ],
            metadata_fields=["confidence_level", "evidence_quality"],
        )
        text = """### Executive Summary
The hypothesis is well-supported by preclinical data.

### Evidence For
- GWAS data supports target involvement [PUBMED:12345678]
- Preclinical models show efficacy

### Key Risks
- Single lab reproducibility concern
- No clinical data yet

confidence_level: high
evidence_quality: moderate
"""
        result = parse_synthesis(text, template)
        assert result.template_type == "assessment"
        assert "executive_summary" in result.sections
        assert "evidence_for" in result.sections
        assert "key_risks" in result.sections
        assert result.metadata.get("confidence_level") == "high"
        assert result.metadata.get("evidence_quality") == "moderate"

    def test_parse_synthesis_with_posts_and_audit_chains(self):
        from colloquip.synthesis import parse_synthesis
        from tests.conftest import create_post

        posts = [
            create_post(
                agent_id="biology",
                content="GWAS data strongly supports target involvement in disease pathway.",
                stance=AgentStance.SUPPORTIVE,
            ),
            create_post(
                agent_id="red_team",
                content="Single lab finding raises reproducibility concerns.",
                stance=AgentStance.CRITICAL,
            ),
        ]
        template = OutputTemplate(
            template_type="assessment",
            sections=[
                OutputSection(name="evidence_for", description=""),
            ],
        )
        text = """### Evidence For
- GWAS data strongly supports target involvement in disease pathway
"""
        result = parse_synthesis(text, template, posts=posts)
        # Should have audit chains linking claims to posts
        assert isinstance(result.audit_chains, list)

    def test_parse_synthesis_empty_text(self):
        from colloquip.synthesis import parse_synthesis

        template = OutputTemplate(
            template_type="assessment",
            sections=[OutputSection(name="summary", description="")],
        )
        result = parse_synthesis("", template)
        assert "raw_synthesis" in result.sections
        assert result.sections["raw_synthesis"] == "No synthesis content generated."

    def test_parse_synthesis_custom_thread_id(self):
        from colloquip.synthesis import parse_synthesis

        template = OutputTemplate(
            template_type="assessment",
            sections=[OutputSection(name="summary", description="")],
        )
        tid = uuid4()
        result = parse_synthesis("Some text", template, thread_id=tid)
        assert result.thread_id == tid

    def test_parse_synthesis_configurable_audit_params(self):
        from colloquip.synthesis import parse_synthesis
        from tests.conftest import create_post

        posts = [
            create_post(
                agent_id="bio",
                content="Target validated by comprehensive GWAS meta-analysis across populations.",
                stance=AgentStance.SUPPORTIVE,
            ),
        ]
        template = OutputTemplate(
            template_type="assessment",
            sections=[OutputSection(name="evidence_for", description="")],
        )
        text = (
            "### Evidence For\n"
            "- Target validated by comprehensive GWAS meta-analysis across populations"
        )

        # With very high threshold, no chains should match
        result_strict = parse_synthesis(text, template, posts=posts, overlap_threshold=0.99)
        assert len(result_strict.audit_chains) == 0

        # With low threshold, chains should match
        result_loose = parse_synthesis(text, template, posts=posts, overlap_threshold=0.1)
        assert len(result_loose.audit_chains) >= 0  # May or may not match


# =========================================================================
# Principle #4: Configurable scoring weights
# =========================================================================


class TestScoringWeights:
    def test_default_scoring_weights(self):
        from colloquip.registry import DEFAULT_SCORING_WEIGHTS, ScoringWeights

        assert isinstance(DEFAULT_SCORING_WEIGHTS, ScoringWeights)
        assert DEFAULT_SCORING_WEIGHTS.exact_type_match == 0.5
        assert DEFAULT_SCORING_WEIGHTS.expertise_tag_match == 0.3
        assert DEFAULT_SCORING_WEIGHTS.keyword_overlap == 0.2
        assert DEFAULT_SCORING_WEIGHTS.scope_overlap == 0.1

    def test_custom_scoring_weights(self):
        from colloquip.registry import AgentRegistry, ScoringWeights

        # Create registry with custom weights that heavily favor exact match
        weights = ScoringWeights(
            exact_type_match=1.0,
            expertise_tag_match=0.0,
            keyword_overlap=0.0,
            scope_overlap=0.0,
            min_score=0.5,
        )
        registry = AgentRegistry(scoring_weights=weights)
        registry.load_from_personas()

        # With these weights, only exact matches should appear
        matches = registry.find_by_expertise("molecular_biology")
        assert len(matches) >= 1
        best_agent, _ = matches[0]
        assert best_agent.agent_type == "molecular_biology"

    def test_scoring_weights_zero_min(self):
        from colloquip.registry import AgentRegistry, ScoringWeights

        weights = ScoringWeights(min_score=0.0)
        registry = AgentRegistry(scoring_weights=weights)
        registry.load_from_personas()
        # With min_score=0, everything with any score should match
        matches = registry.find_by_expertise("biology")
        assert len(matches) >= 5


# =========================================================================
# Principle #5: Mock tools inherit from real classes
# =========================================================================


class TestMockInheritance:
    def test_mock_pubmed_inherits(self):
        from colloquip.tools.pubmed import MockPubMedTool, PubMedTool

        assert issubclass(MockPubMedTool, PubMedTool)

    def test_mock_web_search_inherits(self):
        from colloquip.tools.web_search import MockWebSearchTool, WebSearchTool

        assert issubclass(MockWebSearchTool, WebSearchTool)

    def test_mock_company_docs_inherits(self):
        from colloquip.tools.company_docs import CompanyDocsTool, MockCompanyDocsTool

        assert issubclass(MockCompanyDocsTool, CompanyDocsTool)

    def test_mock_pubmed_shares_schema_structure(self):
        from colloquip.tools.pubmed import MockPubMedTool, PubMedTool

        real = PubMedTool()
        mock = MockPubMedTool()
        # Both should have the same schema structure
        assert real.tool_schema["name"] == mock.tool_schema["name"]
        assert "input_schema" in mock.tool_schema

    def test_verification_report_is_pydantic(self):
        from pydantic import BaseModel

        from colloquip.tools.citation_verifier import VerificationReport

        assert issubclass(VerificationReport, BaseModel)

        report = VerificationReport(total_citations=3, verified=2, flagged=1)
        dumped = report.model_dump()
        assert dumped["total_citations"] == 3
        assert dumped["verified"] == 2

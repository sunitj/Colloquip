"""Tests for Anthropic Claude adapter response parsing."""

import pytest

from colloquip.llm.anthropic import parse_agent_response, _extract_list_items
from colloquip.models import AgentStance


class TestExtractListItems:
    def test_bullet_list(self):
        text = "- First item\n- Second item\n- Third item"
        items = _extract_list_items(text)
        assert items == ["First item", "Second item", "Third item"]

    def test_star_list(self):
        text = "* Item A\n* Item B"
        items = _extract_list_items(text)
        assert items == ["Item A", "Item B"]

    def test_empty_string(self):
        assert _extract_list_items("") == []

    def test_no_bullets(self):
        assert _extract_list_items("Just text here") == []

    def test_numbered_list_dot(self):
        text = "1. First item\n2. Second item\n3. Third item"
        items = _extract_list_items(text)
        assert items == ["First item", "Second item", "Third item"]

    def test_numbered_list_paren(self):
        text = "1) Item A\n2) Item B"
        items = _extract_list_items(text)
        assert items == ["Item A", "Item B"]

    def test_mixed_list_formats(self):
        text = "- Bullet item\n1. Numbered item\n* Star item"
        items = _extract_list_items(text)
        assert len(items) == 3


class TestParseAgentResponse:
    def test_full_structured_response(self):
        raw = (
            "This is my analysis of the hypothesis.\n\n"
            "**Stance**: SUPPORTIVE\n\n"
            "**Key Claims**:\n"
            "- The mechanism is well-established\n"
            "- Preclinical data supports the hypothesis\n\n"
            "**Questions Raised**:\n"
            "- What about dose-response?\n"
            "- Are there off-target effects?\n\n"
            "**Connections Identified**:\n"
            "- Link between target and safety profile\n"
        )
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.SUPPORTIVE
        assert len(result.key_claims) == 2
        assert "mechanism" in result.key_claims[0].lower()
        assert len(result.questions_raised) == 2
        assert len(result.connections_identified) == 1

    def test_critical_stance(self):
        raw = "**Stance**: CRITICAL\n\nSome content here."
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.CRITICAL
        assert result.novelty_score == 0.6  # Critical gets higher novelty

    def test_novel_connection_stance(self):
        raw = "**Stance**: NOVEL_CONNECTION\n\nSome content here."
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.NOVEL_CONNECTION
        assert result.novelty_score == 0.8

    def test_missing_stance_defaults_neutral(self):
        raw = "Just some analysis without structured sections."
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.NEUTRAL
        assert result.novelty_score == 0.5

    def test_case_insensitive_stance(self):
        raw = "**Stance**: supportive"
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.SUPPORTIVE

    def test_partial_response(self):
        raw = (
            "Analysis here.\n\n"
            "**Stance**: NEUTRAL\n\n"
            "**Key Claims**:\n"
            "- One claim\n"
        )
        result = parse_agent_response(raw)
        assert result.stance == AgentStance.NEUTRAL
        assert len(result.key_claims) == 1
        assert result.questions_raised == []
        assert result.connections_identified == []

    def test_content_preserved(self):
        raw = "Full response content here.\n\n**Stance**: SUPPORTIVE"
        result = parse_agent_response(raw)
        assert "Full response content" in result.content

    def test_claims_capped_at_five(self):
        claims = "\n".join(f"- Claim {i}" for i in range(10))
        raw = f"**Key Claims**:\n{claims}\n\n**Stance**: NEUTRAL"
        result = parse_agent_response(raw)
        assert len(result.key_claims) <= 5

    def test_questions_capped_at_three(self):
        questions = "\n".join(f"- Question {i}?" for i in range(10))
        raw = f"**Questions Raised**:\n{questions}\n\n**Stance**: NEUTRAL"
        result = parse_agent_response(raw)
        assert len(result.questions_raised) <= 3

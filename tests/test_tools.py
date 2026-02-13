"""Tests for tool modules: citation_verifier, company_docs, web_search.

Mocks external APIs. Covers parsing, error handling, and edge cases.
See tests/TEST_STRATEGY.md for conventions.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# =========================================================================
# Citation Verifier
# =========================================================================


class TestCitationExtraction:
    def test_extract_pubmed_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        text = "See [PUBMED:12345] and [PUBMED:67890] for details."
        refs = CitationVerifier.extract_citation_refs(text)
        assert "[PUBMED:12345]" in refs
        assert "[PUBMED:67890]" in refs
        assert len(refs) == 2

    def test_extract_internal_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        text = "See [INTERNAL:report-2024] and [INTERNAL:data_v2]."
        refs = CitationVerifier.extract_citation_refs(text)
        assert "[INTERNAL:report-2024]" in refs
        assert "[INTERNAL:data_v2]" in refs

    def test_extract_web_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        text = "Reference [WEB:https://example.com/paper] for more."
        refs = CitationVerifier.extract_citation_refs(text)
        assert "[WEB:https://example.com/paper]" in refs

    def test_extract_mixed_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        text = "[PUBMED:111] [INTERNAL:abc] [WEB:https://x.com/y] plain text."
        refs = CitationVerifier.extract_citation_refs(text)
        assert len(refs) == 3

    def test_extract_no_refs(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        refs = CitationVerifier.extract_citation_refs("No citations here.")
        assert refs == []


class TestCitationVerify:
    async def test_verify_text_no_citations(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        verifier = CitationVerifier()
        report = await verifier.verify_text("No citations in this text.")
        assert report.total_citations == 0
        assert report.verified == 0

    async def test_verify_text_internal_marked_unverified(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        verifier = CitationVerifier()
        report = await verifier.verify_text("See [INTERNAL:abc123].")
        assert report.total_citations == 1
        assert report.unverified == 1
        assert report.details[0]["status"] == "unverified"

    async def test_verify_text_web_marked_unverified(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        verifier = CitationVerifier()
        report = await verifier.verify_text("See [WEB:https://example.com].")
        assert report.total_citations == 1
        assert report.unverified == 1

    async def test_verify_pmid_success(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"12345": {"title": "GLP-1 and Cognition", "error": ""}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            verifier = CitationVerifier()
            report = await verifier.verify_text("[PUBMED:12345]")

        assert report.verified == 1
        assert report.flagged == 0
        assert report.details[0]["status"] == "verified"

    async def test_verify_pmid_not_found(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            verifier = CitationVerifier()
            report = await verifier.verify_text("[PUBMED:99999]")

        assert report.flagged == 1
        assert report.details[0]["status"] == "flagged"

    async def test_verify_pmid_api_error(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("API timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            verifier = CitationVerifier()
            report = await verifier.verify_text("[PUBMED:12345]")

        assert report.flagged == 1

    async def test_verify_pmid_with_error_field(self):
        from colloquip.tools.citation_verifier import CitationVerifier

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"12345": {"title": "", "error": "PMID retracted"}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            verifier = CitationVerifier()
            report = await verifier.verify_text("[PUBMED:12345]")

        assert report.flagged == 1
        assert "retracted" in report.details[0]["reason"].lower()


class TestMockCitationVerifier:
    async def test_mock_verifies_pubmed(self):
        from colloquip.tools.citation_verifier import MockCitationVerifier

        verifier = MockCitationVerifier()
        report = await verifier.verify_text("[PUBMED:12345] and [INTERNAL:abc]")
        assert report.verified == 2  # Both pubmed + internal verified in mock
        assert report.total_citations == 2


# =========================================================================
# Company Docs Tool
# =========================================================================


class TestCompanyDocsTool:
    async def test_empty_query(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        tool = CompanyDocsTool(doc_path="/tmp/nonexistent")
        result = await tool.execute(query="")
        assert result.error == "Empty query"

    async def test_no_doc_path(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        tool = CompanyDocsTool(doc_path=None)
        result = await tool.execute(query="GLP-1")
        assert "not configured" in result.error

    async def test_nonexistent_path(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        tool = CompanyDocsTool(doc_path="/tmp/nonexistent_dir_12345")
        result = await tool.execute(query="GLP-1")
        assert "not configured" in result.error or "does not exist" in result.error

    async def test_search_files_with_matches(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "glp1_study.md").write_text(
                "# GLP-1 Study\n\nThis study found that GLP-1 receptor agonists "
                "improve cognition in mouse models.\n"
            )
            Path(tmpdir, "unrelated.txt").write_text(
                "This file is about something unrelated to the query."
            )

            tool = CompanyDocsTool(doc_path=tmpdir, max_results=5)
            result = await tool.execute(query="GLP-1 cognition")

            assert result.error is None
            assert len(result.results) >= 1
            assert "Glp1 Study" in result.results[0].title

    async def test_search_files_no_matches(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "other.md").write_text("Nothing relevant here.")

            tool = CompanyDocsTool(doc_path=tmpdir)
            result = await tool.execute(query="xyznonexistent12345")

            assert result.error is None
            assert len(result.results) == 0

    async def test_snippet_extraction(self):
        from colloquip.tools.company_docs import CompanyDocsTool

        tool = CompanyDocsTool(doc_path="/tmp")
        content = "A " * 100 + "GLP-1 receptor agonist data here." + " B" * 100
        snippet = tool._extract_snippet(content, {"glp-1", "receptor"})
        assert "GLP-1" in snippet or "glp-1" in snippet.lower()

    async def test_mock_company_docs(self):
        from colloquip.tools.company_docs import MockCompanyDocsTool

        tool = MockCompanyDocsTool()
        result = await tool.execute(query="GLP-1 selectivity")
        assert len(result.results) == 2
        assert "GLP-1" in result.results[0].title


# =========================================================================
# Web Search Tool
# =========================================================================


class TestWebSearchTool:
    async def test_empty_query(self):
        from colloquip.tools.web_search import WebSearchTool

        tool = WebSearchTool()
        result = await tool.execute(query="")
        assert result.error == "Empty query"

    async def test_successful_search(self):
        from colloquip.tools.web_search import WebSearchTool

        mock_data = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "GLP-1 and Neuroprotection",
                    "abstract": "This study examines GLP-1 receptor agonists...",
                    "authors": [{"name": "Smith J"}, {"name": "Doe A"}],
                    "year": 2024,
                    "externalIds": {"DOI": "10.1234/test", "PubMed": "12345"},
                    "url": "https://semanticscholar.org/paper/abc123",
                    "citationCount": 42,
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool()
            result = await tool.execute(query="GLP-1 neuroprotection")

        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "GLP-1 and Neuroprotection"
        assert result.results[0].doi == "10.1234/test"
        assert result.results[0].source_id == "12345"  # PMID preferred
        assert result.results[0].authors == ["Smith J", "Doe A"]

    async def test_search_missing_fields(self):
        from colloquip.tools.web_search import WebSearchTool

        mock_data = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Paper Without Details",
                    "abstract": None,
                    "authors": [],
                    "year": None,
                    "externalIds": None,
                    "url": "",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool()
            result = await tool.execute(query="GLP-1")

        assert result.error is None
        assert len(result.results) == 1
        paper = result.results[0]
        assert paper.title == "Paper Without Details"
        assert paper.doi == ""
        assert paper.authors == []
        assert paper.source_id == "abc123"  # Falls back to paperId

    async def test_search_api_error(self):
        from colloquip.tools.web_search import WebSearchTool

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool()
            result = await tool.execute(query="GLP-1")

        assert result.error is not None
        assert "Network error" in result.error

    async def test_truncated_flag(self):
        from colloquip.tools.web_search import WebSearchTool

        papers = [
            {
                "paperId": f"id{i}",
                "title": f"Paper {i}",
                "abstract": f"Abstract {i}",
                "authors": [],
                "year": 2024,
                "externalIds": {},
                "url": "",
            }
            for i in range(3)
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": papers}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            tool = WebSearchTool(max_results=3)
            result = await tool.execute(query="GLP-1", max_results=3)

        assert result.truncated is True

    async def test_mock_web_search(self):
        from colloquip.tools.web_search import MockWebSearchTool

        tool = MockWebSearchTool()
        result = await tool.execute(query="GLP-1 cognition")
        assert len(result.results) == 1
        assert "GLP-1 cognition" in result.results[0].title

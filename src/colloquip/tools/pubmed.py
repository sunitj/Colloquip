"""PubMed literature search tool using NCBI E-utilities API."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)

# NCBI E-utilities base URL
_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_DEFAULT_MAX_RESULTS = 5
_RATE_LIMIT_DELAY = 0.34  # ~3 requests/sec without API key


class PubMedTool(BaseSearchTool):
    """Search PubMed for relevant literature via NCBI E-utilities.

    Uses the esearch → efetch pipeline:
    1. esearch: search for PMIDs matching a query
    2. efetch: retrieve abstracts for those PMIDs
    """

    _name = "pubmed_search"
    _description = (
        "Search PubMed for peer-reviewed biomedical literature. "
        "Returns titles, authors, abstracts, and PMIDs for relevant papers."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: int = _DEFAULT_MAX_RESULTS,
        email: Optional[str] = None,
    ):
        self.api_key = api_key
        self.max_results = max_results
        self.email = email
        self._last_request_time = 0.0

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "PubMed search query. Use MeSH terms and boolean "
                            "operators for best results. Example: "
                            "'GLP-1 receptor agonist AND Alzheimer disease'"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-10)",
                        "default": self.max_results,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Search PubMed and return structured results."""
        query = kwargs.get("query", "")
        max_results = min(kwargs.get("max_results", self.max_results), 10)

        if not query:
            return ToolResult(
                source="pubmed", query=query,
                error="Empty query provided",
            )

        start_time = time.monotonic()
        try:
            pmids = await self._esearch(query, max_results)
            if not pmids:
                return ToolResult(
                    source="pubmed", query=query,
                    execution_time_ms=(time.monotonic() - start_time) * 1000,
                )

            results = await self._efetch(pmids)
            return ToolResult(
                source="pubmed",
                query=query,
                results=results,
                truncated=len(pmids) >= max_results,
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            logger.error("PubMed search failed: %s", e)
            return ToolResult(
                source="pubmed", query=query,
                error=str(e),
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _esearch(self, query: str, max_results: int) -> List[str]:
        """Search PubMed for PMIDs matching query."""
        await self._rate_limit()

        try:
            import httpx
        except ImportError:
            raise ImportError("httpx is required for PubMed search: pip install httpx")

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{_EUTILS_BASE}/esearch.fcgi", params=params)
            resp.raise_for_status()
            data = resp.json()

        return data.get("esearchresult", {}).get("idlist", [])

    async def _efetch(self, pmids: List[str]) -> List[SearchResult]:
        """Fetch abstracts for a list of PMIDs."""
        await self._rate_limit()

        try:
            import httpx
        except ImportError:
            raise ImportError("httpx is required for PubMed search: pip install httpx")

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{_EUTILS_BASE}/efetch.fcgi", params=params)
            resp.raise_for_status()
            xml_text = resp.text

        return self._parse_pubmed_xml(xml_text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[SearchResult]:
        """Parse PubMed XML response into SearchResult objects."""
        results = []
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as e:
            logger.error("Failed to parse PubMed XML: %s", e)
            return results

        for article in root.findall(".//PubmedArticle"):
            try:
                result = self._parse_article(article)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning("Failed to parse article: %s", e)

        return results

    def _parse_article(self, article) -> Optional[SearchResult]:
        """Parse a single PubmedArticle element."""
        medline = article.find(".//MedlineCitation")
        if medline is None:
            return None

        pmid_el = medline.find("PMID")
        pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""

        art = medline.find(".//Article")
        if art is None:
            return None

        title_el = art.find("ArticleTitle")
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Authors
        authors = []
        for author in art.findall(".//Author"):
            last = author.find("LastName")
            fore = author.find("ForeName")
            if last is not None:
                name = last.text or ""
                if fore is not None and fore.text:
                    name = f"{fore.text} {name}"
                authors.append(name)

        # Abstract
        abstract_parts = []
        for abstract_text in art.findall(".//AbstractText"):
            if abstract_text.text:
                label = abstract_text.get("Label", "")
                if label:
                    abstract_parts.append(f"{label}: {abstract_text.text}")
                else:
                    abstract_parts.append(abstract_text.text)
        abstract = " ".join(abstract_parts)

        # Journal and year
        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""

        year = None
        year_el = art.find(".//PubDate/Year")
        if year_el is not None and year_el.text:
            try:
                year = int(year_el.text)
            except ValueError:
                pass

        # DOI
        doi = ""
        for eid in article.findall(".//ArticleId"):
            if eid.get("IdType") == "doi":
                doi = eid.text or ""
                break

        return SearchResult(
            title=title,
            authors=authors[:5],  # Cap at 5 authors
            abstract=abstract[:1000],  # Cap length
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            doi=doi,
            year=year,
            source_id=pmid,
            source_type="pubmed",
            snippet=abstract[:300] if abstract else title,
        )

    async def _rate_limit(self):
        """Simple rate limiting for NCBI compliance."""
        elapsed = time.monotonic() - self._last_request_time
        delay = _RATE_LIMIT_DELAY if not self.api_key else 0.1
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request_time = time.monotonic()


class MockPubMedTool(PubMedTool):
    """Mock PubMed tool for testing without network access.

    Inherits schema from PubMedTool; overrides execute() with canned data.
    """

    _description = "Search PubMed (mock mode)"

    def __init__(self, max_results: int = 5):
        super().__init__(max_results=max_results)

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", self.max_results)

        mock_results = [
            SearchResult(
                title=f"Evidence for {query} in preclinical models",
                authors=["Smith J", "Jones A", "Wilson B"],
                abstract=f"This study demonstrates significant findings related to {query}. "
                         f"Results from multiple preclinical models show consistent effects "
                         f"supporting further investigation.",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                doi="10.1234/mock.2024.001",
                year=2024,
                source_id="12345678",
                source_type="pubmed",
                snippet=f"Significant findings related to {query} in preclinical models.",
            ),
            SearchResult(
                title=f"Systematic review: {query} therapeutic potential",
                authors=["Brown C", "Davis M"],
                abstract=f"A systematic review of {query} across 42 studies reveals "
                         f"mixed but promising evidence. Meta-analysis indicates a "
                         f"statistically significant effect (p<0.01).",
                url="https://pubmed.ncbi.nlm.nih.gov/23456789/",
                doi="10.1234/mock.2024.002",
                year=2023,
                source_id="23456789",
                source_type="pubmed",
                snippet=f"Systematic review of {query} across 42 studies.",
            ),
            SearchResult(
                title=f"Safety and tolerability of {query}: Phase I data",
                authors=["Lee K", "Park S", "Chen W"],
                abstract=f"Phase I clinical trial evaluating {query}. "
                         f"Favorable safety profile observed with dose-dependent "
                         f"pharmacokinetic properties and no serious adverse events.",
                url="https://pubmed.ncbi.nlm.nih.gov/34567890/",
                doi="10.1234/mock.2024.003",
                year=2024,
                source_id="34567890",
                source_type="pubmed",
                snippet=f"Phase I data for {query} shows favorable safety.",
            ),
        ]

        return ToolResult(
            source="pubmed",
            query=query,
            results=mock_results[:max_results],
            execution_time_ms=150.0,
        )

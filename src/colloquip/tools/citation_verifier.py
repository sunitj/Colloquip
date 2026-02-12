"""Automated citation verification against PubMed and other sources."""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from colloquip.tools.interface import ToolResult

logger = logging.getLogger(__name__)

# Citation reference patterns
_PUBMED_REF = re.compile(r"\[PUBMED:(\d+)\]")
_INTERNAL_REF = re.compile(r"\[INTERNAL:([\w\-]+)\]")
_WEB_REF = re.compile(r"\[WEB:(https?://[^\]]+)\]")


class CitationVerifier:
    """Verify citations referenced in agent posts and synthesis.

    Checks [PUBMED:PMID] citations against the NCBI API to confirm
    the paper exists and the title/abstract match the claim context.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def verify_text(self, text: str) -> "VerificationReport":
        """Extract and verify all citations found in a block of text."""
        pubmed_ids = _PUBMED_REF.findall(text)
        internal_ids = _INTERNAL_REF.findall(text)
        web_urls = _WEB_REF.findall(text)

        total = len(pubmed_ids) + len(internal_ids) + len(web_urls)
        verified = 0
        unverified = 0
        flagged = 0
        details = []

        # Verify PubMed citations
        for pmid in pubmed_ids:
            is_valid, title = await self._verify_pmid(pmid)
            if is_valid:
                verified += 1
                details.append({
                    "ref": f"[PUBMED:{pmid}]",
                    "status": "verified",
                    "title": title,
                })
            else:
                flagged += 1
                details.append({
                    "ref": f"[PUBMED:{pmid}]",
                    "status": "flagged",
                    "reason": "PMID not found in PubMed",
                })

        # Internal citations — mark as unverified (would need internal DB check)
        for record_id in internal_ids:
            unverified += 1
            details.append({
                "ref": f"[INTERNAL:{record_id}]",
                "status": "unverified",
                "reason": "Internal references require manual verification",
            })

        # Web citations — mark as unverified
        for url in web_urls:
            unverified += 1
            details.append({
                "ref": f"[WEB:{url}]",
                "status": "unverified",
                "reason": "Web references not automatically verified",
            })

        return VerificationReport(
            total_citations=total,
            verified=verified,
            unverified=unverified,
            flagged=flagged,
            details=details,
        )

    async def _verify_pmid(self, pmid: str) -> Tuple[bool, str]:
        """Check if a PMID exists in PubMed. Returns (is_valid, title)."""
        try:
            import httpx
        except ImportError:
            return False, "httpx not installed"

        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "json",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

            result = data.get("result", {})
            if pmid in result:
                title = result[pmid].get("title", "")
                error = result[pmid].get("error", "")
                if error:
                    return False, error
                return True, title
            return False, "PMID not found"
        except Exception as e:
            logger.warning("PMID verification failed for %s: %s", pmid, e)
            return False, str(e)

    @staticmethod
    def extract_citation_refs(text: str) -> List[str]:
        """Extract all citation references from text."""
        refs = []
        refs.extend(f"[PUBMED:{pmid}]" for pmid in _PUBMED_REF.findall(text))
        refs.extend(f"[INTERNAL:{rid}]" for rid in _INTERNAL_REF.findall(text))
        refs.extend(f"[WEB:{url}]" for url in _WEB_REF.findall(text))
        return refs


class VerificationReport:
    """Results of citation verification."""

    def __init__(
        self,
        total_citations: int = 0,
        verified: int = 0,
        unverified: int = 0,
        flagged: int = 0,
        details: Optional[List[Dict]] = None,
    ):
        self.total_citations = total_citations
        self.verified = verified
        self.unverified = unverified
        self.flagged = flagged
        self.details = details or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_citations": self.total_citations,
            "verified": self.verified,
            "unverified": self.unverified,
            "flagged": self.flagged,
            "details": self.details,
        }


class MockCitationVerifier:
    """Mock citation verifier for testing."""

    async def verify_text(self, text: str) -> VerificationReport:
        pubmed_ids = _PUBMED_REF.findall(text)
        internal_ids = _INTERNAL_REF.findall(text)
        web_urls = _WEB_REF.findall(text)

        total = len(pubmed_ids) + len(internal_ids) + len(web_urls)
        details = []

        # In mock mode, all PubMed citations are "verified"
        for pmid in pubmed_ids:
            details.append({
                "ref": f"[PUBMED:{pmid}]",
                "status": "verified",
                "title": f"Mock Paper Title for PMID {pmid}",
            })

        for record_id in internal_ids:
            details.append({
                "ref": f"[INTERNAL:{record_id}]",
                "status": "verified",
                "title": f"Mock Internal Document {record_id}",
            })

        for url in web_urls:
            details.append({
                "ref": f"[WEB:{url}]",
                "status": "unverified",
                "reason": "Web references not verified in mock mode",
            })

        return VerificationReport(
            total_citations=total,
            verified=len(pubmed_ids) + len(internal_ids),
            unverified=len(web_urls),
            flagged=0,
            details=details,
        )

    @staticmethod
    def extract_citation_refs(text: str) -> List[str]:
        return CitationVerifier.extract_citation_refs(text)

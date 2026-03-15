"""Domain-specific scientific database tools.

Provides tools for querying PDB (Protein Data Bank), UniProt, and other
scientific databases that agents use during protein engineering deliberations.
"""

import logging
from typing import Any, Dict

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)


class PDBTool(BaseSearchTool):
    """Tool for searching the Protein Data Bank (PDB) via RCSB REST API."""

    _name = "pdb_search"
    _description = (
        "Search the Protein Data Bank (PDB) for protein structures. "
        "Find structures by protein name, gene, organism, resolution, "
        "experimental method, or ligand."
    )

    def __init__(self, max_results: int = 10, **kwargs):
        self.max_results = max_results

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
                            "Search query: protein name, gene name, PDB ID, organism, or keyword."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 10, max 25).",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        import time

        start = time.monotonic()
        query = kwargs.get("query", "")
        max_results = min(kwargs.get("max_results", self.max_results), 25)

        try:
            import aiohttp

            search_url = "https://search.rcsb.org/rcsbsearch/v2/query"
            payload = {
                "query": {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {"value": query},
                },
                "return_type": "entry",
                "request_options": {
                    "results_content_type": ["experimental"],
                    "paginate": {"start": 0, "rows": max_results},
                },
            }

            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=15)
                async with session.post(search_url, json=payload, timeout=timeout) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return ToolResult(
                            source="pdb",
                            query=query,
                            error=f"PDB API returned status {resp.status}: {text[:200]}",
                        )
                    data = await resp.json()

            results = []
            for hit in data.get("result_set", [])[:max_results]:
                pdb_id = hit.get("identifier", "")
                score = hit.get("score", 0.0)
                results.append(
                    SearchResult(
                        title=pdb_id,
                        abstract=f"PDB structure {pdb_id}",
                        url=f"https://www.rcsb.org/structure/{pdb_id}",
                        source_type="pdb",
                        source_id=pdb_id,
                        relevance_score=min(score, 1.0),
                    )
                )

            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                source="pdb",
                query=query,
                results=results,
                truncated=len(data.get("result_set", [])) > max_results,
                execution_time_ms=elapsed,
            )

        except ImportError:
            return ToolResult(source="pdb", query=query, error="aiohttp not installed")
        except Exception as e:
            logger.error("PDB search failed: %s", e)
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                source="pdb",
                query=query,
                error=str(e),
                execution_time_ms=elapsed,
            )


class MockPDBTool(BaseSearchTool):
    """Mock PDB tool for testing."""

    _name = "pdb_search"
    _description = "Search the Protein Data Bank (PDB) for protein structures."

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        return ToolResult(
            source="pdb",
            query=query,
            results=[
                SearchResult(
                    title="7BZ5",
                    abstract="Crystal structure of EGFR kinase domain in complex with osimertinib",
                    url="https://www.rcsb.org/structure/7BZ5",
                    source_type="pdb",
                    source_id="7BZ5",
                    relevance_score=0.95,
                ),
                SearchResult(
                    title="6JX0",
                    abstract="Cryo-EM structure of EGFR extracellular domain with cetuximab Fab",
                    url="https://www.rcsb.org/structure/6JX0",
                    source_type="pdb",
                    source_id="6JX0",
                    relevance_score=0.82,
                ),
            ],
            execution_time_ms=1.0,
        )


class UniProtTool(BaseSearchTool):
    """Tool for searching UniProt protein database."""

    _name = "uniprot_search"
    _description = (
        "Search UniProt for protein information: function, sequence, "
        "domains, Gene Ontology terms, and cross-references."
    )

    def __init__(self, max_results: int = 10, **kwargs):
        self.max_results = max_results

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
                        "description": "Protein name, gene name, accession, or keyword.",
                    },
                    "organism": {
                        "type": "string",
                        "description": "Filter by organism (e.g., 'Homo sapiens').",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 10, max 25).",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        import time

        start = time.monotonic()
        query = kwargs.get("query", "")
        organism = kwargs.get("organism", "")
        max_results = min(kwargs.get("max_results", self.max_results), 25)

        try:
            import aiohttp

            search_query = query
            if organism:
                search_query += f" AND organism_name:{organism}"

            url = "https://rest.uniprot.org/uniprotkb/search"
            params = {
                "query": search_query,
                "format": "json",
                "size": max_results,
                "fields": "accession,protein_name,gene_names,organism_name,length,cc_function",
            }

            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=15)
                async with session.get(url, params=params, timeout=timeout) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return ToolResult(
                            source="uniprot",
                            query=query,
                            error=f"UniProt API returned status {resp.status}: {text[:200]}",
                        )
                    data = await resp.json()

            results = []
            for entry in data.get("results", [])[:max_results]:
                accession = entry.get("primaryAccession", "")
                protein_name = ""
                if entry.get("proteinDescription", {}).get("recommendedName"):
                    protein_name = (
                        entry["proteinDescription"]["recommendedName"]
                        .get("fullName", {})
                        .get("value", "")
                    )
                gene_names = ", ".join(
                    g.get("geneName", {}).get("value", "") for g in entry.get("genes", [])
                )
                organism = entry.get("organism", {}).get("scientificName", "")
                length = entry.get("sequence", {}).get("length", 0)

                function_text = ""
                for comment in entry.get("comments", []):
                    if comment.get("commentType") == "FUNCTION":
                        for txt in comment.get("texts", []):
                            function_text += txt.get("value", "")

                abstract = f"{protein_name} ({gene_names}) - {organism}, {length} aa"
                if function_text:
                    abstract += f"\nFunction: {function_text[:300]}"

                results.append(
                    SearchResult(
                        title=f"{accession} - {protein_name}",
                        abstract=abstract,
                        url=f"https://www.uniprot.org/uniprot/{accession}",
                        source_type="uniprot",
                        source_id=accession,
                    )
                )

            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                source="uniprot",
                query=query,
                results=results,
                execution_time_ms=elapsed,
            )

        except ImportError:
            return ToolResult(source="uniprot", query=query, error="aiohttp not installed")
        except Exception as e:
            logger.error("UniProt search failed: %s", e)
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                source="uniprot",
                query=query,
                error=str(e),
                execution_time_ms=elapsed,
            )


class MockUniProtTool(BaseSearchTool):
    """Mock UniProt tool for testing."""

    _name = "uniprot_search"
    _description = "Search UniProt for protein information."

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "organism": {"type": "string", "description": "Organism filter."},
                    "max_results": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        return ToolResult(
            source="uniprot",
            query=query,
            results=[
                SearchResult(
                    title="P00533 - Epidermal growth factor receptor",
                    abstract=(
                        "EGFR (ERBB1) - Homo sapiens, 1210 aa\n"
                        "Function: Receptor tyrosine kinase binding ligands in the "
                        "EGF family, activating downstream signaling pathways."
                    ),
                    url="https://www.uniprot.org/uniprot/P00533",
                    source_type="uniprot",
                    source_id="P00533",
                ),
                SearchResult(
                    title="P04626 - Receptor tyrosine-protein kinase erbB-2",
                    abstract=(
                        "ERBB2 (HER2) - Homo sapiens, 1255 aa\n"
                        "Function: Essential component of a neuregulin-receptor complex."
                    ),
                    url="https://www.uniprot.org/uniprot/P04626",
                    source_type="uniprot",
                    source_id="P04626",
                ),
            ],
            execution_time_ms=1.0,
        )

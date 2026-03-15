"""Tests for domain-specific database tools: PDB and UniProt."""


# =========================================================================
# Mock PDB Tool
# =========================================================================


class TestMockPDBTool:
    async def test_returns_results(self):
        from colloquip.tools.domain_databases import MockPDBTool

        tool = MockPDBTool()
        result = await tool.execute(query="EGFR kinase")
        assert result.error is None
        assert len(result.results) == 2
        assert result.source == "pdb"

    async def test_result_structure(self):
        from colloquip.tools.domain_databases import MockPDBTool

        tool = MockPDBTool()
        result = await tool.execute(query="EGFR")
        first = result.results[0]
        assert first.title == "7BZ5"
        assert first.source_type == "pdb"
        assert first.source_id == "7BZ5"
        assert first.url.startswith("https://www.rcsb.org/structure/")
        assert first.relevance_score > 0

    async def test_tool_schema(self):
        from colloquip.tools.domain_databases import MockPDBTool

        tool = MockPDBTool()
        schema = tool.tool_schema
        assert schema["name"] == "pdb_search"
        assert "query" in schema["input_schema"]["properties"]


# =========================================================================
# Mock UniProt Tool
# =========================================================================


class TestMockUniProtTool:
    async def test_returns_results(self):
        from colloquip.tools.domain_databases import MockUniProtTool

        tool = MockUniProtTool()
        result = await tool.execute(query="EGFR")
        assert result.error is None
        assert len(result.results) == 2
        assert result.source == "uniprot"

    async def test_result_structure(self):
        from colloquip.tools.domain_databases import MockUniProtTool

        tool = MockUniProtTool()
        result = await tool.execute(query="EGFR")
        first = result.results[0]
        assert "P00533" in first.title
        assert first.source_type == "uniprot"
        assert first.source_id == "P00533"
        assert first.url.startswith("https://www.uniprot.org/")
        assert "EGFR" in first.abstract

    async def test_accepts_organism_param(self):
        from colloquip.tools.domain_databases import MockUniProtTool

        tool = MockUniProtTool()
        result = await tool.execute(query="EGFR", organism="Homo sapiens")
        assert result.error is None
        assert len(result.results) == 2

    async def test_tool_schema_has_organism(self):
        from colloquip.tools.domain_databases import MockUniProtTool

        tool = MockUniProtTool()
        schema = tool.tool_schema
        assert "organism" in schema["input_schema"]["properties"]


# =========================================================================
# PDB Tool (schema only, no live API)
# =========================================================================


class TestPDBToolSchema:
    def test_schema(self):
        from colloquip.tools.domain_databases import PDBTool

        tool = PDBTool()
        schema = tool.tool_schema
        assert schema["name"] == "pdb_search"
        assert "query" in schema["input_schema"]["required"]


class TestUniProtToolSchema:
    def test_schema(self):
        from colloquip.tools.domain_databases import UniProtTool

        tool = UniProtTool()
        schema = tool.tool_schema
        assert schema["name"] == "uniprot_search"
        assert "query" in schema["input_schema"]["required"]

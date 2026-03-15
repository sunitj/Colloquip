"""Tests for database query tool: SQL validation and query execution."""

from unittest.mock import AsyncMock, MagicMock, patch

# =========================================================================
# SQL Validation
# =========================================================================


class TestValidateReadOnly:
    def test_simple_select(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("SELECT * FROM compounds") is True

    def test_select_with_where(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("SELECT id, name FROM compounds WHERE ic50 < 10") is True

    def test_with_cte(self):
        from colloquip.tools.database_query import validate_read_only

        sql = "WITH top AS (SELECT * FROM compounds LIMIT 10) SELECT * FROM top"
        assert validate_read_only(sql) is True

    def test_rejects_insert(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("INSERT INTO compounds VALUES (1, 'test')") is False

    def test_rejects_update(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("UPDATE compounds SET name='x' WHERE id=1") is False

    def test_rejects_delete(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("DELETE FROM compounds WHERE id=1") is False

    def test_rejects_drop(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("DROP TABLE compounds") is False

    def test_rejects_create(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("CREATE TABLE evil (id INT)") is False

    def test_rejects_truncate(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("TRUNCATE TABLE compounds") is False

    def test_strips_line_comments(self):
        from colloquip.tools.database_query import validate_read_only

        sql = "-- this is a comment\nSELECT * FROM compounds"
        assert validate_read_only(sql) is True

    def test_strips_block_comments(self):
        from colloquip.tools.database_query import validate_read_only

        sql = "/* get all */ SELECT * FROM compounds"
        assert validate_read_only(sql) is True

    def test_rejects_empty(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("") is False
        assert validate_read_only("   ") is False

    def test_rejects_comment_hiding_write(self):
        from colloquip.tools.database_query import validate_read_only

        sql = "SELECT * FROM compounds; DROP TABLE compounds"
        assert validate_read_only(sql) is False

    def test_case_insensitive(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("select * from compounds") is True
        assert validate_read_only("Select Id From compounds") is True

    def test_trailing_semicolon(self):
        from colloquip.tools.database_query import validate_read_only

        assert validate_read_only("SELECT * FROM compounds;") is True


# =========================================================================
# DatabaseQueryTool
# =========================================================================


class TestDatabaseQueryTool:
    async def test_rejects_write_query(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        tool = DatabaseQueryTool()
        result = await tool.execute(query="INSERT INTO t VALUES (1)")
        assert result.error is not None
        assert "SELECT" in result.error

    async def test_no_engine_error(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        tool = DatabaseQueryTool()
        result = await tool.execute(query="SELECT 1")
        assert result.error is not None
        assert "engine" in result.error.lower()

    async def test_execute_with_mock_engine(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchmany.return_value = [(1, "compound_A"), (2, "compound_B")]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_session
        ):
            tool = DatabaseQueryTool(connection_name="test_db")
            tool.set_engine(MagicMock())
            result = await tool.execute(query="SELECT id, name FROM compounds")

        assert result.error is None
        assert len(result.results) == 2
        assert result.results[0].title == "1"
        assert result.results[0].source_type == "database"

    async def test_max_rows_capped_at_200(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["id"]
        mock_result.fetchmany.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_session
        ):
            tool = DatabaseQueryTool()
            tool.set_engine(MagicMock())
            await tool.execute(query="SELECT 1", max_rows=500)
            mock_result.fetchmany.assert_called_with(200)

    async def test_execute_handles_exception(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB connection lost")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_session
        ):
            tool = DatabaseQueryTool()
            tool.set_engine(MagicMock())
            result = await tool.execute(query="SELECT 1")

        assert result.error is not None
        assert "DB connection lost" in result.error

    def test_tool_schema(self):
        from colloquip.tools.database_query import DatabaseQueryTool

        tool = DatabaseQueryTool()
        schema = tool.tool_schema
        assert schema["name"] == "database_query"
        assert "query" in schema["input_schema"]["properties"]


# =========================================================================
# MockDatabaseQueryTool
# =========================================================================


class TestMockDatabaseQueryTool:
    async def test_returns_mock_results(self):
        from colloquip.tools.database_query import MockDatabaseQueryTool

        tool = MockDatabaseQueryTool()
        result = await tool.execute(query="SELECT * FROM compounds")
        assert result.error is None
        assert len(result.results) == 2
        assert "compound_A" in result.results[0].title

    async def test_rejects_write_query(self):
        from colloquip.tools.database_query import MockDatabaseQueryTool

        tool = MockDatabaseQueryTool()
        result = await tool.execute(query="DROP TABLE compounds")
        assert result.error is not None

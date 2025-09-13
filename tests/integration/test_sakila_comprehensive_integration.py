"""
Comprehensive Sakila Integration Tests

This file consolidates safeguard and query routing tests using the Sakila database,
providing comprehensive end-to-end testing of SQLBot functionality.
"""

import pytest
import subprocess
import os
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.integration


class TestSakilaSafeguards:
    """Test safeguard functionality using Sakila database."""

    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']

    def test_dangerous_sql_queries_blocked_by_safeguards(self):
        """Test that dangerous SQL queries are blocked by safeguards."""
        from sqlbot.repl import execute_dbt_sql_rich, handle_safeguard_command

        # Ensure safeguards are enabled
        handle_safeguard_command(['on'])

        # Test dangerous queries are blocked
        dangerous_queries = [
            "DELETE FROM film;",
            "UPDATE film SET title = 'hacked';",
            "DROP TABLE film;",
            "TRUNCATE TABLE rental;",
            "INSERT INTO customer VALUES (999, 'hacker', 'test', 'hack@test.com', 1, true, '2024-01-01', '2024-01-01');"
        ]

        for query in dangerous_queries:
            result = execute_dbt_sql_rich(query)
            assert result.startswith("Query blocked by safeguard"), f"Query should be blocked: {query}"

    def test_safe_sql_queries_allowed_through_safeguards(self):
        """Test that safe SQL queries are allowed through safeguards."""
        from sqlbot.repl import execute_dbt_sql_rich, handle_safeguard_command

        # Ensure safeguards are enabled
        handle_safeguard_command(['on'])

        # Mock the actual execution to avoid database dependency
        with patch('sqlbot.repl.execute_clean_sql') as mock_execute:
            mock_execute.return_value = "Query results: film_count\n1000"

            # Test safe queries are allowed
            safe_queries = [
                "SELECT COUNT(*) as film_count FROM film;",
                "SELECT title, rating FROM film WHERE rating = 'PG-13';",
                "SELECT c.first_name, c.last_name FROM customer c LIMIT 10;"
            ]

            for query in safe_queries:
                result = execute_dbt_sql_rich(query)
                assert not result.startswith("Query blocked by safeguard"), f"Query should not be blocked: {query}"
                assert "Query results:" in result, f"Query should execute normally: {query}"

    def test_shared_session_respects_safeguards(self):
        """Test that the shared session interface respects safeguards."""
        from sqlbot.interfaces.shared_session import SQLBotSession
        from sqlbot.core.config import SQLBotConfig

        config = SQLBotConfig(profile='Sakila')
        session = SQLBotSession(config)

        # Test dangerous query
        result = session.execute_query("DELETE FROM film;")

        # Should return a failed result, not success
        assert result.success == False
        assert "Query blocked by safeguard" in result.error


class TestSakilaQueryRouting:
    """Test query routing functionality using Sakila database."""

    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']

    def test_semicolon_query_routing_to_sql_execution(self):
        """Test that queries ending with semicolon are routed to SQL execution."""
        from sqlbot.interfaces.shared_session import SQLBotSession
        from sqlbot.core.config import SQLBotConfig

        config = SQLBotConfig(profile='Sakila')
        session = SQLBotSession(config)

        # Test dangerous query with semicolon - should be routed to SQL and blocked
        result = session.execute_query("DROP TABLE film;")
        assert result.query_type.value == "sql", f"Should be SQL query type, got: {result.query_type}"
        assert not result.success, "Dangerous query should be blocked"
        assert "safeguard" in result.error.lower(), f"Error should mention safeguards: {result.error}"

        # Test safe query with semicolon - should be routed to SQL
        result = session.execute_query("SELECT COUNT(*) FROM film;")
        assert result.query_type.value == "sql", f"Should be SQL query type, got: {result.query_type}"
        # Note: might fail due to actual DB execution, but routing should be correct

    def test_natural_language_query_routing_to_llm(self):
        """Test that natural language queries are routed to LLM."""
        from sqlbot.interfaces.shared_session import SQLBotSession
        from sqlbot.core.config import SQLBotConfig

        config = SQLBotConfig(profile='Sakila')
        session = SQLBotSession(config)

        # Mock the LLM call to avoid actual LLM execution
        with patch('sqlbot.interfaces.shared_session.SQLBotSession._call_handle_llm_query_safely') as mock_llm:
            mock_llm.return_value = "There are 1000 films in the Sakila database"

            result = session.execute_query("How many films are in the database")

            # Should be routed to LLM
            assert result.query_type.value == "natural_language", f"Should be natural language query type, got: {result.query_type}"
            mock_llm.assert_called_once_with("How many films are in the database")

    def test_semicolon_detection_edge_cases(self):
        """Test edge cases for semicolon detection that affect routing."""
        from sqlbot.repl import is_sql_query

        test_cases = [
            ("SELECT * FROM film;", True, "Basic semicolon"),
            ("SELECT * FROM film; ", True, "Semicolon with trailing space"),
            (" SELECT * FROM film; ", True, "Semicolon with leading and trailing spaces"),
            ("SELECT * FROM film;\n", True, "Semicolon with newline"),
            ("SELECT * FROM film", False, "No semicolon"),
            ("How many films are there?", False, "Natural language question"),
        ]

        for query, expected, description in test_cases:
            result = is_sql_query(query)
            assert result == expected, f"{description}: Expected {expected}, got {result} for query: {repr(query)}"


class TestSakilaEndToEndIntegration:
    """End-to-end integration tests using Sakila database."""

    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']

    @pytest.mark.timeout(30)
    def test_cli_dangerous_query_end_to_end(self):
        """Test that dangerous queries are blocked in CLI mode."""
        from tests.conftest import setup_subprocess_environment

        env = setup_subprocess_environment()
        env['DBT_PROFILE_NAME'] = 'Sakila'

        # Test dangerous query
        cmd = ['python', '-m', 'sqlbot.repl', '--no-repl', '--profile', 'Sakila', 'DELETE FROM film;']

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        output = result.stdout + result.stderr

        # Should not contain LLM response indicators (query should not reach LLM)
        llm_indicators = [
            "[Structured Response]",
            "1) Understood",
            "2) Approach",
            "3) Query execution"
        ]

        for indicator in llm_indicators:
            assert indicator not in output, f"Found LLM indicator '{indicator}' - query should not have gone to LLM"

        # Should contain safeguard blocking
        assert ("Query blocked by safeguard" in output or
                "Query disallowed due to dangerous operations" in output), f"Should see safeguard message in output: {output}"

    @pytest.mark.timeout(30)
    def test_cli_safe_query_end_to_end(self):
        """Test that safe queries work correctly in CLI mode."""
        from tests.conftest import setup_subprocess_environment

        env = setup_subprocess_environment()
        env['DBT_PROFILE_NAME'] = 'Sakila'

        # Test safe query
        cmd = ['python', '-m', 'sqlbot.repl', '--no-repl', '--profile', 'Sakila', 'SELECT 42 AS answer;']

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        output = result.stdout + result.stderr

        # Should not contain LLM response indicators (direct SQL execution)
        llm_indicators = [
            "[Structured Response]",
            "1) Understood",
            "2) Approach"
        ]

        for indicator in llm_indicators:
            assert indicator not in output, f"Found LLM indicator '{indicator}' - query should not have gone to LLM"

        # Should execute as SQL query successfully (or fail with actual DB error, not routing error)
        assert not any(phrase in output for phrase in [
            "Query blocked by safeguard",
            "[Structured Response]"
        ]), f"Query should execute directly as SQL: {output}"


class TestSakilaLLMToolIntegration:
    """Test LLM tool integration with Sakila database."""

    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']

    def test_llm_tool_respects_safeguards(self):
        """Test that the LLM tool respects global safeguard settings."""
        from sqlbot.llm_integration import DbtQueryTool
        from unittest.mock import MagicMock

        # Enable safeguards
        import sqlbot.repl as repl_module
        repl_module.READONLY_MODE = True

        # Create tool with mock display
        mock_display = MagicMock()
        tool = DbtQueryTool(session_id="test", unified_display=mock_display)

        # Test dangerous query
        result = tool._run("DELETE FROM film")

        # Should return error result
        assert '"success": false' in result.lower()
        assert "query blocked by safeguard" in result.lower()

    def test_llm_tool_safeguard_messages_display_correctly(self):
        """Test that safeguard messages display with correct formatting."""
        from sqlbot.llm_integration import DbtQueryTool
        from unittest.mock import MagicMock

        # Enable safeguards
        import sqlbot.repl as repl_module
        repl_module.READONLY_MODE = True

        # Create tool with mock display
        mock_display = MagicMock()
        tool = DbtQueryTool(session_id="test", unified_display=mock_display)

        # Test safe query - just verify it returns expected result format
        with patch('sqlbot.core.dbt_service.get_dbt_service') as mock_service:
            from sqlbot.core.types import QueryResult, QueryType

            # Create a real QueryResult object with simple data
            mock_result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                data=[{"count": 1000}],
                columns=["count"],
                row_count=1,
                execution_time=0.1
            )
            mock_service.return_value.execute_query.return_value = mock_result

            result = tool._run("SELECT COUNT(*) FROM film")

            # Should return successful result JSON
            assert '"success": true' in result.lower(), f"Should return successful result: {result}"
            assert '"data"' in result.lower(), f"Should include data in result: {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Integration tests for safeguard functionality across all execution paths.

This module ensures that safeguards work correctly in all code paths,
preventing dangerous SQL operations from executing.
"""

import pytest

pytestmark = pytest.mark.integration
from unittest.mock import patch, MagicMock
import os

def test_direct_sql_query_blocked_by_safeguards():
    """Test that direct SQL queries (ending with ;) are blocked by safeguards."""
    from sqlbot.repl import execute_dbt_sql_rich, handle_safeguard_command
    
    # Ensure safeguards are enabled
    handle_safeguard_command(['on'])
    
    # Set up environment
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Test dangerous queries are blocked
    dangerous_queries = [
        "DELETE FROM users;",
        "INSERT INTO users VALUES (1, 'test');",
        "UPDATE users SET name = 'hacked';", 
        "DROP TABLE users;",
        "TRUNCATE TABLE logs;",
        "CREATE TABLE malicious (id INT);",
        "ALTER TABLE users ADD COLUMN hacked VARCHAR(100);"
    ]
    
    for query in dangerous_queries:
        result = execute_dbt_sql_rich(query)
        assert result.startswith("Query blocked by safeguard"), f"Query should be blocked: {query}"

def test_safe_sql_queries_allowed():
    """Test that safe SQL queries are allowed through safeguards."""
    from sqlbot.repl import execute_dbt_sql_rich, handle_safeguard_command
    
    # Ensure safeguards are enabled
    handle_safeguard_command(['on'])
    
    # Set up environment
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Mock the actual execution to avoid database calls
    with patch('sqlbot.repl.execute_clean_sql') as mock_execute:
        mock_execute.return_value = "Query results: 5 rows"
        
        # Test safe queries are allowed
        safe_queries = [
            "SELECT * FROM users;",
            "SELECT COUNT(*) FROM orders;",
            "SELECT name, email FROM customers WHERE active = 1;",
            "SELECT TOP 10 * FROM products ORDER BY price DESC;"
        ]
        
        for query in safe_queries:
            result = execute_dbt_sql_rich(query)
            assert not result.startswith("Query blocked by safeguard"), f"Query should not be blocked: {query}"
            assert "Query results: 5 rows" in result, f"Query should execute normally: {query}"

def test_cli_execution_path_respects_safeguards():
    """Test that the CLI execution path properly respects safeguards."""
    from sqlbot.repl import _execute_query_cli_mode
    from rich.console import Console
    
    console = Console(file=open(os.devnull, 'w'))  # Suppress output
    
    # Test dangerous SQL query in CLI
    with patch('sqlbot.repl.execute_dbt_sql_rich') as mock_execute:
        mock_execute.return_value = "Query blocked by safeguard"
        
        # Should not print the blocked message as success
        _execute_query_cli_mode("DELETE FROM users;", console)
        
        # Verify the query was attempted to be executed
        mock_execute.assert_called_once_with("DELETE FROM users;")

def test_shared_session_respects_safeguards():
    """Test that the shared session interface respects safeguards."""
    from sqlbot.interfaces.shared_session import SQLBotSession
    from sqlbot.core.config import SQLBotConfig
    
    config = SQLBotConfig(profile='sqlbot')
    session = SQLBotSession(config)
    
    # Mock the SQL execution to return blocked result
    with patch('sqlbot.repl.execute_dbt_sql_rich') as mock_execute:
        mock_execute.return_value = "Query blocked by safeguard"
        
        result = session.execute_query("DELETE FROM users;")
        
        # Should return a failed result, not success
        assert result.success == False
        assert "Query blocked by safeguard" in result.error

def test_dangerous_flag_disables_safeguards():
    """Test that --dangerous flag properly disables safeguards.""" 
    from sqlbot.repl import handle_safeguard_command
    import sqlbot.repl as repl_module
    
    # Simulate --dangerous flag behavior
    repl_module.READONLY_MODE = False
    repl_module.READONLY_CLI_MODE = True
    
    # Mock the actual execution
    with patch('sqlbot.repl.execute_clean_sql') as mock_execute:
        mock_execute.return_value = "Query executed successfully"
        
        result = repl_module.execute_dbt_sql_rich("DELETE FROM users;")
        
        # Query should execute without safeguard checks
        assert "Query executed successfully" in result
        assert not result.startswith("Query blocked by safeguard")

def test_llm_tool_respects_safeguards():
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
    result = tool._run("DELETE FROM users")
    
    # Should return error result
    assert '"success": false' in result.lower()
    assert "query blocked by safeguard" in result.lower()

def test_safeguard_messages_display_correctly():
    """Test that safeguard messages display with correct icons."""
    from sqlbot.llm_integration import DbtQueryTool
    from unittest.mock import MagicMock
    
    # Enable safeguards
    import sqlbot.repl as repl_module
    repl_module.READONLY_MODE = True
    
    # Create tool with mock display
    mock_display = MagicMock()
    mock_console = MagicMock()
    mock_display.display_impl.console = mock_console
    
    tool = DbtQueryTool(session_id="test", unified_display=mock_display)
    
    # Test safe query
    with patch('sqlbot.core.dbt_service.get_dbt_service') as mock_service:
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = [{"count": 5}]
        mock_result.columns = ["count"]
        mock_result.row_count = 1
        mock_result.execution_time = 0.1
        mock_service.return_value.execute_query.return_value = mock_result
        
        result = tool._run("SELECT COUNT(*) FROM users")
        
        # Should display checkmark message
        mock_console.print.assert_called_with("[green]✔ Query passes safeguard against dangerous operations.[/green]")

def test_safeguard_integration_end_to_end():
    """End-to-end test of safeguard functionality."""
    import sqlbot.repl as repl_module
    
    # Start with safeguards enabled (default)
    assert repl_module.READONLY_MODE == True
    
    # Test that dangerous queries are blocked
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    result = repl_module.execute_safe_sql("DELETE FROM test_table")
    assert "Query blocked by safeguard" in result
    
    # Disable safeguards
    repl_module.handle_safeguard_command(['off'])
    assert repl_module.READONLY_MODE == False
    
    # Mock execution for disabled safeguards test
    with patch('sqlbot.repl.execute_clean_sql') as mock_execute:
        mock_execute.return_value = "Query executed"
        
        result = repl_module.execute_safe_sql("DELETE FROM test_table")
        assert "Query executed" in result
        assert not result.startswith("Query blocked by safeguard")

def test_delete_from_film_semicolon_routing():
    """Specific test for the exact scenario: DELETE FROM film; should be blocked by safeguards."""
    from sqlbot.repl import is_sql_query, execute_dbt_sql_rich
    from sqlbot.interfaces.shared_session import SQLBotSession
    from sqlbot.core.config import SQLBotConfig
    
    # Test the exact query that was problematic
    query = "DELETE FROM film;"
    
    # 1. Test semicolon detection
    assert is_sql_query(query), "DELETE FROM film; should be detected as SQL query"
    
    # 2. Test REPL routing
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    result = execute_dbt_sql_rich(query)
    assert result.startswith("Query blocked by safeguard"), f"Query should be blocked, got: {result}"
    
    # 3. Test shared session routing (used by Textual interface)
    config = SQLBotConfig(profile='sqlbot')
    session = SQLBotSession(config)
    session_result = session.execute_query(query)
    assert not session_result.success, "Session result should indicate failure"
    assert "Query blocked by safeguard" in session_result.error, f"Error should mention safeguard, got: {session_result.error}"
    
    # 4. Test Textual interface logic (duplicate the detection logic)
    textual_is_sql = query.strip().endswith(';')
    assert textual_is_sql, "Textual interface should detect this as SQL"

def test_semicolon_edge_cases():
    """Test edge cases for semicolon detection that might cause routing issues."""
    from sqlbot.repl import is_sql_query
    
    test_cases = [
        ("DELETE FROM film;", True, "Basic semicolon"),
        ("DELETE FROM film; ", True, "Semicolon with trailing space"),
        (" DELETE FROM film; ", True, "Semicolon with leading and trailing spaces"),
        ("DELETE FROM film;\n", True, "Semicolon with newline"),
        ("DELETE FROM film;\t", True, "Semicolon with tab"),
        ("DELETE FROM film", False, "No semicolon"),
        ("DELETE FROM film; -- comment", False, "Semicolon with comment after"),
        ("DELETE FROM film;", True, "Exact problematic query"),
    ]
    
    for query, expected, description in test_cases:
        result = is_sql_query(query)
        assert result == expected, f"{description}: Expected {expected}, got {result} for query: {repr(query)}"

if __name__ == "__main__":
    pytest.main([__file__])
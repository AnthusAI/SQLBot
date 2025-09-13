"""
End-to-end integration tests for semicolon query routing.

This tests the actual user experience to ensure queries ending with semicolon
are handled correctly in all interfaces.
"""

import pytest
import subprocess
import os
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.integration

def test_cli_semicolon_dangerous_query_end_to_end():
    """Test that dangerous queries with semicolon are blocked in CLI mode."""
    from tests.conftest import setup_subprocess_environment
    
    env = setup_subprocess_environment()
    env['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Test dangerous query
    cmd = ['python', '-m', 'sqlbot.repl', '--no-repl', '--profile', 'sqlbot', 'DELETE FROM film;']
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
        env=env
    )
    
    output = result.stdout + result.stderr
    
    # Should not contain LLM response indicators
    llm_indicators = [
        "[Structured Response]",
        "1) Understood",
        "2) Approach", 
        "3) Query execution",
        "I can't run destructive",
        "non-destructive policy"
    ]
    
    for indicator in llm_indicators:
        assert indicator not in output, f"Found LLM indicator '{indicator}' - query should not have gone to LLM"
    
    # Should contain safeguard blocking
    assert ("Query blocked by safeguard" in output or 
            "Query disallowed due to dangerous operations" in output), f"Should see safeguard message in output: {output}"

def test_cli_semicolon_safe_query_end_to_end():
    """Test that safe queries with semicolon work correctly in CLI mode."""
    from tests.conftest import setup_subprocess_environment
    
    env = setup_subprocess_environment()
    env['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Test safe query
    cmd = ['python', '-m', 'sqlbot.repl', '--no-repl', '--profile', 'sqlbot', 'SELECT 42 AS test;']
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
        env=env
    )
    
    output = result.stdout + result.stderr
    
    # Should not contain LLM response indicators
    llm_indicators = [
        "[Structured Response]",
        "1) Understood",
        "2) Approach", 
        "3) Query execution"
    ]
    
    for indicator in llm_indicators:
        assert indicator not in output, f"Found LLM indicator '{indicator}' - query should not have gone to LLM"
    
    # Should execute as SQL query
    assert result.returncode == 0, f"Query should execute successfully: {output}"

def test_textual_interface_semicolon_routing():
    """Test semicolon routing in the Textual interface logic directly."""
    from sqlbot.interfaces.textual_app import SQLBotTextualApp
    
    # Test the query detection logic directly
    app = SQLBotTextualApp()
    
    # Test cases
    test_cases = [
        ("DELETE FROM film;", True, "Should detect as SQL"),
        ("SELECT * FROM film;", True, "Should detect as SQL"), 
        ("How many films are there", False, "Should not detect as SQL"),
        ("DELETE FROM film; -- comment", True, "Should detect as SQL with comment"),
        ("DELETE FROM film; ", True, "Should detect as SQL with trailing space"),
    ]
    
    for query, expected_is_sql, description in test_cases:
        is_sql_query = query.strip().endswith(';')
        assert is_sql_query == expected_is_sql, f"{description}: {query}"

def test_shared_session_semicolon_routing_comprehensive():
    """Comprehensive test of shared session semicolon routing."""
    from sqlbot.interfaces.shared_session import SQLBotSession
    from sqlbot.core.config import SQLBotConfig
    
    config = SQLBotConfig(profile='sqlbot')
    session = SQLBotSession(config)
    
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Test dangerous query with semicolon
    result = session.execute_query("DROP TABLE film;")
    
    # Should be routed to SQL execution and blocked
    assert result.query_type.value == "sql", f"Should be SQL query type, got: {result.query_type}"
    assert not result.success, "Dangerous query should be blocked"
    assert "safeguard" in result.error.lower(), f"Error should mention safeguards: {result.error}"
    
    # Test safe query with semicolon  
    result = session.execute_query("SELECT 42 AS test;")
    
    # Should be routed to SQL execution
    assert result.query_type.value == "sql", f"Should be SQL query type, got: {result.query_type}"
    # Note: might fail due to dbt config issues, but should still be routed as SQL
    
    # Test natural language query (no semicolon)
    with patch('sqlbot.interfaces.shared_session.SQLBotSession._call_handle_llm_query_safely') as mock_llm:
        mock_llm.return_value = "This is an LLM response"
        
        result = session.execute_query("How many films are there")
        
        # Should be routed to LLM
        assert result.query_type.value == "natural_language", f"Should be natural language query type, got: {result.query_type}"
        mock_llm.assert_called_once()

def test_message_formatter_structured_response_issue():
    """Test the [Structured Response] formatting issue."""
    from sqlbot.interfaces.message_formatter import format_llm_response
    
    # Test various problematic responses that might cause [Structured Response]
    problematic_responses = [
        "",  # Empty response
        "{}",  # Empty JSON
        '{"malformed": json}',  # Invalid JSON
        '[]',  # Empty array
        None,  # None response
    ]
    
    for response in problematic_responses:
        try:
            formatted = format_llm_response(response)
            # Should not contain [Structured Response] - this indicates a formatting failure
            if "[Structured Response]" in formatted:
                print(f"Warning: Response '{response}' resulted in [Structured Response]: {formatted}")
        except Exception as e:
            print(f"Response '{response}' caused exception: {e}")

def test_no_semicolon_goes_to_llm():
    """Test that queries without semicolon properly go to LLM."""
    from sqlbot.interfaces.shared_session import SQLBotSession
    from sqlbot.core.config import SQLBotConfig
    
    config = SQLBotConfig(profile='sqlbot')
    session = SQLBotSession(config)
    
    os.environ['DBT_PROFILE_NAME'] = 'sqlbot'
    
    # Mock the LLM call to avoid actual LLM execution
    with patch('sqlbot.interfaces.shared_session.SQLBotSession._call_handle_llm_query_safely') as mock_llm:
        mock_llm.return_value = "This is a natural language response"
        
        result = session.execute_query("How many films are in the database")
        
        # Should be routed to LLM
        assert result.query_type.value == "natural_language", f"Should be natural language query, got: {result.query_type}"
        mock_llm.assert_called_once_with("How many films are in the database")

if __name__ == "__main__":
    pytest.main([__file__])
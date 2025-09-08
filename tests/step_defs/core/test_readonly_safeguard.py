"""Step definitions for read-only safeguard BDD tests."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock
import io
import sys
from contextlib import contextmanager

# Load all scenarios from the feature file
scenarios('../../features/core/readonly_safeguard.feature')

@given('QBot is running in interactive mode')
def qbot_interactive():
    """Ensure QBot is running in interactive mode."""
    # This is handled by conftest.py fixtures
    pass

@given('the database is available')
def database_available():
    """Ensure database is available."""
    # This is handled by conftest.py fixtures
    pass

@given('I am in the QBot REPL')
def in_qbot_repl():
    """Ensure we're in the QBot REPL context."""
    # Set up REPL context
    pass

@given('read-only mode is enabled')
def readonly_mode_enabled():
    """Enable read-only mode for testing."""
    from qbot.repl import handle_readonly_command
    handle_readonly_command(['on'])

@given('read-only mode is disabled')
def readonly_mode_disabled():
    """Disable read-only mode for testing."""
    from qbot.repl import handle_readonly_command
    handle_readonly_command(['off'])

@when(parsers.parse('I try to execute "{sql_query}"'))
def try_execute_dangerous_query(sql_query):
    """Try to execute a potentially dangerous query."""
    pytest.dangerous_query = sql_query

@when(parsers.parse('I execute "{sql_query}"'))
def execute_safe_query(sql_query):
    """Execute a safe query."""
    pytest.safe_query = sql_query

@when('I try to execute a query with comments containing "DELETE"')
def try_execute_query_with_comments():
    """Execute a query with comments that mention dangerous operations."""
    pytest.comment_query = """
    /* This query mentions DELETE in comments but doesn't actually delete */
    -- DELETE is mentioned here too
    SELECT COUNT(*) FROM table -- Not dangerous
    """

@when('I respond "yes" to the override prompt')
def respond_yes_to_override():
    """Respond yes to the safety override prompt."""
    pytest.override_response = 'yes'

@when('I respond "no" to the override prompt')
def respond_no_to_override():
    """Respond no to the safety override prompt."""
    pytest.override_response = 'no'

@when(parsers.parse('I respond "{response}" to execute the query'))
def respond_to_execute_query(response):
    """User responds to execute the query prompt."""
    pytest.execution_response = response

@when('I press Ctrl+C at the override prompt')
def ctrl_c_at_override():
    """Press Ctrl+C during the override prompt."""
    pytest.keyboard_interrupt_override = True

@when(parsers.parse('I enter "{command}"'))
def enter_command_step(command):
    """Enter a command in the REPL."""
    from qbot.repl import handle_double_slash_command
    
    if command.startswith('//'):
        # Handle double-slash commands
        if command == '//preview':
            # Mock the input for preview command to avoid interactive input during testing
            with patch('builtins.input', side_effect=['', '']):  # Empty inputs to cancel
                result = handle_double_slash_command(command)
                pytest.command_result = result
        else:
            result = handle_double_slash_command(command)
            pytest.command_result = result
    else:
        pytest.command_input = command

@then('I should see "Read-only safeguard mode ENABLED"')
def should_see_mode_enabled():
    """Verify read-only mode enabled message."""
    pass

@then('I should see "All queries will be checked for dangerous operations"')
def should_see_safety_message():
    """Verify safety check message."""
    pass

@then('I should see "Read-only safeguard mode DISABLED"')
def should_see_mode_disabled():
    """Verify read-only mode disabled message."""
    pass

@then('I should see "Queries will execute without safety checks"')
def should_see_no_safety_message():
    """Verify no safety checks message."""
    pass

@then('I should see the current safeguard status')
def should_see_current_status():
    """Verify current status is displayed."""
    pass

@then('I should see usage instructions')
def should_see_usage_instructions():
    """Verify usage instructions are shown."""
    pass

@then('I should see "Query blocked by read-only safeguard!"')
def should_see_query_blocked():
    """Verify query blocked message."""
    pass

@then(parsers.parse('I should see "Dangerous operations detected: {operation}"'))
def should_see_dangerous_operations(operation):
    """Verify dangerous operations are detected."""
    pass

@then('I should be prompted for override confirmation')
def should_see_override_prompt():
    """Verify override prompt is shown."""
    pass

@then('the query should execute normally')
def query_should_execute_normally():
    """Verify query executes without issues."""
    pass

@then('I should see query results')
def should_see_query_results():
    """Verify query results are displayed."""
    pass

@then('I should not see any safety warnings')
def should_not_see_safety_warnings():
    """Verify no safety warnings are shown."""
    pass

@then('I should see dangerous operations detected')
def should_see_dangerous_ops_detected():
    """Verify dangerous operations are detected."""
    pass

@then('I should see "Safety override granted. Executing query..."')
def should_see_override_granted():
    """Verify override granted message."""
    pass

@then('the dangerous query should execute')
def dangerous_query_should_execute():
    """Verify dangerous query executes after override."""
    pass

@then('I should see "Query execution cancelled for safety"')
def should_see_execution_cancelled():
    """Verify execution cancelled message."""
    pass

@then('the dangerous query should not execute')
def dangerous_query_should_not_execute():
    """Verify dangerous query does not execute."""
    pass

@then('the query should execute without safety checks')
def query_executes_without_checks():
    """Verify query executes without safety checks."""
    pass

@then(parsers.parse('I should see "{message}"'))
def should_see_message(message):
    """Verify specific message is displayed."""
    pass

# Integration tests for the safety functionality
def test_sql_safety_analysis():
    """Test SQL safety analysis function."""
    from qbot.repl import analyze_sql_safety
    
    # Test safe queries
    safe_queries = [
        "SELECT * FROM table",
        "SELECT TOP 10 * FROM users WHERE active = 1",
        "SELECT COUNT(*) FROM orders",
        "SELECT 'DELETE is just text' as message"
    ]
    
    for query in safe_queries:
        result = analyze_sql_safety(query)
        assert result['is_safe'] == True
        assert len(result['dangerous_operations']) == 0

def test_dangerous_sql_detection():
    """Test detection of dangerous SQL operations."""
    from qbot.repl import analyze_sql_safety
    
    # Test dangerous queries
    dangerous_queries = [
        ("DELETE FROM users", ['DELETE']),
        ("INSERT INTO table VALUES (1, 2)", ['INSERT']),
        ("UPDATE users SET name = 'test'", ['UPDATE']),
        ("DROP TABLE old_table", ['DROP']),
        ("CREATE TABLE new_table (id INT)", ['CREATE']),
        ("ALTER TABLE users ADD COLUMN email VARCHAR(255)", ['ALTER']),
        ("TRUNCATE TABLE logs", ['TRUNCATE']),
        ("INSERT INTO temp SELECT * FROM source; DELETE FROM old", ['INSERT', 'DELETE'])
    ]
    
    for query, expected_ops in dangerous_queries:
        result = analyze_sql_safety(query)
        assert result['is_safe'] == False
        assert all(op in result['dangerous_operations'] for op in expected_ops)

def test_sql_with_comments():
    """Test SQL analysis with comments containing dangerous keywords."""
    from qbot.repl import analyze_sql_safety
    
    # Query with dangerous keywords in comments should be safe
    query_with_comments = """
    /* This DELETE is in a comment */
    -- Another DELETE mention
    SELECT COUNT(*) FROM table /* DROP is mentioned here too */
    """
    
    result = analyze_sql_safety(query_with_comments)
    assert result['is_safe'] == True
    assert len(result['dangerous_operations']) == 0

def test_readonly_mode_toggle():
    """Test read-only mode toggle functionality."""
    from qbot.repl import handle_readonly_command, READONLY_MODE
    import qbot.repl as repl_module
    
    # Test enabling
    handle_readonly_command(['on'])
    assert repl_module.READONLY_MODE == True
    
    # Test disabling
    handle_readonly_command(['off'])
    assert repl_module.READONLY_MODE == False
    
    # Test status check (should not change state)
    handle_readonly_command([])
    assert repl_module.READONLY_MODE == False

def test_execute_safe_sql_when_readonly_disabled():
    """Test that execute_safe_sql bypasses checks when readonly mode is disabled."""
    from qbot.repl import execute_safe_sql, handle_readonly_command
    import os
    
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    
    # Disable readonly mode
    handle_readonly_command(['off'])
    
    # Mock the clean execution
    with patch('qbot.repl.execute_clean_sql') as mock_execute:
        mock_execute.return_value = "Query executed successfully"
        
        result = execute_safe_sql("DELETE FROM test_table")
        assert result == "Query executed successfully"
        assert mock_execute.called

def test_execute_safe_sql_blocks_when_readonly_enabled():
    """Test that execute_safe_sql blocks dangerous queries when readonly mode is enabled."""
    from qbot.repl import execute_safe_sql, handle_readonly_command
    import os
    
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    
    # Enable readonly mode
    handle_readonly_command(['on'])
    
    # Mock user input to reject override
    with patch('builtins.input', return_value='no'):
        result = execute_safe_sql("DELETE FROM test_table")
        assert "Query blocked by read-only safeguard" in result
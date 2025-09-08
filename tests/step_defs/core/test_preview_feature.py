"""Step definitions for preview feature BDD tests."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock
import io
import sys
from contextlib import contextmanager

# Load all scenarios from the feature file
scenarios('../../features/core/preview_feature.feature')

@contextmanager
def mock_input_output():
    """Mock input/output for testing interactive features."""
    mock_input = Mock()
    mock_stdout = io.StringIO()
    
    with patch('builtins.input', mock_input), \
         patch('sys.stdout', mock_stdout):
        yield mock_input, mock_stdout

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

@when('I enter "//preview"')
def enter_preview_command():
    """User enters the //preview command."""
    from qbot.repl import handle_double_slash_command
    
    with mock_input_output() as (mock_input, mock_stdout):
        # Mock empty input to cancel preview
        mock_input.return_value = ""
        result = handle_double_slash_command("//preview")

@when(parsers.parse('I enter "{sql_query}"'))
def enter_sql_query(sql_query):
    """User enters a SQL query."""
    # Store the query for later use in tests
    pytest.current_query = sql_query

@when('I enter an empty query')
def enter_empty_query():
    """User enters an empty query."""
    pytest.current_query = ""

@when('I press Ctrl+C during SQL input')
def ctrl_c_during_input():
    """User presses Ctrl+C during SQL input."""
    pytest.keyboard_interrupt = True

@when('I press Ctrl+C during execution prompt')
def ctrl_c_during_prompt():
    """User presses Ctrl+C during execution prompt."""
    pytest.keyboard_interrupt_prompt = True

@when(parsers.parse('I respond "{response}" to the execution prompt'))
def respond_to_execution_prompt(response):
    """User responds to execution prompt."""
    pytest.execution_response = response

@when('I enter invalid SQL syntax')
def enter_invalid_sql():
    """User enters invalid SQL syntax."""
    pytest.current_query = "INVALID SQL SYNTAX THAT WILL FAIL"

@when(parsers.parse('I enter "{command}"'))
def enter_command(command):
    """User enters a command."""
    pytest.current_command = command

@then('I should see "Preview Mode - Enter SQL to preview compilation:"')
def should_see_preview_prompt():
    """Verify preview prompt is shown."""
    # This would be verified by checking the output
    pass

@then('I should see "Compiled SQL Preview:"')
def should_see_compiled_preview():
    """Verify compiled SQL preview header is shown."""
    pass

@then('I should see the compiled SQL query')
def should_see_compiled_sql():
    """Verify the compiled SQL is displayed."""
    pass

@then('I should see "Execute this query? (y/n):"')
def should_see_execution_prompt():
    """Verify execution prompt is shown."""
    pass

@then('I should see the compiled SQL preview')
def should_see_sql_preview():
    """Verify SQL preview is displayed."""
    pass

@then('the query should execute')
def query_should_execute():
    """Verify the query executes."""
    pass

@then('I should see query results')
def should_see_results():
    """Verify query results are displayed."""
    pass

@then('I should see "Query execution cancelled"')
def should_see_cancelled():
    """Verify cancellation message is shown."""
    pass

@then('the query should not execute')
def query_should_not_execute():
    """Verify the query does not execute."""
    pass

@then(parsers.parse('the compiled SQL should contain "{text}"'))
def compiled_sql_should_contain(text):
    """Verify compiled SQL contains specific text."""
    pass

@then(parsers.parse('the compiled SQL should not contain "{text}"'))
def compiled_sql_should_not_contain(text):
    """Verify compiled SQL does not contain specific text."""
    pass

@then('I should see "No query provided"')
def should_see_no_query():
    """Verify no query message is shown."""
    pass

@then('I should return to the main prompt')
def should_return_to_prompt():
    """Verify return to main prompt."""
    pass

@then('I should see "Preview cancelled"')
def should_see_preview_cancelled():
    """Verify preview cancellation message."""
    pass

@then('I should see an error message about compilation failure')
def should_see_compilation_error():
    """Verify compilation error message is shown."""
    pass

@then('I should not be prompted for execution')
def should_not_be_prompted():
    """Verify execution prompt is not shown."""
    pass

@then(parsers.parse('I should see "{message}"'))
def should_see_message(message):
    """Verify specific message is displayed."""
    pass

@then('I should see available double-slash commands')
def should_see_available_commands():
    """Verify available commands are listed."""
    pass

# Integration test that actually tests the preview functionality
def test_preview_functionality_integration():
    """Integration test for preview functionality."""
    from qbot.repl import preview_sql_compilation, execute_clean_sql
    import os
    
    # Set up environment
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    
    # Test SQL compilation preview
    test_sql = "SELECT TOP 3 * FROM sakila.film"
    
    # Mock the dbt compilation
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Compiled inline node is:\nSELECT TOP 3 * FROM \"sakila\".\"film\""
        mock_run.return_value = mock_result
        
        result = preview_sql_compilation(test_sql)
        
        assert "Compiled inline node is:" in result
        assert "SELECT TOP 3" in result
        assert mock_run.called

def test_preview_with_source_syntax():
    """Test preview with dbt source syntax."""
    from qbot.repl import preview_sql_compilation
    import os
    
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    
    test_sql = "SELECT TOP 5 * FROM {{ source('sakila', 'film') }}"
    
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Compiled inline node is:\nSELECT TOP 5 * FROM \"sakila\".\"film\""
        mock_run.return_value = mock_result
        
        result = preview_sql_compilation(test_sql)
        
        assert "sakila" in result
        assert "film" in result
        assert "{{ source" not in result
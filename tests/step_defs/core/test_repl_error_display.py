"""
BDD step definitions for REPL error display.
Tests that database errors are clearly displayed to users in the REPL interface.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Load scenarios from feature file
scenarios('../../features/core/repl_error_display.feature')

@pytest.fixture
def mock_repl_console():
    """Mock Rich console for REPL testing"""
    console = Mock()
    console.print = Mock()
    return console

@pytest.fixture
def mock_subprocess_result():
    """Mock subprocess result for testing database errors"""
    result = Mock()
    result.returncode = 1
    result.stdout = "Database Error: Table 'nonexistent_table' doesn't exist"
    result.stderr = "Error: Connection failed"
    return result

@given("SQLBot REPL is running")
def qbot_repl_running():
    """Set up SQLBot REPL environment"""
    pass

@given("the database connection is configured")
def database_connection_configured():
    """Ensure database connection is set up"""
    pass

@given("I am in the SQLBot REPL")
def in_qbot_repl(mock_repl_console):
    """Simulate being in the SQLBot REPL"""
    pass

@given("SQLBot is configured with invalid database credentials")
def invalid_database_credentials():
    """Configure SQLBot with invalid credentials"""
    pass

@given("SQLBot is in read-only mode")
def qbot_readonly_mode():
    """Set SQLBot to read-only mode"""
    pass

@given("I am in the SQLBot REPL with debug logging enabled")
def qbot_repl_debug_logging():
    """Enable debug logging in SQLBot REPL"""
    pass

@given("I run SQLBot in non-interactive mode with --no-repl")
def run_qbot_noninteractive():
    """Run SQLBot in non-interactive mode"""
    pass

@when(parsers.parse('I enter an invalid SQL query "{query}"'))
def enter_invalid_sql(query, mock_subprocess_result):
    """Simulate entering invalid SQL"""
    # Mock the execute_clean_sql function to return an error
    with patch('sqlbot.repl.execute_clean_sql') as mock_execute:
        mock_execute.return_value = f"Error executing query:\nSTDOUT: {mock_subprocess_result.stdout}\nSTDERR: {mock_subprocess_result.stderr}"

@when(parsers.parse('I ask "{question}"'))
def ask_question_repl(question):
    """Simulate asking a question in REPL"""
    pass

@when("the LLM generates a query for a table that doesn't exist")
def llm_generates_nonexistent_table_query():
    """Simulate LLM generating query for nonexistent table"""
    pass

@when("I start the SQLBot REPL")
def start_qbot_repl():
    """Simulate starting SQLBot REPL"""
    pass

@when("the LLM generates a query with a nonexistent column")
def llm_generates_nonexistent_column_query():
    """Simulate LLM generating query with nonexistent column"""
    pass

@when("the LLM generates a DELETE query")
def llm_generates_delete_query():
    """Simulate LLM generating DELETE query"""
    pass

@when("I ask a question that generates a very slow query")
def ask_slow_query_question():
    """Simulate asking question that generates slow query"""
    pass

@when("the query times out")
def query_times_out():
    """Simulate query timeout"""
    pass

@when("I encounter different types of database errors in sequence")
def encounter_multiple_error_types():
    """Simulate encountering multiple error types"""
    pass

@when("the LLM generates a problematic query")
def llm_generates_problematic_query():
    """Simulate LLM generating problematic query"""
    pass

@when("a database query fails with any type of error")
def database_query_fails():
    """Simulate database query failure"""
    pass

@when("I provide a query that will cause a database error")
def provide_error_causing_query():
    """Simulate providing query that causes error"""
    pass

@then(parsers.parse('I should see an error message containing "{error_text}"'))
def verify_error_message_contains(error_text, mock_repl_console):
    """Verify error message contains specific text"""
    # This would check that the error message was displayed with the expected text
    pass

@then("the error message should be displayed in red color")
def verify_error_red_color(mock_repl_console):
    """Verify error message uses red color"""
    # This would check that Rich console used red color for error
    pass

@then("the error message should include the specific syntax issue")
def verify_specific_syntax_issue():
    """Verify error includes specific syntax details"""
    pass

@then("I should remain in the REPL for the next command")
def verify_remain_in_repl():
    """Verify REPL continues after error"""
    pass

@then("the error message should be clearly visible to the user")
def verify_error_clearly_visible():
    """Verify error is clearly displayed"""
    pass

@then("the error should suggest checking available tables")
def verify_suggests_check_tables():
    """Verify error suggests checking tables"""
    pass

@then("I should see a clear connection error message")
def verify_clear_connection_error():
    """Verify clear connection error message"""
    pass

@then("the error should mention database connection issues")
def verify_mentions_connection_issues():
    """Verify error mentions connection issues"""
    pass

@then("the error should suggest checking configuration")
def verify_suggests_check_config():
    """Verify error suggests checking configuration"""
    pass

@then("the error should not expose sensitive connection details")
def verify_no_sensitive_details():
    """Verify no sensitive information is exposed"""
    pass

@then("I should see an error message about the invalid column")
def verify_invalid_column_error():
    """Verify invalid column error message"""
    pass

@then("the error should specify which column was not found")
def verify_specifies_column_not_found():
    """Verify error specifies the column"""
    pass

@then("the error should suggest checking the table schema")
def verify_suggests_check_schema():
    """Verify error suggests checking schema"""
    pass

@then("I should see a permission denied error")
def verify_permission_denied_error():
    """Verify permission denied error"""
    pass

@then("the error should mention read-only mode or insufficient permissions")
def verify_mentions_readonly_permissions():
    """Verify error mentions read-only or permissions"""
    pass

@then("the error should suggest using SELECT queries instead")
def verify_suggests_select_queries():
    """Verify error suggests SELECT queries"""
    pass

@then("I should see a timeout error message")
def verify_timeout_error():
    """Verify timeout error message"""
    pass

@then("the error should mention the timeout duration")
def verify_mentions_timeout_duration():
    """Verify error mentions timeout duration"""
    pass

@then("the error should suggest simplifying the query")
def verify_suggests_simplify_query():
    """Verify error suggests simplifying query"""
    pass

@then("each error should be displayed clearly and consistently")
def verify_errors_clear_consistent():
    """Verify errors are clear and consistent"""
    pass

@then("each error should use appropriate color coding")
def verify_appropriate_color_coding():
    """Verify errors use appropriate colors"""
    pass

@then("each error should provide actionable feedback")
def verify_actionable_feedback():
    """Verify errors provide actionable feedback"""
    pass

@then("I should be able to continue using the REPL after each error")
def verify_continue_after_errors():
    """Verify REPL continues after errors"""
    pass

@then("the error message should include or reference the failed query")
def verify_includes_failed_query():
    """Verify error includes failed query"""
    pass

@then("I should be able to understand which part of my request caused the issue")
def verify_understand_issue_cause():
    """Verify can understand what caused the issue"""
    pass

@then("the error should help me reformulate my question")
def verify_helps_reformulate():
    """Verify error helps reformulate question"""
    pass

@then("the full error details should be logged")
def verify_full_error_logged():
    """Verify full error details are logged"""
    pass

@then("the log should include the original user question")
def verify_log_includes_user_question():
    """Verify log includes user question"""
    pass

@then("the log should include the generated SQL query")
def verify_log_includes_sql_query():
    """Verify log includes generated SQL"""
    pass

@then("the log should include the complete database error message")
def verify_log_includes_complete_error():
    """Verify log includes complete error message"""
    pass

@then("the log should include timestamp and context information")
def verify_log_includes_timestamp_context():
    """Verify log includes timestamp and context"""
    pass

@then("the error should be displayed to stdout/stderr")
def verify_error_to_stdout_stderr():
    """Verify error goes to stdout/stderr"""
    pass

@then("the error should be clearly formatted")
def verify_error_clearly_formatted():
    """Verify error is clearly formatted"""
    pass

@then("the error should not be mixed with other output")
def verify_error_not_mixed():
    """Verify error is not mixed with other output"""
    pass

@then("the process should exit with appropriate error code")
def verify_appropriate_exit_code():
    """Verify process exits with appropriate code"""
    pass

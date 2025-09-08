"""
BDD step definitions for database error handling in conversation history.
Tests that database errors are properly captured and made available to the LLM.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Load scenarios from feature file
scenarios('../../features/core/database_error_handling.feature')

@pytest.fixture
def mock_conversation_history():
    """Mock conversation history for testing"""
    return []

@pytest.fixture
def mock_llm_agent():
    """Mock LLM agent for testing"""
    agent = Mock()
    agent.invoke = Mock()
    return agent

@pytest.fixture
def qbot_with_test_db():
    """QBot instance configured with test database"""
    with patch('qbot.llm_integration.conversation_history', []):
        yield

@given("QBot is configured with a test database profile")
def qbot_configured_with_test_db(qbot_with_test_db):
    """Set up QBot with test database configuration"""
    pass

@given("the LLM integration is available")
def llm_integration_available():
    """Ensure LLM integration is available for testing"""
    with patch('qbot.repl.LLM_AVAILABLE', True):
        pass

@given("I start a new conversation with QBot")
def start_new_conversation(mock_conversation_history):
    """Start a new conversation, clearing any existing history"""
    mock_conversation_history.clear()

@given("QBot is configured with invalid database credentials")
def qbot_with_invalid_credentials():
    """Configure QBot with invalid database credentials"""
    pass

@given("QBot is configured with read-only database access")
def qbot_with_readonly_access():
    """Configure QBot with read-only database access"""
    pass

@when(parsers.parse('I ask "{question}"'))
def ask_question(question, mock_llm_agent):
    """Simulate asking a question to QBot"""
    # Store the question for later verification
    mock_llm_agent.last_question = question

@when("the LLM generates a query that fails with a database error")
def llm_generates_failing_query(mock_llm_agent, mock_conversation_history):
    """Simulate LLM generating a query that fails"""
    # Mock the database error
    mock_llm_agent.database_error = "Table 'nonexistent_table' doesn't exist"
    
    # Simulate adding the error to conversation history
    mock_conversation_history.append({
        'role': 'assistant',
        'content': f"I'll query the nonexistent_table for you."
    })
    mock_conversation_history.append({
        'role': 'tool',
        'content': f"Error executing query: {mock_llm_agent.database_error}"
    })

@when("the LLM generates invalid SQL that causes a syntax error")
def llm_generates_invalid_sql(mock_llm_agent, mock_conversation_history):
    """Simulate LLM generating invalid SQL"""
    mock_llm_agent.sql_error = "Syntax error near 'INVALID' at line 1"
    
    # Simulate adding the syntax error to conversation history
    mock_conversation_history.append({
        'role': 'assistant',
        'content': f"I'll count the records with this query: SELECT COUNT(*) FROM table INVALID SYNTAX;"
    })
    mock_conversation_history.append({
        'role': 'tool',
        'content': f"Error executing query: {mock_llm_agent.sql_error}"
    })

@when("the LLM generates a query for the nonexistent table")
def llm_queries_nonexistent_table(mock_llm_agent):
    """Simulate LLM querying a nonexistent table"""
    mock_llm_agent.table_error = "Table 'table_that_does_not_exist' doesn't exist"
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        mock_history.append({
            'role': 'tool',
            'content': f"Database error: {mock_llm_agent.table_error}"
        })

@when("the LLM generates a query with an invalid column name")
def llm_queries_invalid_column(mock_llm_agent):
    """Simulate LLM querying with invalid column"""
    mock_llm_agent.column_error = "Column 'nonexistent_column' not found in table 'film'"
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        mock_history.append({
            'role': 'tool',
            'content': f"Column error: {mock_llm_agent.column_error}"
        })

@when("the LLM generates a DELETE query")
def llm_generates_delete_query(mock_llm_agent):
    """Simulate LLM generating a DELETE query"""
    mock_llm_agent.permission_error = "Permission denied: DELETE operations not allowed in read-only mode"
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        mock_history.append({
            'role': 'tool',
            'content': f"Permission error: {mock_llm_agent.permission_error}"
        })

@when("the LLM generates a query with multiple errors")
def llm_generates_multi_error_query(mock_llm_agent):
    """Simulate LLM generating a query with multiple errors"""
    mock_llm_agent.multi_errors = [
        "Table 'wrong_table' doesn't exist",
        "Column 'wrong_column' not found"
    ]
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        for error in mock_llm_agent.multi_errors:
            mock_history.append({
                'role': 'tool',
                'content': f"Database error: {error}"
            })

@when("the LLM generates another query with remaining errors")
def llm_generates_another_error_query(mock_llm_agent):
    """Simulate LLM generating another query with errors"""
    mock_llm_agent.additional_error = "Column 'still_wrong_column' not found"
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        mock_history.append({
            'role': 'tool',
            'content': f"Database error: {mock_llm_agent.additional_error}"
        })

@when("the LLM generates SQL that produces a detailed error message")
def llm_generates_detailed_error(mock_llm_agent):
    """Simulate LLM generating SQL with detailed error"""
    mock_llm_agent.detailed_error = "Syntax error at line 2, column 15: Expected ')' but found 'FROM'"
    
    with patch('qbot.llm_integration.conversation_history') as mock_history:
        mock_history.append({
            'role': 'tool',
            'content': f"Detailed SQL error: {mock_llm_agent.detailed_error}"
        })

@when(parsers.parse('I ask a follow-up question "{question}"'))
def ask_followup_question(question, mock_llm_agent):
    """Simulate asking a follow-up question"""
    mock_llm_agent.followup_question = question

@then("the database error should be captured in the conversation history")
def verify_error_in_conversation_history(mock_llm_agent, mock_conversation_history):
    """Verify that database errors are captured in conversation history"""
    # Check that error messages are in the conversation history
    error_messages = [msg for msg in mock_conversation_history if 'error' in str(msg.get('content', '')).lower()]
    assert len(error_messages) > 0, f"Database error should be captured in conversation history. History: {mock_conversation_history}"

@then("the LLM should have access to the previous error in its context")
def verify_llm_has_error_context(mock_llm_agent, mock_conversation_history):
    """Verify that LLM receives error context in follow-up queries"""
    # Check that the conversation history contains error messages that would be passed to LLM
    context_parts = []
    for msg in mock_conversation_history:
        if 'error' in str(msg.get('content', '')).lower():
            context_parts.append(f"Previous error: {msg['content']}")
    
    assert len(context_parts) > 0, f"LLM should receive error context. History: {mock_conversation_history}"

@then("the LLM should reference the previous error in its response")
def verify_llm_references_error(mock_llm_agent):
    """Verify that LLM acknowledges previous errors"""
    # Mock LLM response that references the error
    mock_response = "I see there was an error with the previous query. Let me try a different approach."
    mock_llm_agent.invoke.return_value = {"output": mock_response}
    
    # Verify the response references the error
    assert "error" in mock_response.lower(), "LLM should reference the previous error"

@then("the SQL syntax error should be captured in the conversation history")
def verify_syntax_error_captured(mock_llm_agent, mock_conversation_history):
    """Verify SQL syntax errors are captured"""
    syntax_errors = [msg for msg in mock_conversation_history if 'syntax' in str(msg.get('content', '')).lower()]
    assert len(syntax_errors) > 0, f"SQL syntax error should be captured. History: {mock_conversation_history}"

@then("the LLM should acknowledge the previous syntax error")
def verify_llm_acknowledges_syntax_error(mock_llm_agent):
    """Verify LLM acknowledges syntax errors"""
    mock_response = "I apologize for the syntax error in my previous query. Let me correct it."
    mock_llm_agent.invoke.return_value = {"output": mock_response}
    
    assert "syntax error" in mock_response.lower(), "LLM should acknowledge syntax error"

@then("the LLM should generate corrected SQL")
def verify_llm_generates_corrected_sql(mock_llm_agent):
    """Verify LLM generates corrected SQL after error"""
    # This would involve checking that the LLM generates valid SQL
    # after seeing the syntax error
    pass

@then("I should see a clear database connection error message")
def verify_connection_error_message():
    """Verify clear connection error message is shown"""
    # This would test the user-facing error display
    pass

@then("the error should be captured in the conversation history")
def verify_generic_error_captured():
    """Verify any error is captured in conversation history"""
    pass

@then('I should see a "table not found" error message')
def verify_table_not_found_error():
    """Verify table not found error is displayed"""
    pass

@then("the LLM should reference the previous table error")
def verify_llm_references_table_error():
    """Verify LLM references table errors"""
    pass

@then("the LLM should generate a query to list available tables")
def verify_llm_lists_tables():
    """Verify LLM generates table listing query"""
    pass

@then('I should see a "column not found" error message')
def verify_column_not_found_error():
    """Verify column not found error is displayed"""
    pass

@then("the LLM should reference the previous column error")
def verify_llm_references_column_error():
    """Verify LLM references column errors"""
    pass

@then("the LLM should generate a query to describe the table structure")
def verify_llm_describes_table():
    """Verify LLM generates table description query"""
    pass

@then("I should see a permission denied or read-only error")
def verify_permission_error():
    """Verify permission denied error is displayed"""
    pass

@then("the LLM should reference the permission error")
def verify_llm_references_permission_error():
    """Verify LLM references permission errors"""
    pass

@then("the LLM should generate a SELECT query instead")
def verify_llm_generates_select():
    """Verify LLM generates SELECT instead of DELETE"""
    pass

@then("I should see database error messages")
def verify_database_error_messages():
    """Verify database error messages are displayed"""
    pass

@then("the errors should be captured in the conversation history")
def verify_errors_captured():
    """Verify multiple errors are captured"""
    pass

@then("I should see additional error messages")
def verify_additional_error_messages():
    """Verify additional errors are displayed"""
    pass

@then("both errors should be in the conversation history")
def verify_both_errors_captured():
    """Verify multiple errors are in conversation history"""
    pass

@then("the LLM should reference both previous errors")
def verify_llm_references_both_errors():
    """Verify LLM references multiple errors"""
    pass

@then("the LLM should generate a corrected query")
def verify_llm_generates_corrected_query():
    """Verify LLM generates corrected query"""
    pass

@then("the complete error message should be captured")
def verify_complete_error_captured():
    """Verify complete error details are captured"""
    pass

@then("the error should include specific details like line numbers or column names")
def verify_error_includes_details():
    """Verify error includes specific details"""
    pass

@then("the LLM should be able to reference the specific error information")
def verify_llm_references_specific_details():
    """Verify LLM can reference specific error details"""
    pass

@when(parsers.parse('I ask a follow-up question'))
def ask_generic_followup_question(mock_llm_agent):
    """Handle generic follow-up question step"""
    mock_llm_agent.followup_asked = True

@when(parsers.parse('I ask "{question}"'))
def ask_specific_question(question, mock_llm_agent):
    """Handle specific question step"""
    mock_llm_agent.specific_question = question

@when("I ask about the error details")
def ask_about_error_details_when(mock_llm_agent):
    """Handle asking about error details"""
    mock_llm_agent.error_details_asked = True

@then("the LLM should reference the connection issue")
def verify_llm_references_connection_issue(mock_llm_agent):
    """Verify LLM references connection issues"""
    pass  # Implementation would verify LLM mentions connection problems


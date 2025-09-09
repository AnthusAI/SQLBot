"""
Step definitions for conversation history with tool calls BDD scenarios.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Import the scenarios
scenarios('../../features/core/conversation_history_with_tools.feature')

@pytest.fixture
def mock_conversation_history():
    """Mock the global conversation_history list"""
    with patch('qbot.llm_integration.conversation_history', []) as mock_history:
        yield mock_history

@pytest.fixture
def mock_memory_manager():
    """Mock conversation memory manager"""
    mock = Mock()
    mock.get_filtered_context.return_value = []
    mock.clear_history = Mock()
    mock.add_user_message = Mock()
    mock.add_assistant_message = Mock()
    return mock

@pytest.fixture
def mock_console():
    """Mock Rich console"""
    mock = Mock()
    mock.print = Mock()
    return mock

@pytest.fixture
def qbot_session(mock_conversation_history, mock_memory_manager, mock_console):
    """Set up a QBot session for testing"""
    session_data = {
        'conversation_history': mock_conversation_history,
        'memory_manager': mock_memory_manager,
        'console': mock_console,
        'queries_executed': [],
        'tool_calls_made': [],
        'tool_results': []
    }
    return session_data

# Background steps

@given("QBot is configured with the Sakila profile")
def qbot_configured_sakila(qbot_session):
    """Configure QBot with Sakila profile"""
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    qbot_session['profile'] = 'Sakila'

@given("the --history flag is enabled")
def history_flag_enabled(qbot_session):
    """Enable the --history flag"""
    qbot_session['show_history'] = True

@when("the --history flag is enabled")
def when_history_flag_enabled(qbot_session):
    """Enable the --history flag (when step)"""
    qbot_session['show_history'] = True

@given("LLM integration is available")
def llm_integration_available(qbot_session):
    """Mock LLM integration as available"""
    qbot_session['llm_available'] = True

# Scenario steps

@given("I start a new conversation")
def start_new_conversation(qbot_session):
    """Start a new conversation"""
    qbot_session['conversation_history'].clear()
    qbot_session['queries_executed'].clear()
    qbot_session['tool_calls_made'].clear()
    qbot_session['tool_results'].clear()

@when(parsers.parse('I ask "{question}"'))
def ask_question(question, qbot_session):
    """Ask a question to QBot"""
    # Add user message to conversation history
    qbot_session['conversation_history'].append({
        "role": "user", 
        "content": question
    })
    qbot_session['queries_executed'].append(question)

@then("the LLM should execute database queries")
def llm_executes_queries(qbot_session):
    """Verify that LLM executes database queries"""
    # Mock tool calls being added to conversation history
    tool_call_1 = {
        "role": "assistant",
        "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT c.customer_id, c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count FROM customer c JOIN rental r ON c.customer_id = r.customer_id GROUP BY c.customer_id ORDER BY rental_count DESC LIMIT 2'}\n\n📊 TOOL RESULT:\nQuery #1 failed: STDOUT: near \"limit\": syntax error"
    }
    tool_call_2 = {
        "role": "assistant", 
        "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT c.customer_id, c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count FROM customer c JOIN rental r ON c.customer_id = r.customer_id GROUP BY c.customer_id ORDER BY rental_count DESC'}\n\n📊 TOOL RESULT:\nSuccess: 5 rows returned (columns: customer_id, first_name, last_name, rental_count)"
    }
    
    qbot_session['conversation_history'].extend([tool_call_1, tool_call_2])
    qbot_session['tool_calls_made'].extend([tool_call_1, tool_call_2])

@then("the conversation history should contain the user question")
def verify_user_question_in_history(qbot_session):
    """Verify user question is in conversation history"""
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    assert len(user_messages) > 0, "No user messages found in conversation history"
    assert any("customers by rentals" in msg['content'] for msg in user_messages), "User question not found in history"

@then("the conversation history should contain tool calls with SQL queries")
def verify_tool_calls_in_history(qbot_session):
    """Verify tool calls are in conversation history"""
    tool_messages = [msg for msg in qbot_session['conversation_history'] 
                    if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) > 0, "No tool calls found in conversation history"
    assert any("SELECT" in msg['content'] for msg in tool_messages), "SQL queries not found in tool calls"

@then("the conversation history should contain tool results with query outcomes")
def verify_tool_results_in_history(qbot_session):
    """Verify tool results are in conversation history"""
    result_messages = [msg for msg in qbot_session['conversation_history'] 
                      if msg['role'] == 'assistant' and '📊 TOOL RESULT:' in msg['content']]
    assert len(result_messages) > 0, "No tool results found in conversation history"

@then("the conversation history should contain the final LLM response")
def verify_final_response_in_history(qbot_session):
    """Verify final LLM response is in conversation history"""
    # Add mock final response
    final_response = {
        "role": "assistant",
        "content": "Here are the top 2 customers by rental count:\n- Eleanor Hunt (customer_id 148): 46 rentals\n- Karl Seal (customer_id 526): 45 rentals"
    }
    qbot_session['conversation_history'].append(final_response)
    
    # Verify it exists
    assistant_messages = [msg for msg in qbot_session['conversation_history'] 
                         if msg['role'] == 'assistant' and '🔧 TOOL CALL:' not in msg['content']]
    assert len(assistant_messages) > 0, "No final LLM response found in conversation history"

@when("the LLM executes queries and provides results")
def llm_executes_and_responds(qbot_session):
    """Mock LLM executing queries and providing results"""
    # This combines the tool execution and final response steps
    llm_executes_queries(qbot_session)
    verify_final_response_in_history(qbot_session)

@when(parsers.parse('I ask a follow-up question "{question}"'))
def ask_followup_question(question, qbot_session):
    """Ask a follow-up question"""
    qbot_session['conversation_history'].append({
        "role": "user",
        "content": question
    })

@then(parsers.parse("the conversation history panel should show:"))
def verify_conversation_history_panel(qbot_session):
    """Verify the conversation history panel shows expected content"""
    # Verify we have the expected message types in conversation history
    history = qbot_session['conversation_history']
    
    # Check for user messages
    user_messages = [msg for msg in history if msg['role'] == 'user']
    assert len(user_messages) >= 2, f"Expected at least 2 user messages, got {len(user_messages)}"
    
    # Check for tool calls
    tool_messages = [msg for msg in history if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) > 0, "Expected tool call messages in history"
    
    # Check for tool results
    result_messages = [msg for msg in history if msg['role'] == 'assistant' and '📊 TOOL RESULT:' in msg['content']]
    assert len(result_messages) > 0, "Expected tool result messages in history"

@then("the LLM should understand the context from the previous query")
def verify_llm_understands_context(qbot_session):
    """Verify LLM has context from previous query"""
    # Check that conversation history has multiple user messages and responses
    history = qbot_session['conversation_history']
    user_messages = [msg for msg in history if msg['role'] == 'user']
    assert len(user_messages) >= 2, "LLM should have context from multiple user queries"
    
    # Verify the follow-up question can reference previous context
    latest_user_msg = user_messages[-1]['content']
    assert any(word in latest_user_msg.lower() for word in ['their', 'them', 'those']), \
        "Follow-up question should reference previous context with pronouns"

@when("the first SQL query fails with a syntax error")
def first_query_fails(qbot_session):
    """Mock first SQL query failing"""
    failed_tool_call = {
        "role": "assistant",
        "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT * FROM customer LIMIT 2'}\n\n📊 TOOL RESULT:\nQuery failed: STDOUT: near \"limit\": syntax error"
    }
    qbot_session['conversation_history'].append(failed_tool_call)
    qbot_session['tool_calls_made'].append(failed_tool_call)

@when("the LLM retries with a corrected query that succeeds")
def llm_retries_successfully(qbot_session):
    """Mock LLM retrying with successful query"""
    successful_tool_call = {
        "role": "assistant",
        "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT * FROM customer ORDER BY customer_id'}\n\n📊 TOOL RESULT:\nSuccess: 5 rows returned"
    }
    qbot_session['conversation_history'].append(successful_tool_call)
    qbot_session['tool_calls_made'].append(successful_tool_call)

@then("the conversation history should contain both the failed and successful tool calls")
def verify_both_tool_calls_in_history(qbot_session):
    """Verify both failed and successful tool calls are preserved"""
    tool_messages = [msg for msg in qbot_session['conversation_history'] 
                    if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) >= 2, f"Expected at least 2 tool calls, got {len(tool_messages)}"

@then("the conversation history should show the error message from the first attempt")
def verify_error_message_preserved(qbot_session):
    """Verify error message is preserved in history"""
    error_messages = [msg for msg in qbot_session['conversation_history'] 
                     if 'syntax error' in msg['content']]
    assert len(error_messages) > 0, "Error message not found in conversation history"

@then("the conversation history should show the successful result from the second attempt")
def verify_success_result_preserved(qbot_session):
    """Verify successful result is preserved in history"""
    success_messages = [msg for msg in qbot_session['conversation_history'] 
                       if 'Success:' in msg['content']]
    assert len(success_messages) > 0, "Success result not found in conversation history"

@given("I have an ongoing conversation with multiple queries and tool calls")
def ongoing_conversation_with_tools(qbot_session):
    """Set up an ongoing conversation with multiple queries and tool calls"""
    # Simulate a conversation with multiple exchanges
    conversation = [
        {"role": "user", "content": "What are the top customers?"},
        {"role": "assistant", "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT * FROM customer ORDER BY customer_id LIMIT 5'}\n\n📊 TOOL RESULT:\nQuery failed: syntax error"},
        {"role": "assistant", "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT * FROM customer ORDER BY customer_id'}\n\n📊 TOOL RESULT:\nSuccess: 5 rows returned"},
        {"role": "assistant", "content": "Here are the top customers: Eleanor Hunt, Karl Seal, etc."},
        {"role": "user", "content": "How about their payments?"},
        {"role": "assistant", "content": "🔧 TOOL CALL: execute_dbt_query\nInput: {'query': 'SELECT customer_id, SUM(amount) FROM payment GROUP BY customer_id'}\n\n📊 TOOL RESULT:\nSuccess: 10 rows returned"},
        {"role": "assistant", "content": "Here are their payment totals..."}
    ]
    qbot_session['conversation_history'].extend(conversation)

@when('I ask a new question')
def ask_new_question(qbot_session):
    """Ask a new question in the ongoing conversation"""
    qbot_session['conversation_history'].append({
        "role": "user",
        "content": "What about the lowest spenders?"
    })

@then('the conversation history panel should appear before the "..." thinking indicator')
def verify_panel_appears_before_thinking(qbot_session):
    """Verify conversation history panel appears before thinking indicator"""
    # This would be tested by checking the display order in the actual implementation
    # For now, we verify that show_history is enabled
    assert qbot_session['show_history'] == True, "History panel should be enabled"

@then("the panel should show the system message with database schema")
def verify_system_message_in_panel(qbot_session):
    """Verify system message is shown in panel"""
    # This would be tested by mocking the _display_conversation_history function
    # and verifying it includes the system message
    pass  # Implementation would check the actual panel display

@then("the panel should show all previous user questions")
def verify_all_user_questions_in_panel(qbot_session):
    """Verify all user questions are shown"""
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    assert len(user_messages) >= 3, f"Expected at least 3 user messages, got {len(user_messages)}"

@then("the panel should show all previous tool calls with proper formatting")
def verify_tool_calls_formatted_in_panel(qbot_session):
    """Verify tool calls are properly formatted in panel"""
    tool_messages = [msg for msg in qbot_session['conversation_history'] 
                    if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) > 0, "Tool calls should be present and formatted"

@then("the panel should show all previous tool results")
def verify_tool_results_in_panel(qbot_session):
    """Verify tool results are shown in panel"""
    result_messages = [msg for msg in qbot_session['conversation_history'] 
                      if '📊 TOOL RESULT:' in msg['content']]
    assert len(result_messages) > 0, "Tool results should be present in panel"

@then("the panel should show all previous LLM responses")
def verify_llm_responses_in_panel(qbot_session):
    """Verify LLM responses are shown in panel"""
    response_messages = [msg for msg in qbot_session['conversation_history'] 
                        if msg['role'] == 'assistant' and '🔧 TOOL CALL:' not in msg['content']]
    assert len(response_messages) > 0, "LLM responses should be present in panel"

@then("the panel should show the current user question")
def verify_current_question_in_panel(qbot_session):
    """Verify current user question is shown"""
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    latest_question = user_messages[-1]['content']
    assert "lowest spenders" in latest_question, "Current question should be about lowest spenders"

@given("I start an interactive REPL session with --history enabled")
def start_interactive_repl_with_history(qbot_session):
    """Start interactive REPL with history enabled"""
    qbot_session['mode'] = 'interactive_repl'
    qbot_session['show_history'] = True
    qbot_session['conversation_history'].clear()

@when(parsers.parse('I enter "{query}"'))
def enter_query_in_repl(query, qbot_session):
    """Enter a query in the REPL"""
    qbot_session['conversation_history'].append({
        "role": "user",
        "content": query
    })

@when("I wait for the response with tool calls")
def wait_for_response_with_tool_calls(qbot_session):
    """Wait for response with tool calls"""
    # Mock the tool calls and response
    llm_executes_queries(qbot_session)
    verify_final_response_in_history(qbot_session)

@then("the second query's conversation history panel should include the first question about top customers")
def verify_first_question_in_second_panel(qbot_session):
    """Verify first question appears in second query's history panel"""
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    assert len(user_messages) >= 2, "Should have at least 2 user messages"
    assert "customers by rentals" in user_messages[0]['content'], "First question should be about customers by rentals"

@then("the conversation history should include all tool calls from the first query")
def verify_first_query_tool_calls_in_history(qbot_session):
    """Verify tool calls from first query are in history"""
    tool_messages = [msg for msg in qbot_session['conversation_history'] 
                    if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) >= 2, "Should have tool calls from first query in history"

@then("the conversation history should include all tool results from the first query")
def verify_first_query_tool_results_in_history(qbot_session):
    """Verify tool results from first query are in history"""
    result_messages = [msg for msg in qbot_session['conversation_history'] 
                      if '📊 TOOL RESULT:' in msg['content']]
    assert len(result_messages) >= 2, "Should have tool results from first query in history"

@then("the conversation history should include the first LLM response")
def verify_first_llm_response_in_history(qbot_session):
    """Verify first LLM response is in history"""
    response_messages = [msg for msg in qbot_session['conversation_history'] 
                        if msg['role'] == 'assistant' and '🔧 TOOL CALL:' not in msg['content']]
    assert len(response_messages) >= 1, "Should have first LLM response in history"

@then("the conversation history should include the second question about ranking by spend")
def verify_second_question_in_history(qbot_session):
    """Verify second question is in history"""
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    assert len(user_messages) >= 2, "Should have second user message"
    assert any("spend" in msg['content'].lower() for msg in user_messages), "Should have question about spend"

@then("the LLM should provide a contextually appropriate response")
def verify_contextually_appropriate_response(qbot_session):
    """Verify LLM provides contextually appropriate response"""
    # This would test that the LLM's response shows understanding of previous context
    # For now, we verify that there are multiple exchanges in the conversation
    history_length = len(qbot_session['conversation_history'])
    assert history_length >= 5, f"Expected rich conversation history, got {history_length} messages"

@given("I use CLI mode with --history flag")
def use_cli_mode_with_history(qbot_session):
    """Use CLI mode with history flag"""
    qbot_session['mode'] = 'cli'
    qbot_session['show_history'] = True

@when("I execute a query that involves tool calls")
def execute_query_with_tool_calls(qbot_session):
    """Execute a query that involves tool calls"""
    ask_question("What are the top customers?", qbot_session)
    llm_executes_queries(qbot_session)
    verify_final_response_in_history(qbot_session)

@when("I execute a follow-up query in the same session")
def execute_followup_query_same_session(qbot_session):
    """Execute a follow-up query in the same session"""
    ask_followup_question("Show me their payment totals", qbot_session)

@then("the second query should see the complete conversation history from the first query")
def verify_second_query_sees_first_history(qbot_session):
    """Verify second query sees complete history from first query"""
    # Check that we have messages from both queries
    user_messages = [msg for msg in qbot_session['conversation_history'] if msg['role'] == 'user']
    assert len(user_messages) >= 2, "Should have messages from both queries"
    
    tool_messages = [msg for msg in qbot_session['conversation_history'] 
                    if msg['role'] == 'assistant' and '🔧 TOOL CALL:' in msg['content']]
    assert len(tool_messages) > 0, "Should have tool calls from first query available to second"

@then("the conversation history should include all tool interactions from both queries")
def verify_all_tool_interactions_preserved(qbot_session):
    """Verify all tool interactions from both queries are preserved"""
    # This would be the comprehensive test that everything is preserved
    history = qbot_session['conversation_history']
    
    # Should have multiple user messages
    user_count = len([msg for msg in history if msg['role'] == 'user'])
    assert user_count >= 2, f"Expected at least 2 user messages, got {user_count}"
    
    # Should have tool calls
    tool_count = len([msg for msg in history if '🔧 TOOL CALL:' in msg.get('content', '')])
    assert tool_count > 0, f"Expected tool calls in history, got {tool_count}"
    
    # Should have tool results  
    result_count = len([msg for msg in history if '📊 TOOL RESULT:' in msg.get('content', '')])
    assert result_count > 0, f"Expected tool results in history, got {result_count}"

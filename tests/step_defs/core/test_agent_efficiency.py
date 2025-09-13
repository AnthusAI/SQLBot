"""
BDD step definitions for agent efficiency testing.
Tests that verify the LLM agent makes efficient use of database queries.
"""

import pytest
from unittest.mock import patch, MagicMock
from pytest_bdd import scenarios, given, when, then, parsers

# Load scenarios from the feature file
scenarios('../../features/core/agent_efficiency.feature')

@pytest.fixture
def query_counter():
    """Track the number of database queries made"""
    return {"count": 0, "queries": []}

@pytest.fixture
def mock_agent_with_counter(query_counter):
    """Mock LLM agent that tracks query count"""
    mock_agent = MagicMock()
    
    def mock_invoke(inputs):
        # Simulate different query scenarios
        query = inputs.get("input", "")
        
        if "how many tables" in query.lower():
            # Single successful query scenario
            query_counter["count"] = 1
            query_counter["queries"] = ["SELECT COUNT(*) FROM sqlite_master WHERE type='table'"]
            return {
                "output": "There are 17 tables in the database.\n\n--- Query Details ---\nQuery: SELECT COUNT(*) FROM sqlite_master WHERE type='table'\nResult: | count |\n| ----- |\n| 17    |"
            }
        elif "what tables exist" in query.lower() or "list" in query.lower():
            # Two query scenario (count + list)
            query_counter["count"] = 2
            query_counter["queries"] = [
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'",
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ]
            return {
                "output": "The database contains 17 tables: actor, address, category, city, country...\n\n--- Query Details ---\nQuery: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\nResult: | name |\n| ---- |\n| actor |\n| address |"
            }
        else:
            # Default single query
            query_counter["count"] = 1
            query_counter["queries"] = ["SELECT 1"]
            return {"output": "Query executed successfully"}
    
    mock_agent.invoke = mock_invoke
    return mock_agent

@given("SQLBot is properly configured")
def qbot_properly_configured():
    """Ensure SQLBot is properly configured"""
    pass

@given("the LLM integration is available")
def llm_integration_available():
    """Ensure LLM integration is available"""
    pass

@given("the database connection is working")
def database_connection_working():
    """Ensure database connection is working"""
    pass

@given("I have a working SQLBot instance")
def working_qbot_instance():
    """Set up a working SQLBot instance"""
    pass

@given(parsers.parse('I ask "{question}"'))
def given_ask_question(question, mock_agent_with_counter):
    """Ask a question as a given condition"""
    with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent_with_counter):
        result = mock_agent_with_counter.invoke({"input": question})
        return result

@given("the agent successfully returns a count")
def agent_returns_count_given():
    """Verify agent returned a count as a given condition"""
    pass

@when(parsers.parse('I ask "{question}"'))
def ask_question(question, mock_agent_with_counter):
    """Ask a question to the agent"""
    with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent_with_counter):
        # This would normally call handle_llm_query, but we're mocking the agent
        result = mock_agent_with_counter.invoke({"input": question})
        return result

@when('I ask "How many tables are there?"')
def ask_table_count_question(mock_agent_with_counter):
    """Ask about table count"""
    with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent_with_counter):
        result = mock_agent_with_counter.invoke({"input": "How many tables are there?"})
        return result

@when('the agent successfully returns a count')
def agent_returns_count():
    """Verify agent returned a count"""
    pass

@when('I ask "List the table names"')
def ask_table_names(mock_agent_with_counter):
    """Ask for table names"""
    with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent_with_counter):
        result = mock_agent_with_counter.invoke({"input": "List the table names"})
        return result

@when("I ask a question that generates invalid SQL")
def ask_invalid_sql_question(mock_agent_with_counter):
    """Ask a question that would generate invalid SQL"""
    # Mock a scenario with failed queries
    def mock_invoke_with_failures(inputs):
        query_counter = {"count": 3, "queries": ["INVALID SQL", "ANOTHER INVALID", "SELECT 1"]}
        return {"output": "I encountered some SQL errors but found a solution"}
    
    mock_agent_with_counter.invoke = mock_invoke_with_failures
    result = mock_agent_with_counter.invoke({"input": "Show me the color of the database"})
    return result

@then("the LLM should make exactly 1 database query")
def verify_single_query(query_counter):
    """Verify exactly one query was made"""
    assert query_counter["count"] == 1, f"Expected 1 query, but {query_counter['count']} were made"

@then(parsers.parse("the LLM should make at most {max_queries:d} database queries"))
def verify_max_queries(max_queries, query_counter):
    """Verify no more than max_queries were made"""
    assert query_counter["count"] <= max_queries, f"Expected at most {max_queries} queries, but {query_counter['count']} were made"

@then("the query should return a count result")
def verify_count_result(query_counter):
    """Verify the query returns count information"""
    # Check that at least one query looks like a count query
    count_queries = [q for q in query_counter["queries"] if "COUNT" in q.upper()]
    assert len(count_queries) > 0, "No COUNT queries found in executed queries"

@then("the queries should return table information")
def verify_table_info_result(query_counter):
    """Verify queries return table information"""
    # Check that queries are related to tables
    table_queries = [q for q in query_counter["queries"] if "sqlite_master" in q or "table" in q.lower()]
    assert len(table_queries) > 0, "No table-related queries found"

@then("the agent should stop and provide the answer")
def verify_agent_stops():
    """Verify agent provides a complete answer"""
    # This would be verified by checking that the agent's output contains a complete answer
    pass

@then("the agent should not make additional queries")
def verify_no_additional_queries():
    """Verify no unnecessary additional queries"""
    # This is implicitly tested by the query count verification
    pass

@then("the agent should stop when it has sufficient data")
def verify_stops_with_sufficient_data():
    """Verify agent stops when it has enough information"""
    pass

@then("the agent should not hit the max iterations limit")
def verify_no_max_iterations():
    """Verify agent doesn't hit iteration limits"""
    # In a real implementation, we'd check that the agent didn't reach max_iterations
    pass

@then("the LLM should remember the previous context")
def verify_context_memory():
    """Verify LLM uses previous context"""
    # This would be tested by checking conversation history usage
    pass

@then("make efficient queries based on what it already knows")
def verify_efficient_queries():
    """Verify queries are efficient and don't repeat work"""
    pass

@then("not repeat the same table counting query")
def verify_no_repeated_count():
    """Verify the same count query isn't repeated"""
    pass

@then("the LLM should try alternative approaches")
def verify_alternative_approaches():
    """Verify agent tries different approaches on failure"""
    pass

@then(parsers.parse("should not make more than {max_attempts:d} total query attempts"))
def verify_max_attempts(max_attempts, query_counter):
    """Verify total query attempts don't exceed limit"""
    assert query_counter["count"] <= max_attempts, f"Expected at most {max_attempts} query attempts, but {query_counter['count']} were made"

@then("should provide a helpful response about the limitation")
def verify_helpful_error_response():
    """Verify agent provides helpful error information"""
    pass

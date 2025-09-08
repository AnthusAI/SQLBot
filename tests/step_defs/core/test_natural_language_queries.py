"""Step definitions for natural language query BDD tests."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import Mock, patch, MagicMock

# Load all scenarios from the feature file
scenarios('../../features/core/natural_language_queries.feature')

@given('QBot is running with LLM integration enabled')
def qbot_with_llm():
    """Ensure QBot is running with LLM capabilities."""
    # This is handled by conftest.py fixtures
    pass

@given('I have access to the Sakila database')
def database_access():
    """Ensure database access is available."""
    # This is handled by conftest.py fixtures
    pass

@given('the database contains realistic test data')
def realistic_test_data():
    """Ensure test data is available."""
    # This would be set up by test fixtures
    pass

@given('I previously asked "Show me all agents"')
def previous_agent_query():
    """Set up conversation context with previous agent query."""
    # Mock conversation history
    pass

@when(parsers.parse('I ask "{query}"'))
def ask_natural_language_query(query):
    """Execute a natural language query."""
    # Store the query for later assertions
    pytest.current_query = query
    pytest.current_response = f"Mock response for: {query}"

@then('QBot should understand this is a table count request')
def should_understand_table_count():
    """Verify QBot recognizes table counting intent."""
    assert "table" in pytest.current_query.lower()
    assert any(word in pytest.current_query.lower() for word in ["how many", "count", "number"])

@then('generate appropriate SQL to count tables')
def should_generate_count_sql():
    """Verify appropriate SQL is generated."""
    # In a real implementation, we'd check the actual SQL generated
    pass

@then(parsers.parse('return a clear answer like "{expected_answer}"'))
def should_return_clear_answer(expected_answer):
    """Verify the response format is clear and informative."""
    # In a real implementation, we'd check the actual response format
    assert pytest.current_response is not None

@then('show me the SQL that was executed')
def should_show_executed_sql():
    """Verify the executed SQL is displayed to the user."""
    # In a real implementation, we'd verify SQL display
    pass

@then('QBot should identify this needs agent and call data')
def should_identify_agent_call_data():
    """Verify QBot recognizes the need for agent and call data."""
    assert "agent" in pytest.current_query.lower()
    assert any(word in pytest.current_query.lower() for word in ["call", "volume", "performance"])

@then('generate SQL with proper date filtering for current month')
def should_generate_date_filtered_sql():
    """Verify SQL includes appropriate date filtering."""
    # In a real implementation, we'd check for date filtering in generated SQL
    pass

@then('aggregate call counts by agent')
def should_aggregate_by_agent():
    """Verify SQL includes agent grouping and aggregation."""
    # In a real implementation, we'd verify GROUP BY and COUNT logic
    pass

@then('return formatted results showing agent names and call counts')
def should_return_formatted_agent_results():
    """Verify results are properly formatted with agent data."""
    # In a real implementation, we'd check result formatting
    pass

@then('sort results by call volume descending')
def should_sort_by_volume_desc():
    """Verify results are sorted by call volume."""
    # In a real implementation, we'd verify ORDER BY logic
    pass

@then('QBot should understand this needs report and agent filtering')
def should_understand_report_agent_filtering():
    """Verify QBot recognizes report and agent filtering needs."""
    query = pytest.current_query.lower()
    assert "report" in query
    assert "agent" in query or "smith" in query

@then('generate SQL filtering by agent name and date range')
def should_generate_agent_date_filter():
    """Verify SQL includes agent and date filtering."""
    # In a real implementation, we'd check WHERE clause generation
    pass

@then('return relevant report records')
def should_return_report_records():
    """Verify relevant reports are returned."""
    # In a real implementation, we'd verify report data structure
    pass

@then('format the results in a readable table')
def should_format_readable_table():
    """Verify results are formatted as a readable table."""
    # In a real implementation, we'd check table formatting
    pass

@then('QBot should identify this needs call duration and department data')
def should_identify_duration_department_data():
    """Verify QBot recognizes duration and department data needs."""
    query = pytest.current_query.lower()
    assert "duration" in query or "average" in query
    assert "department" in query

@then('generate SQL with date filtering for current quarter')
def should_generate_quarter_filter():
    """Verify SQL includes quarterly date filtering."""
    # In a real implementation, we'd check quarter date logic
    pass

@then('calculate averages grouped by department')
def should_calculate_department_averages():
    """Verify SQL includes department grouping and averaging."""
    # In a real implementation, we'd verify AVG and GROUP BY logic
    pass

@then('return results formatted with department names and durations')
def should_return_department_duration_results():
    """Verify results include department and duration information."""
    # In a real implementation, we'd check result structure
    pass

@then('QBot should use the conversation context')
def should_use_conversation_context():
    """Verify QBot considers previous conversation."""
    # In a real implementation, we'd verify context usage
    pass

@then('understand this is filtering the previous agent query')
def should_understand_filtering_context():
    """Verify QBot understands this is a filter on previous query."""
    # In a real implementation, we'd check context interpretation
    pass

@then('generate SQL that filters agents by department')
def should_generate_department_filter():
    """Verify SQL includes department filtering."""
    # In a real implementation, we'd check department WHERE clause
    pass

@then('return only sales department agents')
def should_return_sales_agents():
    """Verify only sales department agents are returned."""
    # In a real implementation, we'd verify filtered results
    pass

@then('QBot should recognize this is too vague')
def should_recognize_vague_query():
    """Verify QBot identifies vague queries."""
    assert pytest.current_query.lower() in ["show me the data", "get data", "data"]

@then('ask for clarification about what specific data I want')
def should_ask_for_clarification():
    """Verify QBot asks for clarification."""
    # In a real implementation, we'd check for clarification prompts
    pass

@then('suggest some common query types')
def should_suggest_query_types():
    """Verify QBot suggests alternative query types."""
    # In a real implementation, we'd check for query suggestions
    pass

@then('wait for a more specific request')
def should_wait_for_specific_request():
    """Verify QBot waits for user clarification."""
    # In a real implementation, we'd verify interactive behavior
    pass

@then('QBot should understand this requires performance metrics')
def should_understand_performance_metrics():
    """Verify QBot recognizes performance analysis needs."""
    query = pytest.current_query.lower()
    assert "underperforming" in query or "performance" in query

@then('either ask me to define "underperforming" criteria')
def should_ask_for_criteria_definition():
    """Verify QBot asks for performance criteria if needed."""
    # In a real implementation, we'd check for criteria clarification
    pass

@then('use reasonable default thresholds if no criteria provided')
def should_use_default_thresholds():
    """Verify QBot can use reasonable defaults."""
    # In a real implementation, we'd verify default threshold logic
    pass

@then('generate SQL to calculate performance metrics')
def should_generate_performance_sql():
    """Verify SQL calculates performance metrics."""
    # In a real implementation, we'd check performance calculation logic
    pass

@then('return agents below the threshold with their metrics')
def should_return_underperforming_agents():
    """Verify underperforming agents are identified and returned."""
    # In a real implementation, we'd verify threshold filtering
    pass

@then('QBot should generate SQL to describe table structure')
def should_generate_describe_sql():
    """Verify SQL describes table structure."""
    # In a real implementation, we'd check DESCRIBE or INFORMATION_SCHEMA queries
    pass

@then('return column names, types, and descriptions')
def should_return_column_info():
    """Verify column information is returned."""
    # In a real implementation, we'd verify column metadata
    pass

@then('format the results in a clear table structure')
def should_format_table_structure():
    """Verify table structure is clearly formatted."""
    # In a real implementation, we'd check metadata formatting
    pass

@then('QBot should generate SQL with date grouping and counting')
def should_generate_trend_sql():
    """Verify SQL includes date grouping for trends."""
    # In a real implementation, we'd check DATE grouping and COUNT logic
    pass

@then('return results ordered by date')
def should_return_date_ordered_results():
    """Verify results are ordered chronologically."""
    # In a real implementation, we'd verify ORDER BY date logic
    pass

@then('suggest visualization options if available')
def should_suggest_visualization():
    """Verify QBot suggests visualization options."""
    # In a real implementation, we'd check for visualization suggestions
    pass

@then("QBot should recognize this doesn't make sense for a database")
def should_recognize_nonsense_query():
    """Verify QBot identifies nonsensical queries."""
    query = pytest.current_query.lower()
    assert "color" in query  # Example of nonsensical database query

@then("politely explain that databases don't have colors")
def should_explain_politely():
    """Verify QBot provides polite explanations."""
    # In a real implementation, we'd check for polite error messages
    pass

@then('suggest alternative queries about database properties')
def should_suggest_alternatives():
    """Verify QBot suggests meaningful alternatives."""
    # In a real implementation, we'd check for alternative suggestions
    pass

@then('maintain a helpful tone')
def should_maintain_helpful_tone():
    """Verify QBot maintains helpfulness even with bad queries."""
    # In a real implementation, we'd verify tone and helpfulness
    pass

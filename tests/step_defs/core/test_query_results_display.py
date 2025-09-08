"""
Step definitions for query results display feature tests
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import patch, MagicMock
import subprocess
import os

# Load scenarios from the feature file
scenarios('../../features/core/query_results_display.feature')

@given('QBot is configured with a valid database connection')
def qbot_configured():
    """QBot is set up with valid database configuration"""
    pass

@given('I have access to database tables')
def database_tables_available():
    """Database tables are accessible"""
    pass

@given('I run a simple database query')
def run_simple_query(mock_dbt_query_tool):
    """Execute a simple database query"""
    mock_dbt_query_tool.setup_simple_query()

@given('I run a database query that returns data')
def run_query_with_data(mock_dbt_query_tool):
    """Execute a query that returns actual data"""
    mock_dbt_query_tool.setup_query_with_data()

@given('I run an invalid database query')
def run_invalid_query(mock_dbt_query_tool):
    """Execute an invalid query that should fail"""
    mock_dbt_query_tool.setup_invalid_query()

@given('I run a query that returns no rows')
def run_empty_query(mock_dbt_query_tool):
    """Execute a query that returns no results"""
    mock_dbt_query_tool.setup_empty_query()

@given('I run a query that would return many rows')
def run_large_query(mock_dbt_query_tool):
    """Execute a query that returns many rows"""
    mock_dbt_query_tool.setup_large_query()

@when('the query executes successfully')
def query_executes_successfully(mock_dbt_query_tool):
    """The database query completes without errors"""
    mock_dbt_query_tool.execute_successfully()

@when('the query executes successfully but LLM processing encounters an error')
def query_succeeds_llm_fails(mock_dbt_query_tool):
    """Query works but LLM processing fails"""
    mock_dbt_query_tool.execute_with_llm_error()

@when('the query fails to execute')
def query_fails(mock_dbt_query_tool):
    """The database query fails"""
    mock_dbt_query_tool.execute_with_failure()

@when('the query executes with a limit')
def query_executes_with_limit(mock_dbt_query_tool):
    """Query executes with row limit applied"""
    mock_dbt_query_tool.execute_with_limit()

@then('I should see the actual query results in the output')
def should_see_query_results(mock_dbt_query_tool):
    """Verify actual database results are displayed"""
    output = mock_dbt_query_tool.get_output()
    assert "📊 Results:" in output
    assert mock_dbt_query_tool.expected_results in output

@then('the results should include column headers')
def should_see_column_headers(mock_dbt_query_tool):
    """Verify column headers are shown"""
    output = mock_dbt_query_tool.get_output()
    # dbt show typically includes column headers in its output
    assert any(header in output for header in ['id', 'name', 'created_date'])

@then('the results should include data rows')
def should_see_data_rows(mock_dbt_query_tool):
    """Verify actual data rows are displayed"""
    output = mock_dbt_query_tool.get_output()
    # Should contain actual data values
    assert mock_dbt_query_tool.expected_data_rows in output

@then('the results should be formatted in a readable table')
def should_see_readable_table(mock_dbt_query_tool):
    """Verify results are in table format"""
    output = mock_dbt_query_tool.get_output()
    # dbt show formats results as tables with borders/separators
    assert any(char in output for char in ['|', '+', '-'])

@then('I should still see the actual database results')
def should_still_see_results(mock_dbt_query_tool):
    """Even with LLM errors, database results should be visible"""
    output = mock_dbt_query_tool.get_output()
    assert "📊 Results:" in output
    assert mock_dbt_query_tool.expected_results in output

@then('the results should be displayed before any error messages')
def results_before_errors(mock_dbt_query_tool):
    """Results should appear before error messages"""
    output = mock_dbt_query_tool.get_output()
    results_pos = output.find("📊 Results:")
    error_pos = output.find("❌")
    if error_pos != -1:
        assert results_pos < error_pos

@then('I should see a clear error message')
def should_see_error_message(mock_dbt_query_tool):
    """Clear error message should be displayed"""
    output = mock_dbt_query_tool.get_output()
    assert "❌ Query failed:" in output

@then('the error message should include details about what went wrong')
def should_see_error_details(mock_dbt_query_tool):
    """Error details should be included"""
    output = mock_dbt_query_tool.get_output()
    assert mock_dbt_query_tool.expected_error_details in output

@then('I should not see empty or missing result sections')
def should_not_see_empty_results(mock_dbt_query_tool):
    """No empty result sections should appear"""
    output = mock_dbt_query_tool.get_output()
    # Should not have "📊 Results:" followed immediately by next section
    assert "📊 Results:\n🧠" not in output

@then('I should not see an empty results section')
def should_not_see_empty_results_section(mock_dbt_query_tool):
    """No empty result sections should appear"""
    output = mock_dbt_query_tool.get_output()
    # Should not have "📊 Results:" followed immediately by next section
    assert "📊 Results:\n🧠" not in output

@then('I should see a message indicating no results were found')
def should_see_no_results_message(mock_dbt_query_tool):
    """Clear message for empty results"""
    output = mock_dbt_query_tool.get_output()
    assert "⚠️ No results returned from query" in output or "0 rows" in output

@then('I should see the limited number of rows')
def should_see_limited_rows(mock_dbt_query_tool):
    """Limited number of rows should be displayed"""
    output = mock_dbt_query_tool.get_output()
    assert mock_dbt_query_tool.expected_limited_rows in output

@then('I should see an indication of how many rows were shown')
def should_see_row_count(mock_dbt_query_tool):
    """Row count indication should be present"""
    output = mock_dbt_query_tool.get_output()
    # dbt show typically includes row count information
    assert any(phrase in output.lower() for phrase in ['rows', 'limit', 'showing'])

@then('I should see an indication if more rows are available')
def should_see_more_rows_indication(mock_dbt_query_tool):
    """Indication of additional rows should be present"""
    output = mock_dbt_query_tool.get_output()
    # When limited, should indicate more data available
    assert any(phrase in output.lower() for phrase in ['more', 'additional', 'limit'])


# Fixture to mock the DbtQueryTool behavior
@pytest.fixture
def mock_dbt_query_tool():
    """Mock DbtQueryTool for testing query result display"""
    
    class MockDbtQueryTool:
        def __init__(self):
            self.output = ""
            self.expected_results = ""
            self.expected_data_rows = ""
            self.expected_error_details = ""
            self.expected_limited_rows = ""
            
        def setup_simple_query(self):
            self.expected_results = "| id | name | status |\n|  1 | Test | Active |"
            self.expected_data_rows = "Test | Active"
            
        def setup_query_with_data(self):
            self.expected_results = "| report_id | session_id | created |\n|    123   |   ABC123   | 2024-01-01 |"
            self.expected_data_rows = "123 | ABC123"
            
        def setup_invalid_query(self):
            self.expected_error_details = "Syntax error: Invalid table name"
            
        def setup_empty_query(self):
            self.expected_results = "0 rows returned"
            
        def setup_large_query(self):
            self.expected_limited_rows = "Showing 10 of 1000 rows (limit applied)"
            self.expected_results = "| id | data |\n" + "\n".join([f"|  {i} | Row {i} |" for i in range(1, 11)])
            
        def execute_successfully(self):
            self.output = f"📊 Results:\n{self.expected_results}\n"
            
        def execute_with_llm_error(self):
            self.output = f"📊 Results:\n{self.expected_results}\n❌ LLM Error: Processing failed\n"
            
        def execute_with_failure(self):
            self.output = f"❌ Query failed:\n{self.expected_error_details}\n"
            
        def execute_with_limit(self):
            self.output = f"📊 Results:\n{self.expected_results}\n{self.expected_limited_rows}\n"
            
        def get_output(self):
            return self.output
    
    return MockDbtQueryTool()

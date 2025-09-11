"""
Step definitions for query result management BDD tests
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
import pytest

from qbot.core.query_result_list import QueryResultList, get_query_result_list
from qbot.core.query_result_lookup_tool import create_query_result_lookup_tool
from qbot.core.types import QueryResult, QueryType

# Load scenarios from feature file
scenarios('../../features/core/query_result_management.feature')


@pytest.fixture
def test_session_id():
    """Provide a unique test session ID"""
    return f"test_session_{datetime.now().timestamp()}"


@pytest.fixture
def temp_storage_dir():
    """Provide a temporary directory for test storage"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def query_result_list(test_session_id, temp_storage_dir):
    """Provide a clean QueryResultList for testing"""
    from qbot.core.query_result_list import _query_result_lists
    
    storage_path = temp_storage_dir / f"{test_session_id}.json"
    result_list = QueryResultList(test_session_id, storage_path)
    
    # Register the instance in the global registry so lookup tool can find it
    _query_result_lists[test_session_id] = result_list
    
    yield result_list
    # Test-specific cleanup - remove file directly since clear_session_results is disabled
    if storage_path.exists():
        storage_path.unlink()
    # Remove from global registry
    if test_session_id in _query_result_lists:
        del _query_result_lists[test_session_id]


@pytest.fixture
def lookup_tool(test_session_id):
    """Provide a query result lookup tool for testing"""
    return create_query_result_lookup_tool(test_session_id)


# Background steps

@given("QBot is initialized with a test session")
def qbot_initialized(query_result_list):
    """QBot is initialized with a test session"""
    assert query_result_list.session_id.startswith("test_session_")


@given("the query result list is empty")
def query_result_list_empty(query_result_list):
    """The query result list is empty"""
    assert len(query_result_list) == 0


# Step definitions

@when('I execute a SQL query "SELECT 1 as test_column"')
def execute_test_query(query_result_list):
    """Execute a test SQL query"""
    result = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.1,
        data=[{"test_column": "1"}],
        columns=["test_column"],
        row_count=1
    )
    entry = query_result_list.add_result("SELECT 1 as test_column", result)
    query_result_list._last_entry = entry


@when(parsers.parse('I execute a SQL query "{query}"'))
def execute_sql_query(query_result_list, query):
    """Execute a SQL query with given text"""
    # Mock successful result
    result = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.1,
        data=[{"result": "mock_data"}],
        columns=["result"],
        row_count=1
    )
    entry = query_result_list.add_result(query, result)
    if not hasattr(query_result_list, '_entries_added'):
        query_result_list._entries_added = []
    query_result_list._entries_added.append(entry)


@given(parsers.parse('I execute a SQL query "{query}"'))
def given_execute_sql_query(query_result_list, query):
    """Execute a SQL query with given text (Given step)"""
    # Mock successful result
    result = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.1,
        data=[{"result": "mock_data"}],
        columns=["result"],
        row_count=1
    )
    entry = query_result_list.add_result(query, result)
    if not hasattr(query_result_list, '_entries_added'):
        query_result_list._entries_added = []
    query_result_list._entries_added.append(entry)


@when(parsers.parse('I execute an invalid SQL query "{query}"'))
def execute_invalid_query(query_result_list, query):
    """Execute an invalid SQL query that fails"""
    result = QueryResult(
        success=False,
        query_type=QueryType.SQL,
        execution_time=0.05,
        error="Syntax error in SQL query"
    )
    entry = query_result_list.add_result(query, result)
    query_result_list._last_entry = entry


@when(parsers.parse("I use the query_result_lookup tool with index {index:d}"))
def use_lookup_tool(lookup_tool, index):
    """Use the lookup tool to retrieve a result by index"""
    result = lookup_tool._run(index)
    lookup_tool._last_result = result


@when("I create a new QueryResultList with the same session ID")
def create_new_result_list(test_session_id, temp_storage_dir, query_result_list):
    """Create a new QueryResultList instance with the same session ID"""
    storage_path = temp_storage_dir / f"{test_session_id}.json"
    new_list = QueryResultList(test_session_id, storage_path)
    query_result_list._new_instance = new_list


@given("I have a session \"session_A\"")
def create_session_a(temp_storage_dir):
    """Create session A"""
    storage_path = temp_storage_dir / "session_A.json"
    session_a = QueryResultList("session_A", storage_path)
    create_session_a.session_a = session_a


@given("I have a session \"session_B\"")
def create_session_b(temp_storage_dir):
    """Create session B"""
    storage_path = temp_storage_dir / "session_B.json"
    session_b = QueryResultList("session_B", storage_path)
    create_session_b.session_b = session_b


@when("I execute a query in session_A")
def execute_in_session_a():
    """Execute a query in session A"""
    result = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.1,
        data=[{"data": "session_a"}],
        columns=["data"],
        row_count=1
    )
    create_session_a.session_a.add_result("SELECT 'session_a' as data", result)


@when("I execute a query in session_B")
def execute_in_session_b():
    """Execute a query in session B"""
    result = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.1,
        data=[{"data": "session_b"}],
        columns=["data"],
        row_count=1
    )
    create_session_b.session_b.add_result("SELECT 'session_b' as data", result)


@given("I have executed 3 queries with results")
def execute_three_queries(query_result_list):
    """Execute 3 queries with results"""
    for i in range(1, 4):
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"query_num": str(i)}],
            columns=["query_num"],
            row_count=1
        )
        query_result_list.add_result(f"SELECT {i} as query_num", result)


@given("I have executed 2 queries with results")
def execute_two_queries(query_result_list):
    """Execute 2 queries with results"""
    for i in range(1, 3):
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"query_num": str(i)}],
            columns=["query_num"],
            row_count=1
        )
        query_result_list.add_result(f"SELECT {i} as query_num", result)


# Then steps

@then("the query result should be recorded with index 1")
def check_result_index_1(query_result_list):
    """Check that result was recorded with index 1"""
    entry = query_result_list.get_result(1)
    assert entry is not None
    assert entry.index == 1


@then("the result should include timestamp metadata")
def check_timestamp_metadata(query_result_list):
    """Check that result includes timestamp"""
    entry = query_result_list.get_result(1)
    assert entry.timestamp is not None
    assert isinstance(entry.timestamp, datetime)


@then("the result should contain the original query text")
def check_original_query_text(query_result_list):
    """Check that result contains original query text"""
    entry = query_result_list.get_result(1)
    assert "SELECT" in entry.query_text


@then("the result should contain the structured data")
def check_structured_data(query_result_list):
    """Check that result contains structured data"""
    entry = query_result_list.get_result(1)
    assert entry.result.data is not None
    assert len(entry.result.data) > 0


@then("the query results should have indices 1, 2, and 3")
def check_sequential_indices(query_result_list):
    """Check that results have sequential indices"""
    for i in range(1, 4):
        entry = query_result_list.get_result(i)
        assert entry is not None
        assert entry.index == i


@then("each result should have a unique timestamp")
def check_unique_timestamps(query_result_list):
    """Check that each result has a unique timestamp"""
    timestamps = []
    for i in range(1, 4):
        entry = query_result_list.get_result(i)
        timestamps.append(entry.timestamp)
    
    # All timestamps should be different
    assert len(set(timestamps)) == len(timestamps)


@then("the latest result should be index 3")
def check_latest_result(query_result_list):
    """Check that latest result is index 3"""
    latest = query_result_list.get_latest_result()
    assert latest.index == 3


@then("I should get the full data from query result #2")
def check_lookup_result_2(lookup_tool):
    """Check that lookup returns full data for result #2"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert data["query_index"] == 2
    assert "data" in data
    assert "columns" in data


@then("the data should include the original query text")
def check_lookup_query_text(lookup_tool):
    """Check that lookup result includes original query text"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert "query_text" in data
    assert "SELECT" in data["query_text"]


@then("the data should include all columns and rows")
def check_lookup_columns_rows(lookup_tool):
    """Check that lookup result includes columns and rows"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert "columns" in data
    assert "data" in data
    assert isinstance(data["data"], list)


@then("the data should include execution metadata")
def check_lookup_metadata(lookup_tool):
    """Check that lookup result includes execution metadata"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert "execution_time" in data
    assert "timestamp" in data


@then("I should get an error message about index not found")
def check_lookup_error(lookup_tool):
    """Check that lookup returns error for invalid index"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert "error" in data
    assert "not found" in data["error"]


@then("the error should list available indices [1, 2]")
def check_available_indices(lookup_tool):
    """Check that error lists available indices"""
    result_json = lookup_tool._last_result
    data = json.loads(result_json)
    assert "available_indices" in data
    assert data["available_indices"] == [1, 2]


@then("the result should be marked as failed")
def check_failed_result(query_result_list):
    """Check that result is marked as failed"""
    entry = query_result_list.get_result(1)
    assert not entry.result.success


@then("the result should contain the error message")
def check_error_message(query_result_list):
    """Check that result contains error message"""
    entry = query_result_list.get_result(1)
    assert entry.result.error is not None
    assert "error" in entry.result.error.lower()


@given("the result is recorded with index 1")
def given_result_recorded_index_1(query_result_list):
    """Check that result is recorded with index 1"""
    latest = query_result_list.get_latest_result()
    assert latest is not None
    assert latest.index == 1


@then("the result should still have timestamp metadata")
def check_failed_timestamp(query_result_list):
    """Check that failed result still has timestamp"""
    entry = query_result_list.get_result(1)
    assert entry.timestamp is not None


@then("the query result list should contain 1 result")
def check_persistent_result_count(query_result_list):
    """Check that new instance loaded 1 result"""
    new_list = query_result_list._new_instance
    assert len(new_list) == 1


@then("the result should have index 1")
def check_persistent_index(query_result_list):
    """Check that persisted result has correct index"""
    new_list = query_result_list._new_instance
    entry = new_list.get_result(1)
    assert entry.index == 1


@then("the result data should match the original query")
def check_persistent_data(query_result_list):
    """Check that persisted data matches original"""
    new_list = query_result_list._new_instance
    entry = new_list.get_result(1)
    assert "persistent" in entry.query_text


@then("session_A should have 1 result with index 1")
def check_session_a_result():
    """Check session A has correct result"""
    session_a = create_session_a.session_a
    assert len(session_a) == 1
    entry = session_a.get_result(1)
    assert entry.index == 1


@then("session_B should have 1 result with index 1")
def check_session_b_result():
    """Check session B has correct result"""
    session_b = create_session_b.session_b
    assert len(session_b) == 1
    entry = session_b.get_result(1)
    assert entry.index == 1


@then("the results should be independent")
def check_session_independence():
    """Check that sessions have independent results"""
    session_a = create_session_a.session_a
    session_b = create_session_b.session_b
    
    entry_a = session_a.get_result(1)
    entry_b = session_b.get_result(1)
    
    # Different session IDs
    assert entry_a.session_id != entry_b.session_id
    
    # Different data
    assert entry_a.result.data != entry_b.result.data

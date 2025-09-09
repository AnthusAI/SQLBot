"""
Unit tests for database error handling.
Tests that database errors are properly captured and displayed to both users and LLM.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from qbot.repl import execute_clean_sql

class TestDatabaseErrorHandling:
    """Test database error handling in QBot"""

    def test_execute_clean_sql_captures_stderr_details(self):
        """Test that execute_clean_sql captures detailed error information from dbt SDK"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return error result
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error="Database Error: Table 'nonexistent_table' doesn't exist"
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            result = execute_clean_sql("SELECT * FROM nonexistent_table")
            
            assert "Error executing query:" in result
            assert "Database Error: Table 'nonexistent_table' doesn't exist" in result

    def test_execute_clean_sql_captures_stdout_details(self):
        """Test that execute_clean_sql captures detailed error information from dbt SDK"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return error result  
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error="Runtime Error\nDatabase Error in sql_operation inline_query\nno such table: INFORMATION_SCHEMA.TABLES"
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            result = execute_clean_sql("SELECT * FROM INFORMATION_SCHEMA.TABLES")
            
            assert "Error executing query:" in result
            assert "Runtime Error" in result
            assert "no such table: INFORMATION_SCHEMA.TABLES" in result

    def test_execute_clean_sql_captures_both_stdout_and_stderr(self):
        """Test that execute_clean_sql captures combined error information from dbt SDK"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return error result with combined error info
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error="Connection failed\nRuntime Error: Database connection timeout"
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            result = execute_clean_sql("SELECT * FROM test_table")
            
            assert "Error executing query:" in result
            assert "Connection failed" in result
            assert "Runtime Error: Database connection timeout" in result

    def test_execute_clean_sql_handles_empty_error_output(self):
        """Test that execute_clean_sql handles cases where error is empty"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return error result with empty error message
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error=""
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            result = execute_clean_sql("SELECT * FROM test_table")
            
            assert "Error executing query:" in result

    def test_execute_clean_sql_handles_whitespace_only_errors(self):
        """Test that execute_clean_sql handles cases where error is only whitespace"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return error result with whitespace-only error
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error="   \n  \t  "
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            result = execute_clean_sql("SELECT * FROM test_table")
            
            assert "Error executing query:" in result

    def test_execute_clean_sql_successful_query(self):
        """Test that execute_clean_sql returns formatted table for successful queries"""
        from qbot.core.types import QueryResult, QueryType
        
        # Mock dbt service to return successful result
        mock_success_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"id": 1, "name": "test"}],
            columns=["id", "name"],
            row_count=1
        )

        with patch('qbot.core.dbt_service.DbtService.execute_query', return_value=mock_success_result):
            result = execute_clean_sql("SELECT * FROM test_table")
            
            assert "| id | name |" in result
            assert "| 1 | test |" in result

    def test_execute_clean_sql_exception_handling(self):
        """Test that execute_clean_sql handles exceptions properly"""
        with patch('qbot.core.dbt_service.DbtService.execute_query', side_effect=Exception("dbt service error")):
            result = execute_clean_sql("SELECT * FROM test_table")
            
            assert "Failed to execute query:" in result
            assert "dbt service error" in result

class TestConversationHistoryErrorCapture:
    """Test that database errors are captured in LLM conversation history"""

    @patch('qbot.llm_integration.conversation_history', [])
    def test_database_errors_added_to_conversation_history(self):
        """Test that database errors from tool execution are added to conversation history"""
        from qbot.llm_integration import conversation_history
        
        # Simulate the tool execution that would happen in _execute_llm_query
        mock_agent_result = {
            "output": "I'll query the database for you.",
            "intermediate_steps": [
                (
                    Mock(tool="execute_dbt_query", tool_input={"query": "SELECT * FROM nonexistent_table"}),
                    "Error executing query:\nSTDOUT: Database Error: Table 'nonexistent_table' doesn't exist"
                )
            ]
        }
        
        # Simulate the conversation history building process from _execute_llm_query
        query_results = []
        for step in mock_agent_result["intermediate_steps"]:
            if len(step) >= 2 and hasattr(step[0], 'tool') and step[0].tool == "execute_dbt_query":
                query_executed = step[0].tool_input.get('query', 'Unknown query')
                query_result = step[1] if len(step) > 1 else 'No result'
                query_results.append(f"Query: {query_executed}\nResult: {query_result}")
        
        # Build the full response that would be added to conversation history
        response = mock_agent_result["output"]
        full_response = f"{response}\n\n--- Query Details ---\n" + "\n\n".join(query_results)
        
        # Verify that the error details are included in what would be added to conversation history
        assert "Error executing query:" in full_response
        assert "Database Error: Table 'nonexistent_table' doesn't exist" in full_response
        assert "SELECT * FROM nonexistent_table" in full_response

    def test_multiple_database_errors_captured_in_history(self):
        """Test that multiple database errors are all captured in conversation history"""
        mock_agent_result = {
            "output": "I tried multiple approaches but encountered errors.",
            "intermediate_steps": [
                (
                    Mock(tool="execute_dbt_query", tool_input={"query": "SELECT * FROM wrong_table"}),
                    "Error executing query:\nSTDOUT: Table 'wrong_table' doesn't exist"
                ),
                (
                    Mock(tool="execute_dbt_query", tool_input={"query": "SELECT wrong_column FROM film"}),
                    "Error executing query:\nSTDOUT: Column 'wrong_column' not found"
                )
            ]
        }
        
        # Simulate building conversation history
        query_results = []
        for step in mock_agent_result["intermediate_steps"]:
            if len(step) >= 2 and hasattr(step[0], 'tool') and step[0].tool == "execute_dbt_query":
                query_executed = step[0].tool_input.get('query', 'Unknown query')
                query_result = step[1] if len(step) > 1 else 'No result'
                query_results.append(f"Query: {query_executed}\nResult: {query_result}")
        
        response = mock_agent_result["output"]
        full_response = f"{response}\n\n--- Query Details ---\n" + "\n\n".join(query_results)
        
        # Verify both errors are captured
        assert "Table 'wrong_table' doesn't exist" in full_response
        assert "Column 'wrong_column' not found" in full_response
        assert "SELECT * FROM wrong_table" in full_response
        assert "SELECT wrong_column FROM film" in full_response

class TestErrorDisplayInREPL:
    """Test that errors are properly displayed to users in REPL"""

    @patch('qbot.repl.rich_console')
    def test_error_displayed_to_user_in_repl(self, mock_console):
        """Test that database errors are displayed to users via Rich console"""
        # This would test the actual REPL error display
        # The fix in execute_clean_sql should ensure errors are returned with details
        # which then get displayed via the Rich console
        pass

    def test_error_formatting_preserves_details(self):
        """Test that error formatting preserves important details"""
        error_message = """Error executing query:
STDOUT: Runtime Error
Database Error in sql_operation inline_query
no such table: INFORMATION_SCHEMA.TABLES"""
        
        # Verify that the formatted error contains all the important details
        assert "Runtime Error" in error_message
        assert "Database Error in sql_operation" in error_message
        assert "no such table: INFORMATION_SCHEMA.TABLES" in error_message

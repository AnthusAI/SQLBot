"""
Regression test for the "Object of type Decimal is not JSON serializable" issue.

This test reproduces the exact scenario that was failing and ensures it doesn't regress.
The issue occurred when queries returning monetary amounts (Decimal objects) were
being serialized to JSON for storage and LLM integration.
"""

import pytest
import json
from decimal import Decimal
from unittest.mock import Mock, patch
from datetime import datetime

from qbot.core.types import QueryResult, QueryType
from qbot.core.dbt_service import DbtService
from qbot.core.config import QBotConfig


class TestDecimalSerializationRegression:
    """Regression tests for the original Decimal serialization failure"""
    
    def test_original_payment_query_scenario(self):
        """
        Reproduce the exact scenario that was failing:
        Query with payment amounts returning Decimal objects from agate tables
        """
        # This simulates the exact data structure that was causing the error
        original_failing_data = [
            {"film_id": 1, "title": "ACADEMY DINOSAUR", "revenue": Decimal("67.85")},
            {"film_id": 2, "title": "ACE GOLDFINGER", "revenue": Decimal("58.83")},
            {"film_id": 3, "title": "ADAPTATION HOLES", "revenue": Decimal("58.82")},
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.2,
            data=original_failing_data,
            columns=["film_id", "title", "revenue"],
            row_count=3
        )
        
        # This was the exact operation that was failing
        try:
            # Test direct JSON serialization (this would fail before the fix)
            serialized = result.to_dict()
            json_str = json.dumps(serialized)
            
            # Verify the data was properly converted
            parsed = json.loads(json_str)
            assert isinstance(parsed['data'][0]['revenue'], float)
            assert parsed['data'][0]['revenue'] == 67.85
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail("Decimal serialization regression detected! The original bug has returned.")
            else:
                raise
    
    def test_llm_integration_decimal_scenario(self):
        """
        Test the specific LLM integration code path that was failing
        """
        from qbot.llm_integration import DbtQueryTool
        from qbot.core.query_result_list import QueryResultEntry
        
        # Create the exact type of data that was causing issues
        problematic_data = [
            {"payment_id": 1, "customer_id": 130, "amount": Decimal("4.99")},
            {"payment_id": 2, "customer_id": 459, "amount": Decimal("2.99")},
        ]
        
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.8,
            data=problematic_data,
            columns=["payment_id", "customer_id", "amount"],
            row_count=2
        )
        
        mock_entry = Mock()
        mock_entry.index = 1
        mock_entry.result = mock_result
        
        # Test the key serialization that was failing
        try:
            # The specific operation that was causing JSON serialization errors
            serialized_data = mock_result._serialize_data(mock_result.data)
            
            # Should be able to create the JSON that LLM integration needs
            import json
            result_json = json.dumps({
                "query_index": mock_entry.index,
                "query": "SELECT payment_id, customer_id, amount FROM payment LIMIT 2",
                "success": True,
                "columns": mock_result.columns,
                "data": serialized_data,
                "row_count": mock_result.row_count,
                "execution_time": mock_result.execution_time
            }, indent=2)
            
            # Verify the serialization worked
            parsed = json.loads(result_json)
            assert isinstance(parsed['data'][0]['amount'], float)
            assert parsed['data'][0]['amount'] == 4.99
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail("LLM integration Decimal serialization regression detected!")
            else:
                raise
    
    def test_query_result_storage_decimal_scenario(self):
        """
        Test the query result storage code path that was failing
        """
        from qbot.core.query_result_list import QueryResultList, QueryResultEntry
        
        # Create data with Decimals that would be stored
        revenue_data = [
            {"film_title": "CHAMBER ITALIAN", "total_revenue": Decimal("123.45")},
            {"film_title": "GROSSE WONDERFUL", "total_revenue": Decimal("98.76")},
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=2.1,
            data=revenue_data,
            columns=["film_title", "total_revenue"],
            row_count=2
        )
        
        # Test the storage serialization that was failing
        result_list = QueryResultList(session_id="regression_test")
        
        try:
            # This operation was throwing JSON serialization errors
            entry = result_list.add_result("SELECT film_title, SUM(amount) as total_revenue FROM ...", result)
            
            # Verify the entry was created successfully
            assert entry is not None
            assert entry.result.success is True
            
            # Test that we can retrieve and serialize the entry
            retrieved = result_list.get_result(entry.index)
            assert retrieved is not None
            
            # Test the to_dict serialization that was failing
            entry_dict = retrieved.to_dict()
            json_str = json.dumps(entry_dict)  # This was the failing operation
            
            # Verify the serialized data
            parsed = json.loads(json_str)
            assert isinstance(parsed['result']['data'][0]['total_revenue'], float)
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail("Query result storage Decimal serialization regression detected!")
            else:
                raise
    
    def test_agate_table_extraction_regression(self):
        """
        Test the agate table data extraction that was the root cause
        """
        config = QBotConfig()
        dbt_service = DbtService(config)
        
        # Mock an agate table with the exact structure that was problematic
        mock_table = Mock()
        mock_table.column_names = ["customer_id", "first_name", "last_name", "total_payments"]
        mock_table.rows = [
            [148, "Eleanor", "Hunt", Decimal("194.61")],  # These Decimals were the problem
            [526, "Karl", "Seal", Decimal("190.66")],
            [144, "Clara", "Shaw", Decimal("189.60")],
        ]
        
        # This extraction was preserving Decimal objects before the fix
        try:
            extracted_data = dbt_service._extract_agate_table_data(mock_table)
            
            # Verify that Decimals were converted to floats
            for row in extracted_data['data']:
                assert isinstance(row['total_payments'], float)
            
            # Test that the extracted data is JSON serializable
            json_str = json.dumps(extracted_data)
            parsed = json.loads(json_str)
            assert parsed['data'][0]['total_payments'] == 194.61
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail("Agate table extraction Decimal serialization regression detected!")
            else:
                raise
    
    def test_complex_revenue_query_regression(self):
        """
        Test the exact complex revenue query scenario that was failing
        """
        # This represents the complex query result that was causing issues:
        # "Which actors starred in the top-grossing films?"
        complex_query_data = [
            {
                "film_id": 748,
                "title": "RUGRATS SHAKESPEARE", 
                "revenue": Decimal("231.73"),
                "actor_id": 37,
                "first_name": "VAL",
                "last_name": "BOLGER"
            },
            {
                "film_id": 748,
                "title": "RUGRATS SHAKESPEARE",
                "revenue": Decimal("231.73"), 
                "actor_id": 91,
                "first_name": "CHRISTOPHER",
                "last_name": "BERRY"
            },
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=3.5,
            data=complex_query_data,
            columns=["film_id", "title", "revenue", "actor_id", "first_name", "last_name"],
            row_count=2
        )
        
        # Test all the serialization paths that were failing
        try:
            # 1. QueryResult.to_dict()
            serialized = result.to_dict()
            assert isinstance(serialized['data'][0]['revenue'], float)
            
            # 2. Direct JSON serialization
            json_str = json.dumps(serialized)
            parsed = json.loads(json_str)
            assert parsed['data'][0]['revenue'] == 231.73
            
            # 3. QueryResult.to_json()
            json_str = result.to_json()
            parsed = json.loads(json_str)
            assert parsed['data'][0]['revenue'] == 231.73
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail("Complex revenue query Decimal serialization regression detected!")
            else:
                raise
    
    def test_warning_message_regression(self):
        """
        Test that the specific warning message from the original issue is gone
        """
        from qbot.core.query_result_list import QueryResultList
        import io
        import sys
        
        # Capture stdout to check for the warning message
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            # Create data that would have triggered the warning
            problematic_data = [{"amount": Decimal("4.99")}]
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=problematic_data,
                columns=["amount"],
                row_count=1
            )
            
            # This operation was printing the warning message
            result_list = QueryResultList(session_id="warning_test")
            result_list.add_result("SELECT amount FROM payment", result)
            
            # Get the captured output
            output = captured_output.getvalue()
            
            # The specific warning that was appearing should not be present
            warning_message = "Warning: Failed to save query results to storage: Object of type Decimal is not JSON serializable"
            assert warning_message not in output, f"Regression detected: Warning message appeared: {output}"
            
        finally:
            sys.stdout = old_stdout
    
    @pytest.mark.parametrize("decimal_value,expected_float", [
        (Decimal("0.99"), 0.99),
        (Decimal("123.45"), 123.45),
        (Decimal("999999.99"), 999999.99),
        (Decimal("0.01"), 0.01),
        (Decimal("0"), 0.0),
        (Decimal("-50.25"), -50.25),
    ])
    def test_decimal_conversion_edge_cases(self, decimal_value, expected_float):
        """
        Test various Decimal edge cases that could cause serialization issues
        """
        data = [{"value": decimal_value}]
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=data,
            columns=["value"],
            row_count=1
        )
        
        try:
            serialized = result.to_dict()
            assert isinstance(serialized['data'][0]['value'], float)
            assert serialized['data'][0]['value'] == expected_float
            
            # Ensure JSON serialization works
            json.dumps(serialized)
            
        except TypeError as e:
            if "Object of type Decimal is not JSON serializable" in str(e):
                pytest.fail(f"Decimal serialization failed for value {decimal_value}")
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
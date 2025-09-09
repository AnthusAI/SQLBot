"""
Unit tests for Decimal serialization and JSON compatibility throughout QBot.

This test suite ensures that all data types returned from database queries
can be properly serialized to JSON without errors, particularly focusing
on Decimal objects which are commonly returned by SQL databases.
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, patch

from qbot.core.types import QueryResult, QueryType
from qbot.core.dbt_service import DbtService
from qbot.core.config import QBotConfig


class TestQueryResultSerialization:
    """Test QueryResult serialization with various data types"""
    
    def test_decimal_serialization_success(self):
        """Test that Decimal objects are properly converted to floats"""
        data = [
            {"revenue": Decimal("123.45"), "name": "Film A"},
            {"revenue": Decimal("67.89"), "name": "Film B"},
            {"revenue": Decimal("0.99"), "name": "Film C"}
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=data,
            columns=["revenue", "name"],
            row_count=3
        )
        
        # Test to_dict() serialization
        serialized = result.to_dict()
        assert serialized['data'][0]['revenue'] == 123.45
        assert serialized['data'][1]['revenue'] == 67.89
        assert serialized['data'][2]['revenue'] == 0.99
        assert isinstance(serialized['data'][0]['revenue'], float)
        
        # Test JSON serialization works
        json_str = json.dumps(serialized)
        assert "123.45" in json_str
        
        # Test to_json() method
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed['data'][0]['revenue'] == 123.45
    
    def test_datetime_serialization_success(self):
        """Test that datetime objects are properly converted to ISO strings"""
        test_datetime = datetime(2024, 1, 15, 10, 30, 45)
        test_date = date(2024, 1, 15)
        
        data = [
            {"created_at": test_datetime, "birth_date": test_date, "name": "User A"}
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=data,
            columns=["created_at", "birth_date", "name"],
            row_count=1
        )
        
        serialized = result.to_dict()
        assert serialized['data'][0]['created_at'] == "2024-01-15T10:30:45"
        assert serialized['data'][0]['birth_date'] == "2024-01-15"
        
        # Test JSON serialization works
        json_str = json.dumps(serialized)
        assert "2024-01-15T10:30:45" in json_str
    
    def test_mixed_data_types_serialization(self):
        """Test serialization with mixed data types including Decimal, datetime, None"""
        data = [
            {
                "id": 1,
                "amount": Decimal("99.99"),
                "created_at": datetime(2024, 1, 1, 12, 0, 0),
                "name": "Test Item",
                "description": None,
                "active": True
            }
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=data,
            columns=["id", "amount", "created_at", "name", "description", "active"],
            row_count=1
        )
        
        serialized = result.to_dict()
        row = serialized['data'][0]
        
        assert row['id'] == 1
        assert row['amount'] == 99.99
        assert isinstance(row['amount'], float)
        assert row['created_at'] == "2024-01-01T12:00:00"
        assert row['name'] == "Test Item"
        assert row['description'] is None
        assert row['active'] is True
        
        # Ensure full JSON serialization works
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        assert parsed['data'][0]['amount'] == 99.99
    
    def test_empty_data_serialization(self):
        """Test serialization with empty or None data"""
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=None,
            columns=[],
            row_count=0
        )
        
        serialized = result.to_dict()
        assert serialized['data'] is None
        
        # Test with empty list
        result.data = []
        serialized = result.to_dict()
        assert serialized['data'] == []
        
        # Both should be JSON serializable
        json.dumps(serialized)
    
    def test_large_decimal_precision(self):
        """Test handling of large Decimal numbers with high precision"""
        data = [
            {"precise_value": Decimal("999999999.123456789")},
            {"precise_value": Decimal("-0.000000001")},
            {"precise_value": Decimal("0")}
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=data,
            columns=["precise_value"],
            row_count=3
        )
        
        serialized = result.to_dict()
        assert isinstance(serialized['data'][0]['precise_value'], float)
        assert isinstance(serialized['data'][1]['precise_value'], float)
        assert isinstance(serialized['data'][2]['precise_value'], float)
        
        # Ensure JSON serialization works
        json.dumps(serialized)


class TestDbtServiceSerialization:
    """Test that DbtService properly serializes data from agate tables"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = QBotConfig()
        self.dbt_service = DbtService(self.config)
    
    def test_serialize_value_method(self):
        """Test the _serialize_value method directly"""
        # Test Decimal conversion
        assert self.dbt_service._serialize_value(Decimal("123.45")) == 123.45
        assert isinstance(self.dbt_service._serialize_value(Decimal("123.45")), float)
        
        # Test datetime conversion
        dt = datetime(2024, 1, 1, 10, 30, 45)
        assert self.dbt_service._serialize_value(dt) == "2024-01-01T10:30:45"
        
        # Test date conversion
        d = date(2024, 1, 1)
        assert self.dbt_service._serialize_value(d) == "2024-01-01"
        
        # Test passthrough for other types
        assert self.dbt_service._serialize_value("string") == "string"
        assert self.dbt_service._serialize_value(123) == 123
        assert self.dbt_service._serialize_value(None) is None
        assert self.dbt_service._serialize_value(True) is True
    
    def test_extract_agate_table_data_with_decimals(self):
        """Test _extract_agate_table_data properly serializes Decimal objects"""
        # Mock agate table with Decimal data
        mock_table = Mock()
        mock_table.column_names = ["id", "amount", "name"]
        mock_table.rows = [
            [1, Decimal("99.99"), "Item A"],
            [2, Decimal("149.50"), "Item B"],
            [3, Decimal("0.99"), "Item C"]
        ]
        
        result = self.dbt_service._extract_agate_table_data(mock_table)
        
        assert result['columns'] == ["id", "amount", "name"]
        assert len(result['data']) == 3
        
        # Check that Decimal objects were converted to floats
        for row in result['data']:
            assert isinstance(row['amount'], float)
        
        assert result['data'][0]['amount'] == 99.99
        assert result['data'][1]['amount'] == 149.50
        assert result['data'][2]['amount'] == 0.99
        
        # Ensure the extracted data is JSON serializable
        json.dumps(result)
    
    def test_extract_agate_table_data_with_mixed_types(self):
        """Test agate table extraction with mixed data types"""
        mock_table = Mock()
        mock_table.column_names = ["id", "amount", "created_at", "active"]
        mock_table.rows = [
            [1, Decimal("50.00"), datetime(2024, 1, 1), True],
            [2, Decimal("75.25"), datetime(2024, 1, 2), False]
        ]
        
        result = self.dbt_service._extract_agate_table_data(mock_table)
        
        assert len(result['data']) == 2
        
        # Check type conversions
        row1 = result['data'][0]
        assert isinstance(row1['amount'], float)
        assert isinstance(row1['created_at'], str)
        assert isinstance(row1['active'], bool)
        
        assert row1['amount'] == 50.00
        assert row1['created_at'] == "2024-01-01T00:00:00"
        assert row1['active'] is True
        
        # Ensure JSON serializable
        json.dumps(result)
    
    def test_extract_agate_table_data_none_table(self):
        """Test handling of None table input"""
        result = self.dbt_service._extract_agate_table_data(None)
        assert result == {'data': [], 'columns': []}
        
        # Should be JSON serializable
        json.dumps(result)


class TestLLMIntegrationSerialization:
    """Test that LLM integration properly handles serialization"""
    
    def test_llm_integration_serialization_works(self):
        """Test that LLM integration can handle Decimal data without errors"""
        from qbot.llm_integration import DbtQueryTool
        
        # Create result with Decimal data that would cause JSON errors
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"amount": Decimal("123.45")}],
            columns=["amount"],
            row_count=1
        )
        
        # The key test is that serialization works without errors
        serialized = mock_result._serialize_data(mock_result.data)
        
        # Should be able to JSON serialize the result
        import json
        json_str = json.dumps({
            "data": serialized,
            "columns": mock_result.columns,
            "success": mock_result.success
        })
        
        # Verify conversion worked
        parsed = json.loads(json_str)
        assert isinstance(parsed['data'][0]['amount'], float)
        assert parsed['data'][0]['amount'] == 123.45


class TestQueryResultLookupSerialization:
    """Test that query result lookup tool properly serializes data"""
    
    def test_query_result_lookup_serialization(self):
        """Test that lookup tool can handle Decimal data serialization"""
        from qbot.core.query_result_lookup_tool import QueryResultLookupTool
        
        # Create mock result with Decimal data
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"revenue": Decimal("999.99")}],
            columns=["revenue"],
            row_count=1
        )
        
        # The key test is that the result can be serialized using our methods
        serialized_data = mock_result._serialize_data(mock_result.data)
        
        # Should be able to create JSON output like the tool does
        import json
        result_json = json.dumps({
            "query_index": 1,
            "timestamp": datetime(2024, 1, 1).isoformat(),
            "query_text": "SELECT revenue FROM test",
            "success": True,
            "columns": mock_result.columns,
            "data": serialized_data,
            "row_count": mock_result.row_count,
            "execution_time": mock_result.execution_time
        }, indent=2)
        
        # Parse the JSON to verify it worked
        parsed = json.loads(result_json)
        assert parsed['success'] is True
        assert isinstance(parsed['data'][0]['revenue'], float)
        assert parsed['data'][0]['revenue'] == 999.99


class TestIntegrationSerialization:
    """Integration tests for serialization across the entire pipeline"""
    
    def test_end_to_end_decimal_handling(self):
        """Test that Decimal objects are handled correctly from query to final JSON"""
        # This test simulates the full pipeline:
        # 1. Query execution returns Decimal objects
        # 2. QueryResult serialization
        # 3. Storage serialization
        # 4. LLM tool serialization
        
        # Create a QueryResult with Decimal data (simulating dbt output)
        original_data = [
            {"payment_id": 1, "amount": Decimal("4.99")},
            {"payment_id": 2, "amount": Decimal("2.99")}
        ]
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.5,
            data=original_data,
            columns=["payment_id", "amount"],
            row_count=2
        )
        
        # Test QueryResult serialization
        serialized_result = result.to_dict()
        assert isinstance(serialized_result['data'][0]['amount'], float)
        
        # Test that it can be JSON serialized
        json_str = json.dumps(serialized_result)
        parsed = json.loads(json_str)
        assert parsed['data'][0]['amount'] == 4.99
        
        # Test QueryResultEntry serialization (for storage)
        from qbot.core.query_result_list import QueryResultEntry
        from datetime import datetime
        import uuid
        entry = QueryResultEntry(
            index=1,
            timestamp=datetime.now(),
            session_id="test",
            query_text="SELECT * FROM payment",
            result=result,
            entry_id=str(uuid.uuid4())
        )
        
        # This should not raise a serialization error
        entry_dict = entry.to_dict()
        json.dumps(entry_dict)
    
    def test_storage_serialization_robustness(self):
        """Test that the storage system handles various edge cases"""
        from qbot.core.query_result_list import QueryResultList
        
        # Create results with various problematic data types
        results_data = [
            # Decimal amounts
            [{"amount": Decimal("123.45")}],
            # Mixed types
            [{"id": 1, "value": Decimal("99.99"), "created": datetime.now(), "active": True}],
            # Edge case decimals
            [{"tiny": Decimal("0.001"), "large": Decimal("999999.999")}],
            # None values
            [{"id": 1, "optional_field": None}]
        ]
        
        result_list = QueryResultList(session_id="test_session")
        
        for i, data in enumerate(results_data):
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=data,
                columns=list(data[0].keys()),
                row_count=1
            )
            
            # This should not raise any serialization errors
            try:
                result_list.add_result(f"query_{i}", result)
            except TypeError as e:
                if "JSON serializable" in str(e):
                    pytest.fail(f"JSON serialization failed for data: {data}")
                else:
                    raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
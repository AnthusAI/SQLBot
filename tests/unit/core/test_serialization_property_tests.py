"""
Property-based tests for serialization robustness.

Tests various data combinations to ensure that serialization
works correctly across all edge cases.
"""

import json
import random
from decimal import Decimal
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import pytest

from sqlbot.core.types import QueryResult, QueryType
from sqlbot.core.dbt_service import DbtService
from sqlbot.core.config import SQLBotConfig


def generate_decimal_values():
    """Generate various Decimal values for testing"""
    return [
        Decimal("0.01"), Decimal("0.99"), Decimal("1.00"),
        Decimal("99.99"), Decimal("123.45"), Decimal("999.99"),
        Decimal("1000.00"), Decimal("9999.99"), Decimal("99999.99"),
        Decimal("0"), Decimal("-50.25"), Decimal("-999.99"),
        Decimal("0.001"), Decimal("999999.999")
    ]


def generate_database_values():
    """Generate various values commonly found in database results"""
    return [
        # Integers (IDs, counts)
        0, 1, 42, 100, 999, 1000, 999999,
        # Strings (names, descriptions)
        "", "test", "John Doe", "Long description text with spaces",
        "Special chars: @#$%", "Unicode: café naïve",
        # Booleans
        True, False,
        # None values
        None,
        # Decimals (monetary amounts)
        *generate_decimal_values(),
        # Datetimes
        datetime(2020, 1, 1), datetime(2024, 6, 15, 10, 30, 45),
        datetime.now(),
        # Dates
        date(2020, 1, 1), date(2024, 12, 31), date.today(),
        # Floats
        0.0, 1.5, 99.99, -50.25, 1000000.0
    ]


def generate_query_results():
    """Generate various QueryResult objects for testing"""
    database_values = generate_database_values()
    results = []
    
    # Success cases
    for num_rows in [0, 1, 3, 10]:
        for num_cols in [1, 3, 5]:
            if num_rows == 0:
                data = []
                columns = []
            else:
                columns = [f"col_{i}" for i in range(num_cols)]
                data = []
                for _ in range(num_rows):
                    row = {}
                    for col in columns:
                        row[col] = random.choice(database_values)
                    data.append(row)
            
            result = QueryResult(
                success=True,
                query_type=random.choice(list(QueryType)),
                execution_time=random.uniform(0.001, 30.0),
                data=data,
                columns=columns,
                row_count=len(data)
            )
            results.append(result)
    
    # Failure cases
    for _ in range(3):
        result = QueryResult(
            success=False,
            query_type=random.choice(list(QueryType)),
            execution_time=random.uniform(0.001, 30.0),
            error=f"Test error message {random.randint(1, 100)}"
        )
        results.append(result)
    
    return results


class TestSerializationPropertyTests:
    """Property-based tests for serialization robustness"""
    
    def test_query_result_serialization_always_works(self):
        """Property: QueryResult serialization should never fail with TypeError"""
        query_results = generate_query_results()
        
        for query_result in query_results:
            try:
                # Test to_dict() method
                serialized = query_result.to_dict()
                
                # Should be JSON serializable
                json_str = json.dumps(serialized)
                
                # Should be parseable
                parsed = json.loads(json_str)
                
                # Basic structure should be preserved
                assert isinstance(parsed, dict)
                assert 'success' in parsed
                assert 'query_type' in parsed
                assert 'execution_time' in parsed
                
                if query_result.success and query_result.data:
                    assert 'data' in parsed
                    assert 'columns' in parsed
                    assert isinstance(parsed['data'], list)
                    
                    # All values in data should be JSON-serializable types
                    for row in parsed['data']:
                        for value in row.values():
                            assert isinstance(value, (str, int, float, bool, type(None))), \
                                f"Non-JSON type found: {type(value)}"
                
            except TypeError as e:
                if "JSON serializable" in str(e):
                    pytest.fail(f"Serialization failed for QueryResult: {query_result}. Error: {e}")
                else:
                    raise
    
    def test_decimal_serialization_property(self):
        """Property: All Decimal values should be convertible to JSON-serializable types"""
        decimal_values = generate_decimal_values()
        
        for decimal_val in decimal_values:
            data = [{"amount": decimal_val}]
            
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=data,
                columns=["amount"],
                row_count=1
            )
            
            serialized = result.to_dict()
            
            # Decimal should become float
            assert isinstance(serialized['data'][0]['amount'], float), \
                f"Decimal not converted to float: {decimal_val}"
            
            # Should be JSON serializable
            json.dumps(serialized)
    
    def test_datetime_serialization_property(self):
        """Property: All datetime values should be convertible to ISO strings"""
        datetime_values = [
            datetime(2020, 1, 1), datetime(2024, 6, 15, 10, 30, 45),
            datetime.now(), datetime(2030, 12, 31, 23, 59, 59)
        ]
        
        for dt in datetime_values:
            data = [{"created_at": dt}]
            
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=data,
                columns=["created_at"],
                row_count=1
            )
            
            serialized = result.to_dict()
            
            # Datetime should become string
            assert isinstance(serialized['data'][0]['created_at'], str)
            # Should be valid ISO format
            datetime.fromisoformat(serialized['data'][0]['created_at'])
            
            # Should be JSON serializable
            json.dumps(serialized)
    
    def test_mixed_data_serialization_property(self):
        """Property: Mixed data types should always be serializable"""
        database_values = generate_database_values()
        
        # Test combinations of different data types
        for i in range(10):  # Test 10 random combinations
            columns = [f"col_{j}" for j in range(3)]  # 3 columns
            data = []
            
            # Generate 3 rows with mixed data types
            for _ in range(3):
                row = {}
                for col in columns:
                    row[col] = random.choice(database_values)
                data.append(row)
            
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=data,
                columns=columns,
                row_count=len(data)
            )
            
            try:
                serialized = result.to_dict()
                json_str = json.dumps(serialized)
                parsed = json.loads(json_str)
                
                # Verify structure is preserved
                assert len(parsed['data']) == len(data)
                assert parsed['columns'] == columns
                
            except TypeError as e:
                if "JSON serializable" in str(e):
                    pytest.fail(f"Mixed data serialization failed. Data: {data}. Error: {e}")
                else:
                    raise
    
    def test_dbt_service_serialize_value_property(self):
        """Property: DbtService._serialize_value should handle all common database types"""
        config = SQLBotConfig()
        dbt_service = DbtService(config)
        
        test_values = [
            # Decimal values
            Decimal("123.45"), Decimal("0.99"), Decimal("999999.99"),
            # Datetime values
            datetime(2024, 1, 1, 10, 30, 45), datetime.now(),
            # Date values
            date(2024, 1, 1), date.today(),
            # Other types that should pass through
            "string", 123, 456.78, True, False, None,
        ]
        
        for value in test_values:
            try:
                serialized = dbt_service._serialize_value(value)
                # Should be JSON serializable
                json.dumps(serialized)
                
                # Type should be appropriate
                if isinstance(value, Decimal):
                    assert isinstance(serialized, float)
                elif isinstance(value, (datetime, date)):
                    assert isinstance(serialized, str)
                else:
                    # Other types should pass through unchanged
                    assert serialized == value
                    
            except Exception as e:
                pytest.fail(f"_serialize_value failed for {type(value).__name__} value {value}: {e}")
    
    def test_agate_table_extraction_property(self):
        """Property: Agate table extraction should handle any combination of database values"""
        config = SQLBotConfig()
        dbt_service = DbtService(config)
        
        database_values = generate_database_values()
        
        # Test various combinations of columns and values
        for num_cols in [1, 3, 5]:
            columns = [f"col_{i}" for i in range(num_cols)]
            
            # Test with different value combinations
            for _ in range(5):  # 5 test cases per column count
                values = [random.choice(database_values) for _ in range(num_cols)]
                
                # Create mock agate table structure
                from unittest.mock import Mock
                mock_table = Mock()
                mock_table.column_names = columns
                mock_table.rows = [values]  # Single row for simplicity
                
                try:
                    result = dbt_service._extract_agate_table_data(mock_table)
                    
                    # Should have correct structure
                    assert 'data' in result
                    assert 'columns' in result
                    assert result['columns'] == columns
                    assert len(result['data']) == 1
                    
                    # Should be JSON serializable
                    json.dumps(result)
                    
                    # All values should be serializable types
                    row = result['data'][0]
                    for col, value in row.items():
                        assert isinstance(value, (str, int, float, bool, type(None))), \
                            f"Non-serializable type {type(value)} for column {col}"
                        
                except Exception as e:
                    pytest.fail(f"Agate table extraction failed for columns {columns} with values {values}: {e}")
    
    def test_specific_decimal_edge_cases(self):
        """Test specific Decimal edge cases that might cause issues"""
        edge_case_decimals = [
            Decimal("0"), Decimal("999999999.99"), Decimal("-123.45"),
            Decimal("0.001"), Decimal("1000000.000"), Decimal("-0.01")
        ]
        
        for decimal_value in edge_case_decimals:
            result = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=0.1,
                data=[{"value": decimal_value}],
                columns=["value"],
                row_count=1
            )
            
            serialized = result.to_dict()
            assert isinstance(serialized['data'][0]['value'], float)
            
            # Should round-trip through JSON
            json_str = json.dumps(serialized)
            parsed = json.loads(json_str)
            assert isinstance(parsed['data'][0]['value'], float)
    
    def test_large_dataset_serialization_performance(self):
        """Test that serialization works efficiently with larger datasets"""
        # Create a larger dataset with mixed types including Decimals
        large_data = []
        for i in range(100):  # 100 rows
            large_data.append({
                "id": i,
                "amount": Decimal(f"{random.uniform(0.01, 999.99):.2f}"),
                "name": f"Item {i}",
                "active": i % 2 == 0,
                "created_at": datetime(2024, 1, 1) + (datetime.now() - datetime(2024, 1, 1)) * random.random(),
                "optional": None if i % 10 == 0 else f"Optional {i}"
            })
        
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.5,
            data=large_data,
            columns=["id", "amount", "name", "active", "created_at", "optional"],
            row_count=len(large_data)
        )
        
        # Should serialize without errors
        serialized = result.to_dict()
        
        # All amounts should be floats
        for row in serialized['data']:
            assert isinstance(row['amount'], float)
            assert isinstance(row['created_at'], str)
        
        # Should be JSON serializable
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        assert len(parsed['data']) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
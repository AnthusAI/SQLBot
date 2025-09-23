"""
Unit tests for the data export functionality
"""

import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from sqlbot.core.export import DataExporter, export_latest_result, export_result_by_index
from sqlbot.core.types import QueryResult, QueryType
from sqlbot.core.query_result_list import QueryResultList, QueryResultEntry


@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for exports"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_query_result():
    """Create a mock successful query result with test data"""
    return QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=1.23,
        data=[
            ["John", "Doe", 30, "Engineer"],
            ["Jane", "Smith", 25, "Designer"],
            ["Bob", "Johnson", 35, "Manager"]
        ],
        columns=["first_name", "last_name", "age", "job_title"],
        row_count=3
    )


@pytest.fixture
def mock_failed_query_result():
    """Create a mock failed query result"""
    return QueryResult(
        success=False,
        query_type=QueryType.SQL,
        execution_time=0.5,
        error="Table not found"
    )


@pytest.fixture
def mock_query_result_no_data():
    """Create a mock successful query result with no data"""
    return QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=0.8,
        data=[],
        columns=["id", "name"],
        row_count=0
    )


@pytest.fixture
def populated_query_result_list(temp_export_dir, mock_query_result, mock_failed_query_result):
    """Create a QueryResultList with test data"""
    session_id = "test_session"
    storage_path = Path(temp_export_dir) / f"{session_id}.json"

    result_list = QueryResultList(session_id, storage_path)

    # Add successful query result
    result_list.add_result("SELECT * FROM users", mock_query_result)

    # Add failed query result
    result_list.add_result("SELECT * FROM nonexistent_table", mock_failed_query_result)

    # Add another successful query result
    mock_query_result_2 = QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=2.1,
        data=[["Product A", 100], ["Product B", 200]],
        columns=["product_name", "quantity"],
        row_count=2
    )
    result_list.add_result("SELECT * FROM products", mock_query_result_2)

    return result_list


class TestDataExporter:
    """Test the DataExporter class"""

    def test_init(self, populated_query_result_list):
        """Test DataExporter initialization"""
        exporter = DataExporter("test_session")
        assert exporter.session_id == "test_session"
        assert exporter.query_results is not None

    def test_export_latest_success_csv(self, populated_query_result_list, temp_export_dir):
        """Test exporting latest result to CSV"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("csv", temp_export_dir)

            assert result["success"] is True
            assert result["format"] == "csv"
            assert result["row_count"] == 2
            assert result["columns"] == ["product_name", "quantity"]
            assert result["query_index"] == 3  # Latest query index
            assert temp_export_dir in result["file_path"]
            assert result["file_path"].endswith(".csv")

            # Verify file was created
            file_path = Path(result["file_path"])
            assert file_path.exists()

            # Verify file contents
            df = pd.read_csv(file_path)
            assert len(df) == 2
            assert list(df.columns) == ["product_name", "quantity"]
            assert df.iloc[0]["product_name"] == "Product A"

    def test_export_latest_success_excel(self, populated_query_result_list, temp_export_dir):
        """Test exporting latest result to Excel"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("excel", temp_export_dir)

            assert result["success"] is True
            assert result["format"] == "excel"
            assert result["file_path"].endswith(".xlsx")

            # Verify file was created and can be read
            file_path = Path(result["file_path"])
            assert file_path.exists()

            df = pd.read_excel(file_path, engine='openpyxl')
            assert len(df) == 2
            assert list(df.columns) == ["product_name", "quantity"]

    def test_export_latest_success_parquet(self, populated_query_result_list, temp_export_dir):
        """Test exporting latest result to Parquet"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("parquet", temp_export_dir)

            assert result["success"] is True
            assert result["format"] == "parquet"
            assert result["file_path"].endswith(".parquet")

            # Verify file was created and can be read
            file_path = Path(result["file_path"])
            assert file_path.exists()

            df = pd.read_parquet(file_path)
            assert len(df) == 2
            assert list(df.columns) == ["product_name", "quantity"]

    def test_export_latest_no_results(self, temp_export_dir):
        """Test exporting when no results exist"""
        empty_result_list = QueryResultList("empty_session")

        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = empty_result_list

            exporter = DataExporter("empty_session")
            result = exporter.export_latest("csv", temp_export_dir)

            assert result["success"] is False
            assert "No query results available" in result["error"]
            assert result["file_path"] is None

    def test_export_latest_failed_query(self, temp_export_dir):
        """Test exporting when latest result is a failed query"""
        session_id = "failed_session"
        result_list = QueryResultList(session_id)

        failed_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.5,
            error="Syntax error"
        )
        result_list.add_result("SELECT * FROM bad_query", failed_result)

        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = result_list

            exporter = DataExporter(session_id)
            result = exporter.export_latest("csv", temp_export_dir)

            assert result["success"] is False
            assert "Cannot export failed query result" in result["error"]
            assert result["file_path"] is None

    def test_export_latest_no_data(self, temp_export_dir):
        """Test exporting when latest result has no data"""
        session_id = "no_data_session"
        result_list = QueryResultList(session_id)

        no_data_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.5,
            data=None,
            columns=["id"],
            row_count=0
        )
        result_list.add_result("SELECT * FROM empty_table", no_data_result)

        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = result_list

            exporter = DataExporter(session_id)
            result = exporter.export_latest("csv", temp_export_dir)

            assert result["success"] is False
            assert "No data available" in result["error"]
            assert result["file_path"] is None

    def test_export_latest_default_location(self, populated_query_result_list):
        """Test exporting with default location (./tmp)"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("csv")  # No location specified

            assert result["success"] is True
            assert "tmp" in result["file_path"]

            # Clean up created file
            Path(result["file_path"]).unlink(missing_ok=True)

    def test_export_by_index_success(self, populated_query_result_list, temp_export_dir):
        """Test exporting specific result by index"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_by_index(1, "csv", temp_export_dir)  # First successful result

            assert result["success"] is True
            assert result["query_index"] == 1
            assert result["row_count"] == 3
            assert result["columns"] == ["first_name", "last_name", "age", "job_title"]

    def test_export_by_index_not_found(self, populated_query_result_list, temp_export_dir):
        """Test exporting non-existent index"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_by_index(999, "csv", temp_export_dir)

            assert result["success"] is False
            assert "No query result found with index 999" in result["error"]
            assert result["file_path"] is None

    def test_export_by_index_failed_query(self, populated_query_result_list, temp_export_dir):
        """Test exporting failed query by index"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_by_index(2, "csv", temp_export_dir)  # Failed query index

            assert result["success"] is False
            assert "Cannot export failed query result (index 2)" in result["error"]
            assert result["file_path"] is None

    def test_invalid_export_format(self, populated_query_result_list, temp_export_dir):
        """Test exporting with invalid format"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("invalid_format", temp_export_dir)

            assert result["success"] is False
            assert "Unsupported export format: invalid_format" in result["error"]
            assert result["file_path"] is None

    def test_get_available_results(self, populated_query_result_list):
        """Test getting list of available results"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            results = exporter.get_available_results()

            assert len(results) == 3

            # Check first result (successful)
            assert results[0]["index"] == 1
            assert results[0]["exportable"] is True
            assert results[0]["row_count"] == 3
            assert results[0]["columns"] == ["first_name", "last_name", "age", "job_title"]

            # Check second result (failed)
            assert results[1]["index"] == 2
            assert results[1]["exportable"] is False
            assert "Failed query or no data" in results[1]["reason"]

            # Check third result (successful)
            assert results[2]["index"] == 3
            assert results[2]["exportable"] is True
            assert results[2]["row_count"] == 2

    def test_create_dataframe_with_columns(self, mock_query_result):
        """Test creating DataFrame when columns are provided"""
        exporter = DataExporter("test_session")
        df = exporter._create_dataframe(mock_query_result)

        assert len(df) == 3
        assert list(df.columns) == ["first_name", "last_name", "age", "job_title"]
        assert df.iloc[0]["first_name"] == "John"
        assert df.iloc[0]["age"] == 30

    def test_create_dataframe_without_columns(self):
        """Test creating DataFrame when no columns are provided"""
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0,
            data=[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            columns=None,
            row_count=2
        )

        exporter = DataExporter("test_session")
        df = exporter._create_dataframe(result)

        assert len(df) == 2
        assert "name" in df.columns
        assert "age" in df.columns

    def test_create_dataframe_empty(self):
        """Test creating DataFrame with empty data"""
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0,
            data=None,
            columns=["id", "name"],
            row_count=0
        )

        exporter = DataExporter("test_session")
        df = exporter._create_dataframe(result)

        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)


class TestConvenienceFunctions:
    """Test the convenience functions"""

    def test_export_latest_result_function(self, populated_query_result_list, temp_export_dir):
        """Test the export_latest_result convenience function"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            result = export_latest_result("test_session", "csv", temp_export_dir)

            assert result["success"] is True
            assert result["format"] == "csv"
            assert result["row_count"] == 2

    def test_export_result_by_index_function(self, populated_query_result_list, temp_export_dir):
        """Test the export_result_by_index convenience function"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            result = export_result_by_index("test_session", 1, "excel", temp_export_dir)

            assert result["success"] is True
            assert result["format"] == "excel"
            assert result["query_index"] == 1


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_export_with_pandas_error(self, populated_query_result_list, temp_export_dir):
        """Test handling of pandas-related errors"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                mock_get_list.return_value = populated_query_result_list
                mock_to_csv.side_effect = Exception("Pandas error")

                exporter = DataExporter("test_session")
                result = exporter.export_latest("csv", temp_export_dir)

                assert result["success"] is False
                assert "Export failed: Pandas error" in result["error"]
                assert result["file_path"] is None

    def test_export_with_file_permission_error(self, populated_query_result_list):
        """Test handling of file permission errors"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            # Use a read-only directory path that should cause permission error
            readonly_path = "/root/readonly"  # This should fail on most systems

            exporter = DataExporter("test_session")
            result = exporter.export_latest("csv", readonly_path)

            # The exact error message may vary by OS, but it should fail
            assert result["success"] is False
            assert result["file_path"] is None
            assert "error" in result


class TestFileNaming:
    """Test file naming conventions"""

    def test_filename_format(self, populated_query_result_list, temp_export_dir):
        """Test that filenames follow expected format"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")
            result = exporter.export_latest("csv", temp_export_dir)

            assert result["success"] is True

            filename = Path(result["file_path"]).name

            # Should be in format: sqlbot_query_{index}_{timestamp}.csv
            assert filename.startswith("sqlbot_query_3_")  # Index 3 is latest
            assert filename.endswith(".csv")

            # Check timestamp format (YYYYMMDD_HHMMSS)
            parts = filename.replace("sqlbot_query_3_", "").replace(".csv", "")
            assert len(parts) == 15  # YYYYMMDD_HHMMSS format
            assert "_" in parts

            date_part, time_part = parts.split("_")
            assert len(date_part) == 8  # YYYYMMDD
            assert len(time_part) == 6   # HHMMSS

    def test_different_formats_different_extensions(self, populated_query_result_list, temp_export_dir):
        """Test that different formats get correct file extensions"""
        with patch('sqlbot.core.export.get_query_result_list') as mock_get_list:
            mock_get_list.return_value = populated_query_result_list

            exporter = DataExporter("test_session")

            csv_result = exporter.export_latest("csv", temp_export_dir)
            excel_result = exporter.export_by_index(1, "excel", temp_export_dir)
            parquet_result = exporter.export_by_index(1, "parquet", temp_export_dir)

            assert csv_result["file_path"].endswith(".csv")
            assert excel_result["file_path"].endswith(".xlsx")
            assert parquet_result["file_path"].endswith(".parquet")
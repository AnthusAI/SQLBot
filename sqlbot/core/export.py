"""
Data Export Functionality for SQLBot

This module provides data export capabilities for query results in multiple formats.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import pandas as pd

from .types import QueryResult
from .query_result_list import QueryResultEntry, get_query_result_list


ExportFormat = Literal["csv", "excel", "parquet"]


class DataExporter:
    """Handles exporting query results to various file formats"""

    def __init__(self, session_id: str):
        """
        Initialize DataExporter

        Args:
            session_id: Current session ID for accessing query results
        """
        self.session_id = session_id
        self.query_results = get_query_result_list(session_id)

    def export_latest(
        self,
        format: ExportFormat = "csv",
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export the most recent query result to specified format

        Args:
            format: Export format - "csv", "excel", or "parquet"
            location: Directory path to save file (defaults to "./tmp")

        Returns:
            Dictionary with export result information
        """
        # Get the most recent query result
        latest_result = self.query_results.get_latest_result()

        if not latest_result:
            return {
                "success": False,
                "error": "No query results available to export",
                "file_path": None
            }

        if not latest_result.result.success:
            return {
                "success": False,
                "error": "Cannot export failed query result",
                "file_path": None
            }

        if not latest_result.result.data:
            return {
                "success": False,
                "error": "No data available in the latest query result",
                "file_path": None
            }

        return self._export_result_entry(latest_result, format, location)

    def export_by_index(
        self,
        index: int,
        format: ExportFormat = "csv",
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a specific query result by index

        Args:
            index: Query result index (1-based)
            format: Export format - "csv", "excel", or "parquet"
            location: Directory path to save file (defaults to "./tmp")

        Returns:
            Dictionary with export result information
        """
        result_entry = self.query_results.get_result(index)

        if not result_entry:
            return {
                "success": False,
                "error": f"No query result found with index {index}",
                "file_path": None
            }

        if not result_entry.result.success:
            return {
                "success": False,
                "error": f"Cannot export failed query result (index {index})",
                "file_path": None
            }

        if not result_entry.result.data:
            return {
                "success": False,
                "error": f"No data available in query result {index}",
                "file_path": None
            }

        return self._export_result_entry(result_entry, format, location)

    def _export_result_entry(
        self,
        result_entry: QueryResultEntry,
        format: ExportFormat,
        location: Optional[str]
    ) -> Dict[str, Any]:
        """
        Internal method to export a query result entry

        Args:
            result_entry: The QueryResultEntry to export
            format: Export format
            location: Directory path to save file

        Returns:
            Dictionary with export result information
        """
        try:
            # Set up export location
            if location is None:
                location = "./tmp"

            export_dir = Path(location)
            export_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp and query index
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"sqlbot_query_{result_entry.index}_{timestamp}"

            # Convert data to pandas DataFrame
            df = self._create_dataframe(result_entry.result)

            # Export based on format
            if format == "csv":
                file_path = export_dir / f"{base_filename}.csv"
                df.to_csv(file_path, index=False)
            elif format == "excel":
                file_path = export_dir / f"{base_filename}.xlsx"
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif format == "parquet":
                file_path = export_dir / f"{base_filename}.parquet"
                df.to_parquet(file_path, index=False)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported export format: {format}",
                    "file_path": None
                }

            return {
                "success": True,
                "file_path": str(file_path),
                "format": format,
                "row_count": len(df),
                "columns": list(df.columns),
                "query_index": result_entry.index,
                "export_timestamp": timestamp
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Export failed: {str(e)}",
                "file_path": None
            }

    def _create_dataframe(self, query_result: QueryResult) -> pd.DataFrame:
        """
        Create pandas DataFrame from QueryResult data

        Args:
            query_result: The QueryResult containing data to convert

        Returns:
            pandas DataFrame
        """
        if not query_result.data:
            return pd.DataFrame()

        # If columns are available, use them as DataFrame columns
        if query_result.columns:
            return pd.DataFrame(query_result.data, columns=query_result.columns)
        else:
            # If no column info, assume data is list of dicts or similar
            return pd.DataFrame(query_result.data)

    def get_available_results(self) -> List[Dict[str, Any]]:
        """
        Get information about available query results that can be exported

        Returns:
            List of dictionaries with query result information
        """
        results = []
        for entry in self.query_results.get_all_results():
            if entry.result.success and entry.result.data:
                results.append({
                    "index": entry.index,
                    "timestamp": entry.timestamp.isoformat(),
                    "query_text": entry.query_text[:100] + "..." if len(entry.query_text) > 100 else entry.query_text,
                    "row_count": entry.result.row_count,
                    "columns": entry.result.columns,
                    "exportable": True
                })
            else:
                results.append({
                    "index": entry.index,
                    "timestamp": entry.timestamp.isoformat(),
                    "query_text": entry.query_text[:100] + "..." if len(entry.query_text) > 100 else entry.query_text,
                    "row_count": 0,
                    "columns": None,
                    "exportable": False,
                    "reason": "Failed query or no data"
                })

        return results


def export_latest_result(
    session_id: str,
    format: ExportFormat = "csv",
    location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to export the latest query result

    Args:
        session_id: Current session ID
        format: Export format - "csv", "excel", or "parquet"
        location: Directory path to save file (defaults to "./tmp")

    Returns:
        Dictionary with export result information
    """
    exporter = DataExporter(session_id)
    return exporter.export_latest(format, location)


def export_result_by_index(
    session_id: str,
    index: int,
    format: ExportFormat = "csv",
    location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to export a specific query result by index

    Args:
        session_id: Current session ID
        index: Query result index (1-based)
        format: Export format - "csv", "excel", or "parquet"
        location: Directory path to save file (defaults to "./tmp")

    Returns:
        Dictionary with export result information
    """
    exporter = DataExporter(session_id)
    return exporter.export_by_index(index, format, location)
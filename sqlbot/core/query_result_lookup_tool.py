"""
Query Result Lookup Tool for LLM Integration

This module provides a LangChain tool that allows the LLM to look up
historical query results by index.
"""

import json
from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .query_result_list import get_query_result_list


class QueryResultLookupInput(BaseModel):
    """Input schema for query result lookup tool"""
    index: int = Field(description="The index number of the query result to look up (1-based)")
    session_id: Optional[str] = Field(default=None, description="Optional session ID (uses current session if not provided)")


class QueryResultLookupTool(BaseTool):
    """
    LangChain tool for looking up historical query results
    
    This tool allows the LLM to access full data from previous queries
    by referencing their index numbers.
    """
    
    name: str = "query_result_lookup"
    description: str = """Look up full data from a previous query result by its index number.

Use this tool when you need to access data from an earlier query in the conversation.
Query results are numbered sequentially starting from 1.

Input should be the index number of the query result you want to look up.
For example: {"index": 3} to get the data from query result #3.

The tool will return the full query data including:
- Original query text
- Column names
- All row data
- Execution metadata
"""
    
    args_schema: Type[BaseModel] = QueryResultLookupInput
    
    def __init__(self, session_id: str):
        """
        Initialize the lookup tool
        
        Args:
            session_id: Current session ID for context
        """
        super().__init__()
        # Store session_id as a private attribute to avoid Pydantic field conflicts
        self._session_id = session_id
        # Store last result for testing purposes
        self._last_result = None
    
    def _run(self, index: int, session_id: Optional[str] = None) -> str:
        """
        Look up a query result by index
        
        Args:
            index: Query result index (1-based)
            session_id: Optional session ID (uses current if not provided)
            
        Returns:
            JSON string with full query result data or error message
        """
        try:
            # Use provided session_id or fall back to current session
            lookup_session_id = session_id or self._session_id
            
            # Get the query result list for the session
            result_list = get_query_result_list(lookup_session_id)
            
            # Look up the specific result
            entry = result_list.get_result(index)
            
            if entry is None:
                available_indices = [e.index for e in result_list.get_all_results()]
                result_json = json.dumps({
                    "error": f"Query result #{index} not found",
                    "available_indices": available_indices,
                    "total_results": len(result_list)
                })
                self._last_result = result_json
                return result_json
            
            # Return full result data as JSON
            if entry.result.success:
                # Use serialized data to handle Decimal objects
                serialized_data = entry.result._serialize_data(entry.result.data)
                result_json = json.dumps({
                    "query_index": entry.index,
                    "timestamp": entry.timestamp.isoformat(),
                    "query_text": entry.query_text,
                    "success": True,
                    "columns": entry.result.columns,
                    "data": serialized_data,
                    "row_count": entry.result.row_count,
                    "execution_time": entry.result.execution_time
                }, indent=2)
                self._last_result = result_json
                return result_json
            else:
                result_json = json.dumps({
                    "query_index": entry.index,
                    "timestamp": entry.timestamp.isoformat(),
                    "query_text": entry.query_text,
                    "success": False,
                    "error": entry.result.error,
                    "execution_time": entry.result.execution_time
                }, indent=2)
                self._last_result = result_json
                return result_json
                
        except Exception as e:
            result_json = json.dumps({
                "error": f"Failed to lookup query result: {str(e)}"
            })
            self._last_result = result_json
            return result_json
    
    async def _arun(self, index: int, session_id: Optional[str] = None) -> str:
        """Async version of _run (not implemented, falls back to sync)"""
        return self._run(index, session_id)


def create_query_result_lookup_tool(session_id: str) -> QueryResultLookupTool:
    """
    Create a query result lookup tool for a specific session
    
    Args:
        session_id: Session ID for the tool
        
    Returns:
        Configured QueryResultLookupTool instance
    """
    return QueryResultLookupTool(session_id=session_id)

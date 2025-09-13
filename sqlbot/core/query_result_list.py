"""
Query Result List - Core class for managing and indexing query results

This module provides a clean, well-tested, reusable system for recording
query results with timestamps and indices, designed to work alongside
conversation management logic.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

from .types import QueryResult


@dataclass
class QueryResultEntry:
    """A single entry in the query result list"""
    index: int
    timestamp: datetime
    session_id: str
    query_text: str
    result: QueryResult
    entry_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'query_text': self.query_text,
            'result': self.result.to_dict(),
            'entry_id': self.entry_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResultEntry':
        """Create from dictionary (for deserialization)"""
        from .types import QueryResult, QueryType
        
        # Reconstruct QueryResult
        result_data = data['result']
        result = QueryResult(
            success=result_data['success'],
            query_type=QueryType(result_data['query_type']),
            execution_time=result_data['execution_time'],
            data=result_data.get('data'),
            error=result_data.get('error'),
            compiled_sql=result_data.get('compiled_sql'),
            row_count=result_data.get('row_count'),
            columns=result_data.get('columns')
        )
        
        return cls(
            index=data['index'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            session_id=data['session_id'],
            query_text=data['query_text'],
            result=result,
            entry_id=data['entry_id']
        )
    
    def get_placeholder_message(self) -> str:
        """Get placeholder message for conversation history"""
        status = "✅ Success" if self.result.success else "❌ Failed"
        row_info = f" • {self.result.row_count} rows" if self.result.row_count is not None else ""
        
        return (
            f"[Query Result #{self.index}] {status}{row_info} "
            f"(Use query_result_lookup tool with index={self.index} to access full data)"
        )
    
    def get_conversation_summary(self, include_full_data: bool = False) -> str:
        """Get summary for conversation history"""
        if include_full_data and self.result.success and self.result.data:
            # Return full data as JSON for AI consumption
            return json.dumps({
                'query_index': self.index,
                'query': self.query_text,
                'success': True,
                'columns': self.result.columns,
                'data': self.result.data,
                'row_count': self.result.row_count,
                'execution_time': self.result.execution_time
            }, indent=2)
        else:
            # Return placeholder
            return self.get_placeholder_message()


class QueryResultList:
    """
    Manages a list of query results with indexing and persistence
    
    Features:
    - Sequential indexing starting from 1
    - Timestamp metadata for each result
    - Session-based organization
    - Persistence to disk
    - Efficient lookup by index
    - Conversation history integration
    """
    
    def __init__(self, session_id: str, storage_path: Optional[Path] = None):
        """
        Initialize QueryResultList
        
        Args:
            session_id: Unique identifier for this session
            storage_path: Optional path for persistent storage
        """
        self.session_id = session_id
        self.storage_path = storage_path or Path(f".sqlbot/query_results/{session_id}.json")
        self._entries: List[QueryResultEntry] = []
        self._index_counter = 0
        
        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data if available
        self._load_from_storage()
    
    def add_result(self, query_text: str, result: QueryResult) -> QueryResultEntry:
        """
        Add a new query result to the list
        
        Args:
            query_text: The original query text
            result: The QueryResult object
            
        Returns:
            QueryResultEntry that was added
        """
        self._index_counter += 1
        
        entry = QueryResultEntry(
            index=self._index_counter,
            timestamp=datetime.now(),
            session_id=self.session_id,
            query_text=query_text,
            result=result,
            entry_id=str(uuid.uuid4())
        )
        
        self._entries.append(entry)
        self._save_to_storage()
        
        return entry
    
    def get_result(self, index: int) -> Optional[QueryResultEntry]:
        """
        Get a query result by index
        
        Args:
            index: The query result index (1-based)
            
        Returns:
            QueryResultEntry if found, None otherwise
        """
        for entry in self._entries:
            if entry.index == index:
                return entry
        return None
    
    def get_latest_result(self) -> Optional[QueryResultEntry]:
        """Get the most recent query result"""
        return self._entries[-1] if self._entries else None
    
    def get_all_results(self) -> List[QueryResultEntry]:
        """Get all query results in chronological order"""
        return self._entries.copy()
    
    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary information about all results"""
        total = len(self._entries)
        successful = sum(1 for entry in self._entries if entry.result.success)
        failed = total - successful
        
        return {
            'session_id': self.session_id,
            'total_queries': total,
            'successful_queries': successful,
            'failed_queries': failed,
            'latest_index': self._index_counter,
            'first_query_time': self._entries[0].timestamp.isoformat() if self._entries else None,
            'last_query_time': self._entries[-1].timestamp.isoformat() if self._entries else None
        }
    
    def get_conversation_history_data(self, include_latest_full: bool = True) -> List[str]:
        """
        Get data formatted for conversation history
        
        Args:
            include_latest_full: Whether to include full data for the latest result
            
        Returns:
            List of strings for conversation history
        """
        if not self._entries:
            return []
        
        history_data = []
        
        for i, entry in enumerate(self._entries):
            is_latest = (i == len(self._entries) - 1)
            include_full = include_latest_full and is_latest
            
            history_data.append(entry.get_conversation_summary(include_full_data=include_full))
        
        return history_data
    
    def clear_session(self):
        """DEPRECATED: This method is disabled to prevent accidental data loss.
        Query results should never be deleted."""
        raise NotImplementedError("Query result deletion is disabled to prevent data loss. Query results are preserved permanently.")
    
    def _save_to_storage(self):
        """Save current state to persistent storage"""
        try:
            data = {
                'session_id': self.session_id,
                'index_counter': self._index_counter,
                'entries': [entry.to_dict() for entry in self._entries]
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to save query results to storage: {e}")
    
    def _load_from_storage(self):
        """Load state from persistent storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                self._index_counter = data.get('index_counter', 0)
                self._entries = [
                    QueryResultEntry.from_dict(entry_data) 
                    for entry_data in data.get('entries', [])
                ]
                
        except Exception as e:
            # Log error but start fresh
            print(f"Warning: Failed to load query results from storage: {e}")
            self._entries = []
            self._index_counter = 0
    
    def __len__(self) -> int:
        """Return number of results"""
        return len(self._entries)
    
    def __iter__(self):
        """Iterate over results"""
        return iter(self._entries)
    
    def __getitem__(self, index: int) -> QueryResultEntry:
        """Get result by index (0-based for list access)"""
        return self._entries[index]


# Global registry for managing query result lists by session
_query_result_lists: Dict[str, QueryResultList] = {}


def get_query_result_list(session_id: str) -> QueryResultList:
    """
    Get or create a QueryResultList for a session
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        QueryResultList instance for the session
    """
    if session_id not in _query_result_lists:
        _query_result_lists[session_id] = QueryResultList(session_id)
    
    return _query_result_lists[session_id]


def clear_session_results(session_id: str):
    """DEPRECATED: This method is disabled to prevent accidental data loss.
    Query results should never be deleted."""
    raise NotImplementedError("Query result deletion is disabled to prevent data loss. Query results are preserved permanently.")

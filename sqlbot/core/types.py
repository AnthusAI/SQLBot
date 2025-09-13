"""
Core data types for SQLBot SDK
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


class QueryType(Enum):
    """Type of query being executed"""
    NATURAL_LANGUAGE = "natural_language"
    SQL = "sql"
    DBT = "dbt"
    SLASH_COMMAND = "slash_command"


class SafetyLevel(Enum):
    """Safety level of SQL operations"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


@dataclass
class SafetyAnalysis:
    """Result of SQL safety analysis"""
    level: SafetyLevel
    dangerous_operations: List[str]
    warnings: List[str]
    is_read_only: bool
    message: str


@dataclass
class CompilationResult:
    """Result of SQL compilation through dbt"""
    success: bool
    compiled_sql: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class QueryResult:
    """Result of query execution"""
    success: bool
    query_type: QueryType
    execution_time: float
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    compiled_sql: Optional[str] = None
    safety_analysis: Optional[SafetyAnalysis] = None
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    
    def _serialize_data(self, data: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Serialize data by converting non-JSON-serializable types"""
        if not data:
            return data
        
        from decimal import Decimal
        import datetime
        
        def serialize_value(value):
            """Convert non-JSON-serializable values to serializable ones"""
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, datetime.datetime):
                return value.isoformat()
            elif isinstance(value, datetime.date):
                return value.isoformat()
            else:
                return value
        
        return [
            {key: serialize_value(value) for key, value in row.items()}
            for row in data
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'success': self.success,
            'query_type': self.query_type.value,
            'execution_time': self.execution_time,
            'data': self._serialize_data(self.data),
            'error': self.error,
            'compiled_sql': self.compiled_sql,
            'row_count': self.row_count,
            'columns': self.columns
        }
        
        if self.safety_analysis:
            result['safety_analysis'] = {
                'level': self.safety_analysis.level.value,
                'dangerous_operations': self.safety_analysis.dangerous_operations,
                'warnings': self.safety_analysis.warnings,
                'is_read_only': self.safety_analysis.is_read_only,
                'message': self.safety_analysis.message
            }
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class TableInfo:
    """Information about a database table"""
    name: str
    schema: str
    description: Optional[str] = None
    columns: Optional[List[Dict[str, str]]] = None
    source_name: Optional[str] = None  # dbt source name


@dataclass
class ProfileInfo:
    """Information about dbt profile configuration"""
    name: str
    target: str
    schema_path: Optional[str] = None
    macro_paths: List[str] = None
    tables: List[TableInfo] = None
    
    def __post_init__(self):
        if self.macro_paths is None:
            self.macro_paths = []
        if self.tables is None:
            self.tables = []


@dataclass
class LLMConfig:
    """Configuration for LLM integration"""
    model: str = "gpt-5"
    max_tokens: int = 50000
    temperature: float = 0.1
    verbosity: str = "low"
    effort: str = "minimal"
    api_key: Optional[str] = None
    provider: str = "openai"

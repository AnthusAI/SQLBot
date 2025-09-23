"""
Main SQLBot Agent for Core SDK

This module provides the main SQLBotAgent class that coordinates all core functionality.
"""

import time
from typing import Optional, List
from .config import SQLBotConfig
from .types import QueryResult, QueryType, TableInfo, ProfileInfo
from .safety import SQLSafetyAnalyzer
from .schema import SchemaLoader
from .dbt import DbtExecutor, is_sql_query
from .llm import LLMAgent


class SQLBotAgent:
    """
    Main SQLBot agent that coordinates all core functionality

    This class provides a clean SDK interface for different presentation layers
    (REPL, Lambda, FastMCP, web APIs, etc.)
    """

    def __init__(self, config: SQLBotConfig, session_id: Optional[str] = None):
        """
        Initialize SQLBot agent

        Args:
            config: SQLBot configuration
            session_id: Optional session ID for query result tracking
        """
        self.config = config
        self.session_id = session_id or "default"

        # Initialize components
        self.safety_analyzer = SQLSafetyAnalyzer(dangerous_mode=config.dangerous)
        self.schema_loader = SchemaLoader(config.profile)
        self.dbt_executor = DbtExecutor(config)
        self.llm_agent = LLMAgent(config, self.session_id) if self._llm_available() else None

        # Clean up any leftover temporary files from previous runs
        self._cleanup_temp_files()

        # Cache for schema info
        self._schema_cache = None
        self._tables_cache = None
    
    def query(self, text: str) -> QueryResult:
        """
        Execute any type of query (natural language or SQL)
        
        Args:
            text: The query text
            
        Returns:
            QueryResult with execution results
        """
        text = text.strip()
        
        if not text:
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=0.0,
                error="Empty query"
            )
        
        # Determine query type and route accordingly
        if is_sql_query(text):
            return self.execute_sql(text)
        else:
            return self.execute_natural_language(text)
    
    def execute_sql(self, sql_query: str) -> QueryResult:
        """
        Execute SQL query with safety analysis
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            QueryResult with execution results
        """
        start_time = time.time()
        
        try:
            # Remove trailing semicolon for dbt compatibility
            sql_query = sql_query.rstrip(';')
            
            # Analyze safety
            safety_analysis = self.safety_analyzer.analyze(sql_query)
            
            # Check if execution should be blocked
            if not self.config.dangerous and not safety_analysis.is_read_only:
                return QueryResult(
                    success=False,
                    query_type=QueryType.SQL,
                    execution_time=time.time() - start_time,
                    error="Query blocked by read-only mode",
                    safety_analysis=safety_analysis
                )
            
            if safety_analysis.level.value == "dangerous" and not self._should_allow_dangerous():
                return QueryResult(
                    success=False,
                    query_type=QueryType.SQL,
                    execution_time=time.time() - start_time,
                    error=f"Dangerous query blocked: {safety_analysis.message}",
                    safety_analysis=safety_analysis
                )
            
            # Execute query
            if self.config.preview_mode:
                # Just compile, don't execute
                compilation_result = self.dbt_executor.compile_sql(sql_query)
                return QueryResult(
                    success=compilation_result.success,
                    query_type=QueryType.SQL,
                    execution_time=time.time() - start_time,
                    compiled_sql=compilation_result.compiled_sql,
                    error=compilation_result.error,
                    safety_analysis=safety_analysis
                )
            else:
                # Execute query
                result = self.dbt_executor.execute_sql(sql_query)
                result.safety_analysis = safety_analysis
                return result
        
        except Exception as e:
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=time.time() - start_time,
                error=f"Execution error: {str(e)}"
            )
    
    def execute_natural_language(self, query_text: str) -> QueryResult:
        """
        Execute natural language query via LLM
        
        Args:
            query_text: Natural language query
            
        Returns:
            QueryResult with execution results
        """
        if not self.llm_agent or not self.llm_agent.is_available():
            return QueryResult(
                success=False,
                query_type=QueryType.NATURAL_LANGUAGE,
                execution_time=0.0,
                error="LLM not available. Please use SQL queries ending with ';' or configure OpenAI API key."
            )
        
        return self.llm_agent.process_natural_language_query(query_text)
    
    def get_tables(self) -> List[TableInfo]:
        """
        Get list of available database tables
        
        Returns:
            List of TableInfo objects
        """
        if self._tables_cache is None:
            self._tables_cache = self.schema_loader.get_tables()
        return self._tables_cache
    
    def get_profile_info(self) -> ProfileInfo:
        """
        Get information about current profile configuration
        
        Returns:
            ProfileInfo object
        """
        return self.schema_loader.get_profile_info()
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection is working, False otherwise
        """
        return self.dbt_executor.test_connection()
    
    def is_llm_available(self) -> bool:
        """
        Check if LLM is available and configured
        
        Returns:
            True if LLM is available, False otherwise
        """
        return self.llm_agent is not None and self.llm_agent.is_available()
    
    def get_schema_info(self) -> dict:
        """
        Get raw schema information
        
        Returns:
            Dictionary with schema information
        """
        if self._schema_cache is None:
            self._schema_cache = self.schema_loader.load_schema_info()
        return self._schema_cache
    
    def refresh_cache(self):
        """Refresh cached schema and table information"""
        self._schema_cache = None
        self._tables_cache = None
    
    def _llm_available(self) -> bool:
        """Check if LLM dependencies are available"""
        try:
            import langchain_openai
            import langchain
            return bool(self.config.llm.api_key)
        except ImportError:
            return False
    
    def _should_allow_dangerous(self) -> bool:
        """
        Determine if dangerous operations should be allowed
        
        This can be overridden by specific interfaces for user confirmation
        """
        return False  # Default to safe behavior
    
    def _cleanup_temp_files(self):
        """Clean up temporary files from previous runs"""
        try:
            from .dbt import cleanup_temp_files
            cleaned_count = cleanup_temp_files()
            if cleaned_count > 0:
                # Only log if we actually cleaned something
                pass  # Could add logging here if needed
        except Exception:
            pass  # Ignore cleanup errors during initialization


class SQLBotAgentFactory:
    """Factory for creating SQLBot agents with different configurations"""
    
    @staticmethod
    def create_from_env(profile: Optional[str] = None, session_id: Optional[str] = None, **overrides) -> SQLBotAgent:
        """
        Create SQLBot agent from environment variables

        Args:
            profile: Optional profile name override
            session_id: Optional session ID for query result tracking
            **overrides: Configuration overrides

        Returns:
            Configured SQLBotAgent instance
        """
        config = SQLBotConfig.from_env(profile)

        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return SQLBotAgent(config, session_id)
    
    @staticmethod
    def create_read_only(profile: Optional[str] = None, session_id: Optional[str] = None) -> SQLBotAgent:
        """
        Create read-only SQLBot agent

        Args:
            profile: Optional profile name
            session_id: Optional session ID for query result tracking

        Returns:
            Read-only SQLBotAgent instance
        """
        return SQLBotAgentFactory.create_from_env(profile, session_id, dangerous=False)

    @staticmethod
    def create_preview_mode(profile: Optional[str] = None, session_id: Optional[str] = None) -> SQLBotAgent:
        """
        Create SQLBot agent in preview mode (compile only, don't execute)

        Args:
            profile: Optional profile name
            session_id: Optional session ID for query result tracking

        Returns:
            Preview-mode SQLBotAgent instance
        """
        return SQLBotAgentFactory.create_from_env(profile, session_id, preview_mode=True)

"""
LLM integration for SQLBot Core SDK

This module handles LLM operations independent of any UI.
"""

import os
from typing import Optional, Dict, Any
from .types import QueryResult, QueryType, LLMConfig
from .config import SQLBotConfig
from .schema import SchemaLoader


class LLMAgent:
    """Handles LLM operations for natural language to SQL conversion"""

    def __init__(self, config: SQLBotConfig, session_id: Optional[str] = None):
        self.config = config
        self.session_id = session_id or "default"
        self.schema_loader = SchemaLoader(config.profile)
        self._agent = None
        self._llm = None
    
    def is_available(self) -> bool:
        """Check if LLM is available and configured"""
        try:
            return bool(self.config.llm.api_key and self._get_llm())
        except Exception:
            return False
    
    def process_natural_language_query(self, query_text: str) -> QueryResult:
        """
        Convert natural language query to SQL and execute
        
        Args:
            query_text: Natural language query
            
        Returns:
            QueryResult with execution results
        """
        import time
        start_time = time.time()
        
        try:
            if not self.is_available():
                return QueryResult(
                    success=False,
                    query_type=QueryType.NATURAL_LANGUAGE,
                    execution_time=time.time() - start_time,
                    error="LLM not available or not configured"
                )
            
            # Get LLM agent
            agent = self._get_agent()
            
            # Process query through agent
            response = agent.invoke({"input": query_text})
            
            # Extract SQL from response
            # This is simplified - actual implementation would need proper parsing
            sql_query = self._extract_sql_from_response(response)
            
            if sql_query:
                # Execute the generated SQL
                from .dbt import DbtExecutor
                executor = DbtExecutor(self.config)
                result = executor.execute_sql(sql_query)
                result.query_type = QueryType.NATURAL_LANGUAGE
                result.compiled_sql = sql_query
                return result
            else:
                return QueryResult(
                    success=False,
                    query_type=QueryType.NATURAL_LANGUAGE,
                    execution_time=time.time() - start_time,
                    error="Could not generate SQL from natural language query"
                )
        
        except Exception as e:
            return QueryResult(
                success=False,
                query_type=QueryType.NATURAL_LANGUAGE,
                execution_time=time.time() - start_time,
                error=f"LLM processing error: {str(e)}"
            )
    
    def _get_llm(self):
        """Get or create LLM instance"""
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI
                
                self._llm = ChatOpenAI(
                    model=self.config.llm.model,
                    max_tokens=self.config.llm.max_tokens,
                    temperature=self.config.llm.temperature,
                    api_key=self.config.llm.api_key
                )
            except ImportError:
                raise ImportError("langchain-openai is required but not installed")
        
        return self._llm
    
    def _get_agent(self):
        """Get or create LLM agent"""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent
    
    def _create_agent(self):
        """Create LLM agent with tools and system prompt"""
        try:
            from langchain.agents import create_tool_calling_agent, AgentExecutor
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.tools import tool
            from pydantic import BaseModel
            from .export import export_latest_result

            # Create dbt query tool
            class DbtQueryInput(BaseModel):
                sql_query: str

            @tool("dbt_query", args_schema=DbtQueryInput)
            def dbt_query_tool(sql_query: str) -> str:
                """Execute SQL query using dbt"""
                from .dbt import DbtExecutor
                executor = DbtExecutor(self.config)
                result = executor.execute_sql(sql_query)

                if result.success:
                    return f"Query executed successfully. Rows: {result.row_count or 0}"
                else:
                    return f"Query failed: {result.error}"

            # Create export data tool
            class ExportDataInput(BaseModel):
                format: str = "csv"
                location: str = None

            @tool("export_data", args_schema=ExportDataInput)
            def export_data_tool(format: str = "csv", location: str = None) -> str:
                """
                Export the most recent query results to a file.

                Only exports the most recently executed successful query results.

                Args:
                    format: Export format - "csv", "excel", or "parquet" (default: "csv")
                    location: Directory path to save file (default: "./tmp")

                Returns:
                    Information about the exported file
                """
                # Use the session_id from the LLMAgent instance
                session_id = self.session_id

                # Validate format
                valid_formats = ["csv", "excel", "parquet"]
                if format not in valid_formats:
                    return f"Invalid format '{format}'. Valid formats are: {', '.join(valid_formats)}"

                result = export_latest_result(session_id, format, location)

                if result["success"]:
                    return (f"Successfully exported {result['row_count']} rows to {result['file_path']} "
                           f"in {result['format']} format. "
                           f"Columns: {', '.join(result['columns'])}")
                else:
                    return f"Export failed: {result['error']}"

            # Build system prompt with schema information
            system_prompt = self._build_system_prompt()

            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])

            # Create agent
            llm = self._get_llm()
            tools = [dbt_query_tool, export_data_tool]
            agent = create_tool_calling_agent(llm, tools, prompt)

            return AgentExecutor(agent=agent, tools=tools, verbose=False)
        
        except ImportError as e:
            raise ImportError(f"Required LangChain components not available: {e}")
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with schema information"""
        schema_info = self.schema_loader.load_schema_info()
        macro_info = self.schema_loader.load_macro_info()
        
        prompt = """You are SQLBot, a helpful database query assistant. You help users query their database using natural language and export query results.

IMPORTANT INSTRUCTIONS:
1. Convert natural language questions into SQL queries
2. ALWAYS use direct table names - DO NOT use dbt source() syntax for this database
3. Reference tables directly: FROM film, FROM customer, FROM actor (not from sources)
4. Always use the dbt_query tool to execute SQL
5. Provide clear explanations of what the query does
6. Handle errors gracefully and suggest alternatives
7. Use the export_data tool to export the most recent query results when requested

AVAILABLE TOOLS:
- dbt_query: Execute SQL queries against the database
- export_data: Export the most recent successful query results to CSV, Excel, or Parquet format

EXPORT CAPABILITIES:
- Only the most recent successful query results can be exported
- Supported formats: CSV (default), Excel, Parquet
- Default export location: ./tmp directory (created automatically)
- Users can specify custom export locations

CRITICAL: This database does not support dbt sources. Use direct table references only.

"""
        
        # Add schema information
        if schema_info.get('sources'):
            prompt += "AVAILABLE DATA SOURCES (USE DIRECT TABLE NAMES, NOT SOURCE SYNTAX):\n"
            for source in schema_info['sources']:
                source_name = source.get('name', 'unknown')
                schema_name = source.get('schema', 'dbo')
                prompt += f"\nSource: {source_name} (Schema: {schema_name})\n"
                
                for table in source.get('tables', []):
                    table_name = table.get('name', 'unknown')
                    description = table.get('description', 'No description')
                    prompt += f"  - {table_name}: {description}\n"
                    
                    # Add column information
                    for column in table.get('columns', []):
                        col_name = column.get('name', '')
                        col_desc = column.get('description', '')
                        if col_name:
                            prompt += f"    * {col_name}: {col_desc}\n"
        
        # Add macro information
        if macro_info:
            prompt += "\nAVAILABLE MACROS:\n"
            for macro in macro_info:
                prompt += f"  - {macro['name']}: Available in {macro['file']}\n"
        
        prompt += """
QUERY EXAMPLES (preferred syntax for this database):
- SELECT * FROM film LIMIT 10;
- SELECT COUNT(*) FROM customer;
- SELECT title FROM film WHERE title LIKE 'A%';
- SELECT c.first_name, c.last_name FROM customer c JOIN address a ON c.address_id = a.address_id;

EXPORT EXAMPLES:
- After running a query, users can say "export this to CSV" or "save this as Excel"
- Use export_data tool with format parameter: "csv", "excel", or "parquet"
- Optionally specify location: export_data(format="excel", location="/path/to/directory")

AVAILABLE TABLES: actor, film, customer, rental, payment, inventory, store, staff, category, language, address, city, country, film_actor, film_category

Remember to always use the dbt_query tool to execute your SQL queries and export_data tool to export results.
"""
        
        return prompt
    
    def _extract_sql_from_response(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract SQL query from LLM response"""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated parsing
        output = response.get('output', '')
        
        # Look for SQL patterns
        import re
        sql_patterns = [
            r'```sql\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'SELECT.*?;',
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return None


def test_llm_basic(config: SQLBotConfig, session_id: Optional[str] = None) -> bool:
    """
    Test basic LLM functionality

    Args:
        config: SQLBot configuration
        session_id: Optional session ID

    Returns:
        True if LLM is working, False otherwise
    """
    try:
        agent = LLMAgent(config, session_id)
        return agent.is_available()
    except Exception:
        return False

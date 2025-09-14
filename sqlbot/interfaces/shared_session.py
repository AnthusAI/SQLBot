"""
Shared SQLBot Session Manager

This module provides a shared session manager that both the Rich logging UI (--no-repl)
and the Textual UI can use. It handles:
- SQLBot agent initialization and configuration
- Conversation memory management
- Query execution with proper result formatting
- Event-driven architecture for different UI layers
"""

from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import time
from rich.tree import Tree
from rich.console import Console
from rich.text import Text

from sqlbot.core import SQLBotAgent, SQLBotConfig, QueryResult, QueryType
from sqlbot.conversation_memory import ConversationMemoryManager
from sqlbot.interfaces.repl.formatting import ResultFormatter


class SessionEventType(Enum):
    """Types of events that can occur during a session"""
    QUERY_STARTED = "query_started"
    QUERY_COMPLETED = "query_completed" 
    QUERY_FAILED = "query_failed"
    LLM_THINKING = "llm_thinking"
    SQL_EXECUTING = "sql_executing"
    RESULTS_READY = "results_ready"
    ERROR_OCCURRED = "error_occurred"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


@dataclass
class SessionEvent:
    """Event that occurs during a SQLBot session"""
    event_type: SessionEventType
    data: Dict[str, Any]
    timestamp: float
    
    @classmethod
    def create(cls, event_type: SessionEventType, **data) -> 'SessionEvent':
        """Create a new session event with current timestamp"""
        return cls(
            event_type=event_type,
            data=data,
            timestamp=time.time()
        )


class SQLBotSession:
    """
    Shared SQLBot session that can be used by different UI layers.
    
    This class provides:
    - Unified query execution with event callbacks
    - Conversation memory management
    - Result formatting for different output types
    - Event-driven architecture for UI updates
    """
    
    def __init__(self, config: SQLBotConfig, event_callback: Optional[Callable[[SessionEvent], None]] = None):
        """
        Initialize SQLBot session
        
        Args:
            config: SQLBot configuration
            event_callback: Optional callback for session events
        """
        self.config = config
        self.agent = SQLBotAgent(config)
        self.memory_manager = ConversationMemoryManager()
        self.formatter = ResultFormatter()
        self.event_callback = event_callback
        self.unified_display = None  # Will be set by UI layer
        
        # Session state
        self.is_active = False
        self.query_count = 0
        
        # Rich Tree for organized output
        self.session_tree = Tree(f"🤖 SQLBot Session - Profile: {config.profile}")
        self.current_query_tree = None
        
        # Emit session started event
        self._emit_event(SessionEventType.SESSION_STARTED, 
                        profile=config.profile,
                        dangerous_mode=config.dangerous,
                        preview_mode=config.preview_mode,
                        llm_available=self.agent.is_llm_available())
    
    def set_unified_display(self, unified_display):
        """Set the unified display for real-time tool call display"""
        self.unified_display = unified_display
    
    def execute_query(self, query_text: str) -> QueryResult:
        """
        Execute a query and manage conversation memory
        
        Args:
            query_text: The query to execute
            
        Returns:
            QueryResult with execution details
        """
        query_text = query_text.strip()
        
        if not query_text:
            result = QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=0.0,
                error="Empty query"
            )
            self._emit_event(SessionEventType.ERROR_OCCURRED, error="Empty query")
            return result
        
        # Increment query counter
        self.query_count += 1
        
        # Add query to tree
        self._add_query_to_tree(query_text)
        
        # Add to conversation memory (skip for natural language queries since handle_llm_query manages its own)
        if query_text.startswith('/') or query_text.strip().endswith(';'):
            self.memory_manager.add_user_message(query_text)
        
        # Emit query started event
        self._emit_event(SessionEventType.QUERY_STARTED, 
                        query=query_text, 
                        query_number=self.query_count)
        
        try:
            # Determine query type and emit appropriate thinking event
            if query_text.startswith('/'):
                # Handle slash commands
                self._add_processing_step("Executing command")
                result = self._handle_slash_command(query_text)
            elif query_text.strip().endswith(';'):
                self._add_processing_step("Executing SQL query")
                self._emit_event(SessionEventType.SQL_EXECUTING, query=query_text)
                # Use the working original SQL execution from sqlbot.repl
                try:
                    from sqlbot.repl import execute_dbt_sql_rich
                    import sqlbot.repl as repl_module
                    
                    # Set the profile to match our session
                    repl_module.DBT_PROFILE_NAME = self.config.profile
                    
                    sql_result = execute_dbt_sql_rich(query_text)
                    if sql_result and not sql_result.startswith("Query blocked by safeguard"):
                        result = QueryResult(
                            success=True,
                            query_type=QueryType.SQL,
                            execution_time=0.0,
                            data=[{"result": str(sql_result)}]  # Store result in data field
                        )
                    elif sql_result and sql_result.startswith("Query blocked by safeguard"):
                        result = QueryResult(
                            success=False,
                            query_type=QueryType.SQL,
                            execution_time=0.0,
                            error=sql_result
                        )
                    else:
                        result = QueryResult(
                            success=True,
                            query_type=QueryType.SQL,
                            execution_time=0.0,
                            data=[{"result": "Query executed successfully"}]
                        )
                except ImportError:
                    # Fallback to core SDK if original integration not available
                    result = self.agent.execute_sql(query_text)
            else:
                # Use the working original LLM integration from sqlbot.repl
                try:
                    from sqlbot.repl import handle_llm_query, LLM_AVAILABLE, DBT_PROFILE_NAME
                    import sqlbot.repl as repl_module
                    
                    # Set the profile to match our session
                    repl_module.DBT_PROFILE_NAME = self.config.profile
                    
                    if LLM_AVAILABLE:
                        self._add_processing_step("Processing with LLM", "yellow")
                        self._emit_event(SessionEventType.LLM_THINKING, query=query_text)
                        # Use the working LLM integration with conversation history management
                        try:
                            llm_result = self._call_handle_llm_query_safely(query_text)
                            if llm_result:
                                result = QueryResult(
                                    success=True,
                                    query_type=QueryType.NATURAL_LANGUAGE,
                                    execution_time=0.0,
                                    data=[{"result": str(llm_result)}]  # Store result in data field
                                )
                            else:
                                result = QueryResult(
                                    success=False,
                                    query_type=QueryType.NATURAL_LANGUAGE,
                                    execution_time=0.0,
                                    error="No response from LLM"
                                )
                        except Exception as llm_error:
                            # Capture detailed LLM execution errors
                            import traceback
                            error_details = f"LLM execution error: {type(llm_error).__name__}: {str(llm_error)}"
                            full_traceback = traceback.format_exc()
                            
                            result = QueryResult(
                                success=False,
                                query_type=QueryType.NATURAL_LANGUAGE,
                                execution_time=0.0,
                                error=error_details,
                                raw_output=full_traceback  # Store full traceback for debugging
                            )
                    else:
                        # Fallback to SQL if no LLM
                        self._emit_event(SessionEventType.SQL_EXECUTING, query=query_text)
                        result = self.agent.execute_sql(query_text)
                except ImportError:
                    # Fallback to core SDK if original integration not available
                    if self.agent.is_llm_available():
                        self._emit_event(SessionEventType.LLM_THINKING, query=query_text)
                        result = self.agent.execute_natural_language(query_text)
                    else:
                        # Fallback to SQL if no LLM
                        self._emit_event(SessionEventType.SQL_EXECUTING, query=query_text)
                        result = self.agent.execute_sql(query_text)
            
            # Add result to conversation memory
            if result.success:
                response_text = self._format_result_for_memory(result)
                
                # Add result to tree
                self._add_result_to_tree(result, response_text)
                
                # Skip memory management for natural language queries since handle_llm_query manages its own state
                if result.query_type != QueryType.NATURAL_LANGUAGE:
                    self.memory_manager.add_assistant_message(response_text)
                
                self._emit_event(SessionEventType.QUERY_COMPLETED,
                                query=query_text,
                                result=result,
                                formatted_result=response_text)
            else:
                # Add error to tree
                self._add_result_to_tree(result, "")
                
                # Skip memory management for natural language queries since handle_llm_query manages its own state
                if result.query_type != QueryType.NATURAL_LANGUAGE:
                    error_msg = f"Query failed: {result.error}"
                    self.memory_manager.add_assistant_message(error_msg)
                
                self._emit_event(SessionEventType.QUERY_FAILED,
                                query=query_text,
                                error=result.error,
                                result=result)
            
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.memory_manager.add_assistant_message(error_msg)
            
            result = QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=0.0,
                error=error_msg
            )
            
            self._emit_event(SessionEventType.ERROR_OCCURRED,
                            query=query_text,
                            error=error_msg,
                            exception=str(e))
            
            return result
    
    def _handle_slash_command(self, command: str) -> QueryResult:
        """Handle slash commands like /help, /clear, etc."""
        command = command.lower().strip()
        
        if command == '/clear':
            self.memory_manager.clear_history()
            return QueryResult(
                success=True,
                query_type=QueryType.SLASH_COMMAND,
                execution_time=0.0,
                data=[{"result": "Conversation history cleared"}]
            )
        elif command == '/memory':
            summary = self.memory_manager.get_conversation_summary()
            return QueryResult(
                success=True,
                query_type=QueryType.SLASH_COMMAND,
                execution_time=0.0,
                data=[{"result": f"Conversation: {summary['total_messages']} messages "
                               f"({summary['user_messages']} user, {summary['ai_messages']} AI, "
                               f"{summary['tool_messages']} tool results)"}]
            )
        elif command in ['/help', '/h']:
            help_text = """Available commands:
• Type natural language questions for AI-powered queries
• End queries with ';' for direct SQL/dbt execution  
• /clear - Clear conversation history
• /memory - Show conversation memory stats
• /help - Show this help message
• exit, quit, q - Exit the session"""
            return QueryResult(
                success=True,
                query_type=QueryType.SLASH_COMMAND,
                execution_time=0.0,
                data=[{"result": help_text}]
            )
        else:
            # Delegate to the main slash command handler from sqlbot.repl
            try:
                from sqlbot.repl import handle_slash_command
                import sqlbot.repl as repl_module
                
                # Set the profile to match our session
                repl_module.DBT_PROFILE_NAME = self.config.profile
                
                # Call the main handler
                result_text = handle_slash_command(command)
                
                if result_text == 'EXIT':
                    return QueryResult(
                        success=True,
                        query_type=QueryType.SLASH_COMMAND,
                        execution_time=0.0,
                        data=[{"result": "Exit requested"}]
                    )
                elif result_text:
                    return QueryResult(
                        success=True,
                        query_type=QueryType.SLASH_COMMAND,
                        execution_time=0.0,
                        data=[{"result": str(result_text)}]
                    )
                else:
                    return QueryResult(
                        success=True,
                        query_type=QueryType.SLASH_COMMAND,
                        execution_time=0.0,
                        data=[{"result": "Command executed"}]
                    )
            except Exception as e:
                return QueryResult(
                    success=False,
                    query_type=QueryType.SLASH_COMMAND,
                    execution_time=0.0,
                    error=f"Command failed: {e}"
                )
    
    def _format_result_for_memory(self, result: QueryResult) -> str:
        """Format query result for conversation memory"""
        if result.query_type == QueryType.SLASH_COMMAND:
            if result.data and len(result.data) > 0:
                return result.data[0].get("result", "Command executed")
            return "Command executed"
        elif result.data and len(result.data) > 0:
            if result.query_type == QueryType.NATURAL_LANGUAGE:
                return result.data[0].get("result", "Query executed successfully")
            else:
                return f"Query executed successfully. Returned {len(result.data)} rows."
        elif result.compiled_sql:
            return f"SQL compiled successfully: {result.compiled_sql[:100]}..."
        else:
            return "Query executed successfully"
    
    def get_formatted_result(self, result: QueryResult, format_type: str = "rich") -> str:
        """
        Get formatted result for display
        
        Args:
            result: QueryResult to format
            format_type: Format type ("rich", "plain", "json")
            
        Returns:
            Formatted result string
        """
        # For results from the working original system, extract the actual result text
        if result.data and len(result.data) > 0 and "result" in result.data[0]:
            raw_result = result.data[0]["result"]
            
            # For natural language queries, format the LLM response properly
            if result.query_type == QueryType.NATURAL_LANGUAGE:
                from sqlbot.interfaces.message_formatter import format_llm_response
                return format_llm_response(raw_result)
            else:
                return raw_result
        
        # For other cases, create a simple string representation
        if not result.success:
            return f"❌ Query failed: {result.error or 'Unknown error'}"
        
        # Format successful results
        if result.data:
            # Simple table format for data results
            lines = []
            if result.columns:
                lines.append(" | ".join(result.columns))
                lines.append("-" * len(lines[0]))
            
            for row in result.data[:10]:  # Limit to first 10 rows
                if isinstance(row, dict):
                    if result.columns:
                        lines.append(" | ".join(str(row.get(col, "")) for col in result.columns))
                    else:
                        lines.append(str(row))
                else:
                    lines.append(str(row))
            
            if len(result.data) > 10:
                lines.append(f"... and {len(result.data) - 10} more rows")
            
            result_text = "\n".join(lines)
            if result.execution_time:
                result_text += f"\n\nQuery executed in {result.execution_time:.2f}s"
            if result.row_count is not None:
                result_text += f" • {result.row_count} rows"
            
            return result_text
        else:
            # No data but successful
            success_msg = "Query executed successfully"
            if result.execution_time:
                success_msg += f" in {result.execution_time:.2f}s"
            return success_msg
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary for UI display"""
        return self.memory_manager.get_conversation_summary()
    
    def clear_conversation(self) -> None:
        """Clear conversation history"""
        self.memory_manager.clear_history()
        self._emit_event(SessionEventType.SESSION_STARTED, 
                        message="Conversation cleared")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        return self.agent.test_connection()
    
    def get_profile_info(self):
        """Get current profile information"""
        return self.agent.get_profile_info()
    
    def get_tables(self):
        """Get available database tables"""
        return self.agent.get_tables()
    
    def _add_query_to_tree(self, query_text: str) -> Tree:
        """Add a new query branch to the session tree"""
        query_branch = self.session_tree.add(f"[bold blue]Query {self.query_count}: {query_text}[/bold blue]")
        self.current_query_tree = query_branch
        return query_branch
    
    def _add_processing_step(self, step_text: str, style: str = "dim") -> Tree:
        """Add a processing step to the current query tree"""
        if self.current_query_tree is not None:
            return self.current_query_tree.add(f"[{style}]🔄 {step_text}[/{style}]")
        return None
    
    def _add_result_to_tree(self, result: QueryResult, formatted_result: str):
        """Add query result to the current query tree"""
        if self.current_query_tree is not None:
            if result.success:
                result_branch = self.current_query_tree.add("[green]✅ Success[/green]")
                
                # Add execution time if available
                if hasattr(result, 'execution_time') and result.execution_time:
                    result_branch.add(f"[dim]⏱️  Execution time: {result.execution_time:.2f}s[/dim]")
                
                # Add formatted result (truncated for tree view)
                lines = formatted_result.strip().split('\n')
                if len(lines) <= 3:
                    for line in lines:
                        if line.strip():
                            result_branch.add(f"[cyan]{line.strip()}[/cyan]")
                else:
                    # Show first few lines and indicate more
                    for line in lines[:2]:
                        if line.strip():
                            result_branch.add(f"[cyan]{line.strip()}[/cyan]")
                    result_branch.add(f"[dim]... ({len(lines)-2} more lines)[/dim]")
            else:
                error_branch = self.current_query_tree.add("[red]❌ Failed[/red]")
                error_branch.add(f"[red]{result.error}[/red]")
    
    def get_session_tree(self) -> Tree:
        """Get the complete session tree for display"""
        return self.session_tree
    
    def _call_handle_llm_query_safely(self, query_text: str) -> str:
        """
        Call handle_llm_query with proper conversation history management.
        """
        from sqlbot.repl import handle_llm_query
        import sqlbot.llm_integration as llm_module
        
        # Save the current conversation history
        original_history = getattr(llm_module, 'conversation_history', [])
        
        try:
            # Get the conversation context from our memory manager
            memory_messages = self.memory_manager.get_filtered_context()
            
            # Convert our memory to the format expected by handle_llm_query
            new_history = []
            for msg in memory_messages:
                if hasattr(msg, 'type'):
                    if msg.type == 'human':
                        new_history.append({"role": "user", "content": msg.content})
                    elif msg.type == 'ai':
                        new_history.append({"role": "assistant", "content": msg.content})
            
            # Set the conversation history to our managed state
            # This ensures handle_llm_query sees the full conversation context
            llm_module.conversation_history = new_history
            
            # Call handle_llm_query - it will add the current query and response to the history
            result = handle_llm_query(query_text, unified_display=self.unified_display)
            
            # Sync the updated conversation history back to our memory manager
            self._sync_conversation_history_to_memory(llm_module.conversation_history)
            
            return result
            
        finally:
            # Restore the original conversation history
            llm_module.conversation_history = original_history
    
    def _sync_conversation_history_to_memory(self, conversation_history):
        """
        Sync the conversation history from handle_llm_query back to our memory manager.
        Only add new messages that aren't already in our memory.
        """
        # Clear and rebuild memory from the updated conversation history
        self.memory_manager.clear_history()
        
        for msg in conversation_history:
            if msg["role"] == "user":
                self.memory_manager.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.memory_manager.add_assistant_message(msg["content"])
    
    def close(self):
        """Close the session"""
        self.is_active = False
        self._emit_event(SessionEventType.SESSION_ENDED,
                        query_count=self.query_count)
    
    def _emit_event(self, event_type: SessionEventType, **data):
        """Emit a session event to the callback"""
        if self.event_callback:
            event = SessionEvent.create(event_type, **data)
            try:
                self.event_callback(event)
            except Exception as e:
                # Don't let callback errors break the session
                print(f"Warning: Event callback error: {e}")


class SQLBotSessionFactory:
    """Factory for creating SQLBot sessions with different configurations"""
    
    @staticmethod
    def create_from_args(args, event_callback: Optional[Callable[[SessionEvent], None]] = None) -> SQLBotSession:
        """
        Create SQLBot session from parsed command line arguments
        
        Args:
            args: Parsed arguments (from argparse)
            event_callback: Optional event callback
            
        Returns:
            Configured SQLBotSession
        """
        # Create base config from environment
        config = SQLBotConfig.from_env(profile=getattr(args, 'profile', 'Sakila'))
        
        # Apply command line overrides
        if hasattr(args, 'dangerous') and args.dangerous:
            config.dangerous = True
        if hasattr(args, 'preview') and args.preview:
            config.preview_mode = True
        
        return SQLBotSession(config, event_callback)
    
    @staticmethod
    def create_for_profile(profile: str, event_callback: Optional[Callable[[SessionEvent], None]] = None) -> SQLBotSession:
        """
        Create SQLBot session for a specific profile
        
        Args:
            profile: Profile name
            event_callback: Optional event callback
            
        Returns:
            Configured SQLBotSession
        """
        config = SQLBotConfig.from_env(profile=profile)
        return SQLBotSession(config, event_callback)

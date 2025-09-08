"""
Textual TUI Application for QBot

This module provides a modern terminal user interface for QBot using the Textual framework.
It features a two-column layout with conversation history on the left and detail view on the right.
"""

from typing import Optional, List
import time
import sys
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.reactive import reactive
from textual.message import Message
from textual.command import Command, CommandPalette, Provider
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
import json

from qbot.core import QBotAgent, QBotConfig
from qbot.conversation_memory import ConversationMemoryManager
from qbot.interfaces.repl.formatting import ResultFormatter, MessageStyle
from qbot.interfaces.repl.commands import CommandHandler
from qbot.interfaces.textual_widgets import EnhancedDetailViewWidget
from qbot.interfaces.shared_session import QBotSession
from qbot.interfaces.message_formatter import MessageSymbols


class ConversationHistoryWidget(ScrollableContainer):
    """Widget for displaying conversation history using unified display system"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_log = RichLog(highlight=True, markup=True, wrap=True, auto_scroll=True)
        self.conversation_log.can_focus = False
        
        # Initialize unified message display system
        self.memory_manager = None
        self.unified_display = None
        self._welcome_message = None
    
    def compose(self) -> ComposeResult:
        """Compose the conversation history widget"""
        yield self.conversation_log
    
    def scroll_end(self):
        """Scroll to the end of the conversation"""
        self.conversation_log.scroll_end()
    
    def set_memory_manager(self, memory_manager):
        """Set the memory manager and initialize unified display"""
        self.memory_manager = memory_manager
        from qbot.interfaces.unified_message_display import UnifiedMessageDisplay, TextualMessageDisplay
        
        textual_display = TextualMessageDisplay(self)
        self.unified_display = UnifiedMessageDisplay(textual_display, memory_manager)
    
    def sync_conversation_display(self) -> None:
        """Synchronize the display with the current conversation state"""
        if self.unified_display:
            self.unified_display.sync_conversation_display()
    
    def add_user_message(self, message: str) -> None:
        """Add and display a user message"""
        if self.unified_display:
            self.unified_display.add_user_message(message)
    
    def add_ai_message(self, message: str) -> None:
        """Add and display an AI message"""
        if self.unified_display:
            self.unified_display.add_ai_message(message)
    
    def add_system_message(self, message: str, style: str = "cyan") -> None:
        """Add a system message to the conversation"""
        if self.unified_display:
            self.unified_display.add_system_message(message, style)
        else:
            # Fallback for when unified display isn't set up yet
            styled_message = f"[{style}]{MessageSymbols.SYSTEM} {message}[/{style}]"
            if self._welcome_message is None:
                self._welcome_message = styled_message
            self.conversation_log.write(styled_message)
            self.scroll_end()
    
    def add_error_message(self, message: str) -> None:
        """Add an error message to the conversation"""
        if self.unified_display:
            self.unified_display.add_error_message(message)
        else:
            # Fallback for when unified display isn't set up yet
            styled_message = f"[red]{MessageSymbols.ERROR} {message}[/red]"
            self.conversation_log.write(styled_message)
            self.scroll_end()
    
    def add_live_tool_call(self, tool_call_id: str, tool_name: str, description: str = "") -> None:
        """Add a live tool call indicator"""
        if self.unified_display:
            self.unified_display.display_impl.display_tool_call(tool_name, description)
    
    def update_live_tool_result(self, tool_call_id: str, tool_name: str, result_summary: str) -> None:
        """Update a tool call with its result"""
        if self.unified_display:
            self.unified_display.display_impl.display_tool_result(tool_name, result_summary)
    
    def add_query_result(self, result_text: str) -> None:
        """Add query result to the conversation display"""
        # Parse and format the result with proper styling
        lines = result_text.split('\n')
        for line in lines:
            if line.strip():
                self.conversation_log.write(line)
        self.scroll_end()
    
    def clear_history(self) -> None:
        """Clear the conversation history display"""
        self.conversation_log.clear()
        if self.unified_display:
            self.unified_display.clear_display()
    
    def _format_ai_response_with_markdown(self, content: str) -> str:
        """Format AI response content with markdown styling"""
        # Simple markdown formatting for AI responses
        # This is a placeholder - you might want to use a proper markdown parser
        import re
        
        # Bold text
        content = re.sub(r'\*\*(.*?)\*\*', r'[bold]\1[/bold]', content)
        
        # Italic text
        content = re.sub(r'\*(.*?)\*', r'[italic]\1[/italic]', content)
        
        # Code blocks (inline)
        content = re.sub(r'`(.*?)`', r'[dim cyan]\1[/dim cyan]', content)
        
        return content


# DetailViewWidget is now replaced by EnhancedDetailViewWidget in textual_widgets.py


class QBotCommandProvider(Provider):
    """Command provider for QBot-specific commands"""
    
    def __init__(self, screen, match_style=None):
        """Initialize the command provider"""
        super().__init__(screen, match_style)
    
    @property
    def app(self) -> 'QBotTextualApp':
        """Get the current app instance"""
        return self.screen.app
    
    async def search(self, query: str) -> list[Command]:
        """Search for commands matching the query"""
        commands = []
        
        if "query" in query.lower() or "result" in query.lower():
            commands.append(
                Command(
                    "show-query-results",
                    "Show Query Results",
                    "Switch right panel to show query results with data tables",
                    self.show_query_results
                )
            )
        
        if "history" in query.lower() or "debug" in query.lower() or "conversation" in query.lower():
            commands.append(
                Command(
                    "show-conversation-debug",
                    "Show Conversation Debug",
                    "Switch right panel to show raw LLM conversation history",
                    self.show_conversation_debug
                )
            )
        
        return commands
    
    async def show_query_results(self) -> None:
        """Switch to query results view"""
        if self.app and self.app.detail_widget:
            self.app.detail_widget.switch_to_query_results()
            self.app.notify("Switched to Query Results view", severity="information")
    
    async def show_conversation_debug(self) -> None:
        """Switch to conversation debug view"""
        if self.app and self.app.detail_widget:
            self.app.detail_widget.switch_to_conversation_debug()
            self.app.notify("Switched to Conversation Debug view", severity="information")


class QueryInput(Input):
    """Custom input widget for QBot queries"""
    
    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Type your question or SQL query (end with ; for SQL)...",
            **kwargs
        )


class QBotTextualApp(App):
    """Main Textual application for QBot"""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    #conversation-panel {
        width: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #detail-panel {
        width: 2fr;
        border: solid $secondary;
        margin: 1;
    }
    
    #query-input {
        height: 3;
        dock: bottom;
        margin: 1;
        border: solid $accent;
        background: $surface;
    }
    
    ConversationHistoryWidget {
        scrollbar-gutter: stable;
    }
    
    RichLog {
        background: $surface;
        color: $text;
    }
    """
    
    TITLE = "QBot - Database Query Assistant"
    SUB_TITLE = "Natural Language & SQL Interface"
    
    # Enable command palette
    COMMANDS = {QBotCommandProvider}
    
    def __init__(self, agent: QBotAgent, initial_query: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.memory_manager = ConversationMemoryManager()
        self.formatter = ResultFormatter()
        self.command_handler = CommandHandler(agent, self.formatter)
        self.initial_query = initial_query
    
        
        # Add global exception handler
        import sys
        def handle_exception(exc_type, exc_value, exc_traceback):
            print(f"❌ Unhandled exception: {exc_type.__name__}: {exc_value}")
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = handle_exception
        
        # Widgets
        self.conversation_widget: Optional[ConversationHistoryWidget] = None
        self.detail_widget: Optional[EnhancedDetailViewWidget] = None
        self.query_input: Optional[QueryInput] = None
        
        # Use the same session ID that LLM integration uses by default
        # This ensures query results are tracked in the same list
        self.session_id = "default_session"
        
        # Set the session ID for LLM agent creation
        from qbot.llm_integration import set_session_id
        set_session_id(self.session_id)
        
        # Initialize shared session for query execution
        self.session = QBotSession(agent.config)
        
        # Set up unified display connection once conversation widget is available
        self.call_after_refresh(self._setup_unified_display_connection)
    
    def _setup_unified_display_connection(self):
        """Connect the session's unified display to the conversation widget"""
        if self.conversation_widget and hasattr(self.conversation_widget, 'unified_display'):
            self.session.set_unified_display(self.conversation_widget.unified_display)
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout"""
        yield Header()
        
        # Main content area
        with Horizontal(id="main-container"):
            self.conversation_widget = ConversationHistoryWidget(
                id="conversation-panel"
            )
            self.detail_widget = EnhancedDetailViewWidget(self.session_id, id="detail-panel")
            yield self.conversation_widget
            yield self.detail_widget
        
        # Input area at bottom
        self.query_input = QueryInput(id="query-input")
        yield self.query_input
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        try:
            # Connect memory manager to widgets
            if self.detail_widget:
                self.detail_widget.set_memory_manager(self.memory_manager)
            
            if self.conversation_widget:
                self.conversation_widget.set_memory_manager(self.memory_manager)
            
            # Show welcome message
            self.show_welcome_message()
            
            # Execute initial query if provided
            if self.initial_query:
                self.call_later(self.execute_initial_query)
            
            # Focus the input and ensure it's visible
            if self.query_input:
                self.query_input.focus()
                self.query_input.scroll_visible()
                
        except Exception as e:
            print(f"❌ Mount error: {e}")
            import traceback
            traceback.print_exc()
    
    async def execute_initial_query(self) -> None:
        """Execute the initial query provided from command line"""
        if self.initial_query and self.conversation_widget:
            # Handle initial query using unified display logic
            await self.handle_query(self.initial_query)
    
    def show_welcome_message(self) -> None:
        """Display the welcome message using SAME system as --text mode"""
        if not self.conversation_widget:
            print("❌ ERROR: conversation_widget is None in show_welcome_message")
            return
        
        # Create banner using SAME system as --text mode
        from qbot.interfaces.banner import get_banner_content
        from rich.console import Console
        from rich.panel import Panel
        from io import StringIO
        import os
        
        # Get configuration info - SAME as --text mode
        profile = getattr(self.session.config, 'profile', 'qbot') if self.session and self.session.config else 'qbot'
        llm_model = os.getenv('QBOT_LLM_MODEL', 'gpt-5')
        llm_available = True
        
        banner_text = get_banner_content(
            profile=profile,
            llm_model=llm_model,
            llm_available=llm_available,
            interface_type="textual"
        )
        
        # Render banner using Rich console - SAME as --text mode
        output_buffer = StringIO()
        console = Console(file=output_buffer, width=80, legacy_windows=False)
        panel = Panel(banner_text, border_style="blue", width=80)
        console.print(panel)
        
        # Display the rendered banner in Textual widget
        rendered_banner = output_buffer.getvalue()
        self.conversation_widget.conversation_log.write(rendered_banner)
        self.conversation_widget.scroll_end()
        self.conversation_widget.refresh()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission with immediate feedback"""
        try:
            if not self.query_input or not self.conversation_widget:
                return
                
            user_input = event.value.strip()
            if not user_input:
                return
            
            # 1. Clear the input immediately (user feedback)
            self.query_input.value = ""
            
            # Note: Thinking indicator will be added by the specific query handler
            
            # Handle exit commands
            if user_input.lower() in ['exit', 'quit', 'q'] or user_input == '/exit':
                self.exit()
                return
            
            # Handle slash commands
            if user_input.startswith('/'):
                await self.handle_slash_command(user_input)
                return
            
            # Handle regular queries
            await self.handle_query(user_input)
                
        except Exception as e:
            # Log error and show to user instead of crashing
            if self.conversation_widget:
                self.conversation_widget.add_error_message(f"Input handling error: {e}")
            # Also print to console for debugging
            print(f"❌ Input submission error: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_slash_command(self, command: str) -> None:
        """Handle slash commands"""
        if not self.conversation_widget:
            return
            
        try:
            # Handle special Textual-specific commands
            if command == '/clear':
                self.conversation_widget.clear_history()
                self.memory_manager.clear_history()
                self.conversation_widget.add_system_message("Conversation history cleared", "green")
                return
            elif command == '/memory':
                # Show conversation memory debug info
                summary = self.memory_manager.get_conversation_summary()
                memory_info = (
                    f"Memory Status:\n"
                    f"• Total messages: {summary['total_messages']}\n"
                    f"• User messages: {summary['user_messages']}\n"
                    f"• AI messages: {summary['ai_messages']}\n"
                    f"• Tool messages: {summary['tool_messages']}"
                )
                self.conversation_widget.add_system_message(memory_info, "cyan")
                return
            
            # Use existing command handler for other commands
            # Note: The command handler expects a Rich console, so we'll capture its output
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                should_continue = self.command_handler.handle_command(command)
            
            # Get captured output
            output = output_buffer.getvalue().strip()
            error = error_buffer.getvalue().strip()
            
            if error:
                self.conversation_widget.add_error_message(f"Command error: {error}")
            elif output:
                self.conversation_widget.add_system_message(output, "cyan")
            else:
                self.conversation_widget.add_system_message(f"Command executed: {command}", "green")
            
            if not should_continue:
                self.exit()
                
        except Exception as e:
            self.conversation_widget.add_error_message(f"Command failed: {e}")
    
    async def handle_query(self, query: str) -> None:
        """Handle user queries with real-time feedback"""
        try:
            if not self.conversation_widget:
                return
                
            # Determine query type for different handling
            is_sql_query = query.strip().endswith(';')
            is_slash_command = query.startswith('/')
            
            if is_sql_query or is_slash_command:
                # Direct execution for SQL/commands - simple flow
                await self._handle_direct_query(query)
            else:
                # Natural language query - needs real-time LLM feedback
                await self._handle_llm_query_realtime(query)
                
            # Update conversation debug view if active
            if self.detail_widget:
                self.detail_widget.on_conversation_updated()
            
            # Refocus input for next query
            if self.query_input:
                self.query_input.focus()
            
        except Exception as e:
            if self.conversation_widget:
                self.conversation_widget.add_error_message(f"Query handling error: {e}")
            print(f"❌ Query handling error: {e}")
            import traceback
            traceback.print_exc()
    
    
    async def _handle_direct_query(self, query: str) -> None:
        """Handle SQL queries and slash commands using unified display logic"""
        try:
            # Add user message to display first
            if self.conversation_widget:
                self.conversation_widget.add_user_message(query)
                # Show thinking indicator for SQL queries too
                self.conversation_widget.unified_display.show_thinking_indicator("...")
            
            # Execute query using session
            worker = self.run_worker(
                lambda: self.session.execute_query(query),
                thread=True
            )
            result = await worker.wait()
            
            # Add result to display
            if result and self.conversation_widget:
                formatted_result = self.session.get_formatted_result(result, "rich")
                self.conversation_widget.add_ai_message(formatted_result)
            
            # Notify detail widget of new query result
            if self.detail_widget:
                self.detail_widget.on_new_query_result()
                
        except Exception as e:
            if self.conversation_widget:
                self.conversation_widget.add_error_message(f"Query failed: {e}")
            print(f"❌ Direct query error: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_llm_query_realtime(self, query: str) -> None:
        """Handle LLM queries using unified display system"""
        try:
            # Add user message to display first
            if self.conversation_widget:
                self.conversation_widget.add_user_message(query)
                # Show thinking indicator
                self.conversation_widget.unified_display.show_thinking_indicator("...")
            
            # Execute LLM query using session
            worker = self.run_worker(
                lambda: self.session.execute_query(query),
                thread=True
            )
            result = await worker.wait()
            
            # Add result to display
            if result and self.conversation_widget:
                formatted_result = self.session.get_formatted_result(result, "rich")
                self.conversation_widget.add_ai_message(formatted_result)
            
            # Update conversation debug view if active
            if self.detail_widget:
                self.detail_widget.on_conversation_updated()
                
        except Exception as e:
            if self.conversation_widget:
                self.conversation_widget.add_error_message(f"LLM query failed: {e}")
            print(f"❌ LLM query error: {e}")
            import traceback
            traceback.print_exc()
    
# REMOVED: _sync_memory_to_conversation_widget - no longer needed
# Textual interface now captures output directly from unified display system
    
    def _execute_query_sync(self, query: str) -> str:
        """Execute query synchronously - same as --no-repl mode"""
        try:
            # Use the exact same execution function as --no-repl mode
            from qbot.llm_integration import handle_llm_query
            import os
            
            # Same parameters as --no-repl mode (now always runs in main thread)
            timeout_seconds = int(os.getenv('QBOT_LLM_TIMEOUT', '120'))
            max_retries = int(os.getenv('QBOT_LLM_RETRIES', '3'))
            
            return handle_llm_query(query, max_retries=max_retries, timeout_seconds=timeout_seconds)
            
        except Exception as e:
            return f"❌ LLM Error: {e}"
    
    def _format_query_result(self, result) -> str:
        """Format query result for display"""
        if not result.data:
            return "No data returned"
        
        # Create a simple table format
        lines = []
        
        # Add header
        if result.columns:
            header = " | ".join(str(col) for col in result.columns)
            lines.append(header)
            lines.append("-" * len(header))
        
        # Add data rows (limit to first 10 for display)
        display_rows = result.data[:10] if len(result.data) > 10 else result.data
        
        for row in display_rows:
            if isinstance(row, dict):
                row_data = " | ".join(str(row.get(col, '')) for col in (result.columns or row.keys()))
            else:
                row_data = " | ".join(str(val) for val in row)
            lines.append(row_data)
        
        # Add summary
        if len(result.data) > 10:
            lines.append(f"... and {len(result.data) - 10} more rows")
        
        lines.append(f"\nQuery executed in {result.execution_time:.2f}s")
        if result.row_count is not None:
            lines[-1] += f" • {result.row_count} rows"
        
        return "\n".join(lines)
    
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()
    
    def on_key(self, event) -> None:
        """Handle key events"""
        # Allow Ctrl+C to exit
        if event.key == "ctrl+c":
            self.exit()
        # Allow Ctrl+Q to exit  
        elif event.key == "ctrl+q":
            self.exit()
        # Allow Escape to exit
        elif event.key == "escape":
            self.exit()


def create_textual_app_from_args(args) -> QBotTextualApp:
    """
    Create QBot Textual app from command line arguments
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured QBotTextualApp instance
    """
    # Create configuration
    config = QBotConfig.from_env(args.profile if hasattr(args, 'profile') else 'qbot')
    
    # Apply command line overrides
    if hasattr(args, 'read_only') and args.read_only:
        config.read_only = True
    if hasattr(args, 'preview') and args.preview:
        config.preview_mode = True
    
    # Create agent
    agent = QBotAgent(config)
    
    # Create Textual app
    return QBotTextualApp(agent)


async def run_textual_app(agent: QBotAgent) -> None:
    """
    Run the QBot Textual application
    
    Args:
        agent: Configured QBotAgent instance
    """
    app = QBotTextualApp(agent)
    await app.run_async()

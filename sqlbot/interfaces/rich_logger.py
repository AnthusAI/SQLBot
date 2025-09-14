"""
Rich-based Logging UI for SQLBot

This module provides a Rich-based logging interface for --no-repl mode.
It displays query execution progress and results using Rich's logging and console features.
"""

from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text
from rich.table import Table
from rich.tree import Tree
from rich.status import Status
import time

from .shared_session import SQLBotSession, SessionEvent, SessionEventType, SQLBotSessionFactory


class RichLoggingUI:
    """
    Rich-based logging UI for SQLBot queries
    
    This UI provides:
    - Progress indicators for query execution
    - Formatted result display
    - Error handling with clear messaging
    - Conversation context when requested
    """
    
    def __init__(self, show_context: bool = False):
        """
        Initialize Rich logging UI
        
        Args:
            show_context: Whether to show conversation context
        """
        self.console = Console()
        self.show_context = show_context
        self.current_status: Optional[Status] = None
        
    def execute_single_query(self, session: SQLBotSession, query: str) -> bool:
        """
        Execute a single query with Rich logging
        
        Args:
            session: SQLBot session to use
            query: Query to execute
            
        Returns:
            True if successful, False if failed
        """
        # Set up event handling
        session.event_callback = self._handle_session_event
        
        # Show query being executed
        self.console.print(f"\n[bold blue]❯[/bold blue] {query}")
        
        # Execute query
        result = session.execute_query(query)
        
        # Display results
        if result.success:
            formatted_result = session.get_formatted_result(result, "rich")
            if formatted_result.strip():
                self.console.print(formatted_result)
            else:
                self.console.print("[green]✓[/green] Query executed successfully")
            
            # Show conversation context if requested
            if self.show_context:
                self._display_conversation_context(session)
            
            return True
        else:
            self.console.print(f"[red]✗ Error:[/red] {result.error}")
            return False
    
    def _handle_session_event(self, event: SessionEvent):
        """Handle session events for progress display"""
        if event.event_type == SessionEventType.QUERY_STARTED:
            # Clear any existing status
            if self.current_status:
                self.current_status.stop()
            
        elif event.event_type == SessionEventType.LLM_THINKING:
            self.current_status = self.console.status("[yellow]🤖 AI is thinking...[/yellow]")
            self.current_status.start()
            
        elif event.event_type == SessionEventType.SQL_EXECUTING:
            if self.current_status:
                self.current_status.stop()
            self.current_status = self.console.status("[blue]⚡ Executing SQL...[/blue]")
            self.current_status.start()
            
        elif event.event_type in [SessionEventType.QUERY_COMPLETED, 
                                  SessionEventType.QUERY_FAILED, 
                                  SessionEventType.ERROR_OCCURRED]:
            if self.current_status:
                self.current_status.stop()
                self.current_status = None
    
    def _display_conversation_context(self, session: SQLBotSession):
        """Display conversation context using Rich tree"""
        self.console.print("\n" + "─" * 60)
        self.console.print("[bold magenta]📝 Conversation Context[/bold magenta]")
        
        # Get conversation summary
        summary = session.get_conversation_summary()
        
        # Create summary panel
        summary_text = (f"Total messages: {summary['total_messages']} "
                       f"(👤 {summary['user_messages']} user, "
                       f"🤖 {summary['ai_messages']} AI, "
                       f"🔧 {summary['tool_messages']} tool results)")
        
        self.console.print(Panel(summary_text, title="Memory Stats", border_style="dim"))
        
        # Show recent messages
        if summary['recent_messages']:
            tree = Tree("Recent Messages")
            for msg in summary['recent_messages']:
                msg_type = msg['type']
                content = msg['content']
                
                if msg_type == 'HumanMessage':
                    icon = "👤"
                    style = "blue"
                elif msg_type == 'AIMessage':
                    icon = "🤖"
                    style = "green"
                elif msg_type == 'ToolMessage':
                    icon = "🔧"
                    style = "yellow"
                else:
                    icon = "❓"
                    style = "dim"
                
                tree.add(f"[{style}]{icon} {content}[/{style}]")
            
            self.console.print(tree)
        
        self.console.print("─" * 60)
    
    def display_banner(self, session: SQLBotSession, is_no_repl: bool = True):
        """Display startup banner with session info"""
        profile_info = session.get_profile_info()
        
        banner_text = "🤖 SQLBot - Database Query Assistant"
        if is_no_repl:
            banner_text += " (Single Query Mode)"
        
        # Create info table
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Key", style="dim")
        info_table.add_column("Value")
        
        info_table.add_row("Profile:", f"[bold]{session.config.profile}[/bold]")
        info_table.add_row("Database:", profile_info.database if hasattr(profile_info, 'database') else "Connected")
        info_table.add_row("LLM:", "✅ Available" if session.agent.is_llm_available() else "❌ Not available")
        
        if not session.config.dangerous:
            info_table.add_row("Mode:", "[yellow]Read-Only[/yellow]")
        if session.config.preview_mode:
            info_table.add_row("Mode:", "[blue]Preview (compile only)[/blue]")
        
        # Display banner
        self.console.print(Panel(
            info_table,
            title=banner_text,
            border_style="bright_blue",
            padding=(1, 2)
        ))
    
    def display_error(self, error_msg: str):
        """Display error message"""
        self.console.print(f"[red]❌ Error:[/red] {error_msg}")
    
    def display_help(self):
        """Display help information"""
        help_text = """[bold]SQLBot Usage:[/bold]

[blue]Natural Language Queries:[/blue]
  qbot "How many customers are there?"
  qbot "Show me the top 10 products by sales"

[blue]SQL Queries:[/blue]
  qbot "SELECT COUNT(*) FROM customers;"
  qbot "SELECT * FROM products LIMIT 10;"

[blue]Options:[/blue]
  --profile PROFILE    Use specific dbt profile (default: Sakila)
  --dangerous         Disable safeguards (allow dangerous operations)
  --preview           Preview compiled SQL without executing
  --context           Show conversation context after query
  --no-repl           Exit after single query (default for command line)

[blue]Examples:[/blue]
  qbot --profile Sakila "SELECT 42 AS answer;"
  qbot --dangerous --context "DELETE FROM films WHERE year < 2000;"
  qbot --preview "UPDATE customers SET email = 'new@email.com';"
"""
        self.console.print(Panel(help_text, title="Help", border_style="green"))


def run_rich_logging_mode(args) -> int:
    """
    Run SQLBot in Rich logging mode (for --no-repl)
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    ui = RichLoggingUI(show_context=getattr(args, 'context', False))
    
    try:
        # Create session
        session = SQLBotSessionFactory.create_from_args(args)
        
        # Display banner
        ui.display_banner(session, is_no_repl=True)
        
        # Handle help
        if getattr(args, 'help', False):
            ui.display_help()
            return 0
        
        # Execute query if provided
        if hasattr(args, 'query') and args.query:
            query_text = ' '.join(args.query)
            success = ui.execute_single_query(session, query_text)
            session.close()
            return 0 if success else 1
        else:
            ui.display_error("No query provided")
            ui.display_help()
            return 1
            
    except KeyboardInterrupt:
        ui.console.print("\n[yellow]Interrupted by user[/yellow]")
        return 1
    except Exception as e:
        ui.display_error(f"Unexpected error: {e}")
        return 1

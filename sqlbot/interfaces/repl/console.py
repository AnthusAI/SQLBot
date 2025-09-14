"""
Main REPL console for SQLBot using Rich
"""

import os
import sys
import readline
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel

from sqlbot.core import SQLBotAgent, SQLBotConfig
from .formatting import ResultFormatter
from .commands import CommandHandler


class SQLBotREPL:
    """Rich console REPL interface using SQLBot core SDK"""
    
    def __init__(self, agent: SQLBotAgent, console: Optional[Console] = None):
        """
        Initialize SQLBot REPL
        
        Args:
            agent: SQLBotAgent instance
            console: Optional Rich console (creates new one if None)
        """
        self.agent = agent
        self.console = console or Console()
        self.formatter = ResultFormatter(self.console)
        self.command_handler = CommandHandler(agent, self.formatter)
        
        # Command history
        self.history_file = Path.home() / '.qbot_history'
        self.history_length = 100
        
        self._setup_history()
    
    def show_banner(self, mode: str = "interactive"):
        """
        Display SQLBot banner
        
        Args:
            mode: Banner mode ("interactive" or "cli")
        """
        if mode == "cli":
            # Abbreviated banner for CLI/no-repl mode
            self.console.print(Panel(
                "[bold magenta2]SQLBot CLI[/bold magenta2]\n"
                "[bold magenta2]SQLBot: Database Query Interface[/bold magenta2]",
                border_style="magenta2"
            ))
        else:
            # Full interactive banner
            self.console.print(Panel(
                "[bold magenta2]SQLBot: An agent with a dbt query tool to help you with your SQL.[/bold magenta2]\n\n"
                "[bold green]Ready for questions.[/bold green]\n\n"
                "[bold green]🤖 Default: Natural Language Queries[/bold green]\n"
                "• Just type your question in plain English\n"
                "• Example: [green]How many calls were made today?[/green]\n\n"
                "[bold blue]🔍 SQL/dbt Queries: End with semicolon[/bold blue]\n"
                "• SQL: [blue]SELECT COUNT(*) FROM sys.tables;[/blue]\n"
                "• dbt: [blue]SELECT * FROM {{ source('your_source', 'your_table') }} LIMIT 10;[/blue]\n\n"
                "[dim purple]Commands:[/dim purple]\n"
                "• [bold magenta2]/help[/bold magenta2] - Show all commands\n"
                "• [bold magenta2]/tables[/bold magenta2] - List database tables\n"
                "• [bold magenta2]/preview[/bold magenta2] - Preview SQL compilation before execution\n"
                "• [bold magenta2]/dangerous[/bold magenta2] - Toggle dangerous mode (disables safeguards)\n"
                "• [bold magenta2]exit[/bold magenta2] - Quit\n\n"
                "[dim purple]💡 Tips:[/dim purple]\n"
                "• Use ↑/↓ arrows to navigate command history\n"
                "• Press [bold red]Ctrl+C[/bold red] to interrupt running queries",
                border_style="magenta2"
            ))
    
    def start_interactive(self):
        """Start interactive REPL loop"""
        try:
            self.console.print("\n[dim]Type your question or SQL query. Use /help for commands.[/dim]")
            
            while True:
                try:
                    # Get user input with prompt
                    user_input = input("\ndbt> ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Add to history
                    readline.add_history(user_input)
                    
                    # Handle the input
                    should_continue = self.handle_input(user_input)
                    if not should_continue:
                        break
                        
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Query interrupted. Type 'exit' to quit.[/yellow]")
                    continue
                except EOFError:
                    self.console.print("\nGoodbye! 👋")
                    break
        
        finally:
            self._save_history()
    
    def handle_input(self, user_input: str) -> bool:
        """
        Handle user input (query or command)
        
        Args:
            user_input: The user's input
            
        Returns:
            True if should continue REPL, False if should exit
        """
        # Show user input with styling
        self.formatter.format_user_input(user_input)
        
        # Handle slash commands
        if user_input.startswith('/'):
            return self.command_handler.handle_command(user_input)
        
        # Handle queries
        try:
            result = self.agent.query(user_input)
            self.formatter.format_query_result(result, show_sql=self.agent.config.preview_mode)
            
        except Exception as e:
            self.formatter.format_error(f"Unexpected error: {e}")
        
        return True
    
    def execute_single_query(self, query: str):
        """
        Execute a single query and exit (for --no-repl mode)
        
        Args:
            query: The query to execute
        """
        self.console.print(f"Starting with query: {query}")
        
        try:
            result = self.agent.query(query)
            self.formatter.format_query_result(result, show_sql=self.agent.config.preview_mode)
            
        except Exception as e:
            self.formatter.format_error(f"Query execution failed: {e}")
        
        self.console.print("\nExiting (--no-repl mode)")
    
    def _setup_history(self):
        """Setup command history"""
        try:
            if self.history_file.exists():
                readline.read_history_file(str(self.history_file))
            
            # Set history length
            readline.set_history_length(self.history_length)
            
        except (FileNotFoundError, PermissionError):
            # History not available, continue without it
            pass
    
    def _save_history(self):
        """Save command history"""
        try:
            # Ensure parent directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write history
            readline.write_history_file(str(self.history_file))
            
        except (FileNotFoundError, PermissionError):
            # Can't save history, continue silently
            pass


def create_repl_from_args(args) -> SQLBotREPL:
    """
    Create SQLBot REPL from command line arguments
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured SQLBotREPL instance
    """
    # Create configuration
    config = SQLBotConfig.from_env(args.profile)
    
    # Apply command line overrides
    if hasattr(args, 'read_only') and args.read_only:
        config.dangerous = False
    if hasattr(args, 'preview') and args.preview:
        config.preview_mode = True
    
    # Create agent
    agent = SQLBotAgent(config)
    
    # Create REPL
    return SQLBotREPL(agent)

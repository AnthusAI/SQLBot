"""
Result formatting for QBot REPL interface
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

from qbot.core.types import QueryResult, SafetyLevel


class MessageStyle:
    """Rich styling for different message types"""
    USER_INPUT = "dodger_blue1"
    LLM_RESPONSE = "magenta2" 
    DATABASE_LABEL = "violet"
    ERROR = "red"
    WARNING = "yellow"
    SUCCESS = "green"
    INFO = "cyan"


class ResultFormatter:
    """Formats query results for Rich console display"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def format_query_result(self, result: QueryResult, show_sql: bool = False):
        """
        Format and display a query result
        
        Args:
            result: The QueryResult to format
            show_sql: Whether to show the compiled SQL
        """
        # Show safety analysis if present
        if result.safety_analysis:
            self._show_safety_analysis(result.safety_analysis)
        
        # Show compiled SQL if requested
        if show_sql and result.compiled_sql:
            self._show_compiled_sql(result.compiled_sql)
        
        # Show results or error
        if result.success:
            self._show_success_result(result)
        else:
            self._show_error_result(result)
    
    def format_table_list(self, tables: List[Dict[str, Any]]):
        """
        Format and display a list of tables
        
        Args:
            tables: List of table information dictionaries
        """
        if not tables:
            self.console.print("[yellow]No tables found in schema[/yellow]")
            return
        
        table = Table(title="Available Tables", show_header=True)
        table.add_column("Source", style="cyan")
        table.add_column("Table", style="magenta")
        table.add_column("Schema", style="blue")
        table.add_column("Description", style="white")
        
        for table_info in tables:
            table.add_row(
                table_info.get('source_name', 'unknown'),
                table_info.get('name', 'unknown'),
                table_info.get('schema', 'dbo'),
                table_info.get('description', 'No description')[:50] + "..." if len(table_info.get('description', '')) > 50 else table_info.get('description', '')
            )
        
        self.console.print(table)
    
    def format_help_text(self, help_content: str):
        """
        Format and display help text
        
        Args:
            help_content: The help content to display
        """
        self.console.print(Panel(
            help_content,
            title="QBot Help",
            border_style="blue"
        ))
    
    def format_user_input(self, text: str):
        """
        Format user input with styling
        
        Args:
            text: The user input text
        """
        self.console.print(f"[{MessageStyle.USER_INPUT}]> {text}[/{MessageStyle.USER_INPUT}]")
    
    def format_system_message(self, text: str, style: str = "white"):
        """
        Format system message
        
        Args:
            text: The system message
            style: Rich style to apply
        """
        self.console.print(f"[{style}]{text}[/{style}]")
    
    def format_error(self, error_text: str):
        """
        Format error message
        
        Args:
            error_text: The error message
        """
        self.console.print(f"[{MessageStyle.ERROR}]❌ {error_text}[/{MessageStyle.ERROR}]")
    
    def format_warning(self, warning_text: str):
        """
        Format warning message
        
        Args:
            warning_text: The warning message
        """
        self.console.print(f"[{MessageStyle.WARNING}]⚠️  {warning_text}[/{MessageStyle.WARNING}]")
    
    def format_success(self, success_text: str):
        """
        Format success message
        
        Args:
            success_text: The success message
        """
        self.console.print(f"[{MessageStyle.SUCCESS}]✅ {success_text}[/{MessageStyle.SUCCESS}]")
    
    def _show_safety_analysis(self, safety_analysis):
        """Show safety analysis information"""
        if safety_analysis.level == SafetyLevel.DANGEROUS:
            self.format_error(f"Dangerous operations detected: {', '.join(safety_analysis.dangerous_operations)}")
        elif safety_analysis.level == SafetyLevel.WARNING:
            self.format_warning(f"Warning operations detected: {', '.join(safety_analysis.warnings)}")
    
    def _show_compiled_sql(self, compiled_sql: str):
        """Show compiled SQL with syntax highlighting"""
        self.console.print(Panel(
            Syntax(compiled_sql, "sql", theme="monokai", line_numbers=True),
            title=f"[{MessageStyle.DATABASE_LABEL}]Compiled SQL[/{MessageStyle.DATABASE_LABEL}]",
            border_style="violet"
        ))
    
    def _show_success_result(self, result: QueryResult):
        """Show successful query result"""
        if result.data:
            self._show_data_table(result.data, result.columns)
        
        # Show execution info
        info_text = f"Query executed in {result.execution_time:.2f}s"
        if result.row_count is not None:
            info_text += f" • {result.row_count} rows"
        
        self.console.print(f"[{MessageStyle.INFO}]{info_text}[/{MessageStyle.INFO}]")
    
    def _show_error_result(self, result: QueryResult):
        """Show error result"""
        self.format_error(f"Query failed: {result.error}")
        
        if result.execution_time > 0:
            self.console.print(f"[dim]Failed after {result.execution_time:.2f}s[/dim]")
    
    def _show_data_table(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        """Show data in a Rich table"""
        if not data:
            self.console.print("[yellow]No data returned[/yellow]")
            return
        
        # Get columns from data if not provided
        if not columns and data:
            columns = list(data[0].keys())
        
        if not columns:
            self.console.print("[yellow]No columns found[/yellow]")
            return
        
        # Create Rich table
        table = Table(show_header=True, header_style="bold magenta")
        
        # Add columns
        for col in columns:
            table.add_column(str(col))
        
        # Add rows
        for row in data:
            table.add_row(*[str(row.get(col, '')) for col in columns])
        
        self.console.print(table)

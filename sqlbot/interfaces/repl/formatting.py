"""
Result formatting for SQLBot REPL interface
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

from sqlbot.core.types import QueryResult, SafetyLevel
from sqlbot.interfaces.theme_system import get_theme_manager


class MessageStyle:
    """Rich styling for different message types - now theme-aware"""
    
    @property
    def USER_INPUT(self) -> str:
        return get_theme_manager().get_color("user_message") or "blue"
    
    @property
    def LLM_RESPONSE(self) -> str:
        return get_theme_manager().get_color("ai_response") or "magenta"
    
    @property
    def DATABASE_LABEL(self) -> str:
        return get_theme_manager().get_color("database_label") or "violet"
    
    @property
    def ERROR(self) -> str:
        return get_theme_manager().get_color("error_message") or "red"
    
    @property
    def WARNING(self) -> str:
        return get_theme_manager().get_color("warning_message") or "yellow"
    
    @property
    def SUCCESS(self) -> str:
        return get_theme_manager().get_color("success_message") or "green"
    
    @property
    def INFO(self) -> str:
        return get_theme_manager().get_color("info_message") or "blue"


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
        theme = get_theme_manager()
        table.add_column("Source", style=theme.get_color("info_message"))
        table.add_column("Table", style=theme.get_color("ai_response"))
        table.add_column("Schema", style=theme.get_color("primary"))
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
            title="SQLBot Help",
            border_style="blue"
        ))
    
    def format_user_input(self, text: str):
        """
        Format user input with styling
        
        Args:
            text: The user input text
        """
        theme = get_theme_manager()
        styled = theme.format_user_message(text, ">")
        self.console.print(styled)
    
    def format_system_message(self, text: str, style: str = "system_message"):
        """
        Format system message
        
        Args:
            text: The system message
            style: Theme style name to apply
        """
        theme = get_theme_manager()
        styled = theme.format_system_message(text, "◦")
        self.console.print(styled)
    
    def format_error(self, error_text: str):
        """
        Format error message
        
        Args:
            error_text: The error message
        """
        theme = get_theme_manager()
        styled = theme.format_error(f"❌ {error_text}", "▪")
        self.console.print(styled)
    
    def format_warning(self, warning_text: str):
        """
        Format warning message
        
        Args:
            warning_text: The warning message
        """
        theme = get_theme_manager()
        color = theme.get_color("warning_message")
        self.console.print(f"[{color}]⚠️  {warning_text}[/{color}]")
    
    def format_success(self, success_text: str):
        """
        Format success message
        
        Args:
            success_text: The success message
        """
        theme = get_theme_manager()
        color = theme.get_color("success_message")
        self.console.print(f"[{color}]✅ {success_text}[/{color}]")
    
    def _show_safety_analysis(self, safety_analysis):
        """Show safety analysis information"""
        if safety_analysis.level == SafetyLevel.DANGEROUS:
            self.format_error(f"Dangerous operations detected: {', '.join(safety_analysis.dangerous_operations)}")
        elif safety_analysis.level == SafetyLevel.WARNING:
            self.format_warning(f"Warning operations detected: {', '.join(safety_analysis.warnings)}")
    
    def _show_compiled_sql(self, compiled_sql: str):
        """Show compiled SQL with syntax highlighting"""
        theme = get_theme_manager()
        db_color = theme.get_color("database_label") or "violet"
        self.console.print(Panel(
            Syntax(compiled_sql, "sql", theme="monokai", line_numbers=True),
            title=f"[{db_color}]Compiled SQL[/{db_color}]",
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
        
        theme = get_theme_manager()
        info_color = theme.get_color("info_message") or "blue"
        self.console.print(f"[{info_color}]{info_text}[/{info_color}]")
    
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
        theme = get_theme_manager()
        header_color = theme.get_color("ai_response")
        table = Table(show_header=True, header_style=f"bold {header_color}")
        
        # Add columns
        for col in columns:
            table.add_column(str(col))
        
        # Add rows
        for row in data:
            table.add_row(*[str(row.get(col, '')) for col in columns])
        
        self.console.print(table)

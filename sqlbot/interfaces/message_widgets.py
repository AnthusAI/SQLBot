"""
Message Widgets for SQLBot Textual Interface

Individual Textual widgets for different message types in the conversation.
Each widget handles its own styling, wrapping, and behavior.
"""

from textual.widgets import Static, LoadingIndicator, Collapsible, Markdown, DataTable
from textual.containers import Horizontal
from textual.app import ComposeResult
from rich.text import Text
from sqlbot.interfaces.message_formatter import MessageSymbols
from sqlbot.interfaces.theme_system import get_theme_manager


class UserMessageWidget(Static):
    """Widget for displaying user messages"""
    
    def __init__(self, message: str, **kwargs):
        # Create Rich Text with styling
        theme = get_theme_manager()
        user_color = theme.get_color('user_message') or "blue"
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.USER_MESSAGE} ", style=f"bold {user_color}")
        text.append(message, style=f"bold {user_color}")
        
        super().__init__(text, **kwargs)
        self.add_class("user-message")


class AIMessageWidget(Static):
    """Widget for displaying AI response messages with markdown support"""
    
    def __init__(self, message: str, **kwargs):
        # Store the message for markdown rendering
        self.message = message
        super().__init__(**kwargs)
        self.add_class("ai-message")
    
    def compose(self) -> ComposeResult:
        """Compose the widget with AI symbol and markdown content"""
        theme = get_theme_manager()
        ai_color = theme.get_color('ai_response') or "magenta"
        
        # Create AI symbol as static text
        symbol_text = Text()
        symbol_text.append(f"{MessageSymbols.AI_RESPONSE} ", style=ai_color)
        yield Static(symbol_text)
        
        # Create markdown widget for the message content with proper styling
        markdown_widget = Markdown(self.message)
        markdown_widget.add_class("ai-message-content")
        yield markdown_widget


class SystemMessageWidget(Static):
    """Widget for displaying system messages"""
    
    def __init__(self, message: str, **kwargs):
        theme = get_theme_manager()
        system_color = theme.get_color('system_message')
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.SYSTEM} ", style=system_color if system_color else None)
        text.append(message, style=system_color if system_color else None)
        
        super().__init__(text, **kwargs)
        self.add_class("system-message")


class ErrorMessageWidget(Static):
    """Widget for displaying error messages"""
    
    def __init__(self, message: str, **kwargs):
        theme = get_theme_manager()
        error_color = theme.get_color('error')
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.ERROR} ", style=f"bold {error_color}" if error_color else "bold red")
        text.append(message, style=f"bold {error_color}" if error_color else "bold red")
        
        super().__init__(text, **kwargs)
        self.add_class("error-message")


class ToolCallWidget(Static):
    """Widget for displaying tool calls"""
    
    def __init__(self, tool_name: str, description: str = "", **kwargs):
        display_text = f"{tool_name}: {description}" if description else f"Calling {tool_name}..."
        
        theme = get_theme_manager()
        tool_call_color = theme.get_color('tool_call')
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.TOOL_CALL} ", style=tool_call_color if tool_call_color else None)
        text.append(display_text, style=tool_call_color if tool_call_color else None)
        
        super().__init__(text, **kwargs)
        self.add_class("tool-call")


class ToolResultWidget(Static):
    """Widget for displaying tool results"""
    
    def __init__(self, tool_name: str, result_summary: str, **kwargs):
        theme = get_theme_manager()
        tool_result_color = theme.get_color('tool_result')
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.TOOL_RESULT} ", style=tool_result_color if tool_result_color else None)
        text.append(f"{tool_name} → {result_summary}", style=tool_result_color if tool_result_color else None)
        
        super().__init__(text, **kwargs)
        self.add_class("tool-result")


class CollapsibleToolCallWidget(Static):
    """Collapsible widget for displaying tool calls"""
    
    def __init__(self, tool_name: str, description: str = "", **kwargs):
        self.tool_name = tool_name
        self.description = description
        super().__init__(**kwargs)
        self.add_class("collapsible-tool-call")
        self.styles.padding = 0
    
    def compose(self) -> ComposeResult:
        """Compose the collapsible widget with title and content"""
        # Create title text (without triangle symbol since Collapsible provides its own)
        title_text = Text()
        title_text.append(self.tool_name)
        
        # Use Collapsible widget with proper API - start expanded by default
        collapsible = Collapsible(collapsed=False, title=title_text)
        with collapsible:
            # Create detailed content for inside the collapsible
            if self.description:
                content_text = Text()
                content_text.append("Parameters: ", style="bold")
                content_text.append(self.description)  # Use default color
                yield Static(content_text)
            else:
                yield Static(Text("No parameters provided", style="dim"))


class CollapsibleToolResultWidget(Static):
    """Collapsible widget for displaying tool results"""
    
    def __init__(self, tool_name: str, result_content: str, result_data=None, **kwargs):
        self.tool_name = tool_name
        self.result_content = result_content
        self.result_data = result_data  # Store the actual query result data
        super().__init__(**kwargs)
        self.add_class("collapsible-tool-result")
        self.styles.padding = 0
    
    def compose(self) -> ComposeResult:
        """Compose the collapsible widget with title and content"""
        # Create title text with brief preview (without triangle symbol since Collapsible provides its own)
        title_text = Text()
        
        # Add brief preview in title if result is short (use default color)
        if len(self.result_content) <= 50:
            title_text.append(self.result_content)
        else:
            title_text.append(f"{self.result_content[:47]}...")
        
        # Use Collapsible widget with proper API - start expanded by default
        collapsible = Collapsible(collapsed=False, title=title_text)
        with collapsible:
            # Try to parse and display as DataTable, fallback to text
            if self._is_query_result():
                yield self._create_data_table()
            else:
                # For non-query results, just show the content as text
                yield Static(self.result_content)
    
    def _is_query_result(self) -> bool:
        """Check if the result content looks like a database query result"""
        # Look for patterns that indicate tabular data
        content = self.result_content.lower()
        return (
            'rows returned' in content or 
            'columns:' in content or
            '|' in content or  # Table-like formatting
            'success:' in content and ('row' in content or 'column' in content)
        )
    
    def _create_data_table(self) -> DataTable:
        """Create a DataTable from the query result content"""
        table = DataTable(zebra_stripes=True, show_header=True)
        
        try:
            # If we have actual result data, use it directly
            if self.result_data and hasattr(self.result_data, 'data') and hasattr(self.result_data, 'columns'):
                # Use the actual query result data
                if self.result_data.columns:
                    table.add_columns(*self.result_data.columns)
                    
                    # Add data rows
                    if self.result_data.data:
                        for row in self.result_data.data:
                            # Handle both dictionary and list formats
                            if isinstance(row, dict):
                                # Extract values in the same order as columns
                                row_values = [row.get(col, "") for col in self.result_data.columns]
                            else:
                                # Assume it's already a list/tuple
                                row_values = row
                            
                            # Ensure all values are strings for display
                            row_strings = [str(val) if val is not None else "" for val in row_values]
                            table.add_row(*row_strings)
                    else:
                        # No data rows, just show empty table with headers
                        table.add_row(*[""] * len(self.result_data.columns))
                else:
                    # No columns, create a simple result display
                    table.add_column("Result")
                    table.add_row("No columns returned")
            
            else:
                # Fallback to parsing the result content text
                content = self.result_content.strip()
                
                # Look for patterns like "Success: 1 rows returned (columns: film_count)"
                import re
                
                # Extract column information from the success message
                columns_match = re.search(r'columns:\s*([^)]+)', content)
                if columns_match:
                    columns_text = columns_match.group(1)
                    # Split multiple columns by comma
                    column_names = [col.strip() for col in columns_text.split(',')]
                    
                    # Add columns to table
                    table.add_columns(*column_names)
                    
                    # Since we don't have actual data, show placeholder
                    table.add_row(*["No data available"] * len(column_names))
                
                else:
                    # Simple fallback: create a single result table
                    table.add_column("Query Result")
                    table.add_row(content)
                        
        except Exception:
            # If parsing fails, create a simple table with the raw content
            table.add_column("Query Result")
            table.add_row(self.result_content)
        
        return table


class SuccessMessageWidget(Static):
    """Widget for displaying success messages (like safeguard passes)"""
    
    def __init__(self, message: str, **kwargs):
        theme = get_theme_manager()
        success_color = theme.get_color('success') or "green"
        
        # Create styled text
        text = Text()
        text.append(f"{MessageSymbols.SUCCESS} ", style=f"bold {success_color}")
        text.append(message, style=success_color)
        
        super().__init__(text, **kwargs)
        self.add_class("success-message")


class ThinkingIndicatorWidget(Static):
    """Widget for displaying animated thinking indicator with LoadingIndicator"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("thinking-indicator")
    
    def compose(self) -> ComposeResult:
        """Compose the widget with LoadingIndicator"""
        loading_indicator = LoadingIndicator()
        loading_indicator.add_class("loading-indicator")
        yield loading_indicator

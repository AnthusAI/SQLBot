"""
Message Widgets for QBot Textual Interface

Individual Textual widgets for different message types in the conversation.
Each widget handles its own styling, wrapping, and behavior.
"""

from textual.widgets import Static, LoadingIndicator
from textual.containers import Horizontal
from textual.app import ComposeResult
from rich.text import Text
from rich.markdown import Markdown
from qbot.interfaces.message_formatter import MessageSymbols
from qbot.interfaces.theme_system import get_theme_manager


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
    """Widget for displaying AI response messages"""
    
    def __init__(self, message: str, **kwargs):
        # Create Rich Text with styling and markdown support
        theme = get_theme_manager()
        ai_color = theme.get_color('ai_response') or "magenta"
        
        # Process markdown in the message
        try:
            # Create markdown renderable
            markdown_content = Markdown(message)
            # Wrap in a Text object with AI symbol
            text = Text()
            text.append(f"{MessageSymbols.AI_RESPONSE} ", style=ai_color)
            # For now, just append the raw message - we'll enhance markdown later
            text.append(message, style=ai_color)
        except Exception:
            # Fallback to plain text
            text = Text()
            text.append(f"{MessageSymbols.AI_RESPONSE} ", style=ai_color)
            text.append(message, style=ai_color)
        
        super().__init__(text, **kwargs)
        self.add_class("ai-message")


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

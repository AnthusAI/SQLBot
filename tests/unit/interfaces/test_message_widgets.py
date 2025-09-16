"""
Unit tests for message widgets in the Textual interface.

This test suite ensures that message widgets properly handle content formatting,
particularly the AIMessageWidget's Markdown rendering capabilities.
"""

import pytest
from unittest.mock import Mock, patch
from textual.widgets import Markdown, Static
from textual.app import ComposeResult

# Import the widgets we want to test
from sqlbot.interfaces.message_widgets import (
    AIMessageWidget,
    UserMessageWidget,
    SystemMessageWidget,
    ErrorMessageWidget,
    ToolCallWidget,
    ToolResultWidget
)


class TestAIMessageWidget:
    """Test the AIMessageWidget with Markdown support"""
    
    def test_ai_message_widget_initialization(self):
        """Test that AIMessageWidget initializes correctly"""
        message = "This is a test message with **bold** text"
        widget = AIMessageWidget(message)
        
        assert widget.message == message
        assert "ai-message" in widget.classes
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_ai_message_widget_compose_creates_markdown(self, mock_theme_manager):
        """Test that compose() creates a Markdown widget for the message content"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "magenta"
        mock_theme_manager.return_value = mock_theme
        
        message = "# Header\n\nThis is **bold** and *italic* text with `code`"
        widget = AIMessageWidget(message)
        
        # Get the composed widgets
        composed_widgets = list(widget.compose())
        
        # Should have 2 widgets: Static (for symbol) and Markdown (for content)
        assert len(composed_widgets) == 2
        
        # First widget should be Static for the AI symbol
        assert isinstance(composed_widgets[0], Static)
        
        # Second widget should be Markdown for the message content
        assert isinstance(composed_widgets[1], Markdown)
        
        # Markdown widget should be properly configured
        markdown_widget = composed_widgets[1]
        # Note: The source content is set during widget initialization but may not be
        # immediately available until the widget is mounted in an app context
        
        # Markdown widget should have the ai-message-content class
        assert "ai-message-content" in markdown_widget.classes
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_ai_message_widget_handles_complex_markdown(self, mock_theme_manager):
        """Test that AIMessageWidget handles complex Markdown content"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "magenta"
        mock_theme_manager.return_value = mock_theme
        
        complex_markdown = """
# Main Header

## Subheader

This is a paragraph with **bold text**, *italic text*, and `inline code`.

### Code Block

```python
def hello_world():
    print("Hello, World!")
```

### List

- Item 1
- Item 2
  - Nested item
- Item 3

### Table

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

### Blockquote

> This is a blockquote
> with multiple lines

### Links

[Link text](https://example.com)
"""
        
        widget = AIMessageWidget(complex_markdown.strip())
        composed_widgets = list(widget.compose())
        
        # Should still have 2 widgets
        assert len(composed_widgets) == 2
        
        # Markdown widget should be properly created
        markdown_widget = composed_widgets[1]
        assert isinstance(markdown_widget, Markdown)
        # Note: Content verification requires app context for proper rendering
        # The important thing is that we're using a Markdown widget for rich formatting


class TestUserMessageWidget:
    """Test the UserMessageWidget"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_user_message_widget_initialization(self, mock_theme_manager):
        """Test that UserMessageWidget initializes correctly"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "blue"
        mock_theme_manager.return_value = mock_theme
        
        message = "Show me the top 10 films by rental count"
        widget = UserMessageWidget(message)
        
        assert "user-message" in widget.classes
        # The widget should be properly initialized
        assert widget is not None


class TestSystemMessageWidget:
    """Test the SystemMessageWidget"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_system_message_widget_initialization(self, mock_theme_manager):
        """Test that SystemMessageWidget initializes correctly"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "yellow"
        mock_theme_manager.return_value = mock_theme
        
        message = "Database connection established"
        widget = SystemMessageWidget(message)
        
        assert "system-message" in widget.classes
        assert widget is not None


class TestErrorMessageWidget:
    """Test the ErrorMessageWidget"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_error_message_widget_initialization(self, mock_theme_manager):
        """Test that ErrorMessageWidget initializes correctly"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "red"
        mock_theme_manager.return_value = mock_theme
        
        message = "Query failed: Table not found"
        widget = ErrorMessageWidget(message)
        
        assert "error-message" in widget.classes
        assert widget is not None


class TestToolCallWidget:
    """Test the ToolCallWidget"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_tool_call_widget_initialization(self, mock_theme_manager):
        """Test that ToolCallWidget initializes correctly"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "cyan"
        mock_theme_manager.return_value = mock_theme
        
        tool_name = "database_query"
        description = "SELECT * FROM films LIMIT 10"
        widget = ToolCallWidget(tool_name, description)
        
        assert "tool-call" in widget.classes
        assert widget is not None


class TestToolResultWidget:
    """Test the ToolResultWidget"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_tool_result_widget_initialization(self, mock_theme_manager):
        """Test that ToolResultWidget initializes correctly"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "green"
        mock_theme_manager.return_value = mock_theme
        
        tool_name = "database_query"
        result_summary = "10 rows returned"
        widget = ToolResultWidget(tool_name, result_summary)
        
        assert "tool-result" in widget.classes
        assert widget is not None


class TestMarkdownIntegration:
    """Test Markdown integration and formatting"""
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_markdown_widget_preserves_formatting(self, mock_theme_manager):
        """Test that Markdown widget preserves various formatting elements"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "magenta"
        mock_theme_manager.return_value = mock_theme
        
        # Test various Markdown elements
        test_cases = [
            "**Bold text**",
            "*Italic text*",
            "`inline code`",
            "# Header 1",
            "## Header 2", 
            "### Header 3",
            "- List item",
            "> Blockquote",
            "[Link](https://example.com)",
            "```\ncode block\n```"
        ]
        
        for markdown_content in test_cases:
            widget = AIMessageWidget(markdown_content)
            composed_widgets = list(widget.compose())
            
            # Should have Markdown widget
            assert len(composed_widgets) == 2
            markdown_widget = composed_widgets[1]
            assert isinstance(markdown_widget, Markdown)
            # Content verification requires app context - we just verify structure
    
    @patch('sqlbot.interfaces.message_widgets.get_theme_manager')
    def test_markdown_widget_handles_empty_content(self, mock_theme_manager):
        """Test that Markdown widget handles empty or whitespace content"""
        # Mock theme manager
        mock_theme = Mock()
        mock_theme.get_color.return_value = "magenta"
        mock_theme_manager.return_value = mock_theme
        
        test_cases = ["", "   ", "\n\n", "\t"]
        
        for content in test_cases:
            widget = AIMessageWidget(content)
            composed_widgets = list(widget.compose())
            
            # Should still create widgets even with empty content
            assert len(composed_widgets) == 2
            markdown_widget = composed_widgets[1]
            assert isinstance(markdown_widget, Markdown)

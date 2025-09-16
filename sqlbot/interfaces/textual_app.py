"""
Textual TUI Application for SQLBot

This module provides a modern terminal user interface for SQLBot using the Textual framework.
It features a two-column layout with conversation history on the left and detail view on the right.
"""

from typing import Optional, List
import time
import sys
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, VerticalScroll
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.geometry import Size
from textual.reactive import reactive
from textual.message import Message
from textual.command import Command, CommandPalette, Provider
from textual import events
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
import json

from sqlbot.core import SQLBotAgent, SQLBotConfig
from sqlbot.conversation_memory import ConversationMemoryManager
from sqlbot.interfaces.repl.formatting import ResultFormatter, MessageStyle
from sqlbot.interfaces.repl.commands import CommandHandler
from sqlbot.interfaces.textual_widgets import EnhancedDetailViewWidget
from sqlbot.interfaces.shared_session import SQLBotSession
from sqlbot.interfaces.message_formatter import MessageSymbols
from sqlbot.interfaces.theme_system import get_theme_manager, ThemeMode


    


class ConversationHistoryWidget(ScrollableContainer):
    """Widget for displaying conversation history where everything scrolls together"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # No RichLog needed - we mount widgets directly to this ScrollableContainer
        # Initialize unified message display system
        self.memory_manager = None
        self.unified_display = None
        self._welcome_message_content = None  # Store welcome message for rebuilds
        self._welcome_widget = None  # Store welcome widget for rebuilds
        
        # Track content for potential re-wrapping on resize
        self._last_width = 0
    
    def compose(self) -> ComposeResult:
        """Compose - no child widgets needed, we mount them dynamically"""
        # No static children - all message widgets are mounted dynamically
        return []
    
    def scroll_end(self):
        """Scroll to the end of the conversation"""
        # Use call_after_refresh to ensure the layout is updated before scrolling
        def _do_scroll():
            # Scroll to a position that's guaranteed to be at the bottom
            # Use a large value to ensure we scroll past the end
            self.scroll_to(y=self.max_scroll_y + 1000, animate=False)
        
        # Schedule the scroll after the next refresh cycle
        self.call_after_refresh(_do_scroll)
    
    def show_welcome_message(self, banner_text: str):
        """Show welcome message as a system message with no icon"""
        # Store the welcome content for rebuilds
        self._welcome_message_content = banner_text
        
        # Use the unified display system to show as a system message
        if self.unified_display:
            # Display the welcome message as a custom system message without icon
            self._display_welcome_system_message(banner_text)
        else:
            # Fallback: Create and mount a Static widget with the welcome content
            welcome_widget = Static(banner_text)
            welcome_widget.add_class("welcome-message")
            self.mount(welcome_widget)
            self._welcome_widget = welcome_widget
        
        self.scroll_end()
    
    def _display_welcome_system_message(self, message: str):
        """Display welcome message as a system message without icon"""
        from sqlbot.interfaces.message_widgets import Static
        from rich.text import Text
        from textual.widgets import Markdown
        from sqlbot.interfaces.theme_system import get_theme_manager
        
        # Create a custom widget without icon for the welcome message
        theme = get_theme_manager()
        system_color = theme.get_color('system_message')
        
        # Create a markdown widget for proper rendering of the welcome message
        welcome_widget = Markdown(message)
        welcome_widget.add_class("system-message")  # Use system message styling
        
        # Mount the widget directly
        self.mount(welcome_widget)
        self._welcome_widget = welcome_widget
    
    def set_memory_manager(self, memory_manager):
        """Set the memory manager and initialize unified display"""
        self.memory_manager = memory_manager
        from sqlbot.interfaces.unified_message_display import UnifiedMessageDisplay, TextualMessageDisplay
        
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
        self.unified_display.add_system_message(message, style)
    
    def add_error_message(self, message: str) -> None:
        """Add an error message to the conversation"""
        self.unified_display.add_error_message(message)
    
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
        # Create a static widget for the query result
        result_widget = Static(result_text)
        result_widget.add_class("query-result")
        self.mount(result_widget)
        self.scroll_end()
    
    def clear_history(self) -> None:
        """Clear the conversation history display"""
        # Remove all child widgets
        for child in list(self.children):
            child.remove()
        if self.unified_display:
            self.unified_display.clear_display()
    
    def rebuild_display_with_theme(self) -> None:
        """Rebuild the conversation display with current theme colors"""
        if not self.unified_display:
            return
            
        # Get the current messages before clearing
        temp_messages = self.unified_display.display_impl._display_messages.copy()
        
        # Clear all child widgets
        for child in list(self.children):
            child.remove()
        
        # Restore welcome message if it exists
        if self._welcome_message_content:
            self._display_welcome_system_message(self._welcome_message_content)
        
        # Clear the message tracking to prevent duplicates
        self.unified_display.display_impl._display_messages = []
        
        # Re-render all messages without tracking (to prevent duplicates)
        for message_type, original_content in temp_messages:
            if message_type == "user":
                self.unified_display.display_impl._render_user_message_without_tracking(original_content)
            elif message_type == "ai":
                self.unified_display.display_impl._render_ai_message_without_tracking(original_content)
            elif message_type == "system":
                self.unified_display.display_impl._render_system_message_without_tracking(original_content)
            elif message_type == "error":
                self.unified_display.display_impl._render_error_message_without_tracking(original_content)
            elif message_type == "success":
                self.unified_display.display_impl._render_success_message_without_tracking(original_content)
            elif message_type == "tool_call":
                tool_name, description = original_content
                self.unified_display.display_impl._render_tool_call_without_tracking(tool_name, description)
            elif message_type == "tool_result":
                tool_name, result_summary = original_content
                self.unified_display.display_impl._render_tool_result_without_tracking(tool_name, result_summary)
            elif message_type == "thinking":
                self.unified_display.display_impl._render_thinking_without_tracking(original_content)
        
        # Restore the message tracking
        self.unified_display.display_impl._display_messages = temp_messages
        
        # Scroll to end
        self.scroll_end()
    
    def on_resize(self, event) -> None:
        """Handle widget resize by reflowing content"""
        # Check if width changed significantly 
        current_width = self.size.width if self.size else 0
        if abs(current_width - self._last_width) > 5:  # Only reflow on significant changes
            self._last_width = current_width
            # Trigger content reflow using our widget-level rebuild method
            self.rebuild_display_with_theme()
    
    def _format_ai_response_with_markdown(self, content: str) -> str:
        """Format AI response content with markdown styling"""
        import re
        
        # Process in order to avoid conflicts
        
        # Code blocks (inline) - process first to avoid conflicts with other formatting
        content = re.sub(r'`([^`]+)`', r'[dim cyan]\1[/dim cyan]', content)
        
        # Bold text
        content = re.sub(r'\*\*([^*]+)\*\*', r'[bold]\1[/bold]', content)
        
        # Italic text (avoid already processed bold text)
        content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'[italic]\1[/italic]', content)
        
        # Headers (simple approach)
        content = re.sub(r'^### (.+)$', r'[bold cyan]\1[/bold cyan]', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'[bold magenta]\1[/bold magenta]', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.+)$', r'[bold yellow]\1[/bold yellow]', content, flags=re.MULTILINE)
        
        return content


# DetailViewWidget is now replaced by EnhancedDetailViewWidget in textual_widgets.py


class SQLBotCommandProvider(Provider):
    """Command provider for SQLBot-specific commands"""
    
    def __init__(self, screen, match_style=None):
        """Initialize the command provider"""
        super().__init__(screen, match_style)
    
    @property
    def app(self) -> 'SQLBotTextualApp':
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
        
        if "theme" in query.lower() or "color" in query.lower() or any(t in query.lower() for t in ["dark", "light", "cool", "warm"]):
            # Add unified theme names to command palette
            commands.extend([
                Command(
                    "theme-dark",
                    "Dark Theme",
                    "Switch to dark theme (Tokyo Night base)",
                    lambda: self.change_theme(ThemeMode.DARK)
                ),
                Command(
                    "theme-light",
                    "Light Theme",
                    "Switch to light theme (clean, minimal)",
                    lambda: self.change_theme(ThemeMode.LIGHT)
                ),
                Command(
                    "theme-cool-dark",
                    "Cool Dark Theme",
                    "Switch to cool dark theme (purple/blue tones)",
                    lambda: self.change_theme(ThemeMode.COOL_DARK)
                ),
                Command(
                    "theme-cool-light",
                    "Cool Light Theme",
                    "Switch to cool light theme (purple/blue tones)",
                    lambda: self.change_theme(ThemeMode.COOL_LIGHT)
                ),
                Command(
                    "theme-warm-dark",
                    "Warm Dark Theme",
                    "Switch to warm dark theme (Solarized earth tones)",
                    lambda: self.change_theme(ThemeMode.WARM_DARK)
                ),
                Command(
                    "theme-warm-light",
                    "Warm Light Theme",
                    "Switch to warm light theme (Solarized earth tones)",
                    lambda: self.change_theme(ThemeMode.WARM_LIGHT)
                )
            ])
        
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
    
    async def change_theme(self, theme_mode: ThemeMode) -> None:
        """Change the app theme"""
        if self.app:
            self.app.set_theme(theme_mode)


class QueryInput(Input):
    """Custom input widget for SQLBot queries"""
    
    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Type your question or SQL query (end with ; for SQL)...",
            **kwargs
        )


class SQLBotTextualApp(App):
    """Main Textual application for SQLBot"""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    Header {
        background: $primary;
        color: $text;
        text-style: bold;
    }


    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #conversation-panel {
        width: 1fr;
        height: 1fr;
        border: round $qbot-panel-border;
        background: $surface;
    }

    #detail-panel {
        width: 2fr;
        height: 1fr;
        border: round $qbot-panel-border;
        background: $surface;
    }

    #query-input {
        height: 3;
        dock: bottom;
        border: heavy $qbot-input-border;
        background: $surface;
        color: $qbot-user-message;
    }

    ConversationHistoryWidget {
        scrollbar-gutter: stable;
        height: 1fr;
        background: $surface;
    }

    RichLog {
        background: $surface;
        color: $text;
        text-wrap: wrap;
        min-width: 13;
    }
    
    /* Ensure right panel widgets don't overflow */
    #detail-panel > * {
        height: 1fr;
        overflow-y: auto;
        background: $surface;
    }

    /* Consistent background for all ListView and related widgets */
    ListView {
        background: $surface;
    }

    QueryResultViewer {
        background: $surface;
    }

    QueryResultSidebar {
        background: $surface;
    }

    QueryResultContentView {
        background: $surface;
    }

    ConversationDebugViewer {
        background: $surface;
    }

    EnhancedDetailViewWidget {
        background: $surface;
    }
    
    .thinking-indicator {
        height: 1;
        width: auto;
        margin: 1 0;
        color: #ff00ff;
        background: transparent;
    }
    
    .thinking-indicator LoadingIndicator {
        color: #ff00ff;
    }
    
    LoadingIndicator.loading-indicator {
        color: #ff00ff;
    }
    
    /* Textual will now use the --block-cursor-* CSS variables defined above for ListView selection */
    
    /* Nuclear approach: remove ALL Collapsible padding/margin */
    Collapsible {
        background: $surface;  /* Match main background color */
        padding: 0;           /* Remove all padding */
        margin: 0;            /* Remove all margins */
    }
    
    /* Add padding only to the container widgets */
    .collapsible-tool-call,
    .collapsible-tool-result {
        padding-left: 1;      /* Only 1 character here */
        margin: 0;            /* No margins */
    }
    
    /* Make Collapsible contents wrap text */
    .collapsible-tool-call Static,
    .collapsible-tool-result Static {
        text-wrap: wrap;
        width: 100%;
    }
    
    /* Add consistent spacing to message widgets to match Collapsibles */
    .user-message {
        padding-left: 1;
        margin-top: 1;  /* Match the natural spacing of Collapsibles */
    }
    
    .ai-message {
        padding-left: 1;
        margin-top: 1;  /* Add top margin like user messages */
    }
    
    /* Markdown widget styling for rich-text formatting */
    .ai-message Markdown,
    .ai-message-content {
        text-wrap: wrap;
        width: 100%;
        background: transparent;
        color: $text;
    }
    
    /* Markdown headings with theme-appropriate colors */
    .ai-message Markdown .h1,
    .ai-message-content .h1 {
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    
    .ai-message Markdown .h2,
    .ai-message-content .h2 {
        text-style: bold;
        color: $secondary;
        margin: 1 0;
    }
    
    .ai-message Markdown .h3,
    .ai-message-content .h3 {
        text-style: bold;
        color: $accent;
        margin: 1 0;
    }
    
    /* Code blocks and inline code */
    .ai-message Markdown .code_block,
    .ai-message-content .code_block {
        background: $surface-lighten-1;
        color: $text;
        border: round $border;
        padding: 1;
        margin: 1 0;
        text-wrap: wrap;
    }
    
    .ai-message Markdown .code_inline,
    .ai-message-content .code_inline {
        background: $surface-lighten-1;
        color: $accent;
        text-style: bold;
    }
    
    /* Lists */
    .ai-message Markdown .list_item,
    .ai-message-content .list_item {
        margin-left: 2;
        color: $text;
    }
    
    /* Blockquotes */
    .ai-message Markdown .block_quote,
    .ai-message-content .block_quote {
        border-left: thick $accent;
        padding-left: 2;
        margin: 1 0;
        color: $text-muted;
        text-style: italic;
    }
    
    /* Tables */
    .ai-message Markdown .table,
    .ai-message-content .table {
        border: round $border;
        margin: 1 0;
    }
    
    /* Links */
    .ai-message Markdown .link,
    .ai-message-content .link {
        color: $primary;
        text-style: underline;
    }
    
    /* Emphasis and strong text */
    .ai-message Markdown .em,
    .ai-message-content .em {
        text-style: italic;
    }
    
    .ai-message Markdown .strong,
    .ai-message-content .strong {
        text-style: bold;
    }
    
    /* System messages (like success-message for safety checks) have no top margin */
    .system-message,
    .error-message,
    .success-message {
        padding-left: 1;
    }
    
    """
    
    TITLE = "✦ SQLBot - Database Query Assistant"
    SUB_TITLE = ""
    
    # Command palette disabled - using text input widget instead
    # COMMANDS = {SQLBotCommandProvider}
    
    def __init__(self, agent: SQLBotAgent, initial_query: Optional[str] = None, theme_mode: ThemeMode = ThemeMode.DARK, **kwargs):
        # Initialize theme manager BEFORE calling super().__init__()
        # because get_css_variables() is called during parent initialization
        self.theme_manager = get_theme_manager()
        self.theme_manager.set_theme(theme_mode)
        self.current_theme_mode = theme_mode
        
        # Now call parent init which will call get_css_variables()
        super().__init__(**kwargs)
        
        # Set the Textual built-in theme (this must be done after super().__init__)
        if self.theme_manager.is_builtin_theme:
            self.theme = self.theme_manager.get_textual_theme_name()
        
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
        
        # Use timestamp-based session ID for easy sorting and archiving
        # This ensures query results are tracked in the same list
        from datetime import datetime
        from pathlib import Path
        import glob
        
        # Try to load the most recent session, or create a new one
        query_results_dir = Path(".sqlbot/query_results")
        if query_results_dir.exists():
            # Find all session files and get the most recent one
            session_files = list(query_results_dir.glob("*.json"))
            if session_files:
                # Sort by filename (which is timestamp) and get the most recent
                most_recent_file = sorted(session_files, reverse=True)[0]
                # Extract session ID from filename (remove .json extension)
                self.session_id = most_recent_file.stem
                self.is_resuming_session = True
            else:
                # No existing sessions, create new one
                self.session_id = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
                self.is_resuming_session = False
        else:
            # Directory doesn't exist, create new session
            self.session_id = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
            self.is_resuming_session = False
        
        # Set the session ID for LLM agent creation
        from sqlbot.llm_integration import set_session_id
        set_session_id(self.session_id)
        
        # Initialize shared session for query execution
        self.session = SQLBotSession(agent.config)
        
        # Set up unified display connection once conversation widget is available
        self.call_after_refresh(self._setup_unified_display_connection)
    
    def _setup_unified_display_connection(self):
        """Connect the session's unified display to the conversation widget"""
        if self.conversation_widget and hasattr(self.conversation_widget, 'unified_display'):
            self.session.set_unified_display(self.conversation_widget.unified_display)
    
    def get_css_variables(self) -> dict[str, str]:
        """Get CSS variables for theming - adds SQLBot message colors on top of Textual themes"""
        theme_vars = {}
        if hasattr(self, 'theme_manager') and self.theme_manager:
            theme_vars = self.theme_manager.get_css_variables()
        
        return {**super().get_css_variables(), **theme_vars}
    
    def set_theme(self, theme_mode: ThemeMode):
        """Change the app theme using new hybrid architecture"""
        # Update theme manager 
        self.theme_manager.set_theme(theme_mode)
        self.current_theme_mode = theme_mode
        
        # Set Textual's built-in theme if it's a built-in theme
        if self.theme_manager.is_builtin_theme:
            self.theme = self.theme_manager.get_textual_theme_name()
        
        # Refresh CSS with new variables (for both built-in and user themes)
        self.refresh_css(animate=False)
        self.screen._update_styles()
        
        self.notify(f"Theme changed to {theme_mode.value}", severity="information")
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout"""
        yield Header(show_clock=False)
        
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
    
    def on_key(self, event: events.Key) -> None:
        """Handle key events - ensure input widget always gets typed input"""
        # For ANY printable key, make sure the input widget has focus
        if (hasattr(self, 'set_focus_on_key') and self.set_focus_on_key and 
            self.query_input and event.is_printable and not event.key.startswith('ctrl+')):
            
            # Always focus the input widget for printable characters
            if not self.query_input.has_focus:
                self.query_input.focus()
                # Move cursor to end to avoid selecting all text
                self.call_after_refresh(lambda: self.query_input.action_end())
            
            # Let the input widget handle the key event
            # (Textual will automatically route it there after focus)
    
    def on_focus(self, event: events.Focus) -> None:
        """Handle focus events - keep input widget focused"""
        # If something other than the input widget or ListView gets focus, redirect it back
        # Allow ListView in detail panel to have focus for selection highlighting
        allowed_widgets = [self.query_input]
        if hasattr(self, 'detail_widget') and self.detail_widget:
            if hasattr(self.detail_widget, 'query_result_viewer') and self.detail_widget.query_result_viewer:
                if hasattr(self.detail_widget.query_result_viewer, 'sidebar'):
                    allowed_widgets.append(self.detail_widget.query_result_viewer.sidebar)
        
        if (hasattr(self, 'set_focus_on_key') and self.set_focus_on_key and 
            self.query_input and event.widget not in allowed_widgets):
            
            
            # Use call_later to avoid focus conflicts during event processing
            def refocus_input():
                if self.query_input:
                    self.query_input.focus()
                    # Move cursor to end to avoid selecting all text
                    self.call_after_refresh(lambda: self.query_input.action_end())
            self.call_later(refocus_input)
    
    def on_blur(self, event: events.Blur) -> None:
        """Handle blur events - refocus input if it loses focus"""
        if (hasattr(self, 'set_focus_on_key') and self.set_focus_on_key and 
            self.query_input and event.widget == self.query_input):
            
            
            # Immediately refocus the input widget
            def refocus_input():
                if self.query_input:
                    self.query_input.focus()
                    # Move cursor to end to avoid selecting all text
                    self.call_after_refresh(lambda: self.query_input.action_end())
            self.call_later(refocus_input)
    
    def _ensure_input_focus(self) -> None:
        """Periodically ensure the input widget has focus"""
        if (hasattr(self, 'set_focus_on_key') and self.set_focus_on_key and 
            self.query_input and not self.query_input.has_focus):
            
            
            self.query_input.focus()
            # Move cursor to end to avoid selecting all text
            self.call_after_refresh(lambda: self.query_input.action_end())
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        try:
            # Initialize theme using ColorSystem approach (no manual theme registration needed)
            # CSS variables are automatically generated via get_css_variables()
            
            # Connect memory manager to widgets
            if self.detail_widget:
                self.detail_widget.set_memory_manager(self.memory_manager)
            
            if self.conversation_widget:
                self.conversation_widget.set_memory_manager(self.memory_manager)
            
            # Only show welcome message if no initial query is provided
            if not self.initial_query:
                self.call_after_refresh(self.show_welcome_message)
            
            # Execute initial query if provided (after unified display is connected)
            if self.initial_query:
                self.call_after_refresh(self._execute_initial_query_after_setup)
            
            # Focus the input and ensure it's visible
            if self.query_input:
                self.query_input.focus()
                self.query_input.scroll_visible()
                # Move cursor to end to avoid selecting all text
                self.call_after_refresh(lambda: self.query_input.action_end())
                
            # Set up auto-focus behavior - any key press should focus the input
            self.set_focus_on_key = True
            
            # Start a timer to periodically ensure input widget has focus
            self.set_interval(0.1, self._ensure_input_focus)
                
        except Exception as e:
            print(f"❌ Mount error: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_initial_query_after_setup(self) -> None:
        """Execute initial query after ensuring unified display is connected"""
        # Ensure unified display connection is established
        self._setup_unified_display_connection()
        
        # Now execute the initial query
        if self.initial_query:
            self.call_later(self.execute_initial_query)
    
    async def execute_initial_query(self) -> None:
        """Execute the initial query provided from command line"""
        if self.initial_query and self.conversation_widget:
            # Handle initial query using unified display logic
            await self.handle_query(self.initial_query)
    
    def show_welcome_message(self) -> None:
        """Display the welcome message with responsive Rich Panel"""
        if not self.conversation_widget:
            print("❌ ERROR: conversation_widget is None in show_welcome_message")
            return
        
        # Create banner using SAME system as --text mode
        from sqlbot.interfaces.banner import get_banner_content
        import os
        
        # Get configuration info - SAME as --text mode
        profile = getattr(self.session.config, 'profile', None) if self.session and self.session.config else None
        llm_model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
        llm_available = True
        
        banner_text = get_banner_content(
            profile=profile,
            llm_model=llm_model,
            llm_available=llm_available,
            interface_type="textual"
        )
        
        # Show welcome message in conversation log
        self.conversation_widget.show_welcome_message(banner_text)
        
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
            elif command.startswith('/theme'):
                # Handle theme commands with all available themes
                parts = command.split()
                if len(parts) == 1:
                    # Show current theme
                    current_theme = self.theme_manager.current_mode.value
                    self.conversation_widget.add_system_message(f"Current theme: {current_theme}", "cyan")
                    
                    # Show the 6 unified themes
                    available_themes = self.theme_manager.get_available_themes()
                    unified_themes = [name for name, type_ in available_themes.items() if type_ == "unified"]
                    user_themes = [name for name, type_ in available_themes.items() if type_ == "user"]

                    if unified_themes:
                        self.conversation_widget.add_system_message(f"Available themes: {', '.join(unified_themes)}", "green")
                    if user_themes:
                        self.conversation_widget.add_system_message(f"User themes: {', '.join(user_themes)}", "magenta")
                    self.conversation_widget.add_system_message("Usage: /theme <theme_name>", "cyan")
                elif len(parts) == 2:
                    theme_name = parts[1].lower()
                    
                    try:
                        # Try to set theme by name (supports both built-in and user themes)
                        self.theme_manager.set_theme_by_name(theme_name)
                        
                        # Set Textual's built-in theme if it's a built-in theme
                        if self.theme_manager.is_builtin_theme:
                            self.theme = self.theme_manager.get_textual_theme_name()
                        
                        # Refresh CSS with new variables
                        self.refresh_css(animate=False)
                        self.screen._update_styles()
                        
                        # IMPORTANT: Refresh existing conversation messages with new theme colors
                        if self.conversation_widget and hasattr(self.conversation_widget, 'rebuild_display_with_theme'):
                            self.conversation_widget.rebuild_display_with_theme()
                        
                        theme_type = self.theme_manager.get_available_themes().get(theme_name, "unknown")
                        self.conversation_widget.add_system_message(f"Switched to {theme_type} theme: {theme_name}", "green")
                        
                    except ValueError:
                        self.conversation_widget.add_system_message(f"Unknown theme: {theme_name}", "error")
                        
                        # Show available themes
                        available_themes = self.theme_manager.get_available_themes()
                        builtin_themes = [name for name, type_ in available_themes.items() if type_ == "built-in"]
                        user_themes = [name for name, type_ in available_themes.items() if type_ == "user"]
                        
                        if builtin_themes:
                            self.conversation_widget.add_system_message(f"Built-in themes: {', '.join(builtin_themes)}", "cyan")
                        if user_themes:
                            self.conversation_widget.add_system_message(f"User themes: {', '.join(user_themes)}", "green")
                else:
                    self.conversation_widget.add_system_message("Usage: /theme <theme_name>", "error")
                return
            elif command == '/screenshot':
                # Take SVG screenshot like the command palette did
                try:
                    path = self.save_screenshot()
                    self.conversation_widget.add_system_message(f"Screenshot saved to: {path}", "green")
                except Exception as e:
                    self.conversation_widget.add_error_message(f"Screenshot failed: {e}")
                return
            elif command == '/debug-theme':
                # Debug theme system state
                theme_manager = get_theme_manager()
                current_theme = theme_manager.current_theme
                debug_info = f"""Theme Debug Info:
• Current theme: {theme_manager.current_mode.value}
• Theme colors: user={current_theme.user_message}, ai={current_theme.ai_response}
• System={current_theme.system_message}, error={current_theme.error}
• Conversation widget unified display: {self.conversation_widget.unified_display is not None if self.conversation_widget else False}
• Display impl type: {type(self.conversation_widget.unified_display.display_impl).__name__ if self.conversation_widget and self.conversation_widget.unified_display else 'None'}
• Tracked messages: {len(self.conversation_widget.unified_display.display_impl._display_messages) if self.conversation_widget and self.conversation_widget.unified_display and hasattr(self.conversation_widget.unified_display.display_impl, '_display_messages') else 'Unknown'}"""
                self.conversation_widget.add_system_message(debug_info, "cyan")
                return
            elif command == '/quit' or command == '/exit':
                # Clean exit like command palette quit
                self.exit()
                return
            elif command == '/panel' or command.startswith('/panel '):
                # Switch right panel view (query results vs conversation debug)
                parts = command.split()
                if len(parts) == 1:
                    self.conversation_widget.add_system_message("Panel switching:", "cyan")
                    self.conversation_widget.add_system_message("• /panel results - Show query results", "cyan")
                    self.conversation_widget.add_system_message("• /panel debug - Show conversation debug", "cyan")
                elif len(parts) == 2:
                    panel_type = parts[1].lower()
                    if panel_type in ['results', 'result']:
                        if self.detail_widget:
                            self.detail_widget.switch_to_query_results()
                            self.conversation_widget.add_system_message("Switched to Query Results view", "green")
                    elif panel_type in ['debug', 'conversation', 'history']:
                        if self.detail_widget:
                            self.detail_widget.switch_to_conversation_debug()
                            self.conversation_widget.add_system_message("Switched to Conversation Debug view", "green")
                    else:
                        self.conversation_widget.add_system_message("Unknown panel type. Use: results, debug", "error")
                return
            elif command == '/keys' or command == '/help-keys':
                # Show key bindings (replacement for "Show keys and help panel")
                help_text = """Key Bindings:
• Ctrl+C, Ctrl+Q, Escape - Exit application
• Ctrl+\\ - Command palette (disabled, use slash commands)
• Enter - Submit query
• ↑/↓ - Navigate input history

Slash Commands:
• /help - Show all commands
• /theme [dark|light|cool-dark|cool-light|warm-dark|warm-light] - Change theme (unified names)
• /screenshot - Save SVG screenshot
• /panel [results|debug] - Switch right panel view
• /clear - Clear conversation history
• /debug-theme - Show theme system debug info
• /quit, /exit - Exit application"""
                self.conversation_widget.add_system_message(help_text, "cyan")
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
                
                # Sync conversation display to ensure tool calls are shown
                self.conversation_widget.sync_conversation_display()
            
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
                
                # Force UI refresh to show the thinking indicator before starting LLM
                self.refresh()
                # Give a tiny delay to ensure the thinking indicator renders
                import asyncio
                await asyncio.sleep(0.1)
            
            # Execute LLM query with proper async to keep animation running
            
            import asyncio
            import concurrent.futures
            
            # Use ThreadPoolExecutor with complete async context and error reporting
            def execute_query_with_async_context():
                # Create a complete async context for the thread
                import asyncio
                async def async_execute():
                    try:
                        # This runs in a proper async context
                        result = self.session.execute_query(query)
                        return result
                    except Exception as e:
                        # Capture detailed error information
                        import traceback
                        error_details = {
                            'error': str(e),
                            'type': type(e).__name__,
                            'traceback': traceback.format_exc()
                        }
                        # Re-raise with more context
                        raise Exception(f"LLM execution failed: {type(e).__name__}: {str(e)}") from e
                
                # Run the async function in a new event loop
                result = asyncio.run(async_execute())
                return result
            
            # Execute in thread pool to avoid blocking UI
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(executor, execute_query_with_async_context)
                
                # Wait for completion while keeping UI responsive
                result = await future
            
            # Add result to display
            if result and self.conversation_widget:
                formatted_result = self.session.get_formatted_result(result, "rich")
                self.conversation_widget.add_ai_message(formatted_result)
                
                # Sync conversation display to ensure tool calls are shown
                self.conversation_widget.sync_conversation_display()
            
            # Refocus the input widget after query completion (with delay to let ListView selection render)
            if self.query_input:
                def _restore_focus(timer):
                    self.query_input.focus()
                    # Move cursor to end to avoid selecting all text
                    self.call_after_refresh(lambda: self.query_input.action_end())
                
                # Delay the focus restoration to let ListView selection render first
                self.call_later(_restore_focus, 0.2)
            
            # Update query results and conversation debug views (async to prevent blocking)
            if self.detail_widget:
                def _update_detail_views():
                    try:
                        self.detail_widget.on_new_query_result()  # Update query results panel
                    except Exception as e:
                        # Log error but don't crash the app
                        pass
                    
                    try:
                        self.detail_widget.on_conversation_updated()  # Update conversation debug view
                    except Exception as e:
                        # Log error but don't crash the app
                        pass
                
                # Schedule the updates to run after the current UI refresh cycle
                self.call_after_refresh(_update_detail_views)
                
        except Exception as e:
            if self.conversation_widget:
                # Show detailed error information in the UI
                import traceback
                error_details = f"LLM query failed: {type(e).__name__}: {str(e)}"
                full_traceback = traceback.format_exc()
                
                # Add the main error message
                self.conversation_widget.add_error_message(error_details)
                
                # Add the full traceback as a system message for debugging
                self.conversation_widget.add_system_message(f"Full error details:\n{full_traceback}", "red")
                
            print(f"❌ LLM query error: {e}")
            import traceback
            traceback.print_exc()
    
# REMOVED: _sync_memory_to_conversation_widget - no longer needed
# Textual interface now captures output directly from unified display system
    
    def _execute_query_sync(self, query: str) -> str:
        """Execute query synchronously - same as --no-repl mode"""
        try:
            # Use the exact same execution function as --no-repl mode
            from sqlbot.llm_integration import handle_llm_query
            import os
            
            # Same parameters as --no-repl mode (now always runs in main thread)
            timeout_seconds = int(os.getenv('SQLBOT_LLM_TIMEOUT', '120'))
            max_retries = int(os.getenv('SQLBOT_LLM_RETRIES', '3'))
            
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


def create_textual_app_from_args(args) -> SQLBotTextualApp:
    """
    Create SQLBot Textual app from command line arguments
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured SQLBotTextualApp instance
    """
    # Create configuration
    config = SQLBotConfig.from_env(args.profile if hasattr(args, 'profile') and args.profile else None)
    
    # Apply command line overrides
    if hasattr(args, 'dangerous') and args.dangerous:
        config.dangerous = True
    if hasattr(args, 'preview') and args.preview:
        config.preview_mode = True
    
    # Create agent
    agent = SQLBotAgent(config)
    
    # Create Textual app
    return SQLBotTextualApp(agent)


async def run_textual_app(agent: SQLBotAgent) -> None:
    """
    Run the SQLBot Textual application
    
    Args:
        agent: Configured SQLBotAgent instance
    """
    app = SQLBotTextualApp(agent)
    await app.run_async()

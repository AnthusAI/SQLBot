"""
Unified Message Display System for SQLBot

This module provides a single, consistent message display system that works across
both the Textual app and CLI text mode interfaces, ensuring DRY principles and
consistent user experience.
"""

from typing import List, Optional, Callable, Protocol, Any
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.console import Group
from sqlbot.interfaces.message_formatter import MessageSymbols, format_llm_response
from sqlbot.interfaces.theme_system import get_theme_manager, QBOT_MESSAGE_COLORS
from sqlbot.interfaces.rich_theme_generator import get_rich_theme_generator
from sqlbot.interfaces.message_widgets import (
    UserMessageWidget, AIMessageWidget, SystemMessageWidget, 
    ErrorMessageWidget, SuccessMessageWidget, ToolCallWidget, ToolResultWidget, ThinkingIndicatorWidget,
    CollapsibleToolCallWidget, CollapsibleToolResultWidget
)


class MessageDisplayProtocol(Protocol):
    """Protocol for message display implementations"""
    
    def display_user_message(self, message: str) -> None:
        """Display a user message"""
        ...
    
    def display_ai_message(self, message: str) -> None:
        """Display an AI response message"""
        ...
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Show thinking indicator that can be overwritten later"""
        ...
    
    def display_system_message(self, message: str, style: str = "cyan") -> None:
        """Display a system message"""
        ...
    
    def display_error_message(self, message: str) -> None:
        """Display an error message"""
        ...
    
    def display_success_message(self, message: str) -> None:
        """Display a success message"""
        ...
    
    def display_tool_call(self, tool_name: str, description: str = "") -> None:
        """Display a tool call"""
        ...
    
    def display_tool_result(self, tool_name: str, result_summary: str) -> None:
        """Display a tool result"""
        ...
    
    def clear_display(self) -> None:
        """Clear the display"""
        ...


class UnifiedMessageDisplay:
    """
    Unified message display system that coordinates between conversation memory
    and the actual display implementation (CLI or Textual).
    """
    
    def __init__(self, display_impl: MessageDisplayProtocol, memory_manager: Any):
        self.display_impl = display_impl
        self.memory_manager = memory_manager
        self._last_displayed_count = 0
    
    def sync_conversation_display(self) -> None:
        """
        Synchronize the display with the current conversation state.
        This ensures both interfaces show the same conversation history.
        """
        # Get all conversation messages
        messages = self.memory_manager.get_conversation_context()
        
        # Only display new messages since last sync
        new_messages = messages[self._last_displayed_count:]
        
        for message in new_messages:
            self._display_message(message)
        
        # Update our tracking
        self._last_displayed_count = len(messages)
    
    def _display_message(self, message: Any) -> None:
        """Display a single message based on its type"""
        if hasattr(message, 'type'):
            if message.type == 'human':
                # User message
                self.display_impl.display_user_message(message.content)
                
            elif message.type == 'ai':
                # AI message - may contain tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # AI message with tool calls
                    if message.content:
                        # AI reasoning/response text
                        self.display_impl.display_ai_message(message.content)
                    
                    # Each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.get('name', 'Unknown Tool')
                        tool_args = tool_call.get('args', {})
                        description = f"{str(tool_args)[:50]}..." if tool_args else ""
                        self.display_impl.display_tool_call(tool_name, description)
                else:
                    # Regular AI response without tool calls
                    self.display_impl.display_ai_message(message.content)
                    
            elif message.type == 'tool':
                # Tool result
                tool_name = getattr(message, 'name', 'Tool')
                result_summary = message.content[:100] + "..." if len(message.content) > 100 else message.content
                self.display_impl.display_tool_result(tool_name, result_summary)
    
    def add_user_message(self, message: str) -> None:
        """Add and display a user message"""
        self.memory_manager.add_user_message(message)
        self.display_impl.display_user_message(message)
        self._last_displayed_count += 1
    
    def add_ai_message(self, message: str) -> None:
        """Add and display an AI message"""
        self.memory_manager.add_assistant_message(message)
        self.display_impl.display_ai_message(message)
        self._last_displayed_count += 1
    
    def add_system_message(self, message: str, style: str = "cyan") -> None:
        """Add and display a system message"""
        # System messages typically don't go to memory manager
        self.display_impl.display_system_message(message, style)
    
    def add_error_message(self, message: str) -> None:
        """Add and display an error message"""
        # Error messages typically don't go to memory manager
        self.display_impl.display_error_message(message)
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Show thinking indicator (doesn't go to memory)"""
        # Thinking indicators are temporary and don't go to conversation memory
        self.display_impl.show_thinking_indicator(message)
    
    def clear_display(self) -> None:
        """Clear the display and reset tracking"""
        self.display_impl.clear_display()
        self._last_displayed_count = 0


class CLIMessageDisplay:
    """CLI text mode implementation of message display"""

    def __init__(self, console: Console, live_display=None):
        self.console = console
        self.live_display = live_display  # Rich Live display for real-time updates
        self.interactive_mode = False
        self.last_was_prompt = False
        self.thinking_shown = False
        self.tool_call_shown = False
        self._lines_since_thinking = 0
        self._should_exit_live = False  # Flag to signal Live display should exit
        self._exited_live_for_data = False  # Flag to track if we exited Live for data tables
        self._apply_rich_theme()
    
    def set_interactive_mode(self, interactive: bool = True):
        """Set whether we're in interactive mode (for prompt overwriting)"""
        self.interactive_mode = interactive

    def set_live_display(self, live_display):
        """Set the Rich Live display for real-time updates"""
        self.live_display = live_display
    
    def _apply_rich_theme(self):
        """Apply Rich theme to console based on current theme manager"""
        theme_manager = get_theme_manager()
        theme_generator = get_rich_theme_generator()

        # Get current theme name and resolve it to Textual theme name
        current_theme_name = theme_manager.current_mode.value
        textual_theme_name = theme_manager._resolve_theme_name(current_theme_name)

        # Get message colors for this theme
        message_colors = QBOT_MESSAGE_COLORS.get(textual_theme_name, QBOT_MESSAGE_COLORS["default"])

        # Generate Rich theme dynamically
        if theme_manager.is_builtin_theme:
            rich_theme = theme_generator.generate_rich_theme(textual_theme_name, message_colors)
        else:
            # User custom theme
            rich_theme = theme_generator.generate_rich_theme_from_user_theme(theme_manager.current_theme)

        # Create new console with theme
        from rich.console import Console
        self.console = Console(theme=rich_theme)
    
    def mark_prompt_shown(self):
        """Mark that a prompt was just shown (for overwriting)"""
        self.last_was_prompt = True
    
    def show_user_prompt(self, prompt_text: str = "> ") -> None:
        """Show user input prompt with theme styling"""
        prompt_message = f"[user_prompt]{prompt_text}[/user_prompt]"
        self.console.print(prompt_message, end="")
        self.mark_prompt_shown()
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Show thinking indicator that can be overwritten later"""
        thinking_message = f"[thinking]{MessageSymbols.AI_THINKING} {message}[/thinking]"
        self.console.print(thinking_message)
        self.thinking_shown = True
        self._lines_since_thinking = 0  # Reset counter
    
    def display_user_message(self, message: str) -> None:
        """Display a user message in CLI"""
        styled_message = f"[user_message][user_symbol]{MessageSymbols.USER_MESSAGE}[/user_symbol] {message}[/user_message]"

        # In interactive mode, overwrite the prompt line if it was just shown
        if self.interactive_mode and self.last_was_prompt:
            # Move cursor up one line and clear it, then print the user message
            import sys
            # Use direct terminal control for cursor movement
            sys.stdout.write("\033[1A\033[2K")  # Move up and clear line
            sys.stdout.flush()
            self.console.print(styled_message, end="")
            self.console.print()  # Add newline
            self.last_was_prompt = False
        else:
            self.console.print()  # Add blank line before message
            self.console.print(styled_message)
    
    def display_ai_message(self, message: str) -> None:
        """Display an AI response message in CLI with Markdown rendering"""
        from rich.markdown import Markdown

        # Apply message formatting first
        pre_formatted = format_llm_response(message)
        # Extract content after symbol if present
        if pre_formatted.startswith(MessageSymbols.AI_RESPONSE):
            content = pre_formatted[len(MessageSymbols.AI_RESPONSE):].strip()
        else:
            content = message

        # Create the AI response symbol
        ai_symbol = f"[ai_symbol]{MessageSymbols.AI_RESPONSE}[/ai_symbol] "

        # If thinking indicator was shown, overwrite it
        if self.thinking_shown:
            import sys
            # Move cursor up one line and clear it, then print the AI response
            sys.stdout.write("\033[1A\033[2K")  # Move up and clear line
            sys.stdout.flush()
            # Add blank line before AI response
            self.console.print()
            # Print symbol and markdown separately
            self.console.print(ai_symbol, end="")
            md = Markdown(content)
            self.console.print(md)
            self.thinking_shown = False
        else:
            # Add blank line before AI response
            self.console.print()
            # Print symbol and markdown separately
            self.console.print(ai_symbol, end="")
            md = Markdown(content)
            self.console.print(md)
    
    def display_system_message(self, message: str, style: str = "system_message") -> None:
        """Display a system message in CLI"""
        styled_message = f"[system_message][system_symbol]{MessageSymbols.SYSTEM}[/system_symbol] {message}[/system_message]"
        self.console.print(styled_message)
    
    def display_error_message(self, message: str) -> None:
        """Display an error message in CLI"""
        styled_message = f"[error_message][error_symbol]{MessageSymbols.ERROR}[/error_symbol] {message}[/error_message]"

        # If we have a Live display, print above it (accumulates)
        if self.live_display:
            self.live_display.console.print(styled_message)
            self.thinking_shown = False
        else:
            # Fallback to direct console printing
            # If thinking indicator was shown, overwrite it
            if self.thinking_shown:
                # Use carriage return and overwrite the thinking line
                print(f"\r{' ' * 80}\r", end="", flush=True)  # Clear the line
                self.console.print(styled_message)
                self.thinking_shown = False
            else:
                self.console.print(styled_message)
    
    def display_success_message(self, message: str) -> None:
        """Display a success message in CLI"""
        styled_message = f"[success_message][success_symbol]{MessageSymbols.SUCCESS}[/success_symbol] {message}[/success_message]"

        # If we have a Live display, print above it (accumulates)
        if self.live_display:
            self.live_display.console.print()  # Add blank line before message
            self.live_display.console.print(styled_message)
            self.live_display.console.print()  # Add blank line after message for thinking indicator spacing
            self.thinking_shown = False
        else:
            # Fallback to direct console printing
            # If thinking indicator was shown, overwrite it
            if self.thinking_shown:
                # Use carriage return and overwrite the thinking line
                print(f"\r{' ' * 80}\r", end="", flush=True)  # Clear the line
                self.console.print()  # Add blank line before message
                self.console.print(styled_message)
                # Ensure there's a newline after overwriting
                print()  # Add explicit newline
                self.thinking_shown = False
            else:
                self.console.print()  # Add blank line before message
                self.console.print(styled_message)
                # Ensure there's a newline after the success message
                print()  # Add explicit newline
    
    def display_tool_call(self, tool_name: str, description: str = "") -> None:
        """Display a tool call in CLI using Rich Live properly"""
        if description:
            display_text = f"{tool_name}: {description}"
        else:
            display_text = f"Calling {tool_name}..."

        styled_message = f"[tool_call][tool_call_symbol]{MessageSymbols.TOOL_CALL}[/tool_call_symbol] {display_text}[/tool_call]"

        # If we have a Live display, print above it (accumulates)
        if self.live_display:
            self.live_display.console.print(styled_message)
            self.thinking_shown = False
            self.tool_call_shown = True
        else:
            # Fallback to direct console printing
            self.console.print(styled_message)
            self.tool_call_shown = True
    
    def display_tool_result(self, tool_name: str, result_summary: str) -> None:
        """Display a tool result in CLI"""
        styled_message = f"[tool_result][tool_result_symbol]{MessageSymbols.TOOL_RESULT}[/tool_result_symbol] {tool_name} → {result_summary}[/tool_result]"

        # If we have a Live display, print above it (accumulates)
        if self.live_display:
            self.live_display.console.print(styled_message)
            self.tool_call_shown = False
        else:
            # Fallback to direct console printing
            # If tool call was shown, overwrite it
            if self.tool_call_shown:
                # Use carriage return and overwrite the tool call line
                print(f"\r{' ' * 80}\r", end="", flush=True)  # Clear the line
                self.console.print(styled_message)
                self.tool_call_shown = False
            else:
                self.console.print(styled_message)
    
    def display_tool_result_with_data(self, tool_name: str, result_summary: str, result_data=None) -> None:
        """Display a tool result with actual data in CLI using Rich table"""
        # First show the summary
        styled_message = f"[tool_result][tool_result_symbol]{MessageSymbols.TOOL_RESULT}[/tool_result_symbol] {tool_name} → {result_summary}[/tool_result]"

        # If we have a Live display, print the summary above it (accumulates)
        if self.live_display:
            self.live_display.console.print(styled_message)
            self.tool_call_shown = False
        else:
            # Fallback to direct console printing
            self.console.print()  # Add blank line before message
            self.console.print(styled_message)
            self.tool_call_shown = False
        
        # Then show the actual data if available
        if result_data and hasattr(result_data, 'data') and result_data.data:
            from rich.table import Table

            # Create a Rich table with no width limit for all data
            table = Table(show_header=True, header_style="bold magenta", width=None)

            # Add columns - no width limits for any columns
            if hasattr(result_data, 'columns') and result_data.columns:
                for col in result_data.columns:
                    table.add_column(str(col), no_wrap=False, width=None)

            # Add rows (limit to first 10 for readability, show full text for all columns)
            max_rows = 10
            for i, row in enumerate(result_data.data):
                if i >= max_rows:
                    table.add_row(*["..." for _ in result_data.columns])
                    break
                # Convert all values to strings and handle None values - show full text for ALL columns
                row_values = [str(val) if val is not None else "" for val in row.values()]
                table.add_row(*row_values)

            # Print table above live display (accumulates) or use regular console
            if self.live_display:
                self.live_display.console.print(table)
            else:
                self.console.print(table)

            # Show row count info
            total_rows = len(result_data.data)
            if total_rows > max_rows:
                row_count_msg = f"[dim]Showing first {max_rows} of {total_rows} rows[/dim]"
                if self.live_display:
                    self.live_display.console.print(row_count_msg)
                    self.live_display.console.print()  # Add blank line after table
                else:
                    self.console.print(row_count_msg)
                    self.console.print()  # Add blank line after table
            else:
                # Add blank line after table even when no row count message
                if self.live_display:
                    self.live_display.console.print()
                else:
                    self.console.print()
        elif result_data and hasattr(result_data, 'data') and not result_data.data:
            no_data_msg = "[dim]No data returned[/dim]"
            if self.live_display:
                self.live_display.console.print(no_data_msg)
                self.live_display.console.print()  # Add blank line after no data message
            else:
                self.console.print(no_data_msg)
                self.console.print()  # Add blank line after no data message
    
    def clear_display(self) -> None:
        """Clear the CLI display"""
        # CLI doesn't have a clear concept, just print a separator
        self.console.print("\n" + "─" * 80 + "\n")


class TextualMessageDisplay:
    """Textual app implementation of message display"""
    
    def __init__(self, conversation_widget):
        self.conversation_widget = conversation_widget
        self.thinking_shown = False
        self._display_messages = []  # Track messages for rebuilding
        self._current_thinking_widget = None  # Track current thinking widget
        self._pending_collapsibles = []  # Track collapsibles to auto-collapse
    
    def show_user_prompt(self, prompt_text: str = "> ") -> None:
        """Show user input prompt with theme styling (Textual version)"""
        # In Textual, prompts are typically handled by Input widgets
        # This is for completeness if needed in the future
        prompt_message = f"[user-prompt]{prompt_text}[/user-prompt]"
        self.conversation_widget.conversation_log.write(prompt_message)
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Mount animated ThinkingIndicatorWidget to conversation widget"""
        thinking_widget = ThinkingIndicatorWidget()
        self.conversation_widget.mount(thinking_widget)
        # Store reference for removal when AI responds
        self._current_thinking_widget = thinking_widget
        self.conversation_widget.scroll_end()
        
        # Track for theme rebuilding (store original message, not styled)
        self._display_messages.append(("thinking", message))
        
        self.conversation_widget.scroll_end()
        self.thinking_shown = True
    
    def display_user_message(self, message: str) -> None:
        """Display a user message by mounting a UserMessageWidget"""
        # Create and mount user message widget
        user_widget = UserMessageWidget(message)
        self.conversation_widget.mount(user_widget)
        
        # Track for theme rebuilding (store original message, not styled)
        self._display_messages.append(("user", message))
        
        self.conversation_widget.scroll_end()
    
    def display_ai_message(self, message: str) -> None:
        """Display an AI response message by mounting an AIMessageWidget"""
        formatted_response = format_llm_response(message)
        
        # If thinking indicator was shown, remove it
        if self.thinking_shown and self._current_thinking_widget:
            try:
                self._current_thinking_widget.remove()
            except:
                pass  # Widget might already be removed
            self._current_thinking_widget = None
            self.thinking_shown = False
            
            # Remove thinking messages from display tracking to prevent them showing up on reflow
            self._display_messages = [msg for msg in self._display_messages if msg[0] != "thinking"]
        
        # Handle tool calls vs regular AI responses
        if formatted_response.startswith(MessageSymbols.TOOL_CALL):
            # This is a tool call - create a tool call widget
            tool_widget = ToolCallWidget("Tool Call", formatted_response)
            self.conversation_widget.mount(tool_widget)
        else:
            # Regular AI response - create AI message widget
            # Extract content - keep it simple
            response_text = formatted_response[2:] if formatted_response.startswith(MessageSymbols.AI_RESPONSE) else formatted_response
            ai_widget = AIMessageWidget(response_text)
            self.conversation_widget.mount(ai_widget)
        
        # Track for theme rebuilding (store original message, not styled)
        self._display_messages.append(("ai", message))
        
        # Immediately collapse pending collapsibles when AI message is shown
        if self._pending_collapsibles:
            self._collapse_pending_collapsibles()
        
        self.conversation_widget.scroll_end()
    
    def _collapse_pending_collapsibles(self) -> None:
        """Immediately collapse all pending collapsibles"""
        # Find and collapse all Collapsible widgets within pending containers
        for container_widget in self._pending_collapsibles[:]:  # Copy list to avoid modification during iteration
            try:
                # Find the Collapsible widget within the container
                for child in container_widget.children:
                    # Check if this is a Collapsible widget by type name
                    if type(child).__name__ == 'Collapsible':
                        # Collapse if currently expanded
                        if hasattr(child, 'collapsed') and not child.collapsed:
                            child.collapsed = True
                
                self._pending_collapsibles.remove(container_widget)
                        
            except Exception:
                # If widget was removed or something went wrong, just remove from tracking
                try:
                    self._pending_collapsibles.remove(container_widget)
                except ValueError:
                    pass  # Already removed
    
    def _format_ai_response_with_markdown(self, content: str) -> str:
        """Format AI response content with markdown styling using Textual design tokens"""
        import re
        
        # Process in order to avoid conflicts
        
        # Code blocks (inline) - process first to avoid conflicts with other formatting
        content = re.sub(r'`([^`]+)`', r'[code-inline]\1[/code-inline]', content)
        
        # Bold text
        content = re.sub(r'\*\*([^*]+)\*\*', r'[bold]\1[/bold]', content)
        
        # Italic text (avoid already processed bold text)
        content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'[italic]\1[/italic]', content)
        
        # Headers (simple approach)
        content = re.sub(r'^### (.+)$', r'[$heading-3 bold]\1[/$heading-3 bold]', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'[$heading-2 bold]\1[/$heading-2 bold]', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.+)$', r'[$heading-1 bold]\1[/$heading-1 bold]', content, flags=re.MULTILINE)
        
        return content
    
    def display_system_message(self, message: str, style: str = "system_message") -> None:
        """Display a system message by mounting a SystemMessageWidget"""
        # Create and mount system message widget
        system_widget = SystemMessageWidget(message)
        self.conversation_widget.mount(system_widget)
        
        # Track for theme rebuilding (store original message, not styled)
        self._display_messages.append(("system", message))
        
        self.conversation_widget.scroll_end()
    
    def display_error_message(self, message: str) -> None:
        """Display an error message by mounting an ErrorMessageWidget"""
        def _mount_error():
            # Create and mount error message widget
            error_widget = ErrorMessageWidget(message)
            self.conversation_widget.mount(error_widget)
            
            # Track for theme rebuilding (store original message, not styled)
            self._display_messages.append(("error", message))
            
            self.conversation_widget.scroll_end()
        
        # Thread-safe mounting
        try:
            app = self.conversation_widget.app
            if app and hasattr(app, 'call_from_thread'):
                try:
                    app.call_from_thread(_mount_error)
                except Exception:
                    _mount_error()
            else:
                _mount_error()
        except Exception:
            _mount_error()
    
    def display_success_message(self, message: str) -> None:
        """Display a success message by mounting a SuccessMessageWidget"""
        def _mount_success():
            # Create and mount success message widget
            success_widget = SuccessMessageWidget(message)
            self.conversation_widget.mount(success_widget)
            
            # Track for theme rebuilding (store original message, not styled)
            self._display_messages.append(("success", message))
            
            self.conversation_widget.scroll_end()
        
        # Thread-safe mounting
        try:
            app = self.conversation_widget.app
            if app and hasattr(app, 'call_from_thread'):
                try:
                    app.call_from_thread(_mount_success)
                except Exception:
                    _mount_success()
            else:
                _mount_success()
        except Exception:
            _mount_success()
    
    def display_tool_call(self, tool_name: str, description: str = "") -> None:
        """Display a tool call by mounting a CollapsibleToolCallWidget"""
        def _mount_tool_call():
            # Create and mount collapsible tool call widget
            tool_call_widget = CollapsibleToolCallWidget(tool_name, description)
            self.conversation_widget.mount(tool_call_widget)
            
            # Track for auto-collapse after AI response
            self._pending_collapsibles.append(tool_call_widget)
            
            # Track for theme rebuilding (store original data, not styled)
            self._display_messages.append(("tool_call", (tool_name, description)))
            
            self.conversation_widget.scroll_end()
        
        # Check if we're in the main thread (Textual app context)
        try:
            # Try to access the app - this will work if we're in the main thread
            app = self.conversation_widget.app
            if app and hasattr(app, 'call_from_thread'):
                # We might be in a background thread, use call_from_thread
                try:
                    app.call_from_thread(_mount_tool_call)
                except Exception:
                    # Fallback to direct call if call_from_thread fails
                    _mount_tool_call()
            else:
                # Direct call if no app or call_from_thread not available
                _mount_tool_call()
        except Exception:
            # Fallback to direct call
            _mount_tool_call()
    
    def display_tool_result(self, tool_name: str, result_summary: str) -> None:
        """Display a tool result by mounting a CollapsibleToolResultWidget"""
        def _mount_tool_result():
            # Create and mount collapsible tool result widget
            tool_result_widget = CollapsibleToolResultWidget(tool_name, result_summary)
            self.conversation_widget.mount(tool_result_widget)
            
            # Track for auto-collapse after AI response
            self._pending_collapsibles.append(tool_result_widget)
            
            # Track for theme rebuilding (store original data, not styled)
            self._display_messages.append(("tool_result", (tool_name, result_summary)))
            
            self.conversation_widget.scroll_end()
        
        # Check if we're in the main thread (Textual app context)
        try:
            # Try to access the app - this will work if we're in the main thread
            app = self.conversation_widget.app
            if app and hasattr(app, 'call_from_thread'):
                # We might be in a background thread, use call_from_thread
                try:
                    app.call_from_thread(_mount_tool_result)
                except Exception:
                    # Fallback to direct call if call_from_thread fails
                    _mount_tool_result()
            else:
                # Direct call if no app or call_from_thread not available
                _mount_tool_result()
        except Exception:
            # Fallback to direct call
            _mount_tool_result()
    
    def display_tool_result_with_data(self, tool_name: str, result_summary: str, result_data=None) -> None:
        """Display a tool result with access to the original data for DataTable rendering"""
        def _mount_tool_result():
            # Create and mount collapsible tool result widget with data
            tool_result_widget = CollapsibleToolResultWidget(tool_name, result_summary, result_data)
            self.conversation_widget.mount(tool_result_widget)
            
            # Track for auto-collapse after AI response
            self._pending_collapsibles.append(tool_result_widget)
            
            # Track for theme rebuilding (store original data, not styled)
            self._display_messages.append(("tool_result", (tool_name, result_summary)))
            
            self.conversation_widget.scroll_end()
        
        # Check if we're in the main thread (Textual app context)
        try:
            # Try to access the app - this will work if we're in the main thread
            app = self.conversation_widget.app
            if app and hasattr(app, 'call_from_thread'):
                # We might be in a background thread, use call_from_thread
                try:
                    app.call_from_thread(_mount_tool_result)
                except Exception:
                    # Fallback to direct call if call_from_thread fails
                    _mount_tool_result()
            else:
                # Direct call if no app or call_from_thread not available
                _mount_tool_result()
        except Exception:
            # Fallback to direct call
            _mount_tool_result()
    
    def clear_display(self) -> None:
        """Clear the Textual display by removing all child widgets"""
        # Remove all child widgets from the conversation widget
        for child in list(self.conversation_widget.children):
            child.remove()
        self._display_messages = []
        self._current_thinking_widget = None
    
    # Rebuild method moved to widget level to prevent duplication issues
    
    # Manual wrapping method removed - RichLog handles this automatically now
    
    # Content extraction method removed - we now store original content directly
    
    def _render_user_message_without_tracking(self, message: str) -> None:
        """Render user message without adding to tracking (for theme rebuilds)"""
        user_widget = UserMessageWidget(message)
        self.conversation_widget.mount(user_widget)
    
    def _render_ai_message_without_tracking(self, message: str) -> None:
        """Render AI message without adding to tracking (for theme rebuilds)"""
        formatted_response = format_llm_response(message)
        
        if formatted_response.startswith(MessageSymbols.TOOL_CALL):
            tool_widget = ToolCallWidget("Tool Call", formatted_response)
            self.conversation_widget.mount(tool_widget)
        else:
            response_text = formatted_response[2:] if formatted_response.startswith(MessageSymbols.AI_RESPONSE) else formatted_response
            ai_widget = AIMessageWidget(response_text)
            self.conversation_widget.mount(ai_widget)
    
    def _render_system_message_without_tracking(self, message: str) -> None:
        """Render system message without adding to tracking (for theme rebuilds)"""
        system_widget = SystemMessageWidget(message)
        self.conversation_widget.mount(system_widget)
    
    def _render_error_message_without_tracking(self, message: str) -> None:
        """Render error message without adding to tracking (for theme rebuilds)"""
        error_widget = ErrorMessageWidget(message)
        self.conversation_widget.mount(error_widget)
    
    def _render_success_message_without_tracking(self, message: str) -> None:
        """Render success message without adding to tracking (for theme rebuilds)"""
        success_widget = SuccessMessageWidget(message)
        self.conversation_widget.mount(success_widget)
    
    def _render_tool_call_without_tracking(self, tool_name: str, description: str = "") -> None:
        """Render tool call without adding to tracking (for theme rebuilds)"""
        tool_call_widget = CollapsibleToolCallWidget(tool_name, description)
        self.conversation_widget.mount(tool_call_widget)
    
    def _render_tool_result_without_tracking(self, tool_name: str, result_summary: str) -> None:
        """Render tool result without adding to tracking (for theme rebuilds)"""
        tool_result_widget = CollapsibleToolResultWidget(tool_name, result_summary)
        self.conversation_widget.mount(tool_result_widget)
    
    def _render_thinking_without_tracking(self, message: str = "...") -> None:
        """Render thinking indicator without adding to tracking (for theme rebuilds)"""
        thinking_widget = ThinkingIndicatorWidget()
        self.conversation_widget.mount(thinking_widget)
    

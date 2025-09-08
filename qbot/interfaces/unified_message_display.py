"""
Unified Message Display System for QBot

This module provides a single, consistent message display system that works across
both the Textual app and CLI text mode interfaces, ensuring DRY principles and
consistent user experience.
"""

from typing import List, Optional, Callable, Protocol, Any
from rich.console import Console
from rich.text import Text
from qbot.interfaces.message_formatter import MessageSymbols, format_llm_response


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
    
    def __init__(self, console: Console):
        self.console = console
        self.interactive_mode = False
        self.last_was_prompt = False
        self.thinking_shown = False
        self._lines_since_thinking = 0
    
    def set_interactive_mode(self, interactive: bool = True):
        """Set whether we're in interactive mode (for prompt overwriting)"""
        self.interactive_mode = interactive
    
    def mark_prompt_shown(self):
        """Mark that a prompt was just shown (for overwriting)"""
        self.last_was_prompt = True
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Show thinking indicator that can be overwritten later"""
        thinking_message = f"[dim]{MessageSymbols.AI_THINKING} {message}[/dim]"
        self.console.print(thinking_message)
        self.thinking_shown = True
        self._lines_since_thinking = 0  # Reset counter
    
    def display_user_message(self, message: str) -> None:
        """Display a user message in CLI"""
        styled_message = f"[bold dodger_blue2]{MessageSymbols.USER_MESSAGE} {message}[/bold dodger_blue2]"
        
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
            self.console.print(styled_message)
    
    def display_ai_message(self, message: str) -> None:
        """Display an AI response message in CLI"""
        formatted_response = format_llm_response(message)
        
        # If thinking indicator was shown, overwrite it
        if self.thinking_shown:
            import sys
            # Move cursor up one line and clear it, then print the AI response
            sys.stdout.write("\033[1A\033[2K")  # Move up and clear line
            sys.stdout.flush()
            self.console.print(formatted_response, end="")
            self.console.print()  # Add newline
            self.thinking_shown = False
        else:
            self.console.print(formatted_response)
    
    def display_system_message(self, message: str, style: str = "cyan") -> None:
        """Display a system message in CLI"""
        styled_message = f"[{style}]{MessageSymbols.SYSTEM} {message}[/{style}]"
        self.console.print(styled_message)
    
    def display_error_message(self, message: str) -> None:
        """Display an error message in CLI"""
        styled_message = f"[red]{MessageSymbols.ERROR} {message}[/red]"
        self.console.print(styled_message)
    
    def display_tool_call(self, tool_name: str, description: str = "") -> None:
        """Display a tool call in CLI"""
        display_text = f"{tool_name}: {description}" if description else f"Calling {tool_name}..."
        styled_message = f"[cyan]{MessageSymbols.TOOL_CALL} {display_text}[/cyan]"
        self.console.print(styled_message)
    
    def display_tool_result(self, tool_name: str, result_summary: str) -> None:
        """Display a tool result in CLI"""
        styled_message = f"[green]{MessageSymbols.TOOL_RESULT} {tool_name} → {result_summary}[/green]"
        self.console.print(styled_message)
    
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
    
    def show_thinking_indicator(self, message: str = "...") -> None:
        """Show thinking indicator that can be overwritten later"""
        thinking_message = f"[dim]{MessageSymbols.AI_THINKING} {message}[/dim]"
        
        # Add to our tracked messages as a special thinking indicator
        self._display_messages.append(("thinking", thinking_message))
        
        self.conversation_widget.conversation_log.write(thinking_message)
        self.conversation_widget.scroll_end()
        self.thinking_shown = True
    
    def display_user_message(self, message: str) -> None:
        """Display a user message in Textual"""
        from qbot.interfaces.textual_app import MessageStyle
        styled_message = f"[{MessageStyle.USER_INPUT}]{MessageSymbols.USER_MESSAGE} {message}[/{MessageStyle.USER_INPUT}]"
        
        # Track this message
        self._display_messages.append(("user", styled_message))
        
        self.conversation_widget.conversation_log.write(styled_message)
        self.conversation_widget.scroll_end()
    
    def display_ai_message(self, message: str) -> None:
        """Display an AI response message in Textual"""
        from qbot.interfaces.textual_app import MessageStyle
        formatted_response = format_llm_response(message)
        
        # If thinking indicator was shown, just mark it as no longer shown
        # We can't easily remove it from RichLog, but the AI response will follow it
        if self.thinking_shown:
            # Remove the thinking indicator from our tracked messages
            self._display_messages = [msg for msg in self._display_messages if msg[0] != "thinking"]
            self.thinking_shown = False
        
        # Apply Rich styling to the formatted response
        if formatted_response.startswith(MessageSymbols.TOOL_CALL):
            styled_message = f"[{MessageStyle.INFO}]{formatted_response}[/{MessageStyle.INFO}]"
        else:
            # Apply markdown formatting to AI responses
            response_text = formatted_response[2:] if formatted_response.startswith(MessageSymbols.AI_RESPONSE) else formatted_response
            formatted_content = self._format_ai_response_with_markdown(response_text)
            styled_message = f"[{MessageStyle.LLM_RESPONSE}]{MessageSymbols.AI_RESPONSE} {formatted_content}[/{MessageStyle.LLM_RESPONSE}]"
        
        # Track this AI message
        self._display_messages.append(("ai", styled_message))
        
        # Use Rich Console with width constraint to force wrapping
        from rich.console import Console
        from rich.text import Text
        from io import StringIO
        
        # Create a console with limited width to force wrapping
        string_buffer = StringIO()
        console = Console(file=string_buffer, width=70, force_terminal=True)
        
        # Create Rich Text object and render it with wrapping
        text_obj = Text.from_markup(styled_message)
        console.print(text_obj)
        
        # Get the wrapped output
        wrapped_output = string_buffer.getvalue().rstrip('\n')
        
        # Write the wrapped text to the log
        self.conversation_widget.conversation_log.write(wrapped_output)
        self.conversation_widget.scroll_end()
    
    def _format_ai_response_with_markdown(self, content: str) -> str:
        """Format AI response content with markdown styling"""
        import re
        
        # Bold text
        content = re.sub(r'\*\*(.*?)\*\*', r'[bold]\1[/bold]', content)
        
        # Italic text
        content = re.sub(r'\*(.*?)\*', r'[italic]\1[/italic]', content)
        
        # Code blocks (inline)
        content = re.sub(r'`(.*?)`', r'[dim cyan]\1[/dim cyan]', content)
        
        return content
    
    def display_system_message(self, message: str, style: str = "cyan") -> None:
        """Display a system message in Textual"""
        styled_message = f"[{style}]{MessageSymbols.SYSTEM} {message}[/{style}]"
        
        # Track this message
        self._display_messages.append(("system", styled_message))
        
        self.conversation_widget.conversation_log.write(styled_message)
        self.conversation_widget.scroll_end()
    
    def display_error_message(self, message: str) -> None:
        """Display an error message in Textual"""
        from qbot.interfaces.textual_app import MessageStyle
        styled_message = f"[{MessageStyle.ERROR}]{MessageSymbols.ERROR} {message}[/{MessageStyle.ERROR}]"
        
        # Track this message
        self._display_messages.append(("error", styled_message))
        
        self.conversation_widget.conversation_log.write(styled_message)
        self.conversation_widget.scroll_end()
    
    def display_tool_call(self, tool_name: str, description: str = "") -> None:
        """Display a tool call in Textual"""
        from qbot.interfaces.textual_app import MessageStyle
        display_text = f"{tool_name}: {description}" if description else f"Calling {tool_name}..."
        styled_message = f"[{MessageStyle.INFO}]{MessageSymbols.TOOL_CALL} {display_text}[/{MessageStyle.INFO}]"
        
        # Track this message so it survives display rebuilds
        self._display_messages.append(("tool_call", styled_message))
        
        self.conversation_widget.conversation_log.write(styled_message)
        self.conversation_widget.scroll_end()
    
    def display_tool_result(self, tool_name: str, result_summary: str) -> None:
        """Display a tool result in Textual"""
        from qbot.interfaces.textual_app import MessageStyle
        styled_message = f"[{MessageStyle.SUCCESS}]{MessageSymbols.TOOL_RESULT} {tool_name} → {result_summary}[/{MessageStyle.SUCCESS}]"
        
        # Track this message so it survives display rebuilds
        self._display_messages.append(("tool_result", styled_message))
        
        self.conversation_widget.conversation_log.write(styled_message)
        self.conversation_widget.scroll_end()
    
    def clear_display(self) -> None:
        """Clear the Textual display"""
        self.conversation_widget.conversation_log.clear()

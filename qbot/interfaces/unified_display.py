"""
Unified Display Logic for QBot

This module provides shared display logic that works across both text mode and Textual interface,
ensuring DRY principles and consistent user experience.
"""

from typing import Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.text import Text
from qbot.interfaces.message_formatter import format_llm_response, MessageSymbols


def execute_query_with_unified_display(
    query: str,
    memory_manager,
    execute_llm_func: Callable[[str], str],
    console: Optional[Console] = None,
    display_refresh_func: Optional[Callable] = None,
    show_history: bool = False,
    skip_user_message: bool = False
) -> str:
    """
    Execute a query with unified display logic for both text and Textual modes.
    
    This function provides the same user experience flow:
    1. Show conversation history (if enabled)
    2. Show user message (if not skipped)
    3. Show thinking indicator  
    4. Execute query
    5. Replace thinking with result
    
    Args:
        query: The user's query
        memory_manager: ConversationMemoryManager instance
        execute_llm_func: Function to execute the LLM query
        console: Rich console for text mode (None for Textual mode)
        display_refresh_func: Function to refresh display (for Textual mode)
        show_history: Whether to show conversation history before query
        skip_user_message: If True, don't add user message to memory (caller handles it)
        
    Returns:
        The LLM response result
    """
    
    # Step 1: Handle user message and history display
    if not skip_user_message:
        # Add user message to memory if not skipped
        memory_manager.add_user_message(query)
    
    # Display conversation history if enabled (text mode only)
    if console and show_history:
        _display_conversation_history(memory_manager, console)
    
    # Step 2: Add thinking indicator to memory (temporary) 
    thinking_msg = f"{MessageSymbols.AI_THINKING} GPT-5 thinking..."
    memory_manager.add_assistant_message(thinking_msg)
    
    # Step 3: Display thinking and response with Live updates for text mode
    if console:
        if not skip_user_message:
            # REPL mode: user message already shown by input(), now show thinking -> response progression
            # Move cursor up to overwrite the input line
            console.print("\033[A\033[K", end="")  # Move up one line and clear it
            
            # Start with user message (replacing the input line)
            user_msg = f"[bold dodger_blue2]{MessageSymbols.USER_MESSAGE} {query}[/bold dodger_blue2]"
            current_display = Text.from_markup(user_msg)
        else:
            # Command-line mode: no input() line to overwrite, start with user message
            user_msg = f"[bold dodger_blue2]{MessageSymbols.USER_MESSAGE} {query}[/bold dodger_blue2]"
            console.print(user_msg)
            current_display = Text(f"{thinking_msg}", style="dim")
        
        with Live(current_display, console=console, refresh_per_second=10, auto_refresh=True) as live:
            import time
            
            if not skip_user_message:
                # REPL mode: show user message briefly, then transition to thinking
                time.sleep(0.3)  # Brief pause to show user message
                
                # Update to show thinking indicator
                thinking_text = Text(f"{thinking_msg}", style="dim")
                live.update(thinking_text)
                time.sleep(0.1)  # Brief pause to show thinking
            else:
                # Command-line mode: already showing thinking, just a brief pause
                time.sleep(0.1)
            try:
                # Execute LLM query while showing thinking indicator
                result = execute_llm_func(query)
                
                # Replace thinking message with actual result in memory
                if result:
                    # Remove the thinking message from memory
                    messages = memory_manager.get_conversation_context()
                    if messages and thinking_msg in messages[-1].content:
                        memory_manager.history.messages.pop()
                    
                    # Add the real LLM response to memory
                    memory_manager.add_assistant_message(result)
                    
                    # Update the live display with the actual response
                    formatted_response = format_llm_response(result)
                    response_text = Text.from_markup(formatted_response)
                    live.update(response_text)
                    time.sleep(0.2)  # Brief pause to show response
                
                return result
                
            except Exception as e:
                # Handle errors gracefully
                error_msg = f"❌ Error: {e}"
                
                # Remove thinking message from memory
                messages = memory_manager.get_conversation_context()
                if messages and thinking_msg in messages[-1].content:
                    memory_manager.history.messages.pop()
                
                # Add error message to memory
                memory_manager.add_assistant_message(error_msg)
                
                # Update live display with error
                live.update(Text(error_msg, style="red"))
                return error_msg
                
    elif display_refresh_func:
        # Textual mode: use existing logic with refresh function
        display_refresh_func()
        
        # Execute LLM query
        try:
            result = execute_llm_func(query)
            
            # Replace thinking message with actual result in memory
            if result:
                # Remove the thinking message from memory
                messages = memory_manager.get_conversation_context()
                if messages and thinking_msg in messages[-1].content:
                    memory_manager.history.messages.pop()
                
                # Add the real LLM response to memory
                memory_manager.add_assistant_message(result)
                
                # Refresh display to show the response
                display_refresh_func()
            
            return result
            
        except Exception as e:
            # Handle errors gracefully
            error_msg = f"❌ Error: {e}"
            
            # Remove thinking message from memory
            messages = memory_manager.get_conversation_context()
            if messages and thinking_msg in messages[-1].content:
                memory_manager.history.messages.pop()
            
            # Add error message to memory
            memory_manager.add_assistant_message(error_msg)
            
            # Refresh display
            display_refresh_func()
            return error_msg
    
    # If no console or display_refresh_func, just execute the query
    else:
        try:
            result = execute_llm_func(query)
            
            # Replace thinking message with actual result in memory
            if result:
                # Remove the thinking message from memory
                messages = memory_manager.get_conversation_context()
                if messages and thinking_msg in messages[-1].content:
                    memory_manager.history.messages.pop()
                
                # Add the real LLM response to memory
                memory_manager.add_assistant_message(result)
            
            return result
            
        except Exception as e:
            # Handle errors gracefully
            error_msg = f"❌ Error: {e}"
            
            # Remove thinking message from memory
            messages = memory_manager.get_conversation_context()
            if messages and thinking_msg in messages[-1].content:
                memory_manager.history.messages.pop()
            
            # Add error message to memory
            memory_manager.add_assistant_message(error_msg)
            
            return error_msg


def _display_conversation_history(memory_manager, console: Console) -> None:
    """Display conversation history panel for text mode when history is enabled."""
    from rich.panel import Panel
    from rich.text import Text
    
    # Get conversation messages
    messages = memory_manager.get_conversation_context()
    
    if not messages:
        return
    
    # Build conversation history text
    conversation_text = Text()
    
    for i, message in enumerate(messages):
        if hasattr(message, 'type'):
            msg_type = message.type.upper()
            content = str(message.content)
            
            # Truncate long content for display
            if len(content) > 500:
                content = content[:500] + "..."
            
            conversation_text.append(f"[{i+1}] {msg_type} MESSAGE:\n", style="bold white")
            conversation_text.append(f"{content}\n\n", style="white")
    
    # Display in a panel
    panel = Panel(
        conversation_text,
        title="Agent's Conversation History",
        border_style="red",
        width=120
    )
    console.print(panel)



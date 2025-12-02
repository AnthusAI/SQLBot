"""
Unified Display Logic for SQLBot

This module provides shared display logic that works across both text mode and Textual interface,
ensuring DRY principles and consistent user experience.
"""

from typing import Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.text import Text
from sqlbot.interfaces.message_formatter import format_llm_response, MessageSymbols


def execute_query_with_unified_display(
    query: str,
    memory_manager,
    execute_llm_func: Callable[[str], str],
    console: Optional[Console] = None,
    display_refresh_func: Optional[Callable] = None,
    show_history: bool = False,
    show_full_history: bool = False,
    skip_user_message: bool = False,
    unified_display = None
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
        
        # Note: User message is added to global conversation history in llm_integration.py
        # to avoid duplicates
    
    # Note: Display conversation history AFTER query execution to include tool calls
    
    # Step 2: Add thinking indicator to memory (temporary) 
    thinking_msg = f"{MessageSymbols.AI_THINKING} ..."
    memory_manager.add_assistant_message(thinking_msg)
    
    # Step 3: Display thinking and response with Live updates for text mode
    if console:
        if not skip_user_message:
            # REPL mode: user message already shown by input(), now show thinking -> response progression
            # Move cursor up to overwrite the input line
            import sys
            sys.stdout.write("\033[1A\033[2K")  # Move up one line and clear it
            sys.stdout.flush()

            # Print the user message immediately to replace the prompt line
            user_msg = f"[bold dodger_blue2]{MessageSymbols.USER_MESSAGE} {query}[/bold dodger_blue2]"
            console.print(user_msg)

            # Add blank line before thinking indicator
            console.print()

            # Start Live display with thinking indicator
            current_display = Text(f"{thinking_msg}", style="dim")
        else:
            # Command-line mode: no input() line to overwrite, start with user message
            console.print()  # Add blank line before user message
            user_msg = f"[bold dodger_blue2]{MessageSymbols.USER_MESSAGE} {query}[/bold dodger_blue2]"
            console.print(user_msg)
            current_display = Text(f"{thinking_msg}", style="dim")
        
        with Live(current_display, console=console, refresh_per_second=10, auto_refresh=True) as live:
            import time

            # Set the Live display on the unified_display's CLI implementation for real-time tool updates
            if unified_display and hasattr(unified_display.display_impl, 'set_live_display'):
                unified_display.display_impl.set_live_display(live)

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
                    
                    # Check if Live display is still active (may have been exited for data tables)
                    if unified_display and hasattr(unified_display.display_impl, 'live_display') and unified_display.display_impl.live_display:
                        # Update the live display with the actual response as Markdown
                        from rich.markdown import Markdown
                        from rich.console import Group

                        formatted_response = format_llm_response(result)
                        # Extract content after symbol if present
                        if formatted_response.startswith(MessageSymbols.AI_RESPONSE):
                            content = formatted_response[len(MessageSymbols.AI_RESPONSE):].strip()
                        else:
                            content = result

                        # For Live display, combine symbol and markdown content
                        # Rich Markdown can include the symbol at the beginning
                        symbol_text = f"{MessageSymbols.AI_RESPONSE} "
                        full_content = symbol_text + content
                        md = Markdown(full_content)
                        live.update(md)
                        time.sleep(0.2)  # Brief pause to show response
                    else:
                        # Live display was exited early, print AI response directly with proper spacing and Markdown
                        from rich.markdown import Markdown

                        formatted_response = format_llm_response(result)
                        # Extract content after symbol if present
                        if formatted_response.startswith(MessageSymbols.AI_RESPONSE):
                            content = formatted_response[len(MessageSymbols.AI_RESPONSE):].strip()
                        else:
                            content = result

                        # Print symbol and markdown
                        ai_symbol = f"[ai_symbol]{MessageSymbols.AI_RESPONSE}[/ai_symbol] "
                        console.print(f"\n{ai_symbol}", end="")
                        md = Markdown(content)
                        console.print(md)
                
                # Clear the Live display reference when we're done
                if unified_display and hasattr(unified_display.display_impl, 'set_live_display'):
                    unified_display.display_impl.set_live_display(None)

                # History display moved to before each LLM call in llm_integration.py

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

                # Clear the Live display reference when we're done (error case)
                if unified_display and hasattr(unified_display.display_impl, 'set_live_display'):
                    unified_display.display_impl.set_live_display(None)

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
                
                # Display conversation history AFTER query execution (Textual mode doesn't show history in console)
                # Textual mode handles its own history display
            
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


def _display_conversation_history(memory_manager, console: Console, show_full_history: bool = False) -> None:
    """Display conversation history panel for text mode when history is enabled."""
    from rich.panel import Panel
    from rich.text import Text
    
    # Build conversation history text showing actual LLM conversation structure
    conversation_text = Text()
    
    # 1. Show the system prompt that will be sent to LLM
    try:
        from sqlbot.llm_integration import build_system_prompt
        system_prompt = build_system_prompt()
        
        # Truncate system prompt for display readability (unless full history is requested)
        if show_full_history:
            system_prompt_display = system_prompt
        elif len(system_prompt) > 200:
            system_prompt_display = system_prompt[:200] + "... [TRUNCATED - Full system prompt sent to LLM]"
        else:
            system_prompt_display = system_prompt
            
        conversation_text.append("[1] SYSTEM MESSAGE:\n", style="bold yellow")
        conversation_text.append(f"{system_prompt_display}\n\n", style="dim white")
        
        message_count = 2
    except Exception as e:
        conversation_text.append("[1] SYSTEM MESSAGE:\n", style="bold yellow")
        conversation_text.append(f"[Error loading system prompt: {e}]\n\n", style="red")
        message_count = 2
    
    # 2. Show the chat history from global conversation_history (which contains tool calls)
    try:
        from sqlbot.llm_integration import conversation_history
        global_messages = conversation_history
    except ImportError:
        try:
            import llm_integration
            global_messages = llm_integration.conversation_history
        except ImportError:
            # Fallback to memory manager if we can't access global history
            global_messages = []
            messages = memory_manager.get_filtered_context()
            # Fallback to memory manager messages
    
    # Convert global conversation history to display format
    if global_messages:
        messages = []
        for msg in global_messages:
            # Create a simple object that mimics the memory manager message format
            class SimpleMessage:
                def __init__(self, msg_type, content):
                    self.type = msg_type
                    self.content = content
            
            if msg.get("role") == "user":
                messages.append(SimpleMessage("human", msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(SimpleMessage("ai", msg.get("content", "")))
    else:
        # Fallback to memory manager messages
        messages = memory_manager.get_filtered_context()
    
    if messages:
        for message in messages:
            if hasattr(message, 'type'):
                msg_type = message.type.upper()
                content = str(message.content)
                
                conversation_text.append(f"[{message_count}] {msg_type} MESSAGE:\n", style="bold white")
                
                # Parse and format tool calls if this is an AI message with query details
                if msg_type.upper() == "AI" and "--- Query Details ---" in content:
                    parts = content.split("--- Query Details ---")
                    if len(parts) == 2:
                        # Show the main response
                        main_response = parts[0].strip()
                        conversation_text.append(f"{main_response}\n\n", style="white")
                        
                        # Parse and show tool calls
                        tool_section = parts[1].strip()
                        tool_calls = tool_section.split("\n\nQuery:")
                        
                        for i, tool_call in enumerate(tool_calls):
                            if not tool_call.strip():
                                continue
                                
                            # Add "Query:" back for calls after the first
                            if i > 0:
                                tool_call = "Query:" + tool_call
                            
                            if "Result:" in tool_call:
                                query_part, result_part = tool_call.split("Result:", 1)
                                query_text = query_part.replace("Query:", "").strip()
                                result_text = result_part.strip()
                                
                                # Show tool call
                                conversation_text.append(f"  🔧 TOOL CALL:\n", style="bold cyan")
                                conversation_text.append(f"     {query_text}\n", style="cyan")
                                
                                # Show tool result
                                conversation_text.append(f"  📊 TOOL RESULT:\n", style="bold yellow")
                                conversation_text.append(f"     {result_text}\n", style="yellow")
                        
                        conversation_text.append("\n", style="white")
                    else:
                        # Fallback for malformed content
                        conversation_text.append(f"{content}\n\n", style="white")
                else:
                    # Regular message without tool calls
                    conversation_text.append(f"{content}\n\n", style="white")
                
                message_count += 1
    
    # If no messages yet, show placeholder
    if not messages:
        conversation_text.append(f"[{message_count}] CHAT HISTORY:\n", style="bold white")
        conversation_text.append("(No previous conversation)\n\n", style="dim white")
    
    # Display in a panel - always show it
    panel = Panel(
        conversation_text,
        title="🤖 Complete LLM Conversation Context (sent to GPT-5)",
        border_style="red",
        width=120
    )
    console.print(panel)



"""
Conversation Memory Management for SQLBot

This module handles conversation history management using LangChain's memory features.
All conversation history logic is centralized here and must be covered by BDD tests.
"""

from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.chat_history import BaseChatMessageHistory
from rich.console import Console
from rich.tree import Tree
from rich.text import Text
import logging

logger = logging.getLogger(__name__)

class SQLBotConversationHistory(BaseChatMessageHistory):
    """
    Custom conversation history implementation for SQLBot.
    
    Handles filtering, truncation, and formatting of conversation messages
    for optimal LLM performance and context management.
    """
    
    def __init__(self, max_messages: int = 20, max_content_length: int = 2000):
        """
        Initialize conversation history.
        
        Args:
            max_messages: Maximum number of messages to keep in history
            max_content_length: Maximum length of individual message content
        """
        self.messages: List[BaseMessage] = []
        self.max_messages = max_messages
        self.max_content_length = max_content_length
        
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history with filtering."""
        # Truncate content if too long
        if hasattr(message, 'content') and len(message.content) > self.max_content_length:
            truncated_content = message.content[:self.max_content_length - 50] + "\n\n[Message truncated for memory efficiency]"
            if isinstance(message, HumanMessage):
                message = HumanMessage(content=truncated_content)
            elif isinstance(message, AIMessage):
                message = AIMessage(content=truncated_content)
            elif isinstance(message, ToolMessage):
                message = ToolMessage(content=truncated_content, tool_call_id=message.tool_call_id)
        
        self.messages.append(message)
        
        # Keep only the most recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
    def clear(self) -> None:
        """Clear all conversation history."""
        self.messages.clear()
        
    def get_messages(self) -> List[BaseMessage]:
        """Get all messages in the conversation history."""
        return self.messages.copy()

class ConversationMemoryManager:
    """
    Manages conversation memory for SQLBot using LangChain's memory system.
    
    This class handles:
    - Converting SQLBot's internal conversation format to LangChain messages
    - Filtering and truncating messages for optimal LLM performance
    - Extracting tool results from assistant responses
    - Managing conversation context across multiple queries
    """
    
    def __init__(self, max_messages: int = 20, max_content_length: int = 2000):
        """
        Initialize the conversation memory manager.
        
        Args:
            max_messages: Maximum number of messages to keep in memory
            max_content_length: Maximum length of individual message content
        """
        self.history = SQLBotConversationHistory(max_messages, max_content_length)
        # Use the chat history directly instead of deprecated ConversationBufferWindowMemory
        self.max_messages = max_messages
        
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history."""
        message = HumanMessage(content=content)
        self.history.add_message(message)
        logger.debug(f"Added user message: {content[:100]}...")
        
    def add_assistant_message(self, content: str) -> None:
        """
        Add an assistant message to conversation history.
        
        Since tool extraction is disabled to avoid tool call ID conflicts,
        tool results are kept inline with the assistant message.
        """
        # Since tool extraction is disabled, keep the entire message intact
        ai_message = AIMessage(content=content)
        self.history.add_message(ai_message)
        logger.debug(f"Added assistant message: {content[:100]}...")
            
    def _extract_and_add_tool_results(self, tool_results_section: str) -> None:
        """
        Extract tool results from assistant response and add as ToolMessages.
        
        DISABLED: This was causing tool call ID mismatches that broke follow-up questions.
        The LLM agent handles tool calls internally, so we don't need to reconstruct them.
        """
        # DISABLED: Don't reconstruct tool messages to avoid tool call ID conflicts
        # The assistant response already contains the tool execution context
        # and the LLM can understand follow-up questions from the assistant message alone
        pass
                
    def get_conversation_context(self) -> List[BaseMessage]:
        """
        Get the current conversation context as LangChain messages.
        
        Returns:
            List of LangChain messages suitable for passing to an agent
        """
        messages = self.history.get_messages()
        logger.debug(f"Retrieved {len(messages)} messages from conversation history")
        return messages
        
    def display_conversation_tree(self, title: str = "Conversation History Sent to LLM") -> None:
        """
        Display the conversation history as a Rich tree for debugging.
        
        This shows exactly what context is being sent to the LLM at each step.
        """
        console = Console()
        
        messages = self.get_conversation_context()
        
        if not messages:
            console.print(f"📝 {title}: [dim]No conversation history[/dim]")
            return
            
        # Create the main tree
        tree = Tree(f"📝 {title} ({len(messages)} messages)")
        
        for i, message in enumerate(messages):
            # Determine message type and styling
            if isinstance(message, HumanMessage):
                msg_type = "👤 User"
                style = "blue"
            elif isinstance(message, AIMessage):
                msg_type = "🤖 Assistant"
                style = "green"
            elif isinstance(message, ToolMessage):
                msg_type = "🔧 Tool Result"
                style = "yellow"
            else:
                msg_type = f"❓ {type(message).__name__}"
                style = "dim"
                
            # Create message node
            content = message.content if hasattr(message, 'content') else str(message)
            
            # Truncate long content for display
            if len(content) > 200:
                display_content = content[:200] + "..."
            else:
                display_content = content
                
            # Replace newlines for better tree display
            display_content = display_content.replace('\n', ' ↵ ')
            
            message_node = tree.add(f"[{style}]{msg_type}[/{style}]")
            
            # Add content as child node
            content_text = Text(display_content, style="dim")
            message_node.add(content_text)
            
            # Add metadata for tool messages
            if isinstance(message, ToolMessage):
                if hasattr(message, 'tool_call_id'):
                    message_node.add(f"[dim]Tool Call ID: {message.tool_call_id}[/dim]")
                    
        console.print(tree)
        
    def display_filtered_context_tree(self) -> None:
        """Display the filtered conversation context that will be sent to the LLM."""
        console = Console()
        
        all_messages = self.history.get_messages()
        filtered_messages = self.get_filtered_context()
        
        tree = Tree(f"🔍 Filtered Context ({len(filtered_messages)}/{len(all_messages)} messages)")
        
        if not filtered_messages:
            tree.add("[dim]No messages pass the filter[/dim]")
        else:
            for i, message in enumerate(filtered_messages):
                # Same styling as display_conversation_tree
                if isinstance(message, HumanMessage):
                    msg_type = "👤 User"
                    style = "blue"
                elif isinstance(message, AIMessage):
                    msg_type = "🤖 Assistant"
                    style = "green"
                elif isinstance(message, ToolMessage):
                    msg_type = "🔧 Tool Result"
                    style = "yellow"
                else:
                    msg_type = f"❓ {type(message).__name__}"
                    style = "dim"
                    
                content = message.content if hasattr(message, 'content') else str(message)
                display_content = content[:150] + "..." if len(content) > 150 else content
                display_content = display_content.replace('\n', ' ↵ ')
                
                message_node = tree.add(f"[{style}]{msg_type}[/{style}]: {display_content}")
                
        console.print(tree)
        
    def clear_history(self) -> None:
        """Clear all conversation history."""
        self.history.clear()
        logger.debug("Cleared conversation history")
        
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for LangChain agent."""
        # Return the messages directly in the format expected by LangChain agents
        messages = self.get_conversation_context()
        return {"history": messages, "chat_history": messages}
        
    def should_include_message(self, message: BaseMessage) -> bool:
        """
        Determine if a message should be included in the conversation context.
        
        This method implements filtering logic for conversation history.
        Override this method to implement custom filtering rules.
        """
        # Skip empty messages
        if not hasattr(message, 'content') or not message.content.strip():
            return False
            
        # Skip overly long messages (they should be truncated by now)
        if len(message.content) > self.history.max_content_length * 2:
            return False
            
        # Include all other messages
        return True
        
    def get_filtered_context(self) -> List[BaseMessage]:
        """
        Get conversation context with filtering applied.
        
        Returns:
            Filtered list of messages for optimal LLM performance
        """
        all_messages = self.history.get_messages()
        filtered_messages = [msg for msg in all_messages if self.should_include_message(msg)]
        
        logger.debug(f"Filtered {len(all_messages)} messages down to {len(filtered_messages)}")
        return filtered_messages
        
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current conversation state.
        
        Returns:
            Dictionary with conversation statistics and recent messages
        """
        messages = self.history.get_messages()
        
        # Count message types
        user_messages = len([m for m in messages if isinstance(m, HumanMessage)])
        ai_messages = len([m for m in messages if isinstance(m, AIMessage)])
        tool_messages = len([m for m in messages if isinstance(m, ToolMessage)])
        
        # Get recent messages for preview
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        
        return {
            "total_messages": len(messages),
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "tool_messages": tool_messages,
            "recent_messages": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                }
                for msg in recent_messages
            ]
        }

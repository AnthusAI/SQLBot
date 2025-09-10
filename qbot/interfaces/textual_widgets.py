"""
Enhanced Textual widgets for QBot TUI interface

This module provides specialized widgets for the right-side panel of the QBot Textual interface,
including query result viewing and conversation history debugging.
"""

from typing import Optional, List, Dict, Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, ListView, ListItem, Label, RichLog
from textual.reactive import reactive
from textual.message import Message
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.json import JSON
import json

from qbot.core.query_result_list import QueryResultList, QueryResultEntry, get_query_result_list
from qbot.conversation_memory import ConversationMemoryManager


class QueryResultListItem(ListItem):
    """List item for displaying a query result entry"""
    
    def __init__(self, entry: QueryResultEntry, **kwargs):
        self.entry = entry
        
        # Create display text for the list item
        status_icon = "[OK]" if entry.result.success else "[FAIL]"
        
        # Handle timestamp (could be datetime object or ISO string)
        if hasattr(entry.timestamp, 'strftime'):
            timestamp = entry.timestamp.strftime("%H:%M:%S")
        else:
            # Parse ISO string and format
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime("%H:%M:%S")
            except:
                timestamp = str(entry.timestamp)[:8]  # Fallback
        
        row_info = f" • {entry.result.row_count} rows" if entry.result.row_count else ""
        
        display_text = f"#{entry.index} {status_icon} {timestamp}{row_info}"
        
        super().__init__(Label(display_text), **kwargs)


class QueryResultSidebar(ListView):
    """Sidebar showing list of query results"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_list: Optional[QueryResultList] = None
        self.selected_entry: Optional[QueryResultEntry] = None
    
    def set_result_list(self, result_list: QueryResultList) -> None:
        """Set the query result list to display"""
        self.result_list = result_list
        self.refresh_list()
    
    def refresh_list(self) -> None:
        """Refresh the list of query results"""
        if not self.result_list:
            return
        
        # Clear current items
        self.clear()
        
        # Add items in reverse order (newest first)
        entries = list(reversed(self.result_list.get_all_results()))
        
        for entry in entries:
            item = QueryResultListItem(entry)
            self.append(item)
        
        # Select the first item (most recent) if available
        if entries:
            self.index = 0
            self.selected_entry = entries[0]
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection of a query result"""
        if event.item and hasattr(event.item, 'entry'):
            self.selected_entry = event.item.entry
            # Post a message to notify parent widget
            self.post_message(QueryResultSelected(self.selected_entry))


class QueryResultSelected(Message):
    """Message sent when a query result is selected"""
    
    def __init__(self, entry: QueryResultEntry) -> None:
        self.entry = entry
        super().__init__()


class QueryResultContentView(ScrollableContainer):
    """Content view showing the selected query result as a Rich table"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_entry: Optional[QueryResultEntry] = None
        self.metadata_display = Static()
        self.table_display = Static()
    
    def compose(self) -> ComposeResult:
        """Compose the content view"""
        yield self.metadata_display
        yield self.table_display
    
    def show_entry(self, entry: QueryResultEntry) -> None:
        """Display a query result entry"""
        self.current_entry = entry
        
        if entry.result.success and entry.result.data:
            # Create Rich table from the data
            table = Table(title=f"Query Result #{entry.index}", show_header=True, header_style="bold magenta")
            
            # Add columns
            if entry.result.columns:
                for col in entry.result.columns:
                    table.add_column(str(col))
            
            # Add rows
            for row in entry.result.data:
                if entry.result.columns:
                    table.add_row(*[str(row.get(col, '')) for col in entry.result.columns])
            
            # Create panel with metadata
            # Handle timestamp formatting
            if hasattr(entry.timestamp, 'strftime'):
                formatted_time = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    formatted_time = str(entry.timestamp)
            
            metadata = (
                f"Query: {entry.query_text}\\n"
                f"Executed: {formatted_time}\\n"
                f"Execution time: {entry.result.execution_time:.3f}s\\n"
                f"Rows: {entry.result.row_count}"
            )
            
            # Update separate displays - Rich objects can be passed directly to Static.update()
            metadata_panel = Panel(metadata, title="[bold blue]Query Info[/bold blue]", border_style="blue")
            self.metadata_display.update(metadata_panel)
            self.table_display.update(table)
            
        else:
            # Show error or empty result
            if entry.result.error:
                error_text = f"Query Failed\\n\\n{entry.result.error}"
                error_panel = Panel(
                    error_text,
                    title=f"[bold red]Query Result #{entry.index} - Failed[/bold red]",
                    border_style="red"
                )
                self.metadata_display.update(error_panel)
                self.table_display.update("")
            else:
                empty_panel = Panel(
                    "No data returned",
                    title=f"[bold yellow]Query Result #{entry.index} - Empty[/bold yellow]",
                    border_style="yellow"
                )
                self.metadata_display.update(empty_panel)
                self.table_display.update("")
    
    def show_empty(self) -> None:
        """Show empty state"""
        empty_panel = Panel(
            "No query results yet.\\n\\nExecute a query to see results here.",
            title="[bold cyan]Query Results[/bold cyan]",
            border_style="cyan"
        )
        self.metadata_display.update(empty_panel)
        self.table_display.update("")


class QueryResultViewer(Horizontal):
    """Complete query result viewer with sidebar and content"""
    
    def __init__(self, session_id: str, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.sidebar = QueryResultSidebar()
        self.content_view = QueryResultContentView()
        self.result_list: Optional[QueryResultList] = None
    
    def compose(self) -> ComposeResult:
        """Compose the query result viewer"""
        # Sidebar takes 1/3, content takes 2/3
        self.sidebar.styles.width = "1fr"
        self.content_view.styles.width = "2fr"
        
        yield self.sidebar
        yield self.content_view
    
    def on_mount(self) -> None:
        """Initialize the viewer when mounted"""
        self.result_list = get_query_result_list(self.session_id)
        self.sidebar.set_result_list(self.result_list)
        
        latest = self.result_list.get_latest_result()
        if latest:
            # Show the latest result
            self.content_view.show_entry(latest)
        else:
            self.content_view.show_empty()
    
    def on_query_result_selected(self, event: QueryResultSelected) -> None:
        """Handle query result selection"""
        self.content_view.show_entry(event.entry)
    
    def refresh_data(self) -> None:
        """Refresh the data (call when new query results are added)"""
        if self.result_list:
            self.sidebar.refresh_list()
            
            # If this is a new result, show it
            latest = self.result_list.get_latest_result()
            if latest and (not self.content_view.current_entry or 
                          latest.index > self.content_view.current_entry.index):
                self.content_view.show_entry(latest)
                # Select the latest in sidebar
                self.sidebar.index = 0


class ConversationDebugViewer(ScrollableContainer):
    """Debug viewer showing raw LLM conversation history"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_log = RichLog(highlight=True, markup=True, wrap=True, min_width=1)
        self.conversation_log.styles.text_wrap = "wrap"
        self.memory_manager: Optional[ConversationMemoryManager] = None
    
    def compose(self) -> ComposeResult:
        """Compose the debug viewer"""
        yield self.conversation_log
    
    def set_memory_manager(self, memory_manager: ConversationMemoryManager) -> None:
        """Set the conversation memory manager"""
        self.memory_manager = memory_manager
        self.refresh_conversation()
    
    def refresh_conversation(self) -> None:
        """Refresh the conversation display"""
        if not self.memory_manager:
            return
        
        self.conversation_log.clear()
        
        # Add header
        header_panel = Panel(
            "Raw LLM Conversation History\\n\\n"
            "This shows the actual conversation data sent to the LLM,\\n"
            "including query result placeholders and JSON data.",
            title="[bold yellow]Debug View[/bold yellow]",
            border_style="yellow"
        )
        self.conversation_log.write(header_panel)
        
        # Get filtered context (what actually goes to LLM)
        try:
            messages = self.memory_manager.get_filtered_context()
            
            for i, message in enumerate(messages):
                msg_type = type(message).__name__.replace('Message', '').upper()
                
                # Color code by message type
                if 'Human' in type(message).__name__:
                    style = "bold blue"
                    icon = "👤"
                elif 'AI' in type(message).__name__:
                    style = "bold green"
                    icon = "🤖"
                elif 'Tool' in type(message).__name__:
                    style = "bold yellow"
                    icon = "🔧"
                else:
                    style = "bold white"
                    icon = "💬"
                
                # Add message header
                self.conversation_log.write(f"\\n[{style}]{icon} {msg_type} MESSAGE #{i+1}[/{style}]")
                
                # Add message content
                content = str(message.content)
                
                # Try to format JSON content nicely
                if content.strip().startswith('{') and content.strip().endswith('}'):
                    try:
                        json_data = json.loads(content)
                        formatted_json = JSON.from_data(json_data)
                        self.conversation_log.write(formatted_json)
                    except:
                        # Not valid JSON, show as text
                        self.conversation_log.write(Panel(content, border_style="dim"))
                else:
                    # Regular text content
                    self.conversation_log.write(Panel(content, border_style="dim"))
        
        except Exception as e:
            self.conversation_log.write(f"[red]Error loading conversation: {e}[/red]")


class EnhancedDetailViewWidget(Static):
    """Enhanced detail view widget that can switch between different views"""
    
    # Reactive property to track current view mode
    view_mode: reactive[str] = reactive("query_results")
    
    def __init__(self, session_id: str, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.query_result_viewer: Optional[QueryResultViewer] = None
        self.conversation_debug_viewer: Optional[ConversationDebugViewer] = None
        self.memory_manager: Optional[ConversationMemoryManager] = None
        
    
    def compose(self) -> ComposeResult:
        """Compose the enhanced detail view"""
        # Create both viewers
        self.query_result_viewer = QueryResultViewer(self.session_id)
        self.conversation_debug_viewer = ConversationDebugViewer()
        
        # Start with query results view
        yield self.query_result_viewer
    
    def set_memory_manager(self, memory_manager: ConversationMemoryManager) -> None:
        """Set the conversation memory manager for debug view"""
        self.memory_manager = memory_manager
        if self.conversation_debug_viewer:
            self.conversation_debug_viewer.set_memory_manager(memory_manager)
    
    def switch_to_query_results(self) -> None:
        """Switch to query results view"""
        if self.view_mode != "query_results":
            self.view_mode = "query_results"
            self.refresh_view()
    
    def switch_to_conversation_debug(self) -> None:
        """Switch to conversation debug view"""
        if self.view_mode != "conversation_debug":
            self.view_mode = "conversation_debug"
            self.refresh_view()
    
    def refresh_view(self) -> None:
        """Refresh the current view"""
        # Remove all children
        for child in list(self.children):
            child.remove()
        
        # Add the appropriate view
        if self.view_mode == "query_results":
            if self.query_result_viewer:
                self.mount(self.query_result_viewer)
        elif self.view_mode == "conversation_debug":
            if self.conversation_debug_viewer:
                self.mount(self.conversation_debug_viewer)
                self.conversation_debug_viewer.refresh_conversation()
    
    def on_new_query_result(self) -> None:
        """Called when a new query result is added"""
        if self.view_mode == "query_results" and self.query_result_viewer:
            self.query_result_viewer.refresh_data()
    
    def on_conversation_updated(self) -> None:
        """Called when conversation is updated"""
        if self.view_mode == "conversation_debug" and self.conversation_debug_viewer:
            self.conversation_debug_viewer.refresh_conversation()

"""
Enhanced Textual widgets for SQLBot TUI interface

This module provides specialized widgets for the right-side panel of the SQLBot Textual interface,
including query result viewing and conversation history debugging.
"""

from typing import Optional, List, Dict, Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, ListView, ListItem, Label, RichLog, TabbedContent, TabPane, DataTable
from textual.reactive import reactive
from textual.message import Message
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.json import JSON
import json

from sqlbot.core.query_result_list import QueryResultList, QueryResultEntry, get_query_result_list
from sqlbot.conversation_memory import ConversationMemoryManager


class QueryResultListItem(ListItem):
    """List item for displaying a query result entry"""
    
    def __init__(self, entry: QueryResultEntry, **kwargs):
        self.entry = entry
        
        # Handle timestamp (could be datetime object or ISO string)  
        if hasattr(entry.timestamp, 'strftime'):
            # Format as "Tue 3:32 PM"
            day_time = entry.timestamp.strftime('%a %-I:%M %p')
        else:
            # Parse ISO string and format
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                day_time = dt.strftime('%a %-I:%M %p')
            except:
                day_time = str(entry.timestamp)[:16]  # Fallback
        
        # Handle row count with proper pluralization
        if entry.result.row_count is not None and entry.result.row_count > 0:
            row_word = "row" if entry.result.row_count == 1 else "rows"
            row_info = f" - {entry.result.row_count} {row_word}"
        else:
            row_info = ""
        
        # Create friendly display text: "Tue 3:32 PM - 1 row" or "Mon 1:45 PM - 7 rows"
        display_text = f"{day_time}{row_info}"
        
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
        # For initial setup, we need to populate the entire list
        self._initial_populate()
    
    def _initial_populate(self) -> None:
        """Initial population of the ListView"""
        if not self.result_list:
            return
        
        # Clear any existing items
        self.clear()
        
        # Add all results in reverse order (newest first), limited to 100
        entries = list(reversed(self.result_list.get_all_results()))[:100]
        for entry in entries:
            item = QueryResultListItem(entry)
            self.append(item)
    
    def refresh_list(self) -> None:
        """Refresh the list of query results"""
        if not self.result_list:
            return
        
        # Get current number of items in ListView
        current_count = len(self)
        # Get total number of results
        all_results = self.result_list.get_all_results()
        
        # If we have new results, insert them at the beginning (newest first)
        if len(all_results) > current_count:
            # Get only the new results
            new_results = all_results[current_count:]
            # Insert new results in reverse order at the beginning
            for i, entry in enumerate(reversed(new_results)):
                item = QueryResultListItem(entry)
                self.insert(i, [item])
            
            # Trim to 100 items maximum if we exceed the limit
            if len(self) > 100:
                # Instead of using pop() which can cause CSS query stalls,
                # rebuild the list with only the first 100 items
                items_to_keep = []
                for i in range(min(100, len(self))):
                    items_to_keep.append(self[i])
                
                # Clear and rebuild
                self.clear()
                for item in items_to_keep:
                    self.append(item)
    
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


class QueryResultContentView(Static):
    """Content view showing the selected query result with tabbed interface"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_entry: Optional[QueryResultEntry] = None
        self.tabbed_content: Optional[TabbedContent] = None
        self.data_table: Optional[DataTable] = None
        self.info_tab_content: Optional[Static] = None
    
    def compose(self) -> ComposeResult:
        """Compose the tabbed content view"""
        with TabbedContent("Result", "Query") as self.tabbed_content:
            with TabPane("Result", id="data_tab"):
                self.data_table = DataTable(zebra_stripes=True, show_header=True)
                yield self.data_table
            with TabPane("Query", id="info_tab"):
                self.info_tab_content = Static()
                yield self.info_tab_content
    
    def show_entry(self, entry: QueryResultEntry) -> None:
        """Display a query result entry in both tabs"""
        self.current_entry = entry
        
        # Format timestamp for display instead of using index
        if hasattr(entry.timestamp, 'strftime'):
            time_str = entry.timestamp.strftime('%a %-I:%M %p')
        else:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%a %-I:%M %p')
            except:
                time_str = "Unknown time"
        
        if entry.result.success and entry.result.data:
            # DATA TAB: Populate DataTable with the data
            if self.data_table:
                # Clear existing data AND columns
                self.data_table.clear(columns=True)
                
                # Add columns
                if entry.result.columns:
                    self.data_table.add_columns(*entry.result.columns)
                
                # Add rows
                if entry.result.data:
                    rows_to_add = []
                    for row in entry.result.data:
                        if entry.result.columns:
                            # Extract values in the same order as columns
                            row_values = [str(row.get(col, '')) for col in entry.result.columns]
                            rows_to_add.append(row_values)
                    
                    if rows_to_add:
                        self.data_table.add_rows(rows_to_add)
            
            # QUERY TAB: Show just the query text
            if self.info_tab_content:
                self.info_tab_content.update(entry.query_text)
            
        else:
            # Show error or empty result
            if self.data_table:
                # Clear the data table AND columns for error/empty states
                self.data_table.clear(columns=True)
            
            # QUERY TAB: Show just the query text (even for errors/empty results)
            if self.info_tab_content:
                self.info_tab_content.update(entry.query_text)
    
    def show_empty(self) -> None:
        """Show empty state in both tabs"""
        # Clear the data table AND columns
        if self.data_table:
            self.data_table.clear(columns=True)
        
        # Show empty state in query tab
        if self.info_tab_content:
            self.info_tab_content.update("No query results yet.\\n\\nExecute a query to see results here.")


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
        # Sidebar takes ~1/4.5, content takes ~3.5/4.5 (just slightly wider than 1:4)
        self.sidebar.styles.width = "2fr"
        self.content_view.styles.width = "7fr"
        
        yield self.sidebar
        yield self.content_view
    
    def on_mount(self) -> None:
        """Initialize the viewer when mounted"""
        self.result_list = get_query_result_list(self.session_id)
        self.sidebar.set_result_list(self.result_list)
        
        latest = self.result_list.get_latest_result()
        if latest:
            # Show the latest result in content view
            self.content_view.show_entry(latest)
            
            # Select the latest result in sidebar (first item)
            def _select_latest():
                if len(self.sidebar) > 0:
                    # Force selection change to ensure visual highlighting
                    current_index = self.sidebar.index
                    if current_index == 0:
                        # If already at 0, temporarily move away to force change
                        self.sidebar.index = 1 if len(self.sidebar) > 1 else -1
                    
                    # Set to first item (latest result)
                    self.sidebar.index = 0
                    self.sidebar.selected_entry = latest
            
            # Use call_after_refresh to ensure ListView is fully rendered
            self.call_after_refresh(_select_latest)
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
                
                # Set selection after ListView is fully refreshed
                def _set_selection():
                    if len(self.sidebar) > 0:
                        # Force selection change by first clearing, then setting to 0
                        # This ensures the visual selection updates properly
                        current_index = self.sidebar.index
                        if current_index == 0:
                            # If already at 0, temporarily move away to force change
                            self.sidebar.index = 1 if len(self.sidebar) > 1 else -1
                        
                        # Now set to 0 (newest item should be here after insert)
                        self.sidebar.index = 0
                        # Store the selected entry for our logic (should be the newest)
                        self.sidebar.selected_entry = latest
                        # Verify that the item at index 0 is actually the latest result
                        if len(self.sidebar) > 0 and hasattr(self.sidebar.children[0], 'entry'):
                            first_item_entry = self.sidebar.children[0].entry
                            if first_item_entry.index == latest.index:
                                # Confirmed: index 0 has the latest result
                                self.content_view.show_entry(latest)
                            else:
                                # Mismatch: find the correct index for the latest result
                                for idx, child in enumerate(self.sidebar.children):
                                    if hasattr(child, 'entry') and child.entry.index == latest.index:
                                        self.sidebar.index = idx
                                        self.content_view.show_entry(latest)
                                        break
                
                self.call_after_refresh(_set_selection)


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

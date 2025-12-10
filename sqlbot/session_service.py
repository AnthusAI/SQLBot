"""
Session service for SQLBot web interface.

Wraps existing REPL logic and provides SSE event broadcasting for real-time updates.
Modeled after DeckBot's SessionService pattern.
"""

import os
import json
import threading
import uuid
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime
from pathlib import Path


class SessionService:
    """Manages a SQLBot session with event broadcasting for web interface."""

    def __init__(self, session_context: Dict[str, Any]):
        """
        Initialize session service.

        Args:
            session_context: Dictionary with session configuration:
                - session_id: Unique session identifier
                - session_name: Display name for session
                - profile: dbt profile name
                - safeguard_mode: Enable/disable safeguards
                - preview_mode: Enable/disable preview mode
        """
        self.context = session_context
        self.session_id = session_context['session_id']
        self.session_name = session_context['session_name']
        self.profile = session_context.get('profile')

        # Conversation memory manager
        from sqlbot.conversation_memory import ConversationMemoryManager
        self.conversation_manager = ConversationMemoryManager()

        # Query history for this session
        self.queries: List[Dict[str, Any]] = []

        # Event listeners for SSE
        self.listeners: List[Callable[[str, Any], None]] = []
        self._lock = threading.Lock()

        # Session storage path
        self.sessions_dir = Path.home() / '.sqlbot_sessions'
        self.sessions_dir.mkdir(exist_ok=True)
        self.session_file = self.sessions_dir / f"{self.session_id}.json"

    def subscribe(self, callback: Callable[[str, Any], None]):
        """
        Subscribe to events. Callback receives (event_type, data).

        Args:
            callback: Function to call with (event_type, data)
        """
        with self._lock:
            self.listeners.append(callback)

    def _notify(self, event_type: str, data: Any = None):
        """
        Notify all listeners of an event.

        Args:
            event_type: Type of event (e.g., 'message', 'query_complete')
            data: Event data
        """
        # If this is a system message event, also save it to conversation history
        if event_type == "message" and data and data.get("role") == "system":
            import sys
            print(f"[SessionService._notify] Saving system message to history: {data.get('content', '')[:100]}", file=sys.stderr)
            from langchain_core.messages import SystemMessage
            self.conversation_manager.history.add_message(
                SystemMessage(content=data.get("content", ""))
            )
            print(f"[SessionService._notify] History now has {len(self.conversation_manager.history.get_messages())} messages", file=sys.stderr)

        with self._lock:
            for listener in self.listeners:
                try:
                    listener(event_type, data)
                except Exception as e:
                    print(f"Error in listener: {e}")

    def execute_query(self, user_input: str):
        """
        Execute a query (SQL, natural language, or slash command).

        This runs in a background thread and sends SSE events as it progresses.

        Args:
            user_input: The user's query text
        """
        def _execute():
            query_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Emit user message event
            self._notify("message", {
                "role": "user",
                "content": user_input
            })

            # Add to conversation memory
            self.conversation_manager.add_user_message(user_input)

            # Determine query type
            from sqlbot.repl import is_sql_query
            is_sql = is_sql_query(user_input)
            is_slash = user_input.strip().startswith('/')

            query_record = {
                "id": query_id,
                "timestamp": timestamp,
                "user_input": user_input,
                "query_type": "slash" if is_slash else ("sql" if is_sql else "natural_language"),
                "generated_sql": None,
                "results": None,
                "execution_time": None,
                "error": None
            }

            # Emit query started event
            self._notify("query_started", {"query_id": query_id})

            try:
                import time
                start_time = time.time()

                if is_slash:
                    # Handle slash command
                    from sqlbot.repl import handle_slash_command
                    result = handle_slash_command(user_input)
                    query_record["results"] = {"output": result}

                elif is_sql:
                    # Direct SQL query
                    self._notify("tool_start", {
                        "tool_name": "execute_sql",
                        "sql": user_input.strip()
                    })

                    from sqlbot.repl import execute_safe_sql
                    result = execute_safe_sql(user_input.strip())

                    query_record["generated_sql"] = user_input.strip()
                    query_record["results"] = self._parse_sql_result(result)

                    self._notify("tool_end", {
                        "tool_name": "execute_sql",
                        "result": "success" if result else "error"
                    })

                else:
                    # Natural language query - use LLM
                    self._notify("thinking_start")

                    from sqlbot.llm_integration import handle_llm_query, set_session_id
                    import sys

                    # Set session ID for query result tracking
                    set_session_id(self.session_id)

                    print(f"[SessionService] Calling handle_llm_query with: {user_input}", file=sys.stderr)
                    # Pass conversation history from this session's conversation manager
                    chat_history = self.conversation_manager.get_filtered_context()
                    # Convert session's safeguard_mode to dangerous_mode (opposite meaning)
                    safeguard_mode = self.context.get('safeguard_mode', True)
                    dangerous_mode = not safeguard_mode
                    print(f"[SessionService] Session config: safeguard_mode={safeguard_mode}, passing dangerous_mode={dangerous_mode}", file=sys.stderr)
                    result = handle_llm_query(user_input, event_notifier=self._notify, chat_history=chat_history, dangerous_mode=dangerous_mode)
                    print(f"[SessionService] Got result type: {type(result)}, length: {len(result) if result else 0}", file=sys.stderr)
                    print(f"[SessionService] Result preview: {str(result)[:200]}", file=sys.stderr)

                    self._notify("thinking_end")

                    # Parse LLM response for generated SQL
                    query_record["results"] = {"output": result}

                    # Try to extract SQL from result if present
                    # The LLM response may include executed SQL and results
                    # This is a simplified extraction - may need refinement
                    if "```sql" in result:
                        import re
                        sql_match = re.search(r'```sql\n(.*?)\n```', result, re.DOTALL)
                        if sql_match:
                            query_record["generated_sql"] = sql_match.group(1).strip()

                execution_time = time.time() - start_time
                query_record["execution_time"] = execution_time

                # Emit AI response
                import sys
                print(f"[SessionService] Emitting message event with content length: {len(str(result))}", file=sys.stderr)
                self._notify("message", {
                    "role": "assistant",
                    "content": str(result)
                })
                print(f"[SessionService] Message event emitted", file=sys.stderr)

                # Add to conversation memory
                self.conversation_manager.add_assistant_message(str(result))

            except Exception as e:
                query_record["error"] = str(e)
                self._notify("error", {
                    "message": str(e),
                    "query_id": query_id
                })

                # Emit error message
                self._notify("message", {
                    "role": "system",
                    "content": f"Error: {str(e)}"
                })

            # Store query in history
            self.queries.append(query_record)

            # Emit query complete event
            self._notify("query_complete", query_record)

            # Auto-save session after each query
            self.save_session()

        # Run in background thread
        threading.Thread(target=_execute, daemon=True).start()

    def _parse_sql_result(self, result_text: str) -> Dict[str, Any]:
        """
        Parse SQL result text into structured format.

        Args:
            result_text: Text output from execute_safe_sql

        Returns:
            Dictionary with columns and rows, or raw output
        """
        if not result_text:
            return {"output": "No results"}

        # Try to parse table format
        # Result format from repl.py:
        # | col1 | col2 |
        # | ---- | ---- |
        # | val1 | val2 |
        lines = result_text.strip().split('\n')

        if len(lines) >= 3 and lines[0].startswith('|'):
            # Looks like table format
            try:
                # Parse header
                header_line = lines[0].strip()
                columns = [col.strip() for col in header_line.split('|')[1:-1]]

                # Parse data rows (skip header and separator)
                rows = []
                for line in lines[2:]:
                    if line.strip().startswith('|'):
                        values = [val.strip() for val in line.split('|')[1:-1]]
                        rows.append(values)

                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows)
                }
            except Exception:
                # Parsing failed, return raw output
                pass

        # Return raw output if not table format
        return {"output": result_text}

    def get_queries(self) -> List[Dict[str, Any]]:
        """Get all queries executed in this session."""
        return self.queries

    def get_conversation_history(self) -> Dict[str, Any]:
        """Get conversation history from memory manager."""
        return {
            "messages": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content
                }
                for msg in self.conversation_manager.history.get_messages()
            ],
            "total_messages": len(self.conversation_manager.history.get_messages())
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current session state."""
        return {
            "session": self.context,
            "query_count": len(self.queries),
            "conversation_summary": self.conversation_manager.get_summary()
        }

    def save_session(self):
        """Save session to disk."""
        session_data = {
            'session_id': self.session_id,
            'name': self.session_name,
            'created': self.context.get('created'),
            'modified': datetime.utcnow().isoformat() + 'Z',
            'queries': self.queries,
            'conversation_history': self.get_conversation_history(),
            'config': {
                'safeguard_mode': self.context.get('safeguard_mode', True),
                'preview_mode': self.context.get('preview_mode', False),
                'profile': self.profile
            }
        }

        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

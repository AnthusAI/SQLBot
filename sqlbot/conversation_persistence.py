"""
Conversation Persistence for SQLBot

Handles saving and loading conversation history to/from disk to enable
resuming conversations across sessions.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationPersistence:
    """Manages persistence of conversation history to disk."""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize conversation persistence manager.

        Args:
            storage_dir: Directory to store conversations (defaults to ~/.sqlbot_conversations)
        """
        if storage_dir is None:
            storage_dir = os.path.join(os.path.expanduser("~"), ".sqlbot_conversations")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Current session file
        self.current_session_file = self.storage_dir / "current_session.json"

        # Archive directory for old sessions
        self.archive_dir = self.storage_dir / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def save_conversation(self, conversation_history: List[Dict], session_id: Optional[str] = None) -> str:
        """
        Save conversation history to disk.

        Args:
            conversation_history: List of message dicts with 'role' and 'content'
            session_id: Optional session identifier

        Returns:
            Session ID (timestamp if not provided)
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "messages": conversation_history,
            "message_count": len(conversation_history)
        }

        try:
            # Save as current session (always overwrite)
            with open(self.current_session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved conversation session {session_id} with {len(conversation_history)} messages")
            return session_id

        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise

    def load_current_conversation(self) -> Optional[List[Dict]]:
        """
        Load the most recent conversation from disk.

        Returns:
            List of message dicts or None if no conversation exists
        """
        if not self.current_session_file.exists():
            logger.debug("No current session file found")
            return None

        try:
            with open(self.current_session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            messages = session_data.get("messages", [])
            session_id = session_data.get("session_id", "unknown")
            timestamp = session_data.get("timestamp", "unknown")

            logger.info(f"Loaded conversation session {session_id} from {timestamp} with {len(messages)} messages")
            return messages

        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return None

    def archive_current_conversation(self) -> Optional[str]:
        """
        Archive the current conversation to the archive directory.

        Returns:
            Path to archived file or None if no current session
        """
        if not self.current_session_file.exists():
            return None

        try:
            # Load current session data
            with open(self.current_session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            session_id = session_data.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))

            # Save to archive
            archive_file = self.archive_dir / f"session_{session_id}.json"
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Archived conversation session {session_id} to {archive_file}")
            return str(archive_file)

        except Exception as e:
            logger.error(f"Failed to archive conversation: {e}")
            return None

    def clear_current_conversation(self):
        """Clear the current conversation file."""
        if self.current_session_file.exists():
            try:
                self.current_session_file.unlink()
                logger.info("Cleared current conversation session")
            except Exception as e:
                logger.error(f"Failed to clear current conversation: {e}")

    def list_archived_sessions(self) -> List[Dict]:
        """
        List all archived conversation sessions.

        Returns:
            List of dicts with session info (session_id, timestamp, message_count)
        """
        sessions = []

        try:
            for session_file in sorted(self.archive_dir.glob("session_*.json"), reverse=True):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)

                    sessions.append({
                        "session_id": session_data.get("session_id", "unknown"),
                        "timestamp": session_data.get("timestamp", "unknown"),
                        "message_count": session_data.get("message_count", 0),
                        "file_path": str(session_file)
                    })
                except Exception as e:
                    logger.warning(f"Failed to read session file {session_file}: {e}")
                    continue

            return sessions

        except Exception as e:
            logger.error(f"Failed to list archived sessions: {e}")
            return []

    def load_archived_session(self, session_id: str) -> Optional[List[Dict]]:
        """
        Load a specific archived conversation session.

        Args:
            session_id: Session identifier

        Returns:
            List of message dicts or None if session not found
        """
        session_file = self.archive_dir / f"session_{session_id}.json"

        if not session_file.exists():
            logger.warning(f"Session {session_id} not found")
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            messages = session_data.get("messages", [])
            logger.info(f"Loaded archived session {session_id} with {len(messages)} messages")
            return messages

        except Exception as e:
            logger.error(f"Failed to load archived session {session_id}: {e}")
            return None


# Global persistence manager instance
_persistence_manager = None


def get_persistence_manager() -> ConversationPersistence:
    """Get the global conversation persistence manager."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = ConversationPersistence()
    return _persistence_manager


def save_conversation_history(conversation_history: List[Dict]):
    """
    Save the current conversation history to disk.

    Args:
        conversation_history: List of message dicts to save
    """
    manager = get_persistence_manager()
    manager.save_conversation(conversation_history)


def load_conversation_history() -> Optional[List[Dict]]:
    """
    Load the most recent conversation history from disk.

    Returns:
        List of message dicts or None if no saved conversation
    """
    manager = get_persistence_manager()
    return manager.load_current_conversation()

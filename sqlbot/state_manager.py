"""
Application state management for SQLBot.

Stores application state (current session, etc.) in a YAML dotfile (.sqlbot_state.yaml) in the user's home directory.
Separated from user preferences to keep configuration and state distinct.
"""

import os
import yaml
from typing import Any, Optional
from pathlib import Path


class StateManager:
    """Manages application state stored in YAML format."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            config_path: Path to state file. Defaults to ~/.sqlbot_state.yaml
        """
        if config_path:
            self.config_path = config_path
        else:
            # Default to user's home directory
            home_dir = Path.home()
            self.config_path = os.path.join(home_dir, '.sqlbot_state.yaml')

        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Create state file with defaults if it doesn't exist."""
        if not os.path.exists(self.config_path):
            defaults = {
                'current_session': None
            }
            self._write_config(defaults)

    def _read_config(self) -> dict:
        """Read the state file."""
        try:
            if not os.path.exists(self.config_path):
                return {}
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except Exception as e:
            print(f"Error reading state: {e}")
            return {}

    def _write_config(self, config: dict):
        """Write the state file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Error writing state: {e}")

    def get_current_session(self) -> Optional[str]:
        """
        Get the ID of the currently active session.

        Returns:
            Session ID or None if none is active
        """
        config = self._read_config()
        return config.get('current_session')

    def set_current_session(self, session_id: str):
        """
        Set the currently active session.

        Args:
            session_id: ID of the session
        """
        config = self._read_config()
        config['current_session'] = session_id
        self._write_config(config)

    def clear_current_session(self):
        """Clear the currently active session state."""
        config = self._read_config()
        if 'current_session' in config:
            del config['current_session']
            self._write_config(config)

    def get_all(self) -> dict:
        """Get all state."""
        return self._read_config()

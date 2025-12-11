"""Utility functions for SQLBot."""

from pathlib import Path


def debug_log(message):
    """Write a debug message to the SQLBot debug log file.

    Args:
        message: The message to log (will be converted to string)
    """
    try:
        log_path = Path.home() / '.sqlbot' / 'debug.log'
        # Ensure directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(f"{message}\n")
    except (OSError, IOError):
        # Silently ignore logging errors - debug logging is optional
        pass


def get_sqlbot_dir():
    """Get the SQLBot data directory path.

    Returns:
        Path: Path to ~/.sqlbot directory
    """
    sqlbot_dir = Path.home() / '.sqlbot'
    sqlbot_dir.mkdir(parents=True, exist_ok=True)
    return sqlbot_dir

"""
SQLBot file locations management

Handles standard locations for configuration files, themes, and data storage.
"""

from pathlib import Path
import os


def qbot_directory() -> Path:
    """Return (possibly creating) the main SQLBot directory"""
    qbot_dir = Path.home() / ".qbot"
    qbot_dir.mkdir(exist_ok=True, parents=True)
    return qbot_dir


def config_directory() -> Path:
    """Return (possibly creating) the SQLBot config directory"""
    return qbot_directory()


def data_directory() -> Path:
    """Return (possibly creating) the SQLBot data directory"""
    return qbot_directory()


def config_file() -> Path:
    """Return the path to the main config file"""
    return config_directory() / "config.toml"


def theme_directory() -> Path:
    """Return (possibly creating) the themes directory"""
    theme_dir = qbot_directory() / "themes"
    theme_dir.mkdir(exist_ok=True, parents=True)
    return theme_dir


def user_theme_file(theme_name: str) -> Path:
    """Return the path to a specific user theme file"""
    return theme_directory() / f"{theme_name}.yaml"
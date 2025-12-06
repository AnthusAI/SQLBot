"""
File Security Validator - Ensures all file operations are sandboxed to profile directories.

This module provides security validation for file paths to prevent directory traversal
attacks and ensure all file operations stay within the current DBT profile's directories.
"""

import os
import re
from pathlib import Path
from typing import Optional


class FileSecurityValidator:
    """Validates file paths are within allowed profile directories."""

    def __init__(self, profile_name: str):
        """
        Initialize the validator for a specific profile.

        Args:
            profile_name: The name of the DBT profile to validate against
        """
        self.profile_name = profile_name

        # Define allowed base paths for this profile
        self.allowed_base_paths = [
            Path(f'.sqlbot/profiles/{profile_name}').resolve(),
            Path(f'profiles/{profile_name}').resolve()
        ]

    def validate_schema_path(self) -> Path:
        """
        Return validated schema.yml path in profile's models directory.

        Returns:
            Path: Absolute path to schema.yml file

        Raises:
            ValueError: If no valid profile directory exists
        """
        # Try to find existing schema.yml in profile directories
        for base_path in self.allowed_base_paths:
            models_dir = base_path / 'models'
            schema_path = models_dir / 'schema.yml'

            if schema_path.exists():
                # Verify the path is safe before returning
                if self.is_path_safe(schema_path):
                    return schema_path

        # No existing schema.yml found, return path where it should be created
        # Prefer .sqlbot/profiles/{profile}/models/schema.yml
        default_base = self.allowed_base_paths[0]
        models_dir = default_base / 'models'
        schema_path = models_dir / 'schema.yml'

        # Verify the path would be safe
        if not self.is_path_safe(schema_path):
            raise ValueError(f"Schema path outside allowed directories: {schema_path}")

        return schema_path

    def validate_macro_path(self, filename: str) -> Path:
        """
        Validate macro filename and return safe path.

        Args:
            filename: The macro filename (e.g., 'my_macro.sql')

        Returns:
            Path: Absolute path to the macro file

        Raises:
            ValueError: If filename is invalid or path is unsafe
        """
        # Sanitize filename - only allow alphanumeric, underscore, and .sql extension
        if not re.match(r'^[a-zA-Z0-9_]+\.sql$', filename):
            raise ValueError(
                f"Invalid macro filename: {filename}. "
                "Must contain only alphanumeric characters and underscores, "
                "and end with .sql"
            )

        # Block directory traversal attempts
        if '/' in filename or '\\' in filename or '..' in filename:
            raise ValueError(f"Directory traversal detected in filename: {filename}")

        # Try to find existing macro in profile directories
        for base_path in self.allowed_base_paths:
            macros_dir = base_path / 'macros'
            macro_path = macros_dir / filename

            if macro_path.exists():
                # Verify the path is safe before returning
                if self.is_path_safe(macro_path):
                    return macro_path

        # No existing macro found, return path where it should be created
        # Prefer .sqlbot/profiles/{profile}/macros/
        default_base = self.allowed_base_paths[0]
        macros_dir = default_base / 'macros'
        macro_path = macros_dir / filename

        # Verify the path would be safe
        if not self.is_path_safe(macro_path):
            raise ValueError(f"Macro path outside allowed directories: {macro_path}")

        return macro_path

    def list_macro_files(self) -> list[Path]:
        """
        List all macro files in the profile's macros directories.

        Returns:
            List of Path objects for all .sql files in macros directories
        """
        macro_files = []

        for base_path in self.allowed_base_paths:
            macros_dir = base_path / 'macros'

            if not macros_dir.exists():
                continue

            # Find all .sql files
            for file_path in macros_dir.glob('*.sql'):
                if file_path.is_file() and self.is_path_safe(file_path):
                    macro_files.append(file_path)

        # Remove duplicates (same file might exist in multiple paths)
        seen = set()
        unique_files = []
        for path in macro_files:
            if path.name not in seen:
                seen.add(path.name)
                unique_files.append(path)

        return unique_files

    def is_path_safe(self, path: Path) -> bool:
        """
        Check if resolved path is within allowed base paths.

        Args:
            path: The path to validate

        Returns:
            bool: True if path is safe, False otherwise
        """
        try:
            # Resolve to absolute path, following symlinks
            resolved_path = path.resolve()

            # Check if path is within any allowed base path
            for allowed_base in self.allowed_base_paths:
                try:
                    # relative_to() raises ValueError if path is not relative to base
                    resolved_path.relative_to(allowed_base)
                    return True
                except ValueError:
                    continue

            return False
        except Exception:
            # Any error during path resolution means it's not safe
            return False

    def create_directory_if_needed(self, file_path: Path) -> None:
        """
        Create parent directories for a file path if they don't exist.

        Args:
            file_path: The file path whose parent directories should be created

        Raises:
            ValueError: If the path is not safe
        """
        if not self.is_path_safe(file_path):
            raise ValueError(f"Unsafe path, cannot create directories: {file_path}")

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

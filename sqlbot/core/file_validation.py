"""
File Validation - Validates YAML and SQL syntax for DBT files.

This module provides syntax validation for DBT schema (YAML) and macro (SQL) files
to ensure they are properly formatted before saving.
"""

import re
from typing import Tuple, Optional
import yaml


class FileValidator:
    """Validates YAML and SQL syntax."""

    # Maximum file sizes (in bytes)
    MAX_SCHEMA_SIZE = 1024 * 1024  # 1MB
    MAX_MACRO_SIZE = 512 * 1024    # 500KB

    @staticmethod
    def validate_yaml(content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate YAML syntax.

        Args:
            content: The YAML content to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if YAML is valid
            - error_message: None if valid, error description if invalid
        """
        if not content or not content.strip():
            return False, "YAML content is empty"

        try:
            # Use safe_load to prevent code execution
            yaml.safe_load(content)
            return True, None
        except yaml.YAMLError as e:
            error_msg = str(e)
            # Make error message more user-friendly
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                error_msg = f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}: {e.problem}"
            return False, f"YAML syntax error: {error_msg}"
        except Exception as e:
            return False, f"Unexpected error parsing YAML: {str(e)}"

    @staticmethod
    def validate_dbt_schema(content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate DBT schema structure.

        Args:
            content: The schema YAML content to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if schema structure is valid
            - error_message: None if valid, error description if invalid
        """
        # First validate YAML syntax
        is_valid_yaml, yaml_error = FileValidator.validate_yaml(content)
        if not is_valid_yaml:
            return False, yaml_error

        try:
            data = yaml.safe_load(content)

            # Check if data is a dictionary
            if not isinstance(data, dict):
                return False, "Schema must be a YAML dictionary/object"

            # Check for required keys
            if 'version' not in data:
                return False, "Schema must include a 'version' field"

            # Validate version is 2
            version = data.get('version')
            if version != 2:
                return False, f"Schema version must be 2 (found: {version})"

            # Check if sources exist (optional but common)
            if 'sources' in data:
                sources = data['sources']

                # Validate sources is a list
                if not isinstance(sources, list):
                    return False, "'sources' must be a list"

                # Validate each source has required fields
                for idx, source in enumerate(sources):
                    if not isinstance(source, dict):
                        return False, f"Source at index {idx} must be a dictionary"

                    if 'name' not in source:
                        return False, f"Source at index {idx} missing required 'name' field"

                    # Check for tables (optional)
                    if 'tables' in source:
                        tables = source['tables']
                        if not isinstance(tables, list):
                            return False, f"Source '{source['name']}' tables must be a list"

                        for tidx, table in enumerate(tables):
                            if not isinstance(table, dict):
                                return False, f"Table at index {tidx} in source '{source['name']}' must be a dictionary"

                            if 'name' not in table:
                                return False, f"Table at index {tidx} in source '{source['name']}' missing required 'name' field"

            return True, None

        except Exception as e:
            return False, f"Error validating DBT schema structure: {str(e)}"

    @staticmethod
    def validate_sql(content: str) -> Tuple[bool, Optional[str]]:
        """
        Basic SQL syntax validation for macro files.

        Note: This performs basic checks only, not full SQL parsing.
        Returns warnings rather than hard errors since SQL parsing is complex.

        Args:
            content: The SQL/Jinja content to validate

        Returns:
            Tuple of (is_valid, warning_message)
            - is_valid: True unless there are critical syntax errors
            - warning_message: None if no issues, warning description if potential issues found
        """
        if not content or not content.strip():
            return False, "SQL content is empty"

        warnings = []

        # Check for balanced quotes
        single_quotes = content.count("'")
        double_quotes = content.count('"')

        if single_quotes % 2 != 0:
            warnings.append("Unbalanced single quotes detected")

        if double_quotes % 2 != 0:
            warnings.append("Unbalanced double quotes detected")

        # Check for balanced parentheses
        open_parens = content.count('(')
        close_parens = content.count(')')

        if open_parens != close_parens:
            warnings.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")

        # Check for balanced braces (for Jinja)
        open_braces = content.count('{')
        close_braces = content.count('}')

        if open_braces != close_braces:
            warnings.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")

        # Validate DBT macro syntax if present
        macro_pattern = r'{%\s*macro\s+(\w+)\s*\((.*?)\)\s*%}'
        endmacro_pattern = r'{%\s*endmacro\s*%}'

        macro_opens = re.findall(macro_pattern, content, re.DOTALL)
        macro_closes = re.findall(endmacro_pattern, content)

        if len(macro_opens) != len(macro_closes):
            warnings.append(f"Unbalanced macro tags: {len(macro_opens)} {{% macro %}}, {len(macro_closes)} {{% endmacro %}}")

        # Check for macro name validity
        for macro_name, params in macro_opens:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', macro_name):
                warnings.append(f"Invalid macro name: '{macro_name}'. Must start with letter or underscore, contain only alphanumeric and underscore")

        # Return result
        if warnings:
            return True, "Potential syntax issues found:\n" + "\n".join(f"  - {w}" for w in warnings)

        return True, None

    @staticmethod
    def validate_file_size(content: str, max_size: int, file_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file size is within limits.

        Args:
            content: The file content
            max_size: Maximum allowed size in bytes
            file_type: Description of file type for error message

        Returns:
            Tuple of (is_valid, error_message)
        """
        size = len(content.encode('utf-8'))

        if size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            actual_size_mb = size / (1024 * 1024)
            return False, f"{file_type} file too large: {actual_size_mb:.2f}MB (max: {max_size_mb:.2f}MB)"

        return True, None

    @staticmethod
    def validate_schema_file(content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a schema file completely (size, YAML syntax, DBT structure).

        Args:
            content: The schema file content

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        is_valid_size, size_error = FileValidator.validate_file_size(
            content,
            FileValidator.MAX_SCHEMA_SIZE,
            "Schema"
        )
        if not is_valid_size:
            return False, size_error

        # Validate DBT schema (includes YAML syntax check)
        return FileValidator.validate_dbt_schema(content)

    @staticmethod
    def validate_macro_file(content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a macro file completely (size, SQL syntax).

        Args:
            content: The macro file content

        Returns:
            Tuple of (is_valid, warning_message)
            Note: Returns warnings, not hard errors for SQL
        """
        # Check file size
        is_valid_size, size_error = FileValidator.validate_file_size(
            content,
            FileValidator.MAX_MACRO_SIZE,
            "Macro"
        )
        if not is_valid_size:
            return False, size_error

        # Validate SQL (returns warnings)
        return FileValidator.validate_sql(content)

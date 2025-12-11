"""
File Editing Tool - LangChain tool for LLM agent to edit DBT schema and macro files.

This tool allows the LLM agent to read, create, and update DBT schema and macro files
within the current profile's directory structure, with security sandboxing and validation.
"""

from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from sqlbot.core.docblocks import DocBlockCache
from sqlbot.core.file_security import FileSecurityValidator
from sqlbot.core.file_validation import FileValidator


class FileEditingInput(BaseModel):
    """Input schema for FileEditingTool."""

    operation: str = Field(
        description="Operation to perform: 'read_schema', 'update_schema', 'delete_schema', 'list_macros', 'read_macro', 'update_macro', 'create_macro', 'delete_macro'"
    )
    content: Optional[str] = Field(
        default=None,
        description="File content for write operations (update_schema, update_macro, create_macro)"
    )
    filename: Optional[str] = Field(
        default=None,
        description="Macro filename for macro operations (read_macro, update_macro, create_macro). Must end with .sql"
    )


class FileEditingTool(BaseTool):
    """Tool for editing DBT schema and macro files."""

    name: str = "edit_dbt_files"
    description: str = """Edit DBT schema and macro files within the current profile.

Use this to:
- Read current schema.yml (operation='read_schema')
- Update schema.yml with new definitions (operation='update_schema', content='...')
- Delete schema.yml (operation='delete_schema')
- List available macros (operation='list_macros')
- Read a macro file (operation='read_macro', filename='my_macro.sql')
- Update a macro (operation='update_macro', filename='my_macro.sql', content='...')
- Create new macro (operation='create_macro', filename='new_macro.sql', content='...')
- Delete a macro file (operation='delete_macro', filename='my_macro.sql')

All paths are automatically sandboxed to the current profile directory.
Always read files before editing to understand current state.

Examples:
- edit_dbt_files(operation='read_schema')
- edit_dbt_files(operation='update_schema', content='version: 2\\nsources:\\n  - name: my_source\\n...')
- edit_dbt_files(operation='delete_schema')
- edit_dbt_files(operation='list_macros')
- edit_dbt_files(operation='read_macro', filename='my_macro.sql')
- edit_dbt_files(operation='create_macro', filename='new_macro.sql', content='{% macro name() %}...{% endmacro %}')
- edit_dbt_files(operation='delete_macro', filename='my_macro.sql')
"""
    args_schema: Type[BaseModel] = FileEditingInput

    profile_name: str

    def __init__(self, profile_name: str):
        """
        Initialize the tool for a specific profile.

        Args:
            profile_name: The name of the DBT profile to work with
        """
        super().__init__(profile_name=profile_name)

    def _run(
        self,
        operation: str,
        content: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Execute the file editing operation.

        Args:
            operation: The operation to perform
            content: File content (for write operations)
            filename: Macro filename (for macro operations)

        Returns:
            str: Result message describing what was done
        """
        try:
            validator = FileSecurityValidator(self.profile_name)

            # READ SCHEMA
            if operation == 'read_schema':
                return self._read_schema(validator)

            # UPDATE SCHEMA
            elif operation == 'update_schema':
                if content is None:
                    return "Error: content parameter is required for update_schema operation"
                return self._update_schema(validator, content)

            # DELETE SCHEMA
            elif operation == 'delete_schema':
                return self._delete_schema(validator)

            # LIST MACROS
            elif operation == 'list_macros':
                return self._list_macros(validator)

            # READ MACRO
            elif operation == 'read_macro':
                if filename is None:
                    return "Error: filename parameter is required for read_macro operation"
                return self._read_macro(validator, filename)

            # UPDATE MACRO
            elif operation == 'update_macro':
                if filename is None:
                    return "Error: filename parameter is required for update_macro operation"
                if content is None:
                    return "Error: content parameter is required for update_macro operation"
                return self._update_macro(validator, filename, content)

            # CREATE MACRO
            elif operation == 'create_macro':
                if filename is None:
                    return "Error: filename parameter is required for create_macro operation"
                if content is None:
                    return "Error: content parameter is required for create_macro operation"
                return self._create_macro(validator, filename, content)

            # DELETE MACRO
            elif operation == 'delete_macro':
                if filename is None:
                    return "Error: filename parameter is required for delete_macro operation"
                return self._delete_macro(validator, filename)

            else:
                return f"Error: Unknown operation '{operation}'. Valid operations: read_schema, update_schema, delete_schema, list_macros, read_macro, update_macro, create_macro, delete_macro"

        except Exception as e:
            return f"Error executing {operation}: {str(e)}"

    def _read_schema(self, validator: FileSecurityValidator) -> str:
        """Read the schema.yml file."""
        try:
            schema_path = validator.validate_schema_path()

            if not schema_path.exists():
                return f"Schema file does not exist yet. It would be created at: {schema_path}\n\nYou can create it using update_schema with valid DBT schema YAML content."

            with open(schema_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"Schema file location: {schema_path}\n\nContent:\n{content}"

        except Exception as e:
            return f"Error reading schema: {str(e)}"

    def _update_schema(self, validator: FileSecurityValidator, content: str) -> str:
        """Update the schema.yml file with validation."""
        try:
            # Validate schema content
            is_valid, error_message = FileValidator.validate_schema_file(content)
            if not is_valid:
                return f"Schema validation failed:\n{error_message}\n\nPlease fix the errors and try again."

            # Get validated path
            schema_path = validator.validate_schema_path()

            # Create parent directories if needed
            validator.create_directory_if_needed(schema_path)

            # Write atomically (temp file → rename)
            temp_path = schema_path.with_suffix('.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.rename(schema_path)

            self._invalidate_doc_blocks()

            return f"Successfully updated schema file at: {schema_path}\n\nThe schema has been validated and saved."

        except Exception as e:
            return f"Error updating schema: {str(e)}"

    def _list_macros(self, validator: FileSecurityValidator) -> str:
        """List all macro files."""
        try:
            macro_files = validator.list_macro_files()

            if not macro_files:
                return "No macro files found in the profile's macros directory.\n\nYou can create new macros using the create_macro operation."

            result = f"Found {len(macro_files)} macro file(s):\n\n"
            for macro_path in macro_files:
                result += f"  - {macro_path.name} (name: {macro_path.stem})\n"

            result += "\nUse read_macro operation with the filename to view contents."
            return result

        except Exception as e:
            return f"Error listing macros: {str(e)}"

    def _read_macro(self, validator: FileSecurityValidator, filename: str) -> str:
        """Read a specific macro file."""
        try:
            # Validate and get macro path
            macro_path = validator.validate_macro_path(filename)

            if not macro_path.exists():
                return f"Macro file not found: {filename}\n\nUse list_macros to see available macros, or create_macro to create a new one."

            with open(macro_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"Macro file: {filename}\nLocation: {macro_path}\n\nContent:\n{content}"

        except ValueError as e:
            return f"Invalid filename: {str(e)}"
        except Exception as e:
            return f"Error reading macro: {str(e)}"

    def _update_macro(self, validator: FileSecurityValidator, filename: str, content: str) -> str:
        """Update an existing macro file."""
        try:
            # Validate macro content (returns warnings, not errors)
            is_valid, warning_message = FileValidator.validate_macro_file(content)
            if not is_valid:
                return f"Macro validation failed:\n{warning_message}\n\nPlease fix the errors and try again."

            # Validate and get macro path
            macro_path = validator.validate_macro_path(filename)

            if not macro_path.exists():
                return f"Macro file not found: {filename}\n\nUse create_macro to create a new macro, or list_macros to see existing macros."

            # Write atomically (temp file → rename)
            temp_path = macro_path.with_suffix('.tmp')
            temp_path.write_text(content, encoding='utf-8')
            temp_path.rename(macro_path)

            result = f"Successfully updated macro file: {filename}\nLocation: {macro_path}"
            if warning_message:
                result += f"\n\nWarning: {warning_message}"

            self._invalidate_doc_blocks()

            return result

        except ValueError as e:
            return f"Invalid filename: {str(e)}"
        except Exception as e:
            return f"Error updating macro: {str(e)}"

    def _create_macro(self, validator: FileSecurityValidator, filename: str, content: str) -> str:
        """Create a new macro file."""
        try:
            # Validate macro content (returns warnings, not errors)
            is_valid, warning_message = FileValidator.validate_macro_file(content)
            if not is_valid:
                return f"Macro validation failed:\n{warning_message}\n\nPlease fix the errors and try again."

            # Validate and get macro path
            macro_path = validator.validate_macro_path(filename)

            if macro_path.exists():
                return f"Macro file already exists: {filename}\n\nUse update_macro to modify it, or choose a different filename."

            # Create parent directories if needed
            validator.create_directory_if_needed(macro_path)

            # Write file
            macro_path.write_text(content, encoding='utf-8')

            result = f"Successfully created macro file: {filename}\nLocation: {macro_path}\n\nThe macro is now available for use in your queries."
            if warning_message:
                result += f"\n\nWarning: {warning_message}"

            self._invalidate_doc_blocks()

            return result

        except ValueError as e:
            return f"Invalid filename: {str(e)}"
        except Exception as e:
            return f"Error creating macro: {str(e)}"

    def _delete_schema(self, validator: FileSecurityValidator) -> str:
        """Delete the schema.yml file."""
        try:
            schema_path = validator.validate_schema_path()

            if not schema_path.exists():
                return f"Schema file does not exist: {schema_path}\n\nNothing to delete."

            # Delete the file
            schema_path.unlink()

            self._invalidate_doc_blocks()

            return f"Successfully deleted schema file at: {schema_path}\n\nThe schema file has been removed."

        except Exception as e:
            return f"Error deleting schema: {str(e)}"

    def _delete_macro(self, validator: FileSecurityValidator, filename: str) -> str:
        """Delete a macro file."""
        try:
            # Validate and get macro path
            macro_path = validator.validate_macro_path(filename)

            if not macro_path.exists():
                return f"Macro file not found: {filename}\n\nNothing to delete."

            # Delete the file
            macro_path.unlink()

            self._invalidate_doc_blocks()

            return f"Successfully deleted macro file: {filename}\nLocation was: {macro_path}\n\nThe macro has been removed."

        except ValueError as e:
            return f"Invalid filename: {str(e)}"
        except Exception as e:
            return f"Error deleting macro: {str(e)}"

    def _invalidate_doc_blocks(self) -> None:
        """Clear cached doc blocks for this profile."""
        try:
            DocBlockCache.invalidate(self.profile_name)
        except Exception:
            # Cache invalidation failures should never block file operations
            pass

    async def _arun(
        self,
        operation: str,
        content: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """Async version of _run (not implemented, falls back to sync)."""
        return self._run(operation, content, filename)

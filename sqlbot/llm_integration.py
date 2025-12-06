#!/usr/bin/env python3
"""
LLM Integration for SQLBot Database Interface

Clean version with simple status messages and full query visibility.
"""

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.agents import create_agent as create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from typing import Type
from pydantic import BaseModel, Field
import os
import logging
import subprocess
import sys
import yaml
import re

# Load environment variables
load_dotenv()

# Global dbt profile configuration (can be set from CLI or environment)
# Note: This will be dynamically checked, not cached at import time
DBT_PROFILE_NAME = None  # No fallback - load from config

def get_current_profile():
    """Get the current dbt profile name from config or global variable"""
    if DBT_PROFILE_NAME:
        return DBT_PROFILE_NAME

    # Fall back to loading from config system
    try:
        from .core.config import SQLBotConfig
        config = SQLBotConfig.from_env()
        return config.profile
    except Exception as e:
        # Last resort: check environment variable
        import os
        profile = os.getenv('DBT_PROFILE_NAME') or os.getenv('SQLBOT_PROFILE')
        if profile:
            return profile
        # If still nothing, return a default
        return 'sqlbot'

def check_dbt_setup():
    """
    Check if dbt is properly configured and provide helpful guidance if not.
    Uses DbtService with virtual dbt_project.yml spoofing.

    Returns:
        tuple: (is_configured: bool, message: str)
    """
    try:
        # Use DbtService which handles virtual dbt_project.yml spoofing
        from .core.config import SQLBotConfig
        from .core.dbt_service import get_dbt_service

        config = SQLBotConfig.from_env(profile=get_current_profile())
        dbt_service = get_dbt_service(config)

        # Use our fixed debug method that handles virtual dbt_project.yml
        debug_result = dbt_service.debug()

        if debug_result['success'] and debug_result['connection_ok']:
            return True, "dbt is properly configured"
        
        # Parse common error messages and provide helpful guidance
        error_output = debug_result.get('error', 'Unknown connection error')
        
        if "Could not find profile" in error_output or f"profile named '{get_current_profile()}'" in error_output:
            return False, f"""
🔧 **dbt Profile Not Found**

SQLBot needs a dbt profile to connect to your database. You can create it locally or globally:

**Option 1: Local .dbt folder (recommended):**
```bash
mkdir -p .dbt
```

**Create `.dbt/profiles.yml` with your database connection:**
```yaml
{get_current_profile()}:
  target: dev
  outputs:
    dev:
      type: sqlserver  # or postgres, snowflake, etc.
      server: "{{ env_var('DB_SERVER') }}"
      database: "{{ env_var('DB_NAME') }}"
      schema: dbo
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
      port: 1433
      encrypt: true
      trust_cert: false
```

**Option 2: Global ~/.dbt folder:**
```bash
mkdir -p ~/.dbt
```

**Create `~/.dbt/profiles.yml` with your database connection (same format as above)**

**3. Make sure your `.env` file has the database credentials:**
```bash
DB_SERVER=your_database_server.com
DB_NAME=your_database_name
DB_USER=your_username
DB_PASS=your_password
```

**4. Test the connection:**
```bash
dbt debug
```

📚 **Need help?** See the README.md for detailed setup instructions.
"""
        
        elif "Could not connect" in error_output or "connection" in error_output.lower() or "Connection test: FAIL" in error_output:
            # Get additional debug information from the debug result
            debug_info = debug_result
            profiles_dir = debug_info.get('profiles_dir', 'unknown')
            
            return False, f"""
🔌 **Database Connection Failed**

Your dbt profile exists but can't connect to the database. Here's what went wrong:

**Error Details:**
{debug_info.get('error', 'No detailed error information available')}

**Configuration Info:**
- Profile: `{debug_info.get('profile', 'unknown')}`
- Profiles directory: `{profiles_dir}`
- Exit code: {debug_info.get('return_code', 'unknown')}

**How to fix it:**

**1. Check your database connection settings:**
```bash
# Verify your .env file has correct credentials:
DB_SERVER=your_database_server.com  # Check this hostname
DB_NAME=your_database_name          # Check this database exists  
DB_USER=your_username               # Check this user exists
DB_PASS=your_password               # Check this password is correct
```

**2. Test your connection manually:**
```bash
# Test with the same configuration SQLBot is using:
DBT_PROFILES_DIR="{profiles_dir}" dbt debug --profile {debug_info.get('profile', 'your_profile')}
```

**3. Common fixes:**
- ✅ Database server is running and accessible
- ✅ Network/firewall allows database connections  
- ✅ Database drivers are installed (e.g., ODBC Driver for SQL Server)
- ✅ Environment variables are properly set

**4. For SQL Server, ensure you have the ODBC driver:**
```bash
# On Ubuntu/Debian:
sudo apt-get install unixodbc-dev

# On macOS:
brew install unixodbc
```

📚 **Still having issues?** Check the troubleshooting section in README.md.
"""
        
        else:
            # Get additional debug information from the debug result
            debug_info = debug_result
            profiles_dir = debug_info.get('profiles_dir', 'unknown')
            
            return False, f"""
⚠️ **dbt Configuration Issue**

There's an issue with your dbt setup. Here's what dbt reported:

**Error Details:**
{debug_info.get('error', error_output.strip())}

**Configuration Info:**
- Profile: `{debug_info.get('profile', 'unknown')}`
- Profiles directory: `{profiles_dir}`
- Exit code: {debug_info.get('return_code', 'unknown')}

**Raw dbt debug output:**
```
{debug_info.get('stdout', '').strip() or 'No output captured'}
```

**How to fix it:**

**1. Test your connection manually:**
```bash
# Test with the same configuration SQLBot is using:
DBT_PROFILES_DIR="{profiles_dir}" dbt debug --profile {debug_info.get('profile', 'your_profile')}
```

**2. Check your configuration files:**
- Verify your `{profiles_dir}/profiles.yml` file syntax
- Check your `.env` file has all required database credentials
- Make sure your database is running and accessible

**3. Common fixes:**
- ✅ Profile name matches exactly in profiles.yml
- ✅ Environment variables are properly set
- ✅ Database server is accessible
- ✅ Required database drivers are installed

📚 **Need help?** See the troubleshooting section in README.md.
"""
    
    except subprocess.TimeoutExpired:
        return False, """
⏱️ **dbt Debug Timeout**

The dbt debug command timed out. This usually means:
- Database server is unreachable
- Network connectivity issues
- Database is overloaded

**Try these steps:**
1. Check your database server is running
2. Test network connectivity to your database
3. Verify your connection settings in `~/.dbt/profiles.yml`
"""
    
    except FileNotFoundError:
        return False, """
❌ **dbt Not Installed**

SQLBot requires dbt to be installed. Install it with:

```bash
pip install dbt-sqlserver  # for SQL Server
# or
pip install dbt-postgres   # for PostgreSQL
# or  
pip install dbt-snowflake  # for Snowflake
```

Then set up your dbt profile as described in the README.md.
"""
    
    except Exception as e:
        return False, f"""
🔧 **Unexpected dbt Issue**

An unexpected error occurred while checking dbt setup:
```
{str(e)}
```

**Try these steps:**
1. Run `dbt debug` manually to see what's happening
2. Check that dbt is properly installed: `dbt --version`
3. Verify your `~/.dbt/profiles.yml` file exists and has correct syntax

📚 **Need help?** See the README.md for detailed setup instructions.
"""

logger = logging.getLogger(__name__)

# Global conversation history for the session
conversation_history = []

def clear_conversation_history():
    """Clear the global conversation history"""
    global conversation_history
    conversation_history = []

# Global flag to control context display
show_context = False

# Global flag to control debug logging
DEBUG_MODE = False

def get_llm():
    """
    Create and return a configured OpenAI LLM instance for ccdbi.
    
    Returns:
        ChatOpenAI: Configured LLM instance
    """
    try:
        # Use SQLBot-specific variables 
        model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
        max_tokens = int(os.getenv('SQLBOT_LLM_MAX_TOKENS', '50000'))
        verbosity = os.getenv('SQLBOT_LLM_VERBOSITY', 'low')
        effort = os.getenv('SQLBOT_LLM_EFFORT', 'minimal')
        
        from rich.console import Console
        console = Console()
        
        # GPT-5 supports verbosity and reasoning effort parameters via Responses API
        
        # Configure GPT-5 specific parameters for LangChain
        llm_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "api_key": os.getenv('OPENAI_API_KEY'),
            "streaming": False,
            "disable_streaming": True,
            "request_timeout": int(os.getenv('SQLBOT_LLM_REQUEST_TIMEOUT', '90')),
            "max_retries": 1
        }
        
        if model.startswith('gpt-5'):
            # GPT-5 parameters - using Responses API with LangChain 0.3.32+
            llm_kwargs["output_version"] = "responses/v1"
            llm_kwargs["extra_body"] = {
                "text": {"verbosity": verbosity},
                "reasoning": {"effort": effort}
            }
        
        llm = ChatOpenAI(**llm_kwargs)
        return llm
    except Exception as e:
        logger.error(f"Failed to create LLM instance: {e}")
        raise

def test_llm_basic():
    """
    Basic test of LLM functionality.
    
    Returns:
        bool: True if LLM is working, False otherwise
    """
    try:
        llm = get_llm()
        response = llm.invoke("Say 'Hello from LLM integration!' and nothing else.")
        print(f"✅ LLM Response: {response.content}")
        return True
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False

class DbtQueryInput(BaseModel):
    """Input schema for dbt query tool"""
    query: str = Field(description="SQL query or dbt macro to execute against the database")

class DbtQueryTool(BaseTool):
    """
    LangChain tool for executing dbt/SQL queries against the database.
    
    This tool wraps the existing ccdbi.py functionality to allow the LLM
    to execute database queries and return formatted results.
    """
    name: str = "execute_dbt_query"
    description: str = """Execute SQL queries or dbt macros against the database.

    Use this tool to run SQL queries or dbt macros to answer questions about the data.

    Input should be valid SQL or dbt macro syntax such as:
    - SELECT * FROM film LIMIT 10
    - {{ your_macro_name(parameter) }}
    - SELECT column, COUNT(*) FROM customer WHERE date_col >= '2024-01-01' GROUP BY column
    
    The tool will return formatted query results or error messages.
    """
    args_schema: Type[BaseModel] = DbtQueryInput
    
    def __init__(self, session_id: str = 'default_session', unified_display=None, event_notifier=None):
        """Initialize with session ID for query result tracking, unified display, and event notifier"""
        super().__init__()
        self._session_id = session_id
        self._unified_display = unified_display
        self._event_notifier = event_notifier
    
    def _run(self, query: str) -> str:
        """Execute the dbt query and ALWAYS show results to user"""
        import os
        import datetime
        import traceback
        
        # Set up logging to tmp file
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp', 'tool_errors.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        def log_to_file(message):
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
            except (FileNotFoundError, PermissionError):
                # Silently skip logging if directory doesn't exist or no permissions
                pass
        
        log_to_file(f"🚀 TOOL EXECUTION START: {query[:100]}...")
        
        try:
            # Mark that a tool execution is happening
            global tool_execution_happened
            tool_execution_happened = True

            log_to_file(f"✅ Tool execution flag set, unified_display available: {self._unified_display is not None}")

            from rich.console import Console
            console = Console()

            # Execute the query AS-IS (do not normalize). The agent should learn from errors.

            # FIRST PRIORITY: Execute query and show results to USER using ccdbi directly
            # This ensures the user ALWAYS sees results regardless of what happens with LLM processing
            import sys
            import os
            project_root = os.path.dirname(os.path.abspath(__file__))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            try:
                # Use the new DbtService for all dbt operations
                from .core.config import SQLBotConfig
                from .core.dbt_service import get_dbt_service
                from .interfaces.repl.formatting import ResultFormatter

                # Create config with current profile and respect global safeguard setting
                # Import the global safeguard setting
                try:
                    from . import repl
                    safeguard_enabled = repl.READONLY_MODE
                except ImportError:
                    try:
                        import repl
                        safeguard_enabled = repl.READONLY_MODE
                    except ImportError:
                        safeguard_enabled = True  # Default to safeguards enabled

                config = SQLBotConfig.from_env(profile=get_current_profile())
                config.dangerous = not safeguard_enabled  # Apply global safeguard setting
                config.max_rows = 1000

                # Get dbt service and formatter
                dbt_service = get_dbt_service(config)
                formatter = ResultFormatter(console)

                # Display tool call ONCE - either via unified_display OR event_notifier, not both
                query_message = f"🔍 Executing SQL query:\n```sql\n{query.strip()}\n```"
                if self._event_notifier:
                    # Web interface - send via event notifier
                    self._event_notifier("message", {
                        "role": "system",
                        "content": query_message
                    })
                elif self._unified_display:
                    # CLI interface - display via unified display
                    self._unified_display.display_impl.display_tool_call("Database Query", query)
                    log_to_file("✅ Tool call displayed via unified_display")

                # Perform safety check if safeguards are enabled
                safeguard_message = None
                if safeguard_enabled:
                    from .core.safety import analyze_sql_safety
                    safety_analysis = analyze_sql_safety(query, dangerous_mode=False)

                    if safety_analysis.is_read_only and safety_analysis.level.value == "safe":
                        # Query is safe
                        safeguard_message = "✔ Query passes safeguard against dangerous operations."
                        if self._unified_display:
                            # Display safeguard success message
                            self._unified_display.display_impl.display_success_message(safeguard_message)
                        # Also send to web interface via event notifier
                        if self._event_notifier:
                            self._event_notifier("message", {
                                "role": "system",
                                "content": safeguard_message
                            })
                    else:
                        # Query has dangerous operations
                        operations_str = ", ".join(safety_analysis.dangerous_operations)
                        safeguard_message = f"✖ Query disallowed due to dangerous operations: {operations_str}"

                        if self._unified_display:
                            # Display safeguard error message
                            self._unified_display.display_impl.display_error_message(safeguard_message)
                        # Also send to web interface via event notifier
                        if self._event_notifier:
                            self._event_notifier("message", {
                                "role": "system",
                                "content": safeguard_message
                            })

                        # Return error without executing the query
                        import json
                        return json.dumps({
                            "query": query.strip(),
                            "success": False,
                            "error": f"Query blocked by safeguard: {operations_str}",
                            "safeguard_message": safeguard_message
                        }, indent=2)
                
                # Suppress results output to avoid interfering with thinking indicator
                # console.print("📊 Results:")
                
                # Execute query and get structured results
                # No limit needed - macro prevents dbt from adding LIMIT clauses
                result = dbt_service.execute_query(query)

                # Record the result in the query result list
                from .core.query_result_list import get_query_result_list

                # Use the session ID from this tool instance
                session_id = self._session_id
                result_list = get_query_result_list(session_id)
                entry = result_list.add_result(query.strip(), result)

                # Emit query results as a system message with formatted table
                if result.success and result.data:
                    row_count = len(result.data)
                    exec_time = result.execution_time

                    # Build a formatted results message
                    results_message = f"📊 Query results: {row_count} row(s) returned in {exec_time:.2f}s"

                    # For small result sets, include the data in markdown table format
                    if row_count <= 10 and result.columns:
                        results_message += "\n\n"
                        # Header
                        results_message += "| " + " | ".join(result.columns) + " |\n"
                        results_message += "| " + " | ".join(["---"] * len(result.columns)) + " |\n"
                        # Rows - handle both dict and list formats
                        for row in result.data[:10]:
                            if isinstance(row, dict):
                                # Row is a dictionary - extract values in column order
                                row_values = [row.get(col) for col in result.columns]
                            else:
                                # Row is already a list/tuple
                                row_values = row
                            results_message += "| " + " | ".join(str(v) if v is not None else "NULL" for v in row_values) + " |\n"
                    elif row_count > 10:
                        results_message += f"\n(Showing first 10 of {row_count} rows)"

                    if self._event_notifier:
                        self._event_notifier("message", {
                            "role": "system",
                            "content": results_message
                        })
                
                # Suppress result formatting to avoid interfering with thinking indicator
                # formatter.format_query_result(result)
                
                # Return the full data for conversation history (latest result gets full data)
                if result.success:
                    # Return full JSON data for the LLM to see
                    import json
                    # Use serialized data to handle Decimal objects (empty list if no data)
                    serialized_data = result._serialize_data(result.data) if result.data else []

                    # Build performance context for LLM
                    exec_time = result.execution_time
                    perf_note = ""
                    if exec_time >= 10.0:
                        perf_note = "⚠️ SLOW QUERY (>10s) - Consider optimization with EXPLAIN or adding indexes"
                    elif exec_time >= 5.0:
                        perf_note = "⚠️ Moderately slow query (>5s) - May benefit from optimization"
                    elif exec_time < 1.0:
                        perf_note = "⚡ Fast query (<1s)"

                    result_json = json.dumps({
                        "query_index": entry.index,
                        "query": query.strip(),
                        "success": True,
                        "columns": result.columns or [],
                        "data": serialized_data,
                        "row_count": result.row_count or 0,
                        "execution_time": exec_time,
                        "execution_time_seconds": f"{exec_time:.2f}s",
                        "performance_note": perf_note
                    }, indent=2)
                    # Note: Query results are now displayed via system message above
                    # (no need to display via unified_display anymore)

                    log_to_file(f"✅ TOOL SUCCESS: Query executed successfully, returning result")
                    return result_json
                else:
                    # Return error information with index - preserve all error details
                    if result.error and result.error.strip():
                        error_msg = result.error.strip()
                    else:
                        # Fallback: try to get error details from the result object itself
                        error_msg = f"Query execution failed (success=False, execution_time={result.execution_time:.3f}s)"
                        if hasattr(result, '__dict__'):
                            # Include error information but format it cleanly
                            # Only include key diagnostic fields, not internal representation
                            diagnostic_fields = {
                                'success': getattr(result, 'success', None),
                                'execution_time': getattr(result, 'execution_time', None),
                                'row_count': getattr(result, 'row_count', None)
                            }
                            # Filter out None values
                            diagnostic_info = {k: v for k, v in diagnostic_fields.items() if v is not None}
                            if diagnostic_info:
                                import json
                                error_msg += f" - Diagnostics: {json.dumps(diagnostic_info)}"

                    error_result = f"Query #{entry.index} failed: {error_msg}"

                    # Display error to user via event notifier or unified display
                    error_display_message = f"❌ Query execution failed:\n{error_msg}"
                    if self._event_notifier:
                        # Web interface - send error via event notifier
                        self._event_notifier("message", {
                            "role": "system",
                            "content": error_display_message
                        })
                    elif self._unified_display:
                        # CLI interface - display via unified display
                        self._unified_display.display_impl.display_tool_result("Query Error", error_msg)

                    # Return clear error message for LLM that it should stop and report the error
                    import json

                    # Check if this is a compilation error that cannot be fixed
                    is_compilation_error = any(keyword in error_msg for keyword in [
                        "is undefined", "Compilation Error", "does not exist",
                        "Check for typos", "install package dependencies"
                    ])

                    if is_compilation_error:
                        # CRITICAL: Compilation errors cannot be fixed by the agent
                        return json.dumps({
                            "query_index": entry.index,
                            "query": query.strip(),
                            "success": False,
                            "error": error_msg,
                            "CRITICAL_ERROR": "COMPILATION ERROR - CANNOT BE FIXED",
                            "INSTRUCTION": "STOP IMMEDIATELY. Do NOT retry. Do NOT try variations. Report this error to the user NOW: The macro or function does not exist in the dbt project. This is a configuration issue that the user must fix."
                        }, indent=2)
                    else:
                        return json.dumps({
                            "query_index": entry.index,
                            "query": query.strip(),
                            "success": False,
                            "error": error_msg,
                            "message": "QUERY FAILED - Report this error to the user and do NOT retry more than once."
                        }, indent=2)
                    
            except Exception as e:
                error_result = f"Error executing query: {e}"
                full_traceback = traceback.format_exc()
                
                log_to_file(f"❌ INNER EXCEPTION in tool execution: {type(e).__name__}: {e}")
                log_to_file(f"❌ INNER EXCEPTION traceback:\n{full_traceback}")
                
                # Display detailed tool error in real-time if we have unified display
                if self._unified_display:
                    self._unified_display.display_impl.display_tool_result("Query Error", str(e))
                    # Also display the full error details as a system message
                    self._unified_display.display_impl.display_system_message(f"Tool Execution Error Details:\n{full_traceback}", "red")
                    log_to_file("✅ Displayed inner exception to unified display")
                else:
                    log_to_file("❌ No unified display available for inner exception")
                
                # Log detailed error to stderr for debugging
                import sys
                print(f"🔍 DEBUG: Tool execution error: {e}", file=sys.stderr)
                print(f"🔍 DEBUG: Full traceback:\n{full_traceback}", file=sys.stderr)
                
                log_to_file(f"🔄 INNER EXCEPTION returning: {error_result}")
                return error_result
                
        except Exception as e:
            error_result = f"Error executing query: {str(e)}"
            full_traceback = traceback.format_exc()
            
            log_to_file(f"❌ OUTER EXCEPTION in tool execution: {type(e).__name__}: {e}")
            log_to_file(f"❌ OUTER EXCEPTION traceback:\n{full_traceback}")
            
            # Display detailed tool error in real-time if we have unified display
            if self._unified_display:
                self._unified_display.display_impl.display_tool_result("Query Error", str(e))
                # Also display the full error details as a system message
                self._unified_display.display_impl.display_system_message(f"Tool Execution Error Details:\n{full_traceback}", "red")
                log_to_file("✅ Displayed outer exception to unified display")
            else:
                log_to_file("❌ No unified display available for outer exception")
            
            # Log detailed error to stderr for debugging
            import sys
            print(f"🔍 DEBUG: Tool execution error: {e}", file=sys.stderr)
            print(f"🔍 DEBUG: Full traceback:\n{full_traceback}", file=sys.stderr)
            
            log_to_file(f"🔄 OUTER EXCEPTION returning: {error_result}")
            return error_result
    
    async def _arun(self, query: str) -> str:
        """Async version of _run (not implemented, falls back to sync)"""
        return self._run(query)


class ExportDataInput(BaseModel):
    """Input schema for export data tool"""
    format: str = Field(default="csv", description="Export format: csv, excel, or parquet")
    location: str = Field(default=None, description="Directory path to save the file (defaults to ./tmp)")


class ExportDataTool(BaseTool):
    """Tool for exporting the most recent query results to various file formats"""

    name: str = "export_data"
    description: str = "Export the most recent successful query results to CSV, Excel, or Parquet format. Only exports the most recently executed successful query results."
    args_schema: Type[BaseModel] = ExportDataInput

    def __init__(self, session_id: str):
        super().__init__()
        # Store session_id as a private attribute to avoid Pydantic field conflicts
        self._session_id = session_id

    def _run(self, format: str = "csv", location: str = None) -> str:
        """
        Export the most recent query results

        Args:
            format: Export format - "csv", "excel", or "parquet" (default: "csv")
            location: Directory path to save file (default: "./tmp")

        Returns:
            str: Result message about the export operation
        """
        try:
            from .core.export import export_latest_result

            # Validate format
            valid_formats = ["csv", "excel", "parquet"]
            if format not in valid_formats:
                return f"Invalid format '{format}'. Valid formats are: {', '.join(valid_formats)}"

            # Export the data
            result = export_latest_result(self._session_id, format, location)

            if result["success"]:
                return (f"Successfully exported {result['row_count']} rows to {result['file_path']} "
                       f"in {result['format']} format. "
                       f"Columns: {', '.join(result['columns'])}")
            else:
                return f"Export failed: {result['error']}"

        except Exception as e:
            return f"Export error: {str(e)}"

    async def _arun(self, format: str = "csv", location: str = None) -> str:
        """Async version of _run (not implemented, falls back to sync)"""
        return self._run(format, location)


def create_export_data_tool(session_id: str) -> ExportDataTool:
    """
    Create an export data tool for the given session

    Args:
        session_id: Session ID for the tool

    Returns:
        ExportDataTool instance
    """
    return ExportDataTool(session_id=session_id)


def get_profile_paths(profile_name):
    """
    Get potential paths for profile configuration in priority order.

    Returns:
        tuple: (schema_paths, macro_paths) - lists of paths to try in order
    """
    if not profile_name:
        return [], []

    # Use current working directory (where the user's project is)
    project_root = os.getcwd()

    schema_paths = [
        # 1. Hidden .sqlbot/profiles/ (preferred)
        os.path.join(project_root, '.sqlbot', 'profiles', profile_name, 'models', 'sources.yml'),
        os.path.join(project_root, '.sqlbot', 'profiles', profile_name, 'models', 'schema.yml'),
        # 2. Project ./profiles/ (fallback)
        os.path.join(project_root, 'profiles', profile_name, 'models', 'sources.yml'),
        os.path.join(project_root, 'profiles', profile_name, 'models', 'schema.yml'),
        # 3. dbt models directory (standard location)
        os.path.join(project_root, 'models', 'sources.yml'),
        os.path.join(project_root, 'models', 'schema.yml')
    ]

    macro_paths = [
        # 1. Hidden .sqlbot/profiles/ (preferred)
        os.path.join(project_root, '.sqlbot', 'profiles', profile_name, 'macros'),
        # 2. Project ./profiles/ (fallback)
        os.path.join(project_root, 'profiles', profile_name, 'macros'),
        # 3. dbt macros directory (standard location)
        os.path.join(project_root, 'macros')
    ]

    return schema_paths, macro_paths


def ensure_schema_available_to_dbt():
    """
    Verify that the profile-specific schema exists and is accessible to dbt.
    With the new profile-specific configuration, dbt can access schemas directly
    from profile directories, so no copying is needed.
    """
    try:
        schema_paths, _ = get_profile_paths(get_current_profile())

        # Find the profile-specific schema
        profile_schema_path = None
        for path in schema_paths:
            if os.path.exists(path):
                profile_schema_path = path
                break

        if profile_schema_path:
            from rich.console import Console
            console = Console()
            # Schema file found and available
        else:
            from rich.console import Console
            console = Console()
            console.print(f"⚠️ No schema file found for profile '{get_current_profile()}'")

    except Exception as e:
        # Don't fail if schema verification fails - just log it
        from rich.console import Console
        console = Console()
        console.print(f"⚠️ Could not verify profile schema: {e}")

def load_schema_info():
    """
    Load schema information with profile discovery priority:
    1. .sqlbot/profiles/{profile}/models/schema.yml (preferred)
    2. profiles/{profile}/models/schema.yml (fallback)
    3. models/schema.yml (legacy)
    
    Also ensures dbt can find the schema by copying it to models/schema.yml
    
    Returns:
        str: Formatted schema information for system prompt
    """
    try:
        # First, ensure dbt can find the schema
        ensure_schema_available_to_dbt()

        schema_paths, _ = get_profile_paths(get_current_profile())
        
        schema_path = None
        path_type = "unknown"
        
        for i, path in enumerate(schema_paths):
            if os.path.exists(path):
                schema_path = path
                if i == 0:
                    path_type = "profile (.sqlbot/profiles/)"
                elif i == 1:
                    path_type = "profile (./profiles/)"
                else:
                    path_type = "legacy (./models/)"
                break
        
        if not schema_path:
            return f"""Schema file not found for profile '{get_current_profile()}'.

Please create one of:
  1. .sqlbot/profiles/{get_current_profile()}/models/schema.yml (recommended)
  2. profiles/{get_current_profile()}/models/schema.yml
  3. models/schema.yml (legacy)

Example setup:
  mkdir -p profiles/{get_current_profile()}/models
  # Copy your schema.yml to profiles/{get_current_profile()}/models/"""
        
        with open(schema_path, 'r') as f:
            schema_content = f.read()

        # Return the full raw content of the schema file
        # This gives the LLM complete visibility into the schema structure
        return f"""Schema file: {schema_path}

Full schema.yml content:
```yaml
{schema_content}
```"""
        
    except Exception as e:
        return f"Could not load schema: {e}"

def load_macro_info():
    """
    Load macro information with profile discovery priority:
    1. .sqlbot/profiles/{profile}/macros/ (preferred)
    2. profiles/{profile}/macros/ (fallback)
    3. macros/ (legacy)
    
    Returns:
        str: Formatted macro information for system prompt
    """
    try:
        _, macro_paths = get_profile_paths(get_current_profile())
        
        macros_path = None
        path_type = "unknown"
        
        for i, path in enumerate(macro_paths):
            if os.path.exists(path):
                macros_path = path
                if i == 0:
                    path_type = "profile (.sqlbot/profiles/)"
                elif i == 1:
                    path_type = "profile (./profiles/)"
                else:
                    path_type = "legacy (./macros/)"
                break
        
        if not macros_path:
            return f"""No macros directory found for profile '{get_current_profile()}'.

Consider creating:
  1. .sqlbot/profiles/{get_current_profile()}/macros/ (recommended)
  2. profiles/{get_current_profile()}/macros/
  3. macros/ (legacy)"""
        
        macro_info = [f"Macros directory: {macros_path}\n"]

        for filename in os.listdir(macros_path):
            if filename.endswith('.sql'):
                filepath = os.path.join(macros_path, filename)

                try:
                    with open(filepath, 'r') as f:
                        content = f.read()

                    # Return the full raw content of each macro file
                    # This gives the LLM complete visibility into the macro implementations
                    macro_info.append(f"\n--- {filename} ---")
                    macro_info.append(f"```sql")
                    macro_info.append(content)
                    macro_info.append(f"```")

                except Exception as e:
                    macro_info.append(f"• Error reading {filename}: {e}")

        return "\n".join(macro_info) if len(macro_info) > 1 else "No macros found"
        
    except Exception as e:
        return f"Could not load macros: {e}"

def extract_macro_function_names():
    """
    Extract macro function names from macro files and return them as template variables.
    This allows system prompt templates to reference individual macro functions.

    The key insight is that the system prompt template contains literal dbt macro calls
    that should be passed through to the LLM, but Jinja2 tries to interpret them as variables.
    We need to provide these as template variables so they render correctly.

    Returns:
        dict: Dictionary mapping expected template variables to their literal dbt syntax
    """
    try:
        _, macro_paths = get_profile_paths(get_current_profile())

        # Provide empty/safe values for macro functions so template renders without errors
        # These will be literally included in the final prompt for the LLM to use
        macro_functions = {}

        # Common function signatures that might appear in system prompt templates
        common_functions = [
            'find_report_by_id', 'find_report_by_session_id', 'find_report_by_form_id',
            'find_report_by_transcript_id', 'find_form_id_by_session_id', 'find_form_id_by_report_id',
            'find_session_id_by_report_id', 'find_session_id_by_form_id', 'get_transcript_by_report_id',
            'get_transcript_text_by_report_id', 'get_transcript_by_form_id', 'get_transcript_by_session_id',
            'get_all_ids_by_form_id', 'get_all_ids_by_session_id'
        ]

        # Look for actual macro definitions if macro files exist
        for macro_path in macro_paths:
            if os.path.exists(macro_path):
                for filename in os.listdir(macro_path):
                    if filename.endswith('.sql'):
                        filepath = os.path.join(macro_path, filename)

                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()

                            # Extract macro definitions using regex
                            macro_pattern = r'{% *macro +(\w+) *\((.*?)\) *%}'
                            macros = re.findall(macro_pattern, content)

                            for macro_name, params in macros:
                                # For template variables, provide the literal dbt syntax
                                # This way {{ find_report_by_id(report_id) }} in template becomes literal text
                                param_list = params.strip() if params.strip() else 'id'
                                macro_functions[f'{macro_name}({param_list})'] = f'{{{{ {macro_name}({param_list}) }}}}'

                        except Exception as e:
                            print(f"Warning: Could not parse macro file {filename}: {e}")
                            continue
                break  # Use the first existing macro path

        # If no macro files found, provide safe defaults for common functions
        if not macro_functions:
            for func_name in common_functions:
                if 'by_' in func_name:
                    param = func_name.split('by_')[-1].rstrip('_id') + '_id'
                else:
                    param = 'id'
                macro_functions[f'{func_name}({param})'] = f'{{{{ {func_name}({param}) }}}}'

        return macro_functions

    except Exception as e:
        print(f"Warning: Could not extract macro function names: {e}")
        # Return safe defaults even on error
        return {
            'find_report_by_id(report_id)': '{{ find_report_by_id(report_id) }}',
            'get_transcript_by_form_id(form_id)': '{{ get_transcript_by_form_id(form_id) }}',
        }

def build_system_prompt():
    """
    Build dynamic system prompt with current schema and macro info from profile-specific template

    Returns:
        str: Complete system prompt for the LLM
    """
    schema_info = load_schema_info()
    macro_info = load_macro_info()

    # Load profile-specific system prompt template
    profile_name = get_current_profile()
    template_content = load_profile_system_prompt_template(profile_name)

    # Extract macro function names from loaded macros to provide as template variables
    macro_functions = extract_macro_function_names()

    # Use Jinja2 to render the template with schema and macro info
    try:
        from jinja2 import Template
        template = Template(template_content)

        # Create template variables with only basic info, avoiding macro functions that contain dots
        template_vars = {
            'schema_info': schema_info,
            'macro_info': macro_info
            # Skip macro_functions to avoid Jinja2 parsing issues with dots in SQL
        }

        system_prompt = template.render(**template_vars)
        return system_prompt
    except Exception as e:
        # Enhanced fallback that handles missing template gracefully
        print(f"Warning: Template rendering failed ({e}), using fallback template")
        return f"""You are a helpful database analyst assistant.

DATABASE TABLES:
{schema_info}

AVAILABLE MACROS:
{macro_info}

Use direct table names and available macros. Always execute queries using the tool.
"""

def load_profile_system_prompt_template(profile_name: str) -> str:
    """
    Load system prompt template from profile-specific file
    
    Args:
        profile_name: Name of the profile (e.g., 'sqlbot', 'Sakila')
        
    Returns:
        str: System prompt template content
    """
    import os
    from pathlib import Path
    
    # Try profile-specific paths in order of preference
    template_paths = [
        Path(f".sqlbot/profiles/{profile_name}/system_prompt.txt"),
        Path(f"profiles/{profile_name}/system_prompt.txt"),
        Path(f"profiles/sqlbot/system_prompt.txt"),  # Fallback to default
    ]
    
    for template_path in template_paths:
        if template_path.exists():
            try:
                return template_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Warning: Could not read system prompt template from {template_path}: {e}")
                continue
    
    # Ultimate fallback - basic hardcoded template (with strict syntax guardrails)
    return """You are a helpful database analyst assistant. You help users query their database using SQL queries and dbt macros.

KEY DATABASE TABLES:
{{ schema_info }}

AVAILABLE DBT MACROS:
{{ macro_info }}

FILE EDITING CAPABILITIES:
⚠️ CRITICAL: You MUST use the edit_dbt_files tool for ALL file operations. You CANNOT create, edit, or delete files any other way.

SCHEMA FILES (schema.yml):
• Define database sources, tables, columns, and metadata
• Located in models/schema.yml within the profile directory
• MUST use edit_dbt_files tool with operations: read_schema, update_schema, delete_schema
• Always read current schema before making changes
• Maintain YAML syntax and DBT structure: version, sources, tables, columns
• Documentation: https://docs.getdbt.com/reference/source-properties

MACRO FILES (.sql):
• Reusable SQL/Jinja code snippets (like functions)
• Stored in macros/ directory as .sql files
• Syntax: {% macro name(params) %} ... {% endmacro %}
• MUST use edit_dbt_files tool with operations: list_macros, read_macro, create_macro, update_macro, delete_macro
• Use macros to avoid repeating code across queries
• Documentation: https://docs.getdbt.com/docs/build/jinja-macros

FILE EDITING WORKFLOW:
1. To CREATE a macro: Use edit_dbt_files(operation='create_macro', filename='name.sql', content='...')
2. To UPDATE a macro: Use edit_dbt_files(operation='update_macro', filename='name.sql', content='...')
3. To DELETE a macro: Use edit_dbt_files(operation='delete_macro', filename='name.sql')
4. To LIST macros: Use edit_dbt_files(operation='list_macros')
5. To READ a macro: Use edit_dbt_files(operation='read_macro', filename='name.sql')

IMPORTANT:
• NEVER say you "created" or "updated" a file unless you ACTUALLY called the edit_dbt_files tool
• ALWAYS show the user that you're using the tool by calling it
• All file operations are sandboxed to the current profile directory for security
• After creating/updating a macro, test it immediately by running a query that uses it

STRICT SYNTAX RULES (dbt + Jinja):
• ALWAYS reference tables with direct table names: film, customer, actor, rental, etc.
• NEVER use dbt source() syntax for this database - use direct table names only.
• Do NOT end inline queries with a semicolon.
• Use standard SQL LIMIT clause for row limiting: SELECT * FROM film LIMIT 10
• For counts, prefer: SELECT COUNT(*) AS row_count FROM film
• For sampling: SELECT * FROM customer LIMIT 5
• Ensure Jinja braces are balanced and source names come from the provided schema.
• If unsure about the exact source/table name, first run a small safe discovery query or ask for clarification rather than guessing.

BEHAVIOR:
• Always execute queries immediately using the provided tool; do not just propose SQL.
• Use direct table names for all table references (film, customer, actor, etc.).
• When asked to create/edit macros or schema files, ALWAYS use the edit_dbt_files tool - NEVER claim to edit files without using it.
• Focus on directly answering the user's question with the query results.
• STOP after successfully answering the question - do not perform additional analysis unless specifically requested.

RESPONSE FORMAT:
1. Briefly acknowledge the question
2. Execute the query using the tool
3. Present the results clearly and concisely
4. ONLY suggest follow-up queries if the user explicitly asks for suggestions or if the initial query was incomplete

COMPLETION CRITERIA:
• If your query successfully returns the requested data, you are DONE
• Do not perform exhaustive analysis unless specifically requested
• If a query fails with a compilation error (macro not found, undefined variable, etc.), STOP immediately and report the error to the user - do NOT retry
• If a query fails with a syntax error, you may fix it ONCE, but if it fails again, STOP and report the error
• Maximum 2 query attempts per user request - get it right or ask for clarification

ERROR HANDLING - CRITICAL INSTRUCTIONS:
• IMMEDIATELY CHECK TOOL RESULTS: After EVERY tool execution, check if "success": false or if "CRITICAL_ERROR" appears
• If you see "CRITICAL_ERROR" or "COMPILATION ERROR", you MUST STOP ALL ACTIONS and report to user
• If you see "is undefined" or "Compilation Error" in any tool result, STOP IMMEDIATELY - do NOT retry
• Compilation errors (macro not found, undefined variable, does not exist) CANNOT be fixed by retrying
• When a tool returns an error, your ONLY action is to report it to the user - do NOT execute any more queries
• NEVER say "I'll try again" or "I'll run" after seeing an error - just report the error and stop
"""

# Global counter for LLM requests in current session
llm_request_count = 0
tool_execution_happened = False

def log_llm_request():
    """Log LLM request with appropriate message"""
    global llm_request_count, tool_execution_happened
    llm_request_count += 1
    
    # Debug: Show state
    # print(f"DEBUG: LLM request #{llm_request_count}, tool_execution_happened={tool_execution_happened}")
    
    if llm_request_count == 1:
        model_name = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5').upper()
    elif tool_execution_happened:
        model_name = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5').upper()
        # Removed print statement to avoid interfering with thinking indicator
        # The thinking indicator already shows that LLM is working
    else:
        model_name = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5').upper()

class LoggingChatOpenAI(ChatOpenAI):
    """Custom ChatOpenAI that logs each request with context and shows LLM reasoning to user"""
    
    def __init__(self, *args, console=None, show_history=False, show_full_history=False, **kwargs):
        # Remove our custom fields from kwargs before passing to parent
        super().__init__(*args, **kwargs)
        # Store as private attributes after initialization
        self._console = console
        self._show_history = show_history
        self._show_full_history = show_full_history
    
    def invoke(self, input, *args, **kwargs):
        # Show conversation history before every LLM call if enabled
        if self._show_history and self._console:
            self._console.print(f"\n[bold yellow]🤖 LLM Call #{llm_request_count + 1} - Actual Prompt Context:[/bold yellow]")
            
            # Display the actual messages being sent to the LLM
            from rich.panel import Panel
            from rich.text import Text
            
            messages = input.messages if hasattr(input, 'messages') else input
            if isinstance(messages, list):
                conversation_text = Text()
                for i, msg in enumerate(messages):
                    role = getattr(msg, 'type', 'unknown')
                    content = getattr(msg, 'content', str(msg))
                    
                    # Truncate very long content for readability (unless full history is requested)
                    if not self._show_full_history and len(content) > 500:
                        content = content[:500] + "... [TRUNCATED]"
                    
                    conversation_text.append(f"[{i+1}] {role.upper()} MESSAGE:\n", style="bold yellow")
                    conversation_text.append(f"{content}\n\n", style="dim white")
                
                panel = Panel(conversation_text, title="🤖 Actual LLM Input", border_style="yellow")
                self._console.print(panel)
            else:
                # Fallback to global conversation history display
                from sqlbot.interfaces.unified_display import _display_conversation_history
                from sqlbot.conversation_memory import ConversationMemoryManager
                temp_memory_manager = ConversationMemoryManager()
                _display_conversation_history(temp_memory_manager, self._console)
        
        log_llm_request()
        
        # Display the full conversation being sent to the model
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        
        console = Console()
        
        # Extract messages from input
        if hasattr(input, 'messages'):
            messages = input.messages
        elif isinstance(input, list):
            messages = input
        else:
            messages = [input]
        
        # Create detailed conversation log
        conversation_text = Text()
        
        for i, message in enumerate(messages):
            if hasattr(message, 'type'):
                msg_type = message.type
                content = getattr(message, 'content', str(message))
            elif hasattr(message, 'role'):
                msg_type = message.role
                content = getattr(message, 'content', str(message))
            else:
                msg_type = "unknown"
                content = str(message)
            
            # Truncate content - show more for tool results, less for others
            content_str = str(content)  # Ensure content is a string
            
            if msg_type == 'tool':
                # For tool results, only truncate if really long (>2000 chars or >20 lines)
                lines = content_str.split('\n')
                if len(lines) > 20:
                    truncated_content = '\n'.join(lines[:20]) + f"\n... ({len(lines)-20} more lines)"
                elif len(content_str) > 2000:
                    truncated_content = content_str[:2000] + f"... ({len(content_str)-2000} more chars)"
                else:
                    truncated_content = content_str
            elif msg_type == 'ai':
                # For assistant messages, show full content to see complete tool calls
                truncated_content = content_str
            else:
                # For user/system messages, truncate to about 3 lines (roughly 200 characters)
                lines = content_str.split('\n')
                if len(lines) > 3:
                    truncated_content = '\n'.join(lines[:3]) + "..."
                elif len(content_str) > 200:
                    truncated_content = content_str[:200] + "..."
                else:
                    truncated_content = content_str
            
            # Style based on message type
            if msg_type == 'system':
                conversation_text.append(f"[{i+1}] SYSTEM MESSAGE:\n", style="bold red")
                conversation_text.append(f"{truncated_content}\n\n", style="red")
            elif msg_type == 'human':
                conversation_text.append(f"[{i+1}] USER MESSAGE:\n", style="bold dodger_blue2")
                conversation_text.append(f"{truncated_content}\n\n", style="dodger_blue2")
            elif msg_type == 'ai':
                conversation_text.append(f"[{i+1}] ASSISTANT MESSAGE:\n", style="bold magenta2")
                
                # Check if this assistant message contains tool calls (look for "Query:" pattern)
                if "Query:" in content_str and "Result:" in content_str:
                    # Split into reasoning and tool execution parts
                    parts = content_str.split("--- Query Details ---")
                    if len(parts) == 2:
                        reasoning_part = parts[0].strip()
                        tool_part = parts[1].strip()
                        
                        # Show reasoning first
                        if reasoning_part:
                            conversation_text.append(f"{reasoning_part[:200]}{'...' if len(reasoning_part) > 200 else ''}\n\n", style="magenta2")
                        
                        # Parse and show tool calls
                        tool_calls = tool_part.split("\n\nQuery:")
                        for j, call in enumerate(tool_calls):
                            if not call.strip():
                                continue
                            
                            # Add "Query:" back to calls after the first one
                            if j > 0:
                                call = "Query:" + call
                            
                            if "Result:" in call:
                                query_part, result_part = call.split("Result:", 1)
                                query_text = query_part.replace("Query:", "").strip()
                                result_text = result_part.strip()
                                
                                # Show tool call
                                conversation_text.append(f"  🔧 TOOL CALL: execute_dbt_query\n", style="bold cyan")
                                conversation_text.append(f"     Query: {query_text}\n", style="cyan")
                                
                                # Show tool result (truncated)
                                if len(result_text) > 500:
                                    truncated_result = result_text[:500] + "..."
                                else:
                                    truncated_result = result_text
                                conversation_text.append(f"  📊 TOOL RESULT:\n", style="bold yellow")
                                conversation_text.append(f"     {truncated_result}\n\n", style="yellow")
                    else:
                        conversation_text.append(f"{truncated_content}\n\n", style="magenta2")
                else:
                    conversation_text.append(f"{truncated_content}\n\n", style="magenta2")
            elif msg_type == 'tool':
                conversation_text.append(f"[{i+1}] TOOL RESULT:\n", style="bold yellow")
                conversation_text.append(f"{truncated_content}\n\n", style="yellow")
            else:
                conversation_text.append(f"[{i+1}] {msg_type.upper()} MESSAGE:\n", style="bold white")
                conversation_text.append(f"{truncated_content}\n\n", style="white")
        
        # Note: Conversation history display is now handled by unified display logic
        # to ensure proper timing (before thinking message) and consistent experience
        
        # Get the LLM response
        response = super().invoke(input, *args, **kwargs)
        
        # Extract and display the LLM's reasoning to the user BEFORE any tool execution
        if hasattr(response, 'content'):
            # Extract text from GPT-5 Responses API list format
            reasoning_content = ""
            for item in response.content:
                if hasattr(item, 'text'):
                    reasoning_content += item.text
                elif isinstance(item, str):
                    reasoning_content += item
                else:
                    reasoning_content += str(item)
            reasoning_content = reasoning_content.strip()
            
            # Note: Reasoning content display is now handled by unified display logic
            # to ensure consistent experience across text and Textual modes
        
        return response

def set_session_id(session_id: str):
    """Set the session ID for LLM agent creation"""
    create_llm_agent._session_id = session_id

def create_llm_agent(unified_display=None, console=None, show_history=False, show_full_history=False, event_notifier=None):
    """
    Create LangChain agent with dbt query tool for database analysis.
    
    Returns:
        AgentExecutor: Configured agent ready to handle natural language queries
    """
    try:
        # Create custom logging LLM
        model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
        max_tokens = int(os.getenv('SQLBOT_LLM_MAX_TOKENS', '50000'))
        verbosity = os.getenv('SQLBOT_LLM_VERBOSITY', 'low')
        effort = os.getenv('SQLBOT_LLM_EFFORT', 'minimal')
        
        from rich.console import Console
        console = Console()
        
        # GPT-5 supports verbosity and reasoning effort parameters via Responses API
        
        # Configure GPT-5 specific parameters for LangChain
        llm_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "api_key": os.getenv('OPENAI_API_KEY'),
            "streaming": False,
            "disable_streaming": True,
            "request_timeout": int(os.getenv('SQLBOT_LLM_REQUEST_TIMEOUT', '90')),
            "max_retries": 1
        }
        
        if model.startswith('gpt-5'):
            # GPT-5 parameters - using Responses API with LangChain 0.3.32+
            llm_kwargs["output_version"] = "responses/v1"
            llm_kwargs["extra_body"] = {
                "text": {"verbosity": verbosity},
                "reasoning": {"effort": effort}
            }
        
        llm = LoggingChatOpenAI(console=console, show_history=show_history, show_full_history=show_full_history, **llm_kwargs)
        
        # Create tools - both query execution and result lookup
        from .core.query_result_lookup_tool import create_query_result_lookup_tool
        from .core.file_editing_tool import FileEditingTool

        # Use session ID from global context or default
        session_id = getattr(create_llm_agent, '_session_id', 'default_session')

        # Get current profile for file editing tool
        profile_name = get_current_profile()

        tools = [
            DbtQueryTool(session_id, unified_display, event_notifier),
            create_query_result_lookup_tool(session_id),
            create_export_data_tool(session_id),
            FileEditingTool(profile_name)
        ]
        
        # Create dynamic prompt with current schema/macro info
        system_prompt = build_system_prompt()

        # Custom callback to track tool execution and display messages
        from langchain_core.callbacks import BaseCallbackHandler

        class ToolTrackingCallback(BaseCallbackHandler):
            def __init__(self, unified_display=None, console=None, show_history=False):
                super().__init__()
                self.unified_display = unified_display
                self.console = console
                self.show_history = show_history
                self.current_tool_name = None  # Track current tool name

            def on_llm_start(self, serialized, prompts, **kwargs):
                """Called before every LLM API call - show conversation history here"""
                pass  # History display now handled in LoggingChatOpenAI.invoke()

            def on_tool_start(self, serialized, input_str, **kwargs):
                global tool_execution_happened
                tool_execution_happened = True

                # Store tool name for use in on_tool_end
                self.current_tool_name = serialized.get("name", "Unknown tool")

                # Display tool call if we have access to unified display
                if self.unified_display:
                    if self.current_tool_name == "execute_dbt_query" and isinstance(input_str, dict):
                        query = input_str.get("query", "Unknown query")
                        self.unified_display.display_impl.display_tool_call("Database Query", query)
                    else:
                        self.unified_display.display_impl.display_tool_call(self.current_tool_name, str(input_str))

            def on_tool_end(self, output, **kwargs):
                # Display tool result if we have access to unified display
                # Skip execute_dbt_query as it handles its own result display
                if self.unified_display and output:
                    # Use stored tool name if serialized not in kwargs (langchain 1.1.0 compatibility)
                    serialized = kwargs.get('serialized', {})
                    tool_name = serialized.get('name') or self.current_tool_name or 'Unknown tool'

                    if tool_name != 'execute_dbt_query':
                        # Only display results for non-dbt tools to avoid duplicates
                        result_preview = str(output)[:200] + "..." if len(str(output)) > 200 else str(output)
                        self.unified_display.display_impl.display_tool_result(tool_name, result_preview)

        # Create agent using LangChain tool calling API
        # Note: create_agent (formerly create_tool_calling_agent) returns a runnable agent graph
        agent = create_tool_calling_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt
        )

        # Note: create_tool_calling_agent returns a graph that can be invoked directly
        # We need to adapt the interface to match the old AgentExecutor API
        # Store the callback for use during invocation
        agent._callbacks = [ToolTrackingCallback(unified_display, console, show_history)]

        return agent
        
    except Exception as e:
        logger.error(f"Failed to create LLM agent: {e}")
        raise

# Cache for dbt setup check to avoid repeated slow checks
_dbt_setup_cache = None
_dbt_setup_cache_time = 0

def handle_llm_query(query_text: str, max_retries: int = 3, timeout_seconds: int = 120, unified_display=None, show_history: bool = False, show_full_history: bool = False, event_notifier=None, chat_history=None) -> str:
    """
    Handle natural language query via LLM agent with retry logic.

    Args:
        query_text: User's natural language question about the data
        max_retries: Maximum number of retry attempts (default: 3)
        timeout_seconds: Timeout for LLM requests in seconds (default: 120)
        event_notifier: Optional callback for streaming events (for web interface)
        chat_history: Optional pre-loaded conversation history from session

    Returns:
        str: Agent's response with query results and analysis
    """
    global conversation_history, llm_request_count, tool_execution_happened
    global _dbt_setup_cache, _dbt_setup_cache_time
    
    from rich.console import Console
    import time
    console = Console()
    
    # Check dbt setup before processing query (with caching to avoid delays)
    current_time = time.time()
    if _dbt_setup_cache is None or (current_time - _dbt_setup_cache_time) > 300:  # Cache for 5 minutes
        _dbt_setup_cache = check_dbt_setup()
        _dbt_setup_cache_time = current_time
    
    dbt_configured, dbt_message = _dbt_setup_cache
    if not dbt_configured:
        console.print("🔧 [bold yellow]dbt setup issue detected...[/bold yellow]")
        console.print(dbt_message)
        return dbt_message
    
    # Retry loop for LLM requests
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                console.print(f"🔄 [yellow]Retrying LLM request (attempt {attempt + 1}/{max_retries})...[/yellow]")
            
            return _execute_llm_query(query_text, console, timeout_seconds, unified_display, show_history, show_full_history, event_notifier, chat_history)
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if this is a retryable error
            is_retryable = any(keyword in error_msg.lower() for keyword in [
                'timeout', 'connection', 'network', 'rate limit', 'server error', 
                'service unavailable', 'internal error', '500', '502', '503', '504'
            ])
            
            if attempt < max_retries - 1 and is_retryable:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                console.print(f"⚠️ [yellow]LLM request failed ({error_msg}), retrying in {wait_time}s...[/yellow]")
                import time
                time.sleep(wait_time)
                continue
            else:
                # Final attempt failed or non-retryable error
                console.print(f"❌ [red]LLM query failed after {attempt + 1} attempts: {error_msg}[/red]")
                return f"LLM query failed: {error_msg}"

def _execute_llm_query(query_text: str, console, timeout_seconds: int, unified_display=None, show_history: bool = False, show_full_history: bool = False, event_notifier=None, chat_history=None) -> str:
    """
    Execute the actual LLM query with timeout handling.

    Args:
        query_text: User's natural language question
        console: Rich console for output
        timeout_seconds: Timeout in seconds
        chat_history: Optional pre-loaded conversation history from session

    Returns:
        str: LLM response
    """
    global conversation_history, llm_request_count, tool_execution_happened, DEBUG_MODE
    
    try:
        
        model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
        import sys
        sys.stdout.flush()  # Force immediate display
        
        # Reset LLM request counter and tool tracking for new query
        llm_request_count = 0
        tool_execution_happened = False
        
        # Add user query to conversation history (check for duplicates)
        # Check if the last message is already this same user message to avoid duplicates
        if not conversation_history or conversation_history[-1].get("role") != "user" or conversation_history[-1].get("content") != query_text:
            conversation_history.append({"role": "user", "content": query_text})
        
        # Use chat_history if provided (from session), otherwise build from global conversation_history
        if chat_history is None:
            # Use the new conversation memory manager
            from .conversation_memory import ConversationMemoryManager

            # Initialize memory manager if not already done
            if not hasattr(_execute_llm_query, '_memory_manager'):
                _execute_llm_query._memory_manager = ConversationMemoryManager()

            memory_manager = _execute_llm_query._memory_manager

            # Convert our internal conversation history to LangChain format
            chat_history = []


            if len(conversation_history) > 1:
                # Removed print statement to avoid interfering with thinking indicator
                # print(f"📝 Converting {len(conversation_history)} messages to LangChain format...")

                # Clear and rebuild the memory manager's history from our conversation_history
                memory_manager.clear_history()

                # Process ALL messages in conversation history (the current query is handled separately)
                for msg in conversation_history:
                    if msg["role"] == "user":
                        memory_manager.add_user_message(msg["content"])
                    elif msg["role"] == "assistant":
                        memory_manager.add_assistant_message(msg["content"])

                # Get the processed conversation context
                chat_history = memory_manager.get_filtered_context()

            else:
                chat_history = []
        # else: chat_history was provided by the session, use it as-is
        
        
        sys.stdout.flush()  # Force immediate display
        # Create agent (fresh instance ensures latest schema/macro info)
        agent = create_llm_agent(unified_display, console, show_history, show_full_history, event_notifier)

        # Execute query with chat history (conversation history now shown by callback before each LLM call)
        # create_tool_calling_agent expects: input, chat_history, intermediate_steps
        # Pass callbacks via config parameter
        config = {}
        if hasattr(agent, '_callbacks'):
            config['callbacks'] = agent._callbacks

        # Add streaming callback if we have an event notifier
        import sys
        print(f"[DEBUG] About to check event_notifier, locals: {list(locals().keys())}", file=sys.stderr)
        if event_notifier:
            from langchain_core.callbacks import BaseCallbackHandler

            class StreamingCallback(BaseCallbackHandler):
                def __init__(self, notifier):
                    self.notifier = notifier

                def on_llm_start(self, serialized, prompts, **kwargs):
                    """Called when LLM starts generating"""
                    pass

                def on_llm_new_token(self, token, **kwargs):
                    """Called when LLM generates a new token"""
                    # For streaming token-by-token (optional enhancement)
                    pass

                def on_tool_start(self, serialized, input_str, **kwargs):
                    """Called when a tool starts executing"""
                    tool_name = serialized.get('name', 'unknown')

                    if tool_name == 'execute_dbt_query':
                        # Extract query from input
                        query = input_str
                        if isinstance(input_str, dict):
                            query = input_str.get('query', str(input_str))
                        self.notifier("message", {
                            "role": "system",
                            "content": f"🔧 Executing query:\n```sql\n{query}\n```"
                        })

                    elif tool_name == 'edit_dbt_files':
                        # Display file editing tool call with detailed debugging
                        import sys
                        print(f"[DEBUG] edit_dbt_files tool call - input_str type: {type(input_str)}, value: {input_str}", file=sys.stderr)

                        if isinstance(input_str, dict):
                            operation = input_str.get('operation', 'unknown')
                            filename = input_str.get('filename')
                            content_preview = input_str.get('content', '')[:100] if input_str.get('content') else ''

                            if operation in ['create_macro', 'update_macro', 'delete_macro'] and filename:
                                self.notifier("message", {
                                    "role": "system",
                                    "content": f"📝 {operation}: `{filename}`"
                                })
                            elif operation == 'read_macro' and filename:
                                self.notifier("message", {
                                    "role": "system",
                                    "content": f"📖 Reading macro: `{filename}`"
                                })
                            elif operation == 'list_macros':
                                self.notifier("message", {
                                    "role": "system",
                                    "content": "📂 Listing all macros..."
                                })
                            elif operation in ['read_schema', 'update_schema', 'delete_schema']:
                                self.notifier("message", {
                                    "role": "system",
                                    "content": f"📋 {operation}"
                                })
                            else:
                                self.notifier("message", {
                                    "role": "system",
                                    "content": f"🔧 File operation: {operation} (input: {str(input_str)[:200]})"
                                })
                        else:
                            # Show what we actually received for debugging
                            self.notifier("message", {
                                "role": "system",
                                "content": f"🔧 Tool call: {tool_name} (input type: {type(input_str).__name__}, value: {str(input_str)[:200]})"
                            })

                    else:
                        # Display other tool calls generically
                        self.notifier("message", {
                            "role": "system",
                            "content": f"🔧 Tool call: {tool_name}"
                        })

                def on_tool_end(self, output, **kwargs):
                    """Called when a tool finishes executing"""
                    # Get the tool name from kwargs
                    serialized = kwargs.get('serialized', {})
                    tool_name = serialized.get('name', 'unknown')

                    # Debug: log what we received
                    import sys
                    print(f"[DEBUG on_tool_end] tool_name={tool_name}, output={str(output)[:200]}, kwargs keys={list(kwargs.keys())}", file=sys.stderr)

                    # Detect edit_dbt_files by checking output content (more reliable than tool_name)
                    is_file_edit = (
                        tool_name == 'edit_dbt_files' or
                        'Successfully created macro' in str(output) or
                        'Successfully updated macro' in str(output) or
                        'Successfully deleted macro' in str(output) or
                        'Successfully updated schema' in str(output) or
                        'Successfully created' in str(output) or
                        'Successfully deleted schema' in str(output) or
                        'Macro file:' in str(output) or
                        'Schema file location:' in str(output)
                    )

                    # For edit_dbt_files, always show the result (success or failure)
                    if is_file_edit:
                        # Show the tool output
                        result_preview = str(output)[:500] if len(str(output)) > 500 else str(output)

                        # Check if it's an error
                        if 'Error' in str(output) or 'failed' in str(output).lower():
                            self.notifier("message", {
                                "role": "system",
                                "content": f"❌ File operation failed:\n```\n{result_preview}\n```"
                            })
                        else:
                            self.notifier("message", {
                                "role": "system",
                                "content": f"✅ File operation result:\n```\n{result_preview}\n```"
                            })

                            # Trigger profile refresh if the operation was successful and modified files
                            # Check if output indicates a successful create/update/delete operation
                            if any(keyword in str(output) for keyword in ['Successfully created', 'Successfully updated', 'Successfully deleted']):
                                self.notifier("profile_updated", {})

                    # For other tools (except execute_dbt_query which handles its own display)
                    elif tool_name != 'execute_dbt_query' and output:
                        result_preview = str(output)[:200] if len(str(output)) > 200 else str(output)
                        self.notifier("message", {
                            "role": "system",
                            "content": f"📊 {tool_name} result: {result_preview}"
                        })

                def on_agent_action(self, action, **kwargs):
                    """Called when agent takes an action"""
                    # Emit the agent's reasoning before tool execution
                    if hasattr(action, 'log') and action.log:
                        # Extract just the reasoning text from the log
                        log_text = action.log.strip()
                        if log_text and not log_text.startswith('\nInvoking:'):
                            self.notifier("message", {
                                "role": "assistant",
                                "content": log_text
                            })

            streaming_callback = StreamingCallback(event_notifier)
            if 'callbacks' not in config:
                config['callbacks'] = []
            config['callbacks'].append(streaming_callback)

        # Build messages list for the new create_agent API
        messages_list = []
        for msg in chat_history:
            messages_list.append(msg)
        messages_list.append({"role": "user", "content": query_text})

        result = agent.invoke(
            {"messages": messages_list},
            config=config if config else None
        )

        # Debug: Log what type of result we got
        import sys
        print(f"[DEBUG] Agent result type: {type(result)}", file=sys.stderr)
        print(f"[DEBUG] Agent result hasattr return_values: {hasattr(result, 'return_values')}", file=sys.stderr)
        if isinstance(result, dict):
            print(f"[DEBUG] Result is dict with keys: {list(result.keys())}", file=sys.stderr)

        # Extract the output from the agent result
        # create_tool_calling_agent returns an AgentFinish object with return_values
        if hasattr(result, 'return_values') and isinstance(result.return_values, dict):
            # AgentFinish object from LangChain
            raw_output = result.return_values.get("output", "No response generated")
            # intermediate_steps should be empty for AgentFinish
            intermediate_steps = []

            # Debug: Always log raw_output info to stderr
            import sys
            print(f"[DEBUG] result type = {type(result)}", file=sys.stderr)
            print(f"[DEBUG] raw_output type = {type(raw_output)}", file=sys.stderr)
            if isinstance(raw_output, list):
                print(f"[DEBUG] raw_output is list with {len(raw_output)} items", file=sys.stderr)
                for i, item in enumerate(raw_output[:3]):  # First 3 items only
                    print(f"[DEBUG]   Item {i}: type={type(item).__name__}, repr={repr(item)[:100]}", file=sys.stderr)
            else:
                print(f"[DEBUG] raw_output = {str(raw_output)[:300]}", file=sys.stderr)

            # Debug: Check if output extraction worked
            if DEBUG_MODE:
                print(f"DEBUG: result type = {type(result)}")
                print(f"DEBUG: raw_output type = {type(raw_output)}")
                print(f"DEBUG: raw_output = {str(raw_output)[:300]}")
        elif isinstance(result, dict):
            # LangChain 1.1.0 create_agent returns dict with 'messages' key
            if "messages" in result:
                # Extract the last AI message from the messages list
                messages = result["messages"]
                raw_output = None
                for msg in reversed(messages):
                    # Look for AIMessage (the last assistant response)
                    if hasattr(msg, 'type') and msg.type == 'ai':
                        raw_output = msg.content
                        break
                    elif hasattr(msg, 'role') and msg.role == 'assistant':
                        raw_output = msg.content
                        break

                if raw_output is None:
                    raw_output = "No response generated"
                intermediate_steps = []
            else:
                # Fallback: old dict format with output key
                raw_output = result.get("output", "No response generated")
                intermediate_steps = result.get("intermediate_steps", [])

            # If raw_output is a list, filter out ToolAgentAction objects
            if isinstance(raw_output, list):
                raw_output = [item for item in raw_output if type(item).__name__ != 'ToolAgentAction']
        else:
            raw_output = str(result)
            intermediate_steps = []

        # Debug logging: Log raw response structure before formatting
        if DEBUG_MODE:
            import json
            debug_log_path = os.path.join(os.path.expanduser("~"), ".sqlbot_debug.log")
            try:
                with open(debug_log_path, 'a', encoding='utf-8') as f:
                    import datetime
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"\n{'='*80}\n")
                    f.write(f"[{timestamp}] RAW LLM RESPONSE\n")
                    f.write(f"{'='*80}\n")
                    f.write(f"Query: {query_text}\n")
                    f.write(f"\nRaw output type: {type(raw_output).__name__}\n")
                    f.write(f"\nRaw output structure:\n")
                    if isinstance(raw_output, list):
                        f.write(f"List with {len(raw_output)} items:\n")
                        for i, item in enumerate(raw_output):
                            f.write(f"  [{i}] Type: {type(item).__name__}\n")
                            if hasattr(item, '__dict__'):
                                f.write(f"      Attributes: {list(item.__dict__.keys())}\n")
                            f.write(f"      String repr: {str(item)[:200]}...\n")
                    else:
                        f.write(f"String/Other:\n{str(raw_output)[:1000]}...\n")
                    f.write(f"\nFull raw_output:\n{repr(raw_output)}\n")
                    f.write(f"{'='*80}\n\n")
                    f.flush()
            except Exception as e:
                console.print(f"[dim yellow]Debug logging failed: {e}[/dim yellow]")

        # Extract response from GPT-5 Responses API format
        # For GPT-5, raw_output can be a list of response objects or a string
        if isinstance(raw_output, list):
            response = ""
            for item in raw_output:
                # Skip ToolAgentAction objects - they should not be in the user-facing response
                if type(item).__name__ == 'ToolAgentAction':
                    continue

                if hasattr(item, 'content'):
                    # Handle structured response objects
                    for content in item.content:
                        if hasattr(content, 'text'):
                            response += content.text
                elif isinstance(item, str):
                    response += item
                elif isinstance(item, dict):
                    # Handle dict items from GPT-5 Responses API
                    # Skip reasoning blocks, only extract text blocks
                    if item.get('type') == 'text' and 'text' in item:
                        response += item['text']
                else:
                    # Skip any objects that look like internal LangChain types
                    item_str = str(item)
                    if 'ToolAgentAction' in item_str or 'AgentAction' in item_str:
                        continue

                    # Fallback: try to extract text from string representation
                    if '"text":' in item_str and '"type": "text"' in item_str:
                        # Try to extract just the text content from JSON-like format
                        try:
                            import json
                            # Handle cases where the item might be a JSON string
                            if item_str.startswith('{') and item_str.endswith('}'):
                                parsed = json.loads(item_str)
                                if 'text' in parsed:
                                    response += parsed['text']
                                else:
                                    response += item_str
                            else:
                                response += item_str
                        except:
                            response += item_str
                    else:
                        response += item_str
            if not response:
                response = "No response generated"

            # Debug: Log the extracted response
            import sys
            print(f"[DEBUG] Extracted response length: {len(response)}", file=sys.stderr)
            print(f"[DEBUG] Response preview: {response[:200]}", file=sys.stderr)
        else:
            # Handle string responses - extract text if it's in GPT-5 format
            response_str = str(raw_output)
            if '"text":' in response_str and '"type": "text"' in response_str:
                try:
                    import json
                    import re
                    # Try to extract text from GPT-5 response format
                    text_matches = re.findall(r'"text":\s*"([^"]*)"', response_str)
                    if text_matches:
                        response = ' '.join(text_matches)
                    else:
                        response = response_str
                except:
                    response = response_str
            else:
                response = response_str
        
        # Capture query results from intermediate_steps for context
        query_results = []
        # Parse tool calls and results from intermediate_steps
        # intermediate_steps is a list of (AgentAction, observation) tuples
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) == 2:
                action, observation = step
                # Check if this is a query execution
                if hasattr(action, 'tool') and action.tool == 'execute_dbt_query':
                    query_executed = action.tool_input.get('query', 'Unknown query') if isinstance(action.tool_input, dict) else str(action.tool_input)
                    query_result = str(observation)

                    # Truncate large results for conversation history (unless full history is requested)
                    if not show_full_history and len(query_result) > 2000:
                        truncated_result = query_result[:1500] + f"\n\n[TRUNCATED - Original result was {len(query_result)} characters. This truncation was applied to manage conversation history size for the AI model. The user saw the complete results above.]"
                        query_results.append(f"Query: {query_executed}\nResult: {truncated_result}")
                    else:
                        query_results.append(f"Query: {query_executed}\nResult: {query_result}")
        
        # Build comprehensive response with truncated query results for history
        full_response = response
        if query_results:
            full_response = f"{response}\n\n--- Query Details ---\n" + "\n\n".join(query_results)

        # Add assistant response with query results to conversation history
        conversation_history.append({"role": "assistant", "content": full_response})

        # Limit history to last 20 messages to prevent memory bloat
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        # Save conversation to disk after each exchange
        try:
            from .conversation_persistence import save_conversation_history
            save_conversation_history(conversation_history)
        except Exception as e:
            # Don't fail the query if persistence fails
            logger.warning(f"Failed to save conversation history: {e}")

        # Return response - in web mode, return just the clean response since tool details were streamed
        # In CLI mode, return full_response with query details
        if event_notifier:
            # Web mode: tool actions already streamed, just return final clean response
            return response
        else:
            # CLI mode: return full response with query details
            return full_response
        
    except KeyboardInterrupt:
        print("\n⚠️ Query interrupted by user")
        raise  # Re-raise to be handled by retry logic
        
    except TimeoutError as e:
        print(f"⏱️ Query timed out: {str(e)}")
        raise  # Re-raise to be handled by retry logic
        
    except Exception as e:
        print(f"❌ Query failed: {str(e)}")
        raise  # Re-raise to be handled by retry logic

def test_agent():
    """Test the complete agent functionality"""
    print("=== Testing LangChain Agent ===")
    
    # Test queries of increasing complexity
    test_queries = [
        "Run a simple test query to check database connectivity",
        "How many records are in the main table?",
        "Show me a sample of calls from the last few days"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {query} ---")
        try:
            result = handle_llm_query(query)
            print("Agent Response:")
            print(result)
            print("✅ Query completed")
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    return True

if __name__ == "__main__":
    print("=== Testing Basic LLM Setup ===")
    test_llm_basic()
    
    print("\n" + "="*50)
    test_agent()
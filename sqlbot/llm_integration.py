#!/usr/bin/env python3
"""
LLM Integration for SQLBot Database Interface

Clean version with simple status messages and full query visibility.
"""

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.agents import create_tool_calling_agent, AgentExecutor
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
DBT_PROFILE_NAME = 'sqlbot'  # Default fallback

def get_current_profile():
    """Get the current dbt profile name from the global variable"""
    return DBT_PROFILE_NAME

def check_dbt_setup():
    """
    Check if dbt is properly configured and provide helpful guidance if not.
    
    Returns:
        tuple: (is_configured: bool, message: str)
    """
    try:
        # Set up environment with the profile name
        env = os.environ.copy()
        env['DBT_PROFILE_NAME'] = get_current_profile()
        
        # Run dbt debug to check configuration
        result = subprocess.run(
            ['dbt', 'debug'], 
            capture_output=True, 
            text=True, 
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            return True, "dbt is properly configured"
        
        # Parse common error messages and provide helpful guidance
        error_output = result.stderr + result.stdout
        
        if "Could not find profile" in error_output or f"profile named '{get_current_profile()}'" in error_output:
            return False, f"""
🔧 **dbt Profile Not Found**

SQLBot needs a dbt profile to connect to your database. Here's how to set it up:

**1. Create the dbt directory:**
```bash
mkdir -p ~/.dbt
```

**2. Create `~/.dbt/profiles.yml` with your database connection:**
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
        
        elif "Could not connect" in error_output or "connection" in error_output.lower():
            return False, """
🔌 **Database Connection Failed**

Your dbt profile exists but can't connect to the database. Here's how to fix it:

**1. Test your connection:**
```bash
dbt debug
```

**2. Check common issues:**
- ✅ Database server is running and accessible
- ✅ Credentials in `.env` file are correct
- ✅ Network/firewall allows database connections
- ✅ Database drivers are installed (e.g., ODBC Driver for SQL Server)

**3. Verify your `.env` file:**
```bash
DB_SERVER=your_database_server.com  # Check this hostname
DB_NAME=your_database_name          # Check this database exists
DB_USER=your_username               # Check this user exists
DB_PASS=your_password               # Check this password is correct
```

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
            return False, f"""
⚠️ **dbt Configuration Issue**

There's an issue with your dbt setup. Here's what dbt reported:

```
{error_output.strip()}
```

**Quick fixes to try:**
1. Run `dbt debug` to see detailed error information
2. Check your `~/.dbt/profiles.yml` file syntax
3. Verify your `.env` file has all required database credentials
4. Make sure your database is running and accessible

📚 **Need help?** See the README.md for detailed setup instructions.
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
    - SELECT * FROM {{{{ source('your_source', 'your_table') }}}} LIMIT 10
    - {{{{ your_macro_name(parameter) }}}}
    - SELECT column, COUNT(*) FROM {{{{ source('your_source', 'your_table') }}}} WHERE date_col >= '2024-01-01' GROUP BY column
    
    The tool will return formatted query results or error messages.
    """
    args_schema: Type[BaseModel] = DbtQueryInput
    
    def __init__(self, session_id: str = 'default_session', unified_display=None):
        """Initialize with session ID for query result tracking and unified display"""
        super().__init__()
        self._session_id = session_id
        self._unified_display = unified_display
    
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
            
            # Display tool call in real-time if we have unified display
            if self._unified_display:
                self._unified_display.display_impl.display_tool_call("Database Query", query)
                log_to_file("✅ Displayed tool call to unified display")
            
            from rich.console import Console
            console = Console()
            # Suppress database query output to avoid interfering with thinking indicator
            # The final result will be shown in the AI response
            # console.print(f"\n📡 Database query: {query}")
            
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
                
                config = SQLBotConfig(
                    profile=DBT_PROFILE_NAME,
                    read_only=safeguard_enabled,  # Use global safeguard setting
                    max_rows=1000
                )
                
                # Get dbt service and formatter
                dbt_service = get_dbt_service(config)
                formatter = ResultFormatter(console)
                
                # Perform safety check if safeguards are enabled
                safeguard_message = None
                if safeguard_enabled:
                    from .core.safety import analyze_sql_safety
                    safety_analysis = analyze_sql_safety(query, read_only_mode=True)
                    
                    if safety_analysis.is_read_only and safety_analysis.level.value == "safe":
                        # Query is safe
                        safeguard_message = "Query passes safeguard against dangerous operations."
                        if self._unified_display:
                            # Display safeguard success message
                            self._unified_display.display_impl.display_success_message(safeguard_message)
                    else:
                        # Query has dangerous operations
                        operations_str = ", ".join(safety_analysis.dangerous_operations)
                        safeguard_message = f"Query disallowed due to dangerous operations: {operations_str}"
                        
                        if self._unified_display:
                            # Display safeguard error message
                            self._unified_display.display_impl.display_error_message(safeguard_message)
                        
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
                result = dbt_service.execute_query(query)
                
                # Record the result in the query result list
                from .core.query_result_list import get_query_result_list
                
                # Use the session ID from this tool instance
                session_id = self._session_id
                result_list = get_query_result_list(session_id)
                entry = result_list.add_result(query.strip(), result)
                
                # Suppress result formatting to avoid interfering with thinking indicator
                # formatter.format_query_result(result)
                
                # Return the full data for conversation history (latest result gets full data)
                if result.success and result.data:
                    # Return full JSON data for the LLM to see
                    import json
                    # Use serialized data to handle Decimal objects
                    serialized_data = result._serialize_data(result.data)
                    result_json = json.dumps({
                        "query_index": entry.index,
                        "query": query.strip(),
                        "success": True,
                        "columns": result.columns,
                        "data": serialized_data,
                        "row_count": result.row_count,
                        "execution_time": result.execution_time
                    }, indent=2)
                    
                    # Display tool result in real-time if we have unified display
                    if self._unified_display:
                        # Show concise result summary to avoid confusing the agent
                        try:
                            row_count = result.row_count if hasattr(result, 'row_count') else len(result.data) if result.data else 0
                            result_summary = f"Success: {row_count} rows returned"
                            if result.columns and len(result.columns) <= 3:
                                result_summary += f" (columns: {', '.join(result.columns)})"
                            
                            # Pass the actual query result data for DataTable display
                            self._unified_display.display_impl.display_tool_result_with_data(
                                "Query Result", 
                                result_summary, 
                                result  # Pass the full result object
                            )
                        except Exception as e:
                            # Fallback to basic success message if result parsing fails
                            self._unified_display.display_impl.display_tool_result("Query Result", "Success: Query completed")
                    
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
                            # Include any other available error information
                            result_details = {k: v for k, v in result.__dict__.items() if v is not None and k != 'data'}
                            if result_details:
                                error_msg += f" - Details: {result_details}"
                    
                    error_result = f"Query #{entry.index} failed: {error_msg}"
                    
                    # Display tool result in real-time if we have unified display
                    if self._unified_display:
                        self._unified_display.display_impl.display_tool_result("Query Error", error_msg)
                    
                    # Suppress error output to avoid interfering with thinking indicator
                    # console.print(f"[red]❌ Query failed: {error_msg}[/red]")
                    return error_result
                    
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

def get_profile_paths(profile_name):
    """
    Get potential paths for profile configuration in priority order.
    
    Returns:
        tuple: (schema_paths, macro_paths) - lists of paths to try in order
    """
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    schema_paths = [
        # 1. Hidden .sqlbot/profiles/ (preferred)
        os.path.join(project_root, '.qbot', 'profiles', profile_name, 'models', 'schema.yml'),
        # 2. Project ./profiles/ (fallback)
        os.path.join(project_root, 'profiles', profile_name, 'models', 'schema.yml'),
        # 3. Legacy ./models/ (final fallback)
        os.path.join(project_root, 'models', 'schema.yml')
    ]
    
    macro_paths = [
        # 1. Hidden .sqlbot/profiles/ (preferred)
        os.path.join(project_root, '.qbot', 'profiles', profile_name, 'macros'),
        # 2. Project ./profiles/ (fallback)
        os.path.join(project_root, 'profiles', profile_name, 'macros'),
        # 3. Legacy ./macros/ (final fallback)
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
            schema_data = yaml.safe_load(f)
        
        schema_info = []
        
        # Process sources
        for source in schema_data.get('sources', []):
            source_name = source.get('name', 'unknown')
            schema_info.append(f"\nSource: {source_name}")
            
            for table in source.get('tables', []):
                table_name = table.get('name', 'unknown')
                table_desc = table.get('description', 'No description available')
                schema_info.append(f"  - {table_name}: {table_desc}")
                
                # Add column info if available
                columns = table.get('columns', [])
                if columns:
                    schema_info.append(f"    Columns:")
                    for col in columns[:10]:  # Limit to first 10 columns
                        col_name = col.get('name', 'unknown')
                        col_desc = col.get('description', 'No description')
                        schema_info.append(f"      • {col_name}: {col_desc}")
                    if len(columns) > 10:
                        schema_info.append(f"      ... and {len(columns) - 10} more columns")
        
        return "\n".join(schema_info) if schema_info else "No schema information available"
        
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
        
        macro_info = []
        
        for filename in os.listdir(macros_path):
            if filename.endswith('.sql'):
                filepath = os.path.join(macros_path, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Extract macro definitions using regex
                    # Pattern matches: {% macro macro_name(param1, param2) %}
                    macro_pattern = r'{% *macro +(\w+) *\((.*?)\) *%}(.*?){% *endmacro *%}'
                    macros = re.findall(macro_pattern, content, re.DOTALL)
                    
                    for macro_name, params, macro_body in macros:
                        # Extract any comments from the macro body
                        comment_match = re.search(r'-- *(.*)', macro_body)
                        description = comment_match.group(1).strip() if comment_match else "No description"
                        
                        macro_info.append(f"• {macro_name}({params})")
                        macro_info.append(f"  Description: {description}")
                        macro_info.append(f"  Usage: {{{{ {macro_name}({params}) }}}}")
                        macro_info.append("")
                        
                except Exception as e:
                    macro_info.append(f"• Error reading {filename}: {e}")
        
        return "\n".join(macro_info) if macro_info else "No macros found"
        
    except Exception as e:
        return f"Could not load macros: {e}"

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
    
    # Use Jinja2 to render the template with schema and macro info
    try:
        from jinja2 import Template
        template = Template(template_content)
        system_prompt = template.render(
            schema_info=schema_info,
            macro_info=macro_info
        )
        return system_prompt
    except Exception as e:
        # Fallback to basic template if Jinja2 fails
        return f"""You are a helpful database analyst assistant.

DATABASE TABLES:
{schema_info}

AVAILABLE MACROS:
{macro_info}

Use dbt source() syntax: {{{{ source('your_source', 'table_name') }}}} and always execute queries using the tool.
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

STRICT SYNTAX RULES (dbt + Jinja):
• ALWAYS reference tables via dbt sources with EXACTLY double braces: {{ source('source_name', 'table_name') }}
• NEVER output quadruple braces (e.g., {{{{ … }}}}) or single-brace forms (e.g., { source(…) }).
• Do NOT end inline queries with a semicolon.
• Do NOT include pagination keywords (TOP or LIMIT). Pagination is handled by the executor.
• For counts, prefer: SELECT COUNT(*) AS row_count FROM {{ source('s', 't') }}
• For sampling: SELECT * FROM {{ source('s', 't') }}  (no TOP/LIMIT)
• Ensure Jinja braces are balanced and source names come from the provided schema.
• If unsure about the exact source/table name, first run a small safe discovery query or ask for clarification rather than guessing.

BEHAVIOR:
• Always execute queries immediately using the provided tool; do not just propose SQL.
• Use dbt source() syntax for all table references.
• Focus on concise analysis and actionable follow-ups rather than restating result rows.

RESPONSE FORMAT:
1. Briefly acknowledge the question
2. Execute the query using the tool
3. Provide concise analysis of results
4. Suggest logical follow-up queries if relevant
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
    
    def __init__(self, *args, console=None, show_history=False, **kwargs):
        # Remove our custom fields from kwargs before passing to parent
        super().__init__(*args, **kwargs)
        # Store as private attributes after initialization
        self._console = console
        self._show_history = show_history
    
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
                    
                    # Truncate very long content for readability
                    if len(content) > 500:
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

def create_llm_agent(unified_display=None, console=None, show_history=False):
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
        
        llm = LoggingChatOpenAI(console=console, show_history=show_history, **llm_kwargs)
        
        # Create tools - both query execution and result lookup
        from .core.query_result_lookup_tool import create_query_result_lookup_tool
        
        # Use session ID from global context or default
        session_id = getattr(create_llm_agent, '_session_id', 'default_session')
        
        tools = [
            DbtQueryTool(session_id, unified_display),
            create_query_result_lookup_tool(session_id)
        ]
        
        # Create dynamic prompt with current schema/macro info
        system_prompt = build_system_prompt()
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Create agent (ensure no streaming)
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # Custom callback to track tool execution and display messages
        from langchain_core.callbacks import BaseCallbackHandler
        
        class ToolTrackingCallback(BaseCallbackHandler):
            def __init__(self, unified_display=None, console=None, show_history=False):
                super().__init__()
                self.unified_display = unified_display
                self.console = console
                self.show_history = show_history
                
            def on_llm_start(self, serialized, prompts, **kwargs):
                """Called before every LLM API call - show conversation history here"""
                pass  # History display now handled in LoggingChatOpenAI.invoke()
                
            def on_tool_start(self, serialized, input_str, **kwargs):
                global tool_execution_happened
                tool_execution_happened = True
                
                # Display tool call if we have access to unified display
                if self.unified_display:
                    tool_name = serialized.get("name", "Unknown tool")
                    if tool_name == "execute_dbt_query" and isinstance(input_str, dict):
                        query = input_str.get("query", "Unknown query")
                        self.unified_display.display_impl.display_tool_call("Database Query", query)
                    else:
                        self.unified_display.display_impl.display_tool_call(tool_name, str(input_str))
            
            def on_tool_end(self, output, **kwargs):
                # Display tool result if we have access to unified display
                if self.unified_display and output:
                    # Truncate long results for display
                    result_preview = str(output)[:200] + "..." if len(str(output)) > 200 else str(output)
                    self.unified_display.display_impl.display_tool_result("Query Result", result_preview)
                
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=False,  # Disable verbose to prevent raw JSON output
            max_iterations=20,  # Allow more iterations but let agent decide when to stop
            handle_parsing_errors=True,
            callbacks=[ToolTrackingCallback(unified_display, console, show_history)],
            return_intermediate_steps=True  # Ensure tool results are available to agent
        )
        
        return agent_executor
        
    except Exception as e:
        logger.error(f"Failed to create LLM agent: {e}")
        raise

# Cache for dbt setup check to avoid repeated slow checks
_dbt_setup_cache = None
_dbt_setup_cache_time = 0

def handle_llm_query(query_text: str, max_retries: int = 3, timeout_seconds: int = 120, unified_display=None, show_history: bool = False) -> str:
    """
    Handle natural language query via LLM agent with retry logic.
    
    Args:
        query_text: User's natural language question about the data
        max_retries: Maximum number of retry attempts (default: 3)
        timeout_seconds: Timeout for LLM requests in seconds (default: 120)
        
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
            
            return _execute_llm_query(query_text, console, timeout_seconds, unified_display, show_history)
            
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

def _execute_llm_query(query_text: str, console, timeout_seconds: int, unified_display=None, show_history: bool = False) -> str:
    """
    Execute the actual LLM query with timeout handling.
    
    Args:
        query_text: User's natural language question
        console: Rich console for output
        timeout_seconds: Timeout in seconds
        
    Returns:
        str: LLM response
    """
    global conversation_history, llm_request_count, tool_execution_happened
    
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
        
        
        sys.stdout.flush()  # Force immediate display
        # Create agent (fresh instance ensures latest schema/macro info)  
        agent = create_llm_agent(unified_display, console, show_history)
        
        # Execute query with chat history (conversation history now shown by callback before each LLM call)
        result = agent.invoke({
            "input": query_text,
            "chat_history": chat_history
        })
        
        # Extract intermediate steps (tool calls and results) for conversation history
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Add tool calls and results to conversation history
        for i, (action, observation) in enumerate(intermediate_steps):
            tool_name = getattr(action, 'tool', 'unknown_tool')
            tool_input = getattr(action, 'tool_input', {})
            
            # Add tool call to conversation history
            conversation_history.append({
                "role": "assistant", 
                "content": f"🔧 TOOL CALL: {tool_name}\nInput: {tool_input}\n\n📊 TOOL RESULT:\n{observation}"
            })
        
        # Extract the final answer and intermediate steps
        # Handle both string and list responses (Responses API may return different format)
        raw_output = result.get("output", "No response generated")
        
        # Extract response from GPT-5 Responses API format
        if isinstance(raw_output, list):
            response = ""
            for item in raw_output:
                if hasattr(item, 'content'):
                    # Handle structured response objects
                    for content in item.content:
                        if hasattr(content, 'text'):
                            response += content.text
                elif isinstance(item, str):
                    response += item
                else:
                    # For GPT-5 Responses API, extract text from response objects
                    item_str = str(item)
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
        
        # Capture query results from intermediate steps for context
        query_results = []
        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2 and hasattr(step[0], 'tool') and step[0].tool == "execute_dbt_query":
                    # Extract the query and result
                    query_executed = step[0].tool_input.get('query', 'Unknown query')
                    query_result = step[1] if len(step) > 1 else 'No result'
                    
                    # Truncate large results for conversation history
                    if len(query_result) > 2000:
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
        
        # Return the full response including tool call details for display
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
import warnings
# Suppress import warnings that appear before banner
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")
warnings.filterwarnings("ignore", message=".*found in sys.modules.*")
# Note: LangChain deprecation warnings have been resolved by updating to modern API

from dotenv import load_dotenv
import os
import sys
import readline
import atexit
# dbt imports moved to after banner display
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.pretty import install as rich_install
from rich import print as rprint
import tempfile
from sqlbot.interfaces.theme_system import get_theme_manager, ThemeMode

# Note: We use dbt for all database connections, no direct pyodbc needed

load_dotenv()

# Theme-aware messaging system that uses the global theme manager
class MessageStyle:
    """Theme-aware colors that change based on selected theme"""
    
    @staticmethod
    def get_user_style():
        theme = get_theme_manager()
        color = theme.get_color('user_message') or 'blue'
        return f"[bold {color}]"
    
    @staticmethod  
    def get_llm_style():
        theme = get_theme_manager()
        color = theme.get_color('ai_response') or 'magenta'
        return f"[bold {color}]"
    
    @staticmethod
    def get_database_style():
        theme = get_theme_manager()
        color = theme.get_color('info_message') or 'blue'
        return f"[bold {color}]"
    
    @staticmethod
    def get_system_style():
        theme = get_theme_manager()
        color = theme.get_color('system_message') or 'cyan'
        return f"[{color}]"
    
    # Dynamic properties that update with theme changes
    @property
    def USER(self):
        return MessageStyle.get_user_style()
    
    @property
    def LLM(self):
        return MessageStyle.get_llm_style()
    
    @property
    def DATABASE(self):
        return MessageStyle.get_database_style()
    
    @property
    def SYSTEM(self):
        return MessageStyle.get_system_style()

# Create a global instance to use throughout the file
message_style = MessageStyle()

# Theme-aware helper functions for common colors
def get_error_style():
    theme = get_theme_manager()
    color = theme.get_color('error_message')
    return color if isinstance(color, str) else 'red'

def get_success_style():
    theme = get_theme_manager()
    color = theme.get_color('success_message')
    return color if isinstance(color, str) else 'green'

def get_warning_style():
    theme = get_theme_manager()
    color = theme.get_color('warning_message')
    return color if isinstance(color, str) else 'yellow'

def get_info_style():
    theme = get_theme_manager()
    color = theme.get_color('info_message')
    return color if isinstance(color, str) else 'blue'

# Direct SQL connection functions removed - we use dbt for all database operations
# This ensures consistent behavior, proper source() references, and profile-based configuration

# LLM Integration
try:
    # Try relative import first (when run as module)
    from .llm_integration import handle_llm_query
    LLM_AVAILABLE = True
    pass  # LLM integration loaded - will show message later
except ImportError:
    try:
        # Fallback to absolute import (when run as script)
        from llm_integration import handle_llm_query
        LLM_AVAILABLE = True
        pass  # LLM integration loaded - will show message later
    except ImportError as e:
        LLM_AVAILABLE = False
        print(f"⚠️  LLM integration not available: {e}")
        print("   Install: pip install langchain langchain-openai python-dotenv")

# Initialize Rich console
rich_console = Console()
rich_install()  # Enable rich pretty printing

# Set up command history
HISTORY_FILE = Path.home() / '.qbot_history'
HISTORY_LENGTH = 100

# Global dbt profile configuration
DBT_PROFILE_NAME = 'sqlbot'  # Default profile name, can be overridden via --profile

# Global flags
READONLY_MODE = True  # Default to safeguard mode enabled
READONLY_CLI_MODE = False  # Track if --dangerous was used to disable safeguards
PREVIEW_MODE = False
SHOW_HISTORY = False  # Show conversation history panel
SHOW_FULL_HISTORY = False  # Show full conversation history without truncation

def setup_history():
    """Setup readline history with persistent storage"""
    try:
        # Set up history file and length
        readline.set_history_length(HISTORY_LENGTH)
        
        # Try to read existing history
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
        
        # Register function to save history on exit
        atexit.register(save_history)
        
    except Exception as e:
        # Readline might not be available on all systems
        rich_console.print(f"[dim yellow]Warning: Command history not available: {e}[/dim yellow]")

def save_history():
    """Save command history to file"""
    try:
        # Save only the last HISTORY_LENGTH commands
        readline.set_history_length(HISTORY_LENGTH)
        readline.write_history_file(str(HISTORY_FILE))
    except Exception:
        pass  # Silently fail if we can't save history

# Banner will be shown later when console starts

# Initialize dbt runner
# dbt and PROJECT_ROOT will be initialized later after banner
dbt = None
PROJECT_ROOT = Path(__file__).parent

def run_dbt(command_args):
    """Execute dbt command and return results"""
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    
    try:
        result = dbt.invoke(command_args)
        
        if result.success:
            print(f"✓ dbt {' '.join(command_args)} completed successfully")
            
            # Show results for certain commands
            if hasattr(result, 'result') and result.result:
                if command_args[0] in ['run', 'test', 'compile']:
                    for r in result.result:
                        if hasattr(r, 'node') and hasattr(r, 'status'):
                            status_icon = "✓" if r.status == "success" else "✗"
                            print(f"  {status_icon} {r.node.name}: {r.status}")
                elif command_args[0] == 'list':
                    for item in result.result:
                        print(f"  - {item}")
        else:
            print(f"✗ dbt command failed: {result.exception}")
        
        return result
    except Exception as e:
        print(f"Error executing dbt command: {e}")
        return None
    finally:
        os.chdir(original_dir)

# Convenience functions for common dbt operations
def dbt_debug():
    """Check dbt connection"""
    return run_dbt(["debug"])

def dbt_run(select=None):
    """Run dbt models"""
    cmd = ["run"]
    if select:
        cmd.extend(["--select", select])
    return run_dbt(cmd)

def dbt_test(select=None):
    """Run dbt tests"""
    cmd = ["test"]
    if select:
        cmd.extend(["--select", select])
    return run_dbt(cmd)

def dbt_compile(select=None):
    """Compile dbt models"""
    cmd = ["compile"]
    if select:
        cmd.extend(["--select", select])
    return run_dbt(cmd)

def dbt_list(resource_type=None):
    """List dbt resources"""
    cmd = ["list"]
    if resource_type:
        cmd.extend(["--resource-type", resource_type])
    return run_dbt(cmd)

def dbt_show(model, limit=10):
    """Show model results"""
    return run_dbt(["show", "--select", model, "--limit", str(limit)])

def dbt_docs_generate():
    """Generate dbt documentation"""
    return run_dbt(["docs", "generate"])

def dbt_docs_serve():
    """Serve dbt documentation"""
    return run_dbt(["docs", "serve"])

def execute_clean_sql(sql_query):
    """Execute SQL query using dbt SDK (no subprocess)"""
    try:
        # Use dbt service SDK instead of subprocess
        import os
        from sqlbot.core.dbt_service import get_dbt_service
        from sqlbot.core.config import SQLBotConfig
        
        # Get dbt service with current profile configuration
        # Get the current profile name - try to import from llm_integration if available
        try:
            from . import llm_integration
            profile_name = llm_integration.get_current_profile()
        except ImportError:
            try:
                import llm_integration
                profile_name = llm_integration.get_current_profile()
            except ImportError:
                profile_name = os.getenv('SQLBOT_PROFILE')
        
        config = SQLBotConfig.from_env(profile=profile_name)
        dbt_service = get_dbt_service(config)
        
        # Execute query using SDK - macro prevents dbt from adding LIMIT
        result = dbt_service.execute_query(sql_query)
        
        if result.success:
            # Format results as table output
            if result.data and result.columns:
                # Create table output similar to dbt show
                output_lines = []
                
                # Header row
                header = "| " + " | ".join(result.columns) + " |"
                output_lines.append(header)
                
                # Separator row
                separator = "| " + " | ".join(["-" * len(col) for col in result.columns]) + " |"
                output_lines.append(separator)
                
                # Data rows
                for row in result.data:
                    row_values = [str(row.get(col, "")) for col in result.columns]
                    row_line = "| " + " | ".join(row_values) + " |"
                    output_lines.append(row_line)
                
                return "\n".join(output_lines)
            else:
                return f"Query executed successfully. Rows affected: {result.row_count}"
        else:
            return f"Error executing query: {result.error}"
    except Exception as e:
        return f"Failed to execute query: {str(e)}"


def preview_sql_compilation(sql_query):
    """Preview compiled SQL without executing it using dbt SDK"""
    try:
        # Use dbt service SDK for compilation preview
        from sqlbot.core.dbt_service import get_dbt_service
        from sqlbot.core.config import SQLBotConfig
        
        # Get dbt service with current configuration
        config = SQLBotConfig()
        dbt_service = get_dbt_service(config)
        
        # Use the new SDK compilation method
        result = dbt_service.compile_query_preview(sql_query)
        
        if result.success:
            return result.compiled_sql
        else:
            return f"Error compiling query: {result.error}"
    except Exception as e:
        return f"Failed to compile query: {str(e)}"

def analyze_sql_safety(sql_query):
    """Analyze SQL query for dangerous operations that modify data."""
    import re
    
    # Remove comments first
    normalized_sql = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)  # Remove line comments
    normalized_sql = re.sub(r'/\*.*?\*/', '', normalized_sql, flags=re.DOTALL)  # Remove block comments
    
    # Remove string literals to avoid false positives
    # Handle both single and double quoted strings
    normalized_sql = re.sub(r"'[^']*'", "''", normalized_sql)  # Remove single-quoted strings
    normalized_sql = re.sub(r'"[^"]*"', '""', normalized_sql)  # Remove double-quoted strings
    
    # Normalize whitespace and case
    normalized_sql = re.sub(r'\s+', ' ', normalized_sql).strip().upper()
    
    # Define dangerous operations
    dangerous_operations = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'MERGE', 'REPLACE', 'GRANT', 'REVOKE'
    ]
    
    found_dangers = []
    for operation in dangerous_operations:
        # Look for the operation as a standalone word (not part of another word)
        pattern = r'\b' + operation + r'\b'
        if re.search(pattern, normalized_sql):
            found_dangers.append(operation)
    
    return {
        'is_safe': len(found_dangers) == 0,
        'dangerous_operations': found_dangers,
        'normalized_sql': normalized_sql
    }

def execute_safe_sql(sql_query, force_execute=False):
    """Execute SQL with preview and read-only safety checks if enabled."""
    global READONLY_MODE, READONLY_CLI_MODE, PREVIEW_MODE
    
    # Check PREVIEW_MODE first
    if PREVIEW_MODE:
        # Show preview of the SQL that will be executed
        rich_console.print("SQL Preview:")
        rich_console.print("─" * 60)
        rich_console.print(f"[dim]Query:[/dim] {sql_query.strip()}")
        
        # Show compiled version if it contains Jinja
        if '{{' in sql_query and '}}' in sql_query:
            compiled_preview = preview_sql_compilation(sql_query.strip())
            rich_console.print(f"[dim]Compiled:[/dim]")
            rich_console.print(compiled_preview)
        
        rich_console.print("─" * 60)
        
        # Ask for execution approval
        try:
            # Check if stdin is available for input
            if not sys.stdin.isatty():
                # No interactive terminal - auto-approve
                rich_console.print("\n[dim]Auto-approving (no interactive terminal)[/dim]")
            else:
                execute = input("\n🤔 Execute this SQL query? (y/n): ").strip().lower()
                if execute not in ['y', 'yes']:
                    rich_console.print(f"[{get_warning_style()}]SQL execution cancelled.[/{get_warning_style()}]")
                    return "SQL execution cancelled by user in preview mode"
        except (KeyboardInterrupt, EOFError, OSError):
            rich_console.print(f"\n[{get_warning_style()}]SQL execution cancelled.[/{get_warning_style()}]")
            return "SQL execution cancelled by user in preview mode"
        
        rich_console.print("Executing SQL...")
    
    # If safeguard mode is disabled (dangerous mode), execute directly
    if not READONLY_MODE:
        return execute_clean_sql(sql_query)
    
    # Analyze query safety
    safety_analysis = analyze_sql_safety(sql_query)
    
    if not safety_analysis['is_safe'] and not force_execute:
        # Query contains dangerous operations
        operations = ', '.join(safety_analysis['dangerous_operations'])
        
        # Block dangerous operations - show only the clean safeguard message
        rich_console.print(f"[{get_error_style()}]✖[/{get_error_style()}] Query disallowed due to dangerous operations: {operations}")
        return "Query blocked by safeguard"
    else:
        # Query is safe, execute normally
        rich_console.print(f"[{get_success_style()}]✔[/{get_success_style()}] Query passes safeguard against dangerous operations.")
        return execute_clean_sql(sql_query)

def execute_dbt_sql(sql_query):
    """Execute SQL query with dbt context and Jinja processing - now uses clean approach"""
    return execute_clean_sql(sql_query)

def execute_dbt_sql_unlimited(sql_query):
    """Execute SQL query with dbt context, showing more results - now uses clean approach"""
    return execute_clean_sql(sql_query)

def handle_slash_command(line):
    """Handle slash commands like /debug, /run, etc."""
    if not line.startswith('/'):
        return None
    
    # Remove the '/' and split into command and args
    parts = line[1:].strip().split()
    if not parts:
        return None
    
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    if command == 'debug':
        return dbt_debug()
    elif command == 'run':
        if args:
            return dbt_run(args[0])
        return dbt_run()
    elif command == 'test':
        if args:
            return dbt_test(args[0])
        return dbt_test()
    elif command == 'compile':
        if args:
            return dbt_compile(args[0])
        return dbt_compile()
    elif command == 'list':
        resource_type = args[0] if args else None
        return dbt_list(resource_type)
    elif command == 'show':
        if not args:
            print("Usage: /show model_name [limit]")
            return
        model = args[0]
        limit = int(args[1]) if len(args) > 1 else 10
        return dbt_show(model, limit)
    elif command == 'docs':
        if args and args[0] == 'serve':
            return dbt_docs_serve()
        return dbt_docs_generate()
    elif command == 'dbt':
        if not args:
            print("Usage: /dbt command [args...]")
            return
        return run_dbt(args)
    elif command == 'history':
        # Show command history
        try:
            history_table = Table(
                title="📜 Command History", 
                border_style="purple",
                width=rich_console.width,
                expand=True
            )
            history_table.add_column("#", style="dim magenta2", width=5)
            history_table.add_column("Command", style="bold purple")
            
            # Get history length and display recent commands
            history_length = readline.get_current_history_length()
            start_idx = max(0, history_length - 20)  # Show last 20 commands
            
            for i in range(start_idx, history_length):
                cmd = readline.get_history_item(i + 1)  # readline uses 1-based indexing
                if cmd:
                    history_table.add_row(str(i + 1), cmd)
            
            rich_console.print(history_table)
        except Exception as e:
            rich_console.print(f"[red]History not available: {e}[/red]")
        return
    elif command == 'help':
        help_table = Table(
            title="🔧 SQLBot Database Interface Commands", 
            border_style="purple",
            width=rich_console.width,
            expand=True
        )
        help_table.add_column("Command", style="bold magenta2", width=25)
        help_table.add_column("Description", style="dim white")
        
        help_table.add_row("/debug", "Check dbt connection")
        help_table.add_row("/run [model]", "Run all models or specific model")
        help_table.add_row("/test [model]", "Run all tests or specific model tests")
        help_table.add_row("/compile [model]", "Compile models")
        help_table.add_row("/list [type]", "List resources (models, tests, etc.)")
        help_table.add_row("/show model [limit]", "Show model data")
        help_table.add_row("/docs [serve]", "Generate docs or serve docs")
        help_table.add_row("/dbt command args...", "Run any dbt command")
        help_table.add_row("[bold green]Natural language[/bold green]", "[bold green]Ask questions in plain English (default)[/bold green]")
        help_table.add_row("[bold blue]SQL with ;[/bold blue]", "[bold blue]End with semicolon to run as dbt SQL[/bold blue]")
        help_table.add_row("/preview", "Preview compiled SQL before execution")
        help_table.add_row("/dangerous", "Toggle dangerous mode (disables safeguards)")
        help_table.add_row("/history", "Toggle conversation history display")
        help_table.add_row("/help", "Show this help")
        help_table.add_row("/no-repl", "Exit interactive mode")
        help_table.add_row("/exit", "Exit console")
        
        rich_console.print(help_table)
        return
    elif command == 'preview':
        return handle_preview_command(args)
    elif command == 'dangerous':
        return handle_dangerous_command(args)
    elif command == 'history':
        return handle_history_command(args)
    elif command == 'no-repl':
        rich_console.print("[dim]Exiting interactive mode...[/dim]")
        return 'EXIT'
    elif command == 'exit':
        return 'EXIT'
    else:
        print(f"Unknown command: /{command}")
        print("Type /help for available commands")
        return

def handle_double_slash_command(line):
    """Handle double-slash commands like //preview"""
    if not line.startswith('//'):
        return None
    
    # Remove the '//' and split into command and args
    parts = line[2:].strip().split()
    if not parts:
        return None
    
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    if command == 'preview':
        return handle_preview_command(args)
    elif command == 'dangerous':
        return handle_dangerous_command(args)
    else:
        print(f"Unknown double-slash command: //{command}")
        print("Available double-slash commands:")
        print("  //preview - Preview compiled SQL before execution")
        print("  //dangerous - Toggle dangerous mode (disables safeguards)")
        return

def handle_preview_command(args):
    """Handle the //preview command - shows compiled SQL and prompts for execution"""
    rich_console.print(f"🔍 [bold {get_theme_manager().get_color('ai_response')}]Preview Mode[/bold {get_theme_manager().get_color('ai_response')}] - Enter SQL to preview compilation:")

    # Check if stdin is available for interactive input
    if not sys.stdin.isatty():
        rich_console.print("[dim]Preview command requires interactive terminal[/dim]")
        return

    try:
        # Get SQL query from user
        sql_query = input("SQL> ").strip()
        
        if not sql_query:
            rich_console.print("[yellow]No query provided.[/yellow]")
            return
        
        # Show compiled SQL preview
        rich_console.print("\nCompiled SQL Preview:")
        rich_console.print("─" * 60)
        
        compiled_result = preview_sql_compilation(sql_query)
        rich_console.print(compiled_result)
        
        rich_console.print("─" * 60)
        
        # Ask for execution approval
        try:
            execute = input("\n🤔 Execute this query? (y/n): ").strip().lower()
            if execute in ['y', 'yes']:
                rich_console.print("\nExecuting query...")
                # Use safe execution with read-only safeguard
                result = execute_safe_sql(sql_query)
                rich_console.print(result)
            else:
                rich_console.print("[yellow]Query execution cancelled.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            rich_console.print("\n[yellow]Query execution cancelled.[/yellow]")
        
    except (KeyboardInterrupt, EOFError):
        rich_console.print("\n[yellow]Preview cancelled.[/yellow]")
        return

def handle_dangerous_command(args):
    """Handle the /dangerous command - toggle dangerous mode (disables safeguards)."""
    global READONLY_MODE
    
    if not args:
        # Show current status
        if READONLY_MODE:
            # Safeguards are enabled (safe mode)
            rich_console.print("🔒 [bold green]Safeguards are ENABLED[/bold green]")
            rich_console.print("[dim]Dangerous operations are blocked.[/dim]")
            rich_console.print("[dim]Use '/dangerous on' to disable safeguards.[/dim]")
        else:
            # Safeguards are disabled (dangerous mode)
            rich_console.print("⚠️  [bold red]Dangerous mode is ENABLED[/bold red]")
            rich_console.print("[dim]All operations allowed - safeguards disabled.[/dim]")
            rich_console.print("[dim]Use '/dangerous off' to re-enable safeguards.[/dim]")
    elif args[0].lower() in ['on', 'enable', 'true']:
        READONLY_MODE = False  # Disable safeguards = enable dangerous mode
        rich_console.print("⚠️  [bold red]Dangerous mode ENABLED[/bold red]")
        rich_console.print("[dim]Safeguards are DISABLED - all operations allowed.[/dim]")
    elif args[0].lower() in ['off', 'disable', 'false']:
        READONLY_MODE = True   # Enable safeguards = disable dangerous mode
        rich_console.print("🔒 [bold green]Safeguards ENABLED[/bold green]")
        rich_console.print("[dim]Dangerous operations blocked.[/dim]")
    else:
        rich_console.print(f"[red]Unknown dangerous option: {args[0]}[/red]")
        rich_console.print("Usage: /dangerous [on|off]")

# Safeguard command with opposite semantics from dangerous command
def handle_safeguard_command(args):
    """Handle the /safeguard command - toggle safeguard mode (opposite of dangerous command)."""
    global READONLY_MODE
    
    if not args:
        # Show current status
        if READONLY_MODE:
            rich_console.print("🔒 [bold green]Safeguards are ENABLED[/bold green]")
            rich_console.print("[dim]Dangerous operations are blocked.[/dim]")
        else:
            rich_console.print("⚠️  [bold red]Safeguards are DISABLED[/bold red]")
            rich_console.print("[dim]All operations allowed - dangerous mode active.[/dim]")
    elif args[0].lower() in ['on', 'enable', 'true']:
        READONLY_MODE = True   # Enable safeguards
        rich_console.print("🔒 [bold green]Safeguards ENABLED[/bold green]")
        rich_console.print("[dim]Dangerous operations blocked.[/dim]")
    elif args[0].lower() in ['off', 'disable', 'false']:
        READONLY_MODE = False  # Disable safeguards
        rich_console.print("⚠️  [bold red]Safeguards DISABLED[/bold red]")
        rich_console.print("[dim]All operations allowed - dangerous mode active.[/dim]")
    else:
        rich_console.print(f"[red]Unknown safeguard option: {args[0]}[/red]")
        rich_console.print("Usage: /safeguard [on|off]")

def handle_history_command(args):
    """Handle the /history command - toggle conversation history display."""
    global SHOW_HISTORY
    
    if not args:
        # Show current status
        status = "ON" if SHOW_HISTORY else "OFF"
        rich_console.print(f"[bold blue]Conversation history display: {status}[/bold blue]")
        if SHOW_HISTORY:
            rich_console.print("[dim]LLM conversation history will be shown during queries.[/dim]")
        else:
            rich_console.print("[dim]LLM conversation history will be hidden.[/dim]")
        rich_console.print("[dim]Use '/history on' or '/history off' to change.[/dim]")
    elif args[0].lower() in ['on', 'enable', 'true']:
        SHOW_HISTORY = True
        rich_console.print("[bold green]Conversation history display ENABLED[/bold green]")
        rich_console.print("[dim]LLM conversation history will be shown during queries.[/dim]")
    elif args[0].lower() in ['off', 'disable', 'false']:
        SHOW_HISTORY = False
        rich_console.print("[bold yellow]Conversation history display DISABLED[/bold yellow]")
        rich_console.print("[dim]LLM conversation history will be hidden.[/dim]")
    else:
        rich_console.print(f"[red]Unknown history option: {args[0]}[/red]")
        rich_console.print("Usage: /history [on|off]")

def start_console():
    """Legacy function for backward compatibility with tests."""
    # This function exists for test compatibility but delegates to unified REPL
    from sqlbot.interfaces.unified_display import execute_query_with_unified_display
    from sqlbot.conversation_memory import ConversationMemoryManager
    
    # Show banner for interactive mode (even in test environment)
    profile = os.getenv('DBT_PROFILE_NAME')
    show_banner(is_no_repl=False, profile=profile, llm_model=None, llm_available=LLM_AVAILABLE)
    
    # Create memory manager and execution function
    memory_manager = ConversationMemoryManager()
    def execute_llm_func(q: str) -> str:
        global SHOW_HISTORY, SHOW_FULL_HISTORY
        timeout_seconds = int(os.getenv('SQLBOT_LLM_TIMEOUT', '120'))
        max_retries = int(os.getenv('SQLBOT_LLM_RETRIES', '3'))
        return handle_llm_query(q, max_retries=max_retries, timeout_seconds=timeout_seconds, show_history=SHOW_HISTORY, show_full_history=SHOW_FULL_HISTORY)
    
    # Start unified REPL
    start_unified_repl(memory_manager, rich_console)

def execute_dbt_run_unlimited(sql_query):
    """Execute SQL query with very high limit for now"""
    print("📋 Using high limit (1000 rows) - true unlimited coming soon")
    return execute_dbt_sql_unlimited(sql_query)

def execute_dbt_sql_rich(sql_query):
    """Execute SQL query through dbt and format results with Rich tables"""
    return execute_safe_sql(sql_query)

def execute_dbt_sql_rich_fallback(sql_query):
    """Execute SQL query and format results with Rich tables (full width, no truncation)"""
    import tempfile
    import os
    import re
    import subprocess
    
    # Always use dbt - no more direct SQL bypass
    print(f"🔍 Executing via dbt: {sql_query}")
    # Create and execute query to get raw results
    models_dir = PROJECT_ROOT / 'models'
    models_dir.mkdir(exist_ok=True)
    
    # Clean query - more aggressive cleaning for DBT compatibility
    clean_query = sql_query.strip()
    
    # Remove trailing semicolons (DBT doesn't like them)
    clean_query = re.sub(r';\s*$', '', clean_query)
    
    # Note: TOP clauses now work fine with dbt run-operation approach
    
    # Simplify complex UNION queries that fail in DBT
    if 'UNION ALL' in clean_query.upper() and clean_query.count('UNION ALL') > 1:
        # For complex unions, simplify to just the first part
        parts = clean_query.split('UNION ALL')
        clean_query = parts[0].strip()
        print("ℹ️ Simplified complex UNION query for DBT compatibility")
    
    # Create temporary model file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, 
                                     dir=models_dir, prefix='temp_rich_') as f:
        f.write(clean_query)
        temp_model_path = f.name
        temp_model_name = os.path.basename(temp_model_path).replace('.sql', '')
    
    try:
        # First compile to process Jinja/macros
        os.chdir(PROJECT_ROOT)
        compile_result = subprocess.run([
            'dbt', 'compile', '--select', temp_model_name
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if compile_result.returncode != 0:
            error_msg = compile_result.stderr.strip() or compile_result.stdout.strip() or "Unknown compilation error"
            rich_console.print(f"[{get_error_style()}]Compilation failed: {error_msg}[/{get_error_style()}]")
            return False
        
        # Execute dbt command and capture output (suppress logs)
        result = subprocess.run([
            'dbt', 'show', '--select', temp_model_name, '--limit', '5000', '--quiet'
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            # Parse the dbt output to extract table data
            output_lines = result.stdout.split('\n')
            table_data = []
            column_headers = []
            parsing_table = False
            
            for line in output_lines:
                # Look for the table section after "Previewing node"
                if "Previewing node" in line:
                    parsing_table = False  # Reset parsing state
                    continue
                    
                if line.strip().startswith('|') and '---' not in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if parts:
                        if not column_headers:
                            column_headers = parts
                            parsing_table = True
                        else:
                            table_data.append(parts)
                elif parsing_table and not line.strip().startswith('|') and line.strip():
                    # End of table if we hit a non-pipe, non-empty line
                    break
            
            if column_headers:
                if table_data:
                    # Create Rich table with data
                    rich_table = Table(
                        title="📊 Query Results", 
                        border_style="magenta2",
                        expand=True,
                        show_lines=True
                    )
                    
                    # Add columns
                    for header in column_headers:
                        rich_table.add_column(header, style="bold purple", no_wrap=False, overflow="ignore")
                    
                    # Add all rows
                    for row in table_data:
                        padded_row = row + [''] * (len(column_headers) - len(row))
                        rich_table.add_row(*padded_row[:len(column_headers)])
                    
                    # Display the Rich formatted table
                    rich_console.print(rich_table)
                    
                    # Add summary
                    summary_panel = Panel(
                        f"[bold green]✓ Query executed successfully[/bold green]\n"
                        f"[dim]Showing {len(table_data)} rows with {len(column_headers)} columns[/dim]",
                        border_style="green",
                        title="Summary"
                    )
                    rich_console.print(summary_panel)
                else:
                    # Empty result set
                    empty_table = Table(
                        title="📊 Query Results (No Data)", 
                        border_style="yellow",
                        expand=True
                    )
                    
                    for header in column_headers:
                        empty_table.add_column(header, style="dim yellow")
                    
                    empty_table.add_row(*["(no data)" for _ in column_headers])
                    rich_console.print(empty_table)
                    
                    rich_console.print(Panel(
                        "[yellow]✓ Query executed successfully - No results found[/yellow]",
                        border_style="yellow",
                        title="Summary"
                    ))
                return True
            else:
                # Fallback to regular output if parsing failed
                rich_console.print(f"[yellow]Could not parse table format, showing raw output:[/yellow]")
                rich_console.print(result.stdout)
                return True
        else:
            # Show detailed error information
            error_details = []
            if result.stderr.strip():
                error_details.append(f"STDERR: {result.stderr.strip()}")
            if result.stdout.strip():
                error_details.append(f"STDOUT: {result.stdout.strip()}")
            error_details.append(f"Return code: {result.returncode}")
            
            error_message = "\n".join(error_details) if error_details else "Unknown dbt error occurred"
            rich_console.print(f"[{get_error_style()}]Error: {error_message}[/{get_error_style()}]")
            return False
            
    except Exception as e:
        rich_console.print(f"[{get_error_style()}]Error executing Rich SQL query: {e}[/{get_error_style()}]")
        return False
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_model_path):
                os.unlink(temp_model_path)
        except Exception:
            pass


def is_sql_query(query):
    """Detect if query should be treated as SQL/dbt (ends with semicolon)"""
    return query.strip().endswith(';')

def show_banner(is_no_repl=False, profile=None, llm_model=None, llm_available=False):
    """Show SQLBot banner with setup information"""
    from sqlbot.interfaces.banner import get_banner_content, get_interactive_banner_content
    from rich.markdown import Markdown
    from rich.panel import Panel

    # Get dbt configuration information
    dbt_config_info = None
    try:
        from sqlbot.core.dbt_service import get_dbt_service
        from sqlbot.core.config import SQLBotConfig
        config = SQLBotConfig.from_env(profile=profile)
        # Initialize READONLY_MODE based on config (unless overridden by CLI)
        global READONLY_MODE
        if not READONLY_CLI_MODE:  # Only if not explicitly set by --dangerous flag
            READONLY_MODE = not config.dangerous  # dangerous=false means safeguards enabled
        dbt_service = get_dbt_service(config)
        dbt_config_info = dbt_service.get_dbt_config_info()
    except Exception:
        # If we can't get dbt config info, continue without it
        pass

    if is_no_repl:
        # CLI/no-repl mode banner with Markdown support
        banner_text = get_banner_content(
            profile=profile,
            llm_model=llm_model,
            llm_available=llm_available,
            interface_type="text",
            dbt_config_info=dbt_config_info
        )

        # Use Rich Markdown for proper formatting
        theme = get_theme_manager()
        markdown_content = Markdown(banner_text)

        # Display in a panel with theme colors
        rich_console.print(Panel(markdown_content, border_style=theme.get_color('ai_response')))
    else:
        # Full interactive banner with Markdown support
        banner_text = get_interactive_banner_content(
            profile=profile,
            llm_model=llm_model,
            llm_available=llm_available,
            dbt_config_info=dbt_config_info
        )

        # Use Rich Markdown for proper formatting
        theme = get_theme_manager()
        markdown_content = Markdown(banner_text)

        # Display in a panel with theme colors
        ai_color = theme.get_color('ai_response')
        rich_console.print(Panel(markdown_content, border_style=ai_color))



def main():
    """Main entry point for SQLBot."""
    import sys
    
    # Global variable declarations
    global PREVIEW_MODE, READONLY_MODE, READONLY_CLI_MODE, SHOW_HISTORY, SHOW_FULL_HISTORY
    
    # Parse arguments with subcommand support
    from .cli import parse_args_with_subcommands, handle_cli_subcommands
    
    args = parse_args_with_subcommands()
    if args is None:
        return  # Help was shown
    
    # Handle subcommands first
    if args.command:
        exit_code = handle_cli_subcommands(args)
        sys.exit(exit_code)
    
    # Apply theme early based on command line argument
    theme_map = {mode.value: mode for mode in ThemeMode}
    theme_manager = get_theme_manager()
    theme_manager.set_theme(theme_map[args.theme])
    
    # Theme is now set - all subsequent UI should use theme colors
    
    # Global variable declarations
    global dbt, LLM_AVAILABLE
    
    # Show banner first ONLY for CLI mode with query (not for Textual app)
    # Banner should only show when we'll use Rich/CLI interface, not Textual interface
    # IMPORTANT: Never show banner in --no-repl mode or --text mode with query
    if args.query and not args.no_repl and not args.text and (not sys.stdin.isatty() or not LLM_AVAILABLE):
        # Get LLM model info for banner
        llm_model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5') if LLM_AVAILABLE else None
        show_banner(is_no_repl=True, profile=args.profile, llm_model=llm_model, llm_available=LLM_AVAILABLE)
    
    # Initialize everything after banner display
    if dbt is None:
        from dbt.cli.main import dbtRunner
        dbt = dbtRunner()
    
    # Clear conversation history at startup to avoid stale data
    try:
        from .llm_integration import clear_conversation_history
        clear_conversation_history()
    except ImportError:
        from llm_integration import clear_conversation_history
        clear_conversation_history()
    
    # Get LLM model info for banner
    llm_model = None
    if LLM_AVAILABLE:
        llm_model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
    
    # Banner will be shown by unified display system - no duplicate needed
    
    # Only show status if there are issues, not for successful initialization
    
    # Continue with the rest of main...
    
    # Handle help
    if hasattr(args, 'help') and args.help:
        from .cli import create_cli_parser
        parser = create_cli_parser()
        parser.print_help()
        sys.exit(0)
    
    # Set global profile name
    global DBT_PROFILE_NAME
    DBT_PROFILE_NAME = args.profile
    
    # Set global context flag
    if LLM_AVAILABLE:
        try:
            # Try relative import first (when run as module)
            from . import llm_integration
            llm_integration.show_context = args.context
            llm_integration.DBT_PROFILE_NAME = args.profile
        except ImportError:
            try:
                # Fallback for direct execution
                import llm_integration
                llm_integration.show_context = args.context
                llm_integration.DBT_PROFILE_NAME = args.profile
            except ImportError:
                # If we can't import the module, just skip setting the flag
                pass
    
    # Check for command line input
    if args.query:
        # Join all query arguments as a single query
        query = ' '.join(args.query)
        
        # Set global mode flags
        if args.preview:
            PREVIEW_MODE = True
            rich_console.print("Preview Mode Enabled - SQL will be shown before execution")
        
        if args.dangerous:
            READONLY_MODE = False
            READONLY_CLI_MODE = True  # CLI mode - safeguards explicitly disabled
            rich_console.print("Dangerous Mode Enabled - Safeguards disabled, all operations allowed")
        
        if args.history:
            SHOW_HISTORY = True
        
        if args.full_history:
            SHOW_HISTORY = True  # Enable history display
            SHOW_FULL_HISTORY = True  # Enable full history mode
        
        # Execute query using CLI text mode with unified display
        if args.text:
            # Add spacing after command line when not showing banner
            rich_console.print()
            rich_console.print()

            # Execute the initial query using unified display system
            _execute_query_cli_mode(query, rich_console)
            
            # Check --no-repl flag to determine next action
            if args.no_repl:
                rich_console.print("\n[dim]Exiting (--no-repl mode)[/dim]")
                return  # Exit after query execution
            else:
                # Continue to interactive CLI mode
                _start_cli_interactive_mode(rich_console)
                return
        else:
            # Default: Use Textual interface or CLI mode based on availability and environment
            if args.no_repl or not sys.stdin.isatty():
                # --no-repl or non-interactive terminal: use CLI mode and exit
                if not LLM_AVAILABLE:
                    rich_console.print("[yellow]LLM integration not available. Using CLI mode.[/yellow]")
                
                _execute_query_cli_mode(query, rich_console)
                rich_console.print("\n[dim]Exiting (--no-repl mode)[/dim]")
                return
            elif LLM_AVAILABLE:
                # Interactive environment with LLM: start Textual interface directly with the query
                from sqlbot.interfaces.textual_repl import create_textual_repl_from_args
                textual_repl = create_textual_repl_from_args(args)
                textual_repl.initial_query = query
                textual_repl.run()
                return
            else:
                # Interactive environment without LLM: use CLI mode and continue to interactive
                rich_console.print("[yellow]LLM integration not available. Using CLI mode.[/yellow]")
                _execute_query_cli_mode(query, rich_console)
                _start_cli_interactive_mode(rich_console)
                return

    # No query provided, start interactive mode based on interface choice
    else:
        if args.text or os.getenv('SQLBOT_TEXT_MODE'):
            # Text-mode interactive REPL (can be forced via environment variable for testing)
            show_banner(is_no_repl=False, profile=args.profile, llm_model=llm_model, llm_available=LLM_AVAILABLE)
            _start_cli_interactive_mode(rich_console)
        else:
            # Default: Use Textual interface
            from sqlbot.interfaces.textual_repl import create_textual_repl_from_args
            textual_repl = create_textual_repl_from_args(args)
            textual_repl.run()


def _execute_query_cli_mode(query: str, console):
    """Execute a single query in CLI mode using unified display"""
    try:
        if query.startswith('/'):
            result = handle_slash_command(query)
            if result == 'EXIT':
                sys.exit(0)
            return  # Important: Don't continue processing after slash command
        elif is_sql_query(query):
            # Treat as SQL/dbt (ends with semicolon)
            result = execute_dbt_sql_rich(query)
            if result and not result.startswith("Query blocked by safeguard"):
                console.print(f"\n[green]{result}[/green]")
            elif result and result.startswith("Query blocked by safeguard"):
                # Safeguard already printed the warning messages, don't print the result
                pass
        elif LLM_AVAILABLE:
            # Natural language query - use unified display system with conversation history
            from sqlbot.conversation_memory import ConversationMemoryManager
            from sqlbot.interfaces.unified_display import execute_query_with_unified_display
            
            # Use a global memory manager for CLI mode to persist conversation history
            if not hasattr(_execute_query_cli_mode, '_cli_memory_manager'):
                _execute_query_cli_mode._cli_memory_manager = ConversationMemoryManager()
            memory_manager = _execute_query_cli_mode._cli_memory_manager
            
            # Sync conversation history BEFORE executing the query
            try:
                from . import llm_integration
                _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
            except ImportError:
                try:
                    import llm_integration
                    _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
                except ImportError:
                    pass  # If we can't sync, continue without it
            
            # Set up unified message display for CLI mode
            from sqlbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
            cli_display = CLIMessageDisplay(console)
            cli_display.set_interactive_mode(False)  # Non-interactive CLI mode
            unified_display = UnifiedMessageDisplay(cli_display, memory_manager)
            
            # Create execute_llm_func with conversation sync and unified display
            def execute_llm_func(q: str) -> str:
                global SHOW_HISTORY, SHOW_FULL_HISTORY
                timeout_seconds = int(os.getenv('SQLBOT_LLM_TIMEOUT', '120'))
                max_retries = int(os.getenv('SQLBOT_LLM_RETRIES', '3'))
                
                # Call handle_llm_query with unified_display for tool call display
                result = handle_llm_query(q, max_retries=max_retries, timeout_seconds=timeout_seconds, unified_display=unified_display, show_history=SHOW_HISTORY, show_full_history=SHOW_FULL_HISTORY)
                
                # Sync the updated global conversation_history back to our memory_manager for next time
                try:
                    from . import llm_integration
                    _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
                except ImportError:
                    try:
                        import llm_integration
                        _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
                    except ImportError:
                        pass  # If we can't sync, continue without it
                
                return result
            
            # Execute the query using unified display with conversation history
            try:
                result = execute_query_with_unified_display(
                    query,
                    memory_manager,
                    execute_llm_func,
                    console=console,
                    show_history=SHOW_HISTORY,
                    show_full_history=SHOW_FULL_HISTORY,
                    skip_user_message=False,
                    unified_display=unified_display
                )
                
                # Check if result indicates a dbt setup issue
                if ("dbt Profile Not Found" in result or "Database Connection Failed" in result or 
                    "dbt Configuration Issue" in result or "dbt Not Installed" in result):
                    console.print("\n[yellow]💡 Please fix the dbt setup issue above before using SQLBot.[/yellow]")
                    sys.exit(1)
            except Exception as e:
                console.print(f"[red]Query failed: {e}[/red]")
        else:
            # No LLM available, treat as SQL
            console.print("[yellow]LLM integration not available. Treating as SQL. End with ';' for SQL queries.[/yellow]")
            result = execute_dbt_sql_rich(query)
            if result and not result.startswith("Query blocked by safeguard"):
                console.print(f"\n[green]{result}[/green]")
            elif result and result.startswith("Query blocked by safeguard"):
                # Safeguard already printed the warning messages, don't print the result
                pass
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _start_cli_interactive_mode(console):
    """Start interactive CLI mode"""
    from sqlbot.conversation_memory import ConversationMemoryManager
    from sqlbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
    
    # Create memory manager and execution function for REPL
    memory_manager = ConversationMemoryManager()
    
    # Start unified interactive REPL (will create execute_llm_func with unified_display access)
    start_unified_repl(memory_manager, console)




def _sync_conversation_history_to_memory(memory_manager, conversation_history):
    """
    Sync the conversation history from handle_llm_query back to our memory manager.
    This ensures the memory manager sees the full conversation including tool calls and results.
    """
    # Debug: Print what we're syncing (disabled for production)
    # print(f"\n🔍 DEBUG: Syncing {len(conversation_history)} messages to memory manager:")
    # for i, msg in enumerate(conversation_history):
    #     role = msg.get("role", "unknown")
    #     content_preview = str(msg.get("content", ""))[:100] + "..." if len(str(msg.get("content", ""))) > 100 else str(msg.get("content", ""))
    #     print(f"  [{i+1}] {role.upper()}: {content_preview}")
    
    # Clear and rebuild memory from the updated conversation history
    memory_manager.clear_history()
    
    for msg in conversation_history:
        if msg["role"] == "user":
            memory_manager.add_user_message(msg["content"])
        elif msg["role"] == "assistant":
            memory_manager.add_assistant_message(msg["content"])

def start_unified_repl(memory_manager, console):
    """Start unified interactive REPL using unified message display system"""
    from sqlbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
    from sqlbot.interfaces.unified_display import execute_query_with_unified_display
    from sqlbot.interfaces.message_formatter import MessageSymbols
    import readline
    
    # Set up unified message display
    cli_display = CLIMessageDisplay(console)
    cli_display.set_interactive_mode(True)  # Enable prompt overwriting
    unified_display = UnifiedMessageDisplay(cli_display, memory_manager)
    
    # Create execute_llm_func with access to unified_display and conversation sync
    def execute_llm_func(q: str) -> str:
        global SHOW_HISTORY, SHOW_FULL_HISTORY
        timeout_seconds = int(os.getenv('SQLBOT_LLM_TIMEOUT', '120'))
        max_retries = int(os.getenv('SQLBOT_LLM_RETRIES', '3'))
        
        # Call handle_llm_query which maintains its own global conversation_history
        result = handle_llm_query(q, max_retries=max_retries, timeout_seconds=timeout_seconds, unified_display=unified_display, show_history=SHOW_HISTORY, show_full_history=SHOW_FULL_HISTORY)
        
        # Sync the updated global conversation_history back to our memory_manager
        # This ensures the next query sees the full conversation including tool calls and results
        try:
            from . import llm_integration
            _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
        except ImportError:
            try:
                import llm_integration
                _sync_conversation_history_to_memory(memory_manager, llm_integration.conversation_history)
            except ImportError:
                pass  # If we can't sync, continue without it
        
        return result
    
    try:
        while True:
            try:
                # Mark that we're about to show a prompt
                cli_display.mark_prompt_shown()

                # Add blank line before prompt for better spacing
                print()

                # Use the input prompt symbol
                user_input = input(f"{MessageSymbols.INPUT_PROMPT} ").strip()
                
                if not user_input:
                    # Reset prompt flag if no input
                    cli_display.last_was_prompt = False
                    continue
                    
                # Handle exit commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                
                # Route the query to appropriate handler (same logic as _execute_query_cli_mode)
                try:
                    if user_input.startswith('/'):
                        # Handle slash commands
                        result = handle_slash_command(user_input)
                        if result == 'EXIT':
                            break
                        # Slash commands are handled, don't continue processing
                    elif is_sql_query(user_input):
                        # Handle SQL queries
                        result = execute_dbt_sql_rich(user_input)
                        if result and not result.startswith("Query blocked by safeguard"):
                            console.print(f"\n[green]{result}[/green]")
                        elif result and result.startswith("Query blocked by safeguard"):
                            # Safeguard already printed the warning messages, don't print the result
                            pass
                    elif LLM_AVAILABLE:
                        # Handle natural language queries with unified display
                        result = execute_query_with_unified_display(
                            user_input,
                            memory_manager,
                            execute_llm_func,
                            console=console,
                            show_history=SHOW_HISTORY,
                            show_full_history=SHOW_FULL_HISTORY,
                            skip_user_message=False,
                            unified_display=unified_display
                        )
                        # Result is already displayed by execute_query_with_unified_display
                    else:
                        console.print("[yellow]LLM integration not available. End with ';' for SQL queries.[/yellow]")
                        result = execute_dbt_sql_rich(user_input)
                        if result and not result.startswith("Query blocked by safeguard"):
                            console.print(f"\n[green]{result}[/green]")
                        elif result and result.startswith("Query blocked by safeguard"):
                            # Safeguard already printed the warning messages, don't print the result
                            pass
                except Exception as e:
                    unified_display.add_error_message(f"Query failed: {e}")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit', 'quit', or 'q' to exit[/yellow]")
            except EOFError:
                break
                
    except Exception as e:
        console.print(f"[red]Error in REPL: {e}[/red]")
    
    console.print("[dim]Goodbye![/dim]")


# REMOVED: start_text_repl_with_shared_session function
# --text mode now uses the same unified display logic as --no-repl mode


if __name__ == "__main__":
    main()
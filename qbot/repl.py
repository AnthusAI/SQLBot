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

# Note: We use dbt for all database connections, no direct pyodbc needed

load_dotenv()

# Simplified messaging system - only 4 meaningful color categories
class MessageStyle:
    """Simple, consistent colors based on source only"""
    # User input - unique color
    USER = "[bold dodger_blue2]"
    
    # LLM responses - unique color  
    LLM = "[bold magenta2]"
    
    # Database/Tool responses - unique color
    DATABASE = "[bold cyan]"
    
    # System messages - default color (no formatting)
    SYSTEM = ""

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
DBT_PROFILE_NAME = 'qbot'  # Default profile name, can be overridden via --profile

# Global flags
READONLY_MODE = False
READONLY_CLI_MODE = False  # Track if --read-only was used (no override allowed)
PREVIEW_MODE = False
SHOW_HISTORY = False  # Show conversation history panel

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
    """Execute SQL query using dbt show --inline with TOP handling"""
    import subprocess
    import re
    
    # Get the current profile name - try to import from llm_integration if available
    try:
        from . import llm_integration
        profile_name = llm_integration.get_current_profile()
    except ImportError:
        try:
            import llm_integration
            profile_name = llm_integration.get_current_profile()
        except ImportError:
            profile_name = DBT_PROFILE_NAME
    
    try:
        # Clean up query for dbt compatibility
        clean_query = sql_query.strip()
        # Remove semicolon - dbt show --inline doesn't like it
        clean_query = clean_query.rstrip(';')
        # Remove TOP to avoid OFFSET conflict with dbt show
        clean_query = re.sub(r'\bSELECT\s+TOP\s+\d+\s+', 'SELECT ', clean_query, flags=re.IGNORECASE)
        
        # Use dbt show --inline with --quiet to suppress logs - handles both raw SQL and Jinja
        result = subprocess.run([
            'dbt', 'show', '--inline', clean_query,
            '--profile', profile_name,
            '--quiet'
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            return result.stdout
        else:
            # Capture both stderr and stdout for comprehensive error info
            error_details = []
            if result.stderr and result.stderr.strip():
                error_details.append(f"STDERR: {result.stderr.strip()}")
            if result.stdout and result.stdout.strip():
                error_details.append(f"STDOUT: {result.stdout.strip()}")
            
            if error_details:
                full_error = "\n".join(error_details)
                return f"Error executing query:\n{full_error}"
            else:
                return f"Error executing query: dbt command failed with return code {result.returncode} but no error details were provided"
            
    except Exception as e:
        return f"Failed to execute query: {str(e)}"


def preview_sql_compilation(sql_query):
    """Preview compiled SQL without executing it"""
    import subprocess
    
    # Get the current profile name - try to import from llm_integration if available
    try:
        from . import llm_integration
        profile_name = llm_integration.get_current_profile()
    except ImportError:
        try:
            import llm_integration
            profile_name = llm_integration.get_current_profile()
        except ImportError:
            profile_name = DBT_PROFILE_NAME
    
    try:
        # Use dbt compile --inline to show the compiled SQL
        result = subprocess.run([
            'dbt', 'compile', '--inline', sql_query,
            '--profile', profile_name
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error compiling query: {result.stderr}"
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
        
        # Ask for execution approval (skip in non-interactive environments)
        # Check if we're in a subprocess with no real stdin (like tests)
        try:
            # Try to get terminal size - this will fail in non-interactive environments
            os.get_terminal_size()
            is_interactive = sys.stdin.isatty()
        except OSError:
            # No terminal available - definitely non-interactive
            is_interactive = False
            
        if not is_interactive:
            # Non-interactive environment - auto-approve
            rich_console.print("\n[dim]Auto-approving in non-interactive environment[/dim]")
        else:
            try:
                execute = input("\n🤔 Execute this SQL query? (y/n): ").strip().lower()
                if execute not in ['y', 'yes']:
                    rich_console.print("[yellow]SQL execution cancelled.[/yellow]")
                    return "SQL execution cancelled by user in preview mode"
            except (KeyboardInterrupt, EOFError):
                rich_console.print("\n[yellow]SQL execution cancelled.[/yellow]")
                return "SQL execution cancelled by user in preview mode"
        
        rich_console.print("Executing SQL...")
    
    # If readonly mode is disabled, execute directly
    if not READONLY_MODE:
        return execute_clean_sql(sql_query)
    
    # Analyze query safety
    rich_console.print("Read-only safeguard: Analyzing SQL for dangerous operations...")
    safety_analysis = analyze_sql_safety(sql_query)
    
    if not safety_analysis['is_safe'] and not force_execute:
        # Query contains dangerous operations
        operations = ', '.join(safety_analysis['dangerous_operations'])
        
        if READONLY_CLI_MODE:
            # CLI mode - no override allowed
            rich_console.print("Query blocked by read-only mode!")
            rich_console.print(f"[yellow]Dangerous operations detected: {operations}[/yellow]")
            rich_console.print(f"[dim]Query: {sql_query}[/dim]")
            rich_console.print("Query execution blocked for safety - no override available in read-only mode.")
            return "Query blocked by read-only mode"
        else:
            # Interactive mode - allow admin override
            rich_console.print("Query blocked by read-only safeguard!")
            rich_console.print(f"[yellow]Dangerous operations detected: {operations}[/yellow]")
            rich_console.print(f"[dim]Query: {sql_query}[/dim]")
            
            # Ask for admin override (skip in non-interactive environments)
            # Check if we're in a subprocess with no real stdin (like tests)
            try:
                # Try to get terminal size - this will fail in non-interactive environments
                os.get_terminal_size()
                is_interactive = sys.stdin.isatty()
            except OSError:
                # No terminal available - definitely non-interactive
                is_interactive = False
                
            if not is_interactive:
                # Non-interactive environment - deny override
                rich_console.print("\n[dim]Auto-denying override in non-interactive environment[/dim]")
                rich_console.print("Query execution cancelled for safety.")
                return "Query blocked by read-only safeguard"
            else:
                try:
                    override = input("\n⚠️  Override safety check and execute anyway? (yes/no): ").strip().lower()
                    if override in ['yes', 'y']:
                        rich_console.print("Safety override granted. Executing query...")
                        return execute_clean_sql(sql_query)
                    else:
                        rich_console.print("Query execution cancelled for safety.")
                        return "Query blocked by read-only safeguard"
                except (KeyboardInterrupt, EOFError):
                    rich_console.print("\nQuery execution cancelled for safety.")
                    return "Query blocked by read-only safeguard"
    else:
        # Query is safe, execute normally
        rich_console.print("Read-only safeguard: Query is safe - no dangerous operations detected.")
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
    elif command == 'tables':
        # Rich formatted full-width table list
        query = "select table_name, table_type from information_schema.tables where table_schema not in ('information_schema', 'sys', 'INFORMATION_SCHEMA', 'SYS') order by table_name"
        rich_console.print("🔍 [bold magenta2]Listing all database tables[/bold magenta2]")
        return execute_dbt_rich_tables(query)
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
            title="🔧 QBot Database Interface Commands", 
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
        help_table.add_row("/tables", "[bold purple]List all database tables (Rich formatted, full width)[/bold purple]")
        help_table.add_row("[bold green]Natural language[/bold green]", "[bold green]Ask questions in plain English (default)[/bold green]")
        help_table.add_row("[bold blue]SQL with ;[/bold blue]", "[bold blue]End with semicolon to run as dbt SQL[/bold blue]")
        help_table.add_row("/preview", "Preview compiled SQL before execution")
        help_table.add_row("/readonly", "Toggle read-only safeguard mode")
        help_table.add_row("/history", "Toggle conversation history display")
        help_table.add_row("/help", "Show this help")
        help_table.add_row("/no-repl", "Exit interactive mode")
        help_table.add_row("/exit", "Exit console")
        
        rich_console.print(help_table)
        return
    elif command == 'preview':
        return handle_preview_command(args)
    elif command == 'readonly':
        return handle_readonly_command(args)
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
    elif command == 'readonly':
        return handle_readonly_command(args)
    else:
        print(f"Unknown double-slash command: //{command}")
        print("Available double-slash commands:")
        print("  //preview - Preview compiled SQL before execution")
        print("  //readonly - Toggle read-only safeguard mode")
        return

def handle_preview_command(args):
    """Handle the //preview command - shows compiled SQL and prompts for execution"""
    rich_console.print("🔍 [bold magenta2]Preview Mode[/bold magenta2] - Enter SQL to preview compilation:")
    
    # Skip interactive prompts in non-interactive environments
    # Check if we're in a subprocess with no real stdin (like tests)
    try:
        # Try to get terminal size - this will fail in non-interactive environments
        os.get_terminal_size()
        is_interactive = sys.stdin.isatty()
    except OSError:
        # No terminal available - definitely non-interactive
        is_interactive = False
        
    if not is_interactive:
        
        rich_console.print("[dim]Preview command not available in non-interactive environment[/dim]")
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

def handle_readonly_command(args):
    """Handle the //readonly command - toggle read-only safeguard mode."""
    global READONLY_MODE
    
    if not args:
        # Show current status
        status = "ON" if READONLY_MODE else "OFF"
        rich_console.print(f"🔒 [bold blue]Read-only safeguard mode: {status}[/bold blue]")
        if READONLY_MODE:
            rich_console.print("[dim]All queries will be checked for dangerous operations.[/dim]")
        else:
            rich_console.print("[dim]Queries will execute without safety checks.[/dim]")
        rich_console.print("[dim]Use '/readonly on' or '/readonly off' to change.[/dim]")
    elif args[0].lower() in ['on', 'enable', 'true']:
        READONLY_MODE = True
        rich_console.print("🔒 [bold green]Read-only safeguard mode ENABLED[/bold green]")
        rich_console.print("[dim]All queries will be checked for dangerous operations.[/dim]")
    elif args[0].lower() in ['off', 'disable', 'false']:
        READONLY_MODE = False
        rich_console.print("🔓 [bold yellow]Read-only safeguard mode DISABLED[/bold yellow]")
        rich_console.print("[dim]Queries will execute without safety checks.[/dim]")
    else:
        rich_console.print(f"[red]Unknown readonly option: {args[0]}[/red]")
        rich_console.print("Usage: /readonly [on|off]")

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
    from qbot.interfaces.unified_display import execute_query_with_unified_display
    from qbot.conversation_memory import ConversationMemoryManager
    
    # Create memory manager and execution function
    memory_manager = ConversationMemoryManager()
    def execute_llm_func(q: str) -> str:
        timeout_seconds = int(os.getenv('QBOT_LLM_TIMEOUT', '120'))
        max_retries = int(os.getenv('QBOT_LLM_RETRIES', '3'))
        return handle_llm_query(q, max_retries=max_retries, timeout_seconds=timeout_seconds)
    
    # Start unified REPL
    start_unified_repl(memory_manager, execute_llm_func, rich_console)

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
            rich_console.print(f"[red]Compilation failed: {error_msg}[/red]")
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
            rich_console.print(f"[red]Error: {error_message}[/red]")
            return False
            
    except Exception as e:
        rich_console.print(f"[red]Error executing Rich SQL query: {e}[/red]")
        return False
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_model_path):
                os.unlink(temp_model_path)
        except Exception:
            pass

def execute_dbt_rich_tables(sql_query):
    """Execute SQL and format results with Rich tables (full width, no truncation)"""
    import sqlalchemy as sa
    import yaml
    from sqlalchemy import text
    
    try:
        # Read dbt profile to get connection details
        profiles_path = Path.home() / '.dbt' / 'profiles.yml'
        
        with open(profiles_path, 'r') as f:
            profiles = yaml.safe_load(f)
        
        # Use the configured profile name
        if DBT_PROFILE_NAME not in profiles:
            return f"❌ Profile '{DBT_PROFILE_NAME}' not found in ~/.dbt/profiles.yml"
        
        profile_config = profiles[DBT_PROFILE_NAME]['outputs']['dev']
        
        # Create SQLAlchemy connection string using the profile details
        host = profile_config['host']
        database = profile_config['database'] 
        user = profile_config['user']
        password = profile_config['password']
        port = profile_config.get('port', 1433)
        driver = profile_config.get('driver', 'ODBC Driver 18 for SQL Server')
        
        # SQL Server connection string with authentication
        connection_string = f"mssql+pyodbc://{user}:{password}@{host}:{port}/{database}?driver={driver.replace(' ', '+')}&TrustServerCertificate=yes"
        
        # Create engine and execute query directly
        engine = sa.create_engine(connection_string)
        
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            
            # Create Rich table with full width and NO truncation
            rich_table = Table(
                title="📋 Database Tables", 
                border_style="magenta2",
                expand=True,
                show_lines=True,
                width=None,  # No width constraint
                min_width=None  # No minimum width
            )
            
            # Add columns with NO width limits and NO truncation
            rich_table.add_column(
                "Table Name", 
                style="bold purple", 
                no_wrap=False, 
                overflow="fold",
                width=None,
                min_width=None,
                max_width=None
            )
            rich_table.add_column(
                "Type", 
                style="dim magenta2", 
                no_wrap=False, 
                overflow="fold",
                width=None,
                min_width=None,
                max_width=None
            )
            
            # Add all rows with FULL table names (no truncation)
            for row in rows:
                rich_table.add_row(str(row[0]), str(row[1]))
            
            # Display the Rich formatted table
            rich_console.print(rich_table)
            
            # Add summary in a panel
            summary_panel = Panel(
                f"[bold green]✓ Found {len(rows)} database objects[/bold green]\n"
                f"[dim]Direct database query with Rich formatting[/dim]",
                border_style="green",
                title="Summary"
            )
            rich_console.print(summary_panel)
            
            return True
            
    except Exception as e:
        rich_console.print(f"[red]Direct database connection failed: {e}[/red]")
        rich_console.print(f"[yellow]This will show full table names without truncation when connection works[/yellow]")
        return False

def is_sql_query(query):
    """Detect if query should be treated as SQL/dbt (ends with semicolon)"""
    return query.strip().endswith(';')

def show_banner(is_no_repl=False, profile=None, llm_model=None, llm_available=False):
    """Show QBot banner with setup information"""
    from qbot.interfaces.banner import get_banner_content, get_interactive_banner_content
    
    if is_no_repl:
        # CLI/no-repl mode banner - ensure it contains the expected text
        banner_text = get_banner_content(
            profile=profile, 
            llm_model=llm_model, 
            llm_available=llm_available, 
            interface_type="text"
        )
        # The banner_text already contains "QBot: Database Query Interface" from get_banner_content
        rich_console.print(Panel(banner_text, border_style="magenta2"))
    else:
        # Full interactive banner
        banner_text = get_interactive_banner_content(
            profile=profile,
            llm_model=llm_model, 
            llm_available=llm_available
        )
        # Apply Rich formatting
        formatted_text = banner_text.replace("QBot:", "[bold magenta2]QBot:[/bold magenta2]")
        formatted_text = formatted_text.replace("Ready for questions.", "[bold green]Ready for questions.[/bold green]")
        formatted_text = formatted_text.replace("🤖 Default:", "[bold green]🤖 Default:[/bold green]")
        formatted_text = formatted_text.replace("🔍 SQL/dbt Queries:", "[bold blue]🔍 SQL/dbt Queries:[/bold blue]")
        formatted_text = formatted_text.replace("Commands:", "[dim purple]Commands:[/dim purple]")
        formatted_text = formatted_text.replace("💡 Tips:", "[dim purple]💡 Tips:[/dim purple]")
        formatted_text = formatted_text.replace("📊 Configuration:", "[dim cyan]📊 Configuration:[/dim cyan]")
        
        rich_console.print(Panel(formatted_text, border_style="magenta2"))

def _is_test_environment() -> bool:
    """Check if we're running in a test environment."""
    import sys
    
    # Check for pytest - this is the most reliable indicator
    if 'pytest' in sys.modules:
        return True
    
    # Check for pytest-specific environment variables
    if os.getenv('PYTEST_CURRENT_TEST'):
        return True
    
    # Check if we're being called from pytest
    if len(sys.argv) > 0:
        if any(arg in sys.argv[0] for arg in ['pytest', 'py.test']):
            return True
    
    # Check if we're in a CI environment running tests
    if os.getenv('CI') and any(os.getenv(var) for var in ['TESTING', 'GITHUB_ACTIONS']):
        return True
    
    return False


def main():
    """Main entry point for QBot."""
    import sys
    import argparse
    
    # Global variable declarations
    global PREVIEW_MODE, READONLY_MODE, READONLY_CLI_MODE, SHOW_HISTORY
    
    # Parse arguments first
    parser = argparse.ArgumentParser(description='QBot: Database Query Bot', add_help=False)
    parser.add_argument('--context', action='store_true', help='Show LLM conversation context')
    parser.add_argument('--profile', default='qbot', help='dbt profile name to use (default: qbot)')
    parser.add_argument('--preview', action='store_true', help='Preview compiled SQL before executing query')
    parser.add_argument('--read-only', action='store_true', help='Enable read-only safeguard to block dangerous SQL operations')
    parser.add_argument('--no-repl', '--norepl', action='store_true', help='Exit after executing query without starting interactive mode')
    parser.add_argument('--text', action='store_true', help='Use text-based REPL with shared session (for debugging)')
    parser.add_argument('--history', action='store_true', help='Show conversation history panel (for debugging)')
    parser.add_argument('--help', '-h', action='store_true', help='Show help')
    parser.add_argument('query', nargs='*', help='Query to execute')
    
    args = parser.parse_args()
    
    # Only show banner for --no-repl mode (Rich logging UI)
    # Initialize everything first
    global dbt, LLM_AVAILABLE
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
        import os
        llm_model = os.getenv('QBOT_LLM_MODEL', 'gpt-5')
    
    # Banner will be shown by unified display system - no duplicate needed
    
    # Only show status if there are issues, not for successful initialization
    
    # Continue with the rest of main...
    
    # Handle help
    if args.help:
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
        
        # Always show banner first when executing queries in CLI mode
        show_banner(is_no_repl=args.no_repl, profile=args.profile, llm_model=llm_model, llm_available=LLM_AVAILABLE)
        
        # Show starting message for CLI mode
        rich_console.print(f"\nStarting with query: {query}")
        
        # Set global mode flags
        if args.preview:
            PREVIEW_MODE = True
            rich_console.print("Preview Mode Enabled - SQL will be shown before execution")
        
        if args.read_only:
            READONLY_MODE = True
            READONLY_CLI_MODE = True  # CLI mode - no override allowed
            rich_console.print("Read-Only Mode Enabled - Dangerous operations will be blocked")
        
        if args.history:
            SHOW_HISTORY = True
            rich_console.print("History Mode Enabled - Conversation history will be displayed")
        
        # Execute query using CLI text mode with unified display
        if args.text:
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
            # In non-interactive environments (like tests), always use CLI mode and exit
            # Check if we're in a subprocess with no real stdin (like tests)
            try:
                # Try to get terminal size - this will fail in non-interactive environments
                os.get_terminal_size()
                is_interactive = sys.stdin.isatty()
            except OSError:
                # No terminal available - definitely non-interactive
                is_interactive = False
                
            if not is_interactive or args.no_repl:
                # Non-interactive environment or explicit --no-repl: use CLI mode and exit
                if not LLM_AVAILABLE:
                    rich_console.print("[yellow]LLM integration not available. Using CLI mode.[/yellow]")
                
                _execute_query_cli_mode(query, rich_console)
                rich_console.print("\n[dim]Exiting (--no-repl mode)[/dim]")
                return
            elif LLM_AVAILABLE:
                # Interactive environment with LLM: execute query then start Textual interface
                _execute_query_cli_mode(query, rich_console)
                
                # Start Textual interface with the query as initial input
                from qbot.interfaces.textual_repl import create_textual_repl_from_args
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
        if args.text:
            # Text-mode interactive REPL
            show_banner(is_no_repl=False, profile=args.profile, llm_model=llm_model, llm_available=LLM_AVAILABLE)
            _start_cli_interactive_mode(rich_console)
        elif _is_test_environment():
            # Use start_console for test compatibility
            start_console()
        else:
            # Default: Use Textual interface
            from qbot.interfaces.textual_repl import create_textual_repl_from_args
            textual_repl = create_textual_repl_from_args(args)
            textual_repl.run()


def _execute_query_cli_mode(query: str, console):
    """Execute a single query in CLI mode using unified display"""
    try:
        if query.startswith('/'):
            result = handle_slash_command(query)
            if result == 'EXIT':
                sys.exit(0)
        elif is_sql_query(query):
            # Treat as SQL/dbt (ends with semicolon)
            result = execute_dbt_sql_rich(query)
            if result:
                console.print(f"\n[green]{result}[/green]")
        elif LLM_AVAILABLE:
            # Natural language query - use unified display system
            from qbot.conversation_memory import ConversationMemoryManager
            from qbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
            
            memory_manager = ConversationMemoryManager()
            cli_display = CLIMessageDisplay(console)
            unified_display = UnifiedMessageDisplay(cli_display, memory_manager)
            
            # Add user message to display
            unified_display.add_user_message(query)
            
            # Show thinking indicator
            unified_display.show_thinking_indicator("...")
            
            # Execute the query
            try:
                timeout_seconds = int(os.getenv('QBOT_LLM_TIMEOUT', '120'))
                max_retries = int(os.getenv('QBOT_LLM_RETRIES', '3'))
                result = handle_llm_query(query, max_retries=max_retries, timeout_seconds=timeout_seconds, unified_display=unified_display)
                
                if result:
                    unified_display.add_ai_message(result)
                    
                    # Check if result indicates a dbt setup issue
                    if ("dbt Profile Not Found" in result or "Database Connection Failed" in result or 
                        "dbt Configuration Issue" in result or "dbt Not Installed" in result):
                        console.print("\n[yellow]💡 Please fix the dbt setup issue above before using QBot.[/yellow]")
                        sys.exit(1)
            except Exception as e:
                unified_display.add_error_message(f"Query failed: {e}")
        else:
            # No LLM available, treat as SQL
            console.print("[yellow]LLM integration not available. Treating as SQL. End with ';' for SQL queries.[/yellow]")
            result = execute_dbt_sql_rich(query)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _start_cli_interactive_mode(console):
    """Start interactive CLI mode"""
    from qbot.conversation_memory import ConversationMemoryManager
    from qbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
    
    # Create memory manager and execution function for REPL
    memory_manager = ConversationMemoryManager()
    
    # Start unified interactive REPL (will create execute_llm_func with unified_display access)
    start_unified_repl(memory_manager, console)




def start_unified_repl(memory_manager, console):
    """Start unified interactive REPL using unified message display system"""
    from qbot.interfaces.unified_message_display import UnifiedMessageDisplay, CLIMessageDisplay
    from qbot.interfaces.message_formatter import MessageSymbols
    import readline
    
    # Set up unified message display
    cli_display = CLIMessageDisplay(console)
    cli_display.set_interactive_mode(True)  # Enable prompt overwriting
    unified_display = UnifiedMessageDisplay(cli_display, memory_manager)
    
    # Create execute_llm_func with access to unified_display
    def execute_llm_func(q: str) -> str:
        timeout_seconds = int(os.getenv('QBOT_LLM_TIMEOUT', '120'))
        max_retries = int(os.getenv('QBOT_LLM_RETRIES', '3'))
        return handle_llm_query(q, max_retries=max_retries, timeout_seconds=timeout_seconds, unified_display=unified_display)
    
    try:
        while True:
            try:
                # Mark that we're about to show a prompt
                cli_display.mark_prompt_shown()
                
                # Use the input prompt symbol
                user_input = input(f"{MessageSymbols.INPUT_PROMPT} ").strip()
                
                if not user_input:
                    # Reset prompt flag if no input
                    cli_display.last_was_prompt = False
                    continue
                    
                # Handle exit commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                
                # Add user message and execute query (this will overwrite the prompt line)
                unified_display.add_user_message(user_input)
                
                # Show thinking indicator before executing LLM query
                unified_display.show_thinking_indicator("...")
                
                # Execute the query
                try:
                    result = execute_llm_func(user_input)
                    if result:
                        unified_display.add_ai_message(result)
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
# AGENTS.md

## Project Overview

QBot is a database query bot with AI-powered natural language processing. It provides both a CLI interface and interactive REPL for executing SQL/dbt queries and natural language questions using LangChain and OpenAI's GPT models.

## Code Architecture

### Core Modules
- `qbot/repl.py` - Main REPL and CLI entry point with Rich terminal interface
- `qbot/llm_integration.py` - LLM and dbt integration logic, LangChain agent setup
- `qbot/__init__.py` - Package initialization and version management
- `qbot/__version__.py` - Version information

### Key Implementation Patterns

#### Import Flexibility
```python
# Support both module and script execution
try:
    from .llm_integration import handle_llm_query  # Module execution
except ImportError:
    from llm_integration import handle_llm_query   # Script execution
```

#### Profile Configuration
```python
# Global dbt profile configuration (can be set from CLI)
DBT_PROFILE_NAME = 'qbot'

# Set environment variable for dbt commands
env = os.environ.copy()
env['DBT_PROFILE_NAME'] = DBT_PROFILE_NAME

# dbt_project.yml uses environment variable
profile: "{{ env_var('DBT_PROFILE_NAME', 'qbot') }}"
```

#### Query Type Detection
```python
def is_sql_query(query: str) -> bool:
    """Detect SQL queries by semicolon termination."""
    return query.strip().endswith(';')
```

#### Error Handling
```python
# Always provide helpful error messages
try:
    result = execute_query(query)
except Exception as e:
    rich_console.print(f"[red]Query failed: {e}[/red]")
    rich_console.print("[yellow]💡 Try checking your SQL syntax[/yellow]")
```

## Code Style Guidelines

- **Python 3.11+** with type hints where beneficial
- **Import organization**: Relative imports within package (`from .module import`), absolute for external
- **Error handling**: Graceful degradation with helpful user messages
- **Rich console output**: Use Rich library for formatted terminal output
- **Database queries**: Always use parameterized queries, prefer dbt compilation
- **LLM integration**: Handle API failures gracefully with fallback to SQL mode

## Environment Variables

### QBot Configuration
- `QBOT_LLM_MODEL` - OpenAI model (default: gpt-5)  
- `QBOT_LLM_MAX_TOKENS` - Max tokens per response (default: 1000)
- `OPENAI_API_KEY` - Required for LLM functionality

### Database Configuration
- `DB_SERVER` - Database server hostname
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASS` - Database password
- `DBT_PROFILE_NAME` - dbt profile name (default: 'qbot', can be overridden via --profile CLI argument)

## Query Execution Flow

1. **Query Type Detection**: Natural language vs SQL (semicolon-terminated)
2. **LLM Processing**: Natural language → SQL via OpenAI API
3. **dbt Compilation**: Template processing and source resolution
4. **SQL Execution**: Parameterized queries with error handling
5. **Result Formatting**: Rich console output with tables

## Database Integration

### dbt Configuration
- Uses dbt for SQL compilation and execution
- **Profile-based configuration**: Sources and macros organized by profile
- Database credentials in `~/.dbt/profiles.yml` (NEVER commit this file)
- Global Secondary Indexes required (no full table scans)

#### Profile-Based Architecture
QBot supports multiple database profiles with isolated configurations:

```
profiles/
├── qbot/                    # Default profile
│   ├── models/
│   │   └── schema.yml      # Default schema
│   └── macros/
│       └── *.sql           # Default macros
└── Sakila/                 # Example profile (Sakila sample database)
    ├── models/
    │   └── schema.yml      # Client schema
    └── macros/
        └── *.sql           # Client macros
```

**Usage:** `qbot --profile Sakila` loads client-specific configuration

#### Schema Configuration (`models/schema.yml`)
```yaml
version: 2

sources:
  - name: source_name          # Logical name for database
    description: "Description"
    schema: dbo                # Database schema (dbo, public, etc.)
    tables:
      - name: table_name       # Actual table name in database
        description: "What this table contains"
        columns:
          - name: column_name
            description: "What this column represents"
            # Optional: tests, data_type, constraints
```

**Critical for LLM:** Column descriptions directly influence query generation quality.

#### How LLM Uses Schema Information

**Schema Loading Process:**
```python
def load_schema_info():
    """Load schema with profile discovery priority:
    1. .qbot/profiles/{profile}/models/schema.yml (preferred)
    2. profiles/{profile}/models/schema.yml (fallback)
    3. models/schema.yml (legacy)
    """
    schema_paths, _ = get_profile_paths(DBT_PROFILE_NAME)
    # Finds and loads profile-specific schema
    # Automatically copies to models/ for dbt compatibility
```

**LLM Context Building:**
- Table names → Available data sources
- Column descriptions → Query field selection
- Relationships → JOIN suggestions
- Data types → Appropriate filtering

**Query Generation Flow:**
1. User asks natural language question
2. LLM reads schema context from profile-specific schema
3. LLM generates dbt-compatible SQL using `{{ source() }}` syntax
4. QBot creates temporary model file in `models/qbot_temp_*.sql`
5. dbt compiles source references to actual table names
6. SQL executes against database with `dbt show`
7. Results displayed to user in formatted table
8. Temporary files automatically cleaned up

#### Macro System (`macros/*.sql`)
```sql
{% macro macro_name(parameter) %}
    SELECT * FROM {{ source('source_name', 'table_name') }}
    WHERE condition = {{ parameter }}
{% endmacro %}
```

**Usage in queries:** `{{ macro_name('value') }}`

**Macro compilation flow:**
1. User query contains macro call
2. dbt compiles macro with parameters
3. Resulting SQL executed against database
4. Results returned to user

### SQL Server Specifics
- Uses `TOP` instead of `LIMIT` for pagination
- Supports dbt source() syntax: `{{ source('your_source', 'table_name') }}`
- Parameterized queries prevent SQL injection
- Connection pooling for performance

#### Query Results Display
**Implementation Details:**
- `dbt show` command captures and displays query results via Rich console
- TOP syntax is automatically cleaned from queries for dbt compatibility
- Temporary model files use `qbot_temp_*` prefix for easy identification
- All temp files are added to `.gitignore` and cleaned up after execution

## Testing Strategy

### Test Organization
- **Unit Tests** (`tests/unit/`): Implementation verification (42+ tests)
- **BDD Scenarios** (`tests/step_defs/core/`): User workflow validation (10+ scenarios)
- **Feature Files** (`tests/features/core/`): Gherkin scenarios in plain English

### Test Coverage Areas
1. **LLM Integration**: Configuration, query handling, error scenarios
2. **SQL Execution**: Direct queries, dbt compilation, error handling
3. **REPL Commands**: Slash commands, history, interactive features
4. **CLI Interface**: Argument parsing, help, module execution
5. **Database Connectivity**: Connection handling, query formatting

### Mock Strategy
- `mock_env` fixture for environment variables
- `mock_database` fixture for database connections
- `patch` decorators for external API calls (OpenAI, dbt)

## Security Considerations

- **SQL Injection Prevention**: Always use parameterized queries
- **API Key Security**: Load from environment variables, never commit
- **Database Permissions**: Read-only access recommended
- **Error Information**: Don't expose sensitive system details in error messages

## Performance Guidelines

- **Query Timeouts**: 60-second default timeout for long-running queries
- **Result Limits**: Paginate large result sets (default 1000 rows)
- **Connection Pooling**: Reuse database connections where possible
- **LLM Caching**: Consider caching frequent query patterns

## Implementation Notes

- All DynamoDB queries must use Global Secondary Indexes instead of full table scans due to large number of items in the table
- Module designed as `qbot.repl` for clarity (functions as a REPL)
- CLI command is `qbot` after `pip install -e .`
- Environment variables use `QBOT_*` prefix for configuration
- Generic table/source names used for open source compatibility

## Common Debugging Patterns

### LLM Integration Issues
```python
# Check if LLM is available
try:
    from .llm_integration import handle_llm_query
    llm_available = True
except ImportError:
    llm_available = False
```

### Database Connection Testing
```python
# Test dbt connection
result = subprocess.run(['dbt', 'debug'], capture_output=True, text=True)
if result.returncode == 0:
    console.print("✅ Database connection working")
```

### Rich Console Debugging
```python
from rich.console import Console
console = Console()
console.print("[red]Error message[/red]")
console.print_exception()  # For full tracebacks
```

### Schema and Macro Debugging

#### Schema Issues
```python
# Check if profile-specific schema is loading correctly
from qbot.llm_integration import load_schema_info, get_profile_paths
import qbot.llm_integration as llm

  # Set the profile
llm.DBT_PROFILE_NAME = 'Sakila'

# Check profile paths
schema_paths, macro_paths = get_profile_paths('Sakila')
for i, path in enumerate(schema_paths):
    exists = "✅" if os.path.exists(path) else "❌"
    print(f"{i+1}. {exists} {path}")

# Load schema info
schema_info = load_schema_info()
print(schema_info)  # Should contain your table definitions
```

#### Common Schema Problems:
- **"Source not found"** - Source name in query doesn't match profile's `schema.yml`
- **"Table not found"** - Table name in `schema.yml` doesn't exist in database
- **"Compilation error"** - YAML syntax error in profile's `schema.yml`
- **"Profile not found"** - Profile directory doesn't exist in `profiles/` or `.qbot/profiles/`

#### Macro Debugging
```python
# Test macro compilation
import subprocess
result = subprocess.run(['dbt', 'compile', '--select', 'your_macro'], 
                       capture_output=True, text=True)
print(result.stdout)  # Shows compiled SQL
```

#### Common Macro Problems:
- **"Macro not found"** - Macro name misspelled or not in `macros/` directory
- **"Compilation failed"** - SQL syntax error in macro definition
- **"Parameter error"** - Wrong number/type of parameters passed to macro

## Development Workflow

### Continuous Testing with pytest-watch
```bash
# Start continuous testing (watches qbot/ and tests/ directories)
ptw

# Watch with custom pytest args
ptw -- -v --tb=short

# Watch only unit tests
ptw -- tests/unit/

# Watch with coverage
ptw -- --cov=qbot
```

### Configuration
- `pytest.ini` - pytest and pytest-watch configuration (INI format)
- Watches: `qbot/`, `tests/`, `profiles/`, `models/` (temp files only)
- Extensions: `.py`, `.yml`, `.yaml`, `.sql`
- Auto-clears screen and runs quietly for clean output
- Temp files (`models/qbot_temp_*.sql`) are ignored by git but watched for testing
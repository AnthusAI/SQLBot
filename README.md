# QBot: AI-Powered Database Query Bot

QBot is a database query bot with AI-powered natural language processing. It provides both a CLI interface and interactive REPL for executing SQL/dbt queries and natural language questions using LangChain and OpenAI's GPT-5 models.

## 🚀 Key Features

- **GPT-5 Natural Language Processing** - Ask questions in plain English with advanced reasoning
- **Direct SQL and dbt execution** - Run queries with full dbt processing
- **Interactive REPL** - Rich terminal interface with slash commands
- **Profile-based configuration** - Support multiple database environments with isolated schemas
- **Multi-database support** - SQL Server, PostgreSQL, Snowflake, SQLite, and more
- **Rich terminal output** - Beautiful formatted results and error handling
- **Modular architecture** - Core SDK separated from presentation layers for multiple deployment modes

## 📦 Quick Install

```bash
# Clone and install
git clone <your-repo-url>
cd QBot
pip install -e .

# Verify installation
qbot --help
```

## ⚙️ Setup Guide

### 1. Environment Configuration
Copy `.env.example` to `.env` and configure:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# QBot LLM Configuration  
QBOT_LLM_MODEL=gpt-5
QBOT_LLM_MAX_TOKENS=10000
QBOT_LLM_VERBOSITY=low
QBOT_LLM_EFFORT=minimal

# Database Configuration
DB_SERVER=your_database_server.database.windows.net
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASS=your_database_password
```

### 2. dbt Profile Setup

**IMPORTANT**: dbt requires a `profiles.yml` file with your database connection details. This file contains sensitive credentials and should NEVER be committed to version control.

#### Create dbt Profile Directory
```bash
mkdir -p ~/.dbt
```

#### Create `~/.dbt/profiles.yml`
Create this file with your actual database credentials:

**SQL Server:**
```yaml
qbot:
  target: dev
  outputs:
    dev:
      type: sqlserver
      driver: 'ODBC Driver 17 for SQL Server'
      server: "{{ env_var('DB_SERVER') }}"
      database: "{{ env_var('DB_NAME') }}"
      schema: dbo
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
      port: 1433
      encrypt: true
      trust_cert: false
```

**PostgreSQL:**
```yaml
qbot:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('DB_SERVER') }}"
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
      port: 5432
      dbname: "{{ env_var('DB_NAME') }}"
      schema: public
```

**Snowflake:**
```yaml
qbot:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE') }}"
      database: "{{ env_var('DB_NAME') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: public
```

#### Test Your dbt Connection
```bash
dbt debug
# Should show: "All checks passed!"
```

### 3. Profile-Based Configuration

QBot supports multiple database profiles with isolated configurations. This allows you to work with different databases or environments.

#### Directory Structure
```
profiles/
├── qbot/                    # Default profile
│   ├── models/
│   │   └── schema.yml      # Default schema
│   └── macros/
│       └── *.sql           # Default macros
└── mycompany/              # Custom profile
    ├── models/
    │   └── schema.yml      # Company-specific schema
    └── macros/
        └── *.sql           # Company-specific macros
```

#### Configure Your Database Schema

Create `profiles/qbot/models/schema.yml` (or your custom profile) to define your database tables:

```yaml
version: 2

sources:
  - name: my_database
    description: "My company database"
    schema: dbo  # or public, main, etc.
    tables:
      - name: customers
        description: "Customer information table"
        columns:
          - name: customer_id
            description: "Unique customer identifier"
          - name: name
            description: "Customer full name"
          - name: email
            description: "Customer email address"
          - name: created_date
            description: "Account creation date"
      
      - name: orders
        description: "Customer orders table"
        columns:
          - name: order_id
            description: "Unique order identifier"
          - name: customer_id
            description: "Foreign key to customers table"
          - name: order_date
            description: "Date order was placed"
          - name: total_amount
            description: "Total order value"
```

#### Schema Configuration Tips

**1. Source Names:** Choose logical names that make sense:
```yaml
# Good examples:
- name: sales_db        # For sales/e-commerce data
- name: hr_system       # For HR/employee data  
- name: inventory       # For product/warehouse data
- name: analytics       # For reporting/metrics data
```

**2. Table Descriptions:** Be specific about what each table contains:
```yaml
tables:
  - name: customers
    description: "Active customer accounts with contact information and preferences"
  - name: orders  
    description: "All customer orders including cancelled and refunded transactions"
  - name: products
    description: "Product catalog with pricing, categories, and inventory levels"
```

**3. Column Descriptions:** Help the LLM understand your data:
```yaml
columns:
  - name: customer_id
    description: "Unique customer identifier (primary key)"
  - name: status
    description: "Account status: active, inactive, suspended, closed"
  - name: total_spent
    description: "Lifetime customer value in USD"
  - name: last_login
    description: "Most recent login timestamp (UTC)"
```

**Why This Matters:** The LLM reads these descriptions to:
- Generate accurate SQL queries
- Understand relationships between tables
- Suggest appropriate filters and joins
- Provide meaningful analysis

### 4. Create Custom Macros (Optional)

Create `profiles/qbot/macros/report_lookups.sql` (or your custom profile) for reusable SQL snippets:

```sql
{% macro get_customer_orders(customer_id) %}
    select * from {{ source('my_database', 'orders') }}
    where customer_id = {{ customer_id }}
    order by order_date desc
{% endmacro %}

{% macro monthly_sales_summary(year, month) %}
    select 
        count(*) as order_count,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_order_value
    from {{ source('my_database', 'orders') }}
    where year(order_date) = {{ year }}
      and month(order_date) = {{ month }}
{% endmacro %}
```

## 🎯 Usage

### Command Line Interface
```bash
# Interactive mode (default profile)
qbot

# Single query execution
qbot "How many records are in the main table?"

# Use custom profile
qbot --profile mycompany "What tables are available?"

# Interactive mode with custom profile
qbot --profile production

# Show LLM conversation context
qbot --context "your query"
```

### Interactive REPL

#### Natural Language Queries (Default)
```
> How many customers do we have?
> Show me top 5 customers by revenue
> What were our sales last month?
```

#### SQL/dbt Queries (End with semicolon)
```
> SELECT COUNT(*) FROM {{ source('my_database', 'customers') }};
> {{ get_customer_orders(12345) }}
```

#### Slash Commands
- `/help` - Show available commands
- `/tables` - List database tables  
- `/debug` - Run dbt debug
- `/run [model]` - Execute dbt models
- `/history` - Show command history
- `exit` - Exit REPL

## 🧪 Testing

### Integration Testing Setup

QBot includes a simple setup script for integration testing with the Sakila sample database. This provides a realistic dataset for testing database queries and dbt functionality.

#### Quick Setup (Recommended)
```bash
# Install integration testing dependencies
pip install -r requirements-integration.txt

# Set up Sakila SQLite database (no passwords required!)
python setup_sakila_db.py

# Verify the database is working
sqlite3 sakila.db "SELECT COUNT(*) FROM film;"
# Should return: 1000
```

This creates a `sakila.db` file with:
- **23 tables** including film, actor, customer, rental, etc.
- **1000+ records** with realistic sample data
- **No system setup required** - just a single SQLite file
- **Perfect for testing** - lightweight and portable

#### Configure dbt for SQLite Testing
```bash
# Install SQLite adapter for dbt
pip install dbt-sqlite

# Add to your ~/.dbt/profiles.yml:
sakila_test:
  target: dev
  outputs:
    dev:
      type: sqlite
      threads: 1
      database: 'database'
      schema: 'main'
      schemas_and_paths:
        main: '/path/to/your/sakila.db'
      schema_directory: '/path/to/your/'
```

#### Alternative: MySQL Setup
```bash
# For advanced testing scenarios (requires MySQL installation)
python setup_sakila_db.py --database mysql

# Note: Requires MySQL to be installed first
# Script provides installation instructions if needed
```

### Run Tests
```bash
# Run all tests once (recommended)
pytest

# Continuous testing during development
ptw

# Quick unit tests only
pytest tests/unit/ -q

# BDD scenarios only  
pytest tests/step_defs/core/ -v

# Integration tests with database
pytest tests/integration/ -v

# With coverage
pytest --cov=qbot --cov-report=html
```

### Test Coverage
- **150+ passing tests** across unit and BDD scenarios
- **GPT-5 Integration** - Configuration, query handling, error scenarios, Responses API
- **SQL Execution** - Direct queries, dbt compilation, error handling  
- **REPL Commands** - Slash commands, history, interactive features
- **CLI Interface** - Argument parsing, help, module execution
- **Database Integration** - Real database queries with sample data
- **Core SDK** - Business logic independent of presentation layers

## 🔧 Development

### Project Structure
```
qbot/
├── core/                     # Core SDK (business logic)
│   ├── __init__.py
│   ├── agent.py             # Main QBotAgent class
│   ├── config.py            # Configuration management
│   ├── types.py             # Data types and enums
│   ├── llm.py              # LLM integration
│   ├── dbt.py              # dbt integration
│   ├── safety.py           # SQL safety analysis
│   └── schema.py           # Schema and macro loading
├── interfaces/              # Presentation layers
│   └── repl/               # Rich console REPL
│       ├── __init__.py
│       ├── console.py
│       ├── commands.py
│       └── formatting.py
├── __init__.py             # Package initialization
├── __version__.py          # Version information
├── repl.py                # Legacy REPL entry point
└── llm_integration.py     # Legacy LLM integration

profiles/
├── qbot/                   # Default profile
│   ├── models/
│   │   ├── schema.yml     # Schema definitions
│   │   └── temp/          # Temporary model files
│   ├── macros/*.sql       # dbt macros
│   ├── logs/              # dbt logs
│   └── target/            # dbt artifacts
└── [custom]/              # Custom profiles
    ├── models/
    │   ├── schema.yml
    │   └── temp/
    ├── macros/*.sql
    ├── logs/
    └── target/

tests/
├── unit/                  # Unit tests
│   └── core/             # Core SDK tests
├── interfaces/           # Interface-specific tests
├── step_defs/core/      # BDD step definitions
├── features/core/       # Gherkin feature files
└── conftest.py          # Test fixtures and configuration
```

### Development Workflow
1. **Run Tests** - `pytest` to verify everything works
2. **Make Changes** - Edit code in `qbot/` directory
3. **Test Changes** - `pytest` after each change (or use `ptw` for continuous)
4. **Test CLI** - `qbot --help` to verify installation

## 🐛 Troubleshooting

### Common Issues

**"LLM integration not available"**
- Check `.env` file exists and contains `OPENAI_API_KEY`
- Verify API key is valid and has credits

**"Profile 'qbot' not found"**
- Check that `~/.dbt/profiles.yml` exists and has the correct profile name
- Verify the profile name matches `profile: 'qbot'` in `dbt_project.yml`

**"Could not connect to database"**
- Verify your `.env` file has correct database credentials
- Run `dbt debug` to test connection
- Check that required database drivers are installed

**"Source not found" errors**
- Make sure your profile's `schema.yml` source names match what you use in queries
- Verify table names exist in your actual database
- Check schema names (dbo, public, etc.) are correct

**Import errors**  
- Ensure `pip install -e .` was run successfully
- Check Python version (requires 3.11+)

### Debug Commands
```bash
# Test package import
python -c "import qbot; print('✅ Working')"

# Verify CLI installation  
which qbot

# Check dbt configuration
qbot
/debug
```

## 🔒 Security

- **SQL Injection Prevention** - Always uses parameterized queries
- **API Key Security** - Loads from environment variables, never committed
- **Database Permissions** - Read-only access recommended
- **Profile Isolation** - Client-specific configurations are gitignored

## ⚡ Performance

- **Query Timeouts** - 60-second default timeout for long-running queries
- **Result Limits** - Paginates large result sets (default 1000 rows)
- **Connection Pooling** - Reuses database connections where possible
- **LLM Caching** - Consider caching frequent query patterns

## 📋 Requirements

- **Python 3.11+**
- **OpenAI API Key** with GPT-5 access
- **Database** (SQL Server, PostgreSQL, Snowflake, SQLite, etc.)
- **dbt** for query compilation
- **LangChain 0.3.27+** and **LangChain-OpenAI 0.3.32+** for GPT-5 support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com/) for LLM integration
- [dbt](https://www.getdbt.com/) for SQL compilation and execution
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [OpenAI](https://openai.com/) for natural language processing
# QBot: Agent-Driven Database Programming

> **A New Paradigm**: Instead of writing explicit code, give an AI agent the right tools and context, then let it reason, act, and self-correct to accomplish complex database tasks.

QBot demonstrates a revolutionary approach to programming: **Tool + Context + Feedback Loop = Intelligent Automation**. Rather than manually writing SQL queries or complex data analysis scripts, you provide an AI agent with database tools (dbt, SQL execution) and rich context (schema descriptions, business logic), then engage in natural conversation to accomplish sophisticated data tasks.

## 🧠 The Agent Programming Model

### Traditional Programming
```
Developer → Explicit Instructions → Code → Database → Results
```

### Agent-Driven Programming  
```
Developer → Natural Intent → AI Agent → Tool Selection → Context Analysis → Action → Self-Correction → Results
```

**Key Insight**: When you give an agent powerful tools and comprehensive context, it becomes capable of reasoning about complex problems and correcting its own mistakes - essentially programming itself to solve your specific needs.

## 🚀 Agent Capabilities

- **Contextual Reasoning** - Understands your database schema, relationships, and business logic
- **Tool Orchestration** - Intelligently combines SQL, dbt macros, and data analysis tools
- **Self-Correction** - Learns from errors and refines approaches in real-time
- **Natural Communication** - Translates business questions into technical implementations
- **Adaptive Learning** - Builds understanding of your data patterns and preferences
- **Multi-Modal Execution** - Seamlessly switches between SQL, natural language, and dbt templating
- **Profile Intelligence** - Adapts behavior based on different database environments and schemas

## 🔧 How Agent Programming Works

### The Three Pillars

#### 1. **Tools** - Powerful Capabilities
The agent has access to sophisticated database tools:
- **dbt Integration** - Template processing, macro expansion, source resolution
- **SQL Execution** - Direct database queries with safety analysis  
- **Schema Analysis** - Understanding table relationships and data types
- **Result Formatting** - Rich console output and error handling

#### 2. **Context** - Rich Understanding
You provide the agent with comprehensive context:
- **Schema Descriptions** - What each table and column represents
- **Business Logic** - Custom macros encoding domain knowledge
- **Data Relationships** - How tables connect and relate to each other
- **Environment Profiles** - Different database configurations and rules

#### 3. **Feedback Loop** - Continuous Learning
The agent learns and adapts through interaction:
- **Error Analysis** - When queries fail, it understands why and tries alternatives
- **Result Validation** - Checks if results make sense given the context
- **Conversation Memory** - Builds understanding of your preferences and patterns
- **Iterative Refinement** - Improves approaches based on your feedback

### Example: Agent Reasoning in Action

**Your Request**: "Show me our top customers by revenue this quarter"

**Agent's Internal Process**:
1. **Context Analysis**: Reads schema to find customer and order tables
2. **Tool Selection**: Chooses dbt templating for clean, reusable SQL
3. **Query Generation**: Creates SQL using `{{ source() }}` syntax for proper table references
4. **Execution**: Runs query through dbt compilation pipeline
5. **Result Validation**: Checks if results are reasonable (positive revenue, realistic numbers)
6. **Self-Correction**: If something looks wrong, investigates and refines the approach
7. **Presentation**: Formats results in a clear, readable table

**What You See**: A simple conversation that produces sophisticated, correct results.

**What's Revolutionary**: The agent programmed itself to solve your specific problem using the tools and context you provided.

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

## 🎯 Usage: Conversing with Your Database Agent

### Command Line Interface
```bash
# Interactive mode - start a conversation with your database
qbot

# Single query - the agent analyzes and responds
qbot "How many records are in the main table?"

# Use custom profile - agent adapts to different environments
qbot --profile mycompany "What tables are available?"

# Show agent reasoning - see how it thinks through problems
qbot --context "your query"
```

### Agent Conversations in Action

#### Example 1: Business Intelligence Query
```
You: "Show me our top customers by revenue this quarter"

Agent: I'll analyze your customer and order data to find top revenue generators.
       Let me check the schema for the right tables and date fields...

       [Generates optimized SQL with proper date filtering]
       
       ┌─────────────────┬──────────────┬─────────────┐
       │ Customer Name   │ Total Revenue│ Order Count │
       ├─────────────────┼──────────────┼─────────────┤
       │ Acme Corp       │ $125,430.50  │ 23          │
       │ Global Tech     │ $98,250.75   │ 18          │
       └─────────────────┴──────────────┴─────────────┘

You: "What about last quarter for comparison?"

Agent: I'll modify the date range to show Q2 data for comparison...
       [Automatically adjusts the previous query logic]
```

#### Example 2: Agent Self-Correction
```
You: "Show me customer retention rates"

Agent: I need to calculate retention rates. Let me find customers who made 
       repeat purchases...
       
       [First attempt fails - missing date logic]
       
       I see the issue - I need to define a time window for retention.
       Let me recalculate using monthly cohorts...
       
       [Generates corrected analysis with proper cohort logic]
       
       ✅ Monthly Customer Retention Analysis
       [Shows detailed retention metrics]
```

#### Example 3: Complex Analysis with Tool Orchestration
```
You: "I need a sales performance dashboard"

Agent: I'll create a comprehensive sales analysis using multiple data sources.
       This requires several queries - let me break this down:
       
       1. Overall sales trends (using sales macro)
       2. Top products by category (joining product and order data)  
       3. Geographic performance (analyzing by region)
       4. Sales rep performance (if available in schema)
       
       [Executes multiple coordinated queries]
       [Combines results into formatted dashboard view]
       
       📊 Sales Performance Dashboard
       [Rich formatted output with multiple data views]
```

#### Direct SQL and Macro Usage
```
# The agent also handles direct SQL when you need precise control
> SELECT COUNT(*) FROM {{ source('my_database', 'customers') }};

# And can execute your custom macros intelligently  
> {{ get_customer_orders(12345) }}

# Agent understands context even in SQL mode
> SELECT * FROM orders WHERE customer_id = 12345;
Agent: I notice you're looking at the same customer. Would you like me to 
       analyze their purchase patterns or order history trends?
```

#### Agent Commands and Introspection
- `/help` - Agent explains its capabilities and available tools
- `/tables` - Agent analyzes and describes your database schema
- `/debug` - Agent runs diagnostics and reports system health  
- `/run [model]` - Agent executes dbt models with intelligent dependency handling
- `/history` - Agent shows conversation context and learning patterns
- `exit` - End the agent session

## 🧪 Testing the Agent

### Agent Validation with Real Data

QBot includes comprehensive testing that validates the agent's reasoning capabilities using the Sakila sample database. This provides a realistic environment for testing how the agent handles complex queries, error correction, and tool orchestration.

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

### Agent Testing Coverage
- **150+ passing tests** validating agent intelligence and reliability
- **Reasoning Validation** - Tests agent's ability to understand context and generate appropriate queries
- **Error Recovery** - Validates self-correction when queries fail or produce unexpected results
- **Tool Orchestration** - Tests intelligent combination of SQL, dbt, and analysis tools
- **Context Adaptation** - Ensures agent adapts behavior based on different schemas and profiles
- **Conversation Memory** - Validates learning and adaptation over multi-turn conversations
- **Safety Analysis** - Tests agent's ability to detect and prevent dangerous operations
- **Multi-Modal Execution** - Validates seamless switching between natural language and SQL modes

## 🔧 Development: Building Agent-Driven Systems

### Agent Architecture
```
qbot/
├── core/                     # Agent Intelligence Layer
│   ├── __init__.py
│   ├── agent.py             # Main QBotAgent - orchestrates reasoning and tool usage
│   ├── config.py            # Agent configuration and behavior settings
│   ├── types.py             # Data structures for agent communication
│   ├── llm.py              # Language model integration for reasoning
│   ├── dbt.py              # Database tool integration and execution
│   ├── safety.py           # Agent safety analysis and guardrails
│   └── schema.py           # Context loading and understanding
├── interfaces/              # Human-Agent Interaction Layer
│   └── repl/               # Conversational interface
│       ├── __init__.py
│       ├── console.py      # Rich conversation display
│       ├── commands.py     # Agent command interpretation
│       └── formatting.py   # Agent response formatting
├── __init__.py             # Package initialization
├── __version__.py          # Version information
├── repl.py                # Legacy REPL entry point
└── llm_integration.py     # Legacy LLM integration

profiles/
├── qbot/                   # Default agent context
│   ├── models/
│   │   ├── schema.yml     # Database context for agent understanding
│   │   └── temp/          # Agent-generated temporary models
│   ├── macros/*.sql       # Business logic tools for agent
│   ├── logs/              # Agent execution logs
│   └── target/            # Agent compilation artifacts
└── [custom]/              # Environment-specific agent contexts
    ├── models/
    │   ├── schema.yml     # Custom database context
    │   └── temp/          # Environment-specific temp files
    ├── macros/*.sql       # Environment-specific tools
    ├── logs/              # Environment logs
    └── target/            # Environment artifacts

tests/
├── unit/                  # Agent component tests
│   └── core/             # Core agent intelligence tests
├── interfaces/           # Human-agent interaction tests
├── step_defs/core/      # Agent behavior validation (BDD)
├── features/core/       # Agent capability specifications (Gherkin)
└── conftest.py          # Agent testing framework
```

### Agent Development Workflow
1. **Validate Agent** - `pytest` to ensure agent reasoning works correctly
2. **Enhance Capabilities** - Add new tools or improve context understanding
3. **Test Behavior** - `pytest` after changes (or `ptw` for continuous validation)
4. **Interact with Agent** - `qbot --help` to test conversational interface
5. **Refine Context** - Update schemas and macros to improve agent performance

## 🐛 Agent Troubleshooting

### Agent Behavior Issues

**"Agent seems confused or gives wrong answers"**
- Check that your `schema.yml` has detailed, accurate descriptions
- Verify table and column descriptions match your actual data
- The agent's intelligence depends heavily on context quality

**"Agent can't find tables or data"**
- Ensure your profile's `schema.yml` source names are correct
- Verify table names exist in your actual database  
- Check that schema names (dbo, public, etc.) match your database
- Run `/tables` command to see what the agent can access

**"Agent reasoning seems broken"**
- Check `.env` file exists and contains valid `OPENAI_API_KEY`
- Verify API key has sufficient credits and GPT-5 access
- Try `--context` flag to see agent's internal reasoning process

**"Agent can't connect to database"**
- Verify your `.env` file has correct database credentials
- Run `/debug` command to test connection through the agent
- Check that required database drivers are installed
- Ensure `~/.dbt/profiles.yml` exists with correct profile configuration

**"Agent gives inconsistent results"**
- This may indicate ambiguous schema descriptions
- Add more specific column descriptions to improve context
- Check for naming conflicts in your database schema

### Agent Diagnostic Commands
```bash
# Test agent system health
python -c "import qbot; print('✅ Agent system ready')"

# Verify agent CLI installation  
which qbot

# Interactive agent diagnostics
qbot
/debug    # Agent runs comprehensive system check
/tables   # Agent analyzes available database context
/help     # Agent explains its current capabilities
```

## 🔒 Agent Security & Safety

- **SQL Injection Prevention** - Agent uses parameterized queries and safety analysis
- **API Key Security** - Agent credentials loaded from environment, never committed
- **Database Permissions** - Agent operates with read-only access (recommended)
- **Query Safety Analysis** - Agent analyzes queries for potential risks before execution
- **Profile Isolation** - Agent contexts are environment-specific and gitignored
- **Conversation Privacy** - Agent interactions can be configured for data privacy compliance

## ⚡ Agent Performance & Optimization

- **Intelligent Caching** - Agent learns and caches frequent query patterns
- **Query Optimization** - Agent generates efficient SQL based on schema understanding
- **Connection Management** - Agent reuses database connections intelligently
- **Result Streaming** - Agent handles large datasets with pagination (default 1000 rows)
- **Context Efficiency** - Agent loads only relevant schema information per conversation
- **Adaptive Timeouts** - Agent adjusts query timeouts based on complexity (60s default)

## 📋 Agent System Requirements

- **Python 3.11+** - Modern Python for optimal agent performance
- **OpenAI API Key** with GPT-5 access - Powers agent reasoning and conversation
- **Database** (SQL Server, PostgreSQL, Snowflake, SQLite, etc.) - Agent data source
- **dbt** for query compilation - Agent's primary database tool
- **LangChain 0.3.27+** and **LangChain-OpenAI 0.3.32+** - Agent framework and LLM integration

## 🤝 Contributing to Agent Development

1. Fork the repository
2. Create a feature branch for agent enhancements
3. Implement new agent capabilities or improve existing reasoning
4. Add tests that validate agent behavior and intelligence
5. Ensure all agent validation tests pass
6. Submit a pull request with clear description of agent improvements

### Areas for Agent Enhancement
- **New Tool Integration** - Add capabilities like data visualization, export, or advanced analytics
- **Improved Reasoning** - Enhance context understanding and query generation logic
- **Better Error Recovery** - Improve agent's ability to self-correct and learn from mistakes
- **Extended Context** - Support for more database types, schema patterns, or business domains

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

This agent-driven programming paradigm is built on:
- [LangChain](https://langchain.com/) - Agent framework and tool orchestration
- [dbt](https://www.getdbt.com/) - Powerful database tooling for agent execution
- [Rich](https://rich.readthedocs.io/) - Beautiful agent-human conversation interface
- [OpenAI](https://openai.com/) - Advanced reasoning capabilities via GPT-5

**Special Recognition**: The concept of giving agents tools + context + feedback loops to create intelligent automation represents a fundamental shift in how we think about programming and human-computer interaction.
# ✦SQLBot: Your AI Database Analyst

**"If you give an agent a tool, then nobody has to fish."**

SQLBot is a new kind of interface for your database. Instead of writing SQL queries yourself, you delegate high-level analytical tasks to an AI agent. It reasons through your request, executing a chain of queries and analyzing the results until it arrives at a complete answer—all while keeping your data safe with built-in safeguards.

It represents the next logical layer on the modern data stack, building directly on the power of SQL and dbt.

### The Problem with Raw SQL

Most people use SQL through apps.  Maybe you're comfortable writing raw SQL queries if you're a wizard.  Most people aren't.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="documentation/diagrams/images/architecture/DB+SQL-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="documentation/diagrams/images/architecture/DB+SQL.png">
  <img alt="SQL Layer: The foundation layer showing raw SQL complexity" src="documentation/diagrams/images/architecture/DB+SQL.png">
</picture>

Sure, SQL powers most relational databases—it's incredibly powerful. But here's the thing: even simple questions can turn into sprawling queries with multiple joins and cryptic table relationships. Want to see what a "basic" customer lookup actually looks like? Here's what you'd need to write just to get someone's rental history from the Sakila database:

```sql
-- Raw SQL: Get rental history for customer 526
SELECT
  f.title,
  f.description,
  r.rental_date
FROM customer c
JOIN rental r
  ON c.customer_id = r.customer_id
JOIN inventory i
  ON r.inventory_id = i.inventory_id
JOIN film f
  ON i.film_id = f.film_id
WHERE
  c.customer_id = 526
ORDER BY
  r.rental_date DESC;
```

This is hard to reuse and requires every user to understand the database's join logic.

### Enter dbt: Sharing Database Knowledge

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="documentation/diagrams/images/architecture/DB+SQL+DBT-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="documentation/diagrams/images/architecture/DB+SQL+DBT.png">
  <img alt="dbt Layer: Knowledge sharing layer making database expertise accessible to business users" src="documentation/diagrams/images/architecture/DB+SQL+DBT.png">
</picture>

Here's where dbt changes the game. Those database wizards who understand all the table relationships? They can package their knowledge into macros and schemas that business users can actually work with. That ugly query above becomes a simple, self-documenting function:

```sql
-- In a file like `macros/get_customer_rental_history.sql`
{% macro get_customer_rental_history(customer_id) %}
  SELECT
    f.title,
    f.description,
    r.rental_date
  FROM customer c
  JOIN rental r
    ON c.customer_id = r.customer_id
  JOIN inventory i
    ON r.inventory_id = i.inventory_id
  JOIN film f
    ON i.film_id = f.film_id
  WHERE
    c.customer_id = {{ customer_id }}
  ORDER BY
    r.rental_date DESC;
{% endmacro %}
```

Suddenly, business users can access complex database operations without needing to understand the underlying join logic:

```sql
-- A business user can now write this instead:
{{ get_customer_rental_history(customer_id=526) }}
```

The real magic happens in dbt's `schema.yml` files—they're like institutional memory for your database. Wizards document what each table and column actually means in plain English, creating a shared vocabulary that makes databases accessible to entire teams.

### SQLBot: Adding Intelligence & Safety

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="documentation/diagrams/images/architecture/DB+SQL+DBT+agent-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="documentation/diagrams/images/architecture/DB+SQL+DBT+agent.png">
  <img alt="SQLBot Layer: Intelligence and safety layer with AI agent on top of the stack" src="documentation/diagrams/images/architecture/DB+SQL+DBT+agent.png">
</picture>

SQLBot adds the final layer: an AI agent that uses the structure dbt provides while keeping your data protected. The agent is armed with two crucial pieces of information from your dbt profile:

- **The Schema (`schema.yml`)**: It reads your table and column descriptions to understand what your data means.
- **The Macros (`macros/*.sql`)**: It learns your reusable business logic to solve complex tasks more efficiently.

**Built-in Safeguards**: SQLBot includes read-only protections and query validation to prevent dangerous operations like `DROP`, `DELETE`, or `UPDATE` commands, ensuring your data stays safe while you focus on analysis rather than syntax.

This layered approach gives you the best of all worlds: the raw power of SQL, the structure and reusability of dbt, the conversational intelligence of an AI Agent, and the peace of mind that comes with built-in safety controls.

### **The Result: A Real-World Example**

Because the agent understands this stack, you no longer write SQL or dbt. You state a business goal.

**You:** "I want to run a 'customer of the month' promotion. First, identify our single best customer based on their total lifetime payment amount. Once you have that customer, find out which actor they have rented the most movies from. I'll need the customer's full name, their email address, the full name of their favorite actor, and the count of films they've rented by that actor."

SQLBot accepts the task and begins its reasoning process, writing and executing the necessary SQL.

**Query 1: Find the Top Customer**

```sql
SELECT p.customer_id, c.first_name, c.last_name, c.email, SUM(p.amount) AS total_payments
FROM payment p
JOIN customer c ON p.customer_id = c.customer_id
GROUP BY p.customer_id
ORDER BY total_payments DESC
LIMIT 1
```

```
✔ Query passes safeguard against dangerous operations.
▷ Query Result → Success: Query completed
```

**Query 2: Find Their Favorite Actor**

```sql
WITH cust_rentals AS (
  SELECT r.rental_id, r.inventory_id
  FROM rental r
  WHERE r.customer_id = 526
), films AS (
  SELECT cr.rental_id, i.film_id
  FROM cust_rentals cr
  JOIN inventory i ON cr.inventory_id = i.inventory_id
), film_actor_map AS (
  SELECT f.rental_id, fa.actor_id
  FROM films f
  JOIN film_actor fa ON f.film_id = fa.film_id
)
SELECT a.first_name || ' ' || a.last_name AS actor_name, COUNT(*) AS rentals_by_actor
FROM film_actor_map fam
JOIN actor a ON fam.actor_id = a.actor_id
GROUP BY fam.actor_id
ORDER BY rentals_by_actor DESC, actor_name ASC
LIMIT 1
```

```
✔ Query passes safeguard against dangerous operations.
▷ Query Result → Success: Query completed
```

It then delivers a synthesized answer, even suggesting the next logical step.

**SQLBot:**
> Got it — we'll find the top customer by total payments, then their most-rented actor.
>
> **Approach:**
> - Query total lifetime payments by customer to get the top customer.
> - For that customer, join rentals → inventory → film_actor → actor to find the actor with the highest rental count.
>
> **Results:**
> - **Customer:** KARL SEAL  
> - **Email:** KARL.SEAL@sakilacustomer.org  
> - **Favorite actor:** UMA WOOD  
> - **Films rented from that actor:** 6
>
> **Next step suggestion:**  
> Want a quick profile for this customer (total rentals, average spend, preferred categories)?

### **From SQL Syntax to Business Questions**

The traditional approach requires you to:
1. **Write SQL** - Master complex syntax and join logic
2. **Debug queries** - Fix syntax errors and performance issues  
3. **Interpret results** - Manually analyze and synthesize findings

SQLBot flips this model. Instead of writing SQL, you **delegate analysis**:
1. **Ask business questions** - "Who are our top customers this quarter?"
2. **Let the agent work** - It writes, executes, and chains multiple queries safely
3. **Get insights** - Receive synthesized answers with suggested next steps

The result? You spend time on strategy and insights, not syntax and debugging.

## Key Features

- **Multi-Step Task Resolution**: Handles complex tasks by executing a sequence of queries in a single turn.
- **Context-Aware**: Uses your `schema.yml` and dbt macros to generate accurate, business-aware queries.
- **Built-in Safety**: Read-only safeguards prevent dangerous operations while allowing full analytical power.
- **Iterative & Interactive**: Reasons through data step-by-step, recovers from errors, and allows for conversational follow-ups.
- **Data Export**: Export query results to CSV, Excel, or Parquet formats with simple natural language commands.
- **Direct SQL Passthrough**: For experts, end any query with a semicolon (`;`) to bypass the agent and run it directly.
- **Profile-Based**: Easily switch between different database environments (`--profile mycompany`).
- **Broad Database Support**: Works with SQL Server, PostgreSQL, Snowflake, SQLite, and more.

## Data Export Capabilities

SQLBot now includes powerful data export functionality that allows you to save query results in multiple formats:

### Supported Export Formats

- **CSV** (default): Comma-separated values, perfect for spreadsheet applications
- **Excel**: Native `.xlsx` format with proper formatting
- **Parquet**: Columnar format optimized for analytics and big data workflows

### How to Export Data

After running any successful query, you can export the results using natural language:

```bash
# After running a query, simply ask to export
> "Show me the top 10 customers by revenue"
[Query executes and shows results]

> "Export this to CSV"
> "Save this as Excel"
> "Export to Parquet format"
> "Save this to /path/to/my/reports as Excel"
```

### Export Features

- **Automatic File Naming**: Files are automatically named with query index and timestamp (e.g., `sqlbot_query_1_20241201_143022.csv`)
- **Smart Location**: Exports to `./tmp` directory by default (created automatically)
- **Custom Locations**: Specify any directory path for your exports
- **Only Latest Results**: Exports the most recent successful query results for data integrity
- **Error Handling**: Clear error messages if no data is available or export fails

### Export Examples

```bash
# Basic export (defaults to CSV in ./tmp directory)
> "export the results"

# Specify format
> "export this as Excel"
> "save as Parquet"

# Custom location
> "export to CSV in /Users/john/reports"
> "save this Excel file to ~/Desktop"

# After a specific query
> "Get monthly sales by region"
[Results displayed]
> "Export this to Excel so I can share with the team"
```

### File Structure

Exported files follow a consistent naming pattern:
```
sqlbot_query_{index}_{timestamp}.{extension}

Examples:
- sqlbot_query_1_20241201_143022.csv
- sqlbot_query_3_20241201_144517.xlsx
- sqlbot_query_5_20241201_145203.parquet
```

This ensures you can easily track which export corresponds to which query and when it was created.

## Install & Setup

### 1. Installation

```bash
pip install sqlbot

# Verify installation
sqlbot --help
```

### 2. Environment (.env)

Create a `.env` file in the root directory with your API key and database credentials.

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# SQLBot LLM Configuration
SQLBOT_LLM_MODEL=gpt-5
SQLBOT_LLM_MAX_TOKENS=10000
SQLBOT_LLM_TEMPERATURE=0.1
SQLBOT_LLM_VERBOSITY=low
SQLBOT_LLM_EFFORT=minimal
SQLBOT_LLM_PROVIDER=openai

# Optional: SQLBot Behavior Configuration
# SQLBOT_READ_ONLY=true
# SQLBOT_PREVIEW_MODE=false
# SQLBOT_QUERY_TIMEOUT=60
# SQLBOT_MAX_ROWS=1000
```

### 3. Database Connection (dbt profiles)

SQLBot supports both **local** and **global** dbt profile configurations:

- **Local profiles** (recommended): Create `.dbt/profiles.yml` in your project directory for project-specific configurations
- **Global profiles**: Use `~/.dbt/profiles.yml` for system-wide configurations

SQLBot automatically detects and prioritizes local profiles when available. This allows you to have different database configurations per project while maintaining a global fallback.

<details>
<summary>Click to see example dbt configurations</summary>

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
      dbname: "{{ env_var('DB_NAME') }}"
```

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
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASS') }}"
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
      database: "{{ env_var('DB_NAME') }}"
```
</details>

Then, test your connection: `dbt debug`

### 4. Teach the Agent Your Schema

This is the most important step. Create a `profiles/qbot/models/schema.yml` file. The agent's performance depends heavily on clear, detailed descriptions for your tables and columns.

```yaml
version: 2
sources:
  - name: my_database
    schema: dbo
    tables:
      - name: customers
        description: "Contains one record per customer, including personal details and account creation date."
        columns:
          - name: customer_id
            description: "Unique identifier for each customer (Primary Key)."
```

## Usage

```bash
# Start interactive mode
sqlbot

# Delegate a task from the command line
sqlbot "How many new customers did we get last month?"
```

### Project-Specific Configuration

SQLBot supports project-specific configurations using **local dbt profiles**:

```bash
# Create a local .dbt folder in your project
mkdir .dbt

# Create project-specific profiles
cat > .dbt/profiles.yml << EOF
my_project:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: myuser
      password: mypass
      dbname: myproject_db
      port: 5432
EOF

# SQLBot will automatically detect and use the local configuration
sqlbot --profile my_project
```

**Benefits of local profiles:**
- Keep database credentials with your project
- Different configurations per project/environment
- Team members can share the same profile setup
- No interference with global dbt configurations

When SQLBot starts, you'll see confirmation in the banner:
- `Profiles: Local .dbt/profiles.yml (detected)` - Using project-specific config
- `Profiles: Global ~/.dbt/profiles.yml` - Using system-wide config

## Quick Start with Sample Data

**🚀 Recommended:** Use our standalone demo project for the easiest SQLBot experience:

```bash
# Clone the demo project (includes everything you need)
git clone https://github.com/AnthusAI/SQLBot-Sakila-SQLite
cd SQLBot-Sakila-SQLite

# Install SQLBot and dependencies
pip install -e .

# Set up the Sakila database (SQLite - no server required!)
sqlbot setup sakila

# Start exploring with natural language queries
sqlbot --profile Sakila
```

**Try these queries:**
- "How many films are in each category?"
- "Which actors appear in the most films?"
- "Show me customers from California"

This demo project is also **the perfect template** for setting up SQLBot with your own database - just replace the Sakila data with your own!

### Alternative: Install from main repository

```bash
# Install SQLBot
pip install sqlbot

# Clone the main repository for sample data setup
git clone https://github.com/AnthusAI/SQLBot
cd SQLBot

# Install database dependencies (SQLite adapter for dbt)
pip install -r requirements-integration.txt

# Set up the sample Sakila database (SQLite - no server required!)
python scripts/setup_sakila_db.py

# Start exploring with sample data
sqlbot --profile Sakila
```

**Why SQLite?** No database server installation required! The Sakila database runs entirely from a single `.db` file with:
- **1,000 films** with ratings, categories, and descriptions
- **599 customers** with rental history and payments
- **16,000+ rental transactions** for realistic testing
- **Complete relational structure** with actors, categories, inventory

You can immediately start asking natural language questions like:
- "Who are the top 5 customers by total payments?"
- "Which films are most popular by rental count?"
- "Show me rental trends by month"
- "What's the average rental duration by film category?"

## Using the Demo as a Template for Your Own Database

The [SQLBot-Sakila-SQLite demo project](https://github.com/AnthusAI/SQLBot-Sakila-SQLite) demonstrates the **recommended project structure** for SQLBot:

```
your-database-project/
├── .sqlbot/                    # All SQLBot configuration
│   ├── config.yml             # SQLBot settings
│   ├── agents/                # Custom database knowledge
│   └── profiles/YourDB/       # Database files and config
├── .dbt/profiles.yml          # Local dbt connection config
├── pyproject.toml             # Python dependencies
└── README.md                  # Project documentation
```

**Key benefits of this structure:**
- ✅ **Clean separation** - Keep your database project separate from SQLBot infrastructure
- ✅ **Security** - Store proprietary database projects in private repositories
- ✅ **No junk files** - All SQLBot files contained in `.sqlbot/` folder
- ✅ **Self-contained** - Everything needed for your database in one project
- ✅ **Version control** - Track database queries, agents, and configuration

**To create your own:**
1. Copy the demo project structure
2. Replace Sakila database with your own in `.sqlbot/profiles/YourDB/`
3. Update `.dbt/profiles.yml` with your database connection
4. Add custom agents in `.sqlbot/agents/` with your database knowledge
5. Configure `.sqlbot/config.yml` for your preferences

## For Developers

<details>
<summary>Testing, Development, and Troubleshooting</summary>

### Releases & Versioning

SQLBot uses [Semantic Release](https://semantic-release.gitbook.io/) for automated versioning and publishing. Releases are automatically triggered when commits are pushed to the `main` branch.

#### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types that trigger releases:**
- `feat:` - New feature (minor version bump)
- `fix:` - Bug fix (patch version bump)  
- `feat!:` or `fix!:` - Breaking change (major version bump)
- `BREAKING CHANGE:` in footer - Major version bump

**Other types (no release):**
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build/tooling changes

**Examples:**
```bash
feat: add support for PostgreSQL databases
fix: resolve connection timeout issues
feat!: change CLI command from qbot to sqlbot
docs: update installation instructions
```

### Testing

SQLBot includes comprehensive unit and integration tests.

#### Unit Tests
Run unit tests for core functionality:
```bash
pytest
```

#### Integration Tests
Integration tests verify end-to-end functionality against the Sakila sample database. These tests cover database connectivity, query routing, safeguards, and real-world usage scenarios.

**Quick setup:**
```bash
pip install -r requirements-integration.txt
python scripts/setup_sakila_db.py
pytest -m "integration" tests/integration/
```

**📖 For detailed integration testing documentation, see [tests/integration/README.md](tests/integration/README.md)**

This includes:
- Complete setup instructions
- Test file organization and coverage
- Troubleshooting guide
- Environment configuration options

### Project Structure

- `qbot/core/`: Contains the core agent logic (reasoning loop, tool usage).
- `qbot/interfaces/`: User interface code (CLI, REPL).
- `profiles/`: Profile-specific contexts for the agent (schemas, macros).
- `tests/`: Agent validation scenarios.

### Troubleshooting

- **Agent gives wrong answers or fails to find tables**: The most likely cause is an unclear or incorrect `schema.yml`. Ensure your table and column descriptions are detailed and accurate.
- **Connection issues**: Double-check your `.env` and `~/.dbt/profiles.yml` files. Run `sqlbot /debug` to test the connection.
- **API errors**: Verify your `OPENAI_API_KEY` is correct in `.env`.

</details>

## Security

- **SQL Injection**: Mitigated by using dbt's compilation, which inherently parameterizes inputs.
- **Credentials**: API keys and database passwords are loaded securely from environment variables.
- **Permissions**: We strongly recommend running SQLBot with a read-only database user.

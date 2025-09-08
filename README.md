# QBot: Agent-Driven Database Queries

Relational databases are powerful. Writing SQL is tedious. QBot adds AI that writes SQL for you and runs it with dbt.

Instead of a single query, you give QBot a task. It plans, writes, and runs a series of dbt queries against your database. It uses your schema and macros. It retries on errors and builds follow-ups.

What is dbt? It's SQL plus Jinja templating. You can write macros and use them inside SQL. QBot uses that power to generate better queries.

### A story (Sakila)

You manage the Sakila video store. New release rentals are down. You ask:

"Find the cause and tell me what to do."

QBot reads your schema and macros. It runs a chain of dbt queries:
1) Rentals by month for recent films, compared to last quarter
2) Categories with the largest drop
3) Inventory by store for those categories
4) Customers who stopped renting them

It returns a short summary and next steps:
- Restock popular recent titles in Store 2
- Run a weekend promo on Family titles
- Email lapsed customers who liked Action

You say: "Show me the customers list."

QBot runs the follow-up query and prints the table.

## The Agent Model

### Before
```
You → Write SQL → Database → Results
```

### Now
```
You → Ask Agent → Agent Executes dbt Queries → Results
```

The agent writes queries itself. You just talk.

## What It Does

- Reads your database schema
- Uses your dbt macros
- Writes and runs SQL (dbt)
- Retries errors and chains follow-ups
- Learns your patterns
- Works with multiple databases

## How It Works

### Tool
It executes dbt queries.

### Context  
Schema and macros describe your tables and rules.

### Loop
It retries on errors and builds follow-up queries when needed.

### Example (Sakila)

Task: "Find why new releases are down this quarter and suggest actions."

QBot:
1) Checks film release counts by month vs last quarter
2) Finds top-grossing categories and their recent trends
3) Looks at inventory per store and stockouts
4) Joins rentals to customers to see churn by category
5) Produces a short summary and follow-up queries

It writes and runs multiple dbt queries, each using your schema and macros, and links results across steps.

## Install

```bash
git clone <your-repo-url>
cd QBot
pip install -e .
qbot --help
```

## Setup

### Environment
Create `.env`:

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

### Database Connection

Create `~/.dbt/profiles.yml`:

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

Test connection:
```bash
dbt debug
```

### Schema Configuration

QBot needs to understand your database structure.

Create `profiles/qbot/models/schema.yml`:

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

### Custom Macros (Optional)

Create `profiles/qbot/macros/report_lookups.sql`:

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

## Usage

```bash
qbot                                    # Interactive mode
qbot "How many customers do we have?"   # Single query
qbot --profile mycompany               # Custom profile
```

### Examples

```
> How many customers do we have?
> Show me top 5 customers by revenue
> What were our sales last month?
```

Direct SQL works too:
```
> SELECT COUNT(*) FROM {{ source('my_database', 'customers') }};
> {{ get_customer_orders(12345) }}
```

Commands:
- `/help` - Show commands
- `/tables` - List tables  
- `/debug` - Test connection
- `/history` - Show history
- `exit` - Quit

## Testing

```bash
pip install -r requirements-integration.txt
python setup_sakila_db.py
pytest
```

Test coverage includes agent reasoning, error recovery, and tool usage.

## Development

```
qbot/core/          # Agent logic
qbot/interfaces/    # User interface
profiles/           # Database contexts
tests/              # Agent validation
```

Workflow:
1. Run `pytest`
2. Make changes
3. Test with `qbot`

## Troubleshooting

**Agent gives wrong answers**: Check your `schema.yml` descriptions.

**Can't find tables**: Verify table names in `schema.yml` match database.

**Connection issues**: Check `.env` and `~/.dbt/profiles.yml`.

**API errors**: Verify `OPENAI_API_KEY` in `.env`.

Debug commands:
```bash
qbot
/debug
/tables
```

## Security

- Uses parameterized queries
- API keys from environment variables
- Read-only database access recommended

## Requirements

- Python 3.11+
- OpenAI API key with GPT-5 access
- Database (SQL Server, PostgreSQL, Snowflake, SQLite)
- dbt
- LangChain 0.3.27+

## Contributing

1. Fork repository
2. Add agent capabilities
3. Add tests
4. Submit pull request

## License

[Add license here]

## Built With

- [LangChain](https://langchain.com/) - Agent framework
- [dbt](https://www.getdbt.com/) - Database tooling
- [Rich](https://rich.readthedocs.io/) - Terminal interface
- [OpenAI](https://openai.com/) - GPT-5 reasoning
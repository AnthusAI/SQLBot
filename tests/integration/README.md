# QBot Integration Tests

This directory contains integration tests that require actual database connections and verify QBot functionality against real databases.

## Quick Start

1. **Install integration dependencies:**
   ```bash
   pip install -r requirements-integration.txt
   ```

2. **Set up Sakila test database:**
   ```bash
   python setup_sakila_db.py --database sqlite
   ```

3. **Run integration tests:**
   ```bash
   # Use the integration test script (recommended)
   ./test_integration.sh
   
   # Or run directly with pytest
   pytest -m "integration" tests/integration/
   ```

## Test Database: Sakila

The integration tests use the **Sakila sample database**, a well-known DVD rental store database that provides:

- **1000 films** with ratings, categories, and rental information
- **599 customers** with rental history and payments
- **16,000+ rental transactions** for realistic data testing
- **Complete relational structure** with actors, categories, inventory, stores, and staff

### Why Sakila?

- **Standardized**: Industry-standard sample database used by MySQL, PostgreSQL, and SQLite
- **Realistic**: Contains real-world business data patterns
- **Comprehensive**: Tests complex queries, joins, and aggregations
- **Lightweight**: SQLite version requires no server setup
- **Well-documented**: Extensive schema with proper relationships

## Setup Instructions

### Automatic Setup (Recommended)

```bash
# Install dependencies and set up Sakila database
pip install -r requirements-integration.txt
python setup_sakila_db.py --database sqlite
```

This creates:
- `sakila.db` - SQLite database file with all Sakila data
- `~/.dbt/profiles.yml` - dbt configuration for Sakila profile
- Profile-specific schema and macros in `profiles/Sakila/`

### Manual Setup

If you prefer manual setup or need MySQL instead of SQLite:

```bash
# For MySQL (requires MySQL server)
python setup_sakila_db.py --database mysql --user root --password your_password

# For existing Sakila database, just configure dbt profiles
# Edit ~/.dbt/profiles.yml to add your database connection
```

## Running Tests

### Basic Test Execution

```bash
# Run all integration tests (recommended)
./test_integration.sh

# Or run directly with pytest
pytest -m "integration" tests/integration/

# Run with verbose output
pytest -m "integration" tests/integration/ -v

# Run specific test file
pytest tests/integration/test_sakila_integration.py

# Run tests with specific markers
pytest tests/integration/ -m "sakila"
pytest tests/integration/ -m "dbt"
pytest tests/integration/ -m "llm"
```

### Test Categories and Markers

Tests are automatically marked based on their functionality:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.sakila` - Tests requiring Sakila database
- `@pytest.mark.dbt` - Tests requiring dbt functionality
- `@pytest.mark.llm` - Tests requiring OpenAI API (or mocked)

### Environment Variables

```bash
# Optional: Configure LLM testing
export OPENAI_API_KEY=your_api_key_here

# Optional: Use different dbt profile
export DBT_PROFILE_NAME=Sakila

# Optional: Configure LLM model for testing
export QBOT_LLM_MODEL=gpt-3.5-turbo
export QBOT_LLM_MAX_TOKENS=500
```

## Test Structure

### `test_sakila_integration.py`

Comprehensive integration tests covering:

1. **Database Connectivity**
   - SQLite database file accessibility
   - Data integrity verification (1000 films, 599 customers, etc.)
   - Schema structure validation

2. **Schema Integration**
   - Profile path discovery (`profiles/Sakila/`)
   - Schema loading from `profiles/Sakila/models/schema.yml`
   - dbt source reference validation

3. **dbt Integration**
   - dbt debug and connection testing
   - Query compilation with `{{ source('sakila', 'table') }}` syntax
   - Macro execution (`get_films_by_category`, `get_customer_rentals`, etc.)

4. **LLM Integration**
   - Natural language query processing with Sakila context
   - Schema information injection into LLM prompts
   - End-to-end query flow (LLM → dbt → SQLite → results)

5. **REPL Integration**
   - Command-line argument parsing (`--profile Sakila`)
   - Profile-specific functionality
   - Direct SQL query execution

### `conftest.py`

Shared test configuration providing:

- **Fixtures**: Database setup, environment configuration, mocking
- **Markers**: Automatic test categorization
- **Skip Logic**: Intelligent test skipping based on available dependencies
- **Environment Management**: Clean setup/teardown of test environment

## Test Data and Queries

### Sample Sakila Queries

The tests verify QBot can handle realistic business queries:

```sql
-- Film catalog queries
SELECT COUNT(*) FROM {{ source('sakila', 'film') }} WHERE rating = 'PG-13';

-- Customer analysis
SELECT c.first_name, c.last_name, COUNT(r.rental_id) as rental_count
FROM {{ source('sakila', 'customer') }} c
LEFT JOIN {{ source('sakila', 'rental') }} r ON c.customer_id = r.customer_id
GROUP BY c.customer_id;

-- Revenue analysis
SELECT c.name as category, SUM(p.amount) as total_revenue
FROM {{ source('sakila', 'category') }} c
JOIN {{ source('sakila', 'film_category') }} fc ON c.category_id = fc.category_id
JOIN {{ source('sakila', 'film') }} f ON fc.film_id = f.film_id
JOIN {{ source('sakila', 'inventory') }} i ON f.film_id = i.film_id
JOIN {{ source('sakila', 'rental') }} r ON i.inventory_id = r.inventory_id
JOIN {{ source('sakila', 'payment') }} p ON r.rental_id = p.rental_id
GROUP BY c.category_id, c.name;
```

### Macro Testing

Tests verify Sakila-specific macros work correctly:

- `get_films_by_category('Action')` - Films in specific category
- `get_customer_rentals(123)` - Customer rental history
- `get_top_actors_by_film_count(10)` - Most prolific actors
- `get_revenue_by_category()` - Revenue analysis by film category
- `get_overdue_rentals()` - Overdue rental tracking

## Troubleshooting

### Common Issues

1. **"Sakila database not found"**
   ```bash
   python setup_sakila_db.py --database sqlite
   ```

2. **"dbt command not found"**
   ```bash
   pip install -r requirements-integration.txt
   ```

3. **"Profile 'Sakila' not found"**
   - Check `~/.dbt/profiles.yml` exists and contains Sakila configuration
   - Verify `profiles/Sakila/models/schema.yml` exists

4. **"OpenAI API key not configured"**
   - Set `OPENAI_API_KEY` environment variable, or
   - Run tests with `-m "not llm"` to skip LLM tests

### Debug Information

```bash
# Check database setup
sqlite3 sakila.db "SELECT COUNT(*) FROM film;"

# Check dbt configuration
dbt debug --profile Sakila

# Check profile paths
python -c "from qbot.core.schema import get_profile_paths; print(get_profile_paths('Sakila'))"

# Run single test with full output
pytest tests/integration/test_sakila_integration.py::TestSakilaDatabase::test_sakila_database_exists -v -s
```

## Requirements

Integration tests require additional dependencies not needed for core QBot functionality:

- **dbt-sqlite>=1.0.0** - SQLite adapter for dbt
- **pytest-timeout>=2.1.0** - Test timeout handling
- **SQLite3** - Usually pre-installed on most systems

Optional for extended testing:
- **OpenAI API key** - For LLM integration tests
- **MySQL server** - For MySQL-based testing (alternative to SQLite)

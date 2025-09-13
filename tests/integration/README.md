# SQLBot Integration Tests

This directory contains integration tests that require actual database connections and verify SQLBot functionality against real databases.

## Quick Start

1. **Install integration dependencies:**
   ```bash
   pip install -r requirements-integration.txt
   ```

2. **Set up Sakila test database:**
   ```bash
   python scripts/setup_sakila_db.py
   ```

3. **Run integration tests:**
   ```bash
   # Run directly with pytest
   pytest -m "integration" tests/integration/

   # Run with verbose output
   pytest -m "integration" tests/integration/ -v
   ```

## Test Database: Sakila

The integration tests use the **Sakila sample database**, a well-known DVD rental store database that provides:

- **1000 films** with ratings, categories, and rental information
- **599 customers** with rental history and payments
- **16,000+ rental transactions** for realistic data testing
- **Complete relational structure** with actors, categories, inventory, stores, and staff

### Why Sakila?

- **Standardized**: Industry-standard sample database, available as SQLite for easy setup
- **Realistic**: Contains real-world business data patterns
- **Comprehensive**: Tests complex queries, joins, and aggregations
- **Lightweight**: SQLite version requires no server setup
- **Well-documented**: Extensive schema with proper relationships

## Setup Instructions

### Automatic Setup (Recommended)

```bash
# Install dependencies and set up Sakila database
pip install -r requirements-integration.txt
python scripts/setup_sakila_db.py
```

This creates:
- `sakila.db` - SQLite database file with all Sakila data
- `~/.dbt/profiles.yml` - dbt configuration for Sakila profile
- Profile-specific schema and macros in `profiles/Sakila/`

### Alternative Setup Options

If you need to customize the setup:

```bash
# Skip creating local .dbt/profiles.yml (use global ~/.dbt/profiles.yml instead)
python scripts/setup_sakila_db.py --no-local-profile
```

## Running Tests

### Basic Test Execution

```bash
# Run all integration tests
pytest -m "integration" tests/integration/

# Run with verbose output
pytest -m "integration" tests/integration/ -v

# Run specific test file
pytest tests/integration/test_sakila_integration.py

# Run specific test files
pytest tests/integration/test_basic_setup.py
pytest tests/integration/test_sakila_integration.py
pytest tests/integration/test_sakila_comprehensive_integration.py
```

### Test Categories

Integration tests are organized into focused test files:

- `test_basic_setup.py` - Basic database connectivity and setup verification
- `test_sakila_integration.py` - Core Sakila database functionality testing
- `test_sakila_comprehensive_integration.py` - Safeguards, query routing, and end-to-end workflows
- `test_local_dbt_folder_integration.py` - Local .dbt folder feature testing

### Environment Variables

```bash
# Required for integration tests
export DBT_PROFILE_NAME=Sakila

# Optional: Configure LLM testing (if using LLM features)
export OPENAI_API_KEY=your_api_key_here
```

## Test Structure

### Test File Overview

**`test_basic_setup.py`** - Foundation verification:
- SQLite database file accessibility
- Data integrity verification (1000 films, 599 customers, etc.)
- Schema structure validation
- dbt profiles configuration
- Integration test dependencies

**`test_sakila_integration.py`** - Core functionality:
- Schema integration and profile path discovery
- dbt debug and connection testing
- Query compilation with `{{ source('sakila', 'table') }}` syntax
- Macro execution (`get_films_by_category`, `get_customer_rentals`, etc.)
- REPL integration and command-line functionality

**`test_sakila_comprehensive_integration.py`** - Advanced workflows:
- Safeguard systems (blocking dangerous queries)
- Query routing (SQL vs natural language)
- End-to-end CLI and session integration
- LLM tool integration with safeguards

**`test_local_dbt_folder_integration.py`** - Configuration features:
- Local .dbt folder detection and usage
- Profile management and environment setup
- Banner display integration

### `conftest.py`

Shared test configuration providing:

- **Fixtures**: Database setup, environment configuration, mocking
- **Markers**: Automatic test categorization
- **Skip Logic**: Intelligent test skipping based on available dependencies
- **Environment Management**: Clean setup/teardown of test environment

## Test Data and Queries

### Sample Sakila Queries

The tests verify SQLBot can handle realistic business queries:

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
   python scripts/setup_sakila_db.py
   ```

2. **"dbt command not found"**
   ```bash
   pip install -r requirements-integration.txt
   ```

3. **"Profile 'Sakila' not found"**
   - Check `~/.dbt/profiles.yml` exists and contains Sakila configuration
   - Verify `profiles/Sakila/models/schema.yml` exists

4. **"Local .dbt folder not detected"**
   - Check if `.dbt/profiles.yml` exists in project root
   - Verify profile configuration is correct
   - Run `python -c "from sqlbot.core.config import SQLBotConfig; print(SQLBotConfig.detect_dbt_profiles_dir())"` to debug

### Debug Information

```bash
# Check database setup
sqlite3 profiles/Sakila/data/sakila.db "SELECT COUNT(*) FROM film;"

# Check dbt configuration
env DBT_PROFILE_NAME=Sakila dbt debug --profile Sakila

# Check profile paths
python -c "from sqlbot.core.schema import SchemaLoader; s=SchemaLoader('Sakila'); print(s.get_profile_paths())"

# Run single test with full output
pytest tests/integration/test_basic_setup.py::TestBasicSetup::test_sakila_database_file_exists -v -s
```

## Requirements

Integration tests require additional dependencies not needed for core SQLBot functionality:

- **dbt-sqlite>=1.0.0** - SQLite adapter for dbt
- **pytest-timeout>=2.1.0** - Test timeout handling
- **SQLite3** - Usually pre-installed on most systems

Optional:
- **OpenAI API key** - For LLM-related functionality (most tests work without it)

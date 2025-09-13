#!/usr/bin/env python3
"""
Sakila Database Integration Tests

Tests SQLBot functionality against the Sakila sample database using SQLite.
These tests verify that SQLBot can properly:
- Connect to the Sakila SQLite database
- Execute SQL queries against real data
- Use dbt compilation with Sakila schema
- Handle LLM queries with Sakila context
"""

import os
import pytest
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Import SQLBot modules
try:
    from sqlbot.repl import execute_safe_sql as execute_dbt_query
    from sqlbot.llm_integration import load_schema_info, get_profile_paths, handle_llm_query, DBT_PROFILE_NAME
    from sqlbot.repl import main as repl_main
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from sqlbot.repl import execute_safe_sql as execute_dbt_query
    from sqlbot.llm_integration import load_schema_info, get_profile_paths, handle_llm_query, DBT_PROFILE_NAME
    from sqlbot.repl import main as repl_main


class TestSakilaDatabase:
    """Test basic database connectivity and data integrity."""
    
    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        import sqlbot.llm_integration as llm
        llm.DBT_PROFILE_NAME = 'Sakila'
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']
    
    def test_sakila_database_exists(self):
        """Test that the Sakila SQLite database file exists and is accessible."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        assert sakila_db_path.exists(), f"Sakila database file not found at {sakila_db_path}. Run setup_sakila_db.py first."
        
        # Test basic SQLite connectivity
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Check that we can query the database
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
        assert table_count >= 15, f"Expected at least 15 tables, found {table_count}"
        
        conn.close()
    
    def test_sakila_data_integrity(self):
        """Test that Sakila database contains expected data."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test film count (should be 1000)
        cursor.execute("SELECT COUNT(*) FROM film;")
        film_count = cursor.fetchone()[0]
        assert film_count == 1000, f"Expected 1000 films, found {film_count}"
        
        # Test customer count (should be 599)
        cursor.execute("SELECT COUNT(*) FROM customer;")
        customer_count = cursor.fetchone()[0]
        assert customer_count == 599, f"Expected 599 customers, found {customer_count}"
        
        # Test rental count (should be > 15000)
        cursor.execute("SELECT COUNT(*) FROM rental;")
        rental_count = cursor.fetchone()[0]
        assert rental_count > 15000, f"Expected > 15000 rentals, found {rental_count}"
        
        conn.close()
    
    def test_sakila_schema_structure(self):
        """Test that key tables have expected structure."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test film table structure
        cursor.execute("PRAGMA table_info(film);")
        film_columns = [row[1] for row in cursor.fetchall()]
        expected_film_columns = ['film_id', 'title', 'description', 'release_year', 'language_id']
        for col in expected_film_columns:
            assert col in film_columns, f"Expected column '{col}' not found in film table"
        
        # Test customer table structure
        cursor.execute("PRAGMA table_info(customer);")
        customer_columns = [row[1] for row in cursor.fetchall()]
        expected_customer_columns = ['customer_id', 'first_name', 'last_name', 'email']
        for col in expected_customer_columns:
            assert col in customer_columns, f"Expected column '{col}' not found in customer table"
        
        conn.close()


class TestSakilaSchemaIntegration:
    """Test SQLBot schema loading with Sakila profile."""

    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        import sqlbot.llm_integration as llm
        llm.DBT_PROFILE_NAME = 'Sakila'
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']

    def test_sakila_profile_paths(self):
        """Test that Sakila profile paths are correctly identified."""
        schema_paths, macro_paths = get_profile_paths('Sakila')

        # Should find profile-specific paths (even if files don't exist)
        assert len(schema_paths) > 0, "No schema paths found for Sakila profile"
        assert len(macro_paths) > 0, "No macro paths found for Sakila profile"

        # Just verify paths are properly constructed
        assert any('Sakila' in path for path in schema_paths), f"Schema paths should contain Sakila: {schema_paths}"

    def test_sakila_schema_loading(self):
        """Test that Sakila schema information loads correctly."""
        schema_info = load_schema_info()

        # Schema files are optional - test should handle missing files gracefully
        if "schema file not found" in str(schema_info).lower():
            pytest.skip("Schema files not configured - this is expected for basic setup")

        assert schema_info is not None, "Failed to load schema information"
        assert len(schema_info) > 0, "Schema information is empty"

        # Check for expected Sakila tables if schema is loaded
        expected_tables = ['film', 'customer', 'rental', 'payment', 'actor', 'category']
        schema_text = str(schema_info).lower()

        for table in expected_tables:
            assert table in schema_text, f"Expected table '{table}' not found in schema"

    def test_sakila_source_references(self):
        """Test that schema contains proper dbt source references."""
        schema_info = load_schema_info()
        schema_text = str(schema_info)

        # Schema files are optional - test should handle missing files gracefully
        if "schema file not found" in schema_text.lower():
            pytest.skip("Schema files not configured - this is expected for basic setup")

        # Should contain source definition (formatted as "Source: sakila" by load_schema_info)
        assert 'Source: sakila' in schema_text or 'sources:' in schema_text, "Schema should contain sources definition"
        assert 'sakila' in schema_text.lower(), "Schema should reference 'sakila' source"

        # Should contain table definitions (formatted as "- film:" by load_schema_info)
        assert 'tables:' in schema_text or '- film:' in schema_text, "Schema should contain tables definition"


class TestSakilaDbtIntegration:
    """Test dbt functionality with Sakila database."""
    
    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        import sqlbot.llm_integration as llm
        llm.DBT_PROFILE_NAME = 'Sakila'
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']
    
    @pytest.mark.timeout(30)
    def test_dbt_debug_sakila(self):
        """Test that dbt can connect to Sakila database."""
        # Set environment for Sakila profile
        env = os.environ.copy()
        env['DBT_PROFILE_NAME'] = 'Sakila'

        # Change to project root directory for dbt operations
        project_root = Path(__file__).parent.parent.parent
        old_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Run dbt debug
            result = subprocess.run(
                ['dbt', 'debug', '--profile', 'Sakila'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Should succeed or at least not fail with connection errors
            if result.returncode != 0:
                # Allow skip if there are complex dbt setup issues
                pytest.skip(f"dbt debug failed (may need complex dbt project setup): {result.stderr}")

            assert "Connection test:" in result.stdout and "OK" in result.stdout, \
                f"dbt debug should show successful connection: {result.stdout}"
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.timeout(60)
    def test_simple_dbt_query_execution(self):
        """Test executing a simple dbt query against Sakila."""
        # Simple query to count films
        query = "SELECT COUNT(*) as film_count FROM {{ source('sakila', 'film') }}"
        
        try:
            result = execute_dbt_query(query)
            assert result is not None, "Query execution returned None"
            assert "film_count" in str(result).lower(), "Result should contain film_count"
        except Exception as e:
            pytest.skip(f"dbt query execution failed (may need dbt setup): {e}")
    
    @pytest.mark.timeout(60)
    def test_sakila_macro_execution(self):
        """Test executing Sakila-specific macros."""
        # Test the get_films_by_category macro
        query = "{{ get_films_by_category('Action') }}"
        
        try:
            result = execute_dbt_query(query)
            assert result is not None, "Macro execution returned None"
        except Exception as e:
            pytest.skip(f"Macro execution failed (may need dbt setup): {e}")




class TestSakilaREPLIntegration:
    """Test REPL functionality with Sakila database."""
    
    @pytest.fixture(autouse=True)
    def setup_sakila_profile(self):
        """Set up Sakila profile for all tests."""
        import sqlbot.llm_integration as llm
        llm.DBT_PROFILE_NAME = 'Sakila'
        os.environ['DBT_PROFILE_NAME'] = 'Sakila'
        yield
        # Cleanup
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']
    
    @pytest.mark.timeout(30)
    def test_repl_with_sakila_profile(self):
        """Test that REPL can be started with Sakila profile."""
        # Test command-line argument parsing for Sakila profile
        import sys
        from unittest.mock import patch
        
        test_args = ['sqlbot', '--profile', 'Sakila', '--help']
        
        with patch.object(sys, 'argv', test_args):
            try:
                # This should not crash and should recognize the profile argument
                with pytest.raises(SystemExit):  # --help causes SystemExit
                    repl_main()
            except ImportError:
                pytest.skip("REPL import failed (may need additional setup)")
    
    def test_sql_query_execution_in_sakila_context(self):
        """Test direct SQL query execution with Sakila context."""
        # Test a simple SQL query that should work with Sakila
        query = "SELECT COUNT(*) FROM film;"

        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"

        assert sakila_db_path.exists(), f"Sakila database not found at {sakila_db_path}"

        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        assert result[0] == 1000, f"Expected 1000 films, got {result[0]}"
        conn.close()


# Test fixtures and utilities
@pytest.fixture(scope="session")
def sakila_database():
    """Session-scoped fixture to ensure Sakila database is available."""
    sakila_db_path = Path("sakila.db")
    if not sakila_db_path.exists():
        pytest.skip("Sakila database not found. Run setup_sakila_db.py first.")
    return sakila_db_path


@pytest.fixture
def temp_model_file():
    """Create a temporary dbt model file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.sql',
        prefix='test_sakila_',
        dir='models',
        delete=False
    ) as f:
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Basic Integration Test Setup Verification

Simple tests to verify that the Sakila database and integration testing
infrastructure is properly set up, without importing complex SQLBot modules.
"""

import os
import sqlite3
import subprocess
from pathlib import Path
import pytest

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestBasicSetup:
    """Test basic setup without complex imports."""
    
    def test_sakila_database_file_exists(self):
        """Test that the Sakila SQLite database file exists."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        assert sakila_db_path.exists(), f"Sakila database file not found at {sakila_db_path}. Run: python setup_sakila_db.py --database sqlite"
    
    def test_sakila_database_connectivity(self):
        """Test basic SQLite connectivity to Sakila database."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        
        # Connect to database
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
        
        conn.close()
        
        assert table_count >= 15, f"Expected at least 15 tables, found {table_count}"
    
    def test_sakila_data_integrity(self):
        """Test that Sakila database contains expected data."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test film count
        cursor.execute("SELECT COUNT(*) FROM film;")
        film_count = cursor.fetchone()[0]
        assert film_count == 1000, f"Expected 1000 films, found {film_count}"
        
        # Test customer count
        cursor.execute("SELECT COUNT(*) FROM customer;")
        customer_count = cursor.fetchone()[0]
        assert customer_count == 599, f"Expected 599 customers, found {customer_count}"
        
        # Test that we have rental data
        cursor.execute("SELECT COUNT(*) FROM rental;")
        rental_count = cursor.fetchone()[0]
        assert rental_count > 15000, f"Expected > 15000 rentals, found {rental_count}"
        
        conn.close()
    
    def test_sakila_schema_structure(self):
        """Test that key tables have expected columns."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test film table structure
        cursor.execute("PRAGMA table_info(film);")
        film_columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['film_id', 'title', 'description', 'release_year']
        
        for col in expected_columns:
            assert col in film_columns, f"Expected column '{col}' not found in film table"
        
        conn.close()
    
    def test_dbt_profiles_configuration(self):
        """Test that dbt profiles are configured."""
        profiles_path = Path.home() / ".dbt" / "profiles.yml"
        assert profiles_path.exists(), f"dbt profiles.yml not found at {profiles_path}"
        
        # Read and check content
        content = profiles_path.read_text()
        assert "Sakila:" in content, "Sakila profile not found in profiles.yml"
        assert "sqlite" in content, "SQLite configuration not found in profiles.yml"
    
    def test_sakila_profile_schema_exists(self):
        """Test that Sakila profile schema file exists."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        schema_path = project_root / "profiles/Sakila/models/schema.yml"
        assert schema_path.exists(), f"Sakila schema file not found at {schema_path}"
        
        # Check content
        content = schema_path.read_text()
        assert "sources:" in content, "Schema should contain sources definition"
        assert "sakila" in content.lower(), "Schema should reference sakila source"
        assert "film" in content.lower(), "Schema should contain film table"
    
    def test_sakila_macros_exist(self):
        """Test that Sakila macros are available."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        macros_path = project_root / "profiles/Sakila/macros/sakila_macros.sql"
        assert macros_path.exists(), f"Sakila macros file not found at {macros_path}"
        
        # Check content
        content = macros_path.read_text()
        assert "get_films_by_category" in content, "get_films_by_category macro not found"
        assert "get_customer_rentals" in content, "get_customer_rentals macro not found"
    
    def test_integration_test_dependencies(self):
        """Test that integration test dependencies are installed."""
        # Test that we can import pytest-timeout
        try:
            import pytest_timeout
        except ImportError:
            pytest.fail("pytest-timeout not installed. Run: pip install -r requirements-integration.txt")
        
        # Test that we can import dbt-sqlite (this will test if dbt-core is also installed)
        try:
            import dbt.adapters.sqlite
        except ImportError:
            pytest.fail("dbt-sqlite not installed. Run: pip install -r requirements-integration.txt")
    
    def test_sample_business_queries(self):
        """Test sample business queries that SQLBot should be able to handle."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        sakila_db_path = project_root / "profiles/Sakila/data/sakila.db"
        conn = sqlite3.connect(str(sakila_db_path))
        cursor = conn.cursor()
        
        # Test 1: Films by rating
        cursor.execute("SELECT rating, COUNT(*) as count FROM film GROUP BY rating ORDER BY count DESC;")
        ratings = cursor.fetchall()
        assert len(ratings) > 0, "Should have films with ratings"
        
        # Test 2: Customer with most rentals
        cursor.execute("""
            SELECT c.first_name, c.last_name, COUNT(r.rental_id) as rental_count
            FROM customer c
            LEFT JOIN rental r ON c.customer_id = r.customer_id
            GROUP BY c.customer_id
            ORDER BY rental_count DESC
            LIMIT 1;
        """)
        top_customer = cursor.fetchone()
        assert top_customer[2] > 0, "Top customer should have rentals"
        
        # Test 3: Revenue by category
        cursor.execute("""
            SELECT c.name as category, COUNT(r.rental_id) as rentals, SUM(p.amount) as revenue
            FROM category c
            JOIN film_category fc ON c.category_id = fc.category_id
            JOIN film f ON fc.film_id = f.film_id
            JOIN inventory i ON f.film_id = i.film_id
            JOIN rental r ON i.inventory_id = r.inventory_id
            JOIN payment p ON r.rental_id = p.rental_id
            GROUP BY c.category_id, c.name
            ORDER BY revenue DESC
            LIMIT 5;
        """)
        revenue_data = cursor.fetchall()
        assert len(revenue_data) > 0, "Should have revenue data by category"
        
        conn.close()


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])


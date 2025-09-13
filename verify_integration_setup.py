#!/usr/bin/env python3
"""
Integration Setup Verification Script

This script verifies that the Sakila database and integration testing
infrastructure is properly set up and ready for use.

Usage:
    python verify_integration_setup.py
"""

import os
import sqlite3
import subprocess
from pathlib import Path


def check_sakila_database():
    """Verify Sakila SQLite database setup."""
    print("🔍 Checking Sakila Database Setup...")
    
    sakila_db = Path('sakila.db')
    if not sakila_db.exists():
        print("❌ Sakila database not found")
        print("   Run: python setup_sakila_db.py --database sqlite")
        return False
    
    print("✅ Sakila database file exists")
    
    try:
        conn = sqlite3.connect(str(sakila_db))
        cursor = conn.cursor()
        
        # Check table count
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
        print(f"✅ Found {table_count} tables")
        
        # Check film count
        cursor.execute('SELECT COUNT(*) FROM film;')
        film_count = cursor.fetchone()[0]
        print(f"✅ Found {film_count} films")
        
        # Check customer count
        cursor.execute('SELECT COUNT(*) FROM customer;')
        customer_count = cursor.fetchone()[0]
        print(f"✅ Found {customer_count} customers")
        
        # Check rental count
        cursor.execute('SELECT COUNT(*) FROM rental;')
        rental_count = cursor.fetchone()[0]
        print(f"✅ Found {rental_count} rentals")
        
        conn.close()
        
        # Verify expected data counts
        if film_count != 1000:
            print(f"⚠️  Expected 1000 films, found {film_count}")
        if customer_count != 599:
            print(f"⚠️  Expected 599 customers, found {customer_count}")
        if rental_count < 15000:
            print(f"⚠️  Expected >15000 rentals, found {rental_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connectivity error: {e}")
        return False


def check_dbt_profiles():
    """Verify dbt profiles configuration."""
    print("\n🔍 Checking dbt Profiles Configuration...")
    
    # Check for profiles.yml in project directory (for testing)
    project_profiles = Path('~/.dbt/profiles.yml')
    home_profiles = Path.home() / '.dbt' / 'profiles.yml'
    
    profiles_path = None
    if project_profiles.exists():
        profiles_path = project_profiles
        print("✅ Found dbt profiles.yml in project directory")
    elif home_profiles.exists():
        profiles_path = home_profiles
        print("✅ Found dbt profiles.yml in home directory")
    else:
        print("❌ dbt profiles.yml not found")
        print("   Expected at ~/.dbt/profiles.yml or ./~/.dbt/profiles.yml")
        return False
    
    try:
        content = profiles_path.read_text()
        
        if "Sakila:" in content:
            print("✅ Sakila profile found in profiles.yml")
        else:
            print("❌ Sakila profile not found in profiles.yml")
            return False
        
        if "sqlite" in content:
            print("✅ SQLite configuration found")
        else:
            print("❌ SQLite configuration not found")
            return False
        
        if "sakila.db" in content:
            print("✅ Sakila database path configured")
        else:
            print("⚠️  Sakila database path not explicitly found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading profiles.yml: {e}")
        return False


def check_sakila_schema():
    """Verify Sakila schema configuration."""
    print("\n🔍 Checking Sakila Schema Configuration...")
    
    schema_path = Path('profiles/Sakila/models/schema.yml')
    if not schema_path.exists():
        print(f"❌ Sakila schema not found at {schema_path}")
        return False
    
    print("✅ Sakila schema file exists")
    
    try:
        content = schema_path.read_text()
        
        if "sources:" in content:
            print("✅ Schema contains sources definition")
        else:
            print("❌ Schema missing sources definition")
            return False
        
        if "sakila" in content.lower():
            print("✅ Schema references sakila source")
        else:
            print("❌ Schema missing sakila source reference")
            return False
        
        # Check for key tables
        key_tables = ['film', 'customer', 'rental', 'payment', 'actor']
        found_tables = []
        for table in key_tables:
            if table in content.lower():
                found_tables.append(table)
        
        print(f"✅ Found {len(found_tables)}/{len(key_tables)} key tables in schema")
        
        return len(found_tables) >= 3  # At least 3 key tables should be present
        
    except Exception as e:
        print(f"❌ Error reading schema.yml: {e}")
        return False


def check_sakila_macros():
    """Verify Sakila macros."""
    print("\n🔍 Checking Sakila Macros...")
    
    macros_path = Path('profiles/Sakila/macros/sakila_macros.sql')
    if not macros_path.exists():
        print(f"❌ Sakila macros not found at {macros_path}")
        return False
    
    print("✅ Sakila macros file exists")
    
    try:
        content = macros_path.read_text()
        
        expected_macros = [
            'get_films_by_category',
            'get_customer_rentals',
            'get_top_actors_by_film_count',
            'get_revenue_by_category'
        ]
        
        found_macros = []
        for macro in expected_macros:
            if macro in content:
                found_macros.append(macro)
        
        print(f"✅ Found {len(found_macros)}/{len(expected_macros)} expected macros")
        
        return len(found_macros) >= 2  # At least 2 macros should be present
        
    except Exception as e:
        print(f"❌ Error reading macros file: {e}")
        return False


def check_integration_dependencies():
    """Verify integration test dependencies."""
    print("\n🔍 Checking Integration Test Dependencies...")
    
    # Check via pip instead of import to handle version mismatches
    import subprocess
    
    dependencies_ok = True
    
    try:
        # Check pytest-timeout
        result = subprocess.run(['pip', 'show', 'pytest-timeout'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ pytest-timeout installed")
        else:
            print("❌ pytest-timeout not installed")
            print("   Run: pip install -r requirements-integration.txt")
            dependencies_ok = False
    except Exception:
        print("⚠️  Could not check pytest-timeout installation")
        dependencies_ok = False
    
    try:
        # Check dbt-sqlite
        result = subprocess.run(['pip', 'show', 'dbt-sqlite'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ dbt-sqlite installed")
        else:
            print("❌ dbt-sqlite not installed")
            print("   Run: pip install -r requirements-integration.txt")
            dependencies_ok = False
    except Exception:
        print("⚠️  Could not check dbt-sqlite installation")
        dependencies_ok = False
    
    # Also try direct imports as fallback
    if not dependencies_ok:
        print("   Trying direct imports as fallback...")
        try:
            import pytest_timeout
            print("   ✅ pytest-timeout can be imported")
            dependencies_ok = True
        except ImportError:
            pass
        
        try:
            import dbt.adapters.sqlite
            print("   ✅ dbt-sqlite can be imported")
            dependencies_ok = True
        except ImportError:
            pass
    
    return dependencies_ok


def test_sample_query():
    """Test a sample business query."""
    print("\n🔍 Testing Sample Business Query...")
    
    try:
        sakila_db = Path('sakila.db')
        conn = sqlite3.connect(str(sakila_db))
        cursor = conn.cursor()
        
        # Test a realistic business query
        query = """
        SELECT c.name as category, COUNT(f.film_id) as film_count
        FROM category c
        JOIN film_category fc ON c.category_id = fc.category_id
        JOIN film f ON fc.film_id = f.film_id
        GROUP BY c.category_id, c.name
        ORDER BY film_count DESC
        LIMIT 5;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        if len(results) > 0:
            print("✅ Sample business query executed successfully")
            print(f"   Top category: {results[0][0]} ({results[0][1]} films)")
            return True
        else:
            print("❌ Sample query returned no results")
            return False
        
    except Exception as e:
        print(f"❌ Sample query failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("🚀 SQLBot Integration Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Sakila Database", check_sakila_database),
        ("dbt Profiles", check_dbt_profiles),
        ("Sakila Schema", check_sakila_schema),
        ("Sakila Macros", check_sakila_macros),
        ("Integration Dependencies", check_integration_dependencies),
        ("Sample Query", test_sample_query),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ {name} check failed")
        except Exception as e:
            print(f"❌ {name} check error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Integration testing setup is ready.")
        print("\nNext steps:")
        print("  • Run integration tests: pytest tests/integration/")
        print("  • Test with Sakila profile: export DBT_PROFILE_NAME=Sakila")
        print("  • Try SQLBot with Sakila: qbot --profile Sakila")
        return True
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("  • Run: python setup_sakila_db.py --database sqlite")
        print("  • Run: pip install -r requirements-integration.txt")
        print("  • Check that all files are in the correct locations")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

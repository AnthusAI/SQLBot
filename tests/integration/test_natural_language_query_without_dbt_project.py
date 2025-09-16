"""
Test that natural language queries work without a physical dbt_project.yml file.

This test reproduces the issue where direct SQL queries work (using virtual dbt_project.yml spoofing)
but natural language queries fail because they try to run `dbt debug` which doesn't use the spoofing.

The test should:
1. Set up a clean directory without dbt_project.yml
2. Configure a local dbt profile pointing to a test database
3. Verify that natural language queries work (not just direct SQL)
4. Be as generalized as possible to catch this class of issues
"""

import os
import tempfile
import shutil
import sqlite3
from pathlib import Path
import pytest
import yaml

from sqlbot.core.config import SQLBotConfig
from sqlbot.core.dbt_service import get_dbt_service


class TestNaturalLanguageQueryWithoutDbtProject:
    """Test natural language queries work without physical dbt_project.yml"""

    def setup_method(self):
        """Set up a clean test environment"""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp(prefix="sqlbot_nl_test_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test SQLite database
        self.db_path = Path(self.test_dir) / ".sqlbot" / "profiles" / "TestProfile" / "data" / "test.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create simple test database with some data
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT
            )
        """)
        cursor.execute("INSERT INTO test_table (name, category) VALUES ('Apple', 'Fruit')")
        cursor.execute("INSERT INTO test_table (name, category) VALUES ('Banana', 'Fruit')")
        cursor.execute("INSERT INTO test_table (name, category) VALUES ('Carrot', 'Vegetable')")
        cursor.execute("INSERT INTO test_table (name, category) VALUES ('Mango', 'Fruit')")
        conn.commit()
        conn.close()

        # Create local dbt profile pointing to our test database
        dbt_dir = Path(self.test_dir) / ".dbt"
        dbt_dir.mkdir(exist_ok=True)

        profiles_config = {
            'TestProfile': {
                'target': 'dev',
                'outputs': {
                    'dev': {
                        'type': 'sqlite',
                        'threads': 1,
                        'keepalives_idle': 0,
                        'search_path': 'main',
                        'database': 'database',
                        'schema': 'main',
                        'schemas_and_paths': {
                            'main': str(self.db_path)
                        },
                        'schema_directory': str(self.db_path.parent)
                    }
                }
            }
        }

        with open(dbt_dir / 'profiles.yml', 'w') as f:
            yaml.dump(profiles_config, f, default_flow_style=False)

        # Ensure NO dbt_project.yml exists (this is the key condition)
        dbt_project_path = Path(self.test_dir) / "dbt_project.yml"
        if dbt_project_path.exists():
            dbt_project_path.unlink()

    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_direct_sql_query_works_without_dbt_project(self):
        """Verify direct SQL queries work (baseline - this should pass)"""
        config = SQLBotConfig(profile="TestProfile")
        dbt_service = get_dbt_service(config)

        # This should work because it uses virtual dbt_project.yml spoofing
        result = dbt_service.execute_query("SELECT COUNT(*) as count FROM test_table")

        assert result.success, f"Direct SQL query failed: {result.error}"
        assert len(result.data) == 1
        assert result.data[0]['count'] == '4'  # We inserted 4 test records

    def test_natural_language_query_works_without_dbt_project(self):
        """
        Test that natural language queries work without physical dbt_project.yml

        This test reproduces the core issue:
        - Direct SQL works (uses virtual spoofing)
        - Natural language queries fail (try to run dbt debug without spoofing)

        This should initially FAIL, then PASS after we fix the spoofing.
        """
        # Set the profiles directory to our test location
        import os
        old_profiles_dir = os.environ.get('DBT_PROFILES_DIR')
        os.environ['DBT_PROFILES_DIR'] = str(Path(self.test_dir) / ".dbt")

        try:
            config = SQLBotConfig(profile="TestProfile")

            # Simulate what happens in natural language query processing
            # This typically involves:
            # 1. Connection validation (runs dbt debug - THIS FAILS)
            # 2. Schema introspection
            # 3. LLM generates SQL
            # 4. SQL execution (this part works)

            dbt_service = get_dbt_service(config)

            # Step 1: Connection validation - this is where it currently fails
            debug_result = dbt_service.debug()
            assert debug_result['success'], f"dbt debug failed: {debug_result['error']}"
            assert debug_result['connection_ok'], "Connection should be OK"

            # Step 2: If debug passes, the rest should work
            # Test a query that would come from natural language processing
            result = dbt_service.execute_query("SELECT COUNT(*) FROM test_table WHERE category = 'Fruit'")

            assert result.success, f"Natural language query execution failed: {result.error}"
            assert len(result.data) == 1
            assert result.data[0]['COUNT(*)'] == '3'  # Apple, Banana, Mango

        finally:
            # Restore original environment
            if old_profiles_dir is not None:
                os.environ['DBT_PROFILES_DIR'] = old_profiles_dir
            elif 'DBT_PROFILES_DIR' in os.environ:
                del os.environ['DBT_PROFILES_DIR']

    def test_generalized_dbt_operations_work_without_physical_project_file(self):
        """
        Generalized test for ANY dbt operation working without dbt_project.yml

        This tests the broader issue: ALL dbt operations should work with virtual spoofing,
        not just the direct SQL execution path.
        """
        # Set the profiles directory to our test location
        import os
        old_profiles_dir = os.environ.get('DBT_PROFILES_DIR')
        os.environ['DBT_PROFILES_DIR'] = str(Path(self.test_dir) / ".dbt")

        try:
            config = SQLBotConfig(profile="TestProfile")
            dbt_service = get_dbt_service(config)

            # Test various dbt operations that natural language queries might use
            operations_to_test = [
                ("debug", lambda: dbt_service.debug()),
                ("list_models", lambda: dbt_service.list_models()),
                # Add more operations as needed
            ]

            for operation_name, operation_func in operations_to_test:
                try:
                    result = operation_func()
                    # Each operation should succeed or gracefully handle the virtual environment
                    if isinstance(result, dict):
                        assert not (result.get('success') is False and 'dbt_project.yml' in str(result.get('error', ''))), \
                            f"Operation {operation_name} failed due to missing dbt_project.yml: {result}"
                    # For operations that return other types, just ensure they don't crash
                except Exception as e:
                    if 'dbt_project.yml' in str(e):
                        pytest.fail(f"Operation {operation_name} failed due to missing dbt_project.yml: {e}")
                    # Other exceptions might be expected (e.g., no models to list)

        finally:
            # Restore original environment
            if old_profiles_dir is not None:
                os.environ['DBT_PROFILES_DIR'] = old_profiles_dir
            elif 'DBT_PROFILES_DIR' in os.environ:
                del os.environ['DBT_PROFILES_DIR']


if __name__ == "__main__":
    # Run the test to reproduce the issue
    test = TestNaturalLanguageQueryWithoutDbtProject()
    test.setup_method()

    try:
        print("Testing direct SQL query (should work)...")
        test.test_direct_sql_query_works_without_dbt_project()
        print("✓ Direct SQL query works")

        print("\nTesting natural language query (should fail initially)...")
        test.test_natural_language_query_works_without_dbt_project()
        print("✓ Natural language query works")

    except Exception as e:
        print(f"✗ Test failed as expected: {e}")
        print("This confirms the issue exists and needs to be fixed.")
    finally:
        test.teardown_method()
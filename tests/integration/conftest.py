#!/usr/bin/env python3
"""
Integration Test Configuration

Shared fixtures and configuration for SQLBot integration tests.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(scope="session")
def integration_test_env():
    """Set up environment for integration tests."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test-specific environment variables
    test_env = {
        'QBOT_LLM_MODEL': 'gpt-3.5-turbo',  # Use cheaper model for testing
        'QBOT_LLM_MAX_TOKENS': '500',       # Limit tokens for faster tests
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_openai_api():
    """Mock OpenAI API for tests that don't need real API calls."""
    with patch('sqlbot.llm_integration.openai') as mock_openai:
        # Set up default mock response
        mock_response = type('MockResponse', (), {})()
        mock_response.choices = [type('MockChoice', (), {})()]
        mock_response.choices[0].message = type('MockMessage', (), {})()
        mock_response.choices[0].message.content = "SELECT COUNT(*) FROM {{ source('sakila', 'film') }}"
        
        mock_openai.ChatCompletion.create.return_value = mock_response
        yield mock_openai


@pytest.fixture
def temp_dbt_model():
    """Create a temporary dbt model file for testing."""
    # Ensure models directory exists
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.sql',
        prefix='qbot_temp_test_',
        dir=models_dir,
        delete=False
    ) as f:
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def sakila_profile_env():
    """Set up Sakila profile environment."""
    original_profile = os.environ.get('DBT_PROFILE_NAME')
    os.environ['DBT_PROFILE_NAME'] = 'Sakila'
    
    # Also set in the module
    try:
        import sqlbot.llm_integration as llm
        original_module_profile = llm.DBT_PROFILE_NAME
        llm.DBT_PROFILE_NAME = 'Sakila'
    except ImportError:
        original_module_profile = None
    
    yield 'Sakila'
    
    # Restore original values
    if original_profile is not None:
        os.environ['DBT_PROFILE_NAME'] = original_profile
    elif 'DBT_PROFILE_NAME' in os.environ:
        del os.environ['DBT_PROFILE_NAME']
    
    if original_module_profile is not None:
        try:
            import sqlbot.llm_integration as llm
            llm.DBT_PROFILE_NAME = original_module_profile
        except ImportError:
            pass


@pytest.fixture(scope="session")
def check_sakila_database():
    """Check that Sakila database is available for testing."""
    sakila_db_path = Path("sakila.db")
    if not sakila_db_path.exists():
        pytest.skip(
            "Sakila database not found. Please run: python setup_sakila_db.py --database sqlite"
        )
    return sakila_db_path


@pytest.fixture(scope="session") 
def check_dbt_installation():
    """Check that dbt is properly installed and configured."""
    import subprocess
    
    try:
        result = subprocess.run(['dbt', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            pytest.skip("dbt is not properly installed or configured")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("dbt command not found or timed out")
    
    return True


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring database"
    )
    config.addinivalue_line(
        "markers", "llm: mark test as requiring LLM/OpenAI API access"
    )
    config.addinivalue_line(
        "markers", "dbt: mark test as requiring dbt functionality"
    )
    config.addinivalue_line(
        "markers", "sakila: mark test as requiring Sakila database"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        # Mark all tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark tests that use specific fixtures
        if "mock_openai_api" in item.fixturenames or "llm" in item.name.lower():
            item.add_marker(pytest.mark.llm)
        
        if "dbt" in item.name.lower() or "temp_dbt_model" in item.fixturenames:
            item.add_marker(pytest.mark.dbt)
        
        if "sakila" in item.name.lower() or "sakila_profile_env" in item.fixturenames:
            item.add_marker(pytest.mark.sakila)


# Skip integration tests if dependencies are missing
def pytest_runtest_setup(item):
    """Skip tests based on available dependencies and configuration."""
    # Skip LLM tests if no API key (unless mocked)
    if item.get_closest_marker("llm") and "mock_openai_api" not in item.fixturenames:
        if not os.environ.get('OPENAI_API_KEY'):
            pytest.skip("OpenAI API key not configured (set OPENAI_API_KEY environment variable)")
    
    # Skip Sakila tests if database not available
    if item.get_closest_marker("sakila"):
        sakila_db_path = Path("sakila.db")
        if not sakila_db_path.exists():
            pytest.skip("Sakila database not found. Run setup_sakila_db.py first.")


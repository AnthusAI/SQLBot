"""Pytest configuration and shared fixtures for SQLBot tests."""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set PYTEST_CURRENT_TEST early to prevent repl.py from loading config
os.environ['PYTEST_CURRENT_TEST'] = 'conftest'

# Patch config loading BEFORE any sqlbot modules are imported
# This prevents .sqlbot/config.yml from overriding test environment variables
from sqlbot.core.config import SQLBotConfig
_original_load_yaml = SQLBotConfig.load_yaml_config
_original_load_dbt = SQLBotConfig.load_dbt_profiles_with_dotyaml
SQLBotConfig.load_yaml_config = staticmethod(lambda: False)
SQLBotConfig.load_dbt_profiles_with_dotyaml = staticmethod(lambda: False)

def setup_subprocess_environment(env=None):
    """Set up environment for subprocess tests to find local qbot module.
    
    Args:
        env: Environment dict to modify, or None to create a new one
        
    Returns:
        Modified environment dict with PYTHONPATH set correctly
    """
    if env is None:
        env = os.environ.copy()
    
    # Add project root to PYTHONPATH so subprocess can find qbot module
    current_pythonpath = env.get('PYTHONPATH', '')
    if current_pythonpath:
        env['PYTHONPATH'] = f"{project_root}:{current_pythonpath}"
    else:
        env['PYTHONPATH'] = str(project_root)
    
    return env

@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-api-key',
        'SQLBOT_LLM_MODEL': 'gpt-5',
        'SQLBOT_LLM_MAX_TOKENS': '1000'
    }):
        yield

@pytest.fixture
def mock_database():
    """Mock database connection and responses."""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Mock successful connection
    mock_cursor.description = [('count', None)]
    mock_cursor.fetchall.return_value = [(1458,)]  # Mock table count
    mock_conn.cursor.return_value = mock_cursor
    
    with patch('pyodbc.connect', return_value=mock_conn):
        yield mock_conn

@pytest.fixture
def mock_llm():
    """Mock LLM responses for testing."""
    mock_response = Mock()
    mock_response.content = "I'll help you query the database. Let me run a query to count the tables."
    
    mock_llm_instance = Mock()
    mock_llm_instance.invoke.return_value = mock_response
    
    with patch('sqlbot.llm_integration.ChatOpenAI', return_value=mock_llm_instance):
        yield mock_llm_instance

@pytest.fixture
def mock_dbt():
    """Mock dbt runner and responses."""
    mock_result = Mock()
    mock_result.success = True
    mock_result.returncode = 0
    
    mock_runner = Mock()
    mock_runner.invoke.return_value = mock_result
    
    with patch('sqlbot.repl.dbtRunner', return_value=mock_runner):
        yield mock_runner

@pytest.fixture
def qbot_instance(mock_env, mock_database, mock_llm, mock_dbt):
    """Create a SQLBot instance with all dependencies mocked."""
    # Import after mocking to ensure mocks are in place
    from sqlbot import repl
    
    # Mock the LLM_AVAILABLE flag
    repl.LLM_AVAILABLE = True
    
    return repl

@pytest.fixture
def cli_runner():
    """Provide a CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory for testing."""
    # Create basic dbt project structure
    (tmp_path / "models").mkdir()
    (tmp_path / "macros").mkdir()
    
    # Create basic dbt_project.yml
    dbt_project = """
name: 'test_qbot'
version: '1.0.0'
config-version: 2

model-paths: ["models"]
macro-paths: ["macros"]
target-path: "target"
"""
    (tmp_path / "dbt_project.yml").write_text(dbt_project)
    
    return tmp_path

@pytest.fixture(autouse=True)
def reset_readonly_mode():
    """Reset READONLY_MODE to default (True) after each test."""
    import sqlbot.repl as repl_module
    
    yield
    
    # Always restore to default state (safeguards enabled)
    repl_module.READONLY_MODE = True

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_project_dir):
    """Set up the test environment for all tests."""
    # Change to temp directory for dbt operations
    monkeypatch.chdir(temp_project_dir)
    
    # Mock the PROJECT_ROOT to point to temp directory
    with patch('sqlbot.repl.PROJECT_ROOT', temp_project_dir):
        yield

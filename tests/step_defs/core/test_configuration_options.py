"""
BDD step definitions for configuration options testing
"""

import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch
import pytest
from pytest_bdd import given, when, then, scenario, parsers

from sqlbot.core.config import SQLBotConfig


# Scenario bindings
@scenario('../../features/core/configuration_options.feature', 'Configure dbt profile name using DBT_PROFILE_NAME')
def test_dbt_profile_name():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure dbt profile name using SQLBOT_PROFILE (takes precedence)')
def test_sqlbot_profile_precedence():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure dbt target using DBT_TARGET')
def test_dbt_target():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure dbt target using SQLBOT_TARGET (takes precedence)')
def test_sqlbot_target_precedence():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM model using SQLBOT_LLM_MODEL')
def test_sqlbot_llm_model():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM max tokens using SQLBOT_LLM_MAX_TOKENS')
def test_sqlbot_llm_max_tokens():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM temperature using SQLBOT_LLM_TEMPERATURE')
def test_sqlbot_llm_temperature():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM verbosity using SQLBOT_LLM_VERBOSITY')
def test_sqlbot_llm_verbosity():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM effort using SQLBOT_LLM_EFFORT')
def test_sqlbot_llm_effort():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure LLM provider using SQLBOT_LLM_PROVIDER')
def test_sqlbot_llm_provider():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure OpenAI API key')
def test_openai_api_key():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure query timeout using SQLBOT_QUERY_TIMEOUT')
def test_sqlbot_query_timeout():
    pass

@scenario('../../features/core/configuration_options.feature', 'Configure max rows using SQLBOT_MAX_ROWS')
def test_sqlbot_max_rows():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure preview mode using SQLBOT_PREVIEW_MODE with 'true'")
def test_sqlbot_preview_mode_true():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure preview mode using SQLBOT_PREVIEW_MODE with '1'")
def test_sqlbot_preview_mode_1():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure preview mode using SQLBOT_PREVIEW_MODE with 'yes'")
def test_sqlbot_preview_mode_yes():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure read only mode using SQLBOT_READ_ONLY with 'true'")
def test_sqlbot_read_only_true():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure read only mode using SQLBOT_READ_ONLY with '1'")
def test_sqlbot_read_only_1():
    pass

@scenario('../../features/core/configuration_options.feature', "Configure read only mode using SQLBOT_READ_ONLY with 'yes'")
def test_sqlbot_read_only_yes():
    pass

@scenario('../../features/core/configuration_options.feature', 'Default values are used when no configuration is provided')
def test_default_values():
    pass


# Fixtures and shared state
class ConfigTestContext:
    def __init__(self):
        self.env_vars = {}
        self.config = None
        self.yaml_file = None
        self.original_cwd = None

@pytest.fixture
def config_context():
    """Context for configuration testing"""
    return ConfigTestContext()


# Step definitions
@given('SQLBot is available')
def sqlbot_is_available():
    """Ensure SQLBot is available for testing"""
    pass

@given('environment variables are cleared')
def clear_environment_variables(config_context):
    """Clear relevant environment variables"""
    config_vars = [
        'DBT_PROFILE_NAME', 'SQLBOT_PROFILE', 'DBT_TARGET', 'SQLBOT_TARGET',
        'SQLBOT_LLM_MODEL', 'SQLBOT_LLM_MAX_TOKENS', 'SQLBOT_LLM_TEMPERATURE',
        'SQLBOT_LLM_VERBOSITY', 'SQLBOT_LLM_EFFORT', 'SQLBOT_LLM_PROVIDER',
        'OPENAI_API_KEY', 'SQLBOT_QUERY_TIMEOUT', 'SQLBOT_MAX_ROWS',
        'SQLBOT_PREVIEW_MODE', 'SQLBOT_READ_ONLY'
    ]
    config_context.env_vars = {}
    for var in config_vars:
        config_context.env_vars[var] = os.environ.pop(var, None)

@given(parsers.parse('I set environment variable "{var_name}" to "{var_value}"'))
def set_environment_variable(var_name, var_value):
    """Set an environment variable"""
    os.environ[var_name] = var_value

@when('I load SQLBot configuration')
def load_sqlbot_configuration(config_context):
    """Load SQLBot configuration"""
    config_context.config = SQLBotConfig.from_env()

@then(parsers.parse('the profile should be "{expected_value}"'))
def check_profile(config_context, expected_value):
    """Check the profile configuration"""
    assert config_context.config.profile == expected_value

@then(parsers.parse('the target should be "{expected_value}"'))
def check_target_string(config_context, expected_value):
    """Check the target configuration (string)"""
    assert config_context.config.target == expected_value

@then('the target should be None')
def check_target_none(config_context):
    """Check the target configuration is None"""
    assert config_context.config.target is None

@then(parsers.parse('the LLM model should be "{expected_value}"'))
def check_llm_model(config_context, expected_value):
    """Check the LLM model configuration"""
    assert config_context.config.llm.model == expected_value

@then(parsers.parse('the LLM max tokens should be {expected_value:d}'))
def check_llm_max_tokens(config_context, expected_value):
    """Check the LLM max tokens configuration"""
    assert config_context.config.llm.max_tokens == expected_value

@then(parsers.parse('the LLM temperature should be {expected_value:g}'))
def check_llm_temperature(config_context, expected_value):
    """Check the LLM temperature configuration"""
    assert config_context.config.llm.temperature == expected_value

@then(parsers.parse('the LLM verbosity should be "{expected_value}"'))
def check_llm_verbosity(config_context, expected_value):
    """Check the LLM verbosity configuration"""
    assert config_context.config.llm.verbosity == expected_value

@then(parsers.parse('the LLM effort should be "{expected_value}"'))
def check_llm_effort(config_context, expected_value):
    """Check the LLM effort configuration"""
    assert config_context.config.llm.effort == expected_value

@then(parsers.parse('the LLM provider should be "{expected_value}"'))
def check_llm_provider(config_context, expected_value):
    """Check the LLM provider configuration"""
    assert config_context.config.llm.provider == expected_value

@then(parsers.parse('the LLM API key should be "{expected_value}"'))
def check_llm_api_key(config_context, expected_value):
    """Check the LLM API key configuration"""
    assert config_context.config.llm.api_key == expected_value

@then(parsers.parse('the query timeout should be {expected_value:d}'))
def check_query_timeout(config_context, expected_value):
    """Check the query timeout configuration"""
    assert config_context.config.query_timeout == expected_value

@then(parsers.parse('the max rows should be {expected_value:d}'))
def check_max_rows(config_context, expected_value):
    """Check the max rows configuration"""
    assert config_context.config.max_rows == expected_value

@then('preview mode should be enabled')
def check_preview_mode_enabled(config_context):
    """Check that preview mode is enabled"""
    assert config_context.config.preview_mode is True

@then('preview mode should be disabled')
def check_preview_mode_disabled(config_context):
    """Check that preview mode is disabled"""
    assert config_context.config.preview_mode is False

@then('read only mode should be enabled')
def check_read_only_mode_enabled(config_context):
    """Check that read only mode is enabled"""
    assert config_context.config.read_only is True

@then('read only mode should be disabled')
def check_read_only_mode_disabled(config_context):
    """Check that read only mode is disabled"""
    assert config_context.config.read_only is False


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_config_test(config_context):
    """Cleanup after configuration tests"""
    yield

    # Restore environment variables
    if hasattr(config_context, 'env_vars'):
        for var, value in config_context.env_vars.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    # Restore working directory
    if hasattr(config_context, 'original_cwd') and config_context.original_cwd:
        os.chdir(config_context.original_cwd)

    # Clean up temporary files
    if hasattr(config_context, 'yaml_file') and config_context.yaml_file:
        try:
            if config_context.yaml_file.exists():
                config_context.yaml_file.unlink()
            # Remove .sqlbot directory if it exists
            sqlbot_dir = config_context.yaml_file.parent
            if sqlbot_dir.exists():
                sqlbot_dir.rmdir()
        except Exception:
            pass
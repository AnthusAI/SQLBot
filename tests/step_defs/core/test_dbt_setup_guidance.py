"""Step definitions for dbt setup guidance scenarios."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import patch, Mock
import subprocess

# Load scenarios from the feature file - temporarily skip until fully implemented
# scenarios('../../features/core/dbt_setup_guidance.feature')

@given('I have SQLBot installed')
def qbot_installed():
    """SQLBot is installed and importable."""
    try:
        import sqlbot
        return True
    except ImportError:
        pytest.fail("SQLBot is not installed")

@given('I have a valid OpenAI API key')
def valid_openai_key():
    """Mock a valid OpenAI API key."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        pass

@given('I do not have a dbt profile configured')
def no_dbt_profile():
    """Mock missing dbt profile by making dbt debug fail with profile error."""
    def mock_dbt_debug(*args, **kwargs):
        result = Mock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "Could not find profile named 'sqlbot'"
        return result
    
    return patch('subprocess.run', side_effect=mock_dbt_debug)

@given('I have a dbt profile with incorrect connection details')
def invalid_dbt_profile():
    """Mock invalid dbt profile by making dbt debug fail with connection error."""
    def mock_dbt_debug(*args, **kwargs):
        result = Mock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "Could not connect to database"
        return result
    
    return patch('subprocess.run', side_effect=mock_dbt_debug)

@given('I have a properly configured dbt profile')
@given('my database connection is working')
def working_dbt_profile():
    """Mock working dbt profile."""
    def mock_dbt_debug(*args, **kwargs):
        result = Mock()
        result.returncode = 0
        result.stdout = "All checks passed!"
        result.stderr = ""
        return result
    
    return patch('subprocess.run', side_effect=mock_dbt_debug)

@when('I ask a natural language question that requires database access')
def ask_database_question():
    """Ask a question that requires database access."""
    # This step will be implemented when the actual feature is complete
    pass

@then('SQLBot should detect the missing dbt profile')
def detect_missing_profile():
    """SQLBot should detect that dbt profile is missing."""
    # This will be implemented in the actual feature
    pass

@then('show me a clear setup message with next steps')
def show_setup_message():
    """SQLBot should show clear setup instructions."""
    # This will be implemented in the actual feature
    pass

@then('provide links to documentation')
def provide_documentation_links():
    """SQLBot should provide helpful documentation links."""
    # This will be implemented in the actual feature
    pass

@then('suggest the specific profile name I need to create')
def suggest_profile_name():
    """SQLBot should suggest the correct profile name 'sqlbot'."""
    # This will be implemented in the actual feature
    pass

@then('not show cryptic dbt error messages to the user')
def no_cryptic_errors():
    """SQLBot should hide raw dbt errors from users."""
    # This will be implemented in the actual feature
    pass

@then('SQLBot should detect the connection failure')
def detect_connection_failure():
    """SQLBot should detect database connection issues."""
    # This will be implemented in the actual feature
    pass

@then('show me troubleshooting steps for database connection')
def show_troubleshooting_steps():
    """SQLBot should show database troubleshooting guidance."""
    # This will be implemented in the actual feature
    pass

@then('suggest running "dbt debug" to test the connection')
def suggest_dbt_debug():
    """SQLBot should suggest running dbt debug."""
    # This will be implemented in the actual feature
    pass

@then('provide guidance on common connection issues')
def provide_connection_guidance():
    """SQLBot should provide common connection issue guidance."""
    # This will be implemented in the actual feature
    pass

@then('SQLBot should execute the query successfully')
def execute_query_successfully():
    """SQLBot should execute queries when dbt is properly configured."""
    # This will be implemented in the actual feature
    pass

@then('return formatted results')
def return_formatted_results():
    """SQLBot should return properly formatted query results."""
    # This will be implemented in the actual feature
    pass

@then('not show any setup messages')
def no_setup_messages():
    """SQLBot should not show setup messages when everything is working."""
    # This will be implemented in the actual feature
    pass

# New step definitions for --profile feature

@given('I have a dbt profile named "mycompany"')
def dbt_profile_mycompany():
    """Mock a dbt profile named 'mycompany'."""
    pass

@given('the "mycompany" profile has valid database connection details')
def mycompany_profile_valid():
    """Mock valid connection details for 'mycompany' profile."""
    pass

@given('I do not have a dbt profile named "nonexistent"')
def no_nonexistent_profile():
    """Mock missing 'nonexistent' profile."""
    pass

@when('I run SQLBot with "--profile mycompany" and ask a database question')
def run_qbot_with_mycompany_profile():
    """Run SQLBot with custom profile name."""
    # This will test the --profile argument functionality
    pass

@when('I run SQLBot with "--profile nonexistent" and ask a database question')
def run_qbot_with_nonexistent_profile():
    """Run SQLBot with non-existent profile name."""
    # This will test error handling for invalid profile names
    pass

@then('SQLBot should use the "mycompany" profile for database connection')
def should_use_mycompany_profile():
    """SQLBot should use the specified profile name."""
    # This will be implemented in the actual feature
    pass

@then('not show profile not found errors')
def no_profile_not_found_errors():
    """SQLBot should not show profile errors when profile exists."""
    # This will be implemented in the actual feature
    pass

@then('SQLBot should show a profile not found error')
def should_show_profile_not_found_error():
    """SQLBot should show helpful error for missing profile."""
    # This will be implemented in the actual feature
    pass

@then('suggest creating a profile named "nonexistent"')
def suggest_creating_nonexistent_profile():
    """SQLBot should suggest creating the specified profile name."""
    # This will be implemented in the actual feature
    pass

@then('provide setup instructions for the "nonexistent" profile')
def provide_setup_instructions_for_nonexistent():
    """SQLBot should provide setup instructions with the correct profile name."""
    # This will be implemented in the actual feature
    pass

# Additional missing step definitions

@given('I have a dbt profile named "sqlbot"')
def dbt_profile_sqlbot():
    """Mock a dbt profile named 'sqlbot'."""
    pass

@then('execute the query successfully')
def execute_query_successfully_alt():
    """Alternative step definition for execute query successfully."""
    # This will be implemented in the actual feature
    pass

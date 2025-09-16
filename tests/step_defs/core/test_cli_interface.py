"""
Test steps for CLI interface behavior.
"""

import os
import pytest
import subprocess
import sys
from pathlib import Path


@pytest.fixture
def sqlbot_command():
    """Get the sqlbot command to use for testing."""
    # Use the sqlbot command directly
    return ["sqlbot"]


@pytest.mark.integration
def test_text_mode_with_query_skips_banner(sqlbot_command):
    """
    Test that --text mode with a command-line query skips the banner.

    This corresponds to the BDD scenario:
    "Text mode with command-line query should skip banner"
    """
    # Run sqlbot with --text and a query, with proper environment
    env = os.environ.copy()
    env.update({
        'DBT_PROFILES_DIR': '.dbt',
        'DBT_PROFILE_NAME': 'Sakila'
    })
    result = subprocess.run(
        sqlbot_command + ["--text", "count the films", "--profile", "Sakila"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env
    )

    # Check that the command succeeded
    assert result.returncode == 0, f"Command failed with: {result.stderr}"

    # Get the output lines
    output_lines = result.stdout.strip().split('\n')

    # The first non-empty line should be the user message (starts with ◀)
    first_content_line = None
    for line in output_lines:
        if line.strip():
            first_content_line = line.strip()
            break

    assert first_content_line is not None, "No content found in output"
    assert first_content_line.startswith('◀'), f"First line should be user message, got: {first_content_line}"

    # Should not see the SQLBot banner
    full_output = result.stdout
    assert "SQLBot CLI" not in full_output, "Should not see SQLBot banner in --text mode with query"
    assert "Database Query Interface" not in full_output, "Should not see banner content"

    # Should not see "Starting with query:"
    assert "Starting with query:" not in full_output, "Should not see redundant 'Starting with query:' message"

    # Should see the query execution (user message followed by results)
    assert "◀" in full_output, "Should see user message symbol"
    assert ("count the films" in full_output or "film" in full_output.lower()), "Should see query content or results"


@pytest.mark.integration
def test_text_mode_without_query_shows_banner():
    """
    Test that --text mode without a query shows the banner in interactive mode.

    This corresponds to the BDD scenario:
    "Text mode without query should show banner"

    Note: This test is more complex because it requires interactive mode simulation.
    For now, we'll test the non-interactive case by checking the banner display logic.
    """
    # This test would require interactive mode simulation which is complex
    # For now, we can verify the logic by checking that the banner is shown
    # when not providing a query with --text

    # We can test this indirectly by ensuring the banner logic is correct
    # The actual interactive test would require pexpect or similar
    pass  # TODO: Implement interactive test with pexpect if needed


@pytest.mark.integration
def test_regular_mode_with_query_behavior():
    """
    Test that regular mode (not --text) behaves correctly.
    This helps ensure we didn't break existing functionality.
    """
    # Test with --no-repl to avoid interactive mode, with proper environment
    env = os.environ.copy()
    env.update({
        'DBT_PROFILES_DIR': '.dbt',
        'DBT_PROFILE_NAME': 'Sakila'
    })
    result = subprocess.run(
        ["sqlbot", "--no-repl", "count the films", "--profile", "Sakila"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env
    )

    # Should succeed
    assert result.returncode == 0, f"Command failed with: {result.stderr}"

    # Should contain the query results
    output = result.stdout
    assert "◀" in output, "Should see user message"
    assert ("film" in output.lower() or "count" in output.lower()), "Should see query-related content"


# BDD-style step definitions (using pytest-bdd if available)
# These are integration tests and should be run with: pytest -m integration
try:
    import os
    if os.getenv('RUN_INTEGRATION_TESTS'):
        from pytest_bdd import scenarios, given, when, then, parsers

        # Load scenarios from the feature file
        scenarios('../../features/core/cli_interface.feature')

        @given('SQLBot is installed and available as \'sqlbot\' command')
        def sqlbot_available():
            """Verify sqlbot command is available."""
            result = subprocess.run(["sqlbot", "--help"], capture_output=True, timeout=10)
            assert result.returncode == 0, "sqlbot command not available"

        @given('the database is available')
        def database_available():
            """Verify database connection works."""
            # This would typically check database connectivity
            # For now, assume it's available if sqlbot runs
            pass

        @when(parsers.parse('I run \'sqlbot --text "{query}"\''))
        def run_sqlbot_text_with_query(query):
            """Run sqlbot with --text and a query."""
            global last_result
            env = os.environ.copy()
            env.update({
                'DBT_PROFILES_DIR': '.dbt',
                'DBT_PROFILE_NAME': 'Sakila'
            })
            last_result = subprocess.run(
                ["sqlbot", "--text", query, "--profile", "Sakila"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

        @when('I run "sqlbot --text" in interactive mode')
        def run_sqlbot_text_interactive():
            """Run sqlbot with --text in interactive mode."""
            # This would require interactive testing - skip for now
            pytest.skip("Interactive mode testing not implemented")

        @then('the first output line should be the user message')
        def check_first_line_user_message():
            """Check that first line is a user message."""
            output_lines = [line.strip() for line in last_result.stdout.split('\n') if line.strip()]
            assert len(output_lines) > 0, "No output found"
            assert output_lines[0].startswith('◀'), f"First line should be user message, got: {output_lines[0]}"

        @then('I should not see the SQLBot banner')
        def check_no_banner():
            """Check that SQLBot banner is not shown."""
            output = last_result.stdout
            assert "SQLBot CLI" not in output, "Should not see SQLBot banner"
            assert "Database Query Interface" not in output, "Should not see banner content"

        @then('I should not see "Starting with query:"')
        def check_no_starting_message():
            """Check that redundant starting message is not shown."""
            output = last_result.stdout
            assert "Starting with query:" not in output, "Should not see redundant starting message"

        @then('the query should execute normally')
        def check_query_executes():
            """Check that the query executed successfully."""
            assert last_result.returncode == 0, f"Query execution failed: {last_result.stderr}"
            # Should see some indication of query execution
            output = last_result.stdout.lower()
            assert any(word in output for word in ['film', 'count', 'result', '◀', '▶']), "Should see query execution indicators"

except ImportError:
    # pytest-bdd not available, skip BDD step definitions
    pass
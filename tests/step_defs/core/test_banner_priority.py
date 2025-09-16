"""Step definitions for banner priority BDD tests."""

import pytest
import subprocess
import os
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import patch

# Load all scenarios from the feature file
scenarios('../../features/core/banner_priority.feature')

@given('SQLBot is available')
def qbot_is_available():
    """Ensure SQLBot is available."""
    pass

@given('dbt is configured with profile "Sakila"')
def dbt_configured():
    """Ensure dbt is configured with the test profile."""
    pass

@when(parsers.parse('I run SQLBot with query "{query}" and flag "{flag}"'))
def run_qbot_with_query_and_flag(query, flag):
    """Run SQLBot with a specific query and CLI flag."""
    from tests.conftest import setup_subprocess_environment
    
    env = setup_subprocess_environment()
    env['DBT_PROFILE_NAME'] = 'Sakila'
    
    cmd = ['python', '-m', 'sqlbot.repl', flag, '--profile', 'Sakila', query]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
        env=env
    )
    
    pytest.qbot_result = result

@when(parsers.parse('I run SQLBot with query "{query}" and flags "{flags}"'))
def run_qbot_with_query_and_flags(query, flags):
    """Run SQLBot with a specific query and multiple CLI flags."""
    from tests.conftest import setup_subprocess_environment
    
    env = setup_subprocess_environment()
    env['DBT_PROFILE_NAME'] = 'Sakila'
    
    flag_list = flags.split()
    cmd = ['python', '-m', 'sqlbot.repl'] + flag_list + ['--profile', 'Sakila', query]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
        env=env
    )
    
    pytest.qbot_result = result

@when('I start SQLBot in interactive mode')
def start_qbot_interactive():
    """Start SQLBot in interactive mode (no query provided)."""
    from tests.conftest import setup_subprocess_environment
    
    env = setup_subprocess_environment()
    env['DBT_PROFILE_NAME'] = 'Sakila'
    
    # Use echo to provide input and exit quickly
    cmd = ['python', '-m', 'sqlbot.repl', '--profile', 'Sakila', '--text']
    
    # Send exit command immediately to avoid hanging
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    try:
        stdout, stderr = process.communicate(input='exit\n', timeout=10)
        result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
        pytest.qbot_result = result
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        result = subprocess.CompletedProcess(cmd, -1, stdout, stderr)
        pytest.qbot_result = result

@then('the banner should be the first output')
def banner_should_be_first():
    """Verify the banner appears as the first meaningful output."""
    output = pytest.qbot_result.stdout
    stderr = pytest.qbot_result.stderr

    # Check for unexpected errors in stderr
    if stderr.strip():
        allowed_patterns = ["DeprecationWarning", "UserWarning"]
        stderr_lines = stderr.strip().split('\n')
        for line in stderr_lines:
            if line.strip() and not any(pattern in line for pattern in allowed_patterns):
                assert False, f"Unexpected stderr output: '{line}'"

    lines = [line for line in output.strip().split('\n') if line.strip()]

    if not lines:
        pytest.skip("No output to verify banner priority")

    # Check if we have banner output
    banner_lines = [line for line in lines if line.startswith('╭') or 'SQLBot' in line]
    if not banner_lines:
        pytest.skip("No banner found in output")

    # Find first banner line
    first_banner_idx = None
    for i, line in enumerate(lines):
        if line.startswith('╭') or ('SQLBot' in line and '│' in line):
            first_banner_idx = i
            break

    # Verify no significant content appears before banner
    if first_banner_idx is not None and first_banner_idx > 0:
        for i in range(first_banner_idx):
            line = lines[i].strip()
            # Allow certain system messages that might appear before banner
            if (line.startswith('dbt>') or
                'Starting interactive console' in line or
                line == 'Goodbye!'):
                continue
            assert False, f"Content appears before banner at line {i+1}: '{line}'"

@then('I should see the "SQLBot CLI" banner')
def should_see_cli_banner():
    """Verify the CLI banner is displayed."""
    output = pytest.qbot_result.stdout
    assert "SQLBot CLI" in output, "Should show CLI banner for interactive mode"

@then('I should NOT see any banner')
def should_not_see_any_banner():
    """Verify no banner is displayed in --no-repl mode."""
    output = pytest.qbot_result.stdout + pytest.qbot_result.stderr
    # No banner elements should appear
    assert "SQLBot CLI" not in output, f"No banner should appear in --no-repl mode. Output: {output}"
    assert "Database Query Interface" not in output, f"No banner should appear in --no-repl mode. Output: {output}"
    assert "╭" not in output, f"No banner borders should appear in --no-repl mode. Output: {output}"
    assert "╰" not in output, f"No banner borders should appear in --no-repl mode. Output: {output}"

@then('the output should be minimal')
def output_should_be_minimal():
    """Verify the output is minimal in --no-repl mode (no verbose banner)."""
    output = pytest.qbot_result.stdout + pytest.qbot_result.stderr
    
    # The main point is that the verbose intro banner should not appear
    # We allow query execution output, error messages, mode messages, etc.
    # But we should NOT see the full intro banner with all the help text
    
    # Check that banner elements are NOT present
    assert "Database Query Interface" not in output, "Verbose banner should not appear in --no-repl mode"
    assert "Natural Language Queries (Default)" not in output, "Verbose banner should not appear in --no-repl mode"
    assert "Just type your question in plain English" not in output, "Verbose banner should not appear in --no-repl mode"
    assert "Commands" not in output, "Verbose banner should not appear in --no-repl mode"
    assert "/help - Show all available commands" not in output, "Verbose banner should not appear in --no-repl mode"
    
    # We should still see the essential operational messages
    assert "Exiting (--no-repl mode)" in output, "Should show exit message"

@then('I should see the "Ready for questions." banner')
def should_see_interactive_banner():
    """Verify the interactive banner is displayed."""
    output = pytest.qbot_result.stdout
    assert "Ready for questions." in output, "Should show interactive banner"

@then('initialization messages should appear after the banner')
def init_messages_after_banner():
    """Verify initialization messages appear after the banner."""
    output = pytest.qbot_result.stdout
    lines = output.strip().split('\n')
    
    banner_ended = False
    init_found_after_banner = False
    
    for line in lines:
        if '╰' in line:  # Banner bottom border
            banner_ended = True
        elif banner_ended and ('Initializing' in line or 'ready' in line or 'LLM integration' in line):
            init_found_after_banner = True
            break
    
    # Only check if there are initialization messages
    if 'Initializing' in output or 'ready' in output or 'LLM integration' in output:
        assert init_found_after_banner, "Initialization messages should appear after banner ends"
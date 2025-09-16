Feature: No-REPL Mode
  As a user running SQLBot in automation or CI/CD
  I want to execute queries without entering interactive mode
  So that SQLBot can be used in scripts and pipelines

  Background:
    Given SQLBot is available
    And dbt is configured with profile "Sakila"

  Scenario: Execute query with --no-repl flag
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--no-repl"
    Then I should NOT see the intro banner
    And I should see "Exiting (--no-repl mode)"
    And SQLBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Execute query with --norepl synonym
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--norepl"
    Then I should NOT see the intro banner
    And I should see "Exiting (--no-repl mode)"
    And SQLBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Execute dangerous query with --no-repl (safeguards enabled by default)
    When I run SQLBot with query "CREATE TABLE test_table (id INT);" and flag "--no-repl"
    Then I should NOT see the intro banner
    And I should see "✖ Query disallowed due to dangerous operations: CREATE"
    And I should see "Exiting (--no-repl mode)"
    And SQLBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Execute dangerous query with --no-repl and --dangerous (safeguards disabled)
    When I run SQLBot with query "CREATE TABLE test_table (id INT);" and flags "--no-repl --dangerous"
    Then I should NOT see the intro banner
    And I should see "Dangerous Mode Enabled - Safeguards disabled, all operations allowed"
    And I should see "Exiting (--no-repl mode)"
    And SQLBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Use /no-repl command in interactive mode
    Given SQLBot is running in interactive mode
    When I enter "/no-repl"
    Then I should see "Exiting interactive mode..."
    And SQLBot should exit
    And the exit code should be 0

  Scenario: /no-repl command appears in help
    Given SQLBot is running in interactive mode
    When I enter "/help"
    Then I should see "/no-repl" in the command list
    And I should see "Exit interactive mode" as the description

  Scenario: No intro banner in --no-repl mode
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--no-repl"
    Then I should NOT see the intro banner
    And I should see "Exiting (--no-repl mode)"
    And SQLBot should exit without starting interactive mode
    And the exit code should be 0
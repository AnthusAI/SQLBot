Feature: No-REPL Mode
  As a user running QBot in automation or CI/CD
  I want to execute queries without entering interactive mode
  So that QBot can be used in scripts and pipelines

  Background:
    Given QBot is available
    And dbt is configured with profile "Sakila"

  Scenario: Execute query with --no-repl flag
    When I run QBot with query "SELECT 42 AS Answer;" and flag "--no-repl"
    Then I should see the ready banner
    And I should see "Starting with query: SELECT 42 AS Answer;"
    And I should see "Exiting (--no-repl mode)"
    And QBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Execute query with --norepl synonym
    When I run QBot with query "SELECT 42 AS Answer;" and flag "--norepl"
    Then I should see the ready banner
    And I should see "Starting with query: SELECT 42 AS Answer;"
    And I should see "Exiting (--no-repl mode)"
    And QBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Execute dangerous query with --no-repl and --read-only
    When I run QBot with query "CREATE TABLE test_table (id INT);" and flags "--no-repl --read-only"
    Then I should see the ready banner
    And I should see "Query blocked by read-only mode!"
    And I should see "Dangerous operations detected: CREATE"
    And I should see "Exiting (--no-repl mode)"
    And QBot should exit without starting interactive mode
    And the exit code should be 0

  Scenario: Use /no-repl command in interactive mode
    Given QBot is running in interactive mode
    When I enter "/no-repl"
    Then I should see "Exiting interactive mode..."
    And QBot should exit
    And the exit code should be 0

  Scenario: /no-repl command appears in help
    Given QBot is running in interactive mode
    When I enter "/help"
    Then I should see "/no-repl" in the command list
    And I should see "Exit interactive mode" as the description
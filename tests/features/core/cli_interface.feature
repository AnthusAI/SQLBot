Feature: Command Line Interface
  As a user of SQLBot
  I want to use SQLBot from the command line
  So that I can integrate it into scripts and workflows

  Background:
    Given SQLBot is installed and available as 'sqlbot' command

  Scenario: Display help information
    When I run "sqlbot --help"
    Then I should see usage information
    And I should see available options
    And I should see example commands

  Scenario: Execute single query from command line
    Given the database is available
    When I run 'sqlbot "How many tables are in the database?"'
    Then the query should execute
    And I should see the results
    And the command should exit cleanly

  Scenario: Show LLM context information
    Given the database is available
    When I run 'sqlbot --context "test query"'
    Then I should see the LLM conversation context
    And the query should still execute normally

  Scenario: Interactive REPL mode
    Given the database is available
    When I run "sqlbot" without arguments
    Then I should enter interactive mode
    And I should see the welcome banner
    And I should be able to enter queries
    And I should be able to exit with "exit" command

  Scenario: Handle invalid command line arguments
    When I run "sqlbot --invalid-option"
    Then I should see an error message
    And I should see help information
    And the command should exit with error code

  Scenario: Module execution
    Given SQLBot is installed
    When I run "python -m sqlbot.repl --help"
    Then I should see the same help as "sqlbot --help"
    And the functionality should be identical

  Scenario: Text mode with command-line query should skip banner
    Given the database is available
    When I run 'sqlbot --text "count the films"'
    Then the first output line should be the user message
    And I should not see the SQLBot banner
    And I should not see "Starting with query:"
    And the query should execute normally

  Scenario: Text mode without query should show banner
    Given the database is available
    When I run "sqlbot --text" in interactive mode
    Then I should see the SQLBot banner
    And I should enter interactive mode
    And I should be able to enter queries

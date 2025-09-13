Feature: REPL Commands and Navigation
  As a user of SQLBot's interactive mode
  I want to use slash commands and navigate efficiently
  So that I can explore the database and manage my session

  Background:
    Given I am in SQLBot interactive mode
    And the database connection is working

  Scenario: List available commands
    When I type "/help"
    Then I should see a formatted table of all available commands
    And each command should have a clear description
    And I should see examples of usage

  Scenario: List database tables
    When I type "/tables"
    Then I should see a formatted list of database tables
    And the tables should be displayed with full names
    And I should see a summary of total table count

  Scenario: Execute dbt debug
    When I type "/debug"
    Then dbt should check the connection
    And I should see connection status information
    And any configuration issues should be reported

  Scenario: Run dbt models
    When I type "/run"
    Then dbt should execute all models
    And I should see progress information
    And I should see success/failure status for each model

  Scenario: Show command history
    Given I have executed several commands
    When I type "/history"
    Then I should see my recent command history
    And commands should be numbered
    And I should see the last 20 commands

  Scenario: Navigate command history with arrows
    Given I have executed several commands
    When I press the up arrow key
    Then I should see my previous command
    And I should be able to edit and re-execute it

  Scenario: Exit the REPL
    When I type "exit"
    Then SQLBot should exit gracefully
    And display a goodbye message
    And save my command history

  Scenario: Handle unknown commands
    When I type "/unknown-command"
    Then I should see an error message
    And I should be shown available commands
    And the REPL should remain active

  Scenario: Multi-line query support
    When I start typing a query with unclosed braces
    Then SQLBot should prompt for continuation
    And I should be able to complete the query on multiple lines
    And the complete query should execute when finished

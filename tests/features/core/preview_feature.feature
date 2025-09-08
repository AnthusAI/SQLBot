Feature: Preview SQL Compilation Feature
  As a user of QBot
  I want to preview SQL compilation before execution
  So that I can verify the generated SQL and choose whether to execute it

  Background:
    Given QBot is running in interactive mode
    And the database is available

  Scenario: Preview SQL compilation with //preview command
    Given I am in the QBot REPL
    When I enter "//preview"
    Then I should see "Preview Mode - Enter SQL to preview compilation:"
    When I enter "SELECT TOP 5 * FROM {{ source('sakila', 'film') }}"
    Then I should see "Compiled SQL Preview:"
    And I should see the compiled SQL query
    And I should see "Execute this query? (y/n):"

  Scenario: Preview and approve execution
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter "SELECT TOP 3 * FROM sakila.film"
    Then I should see the compiled SQL preview
    When I respond "y" to the execution prompt
    Then the query should execute
    And I should see query results

  Scenario: Preview and reject execution
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter "SELECT COUNT(*) FROM sakila.film"
    Then I should see the compiled SQL preview
    When I respond "n" to the execution prompt
    Then I should see "Query execution cancelled"
    And the query should not execute

  Scenario: Preview with dbt source syntax compilation
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter "SELECT TOP 5 * FROM {{ source('sakila', 'film') }}"
    Then I should see the compiled SQL preview
    And the compiled SQL should contain "sakila"."film"
    And the compiled SQL should not contain "{{ source"

  Scenario: Preview with empty query
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter an empty query
    Then I should see "No query provided"
    And I should return to the main prompt

  Scenario: Cancel preview with Ctrl+C
    Given I am in the QBot REPL
    When I enter "//preview"
    And I press Ctrl+C during SQL input
    Then I should see "Preview cancelled"
    And I should return to the main prompt

  Scenario: Cancel execution prompt with Ctrl+C
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter "SELECT 1"
    And I press Ctrl+C during execution prompt
    Then I should see "Query execution cancelled"
    And I should return to the main prompt

  Scenario: Preview with compilation error
    Given I am in the QBot REPL
    When I enter "//preview"
    And I enter invalid SQL syntax
    Then I should see an error message about compilation failure
    And I should not be prompted for execution

  Scenario: Unknown double-slash command
    Given I am in the QBot REPL
    When I enter "//unknown"
    Then I should see "Unknown double-slash command: //unknown"
    And I should see available double-slash commands
    And I should see "//preview - Preview compiled SQL before execution"
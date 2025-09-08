Feature: SQL and dbt Query Execution
  As a user of QBot
  I want to execute SQL and dbt queries directly
  So that I can have precise control over database operations

  Background:
    Given QBot is properly configured
    And the database connection is working
    And dbt is properly initialized

  Scenario: Execute basic SQL query
    Given I have a working QBot instance
    When I execute the SQL query "SELECT COUNT(*) FROM sys.tables;"
    Then the query should execute successfully
    And I should receive a numeric result
    And the result should be formatted nicely

  Scenario: Execute dbt source query
    Given I have a working QBot instance
    When I execute the dbt query "SELECT TOP 5 * FROM {{ source('your_source', 'your_main_table') }};"
    Then the dbt compilation should succeed
    And the query should execute successfully
    And I should receive formatted table results

  Scenario: Execute dbt macro
    Given I have a working QBot instance
    And dbt macros are available
    When I execute "{{ find_report_by_id(283195544) }}"
    Then the macro should be compiled correctly
    And the query should execute successfully
    And I should receive specific report data

  Scenario: Handle SQL syntax errors
    Given I have a working QBot instance
    When I execute an invalid SQL query "SELCT * FRM invalid_table;"
    Then QBot should detect the syntax error
    And provide a helpful error message
    And not crash the application

  Scenario: Handle database connection issues
    Given QBot is configured but database is unavailable
    When I try to execute any SQL query
    Then QBot should detect the connection failure
    And provide a clear error message about connectivity
    And suggest troubleshooting steps

  Scenario: Query timeout handling
    Given I have a working QBot instance
    When I execute a query that would take too long
    Then QBot should timeout gracefully
    And inform me about the timeout
    And suggest optimizing the query

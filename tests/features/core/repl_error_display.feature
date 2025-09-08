Feature: REPL Error Display for Users
  As a user of the QBot REPL
  I want to see clear, detailed error messages when database queries fail
  So that I can understand what went wrong and how to fix it

  Background:
    Given QBot REPL is running
    And the database connection is configured

  Scenario: SQL syntax error is clearly displayed in REPL
    Given I am in the QBot REPL
    When I enter an invalid SQL query "SELECT * FROM table WHERE invalid syntax;"
    Then I should see an error message containing "syntax error"
    And the error message should be displayed in red color
    And the error message should include the specific syntax issue
    And I should remain in the REPL for the next command

  Scenario: Table not found error shows helpful message
    Given I am in the QBot REPL
    When I ask "Show me data from nonexistent_table"
    And the LLM generates a query for a table that doesn't exist
    Then I should see an error message containing "table" and "not found"
    And the error message should be clearly visible to the user
    And the error should suggest checking available tables
    And I should remain in the REPL for the next command

  Scenario: Database connection error is user-friendly
    Given QBot is configured with invalid database credentials
    When I start the QBot REPL
    And I ask "How many tables are there?"
    Then I should see a clear connection error message
    And the error should mention database connection issues
    And the error should suggest checking configuration
    And the error should not expose sensitive connection details

  Scenario: Column not found error provides context
    Given I am in the QBot REPL
    When I ask "Show me the invalid_column from the film table"
    And the LLM generates a query with a nonexistent column
    Then I should see an error message about the invalid column
    And the error should specify which column was not found
    And the error should suggest checking the table schema
    And I should remain in the REPL for the next command

  Scenario: Permission denied error is informative
    Given QBot is in read-only mode
    When I ask "Delete all records from the test table"
    And the LLM generates a DELETE query
    Then I should see a permission denied error
    And the error should mention read-only mode or insufficient permissions
    And the error should suggest using SELECT queries instead
    And I should remain in the REPL for the next command

  Scenario: Timeout error provides clear feedback
    Given I am in the QBot REPL
    When I ask a question that generates a very slow query
    And the query times out
    Then I should see a timeout error message
    And the error should mention the timeout duration
    And the error should suggest simplifying the query
    And I should remain in the REPL for the next command

  Scenario: Multiple error types are handled consistently
    Given I am in the QBot REPL
    When I encounter different types of database errors in sequence
    Then each error should be displayed clearly and consistently
    And each error should use appropriate color coding
    And each error should provide actionable feedback
    And I should be able to continue using the REPL after each error

  Scenario: Error messages include query context
    Given I am in the QBot REPL
    When I ask "Show me sales data with invalid syntax"
    And the LLM generates a problematic query
    Then the error message should include or reference the failed query
    And I should be able to understand which part of my request caused the issue
    And the error should help me reformulate my question

  Scenario: Error logging captures full details for debugging
    Given I am in the QBot REPL with debug logging enabled
    When a database query fails with any type of error
    Then the full error details should be logged
    And the log should include the original user question
    And the log should include the generated SQL query
    And the log should include the complete database error message
    And the log should include timestamp and context information

  Scenario: Non-interactive mode shows errors clearly
    Given I run QBot in non-interactive mode with --no-repl
    When I provide a query that will cause a database error
    Then the error should be displayed to stdout/stderr
    And the error should be clearly formatted
    And the error should not be mixed with other output
    And the process should exit with appropriate error code

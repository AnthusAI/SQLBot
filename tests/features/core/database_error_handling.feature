Feature: Database Error Handling in Conversation History
  As a user of QBot
  I want database query errors to be visible to both me and the LLM
  So that the LLM can learn from errors and adjust its approach

  Background:
    Given QBot is configured with a test database profile
    And the LLM integration is available

  Scenario: Database query error is added to LLM conversation history
    Given I start a new conversation with QBot
    When I ask "Show me data from nonexistent_table"
    And the LLM generates a query that fails with a database error
    Then the database error should be captured in the conversation history
    When I ask a follow-up question "Try a different approach"
    Then the LLM should have access to the previous error in its context
    And the LLM should reference the previous error in its response

  Scenario: SQL syntax error is visible to LLM for learning
    Given I start a new conversation with QBot
    When I ask "Count all records with invalid SQL syntax"
    And the LLM generates invalid SQL that causes a syntax error
    Then the SQL syntax error should be captured in the conversation history
    When I ask "Fix the previous query"
    Then the LLM should acknowledge the previous syntax error
    And the LLM should generate corrected SQL

  Scenario: Database connection error is handled properly
    Given QBot is configured with invalid database credentials
    When I ask "How many tables are there?"
    Then I should see a clear database connection error message
    And the error should be captured in the conversation history
    When I ask a follow-up question
    Then the LLM should reference the connection issue

  Scenario: Table not found error guides LLM to correct approach
    Given I start a new conversation with QBot
    When I ask "Show me data from table_that_does_not_exist"
    And the LLM generates a query for the nonexistent table
    Then I should see a "table not found" error message
    And the error should be captured in the conversation history
    When I ask "What tables are actually available?"
    Then the LLM should reference the previous table error
    And the LLM should generate a query to list available tables

  Scenario: Column not found error helps LLM adjust query
    Given I start a new conversation with QBot
    When I ask "Show me the nonexistent_column from the film table"
    And the LLM generates a query with an invalid column name
    Then I should see a "column not found" error message
    And the error should be captured in the conversation history
    When I ask "Show me the actual columns available"
    Then the LLM should reference the previous column error
    And the LLM should generate a query to describe the table structure

  Scenario: Permission denied error is handled gracefully
    Given QBot is configured with read-only database access
    When I ask "Delete all records from the test table"
    And the LLM generates a DELETE query
    Then I should see a permission denied or read-only error
    And the error should be captured in the conversation history
    When I ask "Show me the data instead"
    Then the LLM should reference the permission error
    And the LLM should generate a SELECT query instead

  Scenario: Multiple consecutive errors build conversation context
    Given I start a new conversation with QBot
    When I ask "Show me data from wrong_table with wrong_column"
    And the LLM generates a query with multiple errors
    Then I should see database error messages
    And the errors should be captured in the conversation history
    When I ask "Try again with correct table name"
    And the LLM generates another query with remaining errors
    Then I should see additional error messages
    And both errors should be in the conversation history
    When I ask "Now fix all the issues"
    Then the LLM should reference both previous errors
    And the LLM should generate a corrected query

  Scenario: Error details are preserved in conversation history
    Given I start a new conversation with QBot
    When I ask "Execute invalid SQL query"
    And the LLM generates SQL that produces a detailed error message
    Then the complete error message should be captured
    And the error should include specific details like line numbers or column names
    When I ask about the error details
    Then the LLM should be able to reference the specific error information

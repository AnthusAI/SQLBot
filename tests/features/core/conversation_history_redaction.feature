Feature: Conversation History Redaction
  As a SQLBot user
  I want query results to be redacted in conversation history
  So that the conversation stays manageable while preserving access to data

  Background:
    Given SQLBot is initialized with conversation memory
    And the query result list is empty

  Scenario: Most recent query result shows full data in conversation history
    When I execute a SQL query "SELECT 'Alice' as name, 25 as age"
    Then the conversation history should contain the full JSON data
    And the JSON should include all columns and rows
    And the JSON should include the query index
    And the JSON should not be redacted

  Scenario: Previous query results are redacted with placeholders
    Given I execute a SQL query "SELECT 'first' as data"
    When I execute a SQL query "SELECT 'second' as data"
    Then the conversation history should contain a placeholder for query #1
    And the placeholder should mention "Query Result #1"
    And the placeholder should mention "Use query_result_lookup tool"
    And the conversation history should contain full data for query #2

  Scenario: Multiple historical queries all get redacted except latest
    Given I execute 4 SQL queries with different results
    When I check the conversation history
    Then queries #1, #2, and #3 should have placeholder messages
    And query #4 should have full JSON data
    And each placeholder should have the correct index number
    And each placeholder should indicate success/failure status

  Scenario: Failed queries also get redacted with appropriate placeholders
    Given I execute a successful query "SELECT 1 as success"
    When I execute a failed query "INVALID SQL SYNTAX"
    Then the conversation history should have a placeholder for query #1
    And the placeholder should show "✅ Success"
    And the conversation history should have full error data for query #2
    And the error data should include the failure details

  Scenario: Conversation history includes row count in placeholders
    Given I execute a query returning 5 rows
    When I execute another query returning 10 rows
    Then the placeholder for query #1 should mention "5 rows"
    And the full data for query #2 should show row_count: 10

  Scenario: LLM can access redacted data using lookup tool
    Given I have 3 queries with redacted results in conversation history
    When the LLM uses query_result_lookup tool with index 2
    Then it should receive the full JSON data for query #2
    And the data should match what was originally redacted
    And the LLM can continue the conversation with that data

  Scenario: Redaction preserves conversation flow and context
    Given I ask "Show me user data"
    And SQLBot executes "SELECT name, age FROM users" returning 100 rows
    And I ask "What's the average age?"
    And SQLBot executes "SELECT AVG(age) FROM users" returning 1 row
    When I check the conversation history
    Then I should see my questions in full
    And I should see a placeholder for the first query (100 rows)
    And I should see full JSON for the second query (1 row)
    And the conversation flow should remain coherent

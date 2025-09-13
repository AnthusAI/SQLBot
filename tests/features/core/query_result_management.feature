Feature: Query Result Management
  As a SQLBot user
  I want my query results to be stored and indexed
  So that I can reference them later in the conversation

  Background:
    Given SQLBot is initialized with a test session
    And the query result list is empty

  Scenario: First query result is recorded with index 1
    When I execute a SQL query "SELECT 1 as test_column"
    Then the query result should be recorded with index 1
    And the result should include timestamp metadata
    And the result should contain the original query text
    And the result should contain the structured data

  Scenario: Multiple query results get sequential indices
    When I execute a SQL query "SELECT 1 as first"
    And I execute a SQL query "SELECT 2 as second"  
    And I execute a SQL query "SELECT 3 as third"
    Then the query results should have indices 1, 2, and 3
    And each result should have a unique timestamp
    And the latest result should be index 3

  Scenario: Query result lookup tool can retrieve historical data
    Given I have executed 3 queries with results
    When I use the query_result_lookup tool with index 2
    Then I should get the full data from query result #2
    And the data should include the original query text
    And the data should include all columns and rows
    And the data should include execution metadata

  Scenario: Query result lookup handles invalid indices gracefully
    Given I have executed 2 queries with results
    When I use the query_result_lookup tool with index 5
    Then I should get an error message about index not found
    And the error should list available indices [1, 2]

  Scenario: Failed queries are also recorded in the result list
    When I execute an invalid SQL query "SELECT FROM invalid_syntax"
    Then the query result should be recorded with index 1
    And the result should be marked as failed
    And the result should contain the error message
    And the result should still have timestamp metadata

  Scenario: Query results persist across session reloads
    Given I execute a SQL query "SELECT 'persistent' as data"
    And the result is recorded with index 1
    When I create a new QueryResultList with the same session ID
    Then the query result list should contain 1 result
    And the result should have index 1
    And the result data should match the original query

  Scenario: Different sessions have separate result lists
    Given I have a session "session_A"
    And I have a session "session_B"
    When I execute a query in session_A
    And I execute a query in session_B
    Then session_A should have 1 result with index 1
    And session_B should have 1 result with index 1
    And the results should be independent

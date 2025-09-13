Feature: Query Results Display
  As a SQLBot user
  I want to see the actual database query results
  So that I can verify the data and understand what the query returned

  Background:
    Given SQLBot is configured with a valid database connection
    And I have access to database tables

  Scenario: Database query results are always displayed to user
    Given I run a simple database query
    When the query executes successfully
    Then I should see the actual query results in the output
    And the results should include column headers
    And the results should include data rows
    And the results should be formatted in a readable table

  Scenario: Query results are shown even when LLM processing fails
    Given I run a database query that returns data
    When the query executes successfully but LLM processing encounters an error
    Then I should still see the actual database results
    And the results should be displayed before any error messages

  Scenario: Failed queries show clear error messages
    Given I run an invalid database query
    When the query fails to execute
    Then I should see a clear error message
    And the error message should include details about what went wrong
    And I should not see empty or missing result sections

  Scenario: Empty result sets are clearly indicated
    Given I run a query that returns no rows
    When the query executes successfully
    Then I should see a message indicating no results were found
    And I should not see an empty results section

  Scenario: Large result sets are properly limited and indicated
    Given I run a query that would return many rows
    When the query executes with a limit
    Then I should see the limited number of rows
    And I should see an indication of how many rows were shown
    And I should see an indication if more rows are available

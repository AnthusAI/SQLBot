Feature: LLM Integration
  As a user of SQLBot
  I want to interact with the database using natural language
  So that I can query data without writing SQL

  Background:
    Given SQLBot is properly configured
    And the LLM integration is available
    And the database connection is working

  Scenario: Basic natural language query
    Given I have a working SQLBot instance
    When I ask "How many tables are in the database?"
    Then the LLM should generate a SQL query
    And the query should execute successfully
    And I should receive a meaningful response about table count

  Scenario: Complex analytical query
    Given I have a working SQLBot instance
    When I ask "Show me the top 5 agents by call volume this month"
    Then the LLM should generate an appropriate SQL query with filtering and aggregation
    And the query should execute successfully
    And I should receive formatted results showing agent names and call counts

  Scenario: Query with follow-up context
    Given I have a working SQLBot instance
    And I previously asked about "table counts"
    When I ask "What about just the report tables?"
    Then the LLM should use conversation context
    And generate a query filtering for report-related tables
    And provide relevant results

  Scenario: Handling query errors gracefully
    Given I have a working SQLBot instance
    When I ask something that would generate invalid SQL
    Then the LLM should handle the error gracefully
    And provide a helpful error message
    And suggest alternative approaches

  Scenario: LLM unavailable fallback
    Given SQLBot is configured but LLM integration is unavailable
    When I try to ask a natural language question
    Then SQLBot should inform me that LLM is not available
    And suggest using SQL queries instead
    And still allow me to use the SQL/dbt functionality

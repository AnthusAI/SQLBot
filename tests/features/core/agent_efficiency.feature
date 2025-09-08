Feature: Agent Query Efficiency
  As a user of QBot
  I want the LLM agent to stop making queries when it gets the answer
  So that it doesn't waste time and resources on unnecessary database calls

  Background:
    Given QBot is properly configured
    And the LLM integration is available
    And the database connection is working

  Scenario: Agent stops after successful single query
    Given I have a working QBot instance
    When I ask "How many tables are in the database?"
    Then the LLM should make exactly 1 database query
    And the query should return a count result
    And the agent should stop and provide the answer
    And the agent should not make additional queries

  Scenario: Agent stops after getting sufficient data
    Given I have a working QBot instance  
    When I ask "What tables exist in the database?"
    Then the LLM should make at most 2 database queries
    And the queries should return table information
    And the agent should stop when it has sufficient data
    And the agent should not hit the max iterations limit

  Scenario: Agent uses previous query results within same session
    Given I have a working QBot instance
    And I ask "How many tables are there?" 
    And the agent successfully returns a count
    When I ask "List the table names"
    Then the LLM should remember the previous context
    And make efficient queries based on what it already knows
    And not repeat the same table counting query

  Scenario: Agent handles failed queries efficiently  
    Given I have a working QBot instance
    When I ask a question that generates invalid SQL
    Then the LLM should try alternative approaches
    But should not make more than 3 total query attempts
    And should provide a helpful response about the limitation

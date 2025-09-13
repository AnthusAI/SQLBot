Feature: Natural Language Query Processing
  As a data analyst
  I want to ask questions in plain English
  So that I can get insights without writing SQL

  Background:
    Given SQLBot is running with LLM integration enabled
    And I have access to the Sakila database
    And the database contains realistic test data

  Scenario: Basic table counting query
    When I ask "How many tables are in the database?"
    Then SQLBot should understand this is a table count request
    And generate appropriate SQL to count tables
    And return a clear answer like "There are 1,458 tables in the database"
    And show me the SQL that was executed

  Scenario: Agent performance analysis
    When I ask "Show me the top 5 agents by call volume this month"
    Then SQLBot should identify this needs agent and call data
    And generate SQL with proper date filtering for current month
    And aggregate call counts by agent
    And return formatted results showing agent names and call counts
    And sort results by call volume descending

  Scenario: Report-specific queries
    When I ask "Find me reports created by agent Smith in the last week"
    Then SQLBot should understand this needs report and agent filtering
    And generate SQL filtering by agent name and date range
    And return relevant report records
    And format the results in a readable table

  Scenario: Complex analytical query
    When I ask "What's the average call duration for each department this quarter?"
    Then SQLBot should identify this needs call duration and department data
    And generate SQL with date filtering for current quarter
    And calculate averages grouped by department
    And return results formatted with department names and durations

  Scenario: Follow-up context queries
    Given I previously asked "Show me all agents"
    When I ask "What about just the ones from the sales department?"
    Then SQLBot should use the conversation context
    And understand this is filtering the previous agent query
    And generate SQL that filters agents by department
    And return only sales department agents

  Scenario: Ambiguous query clarification
    When I ask "Show me the data"
    Then SQLBot should recognize this is too vague
    And ask for clarification about what specific data I want
    And suggest some common query types
    And wait for a more specific request

  Scenario: Query with business logic
    When I ask "Which agents are underperforming this month?"
    Then SQLBot should understand this requires performance metrics
    And either ask me to define "underperforming" criteria
    And use reasonable default thresholds if no criteria provided
    And generate SQL to calculate performance metrics
    And return agents below the threshold with their metrics

  Scenario: Data exploration query
    When I ask "What columns are available in the reports table?"
    Then SQLBot should generate SQL to describe table structure
    And return column names, types, and descriptions
    And format the results in a clear table structure

  Scenario: Trend analysis query
    When I ask "Show me the trend of daily call volumes over the last 30 days"
    Then SQLBot should generate SQL with date grouping and counting
    And return results ordered by date
    And suggest visualization options if available

  Scenario: Error handling for impossible queries
    When I ask "What's the color of the database?"
    Then SQLBot should recognize this doesn't make sense for a database
    And politely explain that databases don't have colors
    And suggest alternative queries about database properties
    And maintain a helpful tone

Feature: Data Exploration and Discovery
  As a data analyst new to the database
  I want to explore and understand the data structure
  So that I can effectively analyze the available information

  Background:
    Given SQLBot is running
    And I have access to the Sakila database
    And the database contains multiple tables and schemas

  Scenario: Discover available tables
    When I type "/tables"
    Then I should see a comprehensive list of all database tables
    And tables should be grouped by schema or category
    And I should see table row counts where available
    And the list should be formatted clearly and searchable

  Scenario: Explore table structure
    When I ask "What's in the main data table?"
    Then SQLBot should show me the table schema
    And display column names, data types, and descriptions
    And show sample data from the table
    And indicate any primary keys or indexes

  Scenario: Find related tables
    When I ask "What tables are related to agents?"
    Then SQLBot should search table names and descriptions
    And return tables containing agent-related data
    And show how tables might be related to each other
    And suggest common join patterns

  Scenario: Understand data relationships
    When I ask "How do I connect reports to agents?"
    Then SQLBot should identify the relationship between these entities
    And show the foreign key connections
    And provide example JOIN queries
    And explain the relationship cardinality

  Scenario: Sample data exploration
    When I ask "Show me some sample data from the calls table"
    Then SQLBot should return a representative sample
    And limit the results to a reasonable number of rows
    And show diverse examples if possible
    And highlight interesting or unusual values

  Scenario: Data quality assessment
    When I ask "Are there any data quality issues in the reports table?"
    Then SQLBot should check for common data quality problems
    And report on null values, duplicates, or outliers
    And suggest data cleaning strategies if needed
    And provide statistics about data completeness

  Scenario: Find recent data
    When I ask "What's the most recent data available?"
    Then SQLBot should identify date/timestamp columns
    And show the latest records across key tables
    And indicate data freshness and update frequency
    And highlight any stale or missing recent data

  Scenario: Explore data patterns
    When I ask "What are the most common values in the status column?"
    Then SQLBot should analyze the column distribution
    And show frequency counts for each value
    And identify any unusual or unexpected patterns
    And suggest further analysis opportunities

  Scenario: Discover business rules
    When I ask "What business rules can I infer from the data?"
    Then SQLBot should analyze constraints and patterns
    And identify possible business logic from data relationships
    And highlight validation rules or data constraints
    And suggest questions to ask business stakeholders

  Scenario: Find documentation
    When I ask "Is there any documentation for this database?"
    Then SQLBot should look for schema comments and descriptions
    And show any available table or column documentation
    And identify dbt model documentation if available
    And suggest where to find additional documentation

  Scenario: Performance exploration
    When I ask "Which tables are largest or slowest to query?"
    Then SQLBot should provide information about table sizes
    And identify potentially slow queries or large tables
    And suggest optimization strategies
    And recommend indexing or partitioning approaches

  Scenario: Historical data analysis
    When I ask "How far back does the historical data go?"
    Then SQLBot should identify date ranges across tables
    And show data availability timelines
    And highlight any gaps in historical data
    And suggest strategies for historical analysis

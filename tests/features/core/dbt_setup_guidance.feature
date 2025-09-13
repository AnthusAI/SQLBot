Feature: dbt Setup Guidance
  As a new SQLBot user
  I want clear guidance when dbt is not properly configured
  So that I can quickly set up my database connection

  Background:
    Given I have SQLBot installed
    And I have a valid OpenAI API key

  Scenario: Missing dbt profile shows helpful setup message
    Given I do not have a dbt profile configured
    When I ask a natural language question that requires database access
    Then SQLBot should detect the missing dbt profile
    And show me a clear setup message with next steps
    And provide links to documentation
    And suggest the specific profile name I need to create
    And not show cryptic dbt error messages to the user

  Scenario: Invalid dbt profile shows helpful guidance
    Given I have a dbt profile with incorrect connection details
    When I ask a natural language question that requires database access
    Then SQLBot should detect the connection failure
    And show me troubleshooting steps for database connection
    And suggest running "dbt debug" to test the connection
    And provide guidance on common connection issues

  Scenario: Working dbt profile allows normal operation
    Given I have a properly configured dbt profile
    And my database connection is working
    When I ask a natural language question that requires database access
    Then SQLBot should execute the query successfully
    And return formatted results
    And not show any setup messages

  Scenario: Custom profile name via --profile argument
    Given I have a dbt profile named "mycompany"
    And the "mycompany" profile has valid database connection details
    When I run SQLBot with "--profile mycompany" and ask a database question
    Then SQLBot should use the "mycompany" profile for database connection
    And execute the query successfully
    And not show profile not found errors

  Scenario: Invalid profile name shows helpful error
    Given I have a dbt profile named "sqlbot"
    But I do not have a dbt profile named "nonexistent"
    When I run SQLBot with "--profile nonexistent" and ask a database question
    Then SQLBot should show a profile not found error
    And suggest creating a profile named "nonexistent"
    And provide setup instructions for the "nonexistent" profile

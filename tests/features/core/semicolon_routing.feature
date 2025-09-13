Feature: Semicolon Query Routing
  As a user of SQLBot
  I want queries ending with semicolon to be executed directly as SQL
  So that I can bypass the LLM for direct database operations

  Background:
    Given SQLBot is running
    And the database is available
    And safeguards are enabled by default

  Scenario: Direct SQL query with semicolon bypasses LLM
    Given I am in the SQLBot interface
    When I enter "DELETE FROM film;"
    Then the query should be routed to direct SQL execution
    And I should see "✖ Query disallowed due to dangerous operations: DELETE"
    And I should NOT see any LLM response
    And I should NOT see "[Structured Response]"

  Scenario: Safe SQL query with semicolon shows safeguard message
    Given I am in the SQLBot interface  
    When I enter "SELECT COUNT(*) FROM film;"
    Then the query should be routed to direct SQL execution
    And I should see "✔ Query passes safeguard against dangerous operations."
    And I should see query results
    And I should NOT see any LLM response
    And I should NOT see "[Structured Response]"

  Scenario: Query without semicolon goes to LLM
    Given I am in the SQLBot interface
    When I enter "How many films are there"
    Then the query should be routed to the LLM
    And I should see an LLM response
    And I should NOT see safeguard messages

  Scenario: Mixed semicolon queries are handled correctly
    Given I am in the SQLBot interface
    When I enter "SELECT * FROM film LIMIT 5;"
    Then the query should be routed to direct SQL execution
    And I should see "✔ Query passes safeguard against dangerous operations."
    And I should see query results
    When I enter "What does this data show"
    Then the query should be routed to the LLM
    And I should see an LLM response

  Scenario: Semicolon with dangerous operations blocked consistently
    Given I am in the SQLBot interface
    When I enter "DROP TABLE film;"
    Then the query should be routed to direct SQL execution
    And I should see "✖ Query disallowed due to dangerous operations: DROP"
    And I should NOT see any LLM response
    And I should NOT see "[Structured Response]"

  Scenario: Semicolon queries work in CLI mode
    When I run SQLBot with query "SELECT 42 AS test;" and flag "--no-repl"
    Then the query should be executed directly
    And I should see "✔ Query passes safeguard against dangerous operations."
    And I should NOT see any LLM response

  Scenario: Semicolon queries work in Textual mode
    Given I start SQLBot in Textual mode
    When I enter "SELECT COUNT(*) FROM film;"
    Then the query should be routed to direct SQL execution
    And I should see "✔ Query passes safeguard against dangerous operations."
    And I should NOT see any LLM response
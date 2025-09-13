Feature: Safeguard Feature
  As a user of SQLBot
  I want safeguard protection by default
  So that I can prevent accidental data modifications and ensure safe query execution

  Background:
    Given SQLBot is running in interactive mode
    And the database is available
    And safeguards are enabled by default

  Scenario: Check default safeguard status
    Given I am in the SQLBot REPL
    When I enter "/safeguard"
    Then I should see "Safeguard mode: ON"
    And I should see "All queries will be checked for dangerous operations"

  Scenario: Disable safeguard mode
    Given I am in the SQLBot REPL
    When I enter "/safeguard off"
    Then I should see "Safeguard mode DISABLED"
    And I should see "Queries will execute without safety checks"

  Scenario: Re-enable safeguard mode
    Given I am in the SQLBot REPL
    And safeguard mode is disabled
    When I enter "/safeguard on"
    Then I should see "Safeguard mode ENABLED"
    And I should see "All queries will be checked for dangerous operations"

  Scenario: Block dangerous INSERT operation by default
    Given I am in the SQLBot REPL
    When I try to execute "INSERT INTO test_table VALUES (1, 'test')"
    Then I should see "Query blocked by safeguard!"
    And I should see "✖ Query disallowed due to dangerous operations: INSERT"
    And I should be prompted for override confirmation

  Scenario: Block dangerous DELETE operation by default
    Given I am in the SQLBot REPL
    When I try to execute "DELETE FROM test_table WHERE id = 1"
    Then I should see "Query blocked by safeguard!"
    And I should see "✖ Query disallowed due to dangerous operations: DELETE"
    And I should be prompted for override confirmation

  Scenario: Block dangerous UPDATE operation by default
    Given I am in the SQLBot REPL
    When I try to execute "UPDATE test_table SET name = 'new' WHERE id = 1"
    Then I should see "Query blocked by safeguard!"
    And I should see "✖ Query disallowed due to dangerous operations: UPDATE"
    And I should be prompted for override confirmation

  Scenario: Block dangerous DROP operation by default
    Given I am in the SQLBot REPL
    When I try to execute "DROP TABLE test_table"
    Then I should see "Query blocked by safeguard!"
    And I should see "✖ Query disallowed due to dangerous operations: DROP"
    And I should be prompted for override confirmation

  Scenario: Allow safe SELECT operation with safeguard message
    Given I am in the SQLBot REPL
    When I execute "SELECT TOP 5 * FROM test_table"
    Then the query should execute normally
    And I should see "✔ Query passes safeguard against dangerous operations."
    And I should see query results

  Scenario: Detect multiple dangerous operations by default
    Given I am in the SQLBot REPL
    When I try to execute "INSERT INTO temp AS SELECT * FROM source; DELETE FROM old_table"
    Then I should see "Query blocked by safeguard!"
    And I should see dangerous operations detected
    And I should be prompted for override confirmation

  Scenario: Admin override allows dangerous operation
    Given I am in the SQLBot REPL
    When I try to execute "DELETE FROM test_table WHERE id = 999"
    And I respond "yes" to the override prompt
    Then I should see "Safety override granted. Executing query..."
    And the dangerous query should execute

  Scenario: Admin override cancelled
    Given I am in the SQLBot REPL
    When I try to execute "DROP TABLE temp_table"
    And I respond "no" to the override prompt
    Then I should see "Query execution cancelled for safety"
    And the dangerous query should not execute

  Scenario: Override prompt cancelled with Ctrl+C
    Given I am in the SQLBot REPL
    When I try to execute "TRUNCATE TABLE log_table"
    And I press Ctrl+C at the override prompt
    Then I should see "Query execution cancelled for safety"
    And the dangerous query should not execute

  Scenario: Complex query with comments and formatting
    Given I am in the SQLBot REPL
    When I try to execute a query with comments containing "DELETE"
    """
    /* This query mentions DELETE in comments but doesn't actually delete */
    -- DELETE is mentioned here too
    SELECT COUNT(*) FROM table -- Not dangerous
    """
    Then the query should execute normally
    And I should see "✔ Query passes safeguard against dangerous operations."

  Scenario: Query with dangerous operation in string literals
    Given I am in the SQLBot REPL
    When I execute "SELECT 'DELETE operation' as description FROM test_table"
    Then the query should execute normally
    And I should see "✔ Query passes safeguard against dangerous operations."

  Scenario: Safeguard mode disabled allows all operations
    Given I am in the SQLBot REPL
    And safeguard mode is disabled
    When I execute "DELETE FROM test_table WHERE id = 1"
    Then the query should execute without safety checks
    And I should not see any safeguard messages

  Scenario: Dangerous CLI flag disables safeguards
    Given SQLBot is started with the --dangerous flag
    When I execute "DELETE FROM test_table WHERE id = 1"
    Then the query should execute without safety checks
    And I should not see any safeguard messages

  Scenario: Preview mode respects safeguard
    Given I am in the SQLBot REPL
    When I enter "/preview"
    And I enter "DELETE FROM test_table WHERE id = 1"
    And I respond "y" to execute the query
    Then I should see "Query blocked by safeguard!"
    And I should be prompted for override confirmation

  Scenario: Invalid safeguard command option
    Given I am in the SQLBot REPL
    When I enter "/safeguard invalid"
    Then I should see "Unknown safeguard option: invalid"
    And I should see "Usage: /safeguard [on|off]"
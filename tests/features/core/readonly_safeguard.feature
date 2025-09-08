Feature: Read-Only Safeguard Feature
  As a user of QBot
  I want read-only safeguard protection
  So that I can prevent accidental data modifications and ensure safe query execution

  Background:
    Given QBot is running in interactive mode
    And the database is available

  Scenario: Enable read-only safeguard mode
    Given I am in the QBot REPL
    When I enter "//readonly on"
    Then I should see "Read-only safeguard mode ENABLED"
    And I should see "All queries will be checked for dangerous operations"

  Scenario: Disable read-only safeguard mode
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I enter "//readonly off"
    Then I should see "Read-only safeguard mode DISABLED"
    And I should see "Queries will execute without safety checks"

  Scenario: Check read-only safeguard status
    Given I am in the QBot REPL
    When I enter "//readonly"
    Then I should see the current safeguard status
    And I should see usage instructions

  Scenario: Block dangerous INSERT operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "INSERT INTO test_table VALUES (1, 'test')"
    Then I should see "Query blocked by read-only safeguard!"
    And I should see "Dangerous operations detected: INSERT"
    And I should be prompted for override confirmation

  Scenario: Block dangerous DELETE operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "DELETE FROM test_table WHERE id = 1"
    Then I should see "Query blocked by read-only safeguard!"
    And I should see "Dangerous operations detected: DELETE"
    And I should be prompted for override confirmation

  Scenario: Block dangerous UPDATE operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "UPDATE test_table SET name = 'new' WHERE id = 1"
    Then I should see "Query blocked by read-only safeguard!"
    And I should see "Dangerous operations detected: UPDATE"
    And I should be prompted for override confirmation

  Scenario: Block dangerous DROP operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "DROP TABLE test_table"
    Then I should see "Query blocked by read-only safeguard!"
    And I should see "Dangerous operations detected: DROP"
    And I should be prompted for override confirmation

  Scenario: Allow safe SELECT operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I execute "SELECT TOP 5 * FROM test_table"
    Then the query should execute normally
    And I should see query results
    And I should not see any safety warnings

  Scenario: Detect multiple dangerous operations
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "INSERT INTO temp AS SELECT * FROM source; DELETE FROM old_table"
    Then I should see "Query blocked by read-only safeguard!"
    And I should see dangerous operations detected
    And I should be prompted for override confirmation

  Scenario: Admin override allows dangerous operation
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "DELETE FROM test_table WHERE id = 999"
    And I respond "yes" to the override prompt
    Then I should see "Safety override granted. Executing query..."
    And the dangerous query should execute

  Scenario: Admin override cancelled
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "DROP TABLE temp_table"
    And I respond "no" to the override prompt
    Then I should see "Query execution cancelled for safety"
    And the dangerous query should not execute

  Scenario: Override prompt cancelled with Ctrl+C
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute "TRUNCATE TABLE log_table"
    And I press Ctrl+C at the override prompt
    Then I should see "Query execution cancelled for safety"
    And the dangerous query should not execute

  Scenario: Complex query with comments and formatting
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I try to execute a query with comments containing "DELETE"
    """
    /* This query mentions DELETE in comments but doesn't actually delete */
    -- DELETE is mentioned here too
    SELECT COUNT(*) FROM table -- Not dangerous
    """
    Then the query should execute normally
    And I should not see any safety warnings

  Scenario: Query with dangerous operation in string literals
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I execute "SELECT 'DELETE operation' as description FROM test_table"
    Then the query should execute normally
    And I should not see any safety warnings

  Scenario: Read-only mode disabled allows all operations
    Given I am in the QBot REPL
    And read-only mode is disabled
    When I execute "DELETE FROM test_table WHERE id = 1"
    Then the query should execute without safety checks
    And I should not see any safety warnings

  Scenario: Preview mode respects read-only safeguard
    Given I am in the QBot REPL
    And read-only mode is enabled
    When I enter "//preview"
    And I enter "DELETE FROM test_table WHERE id = 1"
    And I respond "y" to execute the query
    Then I should see "Query blocked by read-only safeguard!"
    And I should be prompted for override confirmation

  Scenario: Invalid readonly command option
    Given I am in the QBot REPL
    When I enter "//readonly invalid"
    Then I should see "Unknown readonly option: invalid"
    And I should see "Usage: //readonly [on|off]"
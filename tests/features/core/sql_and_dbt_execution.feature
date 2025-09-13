Feature: SQL and dbt Query Execution
  As a developer or advanced analyst
  I want to execute SQL and dbt queries directly
  So that I have precise control over database operations

  Background:
    Given SQLBot is running
    And I have database connectivity
    And dbt is properly configured

  Scenario: Execute basic SQL query
    When I execute "SELECT COUNT(*) FROM sys.tables;"
    Then the query should run successfully
    And I should see a numeric result
    And the result should be formatted in a clear table
    And execution time should be displayed

  Scenario: Execute SQL with multiple columns
    When I execute "SELECT name, type FROM sys.tables LIMIT 5;"
    Then the query should return multiple columns
    And results should be formatted in a proper table
    And column headers should be clearly displayed
    And I should see exactly 5 rows

  Scenario: Execute dbt source query
    When I execute "SELECT TOP 10 * FROM {{ source('your_source', 'your_main_table') }};"
    Then dbt should compile the source reference
    And the compiled SQL should execute successfully
    And I should see 10 rows of report data
    And column names should match the source table

  Scenario: Execute dbt macro
    When I execute "SELECT {{ find_report_by_id(283195544) }};"
    Then dbt should compile the macro with the parameter
    And execute the resulting SQL
    And return specific report data for that ID
    And show both the compiled SQL and results

  Scenario: Handle SQL syntax errors gracefully
    When I execute "SELCT * FRM invalid_table;"
    Then SQLBot should detect the syntax error
    And display a clear error message about the syntax issue
    And suggest the correct syntax
    And not crash or hang

  Scenario: Handle missing table errors
    When I execute "SELECT * FROM nonexistent_table;"
    Then SQLBot should detect the table doesn't exist
    And display a helpful error message
    And suggest checking available tables
    And offer to show table list

  Scenario: Handle permission errors
    When I execute "DROP TABLE important_table;"
    Then SQLBot should handle any permission errors gracefully
    And display appropriate security messages
    And not expose sensitive system information
    And maintain system stability

  Scenario: Query timeout handling
    Given I have a query that would take a very long time
    When I execute a complex query that exceeds timeout limits
    Then SQLBot should timeout gracefully after a reasonable period
    And inform me about the timeout
    And suggest query optimization strategies
    And allow me to cancel or modify the query

  Scenario: Large result set handling
    When I execute a query that returns thousands of rows
    Then SQLBot should handle the large result set efficiently
    And paginate or limit the display appropriately
    And show result count information
    And offer options to export or save results

  Scenario: Multiple query execution
    When I execute multiple queries separated by semicolons
    Then SQLBot should execute each query in sequence
    And display results for each query separately
    And handle any errors in individual queries
    And continue with remaining queries if possible

  Scenario: Query with parameters
    When I execute a parameterized query with user input
    Then SQLBot should safely handle the parameters
    And prevent SQL injection attempts
    And execute the query with proper parameter binding
    And return expected results

  Scenario: Database connection recovery
    Given the database connection is temporarily lost
    When I try to execute a query
    Then SQLBot should detect the connection issue
    And attempt to reconnect automatically
    And inform me about the connection status
    And retry the query once reconnected

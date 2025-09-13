Feature: Local .dbt folder support
  As a SQLBot user
  I want SQLBot to detect and use a local .dbt folder when it exists
  So that I can have project-specific dbt configurations

  Background:
    Given I have SQLBot installed
    And I have a valid OpenAI API key

  Scenario: SQLBot detects local .dbt folder
    Given I have a local .dbt folder with profiles.yml
    When I start SQLBot
    Then I should see "Local .dbt/profiles.yml (detected)" in the banner
    And SQLBot should use the local dbt configuration

  Scenario: SQLBot falls back to global .dbt folder
    Given I do not have a local .dbt folder
    And I have a global ~/.dbt/profiles.yml
    When I start SQLBot
    Then I should see "Global ~/.dbt/profiles.yml" in the banner
    And SQLBot should use the global dbt configuration

  Scenario: Local .dbt folder takes priority over global
    Given I have a local .dbt folder with profiles.yml
    And I have a global ~/.dbt/profiles.yml
    When I start SQLBot
    Then I should see "Local .dbt/profiles.yml (detected)" in the banner
    And SQLBot should use the local dbt configuration
    And SQLBot should not use the global dbt configuration

  Scenario: Profile detection works with different profile names
    Given I have a local .dbt folder with profiles.yml containing profile "TestProfile"
    When I start SQLBot with profile "TestProfile"
    Then I should see "Local .dbt/profiles.yml (detected)" in the banner
    And I should see "Profile: TestProfile" in the banner
    And SQLBot should use the TestProfile from local configuration

  Scenario: Local dbt folder enables SQL queries
    Given I have a local .dbt folder with Sakila profile configured
    When I execute SQL query "SELECT 1;"
    Then the query should succeed
    And I should see the result "1"
    And the banner should show local .dbt configuration

  Scenario: Environment variable DBT_PROFILES_DIR is set correctly
    Given I have a local .dbt folder with profiles.yml
    When I start SQLBot
    Then the DBT_PROFILES_DIR environment variable should point to the local .dbt folder
    And dbt commands should work with the local configuration
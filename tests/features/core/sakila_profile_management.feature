Feature: Sakila profile management
  As a SQLBot user
  I want the Sakila setup script to properly manage local dbt profiles
  So that I can have project-specific Sakila configurations

  Background:
    Given I have SQLBot installed
    And I have the Sakila setup script available

  Scenario: Setup creates local dbt profile when none exists
    Given I do not have a local .dbt folder
    When I run the Sakila setup script
    Then a local .dbt folder should be created
    And the local profiles.yml should contain the Sakila profile
    And the Sakila profile should point to the correct database file

  Scenario: Setup merges Sakila profile with existing profiles
    Given I have a local .dbt folder with existing profiles
    When I run the Sakila setup script
    Then the existing profiles should be preserved
    And the Sakila profile should be added to the existing profiles
    And the local profiles.yml should contain both old and new profiles

  Scenario: Setup updates existing Sakila profile
    Given I have a local .dbt folder with an existing Sakila profile
    When I run the Sakila setup script
    Then the existing Sakila profile should be updated
    And other profiles should remain unchanged
    And the updated Sakila profile should point to the correct database file

  Scenario: Setup can be run with --no-local-profile flag
    Given I do not have a local .dbt folder
    When I run the Sakila setup script with --no-local-profile
    Then no local .dbt folder should be created
    And the setup should complete successfully
    And the output should indicate local profile creation was skipped

  Scenario: Setup handles invalid existing profiles gracefully
    Given I have a local .dbt folder with a corrupted profiles.yml
    When I run the Sakila setup script
    Then the setup should warn about the corrupted file
    And a new profiles.yml should be created with only the Sakila profile
    And the setup should complete successfully

  Scenario: Profile verification detects missing database file
    Given I have a local .dbt folder with a Sakila profile
    And the database file referenced in the profile does not exist
    When I check the local dbt profile
    Then the verification should fail
    And the error message should indicate the missing database file

  Scenario: Profile verification succeeds with valid configuration
    Given I have a local .dbt folder with a valid Sakila profile
    And the database file referenced in the profile exists
    When I check the local dbt profile
    Then the verification should succeed
    And the verification message should show the database path
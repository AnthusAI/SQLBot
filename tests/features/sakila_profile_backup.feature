Feature: Sakila Profile Backup Safety
  As a SQLBot user
  I want my existing dbt profiles.yml file to be backed up before any changes
  So that I can recover my configuration if something goes wrong

  Background:
    Given I have a clean test environment
    And I have SQLite installed and available

  Scenario: Backup is created when updating existing profiles file
    Given I have an existing .dbt directory
    And I have an existing profiles.yml with other profiles
    When I run the Sakila profile setup
    Then a timestamped backup of profiles.yml should be created
    And the backup should contain my original profile data
    And the new profiles.yml should contain both old and new profiles

  Scenario: Backup preserves original file permissions and timestamps
    Given I have an existing .dbt directory
    And I have an existing profiles.yml with specific permissions
    When I run the Sakila profile setup
    Then a backup should be created with the same content
    And the backup should preserve the original file metadata

  Scenario: No backup is created for new profiles file
    Given I have no existing .dbt directory
    When I run the Sakila profile setup
    Then no backup file should be created
    And a new profiles.yml should be created with Sakila profile

  Scenario: Profile setup continues even if backup fails
    Given I have an existing profiles.yml file
    And the backup operation will fail due to permissions
    When I run the Sakila profile setup
    Then a warning about backup failure should be shown
    But the profile setup should complete successfully
    And the Sakila profile should be added to profiles.yml

  Scenario: Multiple backups create unique filenames
    Given I have an existing profiles.yml file
    When I run the Sakila profile setup multiple times
    Then multiple backup files should be created
    And each backup file should have a unique timestamp
    And no backup files should be overwritten

  Scenario: Backup filename format is correct
    Given I have an existing profiles.yml file
    When I run the Sakila profile setup
    Then the backup filename should follow the pattern "profiles.backup.YYYYMMDD_HHMMSS.yml"
    And the backup should be in the same directory as the original file
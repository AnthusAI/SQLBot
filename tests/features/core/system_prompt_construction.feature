Feature: System Prompt Construction
  As a SQLBot user
  I want the system prompt to always include the base template with optional profile-specific additions
  So that I can customize the AI behavior per profile while maintaining core functionality

  Background:
    Given SQLBot is configured with LLM integration

  Scenario: Base system prompt without profile-specific addition
    Given I am using a profile with no custom system prompt file
    When the system prompt is built
    Then the system prompt should contain the hardcoded base template
    And the system prompt should include schema information placeholders
    And the system prompt should include macro information placeholders
    And the system prompt should not contain any profile-specific additions

  Scenario: Base system prompt with profile-specific addition
    Given I am using a profile with a custom system prompt file
    When the system prompt is built
    Then the system prompt should contain the hardcoded base template
    And the system prompt should include schema information placeholders
    And the system prompt should include macro information placeholders
    And the system prompt should contain the profile-specific addition
    And the profile addition should be appended after the base template

  Scenario: System prompt construction with schema and macro rendering
    Given I am using a profile with schema and macro information
    When the system prompt is built and rendered
    Then the schema placeholders should be replaced with actual schema information
    And the macro placeholders should be replaced with actual macro information
    And the rendered prompt should be valid for LLM consumption

  Scenario: System prompt construction error handling
    Given I am using a profile with an invalid system prompt file
    When the system prompt is built
    Then the system should fall back to the base template
    And a warning should be logged about the invalid file
    And the system prompt should still be functional

  Scenario: Profile-specific system prompt file discovery
    Given I have system prompt files in multiple locations
    When the system searches for profile-specific additions
    Then it should check ".sqlbot/profiles/{profile}/system_prompt.txt" first
    And it should check "profiles/{profile}/system_prompt.txt" second
    And it should use the first file found
    And it should return empty string if no files are found

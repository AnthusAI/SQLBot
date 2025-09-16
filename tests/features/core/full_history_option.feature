Feature: Full History Option
  As a SQLBot developer or advanced user
  I want a --full-history option that shows complete conversation history without truncation
  So that I can debug system prompts and see full LLM interactions

  Background:
    Given SQLBot is configured with LLM integration

  Scenario: --full-history enables history display
    Given I start SQLBot with the --full-history flag
    When I execute a natural language query
    Then conversation history should be displayed
    And the history should not be truncated

  Scenario: --full-history shows complete system prompt
    Given I start SQLBot with the --full-history flag
    When I execute a natural language query
    Then the system prompt should be displayed in full
    And the system prompt should not contain truncation markers
    And the system prompt should include complete schema information
    And the system prompt should include complete macro information

  Scenario: --full-history shows complete message content
    Given I start SQLBot with the --full-history flag
    And I have a conversation with long messages
    When I execute another natural language query
    Then all previous messages should be displayed in full
    And no message content should be truncated
    And no truncation indicators should be present

  Scenario: --full-history vs regular --history truncation behavior
    Given I have a conversation with very long tool results
    When I use the regular --history flag
    Then tool results should be truncated after 20 lines or 2000 characters
    And truncation indicators should show omitted content
    When I use the --full-history flag instead
    Then the same tool results should be displayed in full
    And no truncation should occur

  Scenario: --full-history works in CLI mode
    Given I start SQLBot with --text and --full-history flags
    When I execute a natural language query with a long result
    Then the complete conversation history should be displayed
    And all content should be shown without truncation
    And the output should be formatted for text mode

  Scenario: --full-history works in interactive REPL mode
    Given I start SQLBot with --full-history flag in interactive mode
    When I execute multiple queries with long responses
    Then each query should show the complete conversation history
    And all historical content should remain untruncated
    And the display should be suitable for interactive use

  Scenario: --full-history error handling
    Given I start SQLBot with the --full-history flag
    When an error occurs during query execution
    Then the error should be displayed in full
    And the conversation history should still be shown completely
    And the system should remain functional for subsequent queries

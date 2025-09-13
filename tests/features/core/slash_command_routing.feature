Feature: Slash Command Routing
  As a user of SQLBot
  I want slash commands to be handled as system commands
  So that they are not sent to the LLM and result in proper system responses

  Background:
    Given SQLBot is running
    And the database is available

  Scenario: /dangerous command is handled as system command
    Given I am in the SQLBot interface
    When I enter "/dangerous"
    Then the command should be routed to system handler
    And I should see dangerous mode status
    And I should NOT see any LLM response
    And I should NOT see "[Structured Response]"

  Scenario: /dangerous on enables dangerous mode
    Given I am in the SQLBot interface
    When I enter "/dangerous on"
    Then I should see "Dangerous mode ENABLED"
    And I should see "Safeguards are DISABLED - all operations allowed"
    And I should NOT see any LLM response

  Scenario: /dangerous off disables dangerous mode
    Given I am in the SQLBot interface
    And dangerous mode is enabled
    When I enter "/dangerous off"
    Then I should see "Dangerous mode DISABLED"
    And I should see "Safeguards are ENABLED - dangerous operations blocked"
    And I should NOT see any LLM response

  Scenario: /help command is handled as system command
    Given I am in the SQLBot interface
    When I enter "/help"
    Then the command should be routed to system handler
    And I should see the help table
    And I should NOT see any LLM response

  Scenario: /tables command is handled as system command
    Given I am in the SQLBot interface
    When I enter "/tables"
    Then the command should be routed to system handler
    And I should see database tables list
    And I should NOT see any LLM response

  Scenario: Unknown slash command shows system error
    Given I am in the SQLBot interface
    When I enter "/unknown"
    Then the command should be routed to system handler
    And I should see "Unknown command: /unknown"
    And I should see "Type /help for available commands"
    And I should NOT see any LLM response

  Scenario: Slash commands work consistently across interfaces
    When I run SQLBot with query "/dangerous" and flag "--no-repl"
    Then I should see dangerous mode status in CLI output
    And I should NOT see any LLM response

  Scenario: Slash command detection is case sensitive
    Given I am in the SQLBot interface
    When I enter "/DANGEROUS"
    Then the command should be routed to system handler
    And I should NOT see any LLM response

  Scenario: Slash commands with extra spaces are handled
    Given I am in the SQLBot interface
    When I enter "/dangerous "
    Then the command should be routed to system handler
    And I should see dangerous mode status
    And I should NOT see any LLM response
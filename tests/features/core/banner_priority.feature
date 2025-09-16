Feature: Banner Display Priority
  As a user of SQLBot
  I want to see the banner as the very first output
  So that I have clear identification of the application before any other messages

  Background:
    Given SQLBot is available
    And dbt is configured with profile "Sakila"

  Scenario: No banner in --no-repl mode
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--no-repl"
    Then I should NOT see any banner
    And the output should be minimal

  Scenario: Banner appears first in interactive mode  
    When I start SQLBot in interactive mode
    Then the banner should be the first output
    And I should see the "Ready for questions." banner
    And initialization messages should appear after the banner

  Scenario: Banner appears first with preview mode
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--preview"
    Then the banner should be the first output
    And initialization messages should appear after the banner

  Scenario: Banner appears first with dangerous mode
    When I run SQLBot with query "SELECT 42 AS Answer;" and flag "--dangerous"  
    Then the banner should be the first output
    And initialization messages should appear after the banner

  Scenario: No banner with --no-repl in combined flags
    When I run SQLBot with query "SELECT 42 AS Answer;" and flags "--no-repl --preview --dangerous"
    Then I should NOT see any banner
    And the output should be minimal
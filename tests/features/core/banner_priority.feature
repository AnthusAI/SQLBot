Feature: Banner Display Priority
  As a user of QBot
  I want to see the banner as the very first output
  So that I have clear identification of the application before any other messages

  Background:
    Given QBot is available
    And dbt is configured with profile "Sakila"

  Scenario: Banner appears first in CLI mode
    When I run QBot with query "SELECT 42 AS Answer;" and flag "--no-repl"
    Then the banner should be the first output
    And I should see the "QBot CLI" banner
    And initialization messages should appear after the banner

  Scenario: Banner appears first in interactive mode  
    When I start QBot in interactive mode
    Then the banner should be the first output
    And I should see the "Ready for questions." banner
    And initialization messages should appear after the banner

  Scenario: Banner appears first with preview mode
    When I run QBot with query "SELECT 42 AS Answer;" and flag "--preview"
    Then the banner should be the first output
    And initialization messages should appear after the banner

  Scenario: Banner appears first with read-only mode
    When I run QBot with query "SELECT 42 AS Answer;" and flag "--read-only"  
    Then the banner should be the first output
    And initialization messages should appear after the banner

  Scenario: Banner appears first with combined flags
    When I run QBot with query "SELECT 42 AS Answer;" and flags "--no-repl --preview --read-only"
    Then the banner should be the first output
    And I should see the "QBot CLI" banner
    And initialization messages should appear after the banner
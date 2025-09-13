Feature: Conversation History with Tool Calls
  As a user of SQLBot
  I want the conversation history to include tool calls and results
  So that I can see the complete context sent to the LLM and understand follow-up queries

  Background:
    Given SQLBot is configured with the Sakila profile
    And the --history flag is enabled
    And LLM integration is available

  Scenario: Tool calls and results are captured in conversation history
    Given I start a new conversation
    When I ask "What are the top 2 customers by rentals?"
    Then the LLM should execute database queries
    And the conversation history should contain the user question
    And the conversation history should contain tool calls with SQL queries
    And the conversation history should contain tool results with query outcomes
    And the conversation history should contain the final LLM response

  Scenario: Conversation history persists between queries with tool context
    Given I start a new conversation
    When I ask "What are the top 2 customers by rentals?"
    And the LLM executes queries and provides results
    When I ask a follow-up question "Now show me their total payments"
    Then the conversation history panel should show:
      | Message Type | Content Contains |
      | SYSTEM       | database schema and instructions |
      | HUMAN        | What are the top 2 customers by rentals? |
      | ASSISTANT    | 🔧 TOOL CALL: execute_dbt_query |
      | ASSISTANT    | 📊 TOOL RESULT |
      | ASSISTANT    | final response about top customers |
      | HUMAN        | Now show me their total payments |
    And the LLM should understand the context from the previous query

  Scenario: Tool call errors are preserved in conversation history
    Given I start a new conversation
    When I ask "What are the top 2 customers by rentals?"
    And the first SQL query fails with a syntax error
    And the LLM retries with a corrected query that succeeds
    Then the conversation history should contain both the failed and successful tool calls
    And the conversation history should show the error message from the first attempt
    And the conversation history should show the successful result from the second attempt

  Scenario: Conversation history display shows complete LLM context
    Given I have an ongoing conversation with multiple queries and tool calls
    When the --history flag is enabled
    And I ask a new question
    Then the conversation history panel should appear before the "..." thinking indicator
    And the panel should show the system message with database schema
    And the panel should show all previous user questions
    And the panel should show all previous tool calls with proper formatting
    And the panel should show all previous tool results
    And the panel should show all previous LLM responses
    And the panel should show the current user question

  Scenario: Interactive REPL maintains conversation history across queries
    Given I start an interactive REPL session with --history enabled
    When I enter "What are the top 2 customers by rentals?"
    And I wait for the response with tool calls
    When I enter "Now rank them by total spend instead"
    Then the second query's conversation history panel should include the first question about top customers
    And the conversation history should include all tool calls from the first query
    And the conversation history should include all tool results from the first query  
    And the conversation history should include the first LLM response
    And the conversation history should include the second question about ranking by spend
    And the LLM should provide a contextually appropriate response

  Scenario: CLI mode preserves conversation history between separate query executions
    Given I use CLI mode with --history flag
    When I execute a query that involves tool calls
    And I execute a follow-up query in the same session
    Then the second query should see the complete conversation history from the first query
    And the conversation history should include all tool interactions from both queries

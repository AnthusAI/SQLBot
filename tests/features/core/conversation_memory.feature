Feature: Conversation Memory Management
  As a user of QBot
  I want the system to properly manage conversation history
  So that the LLM can maintain context across multiple queries

  Background:
    Given QBot is properly configured
    And the conversation memory system is initialized

  Scenario: Basic conversation history tracking
    Given I start a new conversation
    When I ask "How many tables are there?"
    And the LLM responds with query results
    Then the conversation history should contain 1 user message
    And the conversation history should contain 1 assistant message
    And the conversation history should preserve the original content

  Scenario: Tool results are extracted and stored separately
    Given I start a new conversation
    When I ask "Show me the tables"
    And the LLM responds with "Here are the tables:\n\n--- Query Details ---\nQuery: SELECT name FROM tables\nResult: table1, table2"
    Then the conversation history should contain 1 user message
    And the conversation history should contain 1 assistant message
    And the conversation history should contain 1 tool result message
    And the tool result should contain the executed query
    And the tool result should contain the query result

  Scenario: Multiple tool results in single response
    Given I start a new conversation
    When the LLM responds with multiple queries in one response
    Then each query and result should be stored as separate tool messages
    And the main response should be stored as an assistant message
    And all tool messages should have unique tool call IDs

  Scenario: Conversation history filtering and truncation
    Given I have a conversation with 25 messages
    When I request the filtered conversation context
    Then the context should contain at most 20 messages
    And the most recent messages should be preserved
    And overly long messages should be truncated

  Scenario: Message content truncation
    Given I start a new conversation
    When I add a message with content longer than 2000 characters
    Then the message content should be truncated
    And a truncation notice should be added
    And the message should still be functional

  Scenario: Conversation context for LLM agent
    Given I have an ongoing conversation with 5 messages
    When I request the conversation context for the LLM
    Then the context should be in LangChain message format
    And user messages should be HumanMessage objects
    And assistant messages should be AIMessage objects
    And tool results should be ToolMessage objects

  Scenario: Memory manager integration with LLM queries
    Given I have a conversation history with previous queries
    When I ask a follow-up question
    Then the LLM should receive the full conversation context
    And the context should include previous tool results
    And the context should be displayed as a Rich tree for debugging

  Scenario: Conversation history persistence across queries
    Given I ask "How many users are there?" and get a response
    When I ask "What about active users?"
    Then the second query should have access to the first query's context
    And the LLM should see both the question and the previous result
    And the conversation should build incrementally

  Scenario: Error handling in conversation memory
    Given I start a new conversation
    When an invalid message is added to the history
    Then the memory system should handle it gracefully
    And not corrupt the existing conversation history
    And log appropriate error information

  Scenario: Conversation history clearing
    Given I have a conversation with multiple messages
    When I clear the conversation history
    Then the history should be empty
    And subsequent queries should start fresh
    And no previous context should be available

  Scenario: Rich tree visualization of conversation context
    Given I have a conversation with user, assistant, and tool messages
    When I display the conversation tree
    Then it should show all message types with proper styling
    And user messages should be marked with 👤
    And assistant messages should be marked with 🤖
    And tool results should be marked with 🔧
    And message content should be properly truncated for display

  Scenario: Filtered context excludes inappropriate messages
    Given I have a conversation with various message types
    And some messages are empty or overly long
    When I get the filtered conversation context
    Then empty messages should be excluded
    And overly long messages should be truncated or excluded
    And the filtering should be logged for debugging

  Scenario: Conversation history displays tool calls and results
    Given I start a new conversation
    When I ask "How many films are there?" 
    And the LLM makes a tool call to execute_dbt_query
    And the tool returns query results
    Then the conversation history display should show the tool call
    And the conversation history display should show the tool result
    And the tool call should include the query being executed
    And the tool result should show the cleaned output without dbt noise

  Scenario: Tool call display formatting in Rich panel
    Given I have a conversation with tool calls
    When the conversation history is displayed in a Rich panel
    Then tool calls should be clearly labeled as "TOOL CALL"
    And tool calls should show the tool name and parameters
    And tool results should be clearly labeled as "TOOL RESULT"
    And tool results should be truncated appropriately (more for tool results, less for other messages)
    And the display should use appropriate colors for different message types

  Scenario: Multiple tool calls in conversation history
    Given I ask a complex question requiring multiple database queries
    When the LLM makes multiple tool calls in sequence
    Then each tool call should be displayed separately in the conversation history
    And each tool result should be displayed separately
    And the tool calls should be numbered or clearly distinguished
    And the conversation flow should be easy to follow

  Scenario: Tool call truncation rules
    Given I have a conversation with tool calls that return large results
    When the conversation history is displayed
    Then tool results should only be truncated if they exceed 20 lines or 2000 characters
    And other message types should be truncated at 3 lines or 200 characters
    And truncation should show how much content was omitted
    And truncated content should still be meaningful for debugging

  Scenario: Tool call display timing
    Given I make a query that requires a tool call
    When the LLM is about to make the API call
    Then the conversation history should be displayed immediately before the LLM call
    And the display should show all previous tool calls and results
    And the current user query should be included in the display
    And the system prompt should be shown with appropriate truncation

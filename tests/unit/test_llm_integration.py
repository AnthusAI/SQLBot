"""Unit tests for LLM integration module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

class TestLLMIntegration:
    """Test cases for LLM integration functionality."""

    def test_get_llm_with_default_config(self, mock_env):
        """Test LLM creation with default configuration."""
        from sqlbot.llm_integration import get_llm
        
        with patch('sqlbot.llm_integration.ChatOpenAI') as mock_chat:
            llm = get_llm()
            
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args[1]
            assert call_args['model'] == 'gpt-5'  # From mock env
            # GPT-5 doesn't use temperature parameter (uses default=1)
            assert 'temperature' not in call_args
            assert call_args['max_tokens'] == 1000

    def test_get_llm_with_custom_config(self, mock_env):
        """Test LLM creation with custom configuration."""
        from sqlbot.llm_integration import get_llm
        
        with patch.dict(os.environ, {
            'QBOT_LLM_MODEL': 'gpt-5',
            'QBOT_LLM_MAX_TOKENS': '2000'
        }):
            with patch('sqlbot.llm_integration.ChatOpenAI') as mock_chat:
                llm = get_llm()
                
                call_args = mock_chat.call_args[1]
                assert call_args['model'] == 'gpt-5'
                # GPT-5 doesn't use temperature parameter (uses default=1)
                assert 'temperature' not in call_args
                assert call_args['max_tokens'] == 2000

    def test_gpt5_parameter_validation(self, mock_env):
        """Test that GPT-5 doesn't receive temperature parameter."""
        from sqlbot.llm_integration import get_llm
        
        # Even if temperature is set in environment, GPT-5 shouldn't get it
        with patch.dict(os.environ, {
            'QBOT_LLM_MODEL': 'gpt-5',
            'QBOT_LLM_MAX_TOKENS': '1500'
        }):
            with patch('sqlbot.llm_integration.ChatOpenAI') as mock_chat:
                llm = get_llm()
                
                call_args = mock_chat.call_args[1]
                assert call_args['model'] == 'gpt-5'
                # Critical: GPT-5 should never receive temperature parameter
                assert 'temperature' not in call_args
                assert call_args['max_tokens'] == 1500
                # Verify standard GPT-5 parameters are present
                assert call_args['streaming'] == False
                assert call_args['disable_streaming'] == True

    def test_dynamic_model_messaging(self, mock_env):
        """Test that model messages show the actual model being used."""
        from sqlbot.llm_integration import handle_llm_query
        
        with patch('sqlbot.llm_integration.create_llm_agent') as mock_agent:
            with patch('sqlbot.llm_integration.check_dbt_setup', return_value=(True, "OK")):
                # Mock the agent to avoid actual LLM calls
                mock_executor = Mock()
                mock_executor.invoke.return_value = "Test response"
                mock_agent.return_value = mock_executor
                
                # Capture console output by patching rich.console.Console
                with patch('rich.console.Console') as mock_console_class:
                    mock_console = Mock()
                    mock_console_class.return_value = mock_console
                    
                    handle_llm_query("test query")
                    
                    # Verify the model name appears in the processing message
                    calls = mock_console.print.call_args_list
                    processing_call = next((call for call in calls 
                                          if "Processing query with" in str(call)), None)
                    assert processing_call is not None, "Should show processing message with model name"
                    # Should show actual model (gpt-5 from mock_env)
                    assert "gpt-5" in str(processing_call)

    def test_test_llm_basic_success(self, mock_env):
        """Test basic LLM functionality test."""
        from sqlbot.llm_integration import test_llm_basic
        
        mock_response = Mock()
        mock_response.content = "Hello from LLM integration!"
        
        with patch('sqlbot.llm_integration.get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm
            
            result = test_llm_basic()
            
            assert result is True
            mock_llm.invoke.assert_called_once()

    def test_test_llm_basic_failure(self, mock_env):
        """Test basic LLM functionality test failure."""
        from sqlbot.llm_integration import test_llm_basic
        
        with patch('sqlbot.llm_integration.get_llm') as mock_get_llm:
            mock_get_llm.side_effect = Exception("API Error")
            
            result = test_llm_basic()
            
            assert result is False

    def test_dbt_query_tool_success(self, mock_env, tmp_path):
        """Test DbtQueryTool successful execution."""
        from sqlbot.llm_integration import DbtQueryTool
        from sqlbot.core.types import QueryResult, QueryType
        
        tool = DbtQueryTool()
        
        # Mock DbtService to return success result
        mock_success_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=0.1,
            data=[{"id": 1}],
            columns=["id"],
            row_count=1
        )
        
        with patch('sqlbot.core.dbt_service.DbtService.execute_query', return_value=mock_success_result):
            with patch('os.path.dirname', return_value=str(tmp_path)):
                result = tool._run("SELECT 1")
                
                assert "success" in result.lower()
                assert '"id": 1' in result

    def test_dbt_query_tool_failure(self, mock_env, tmp_path):
        """Test DbtQueryTool error handling."""
        from sqlbot.llm_integration import DbtQueryTool
        from sqlbot.core.types import QueryResult, QueryType
        
        tool = DbtQueryTool()
        
        # Mock DbtService to return error result
        mock_error_result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.1,
            error="STDERR: SQL syntax error"
        )
        
        with patch('sqlbot.core.dbt_service.DbtService.execute_query', return_value=mock_error_result):
            with patch('os.path.dirname', return_value=str(tmp_path)):
                result = tool._run("INVALID SQL")
                
                # Check that the result contains error information
                assert "failed" in result
                assert "SQL syntax error" in result

    def test_dbt_query_tool_timeout(self, mock_env, tmp_path):
        """Test DbtQueryTool timeout handling."""
        from sqlbot.llm_integration import DbtQueryTool
        import subprocess
        
        tool = DbtQueryTool()
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('dbt', 60)):
            with patch('os.path.dirname', return_value=str(tmp_path)):
                result = tool._run("SELECT * FROM large_table")
                
                assert "timed out" in result
                assert "60 seconds" in result

    def test_load_schema_info_success(self, tmp_path):
        """Test loading schema information from YAML."""
        from sqlbot.llm_integration import load_schema_info
        
        # Create mock schema.yml
        schema_content = """
sources:
  - name: your_source
    tables:
      - name: your_main_table
        description: Main data table
        columns:
          - name: id
            description: Primary key
          - name: agent
            description: Agent name
"""
        schema_file = tmp_path / "models" / "schema.yml"
        schema_file.parent.mkdir(exist_ok=True)
        schema_file.write_text(schema_content)
        
        with patch('os.path.dirname', return_value=str(tmp_path)):
            result = load_schema_info()
            
            assert "your_source" in result
            assert "your_main_table" in result
            assert "Main data table" in result

    def test_load_schema_info_missing_file(self, tmp_path):
        """Test loading schema info when file is missing."""
        from sqlbot.llm_integration import load_schema_info
        
        with patch('os.path.dirname', return_value=str(tmp_path)):
            result = load_schema_info()
            
            assert "Schema file not found" in result

    def test_load_macro_info_success(self, tmp_path):
        """Test loading macro information."""
        from sqlbot.llm_integration import load_macro_info
        
        # Create mock macro file
        macro_content = """
{% macro find_report_by_id(report_id) %}
-- Find a specific report by ID
SELECT * FROM {{ source('your_source', 'your_table') }}
WHERE id = {{ report_id }}
{% endmacro %}
"""
        macros_dir = tmp_path / "macros"
        macros_dir.mkdir(exist_ok=True)
        (macros_dir / "report_lookups.sql").write_text(macro_content)
        
        with patch('os.path.dirname', return_value=str(tmp_path)):
            result = load_macro_info()
            
            assert "find_report_by_id" in result
            assert "Find a specific report by ID" in result

    def test_build_system_prompt(self, tmp_path):
        """Test building the system prompt."""
        from sqlbot.llm_integration import build_system_prompt

        # Test with default profile (should use generic template)
        with patch('sqlbot.llm_integration.get_current_profile', return_value='sqlbot'):
            prompt = build_system_prompt()

            assert "database analyst assistant" in prompt
            # Should use generic template, not SQL Server specific
            assert "Generic SQL Database" in prompt or "helpful database analyst assistant" in prompt
            assert "database analyst assistant" in prompt
            assert "dbt source()" in prompt

    def test_create_llm_agent(self, mock_env):
        """Test creating LLM agent."""
        from sqlbot.llm_integration import create_llm_agent
        
        with patch('sqlbot.llm_integration.LoggingChatOpenAI') as mock_llm_class:
            with patch('sqlbot.llm_integration.create_tool_calling_agent') as mock_create_agent:
                with patch('sqlbot.llm_integration.AgentExecutor') as mock_executor:
                    mock_llm = Mock()
                    mock_llm_class.return_value = mock_llm
                    
                    agent = create_llm_agent()
                    
                    mock_llm_class.assert_called_once()
                    mock_create_agent.assert_called_once()
                    mock_executor.assert_called_once()

    def test_system_prompt_template_escaping(self, mock_env):
        """Test that system prompt properly renders Jinja2 template with variables."""
        from sqlbot.llm_integration import build_system_prompt

        # Mock schema and macro loading
        with patch('sqlbot.llm_integration.load_schema_info', return_value="Test schema"):
            with patch('sqlbot.llm_integration.load_macro_info', return_value="Test macros"):
                with patch('sqlbot.llm_integration.get_current_profile', return_value='sqlbot'):
                    prompt = build_system_prompt()

                    # Check that template variables were properly substituted
                    assert "Test schema" in prompt
                    assert "Test macros" in prompt
                    
                    # Check that dbt syntax is properly rendered from template
                    # Should contain the rendered dbt source syntax
                    assert "{{ source(" in prompt

    def test_handle_llm_query_success(self, mock_env):
        """Test successful LLM query handling."""
        from sqlbot.llm_integration import handle_llm_query
        
        mock_agent = Mock()
        mock_result = {
            "output": "There are 1,458 tables in the database.",
            "intermediate_steps": []
        }
        mock_agent.invoke.return_value = mock_result
        
        with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent):
            with patch('sqlbot.llm_integration.check_dbt_setup', return_value=(True, "dbt is configured")):
                result = handle_llm_query("How many tables are there?")
                
                assert "1,458 tables" in result
            mock_agent.invoke.assert_called_once()

    def test_handle_llm_query_with_context(self, mock_env):
        """Test LLM query handling with conversation context."""
        from sqlbot.llm_integration import handle_llm_query, conversation_history
        
        # Set up conversation history
        conversation_history.clear()
        conversation_history.extend([
            {"role": "user", "content": "Show me tables"},
            {"role": "assistant", "content": "Here are the tables..."}
        ])
        
        mock_agent = Mock()
        mock_result = {
            "output": "Here are the report tables specifically.",
            "intermediate_steps": []
        }
        mock_agent.invoke.return_value = mock_result
        
        with patch('sqlbot.llm_integration.create_llm_agent', return_value=mock_agent):
            with patch('sqlbot.llm_integration.check_dbt_setup', return_value=(True, "dbt is configured")):
                result = handle_llm_query("What about just report tables?")
                
                assert "report tables" in result
            # Verify context was used in the invoke call - now passed as chat_history
            call_args = mock_agent.invoke.call_args[0][0]
            assert "input" in call_args
            assert "chat_history" in call_args
            # The input should be the raw query, not contextual
            assert call_args["input"] == "What about just report tables?"

    def test_handle_llm_query_dbt_setup_failure(self, mock_env):
        """Test LLM query handling when dbt setup fails."""
        from sqlbot.llm_integration import handle_llm_query
        
        # Mock dbt setup failure
        with patch('sqlbot.llm_integration.check_dbt_setup', return_value=(False, "Profile not found")):
            result = handle_llm_query("How many tables are there?")
            
            assert result == "Profile not found"
            # Should not try to create LLM agent when dbt setup fails

"""
Integration tests for export functionality with LLM agent and full SQLBot system
"""

import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from sqlbot.core.agent import SQLBotAgent, SQLBotAgentFactory
from sqlbot.core.config import SQLBotConfig
from sqlbot.core.types import QueryResult, QueryType, LLMConfig
from sqlbot.core.llm import LLMAgent
from sqlbot.core.query_result_list import get_query_result_list


@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for exports"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_config():
    """Create a mock SQLBot config with LLM enabled"""
    config = SQLBotConfig()
    config.profile = "test_profile"
    config.llm = LLMConfig(
        api_key="test-api-key",
        model="gpt-3.5-turbo",
        max_tokens=1000,
        temperature=0.0
    )
    return config


@pytest.fixture
def mock_successful_query_result():
    """Create a successful query result with sample data"""
    return QueryResult(
        success=True,
        query_type=QueryType.SQL,
        execution_time=1.5,
        data=[
            ["Alice", "Engineering", 75000],
            ["Bob", "Marketing", 65000],
            ["Charlie", "Sales", 70000]
        ],
        columns=["name", "department", "salary"],
        row_count=3,
        compiled_sql="SELECT name, department, salary FROM employees"
    )


class TestLLMAgentExportTool:
    """Test export tool integration with LLM agent"""

    def test_llm_agent_has_export_tool(self, mock_config):
        """Test that LLM agent includes the export tool"""
        with patch('sqlbot.core.llm.ChatOpenAI'), \
             patch('sqlbot.core.llm.create_tool_calling_agent') as mock_create_agent, \
             patch('sqlbot.core.llm.AgentExecutor') as mock_executor:

            agent = LLMAgent(mock_config, "test_session")

            # Mock the agent creation to capture the tools
            mock_create_agent.return_value = Mock()
            mock_executor.return_value = Mock()

            # Trigger agent creation
            agent._get_agent()

            # Verify that create_tool_calling_agent was called with tools
            assert mock_create_agent.called
            call_args = mock_create_agent.call_args
            tools = call_args[0][1]  # Second argument should be tools list

            # Check that we have both dbt_query and export_data tools
            tool_names = [tool.name for tool in tools]
            assert "dbt_query" in tool_names
            assert "export_data" in tool_names

    @patch('sqlbot.core.llm.ChatOpenAI')
    @patch('sqlbot.core.llm.create_tool_calling_agent')
    @patch('sqlbot.core.llm.AgentExecutor')
    def test_export_tool_execution(self, mock_executor, mock_create_agent, mock_openai,
                                   mock_config, mock_successful_query_result, temp_export_dir):
        """Test that the export tool can be executed successfully"""
        # Set up mocks
        mock_create_agent.return_value = Mock()
        mock_agent_executor = Mock()
        mock_executor.return_value = mock_agent_executor

        # Create LLM agent
        agent = LLMAgent(mock_config, "test_session")

        # Add a successful query result to the session
        result_list = get_query_result_list("test_session")
        result_list.add_result("SELECT name, department, salary FROM employees", mock_successful_query_result)

        # Get the actual export tool from the agent
        agent_instance = agent._get_agent()

        # Find the export tool by examining the tools that were passed to create_tool_calling_agent
        call_args = mock_create_agent.call_args
        tools = call_args[0][1]
        export_tool = next(tool for tool in tools if tool.name == "export_data")

        # Test the export tool directly
        result = export_tool.func(format="csv", location=temp_export_dir)

        # Verify the result indicates success
        assert "Successfully exported" in result
        assert "3 rows" in result
        assert "csv format" in result

        # Verify that a file was actually created
        export_files = list(Path(temp_export_dir).glob("sqlbot_query_*.csv"))
        assert len(export_files) == 1

        # Verify file contents
        df = pd.read_csv(export_files[0])
        assert len(df) == 3
        assert list(df.columns) == ["name", "department", "salary"]
        assert df.iloc[0]["name"] == "Alice"

    @patch('sqlbot.core.llm.ChatOpenAI')
    @patch('sqlbot.core.llm.create_tool_calling_agent')
    @patch('sqlbot.core.llm.AgentExecutor')
    def test_export_tool_no_results(self, mock_executor, mock_create_agent, mock_openai, mock_config):
        """Test export tool behavior when no results are available"""
        # Set up mocks
        mock_create_agent.return_value = Mock()
        mock_agent_executor = Mock()
        mock_executor.return_value = mock_agent_executor

        # Create LLM agent with no query results
        agent = LLMAgent(mock_config, "empty_session")

        # Get the export tool
        agent_instance = agent._get_agent()
        call_args = mock_create_agent.call_args
        tools = call_args[0][1]
        export_tool = next(tool for tool in tools if tool.name == "export_data")

        # Test the export tool
        result = export_tool.func(format="csv")

        # Verify the result indicates failure
        assert "Export failed" in result
        assert "No query results available" in result

    @patch('sqlbot.core.llm.ChatOpenAI')
    @patch('sqlbot.core.llm.create_tool_calling_agent')
    @patch('sqlbot.core.llm.AgentExecutor')
    def test_export_tool_invalid_format(self, mock_executor, mock_create_agent, mock_openai,
                                        mock_config, mock_successful_query_result):
        """Test export tool behavior with invalid format"""
        # Set up mocks
        mock_create_agent.return_value = Mock()
        mock_agent_executor = Mock()
        mock_executor.return_value = mock_agent_executor

        # Create LLM agent and add a query result
        agent = LLMAgent(mock_config, "test_session")
        result_list = get_query_result_list("test_session")
        result_list.add_result("SELECT * FROM test", mock_successful_query_result)

        # Get the export tool
        agent_instance = agent._get_agent()
        call_args = mock_create_agent.call_args
        tools = call_args[0][1]
        export_tool = next(tool for tool in tools if tool.name == "export_data")

        # Test with invalid format
        result = export_tool.func(format="invalid_format")

        # Verify the result indicates invalid format
        assert "Invalid format 'invalid_format'" in result
        assert "csv, excel, parquet" in result

    def test_export_tool_schema_validation(self, mock_config):
        """Test that export tool has correct Pydantic schema"""
        with patch('sqlbot.core.llm.ChatOpenAI'), \
             patch('sqlbot.core.llm.create_tool_calling_agent') as mock_create_agent, \
             patch('sqlbot.core.llm.AgentExecutor'):

            agent = LLMAgent(mock_config, "test_session")
            agent._get_agent()

            # Get the tools
            call_args = mock_create_agent.call_args
            tools = call_args[0][1]
            export_tool = next(tool for tool in tools if tool.name == "export_data")

            # Check that the tool has the correct schema
            assert export_tool.args_schema is not None

            # The schema should have format and location fields
            schema_fields = export_tool.args_schema.__fields__
            assert "format" in schema_fields
            assert "location" in schema_fields

            # Format should default to "csv"
            format_field = schema_fields["format"]
            assert format_field.default == "csv"

            # Location should default to None
            location_field = schema_fields["location"]
            assert location_field.default is None


class TestSQLBotAgentWithExport:
    """Test SQLBot agent integration with export functionality"""

    def test_agent_with_session_id(self, mock_config):
        """Test that SQLBot agent properly passes session_id to LLM agent"""
        with patch('sqlbot.core.agent.LLMAgent') as mock_llm_agent_class:
            mock_llm_agent_class.return_value = Mock()

            agent = SQLBotAgent(mock_config, "test_session_123")

            # Verify that LLMAgent was created with the correct session_id
            mock_llm_agent_class.assert_called_once_with(mock_config, "test_session_123")
            assert agent.session_id == "test_session_123"

    def test_agent_default_session_id(self, mock_config):
        """Test that SQLBot agent uses default session_id when none provided"""
        with patch('sqlbot.core.agent.LLMAgent') as mock_llm_agent_class:
            mock_llm_agent_class.return_value = Mock()

            agent = SQLBotAgent(mock_config)

            # Verify that LLMAgent was created with default session_id
            mock_llm_agent_class.assert_called_once_with(mock_config, "default")
            assert agent.session_id == "default"

    def test_factory_methods_with_session_id(self, mock_config):
        """Test that factory methods properly handle session_id parameter"""
        with patch('sqlbot.core.config.SQLBotConfig.from_env') as mock_from_env, \
             patch('sqlbot.core.agent.SQLBotAgent') as mock_agent_class:

            mock_from_env.return_value = mock_config
            mock_agent_class.return_value = Mock()

            # Test create_from_env with session_id
            SQLBotAgentFactory.create_from_env(session_id="factory_session")
            mock_agent_class.assert_called_with(mock_config, "factory_session")

            # Test create_read_only with session_id
            SQLBotAgentFactory.create_read_only(session_id="readonly_session")
            # Should be called twice now (once for each factory method)
            assert mock_agent_class.call_count == 2

            # Test create_preview_mode with session_id
            SQLBotAgentFactory.create_preview_mode(session_id="preview_session")
            assert mock_agent_class.call_count == 3


class TestSystemPromptExportInstructions:
    """Test that system prompt includes export instructions"""

    def test_system_prompt_includes_export_info(self, mock_config):
        """Test that the system prompt mentions export capabilities"""
        with patch('sqlbot.core.llm.ChatOpenAI'), \
             patch('sqlbot.core.schema.SchemaLoader') as mock_schema_loader:

            # Mock schema loader to return empty schema
            mock_schema_loader.return_value.load_schema_info.return_value = {}
            mock_schema_loader.return_value.load_macro_info.return_value = []

            agent = LLMAgent(mock_config, "test_session")
            system_prompt = agent._build_system_prompt()

            # Check that export-related content is in the prompt
            assert "export_data" in system_prompt
            assert "CSV" in system_prompt
            assert "Excel" in system_prompt
            assert "Parquet" in system_prompt
            assert "most recent query results" in system_prompt
            assert "EXPORT CAPABILITIES" in system_prompt
            assert "EXPORT EXAMPLES" in system_prompt

    def test_system_prompt_tool_descriptions(self, mock_config):
        """Test that system prompt correctly describes both tools"""
        with patch('sqlbot.core.llm.ChatOpenAI'), \
             patch('sqlbot.core.schema.SchemaLoader') as mock_schema_loader:

            mock_schema_loader.return_value.load_schema_info.return_value = {}
            mock_schema_loader.return_value.load_macro_info.return_value = []

            agent = LLMAgent(mock_config, "test_session")
            system_prompt = agent._build_system_prompt()

            # Check that both tools are mentioned
            assert "dbt_query: Execute SQL queries" in system_prompt
            assert "export_data: Export the most recent successful query results" in system_prompt

            # Check export format information
            assert "CSV (default)" in system_prompt
            assert "./tmp directory" in system_prompt


class TestEndToEndExportFlow:
    """Test complete end-to-end export flow"""

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_full_export_workflow(self, temp_export_dir):
        """Test complete workflow from query execution to export"""
        # This is a more comprehensive test that would require actual dbt setup
        # For now, we'll mock the major components and test the flow

        with patch('sqlbot.core.dbt.DbtExecutor') as mock_dbt_executor, \
             patch('sqlbot.core.llm.ChatOpenAI'), \
             patch('sqlbot.core.llm.create_tool_calling_agent'), \
             patch('sqlbot.core.llm.AgentExecutor'), \
             patch('sqlbot.core.schema.SchemaLoader'):

            # Mock successful SQL execution
            mock_executor_instance = Mock()
            mock_dbt_executor.return_value = mock_executor_instance
            mock_executor_instance.execute_sql.return_value = QueryResult(
                success=True,
                query_type=QueryType.SQL,
                execution_time=1.2,
                data=[["Product A", 100], ["Product B", 200]],
                columns=["product", "quantity"],
                row_count=2
            )

            # Create agent and execute query
            config = SQLBotConfig()
            config.profile = "test"
            config.llm.api_key = "test-key"

            agent = SQLBotAgent(config, "integration_test_session")

            # Execute a SQL query (this should create a query result)
            query_result = agent.execute_sql("SELECT product, quantity FROM products")
            assert query_result.success

            # Verify that the result was added to the query result list
            result_list = get_query_result_list("integration_test_session")
            latest_result = result_list.get_latest_result()
            assert latest_result is not None
            assert latest_result.result.row_count == 2

            # Now test export functionality
            from sqlbot.core.export import export_latest_result
            export_result = export_latest_result("integration_test_session", "csv", temp_export_dir)

            assert export_result["success"] is True
            assert export_result["row_count"] == 2
            assert export_result["columns"] == ["product", "quantity"]

            # Verify file was created
            export_file = Path(export_result["file_path"])
            assert export_file.exists()

            # Verify file contents
            df = pd.read_csv(export_file)
            assert len(df) == 2
            assert "Product A" in df["product"].values
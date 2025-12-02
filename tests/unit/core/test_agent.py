"""
Unit tests for SQLBot Core SDK Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlbot.core.agent import SQLBotAgent, SQLBotAgentFactory
from sqlbot.core.config import SQLBotConfig
from sqlbot.core.types import QueryResult, QueryType, SafetyLevel


class TestSQLBotAgent:
    """Test SQLBot agent functionality"""
    
    def setup_method(self):
        """Setup test configuration"""
        self.config = SQLBotConfig(
            profile="test_profile",
            dangerous=False,
            preview_mode=False
        )
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_agent_initialization(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test agent initialization"""
        agent = SQLBotAgent(self.config)
        
        assert agent.config == self.config
        assert agent.safety_analyzer is not None
        assert agent.schema_loader is not None
        assert agent.dbt_executor is not None
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_query_routing_sql(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test query routing for SQL queries"""
        agent = SQLBotAgent(self.config)
        
        # Mock execute_sql method
        expected_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0
        )
        agent.execute_sql = Mock(return_value=expected_result)
        
        result = agent.query("SELECT * FROM users;")
        
        agent.execute_sql.assert_called_once_with("SELECT * FROM users;")
        assert result == expected_result
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_query_routing_natural_language(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test query routing for natural language queries"""
        agent = SQLBotAgent(self.config)
        
        # Mock execute_natural_language method
        expected_result = QueryResult(
            success=True,
            query_type=QueryType.NATURAL_LANGUAGE,
            execution_time=2.0
        )
        agent.execute_natural_language = Mock(return_value=expected_result)
        
        result = agent.query("How many users are there?")
        
        agent.execute_natural_language.assert_called_once_with("How many users are there?")
        assert result == expected_result
    
    def test_empty_query(self):
        """Test handling of empty queries"""
        with patch('sqlbot.core.agent.SchemaLoader'), \
             patch('sqlbot.core.agent.DbtExecutor'), \
             patch('sqlbot.core.agent.LLMAgent'):
            
            agent = SQLBotAgent(self.config)
            
            result = agent.query("")
            
            assert result.success == False
            assert result.error == "Empty query"
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_sql_execution_with_safety_check(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test SQL execution with safety analysis"""
        agent = SQLBotAgent(self.config)
        
        # Mock safety analyzer
        mock_safety_analysis = Mock()
        mock_safety_analysis.level.value = "safe"
        mock_safety_analysis.is_read_only = True
        agent.safety_analyzer.analyze = Mock(return_value=mock_safety_analysis)
        
        # Mock dbt executor
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0
        )
        agent.dbt_executor.execute_sql = Mock(return_value=mock_result)
        
        result = agent.execute_sql("SELECT * FROM users")
        
        # Verify safety analysis was called
        agent.safety_analyzer.analyze.assert_called_once_with("SELECT * FROM users")
        
        # Verify execution was called
        agent.dbt_executor.execute_sql.assert_called_once()
        
        # Verify result includes safety analysis
        assert result.safety_analysis == mock_safety_analysis
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_dangerous_query_blocked(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test that dangerous queries are blocked"""
        agent = SQLBotAgent(self.config)
        
        # Mock dangerous safety analysis
        mock_safety_analysis = Mock()
        mock_safety_analysis.level.value = "dangerous"
        mock_safety_analysis.message = "DROP operation detected"
        agent.safety_analyzer.analyze = Mock(return_value=mock_safety_analysis)
        
        result = agent.execute_sql("DROP TABLE users")
        
        assert result.success == False
        assert "Dangerous query blocked" in result.error
        assert result.safety_analysis == mock_safety_analysis
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_read_only_mode_blocks_writes(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test that dangerous mode disabled blocks write operations"""
        config = SQLBotConfig(dangerous=False)
        agent = SQLBotAgent(config)
        
        # Mock safety analysis for write operation
        mock_safety_analysis = Mock()
        mock_safety_analysis.level.value = "safe"
        mock_safety_analysis.is_read_only = False  # This is a write operation
        agent.safety_analyzer.analyze = Mock(return_value=mock_safety_analysis)
        
        result = agent.execute_sql("INSERT INTO users (name) VALUES ('test')")
        
        assert result.success == False
        assert "Query blocked by read-only mode" in result.error
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_preview_mode_compiles_only(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test that preview mode only compiles, doesn't execute"""
        config = SQLBotConfig(preview_mode=True)
        agent = SQLBotAgent(config)
        
        # Mock safety analysis
        mock_safety_analysis = Mock()
        mock_safety_analysis.level.value = "safe"
        mock_safety_analysis.is_read_only = True
        agent.safety_analyzer.analyze = Mock(return_value=mock_safety_analysis)
        
        # Mock compilation
        from sqlbot.core.types import CompilationResult
        mock_compilation = CompilationResult(
            success=True,
            compiled_sql="SELECT * FROM actual_table_name"
        )
        agent.dbt_executor.compile_sql = Mock(return_value=mock_compilation)
        
        result = agent.execute_sql("SELECT * FROM users")
        
        # Verify compilation was called, not execution
        agent.dbt_executor.compile_sql.assert_called_once()
        assert not hasattr(agent.dbt_executor, 'execute_sql') or not agent.dbt_executor.execute_sql.called
        
        assert result.compiled_sql == "SELECT * FROM actual_table_name"


class TestSQLBotAgentFactory:
    """Test SQLBot agent factory"""
    
    @patch.dict('os.environ', {
        'DBT_PROFILE_NAME': 'test_profile',
        'SQLBOT_READ_ONLY': 'true'
    })
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_create_from_env(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test creating agent from environment"""
        agent = SQLBotAgentFactory.create_from_env()

        assert agent.config.profile == 'test_profile'
        assert agent.config.dangerous == False
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_create_from_env_with_overrides(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test creating agent with configuration overrides"""
        agent = SQLBotAgentFactory.create_from_env(
            profile='override_profile',
            max_rows=500
        )
        
        assert agent.config.profile == 'override_profile'
        assert agent.config.max_rows == 500
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_create_read_only(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test creating safe agent (dangerous mode disabled)"""
        agent = SQLBotAgentFactory.create_read_only('test_profile')
        
        assert agent.config.profile == 'test_profile'
        assert agent.config.dangerous == False
    
    @patch('sqlbot.core.agent.SchemaLoader')
    @patch('sqlbot.core.agent.DbtExecutor')
    @patch('sqlbot.core.agent.LLMAgent')
    def test_create_preview_mode(self, mock_llm_agent, mock_dbt_executor, mock_schema_loader):
        """Test creating preview mode agent"""
        agent = SQLBotAgentFactory.create_preview_mode('test_profile')
        
        assert agent.config.profile == 'test_profile'
        assert agent.config.preview_mode == True

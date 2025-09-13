"""
Tests for SQLBot REPL Interface
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from rich.console import Console

from sqlbot.core import SQLBotAgent, SQLBotConfig
from sqlbot.core.types import QueryResult, QueryType
from sqlbot.interfaces.repl import SQLBotREPL, ResultFormatter, CommandHandler


class TestResultFormatter:
    """Test result formatting functionality"""
    
    def setup_method(self):
        """Setup test console"""
        self.console = Console(file=StringIO(), width=80)
        self.formatter = ResultFormatter(self.console)
    
    def test_format_success_result(self):
        """Test formatting successful query results"""
        result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.5,
            data=[{"id": 1, "name": "test"}],
            row_count=1,
            columns=["id", "name"]
        )
        
        self.formatter.format_query_result(result)
        
        # Check that output was generated (basic test)
        output = self.console.file.getvalue()
        assert len(output) > 0
    
    def test_format_error_result(self):
        """Test formatting error results"""
        result = QueryResult(
            success=False,
            query_type=QueryType.SQL,
            execution_time=0.5,
            error="Table not found"
        )
        
        self.formatter.format_query_result(result)
        
        output = self.console.file.getvalue()
        assert "❌" in output
        assert "Table not found" in output
    
    def test_format_user_input(self):
        """Test formatting user input"""
        self.formatter.format_user_input("SELECT * FROM users;")
        
        output = self.console.file.getvalue()
        assert "SELECT * FROM users;" in output
    
    def test_format_table_list(self):
        """Test formatting table list"""
        tables = [
            {
                'source_name': 'users',
                'name': 'user_table',
                'schema': 'dbo',
                'description': 'User information'
            }
        ]
        
        self.formatter.format_table_list(tables)
        
        output = self.console.file.getvalue()
        assert "user_table" in output
        assert "User information" in output


class TestCommandHandler:
    """Test command handling functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mock_agent = Mock(spec=SQLBotAgent)
        self.console = Console(file=StringIO(), width=80)
        self.formatter = ResultFormatter(self.console)
        self.handler = CommandHandler(self.mock_agent, self.formatter)
    
    def test_help_command(self):
        """Test /help command"""
        result = self.handler.handle_command("/help")
        
        assert result == True  # Should continue REPL
        output = self.console.file.getvalue()
        assert "SQLBot Commands:" in output
    
    def test_tables_command(self):
        """Test /tables command"""
        from sqlbot.core.types import TableInfo
        
        mock_tables = [
            TableInfo(name="users", schema="dbo", description="User data"),
            TableInfo(name="orders", schema="dbo", description="Order data")
        ]
        self.mock_agent.get_tables.return_value = mock_tables
        
        result = self.handler.handle_command("/tables")
        
        assert result == True
        self.mock_agent.get_tables.assert_called_once()
    
    def test_readonly_toggle(self):
        """Test /readonly command toggles read-only mode"""
        # Setup mock config and safety analyzer
        mock_config = Mock()
        mock_config.read_only = False
        self.mock_agent.config = mock_config
        
        mock_safety_analyzer = Mock()
        self.mock_agent.safety_analyzer = mock_safety_analyzer
        
        result = self.handler.handle_command("/readonly")
        
        assert result == True
        assert self.mock_agent.config.read_only == True
        assert self.mock_agent.safety_analyzer.read_only_mode == True
    
    def test_preview_toggle(self):
        """Test /preview command toggles preview mode"""
        # Setup mock config
        mock_config = Mock()
        mock_config.preview_mode = False
        self.mock_agent.config = mock_config
        
        result = self.handler.handle_command("/preview")
        
        assert result == True
        assert self.mock_agent.config.preview_mode == True
    
    def test_exit_command(self):
        """Test /exit command"""
        result = self.handler.handle_command("/exit")
        
        assert result == False  # Should exit REPL
    
    def test_unknown_command(self):
        """Test unknown command handling"""
        result = self.handler.handle_command("/unknown")
        
        assert result == True  # Should continue REPL
        output = self.console.file.getvalue()
        assert "Unknown command" in output


class TestSQLBotREPL:
    """Test SQLBot REPL functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mock_agent = Mock(spec=SQLBotAgent)
        self.mock_agent.config = SQLBotConfig()
        self.console = Console(file=StringIO(), width=80)
        self.repl = SQLBotREPL(self.mock_agent, self.console)
    
    def test_repl_initialization(self):
        """Test REPL initialization"""
        assert self.repl.agent == self.mock_agent
        assert self.repl.console == self.console
        assert self.repl.formatter is not None
        assert self.repl.command_handler is not None
    
    def test_show_banner_interactive(self):
        """Test showing interactive banner"""
        self.repl.show_banner("interactive")
        
        output = self.console.file.getvalue()
        assert "Ready for questions." in output
        assert "Natural Language Queries" in output
    
    def test_show_banner_cli(self):
        """Test showing CLI banner"""
        self.repl.show_banner("cli")
        
        output = self.console.file.getvalue()
        assert "SQLBot CLI" in output
        assert "Database Query Interface" in output
    
    def test_handle_query_input(self):
        """Test handling query input"""
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0
        )
        self.mock_agent.query.return_value = mock_result
        
        result = self.repl.handle_input("SELECT * FROM users;")
        
        assert result == True  # Should continue REPL
        self.mock_agent.query.assert_called_once_with("SELECT * FROM users;")
    
    def test_handle_command_input(self):
        """Test handling command input"""
        # Mock the command handler
        self.repl.command_handler.handle_command = Mock(return_value=True)
        
        result = self.repl.handle_input("/help")
        
        assert result == True
        self.repl.command_handler.handle_command.assert_called_once_with("/help")
    
    def test_execute_single_query(self):
        """Test single query execution (no-repl mode)"""
        mock_result = QueryResult(
            success=True,
            query_type=QueryType.SQL,
            execution_time=1.0
        )
        self.mock_agent.query.return_value = mock_result
        
        self.repl.execute_single_query("SELECT 42;")
        
        self.mock_agent.query.assert_called_once_with("SELECT 42;")
        output = self.console.file.getvalue()
        assert "Starting with query: SELECT 42;" in output
        assert "Exiting (--no-repl mode)" in output


class TestREPLIntegration:
    """Integration tests for REPL components"""
    
    @patch('sqlbot.interfaces.repl.console.SQLBotAgent')
    def test_create_repl_from_args(self, mock_agent_class):
        """Test creating REPL from command line arguments"""
        from sqlbot.interfaces.repl.console import create_repl_from_args
        
        # Mock arguments
        mock_args = Mock()
        mock_args.profile = 'test_profile'
        mock_args.read_only = True
        mock_args.preview = False
        
        # Mock agent creation
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        repl = create_repl_from_args(mock_args)
        
        assert isinstance(repl, SQLBotREPL)
        assert repl.agent == mock_agent

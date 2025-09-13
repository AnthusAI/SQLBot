"""Unit tests for REPL module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from pathlib import Path

class TestREPLCore:
    """Test cases for core REPL functionality."""
    
    # Direct SQL connection functions were removed - all database operations now go through dbt
    # Tests for get_direct_sql_connection() and execute_direct_sql() are no longer needed

    def test_is_sql_query_true(self):
        """Test SQL query detection for valid SQL."""
        from sqlbot.repl import is_sql_query
        
        assert is_sql_query("SELECT * FROM table;") is True
        assert is_sql_query("  SELECT 1;  ") is True
        assert is_sql_query("UPDATE table SET col = 1;") is True

    def test_is_sql_query_false(self):
        """Test SQL query detection for non-SQL."""
        from sqlbot.repl import is_sql_query
        
        assert is_sql_query("How many tables are there?") is False
        assert is_sql_query("SELECT * FROM table") is False  # No semicolon
        assert is_sql_query("") is False

class TestDBTIntegration:
    """Test cases for dbt integration."""

    def test_run_dbt_success(self, tmp_path):
        """Test successful dbt command execution."""
        from sqlbot.repl import run_dbt
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = []
        
        mock_runner = Mock()
        mock_runner.invoke.return_value = mock_result
        
        with patch('sqlbot.repl.dbt', mock_runner):
            with patch('sqlbot.repl.PROJECT_ROOT', tmp_path):
                result = run_dbt(['debug'])
                
                assert result.success is True
                mock_runner.invoke.assert_called_once_with(['debug'])

    def test_run_dbt_failure(self, tmp_path):
        """Test failed dbt command execution."""
        from sqlbot.repl import run_dbt
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.exception = "dbt error"
        
        mock_runner = Mock()
        mock_runner.invoke.return_value = mock_result
        
        with patch('sqlbot.repl.dbt', mock_runner):
            with patch('sqlbot.repl.PROJECT_ROOT', tmp_path):
                result = run_dbt(['invalid-command'])
                
                assert result.success is False

    def test_dbt_debug(self):
        """Test dbt debug command."""
        from sqlbot.repl import dbt_debug
        
        with patch('sqlbot.repl.run_dbt') as mock_run:
            dbt_debug()
            mock_run.assert_called_once_with(['debug'])

    def test_dbt_run_without_select(self):
        """Test dbt run command without selection."""
        from sqlbot.repl import dbt_run
        
        with patch('sqlbot.repl.run_dbt') as mock_run:
            dbt_run()
            mock_run.assert_called_once_with(['run'])

    def test_dbt_run_with_select(self):
        """Test dbt run command with model selection."""
        from sqlbot.repl import dbt_run
        
        with patch('sqlbot.repl.run_dbt') as mock_run:
            dbt_run('my_model')
            mock_run.assert_called_once_with(['run', '--select', 'my_model'])

    def test_dbt_test_without_select(self):
        """Test dbt test command without selection."""
        from sqlbot.repl import dbt_test
        
        with patch('sqlbot.repl.run_dbt') as mock_run:
            dbt_test()
            mock_run.assert_called_once_with(['test'])

    def test_dbt_show(self):
        """Test dbt show command."""
        from sqlbot.repl import dbt_show
        
        with patch('sqlbot.repl.run_dbt') as mock_run:
            dbt_show('my_model', 20)
            mock_run.assert_called_once_with(['show', '--select', 'my_model', '--limit', '20'])

class TestSlashCommands:
    """Test cases for slash command handling."""

    def test_handle_slash_command_debug(self):
        """Test /debug command."""
        from sqlbot.repl import handle_slash_command
        
        with patch('sqlbot.repl.dbt_debug') as mock_debug:
            handle_slash_command('/debug')
            mock_debug.assert_called_once()

    def test_handle_slash_command_run(self):
        """Test /run command."""
        from sqlbot.repl import handle_slash_command
        
        with patch('sqlbot.repl.dbt_run') as mock_run:
            handle_slash_command('/run')
            mock_run.assert_called_once_with()

    def test_handle_slash_command_run_with_model(self):
        """Test /run command with model selection."""
        from sqlbot.repl import handle_slash_command
        
        with patch('sqlbot.repl.dbt_run') as mock_run:
            handle_slash_command('/run my_model')
            mock_run.assert_called_once_with('my_model')

    def test_handle_slash_command_help(self, capsys):
        """Test /help command."""
        from sqlbot.repl import handle_slash_command
        
        with patch('sqlbot.repl.rich_console') as mock_console:
            handle_slash_command('/help')
            mock_console.print.assert_called()

    def test_handle_slash_command_exit(self):
        """Test /exit command."""
        from sqlbot.repl import handle_slash_command
        
        result = handle_slash_command('/exit')
        assert result == 'EXIT'

    def test_handle_slash_command_unknown(self, capsys):
        """Test unknown slash command."""
        from sqlbot.repl import handle_slash_command
        
        handle_slash_command('/unknown')
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_handle_slash_command_not_slash(self):
        """Test non-slash command."""
        from sqlbot.repl import handle_slash_command
        
        result = handle_slash_command('regular command')
        assert result is None

class TestSQLExecution:
    """Test cases for SQL execution functionality."""

    def test_execute_dbt_sql_success(self, tmp_path):
        """Test successful dbt SQL execution."""
        from sqlbot.repl import execute_dbt_sql
        
        # Create models directory
        models_dir = tmp_path / 'models'
        models_dir.mkdir(exist_ok=True)
        
        mock_result = "Query executed successfully"
        
        with patch('sqlbot.repl.PROJECT_ROOT', tmp_path):
            with patch('sqlbot.repl.execute_clean_sql', return_value=mock_result):
                result = execute_dbt_sql("SELECT 1")
                
                assert result == "Query executed successfully"

    def test_execute_dbt_sql_cleanup(self, tmp_path):
        """Test that temporary files are cleaned up."""
        from sqlbot.repl import execute_dbt_sql
        
        # Create models directory
        models_dir = tmp_path / 'models'
        models_dir.mkdir(exist_ok=True)
        
        mock_result = Mock()
        mock_result.success = True
        
        with patch('sqlbot.repl.PROJECT_ROOT', tmp_path):
            with patch('sqlbot.repl.run_dbt', return_value=mock_result):
                execute_dbt_sql("SELECT 1")
                
                # Check that no temp files remain
                temp_files = list(models_dir.glob('temp_query_*.sql'))
                assert len(temp_files) == 0

class TestHistoryManagement:
    """Test cases for command history functionality."""

    def test_setup_history_success(self, tmp_path):
        """Test successful history setup."""
        from sqlbot.repl import setup_history
        
        with patch('sqlbot.repl.HISTORY_FILE', tmp_path / 'test_history'):
            with patch('readline.set_history_length') as mock_set_length:
                with patch('readline.read_history_file') as mock_read:
                    with patch('atexit.register') as mock_register:
                        setup_history()
                        
                        mock_set_length.assert_called_once()
                        mock_register.assert_called_once()

    def test_setup_history_no_readline(self, tmp_path):
        """Test history setup when readline is not available."""
        from sqlbot.repl import setup_history
        
        with patch('readline.set_history_length', side_effect=Exception("No readline")):
            # Should not raise exception
            setup_history()

    def test_save_history_success(self, tmp_path):
        """Test successful history saving."""
        from sqlbot.repl import save_history
        
        with patch('readline.set_history_length') as mock_set_length:
            with patch('readline.write_history_file') as mock_write:
                save_history()
                
                mock_set_length.assert_called_once()
                mock_write.assert_called_once()

    def test_save_history_failure(self):
        """Test history saving failure handling."""
        from sqlbot.repl import save_history
        
        with patch('readline.write_history_file', side_effect=Exception("Write failed")):
            # Should not raise exception
            save_history()

class TestMainFunction:
    """Test cases for main function and argument parsing."""

    def test_main_with_help(self, capsys):
        """Test main function with help argument."""
        from sqlbot.repl import main
        import argparse
        
        with patch('sys.argv', ['sqlbot', '--help']):
            # Mock argparse to raise SystemExit(0) when --help is called
            with patch('argparse.ArgumentParser.parse_args') as mock_parse:
                mock_parse.side_effect = SystemExit(0)
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_main_with_query(self):
        """Test main function with query argument in --no-repl mode."""
        from sqlbot.repl import main
        
        with patch('sys.argv', ['sqlbot', '--no-repl', 'test query']):
            with patch('sqlbot.repl.handle_llm_query') as mock_llm:
                with patch('sqlbot.repl.start_console') as mock_console:
                    with patch('sqlbot.repl.LLM_AVAILABLE', True):
                        with patch('sqlbot.repl.show_banner'):  # Mock banner to avoid output
                            main()
                        
                        # Check that handle_llm_query was called with the right basic parameters
                        mock_llm.assert_called_once()
                        args, kwargs = mock_llm.call_args
                        assert args[0] == 'test query'
                        assert kwargs['max_retries'] == 3
                        assert kwargs['timeout_seconds'] == 120
                        assert 'unified_display' in kwargs
                        # In --no-repl mode, start_console should not be called
                        mock_console.assert_not_called()

    def test_main_interactive_mode(self):
        """Test main function in interactive mode."""
        from sqlbot.repl import main
        
        with patch('sys.argv', ['sqlbot', '--text']):
            with patch('sqlbot.repl._start_cli_interactive_mode') as mock_cli_mode:
                with patch('sqlbot.repl.show_banner'):  # Mock banner to avoid output
                    with patch('sqlbot.repl.rich_console') as mock_rich_console:  # Mock rich console to avoid output
                        main()
                        # Should use text-mode interactive REPL
                        mock_cli_mode.assert_called_once()

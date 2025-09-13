"""
dbt integration for SQLBot Core SDK

This module handles dbt operations independent of any UI.
DEPRECATED: Use DbtService from dbt_service.py instead for new code.
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from .types import CompilationResult, QueryResult, QueryType
from .config import SQLBotConfig
from .dbt_service import get_dbt_service


class DbtExecutor:
    """
    Handles dbt operations and SQL execution
    DEPRECATED: Use DbtService from dbt_service.py instead for new code.
    """
    
    def __init__(self, config: SQLBotConfig):
        self.config = config
        self._dbt_service = get_dbt_service(config)
    
    def _setup_environment(self):
        """Setup environment variables for dbt"""
        env_vars = self.config.to_env_dict()
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Set profile-specific log and target paths
        profile_name = self.config.profile
        
        # Priority 1: .sqlbot/profiles/{profile}/
        user_profile_dir = Path(f'.sqlbot/profiles/{profile_name}')
        if user_profile_dir.exists():
            os.environ['DBT_LOG_PATH'] = str(user_profile_dir / 'logs')
            os.environ['DBT_TARGET_PATH'] = str(user_profile_dir / 'target')
        else:
            # Priority 2: profiles/{profile}/
            profile_dir = Path(f'profiles/{profile_name}')
            profile_dir.mkdir(parents=True, exist_ok=True)
            os.environ['DBT_LOG_PATH'] = str(profile_dir / 'logs')
            os.environ['DBT_TARGET_PATH'] = str(profile_dir / 'target')
    
    def _get_temp_directory(self) -> str:
        """
        Get profile-specific temporary directory for model files
        
        Returns:
            Path to temporary directory for this profile
        """
        profile_name = self.config.profile
        
        # Priority 1: .sqlbot/profiles/{profile}/models/temp/
        user_temp_dir = Path(f'.sqlbot/profiles/{profile_name}/models/temp')
        if user_temp_dir.parent.parent.parent.exists():  # Check if .sqlbot/profiles/{profile} exists
            user_temp_dir.mkdir(parents=True, exist_ok=True)
            return str(user_temp_dir)
        
        # Priority 2: profiles/{profile}/models/temp/
        profile_temp_dir = Path(f'profiles/{profile_name}/models/temp')
        if profile_temp_dir.parent.parent.exists():  # Check if profiles/{profile} exists
            profile_temp_dir.mkdir(parents=True, exist_ok=True)
            return str(profile_temp_dir)
        
        # Fallback: Create profile directory structure
        profile_temp_dir = Path(f'profiles/{profile_name}/models/temp')
        profile_temp_dir.mkdir(parents=True, exist_ok=True)
        return str(profile_temp_dir)
    
    def _get_dbt_runner(self):
        """Get or create dbt runner instance"""
        if self._dbt_runner is None:
            try:
                from dbt.cli.main import dbtRunner
                self._dbt_runner = dbtRunner()
            except ImportError:
                raise ImportError("dbt-core is required but not installed")
        return self._dbt_runner
    
    def compile_sql(self, sql_query: str) -> CompilationResult:
        """
        Compile SQL query through dbt
        DEPRECATED: Use DbtService.compile_query() instead
        """
        return self._dbt_service.compile_query(sql_query)
    
    def execute_sql(self, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """
        Execute SQL query through dbt
        DEPRECATED: Use DbtService.execute_query() instead
        """
        return self._dbt_service.execute_query(sql_query, limit)
    
    def test_connection(self) -> bool:
        """
        Test dbt connection
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['debug'])
            return result.success
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """
        List available dbt models
        
        Returns:
            List of model names
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['list', '--resource-type', 'model'])
            
            if result.success:
                # Parse model names from output
                # This would need to be implemented based on dbt output format
                return []
            else:
                return []
        except Exception:
            return []
    
    def run_model(self, model_name: str) -> bool:
        """
        Run a specific dbt model
        
        Args:
            model_name: Name of the model to run
            
        Returns:
            True if successful, False otherwise
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['run', '--select', model_name])
            return result.success
        except Exception:
            return False
    
    def _parse_dbt_show_output(self, dbt_result) -> Dict[str, Any]:
        """
        Parse dbt show output into structured data
        
        Args:
            dbt_result: Result object from dbt.invoke()
            
        Returns:
            Dictionary with 'data' (list of row dicts) and 'columns' (list of column names)
        """
        try:
            # Extract table data from dbt result
            if hasattr(dbt_result, 'result') and dbt_result.result:
                for node_result in dbt_result.result:
                    # Check if dbt provides structured table data directly
                    if hasattr(node_result, 'table') and node_result.table:
                        table = node_result.table
                        if hasattr(table, 'columns') and hasattr(table, 'rows'):
                            return {
                                'data': [dict(zip(table.columns, row)) for row in table.rows],
                                'columns': list(table.columns)
                            }
                    
                    # Parse message output if it contains table data
                    if hasattr(node_result, 'message') and node_result.message:
                        return self._parse_table_from_message(str(node_result.message))
            
            # If no structured data found, return empty
            return {'data': [], 'columns': []}
            
        except Exception as e:
            return {'data': [], 'columns': []}
    
    def _parse_table_from_message(self, message: str) -> Dict[str, Any]:
        """Parse table data from dbt message output"""
        if not message:
            return {'data': [], 'columns': []}
        
        lines = message.split('\n')
        table_data = []
        column_headers = []
        
        for line in lines:
            # Skip separator lines and empty lines
            if not line.strip() or '---' in line:
                continue
                
            # Look for pipe-delimited table rows
            if '|' in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if parts:
                    if not column_headers:
                        column_headers = parts
                    else:
                        table_data.append(parts)
        
        # Convert to structured data
        structured_data = []
        if column_headers and table_data:
            for row in table_data:
                # Ensure row has same number of columns
                padded_row = row + [''] * (len(column_headers) - len(row))
                row_dict = {column_headers[i]: padded_row[i] for i in range(len(column_headers))}
                structured_data.append(row_dict)
        
        return {
            'data': structured_data,
            'columns': column_headers
        }


def is_sql_query(query: str) -> bool:
    """
    Detect if query should be treated as SQL/dbt (ends with semicolon)
    
    Args:
        query: The query string to check
        
    Returns:
        True if it's a SQL query, False otherwise
    """
    return query.strip().endswith(';')


def cleanup_temp_files():
    """
    Clean up any leftover temporary model files
    
    This function removes temporary SQL files that may have been left behind
    due to interrupted executions or exceptions.
    """
    import glob
    
    # Legacy patterns (for backward compatibility)
    legacy_patterns = [
        'models/qbot_temp_*.sql',
        'models/temp_user_display_*.sql',
        'models/temp_rich_*.sql'
    ]
    
    # Profile-specific patterns
    profile_patterns = [
        'profiles/*/models/temp/qbot_temp_*.sql',
        'profiles/*/models/temp/*.sql',
        '.sqlbot/profiles/*/models/temp/qbot_temp_*.sql',
        '.sqlbot/profiles/*/models/temp/*.sql'
    ]
    
    cleaned_count = 0
    
    # Clean legacy files
    for pattern in legacy_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                cleaned_count += 1
            except Exception:
                pass  # Ignore errors during cleanup
    
    # Clean profile-specific files
    for pattern in profile_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                cleaned_count += 1
            except Exception:
                pass  # Ignore errors during cleanup
    
    # Clean empty directories
    empty_dirs = [
        'profiles/*/models/temp',
        '.sqlbot/profiles/*/models/temp',
        'profiles/*/logs',
        'profiles/*/target', 
        '.sqlbot/profiles/*/logs',
        '.sqlbot/profiles/*/target'
    ]
    
    for pattern in empty_dirs:
        for dir_path in glob.glob(pattern):
            try:
                if os.path.isdir(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception:
                pass  # Ignore errors during cleanup
    
    return cleaned_count

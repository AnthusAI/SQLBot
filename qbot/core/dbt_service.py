"""
Centralized dbt service for all programmatic dbt operations

This module provides a single, consistent interface for all dbt operations
throughout QBot, eliminating subprocess calls and providing structured results.
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from .types import QueryResult, QueryType, CompilationResult
from .config import QBotConfig


class DbtService:
    """Centralized service for all dbt operations"""
    
    def __init__(self, config: QBotConfig):
        self.config = config
        self._dbt_runner = None
        self._setup_environment()
        self._temp_dir = self._get_temp_directory()
    
    def _setup_environment(self):
        """Setup environment variables for dbt"""
        env_vars = self.config.to_env_dict()
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Set profile-specific log and target paths
        profile_name = self.config.profile
        
        # Priority 1: .qbot/profiles/{profile}/
        user_profile_dir = Path(f'.qbot/profiles/{profile_name}')
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
        """Get temporary directory for model files - must be in main models/ directory for dbt to find them"""
        # dbt looks for models in the models/ directory, so we must put temp files there
        models_dir = Path('models')
        models_dir.mkdir(parents=True, exist_ok=True)
        return str(models_dir)
    
    def _get_dbt_runner(self):
        """Get or create dbt runner instance"""
        if self._dbt_runner is None:
            try:
                from dbt.cli.main import dbtRunner
                self._dbt_runner = dbtRunner()
            except ImportError:
                raise ImportError("dbt-core is required but not installed")
        return self._dbt_runner
    
    def execute_query(self, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """
        Execute SQL query and return structured results
        
        Args:
            sql_query: The SQL query to execute
            limit: Optional limit on number of rows to return
            
        Returns:
            QueryResult with structured data
        """
        import time
        start_time = time.time()
        
        try:
            # Clean query for dbt inline execution
            clean_query = sql_query.strip().rstrip(';')
            
            # Apply limit if specified (for SQL Server)
            if limit and limit > 0 and 'TOP' not in clean_query.upper():
                if clean_query.upper().startswith('SELECT'):
                    clean_query = clean_query.replace('SELECT', f'SELECT TOP {limit}', 1)
            
            try:
                # Execute via dbt show --inline (no temporary file needed)
                import sys
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                dbt = self._get_dbt_runner()
                
                # Build command args for inline execution
                cmd_args = ['show', '--inline', clean_query]
                if limit:
                    cmd_args.extend(['--limit', str(limit)])
                
                # Capture stdout and stderr
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    result = dbt.invoke(cmd_args)
                
                # Get captured output
                stdout_output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()
                
                # Debug output can be enabled for troubleshooting
                # print(f"DEBUG: dbt stdout: {stdout_output[:500]}...")
                # print(f"DEBUG: dbt stderr: {stderr_output[:500]}...")
                # print(f"DEBUG: dbt result success: {result.success}")
                
                # Store captured output for parsing
                result._captured_stdout = stdout_output
                result._captured_stderr = stderr_output
                
                execution_time = time.time() - start_time
                
                if result.success:
                    # Parse structured results from dbt show output
                    parsed_data = self._parse_dbt_show_output(result)
                    
                    return QueryResult(
                        success=True,
                        query_type=QueryType.SQL,
                        execution_time=execution_time,
                        data=parsed_data['data'],
                        columns=parsed_data['columns'],
                        row_count=len(parsed_data['data']) if parsed_data['data'] else 0
                    )
                else:
                    # Extract detailed error information from result
                    error_details = []
                    
                    # Check for exception
                    if hasattr(result, 'exception') and result.exception:
                        error_details.append(f"Exception: {str(result.exception)}")
                    
                    # Check for result errors
                    if hasattr(result, 'result') and result.result:
                        for node_result in result.result:
                            if hasattr(node_result, 'status') and node_result.status == 'error':
                                if hasattr(node_result, 'message') and node_result.message:
                                    error_details.append(f"Node error: {node_result.message}")
                            if hasattr(node_result, 'error') and node_result.error:
                                error_details.append(f"Node error: {node_result.error}")
                    
                    # Check for args/kwargs that might contain error info
                    if hasattr(result, 'args') and result.args:
                        error_details.append(f"Args: {result.args}")
                    
                    # Fallback error message
                    if not error_details:
                        error_details.append(f"dbt execution failed with success={result.success}")
                        # Add any other attributes for debugging
                        attrs = [attr for attr in dir(result) if not attr.startswith('_')]
                        error_details.append(f"Available result attributes: {attrs}")
                    
                    error_msg = "; ".join(error_details)
                    
                    return QueryResult(
                        success=False,
                        query_type=QueryType.SQL,
                        execution_time=execution_time,
                        error=error_msg
                    )
            
            finally:
                # No cleanup needed for inline execution
                pass
        
        except Exception as e:
            execution_time = time.time() - start_time
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=execution_time,
                error=f"Execution error: {str(e)}"
            )
    
    def compile_query(self, sql_query: str) -> CompilationResult:
        """
        Compile SQL query through dbt
        
        Args:
            sql_query: The SQL query to compile
            
        Returns:
            CompilationResult with compiled SQL
        """
        try:
            # Create temporary model
            model_name = f"qbot_temp_{uuid.uuid4().hex[:8]}"
            model_file = f"{self._temp_dir}/{model_name}.sql"
            
            # Ensure temp directory exists
            os.makedirs(self._temp_dir, exist_ok=True)
            
            # Write SQL to temporary file
            with open(model_file, 'w') as f:
                f.write(sql_query)
            
            try:
                # Compile via dbt
                dbt = self._get_dbt_runner()
                result = dbt.invoke(['compile', '--select', model_name])
                
                if result.success:
                    # Try to read compiled SQL from target directory
                    compiled_sql = self._read_compiled_sql(model_name)
                    
                    return CompilationResult(
                        success=True,
                        compiled_sql=compiled_sql
                    )
                else:
                    error_msg = "dbt compilation failed"
                    if hasattr(result, 'exception') and result.exception:
                        error_msg = str(result.exception)
                    
                    return CompilationResult(
                        success=False,
                        error=error_msg
                    )
            
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(model_file):
                        os.remove(model_file)
                except Exception:
                    pass
        
        except Exception as e:
            return CompilationResult(
                success=False,
                error=f"Compilation error: {str(e)}"
            )
    
    def debug(self) -> Dict[str, Any]:
        """
        Run dbt debug and return connection status
        
        Returns:
            Dictionary with debug information
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['debug'])
            
            return {
                'success': result.success,
                'connection_ok': result.success,
                'profile': self.config.profile,
                'error': None if result.success else "Debug failed"
            }
        except Exception as e:
            return {
                'success': False,
                'connection_ok': False,
                'profile': self.config.profile,
                'error': str(e)
            }
    
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
                # Extract model names from result
                models = []
                if hasattr(result, 'result') and result.result:
                    for node_result in result.result:
                        if hasattr(node_result, 'node') and hasattr(node_result.node, 'name'):
                            models.append(node_result.node.name)
                return models
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
    
    def test_model(self, model_name: Optional[str] = None) -> bool:
        """
        Run dbt tests
        
        Args:
            model_name: Optional specific model to test
            
        Returns:
            True if tests pass, False otherwise
        """
        try:
            dbt = self._get_dbt_runner()
            cmd_args = ['test']
            if model_name:
                cmd_args.extend(['--select', model_name])
            
            result = dbt.invoke(cmd_args)
            return result.success
        except Exception:
            return False
    
    def generate_docs(self) -> bool:
        """
        Generate dbt documentation
        
        Returns:
            True if successful, False otherwise
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['docs', 'generate'])
            return result.success
        except Exception:
            return False
    
    def serve_docs(self) -> bool:
        """
        Serve dbt documentation
        Note: This will start a server process
        
        Returns:
            True if successful, False otherwise
        """
        try:
            dbt = self._get_dbt_runner()
            result = dbt.invoke(['docs', 'serve'])
            return result.success
        except Exception:
            return False
    
    def _parse_dbt_show_output(self, dbt_result) -> Dict[str, Any]:
        """Parse dbt show output into structured data"""
        try:
            # First try to parse captured stdout output
            if hasattr(dbt_result, '_captured_stdout') and dbt_result._captured_stdout:
                parsed = self._parse_table_from_message(dbt_result._captured_stdout)
                if parsed['data'] or parsed['columns']:
                    return parsed
            
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
                        parsed = self._parse_table_from_message(str(node_result.message))
                        if parsed['data'] or parsed['columns']:
                            return parsed
            
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
    
    def _read_compiled_sql(self, model_name: str) -> Optional[str]:
        """Read compiled SQL from dbt target directory"""
        try:
            # Look for compiled SQL in target directory
            target_path = os.environ.get('DBT_TARGET_PATH', 'target')
            compiled_path = Path(target_path) / 'compiled' / 'qbot' / 'models' / f'{model_name}.sql'
            
            if compiled_path.exists():
                with open(compiled_path, 'r') as f:
                    return f.read()
            
            return None
        except Exception:
            return None


# Global service instance - will be initialized when needed
_dbt_service: Optional[DbtService] = None


def get_dbt_service(config: Optional[QBotConfig] = None) -> DbtService:
    """
    Get or create the global dbt service instance
    
    Args:
        config: Optional config to use for initialization
        
    Returns:
        DbtService instance
    """
    global _dbt_service
    
    if _dbt_service is None or (config and config != _dbt_service.config):
        if config is None:
            # Create default config
            config = QBotConfig()
        _dbt_service = DbtService(config)
    
    return _dbt_service

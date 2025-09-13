"""
Centralized dbt service for all programmatic dbt operations

This module provides a single, consistent interface for all dbt operations
throughout SQLBot, eliminating subprocess calls and providing structured results.
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from .types import QueryResult, QueryType, CompilationResult
from .config import SQLBotConfig


class DbtService:
    """Centralized service for all dbt operations"""
    
    def __init__(self, config: SQLBotConfig):
        self.config = config
        self._dbt_runner = None
        self._setup_environment()
        self._temp_dir = self._get_temp_directory()
    
    def _setup_logging_suppression(self):
        """Setup dbt logging suppression"""
        # This will be handled per-command with --log-level none
        pass
    
    def _setup_environment(self):
        """Setup environment variables for dbt"""
        env_vars = self.config.to_env_dict()
        for key, value in env_vars.items():
            os.environ[key] = value

        # Configure dbt to use local .dbt folder if it exists
        from .config import SQLBotConfig
        profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()
        os.environ['DBT_PROFILES_DIR'] = profiles_dir

        # Store detection result for banner/logging purposes
        self._is_using_local_dbt = is_local
        self._dbt_profiles_dir = profiles_dir

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
        """Get temporary directory for model files - must be in main models/ directory for dbt to find them"""
        # dbt looks for models in the models/ directory, so we must put temp files there
        models_dir = Path('models')
        models_dir.mkdir(parents=True, exist_ok=True)
        return str(models_dir)

    def get_dbt_config_info(self) -> dict:
        """
        Get information about current dbt configuration for display purposes.

        Returns:
            Dictionary with dbt configuration details
        """
        return {
            'is_using_local_dbt': getattr(self, '_is_using_local_dbt', False),
            'profiles_dir': getattr(self, '_dbt_profiles_dir', str(Path.home() / '.dbt')),
            'profile_name': self.config.profile
        }
    
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
        Execute SQL query using dbt SDK and return structured results
        
        Args:
            sql_query: The SQL query to execute
            limit: Optional limit on number of rows to return
            
        Returns:
            QueryResult with structured data
        """
        import time
        import os  # Move os import to top level
        start_time = time.time()
        
        try:
            # Clean query for execution
            clean_query = sql_query.strip().rstrip(';')
            
            # Fix common Jinja syntax issues - convert single braces to double braces for dbt functions
            import re
            # Only replace single braces that are NOT already double braces
            # Pattern: single { followed by function(...) followed by single } but NOT preceded/followed by another brace
            clean_query = re.sub(r'(?<!\{)\{\s*([a-zA-Z_][a-zA-Z0-9_]*\s*\([^}]*\))\s*\}(?!\})', r'{{ \1 }}', clean_query)
            # Specifically handle source() function calls
            clean_query = re.sub(r'(?<!\{)\{\s*(source\s*\([^}]*\))\s*\}(?!\})', r'{{ \1 }}', clean_query)
            
            # Debug output can be enabled by setting QBOT_DEBUG=1
            if os.environ.get('QBOT_DEBUG'):
                print(f"🔍 DEBUG: Original query: {sql_query}")
                print(f"🔍 DEBUG: Cleaned query: {clean_query}")
            
            # NEVER modify user queries - execute exactly as written
            # The limit parameter should not be used to modify queries
            
            # Detect macro calls and handle them differently
            from dbt.cli.main import dbtRunner
            import os
            
            # All queries use the same execution path - no special cases
            
            # Execute other queries using run-operation to avoid ANY automatic modifications
            
            # Suppress dbt performance info and unnecessary logging
            old_env_vars = {}
            env_suppressions = {
                'DBT_WRITE_PERF_INFO': 'false',
                'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'
            }
            
            for key, value in env_suppressions.items():
                old_env_vars[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                # Import subprocess and other modules at the top
                import subprocess
                import json
                import sys
                
                # First, try to compile the query to see what SQL dbt actually generates
                temp_model_name = f"qbot_debug_{int(time.time() * 1000)}"
                # Create temp model in profile-specific directory so dbt can find it
                profile_models_dir = Path(f"profiles/{self.config.profile}/models")
                profile_models_dir.mkdir(parents=True, exist_ok=True)
                temp_model_path = profile_models_dir / f"{temp_model_name}.sql"
                
                if os.environ.get('QBOT_DEBUG'):
                    print(f"🔍 DEBUG: Starting compilation for query: {clean_query[:100]}...")
                    print(f"🔍 DEBUG: Profile: {self.config.profile}")
                
                compiled_sql = None
                try:
                    # Write query to temporary model file for compilation
                    with open(temp_model_path, 'w') as f:
                        f.write(clean_query)
                    
                    # Try to compile to get the actual SQL
                    compile_cmd = [
                        "dbt", "compile", "--select", temp_model_name,
                        "--profile", self.config.profile
                    ]
                    
                    compile_result = subprocess.run(compile_cmd, capture_output=True, text=True, cwd=os.getcwd())
                    
                    if compile_result.returncode == 0:
                        # Small delay to ensure file is fully written
                        import time
                        time.sleep(0.1)
                        # Try to read the compiled SQL
                        compiled_sql = self._read_compiled_sql(temp_model_name)
                        if os.environ.get('QBOT_DEBUG'):
                            print(f"🔍 DEBUG: Compilation succeeded")
                            print(f"🔍 DEBUG: Compiled SQL: {compiled_sql[:100] if compiled_sql else 'None'}...")
                            if not compiled_sql:
                                print(f"🔍 DEBUG: Could not read compiled SQL for {temp_model_name}")
                                # Show compilation output for debugging
                                print(f"🔍 DEBUG: Compile stdout: {compile_result.stdout[:200]}...")
                                print(f"🔍 DEBUG: Compile stderr: {compile_result.stderr[:200]}...")
                    else:
                        # Compilation failed - capture the error for the LLM
                        compilation_error = compile_result.stderr.strip() or compile_result.stdout.strip()
                        if os.environ.get('QBOT_DEBUG'):
                            print(f"🔍 DEBUG: dbt compilation failed for profile {self.config.profile}: {compilation_error}")
                        
                        # Return compilation error immediately so LLM can see it
                        execution_time = time.time() - start_time
                        error_msg = f"dbt compilation failed: {compilation_error}"
                        if clean_query != sql_query:
                            error_msg = f"Original Query: {sql_query} | Cleaned Query: {clean_query} | {error_msg}"
                        
                        return QueryResult(
                            success=False,
                            query_type=QueryType.SQL,
                            execution_time=execution_time,
                            error=error_msg
                        )
                except Exception as e:
                    if os.environ.get('QBOT_DEBUG'):
                        print(f"🔍 DEBUG: Exception during compilation: {e}")
                    pass  # Compilation failed, continue with execution
                finally:
                    # Clean up temp file
                    try:
                        if temp_model_path.exists():
                            temp_model_path.unlink()
                    except Exception:
                        pass
                
                # Use dbt run-operation with our custom macro to execute queries without modification
                # We need to capture stdout since that's where the log messages go
                
                # If we have compiled SQL, use that; otherwise use the original query
                query_to_execute = compiled_sql if compiled_sql else clean_query
                
                if os.environ.get('QBOT_DEBUG'):
                    print(f"🔍 DEBUG: Query to execute: {query_to_execute[:100] if query_to_execute else 'None'}...")
                    print(f"🔍 DEBUG: Using compiled SQL: {bool(compiled_sql)}")
                
                # Execute dbt run-operation directly
                query_json = json.dumps({"query": query_to_execute})
                
                cmd = [
                    "dbt", "run-operation", "execute_raw_query",
                    "--args", query_json,
                    "--profile", self.config.profile
                ]
                
                cmd_result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
                
                # Create a mock result object
                # Combine stdout and stderr for error messages since dbt can put errors in either
                combined_error = ""
                if cmd_result.returncode != 0:
                    error_parts = []
                    if cmd_result.stderr and cmd_result.stderr.strip():
                        error_parts.append(f"STDERR: {cmd_result.stderr.strip()}")
                    if cmd_result.stdout and cmd_result.stdout.strip():
                        error_parts.append(f"STDOUT: {cmd_result.stdout.strip()}")
                    combined_error = " | ".join(error_parts) if error_parts else "Unknown dbt error"
                
                result = type('Result', (), {
                    'success': cmd_result.returncode == 0,
                    'stdout': cmd_result.stdout,
                    'stderr': cmd_result.stderr,
                    'exception': None if cmd_result.returncode == 0 else Exception(combined_error),
                    'compiled_sql': compiled_sql  # Add the compiled SQL to the result
                })()
            finally:
                # Restore environment variables
                for key, old_value in old_env_vars.items():
                    if old_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old_value
            
            execution_time = time.time() - start_time
            
            if result.success:
                # Extract data from run-operation macro output
                parsed_data = self._extract_macro_output(result)
                
                return QueryResult(
                    success=True,
                    query_type=QueryType.SQL,
                    execution_time=execution_time,
                    data=parsed_data['data'],
                    columns=parsed_data['columns'],
                    row_count=len(parsed_data['data'])
                )
            else:
                # Extract detailed error message from dbt output and include compiled SQL
                compiled_sql_from_result = getattr(result, 'compiled_sql', None)
                # Use the compiled SQL we generated earlier if available
                final_compiled_sql = compiled_sql if compiled_sql else compiled_sql_from_result
                
                error_msg = self._extract_detailed_error_message(result, clean_query, final_compiled_sql)
                
                # Include original vs cleaned query info if they differ
                if clean_query != sql_query:
                    error_msg = f"Original Query: {sql_query} | Cleaned Query: {clean_query} | {error_msg}"
                
                return QueryResult(
                    success=False,
                    query_type=QueryType.SQL,
                    execution_time=execution_time,
                    error=error_msg
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                execution_time=execution_time,
                error=f"Execution error: {str(e)}"
            )
    
    def compile_query_preview(self, sql_query: str) -> CompilationResult:
        """
        Compile SQL query for preview using dbt SDK (without execution)
        
        Args:
            sql_query: The SQL query to compile
            
        Returns:
            CompilationResult with compiled SQL for preview
        """
        try:
            # Clean query for compilation
            clean_query = sql_query.strip().rstrip(';')
            
            # Use dbt SDK for Jinja compilation
            from dbt.clients.jinja import get_rendered
            from dbt.config import RuntimeConfig
            
            # Load dbt configuration to get context with required parameters
            from pathlib import Path
            from dbt.config.renderer import DbtProjectYamlRenderer
            
            project_root = Path('.').resolve()
            renderer = DbtProjectYamlRenderer(None)
            config = RuntimeConfig.from_project_root(
                project_root=str(project_root),
                renderer=renderer
            )
            
            # Get basic context for Jinja rendering
            # For simple queries, this will render {{ }} macros
            context = {
                'var': lambda x, default=None: config.vars.get(x, default),
                'env_var': lambda x, default=None: os.environ.get(x, default),
            }
            
            # Render Jinja templates in the SQL
            compiled_sql = get_rendered(clean_query, context)
            
            return CompilationResult(
                success=True,
                compiled_sql=compiled_sql
            )
            
        except Exception as e:
            return CompilationResult(
                success=False,
                error=f"Compilation error: {str(e)}"
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
    
    def _execute_macro_with_show(self, macro_query: str, limit: Optional[int] = None) -> QueryResult:
        """Execute macro calls using dbt show to get actual results"""
        try:
            # Create a temporary model file with the macro call
            import tempfile
            import os
            import subprocess
            import time
            
            # Create temp model content
            model_content = macro_query.strip()
            
            # Create temporary model file
            temp_model_name = f"qbot_macro_temp_{int(time.time() * 1000000)}"
            temp_model_path = f"profiles/{self.config.profile}/models/{temp_model_name}.sql"
            
            # Ensure the models directory exists
            os.makedirs(os.path.dirname(temp_model_path), exist_ok=True)
            
            try:
                # Write the temporary model file
                with open(temp_model_path, 'w') as f:
                    f.write(model_content)
                
                # Execute using dbt show with wide printer width to avoid truncation
                cmd = [
                    "dbt", "show", 
                    "--select", temp_model_name,
                    "--profile", self.config.profile,
                    "--printer-width", "10000"  # Very wide to avoid truncation
                ]
                
                if limit:
                    cmd.extend(["--limit", str(limit)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    # Parse the dbt show output to extract the data
                    return self._parse_dbt_show_output(result.stdout, macro_query)
                else:
                    # Return error result
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    return QueryResult(
                        success=False,
                        query_type=QueryType.SQL,
                        error=f"Macro execution failed: {error_msg}",
                        execution_time=0.0
                    )
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_model_path):
                    os.remove(temp_model_path)
                    
        except Exception as e:
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                error=f"Macro execution error: {str(e)}",
                execution_time=0.0
            )
    
    def _parse_dbt_show_output(self, stdout: str, original_query: str) -> QueryResult:
        """Parse dbt show output to extract structured data"""
        try:
            import time
            start_time = time.time()
            
            lines = stdout.split('\n')
            data_started = False
            headers = []
            rows = []
            
            for line in lines:
                line = line.strip()
                
                # Look for the table header (starts with |)
                if line.startswith('|') and not data_started:
                    # This is the header row
                    headers = [col.strip() for col in line.split('|')[1:-1]]  # Remove empty first/last elements
                    data_started = True
                    continue
                elif line.startswith('|') and data_started and not line.startswith('|-'):
                    # This is a data row (skip separator lines that start with |-)
                    row_values = [col.strip() for col in line.split('|')[1:-1]]
                    if len(row_values) == len(headers):
                        # Create row dict
                        row_dict = {headers[i]: row_values[i] for i in range(len(headers))}
                        rows.append(row_dict)
            
            execution_time = time.time() - start_time
            
            return QueryResult(
                success=True,
                query_type=QueryType.SQL,
                data=rows,
                columns=headers,
                row_count=len(rows),
                execution_time=execution_time
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                query_type=QueryType.SQL,
                error=f"Failed to parse dbt show output: {str(e)}",
                execution_time=0.0
            )

    def _extract_dbt_show_data(self, dbt_result) -> Dict[str, Any]:
        """Extract structured data from dbt show result objects"""
        try:
            # For dbt show --inline, the result should contain agate.Table objects
            if hasattr(dbt_result, 'result') and dbt_result.result:
                # dbt show returns a RunResults object with results array
                if hasattr(dbt_result.result, 'results') and dbt_result.result.results:
                    for run_result in dbt_result.result.results:
                        # Check for agate.Table in adapter_response
                        if hasattr(run_result, 'adapter_response') and run_result.adapter_response:
                            adapter_response = run_result.adapter_response
                            # The agate.Table might be stored in the response
                            if hasattr(adapter_response, '_data') or hasattr(adapter_response, 'data'):
                                # Extract table data from adapter response
                                data_attr = getattr(adapter_response, '_data', getattr(adapter_response, 'data', None))
                                if data_attr:
                                    # Convert agate.Table to our format
                                    return self._extract_agate_table_data(data_attr)
                        
                        # Check if the result contains agate.Table directly
                        if hasattr(run_result, 'agate_table'):
                            table = run_result.agate_table
                            return self._extract_agate_table_data(table)
                
                # For older dbt versions, check if result is directly the table data
                if hasattr(dbt_result.result, 'column_names') and hasattr(dbt_result.result, 'rows'):
                    return {
                        'data': [dict(zip(dbt_result.result.column_names, row)) for row in dbt_result.result.rows],
                        'columns': list(dbt_result.result.column_names)
                    }
            
            # Fallback to parsing message output
            if hasattr(dbt_result, 'result') and dbt_result.result:
                if hasattr(dbt_result.result, 'results') and dbt_result.result.results:
                    for run_result in dbt_result.result.results:
                        if hasattr(run_result, 'message') and run_result.message:
                            parsed = self._parse_table_from_message(str(run_result.message))
                            if parsed['data'] or parsed['columns']:
                                return parsed
            
            # If no structured data found, return empty
            return {'data': [], 'columns': []}
            
        except Exception as e:
            return {'data': [], 'columns': []}
    
    def _extract_agate_table_data(self, table) -> Dict[str, Any]:
        """Extract data from agate.Table object"""
        try:
            if table is None:
                return {'data': [], 'columns': []}
            
            # Get column names
            columns = []
            if hasattr(table, 'column_names'):
                columns = list(table.column_names)
            elif hasattr(table, 'columns'):
                columns = [col.name if hasattr(col, 'name') else str(col) for col in table.columns]
            
            # Get row data and serialize values to handle Decimal objects
            rows = []
            if hasattr(table, 'rows'):
                for row in table.rows:
                    if columns:
                        row_dict = {columns[i]: self._serialize_value(row[i]) for i in range(min(len(columns), len(row)))}
                        rows.append(row_dict)
                    else:
                        rows.append([self._serialize_value(val) for val in row])
            
            return {
                'data': rows,
                'columns': columns
            }
            
        except Exception as e:
            return {'data': [], 'columns': []}
    
    def _serialize_value(self, value):
        """Convert non-JSON-serializable values to serializable ones"""
        from decimal import Decimal
        import datetime
        
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, datetime.datetime):
            return value.isoformat()
        elif isinstance(value, datetime.date):
            return value.isoformat()
        else:
            return value
    
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
    
    def _extract_macro_output(self, dbt_result) -> Dict[str, Any]:
        """Extract result from run-operation macro output - ONE method for ALL queries"""
        try:
            # Parse stdout from the subprocess execution
            stdout = getattr(dbt_result, 'stdout', '')
            
            # Extract ROW_DATA and COLUMN_NAMES from stdout
            row_data = []
            columns = []
            
            # Check if this is a DML operation first
            is_dml = any('DML_SUCCESS=' in line for line in stdout.split('\n'))
            
            lines = stdout.split('\n')
            for line in lines:
                if 'ROW_DATA=' in line:
                    # Extract row data
                    data_part = line.split('ROW_DATA=')[1].strip()
                    if data_part:
                        row_values = data_part.split('|') if '|' in data_part else [data_part]
                        row_data.append(row_values)
                elif 'COLUMN_NAMES=' in line:
                    # Extract column names
                    columns_part = line.split('COLUMN_NAMES=')[1].strip()
                    if columns_part:
                        columns = columns_part.split('|') if '|' in columns_part else [columns_part]
            
            # Convert to structured data
            structured_data = []
            if columns and row_data:
                for row in row_data:
                    if len(row) == len(columns):
                        row_dict = {columns[i]: row[i] for i in range(len(columns))}
                        structured_data.append(row_dict)
            
            return {
                'data': structured_data,
                'columns': columns
            }
                
        except Exception as e:
            return {'data': [], 'columns': []}
    
    def _extract_detailed_error_message(self, dbt_result, original_query: str = None, compiled_sql: str = None) -> str:
        """Extract detailed error message from dbt output, including actual database errors"""
        try:
            # Get both stdout and stderr
            stdout = getattr(dbt_result, 'stdout', '')
            stderr = getattr(dbt_result, 'stderr', '')
            
            # Look for specific error patterns in the output
            error_parts = []
            
            # Include the original query that failed for context
            if original_query:
                error_parts.append(f"Original Query: {original_query}")
            
            # Include the compiled SQL if available
            if compiled_sql and compiled_sql != original_query:
                error_parts.append(f"Compiled SQL: {compiled_sql}")
            
            # Capture ALL error-related content from dbt output
            if stdout:
                lines = stdout.split('\n')
                error_started = False
                
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    
                    # Start capturing when we see any error indicator
                    if any(error_marker in line for error_marker in [
                        'Database Error', 'Encountered an error', 'Compilation Error', 
                        'Runtime Error', 'Connection Error', 'ERROR', 'FAILED'
                    ]):
                        error_started = True
                        error_parts.append(line_stripped)
                        
                        # Capture the next several lines for full context
                        for j in range(i + 1, min(i + 10, len(lines))):
                            next_line = lines[j].strip()
                            if next_line:
                                error_parts.append(next_line)
                                # Stop if we hit a new log timestamp or operation
                                if any(marker in next_line for marker in ['Running with dbt', 'Registered adapter', 'Found']):
                                    break
                        break  # Stop after finding the first error block
                    
                    # Also capture any line with obvious error content
                    elif any(error_content in line for error_content in [
                        'ODBC Driver', 'SQLExecDirectW', 'permission violation', 
                        'syntax error', 'does not exist', 'not found', 'invalid'
                    ]):
                        error_parts.append(line_stripped)
                    
                    # Capture the actual query being executed for debugging
                    elif 'EXECUTING_QUERY=' in line:
                        executed_query = line.split('EXECUTING_QUERY=')[1].strip()
                        error_parts.append(f"Executed SQL: {executed_query}")
            
            # Check stderr for additional error info
            if stderr and stderr.strip():
                error_parts.append(f"STDERR: {stderr.strip()}")
            
            # If we found specific errors, use them
            if error_parts:
                # Remove duplicates while preserving order
                unique_parts = []
                seen = set()
                for part in error_parts:
                    if part not in seen:
                        unique_parts.append(part)
                        seen.add(part)
                return ' | '.join(unique_parts)
            
            # If no specific errors found, include the full stdout for debugging
            if stdout and stdout.strip():
                return f"Full dbt output: {stdout.strip()}"
            
            # Fallback to the original exception message
            if hasattr(dbt_result, 'exception') and dbt_result.exception:
                return str(dbt_result.exception)
            
            # Final fallback
            return "Query execution failed - no detailed error information available"
            
        except Exception as e:
            return f"Error extracting error details: {str(e)}"
    
    def _read_compiled_sql(self, model_name: str) -> Optional[str]:
        """Read compiled SQL from dbt target directory"""
        import os  # Import os for this method
        try:
            # Look for compiled SQL in target directory - try both root and profile-specific paths
            possible_paths = [
                Path('target') / 'compiled' / 'sqlbot' / 'models' / f'{model_name}.sql',  # Root target
                Path(f'profiles/{self.config.profile}/target') / 'compiled' / 'sqlbot' / 'models' / f'{model_name}.sql',  # Profile target
                Path(os.environ.get('DBT_TARGET_PATH', 'target')) / 'compiled' / 'sqlbot' / 'models' / f'{model_name}.sql'  # Env var target
            ]
            
            for compiled_path in possible_paths:
                if os.environ.get('QBOT_DEBUG'):
                    print(f"🔍 DEBUG: Checking for compiled SQL at: {compiled_path}")
                if compiled_path.exists():
                    if os.environ.get('QBOT_DEBUG'):
                        print(f"🔍 DEBUG: Found compiled SQL at: {compiled_path}")
                    try:
                        with open(compiled_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if os.environ.get('QBOT_DEBUG'):
                                print(f"🔍 DEBUG: File content length: {len(content)}")
                                print(f"🔍 DEBUG: File content preview: {content[:100]}...")
                            return content
                    except Exception as e:
                        if os.environ.get('QBOT_DEBUG'):
                            print(f"🔍 DEBUG: Error reading file: {e}")
                        continue
            
            # If not found, search more broadly
            if os.environ.get('QBOT_DEBUG'):
                print(f"🔍 DEBUG: Compiled SQL not found in expected locations, searching...")
            for target_dir in ['target', f'profiles/{self.config.profile}/target']:
                if Path(target_dir).exists():
                    for item in Path(target_dir).rglob('*'):
                        if model_name in str(item) and item.suffix == '.sql':
                            if os.environ.get('QBOT_DEBUG'):
                                print(f"🔍 DEBUG: Found matching file: {item}")
                            try:
                                with open(item, 'r', encoding='utf-8') as f:
                                    content = f.read().strip()
                                    if os.environ.get('QBOT_DEBUG'):
                                        print(f"🔍 DEBUG: File content length: {len(content)}")
                                        print(f"🔍 DEBUG: File content preview: {content[:100]}...")
                                    return content
                            except Exception as e:
                                if os.environ.get('QBOT_DEBUG'):
                                    print(f"🔍 DEBUG: Error reading file: {e}")
                                return None
            
            return None
        except Exception:
            return None


# Global service instance - will be initialized when needed
_dbt_service: Optional[DbtService] = None


def get_dbt_service(config: Optional[SQLBotConfig] = None) -> DbtService:
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
            config = SQLBotConfig()
        _dbt_service = DbtService(config)
    
    return _dbt_service

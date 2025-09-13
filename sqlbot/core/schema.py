"""
Schema and macro loading for SQLBot Core SDK

This module handles dbt schema discovery and macro loading independent of UI.
"""

import os
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from .types import TableInfo, ProfileInfo


class SchemaLoader:
    """Handles loading of dbt schemas and macros"""
    
    def __init__(self, profile_name: str = "qbot"):
        self.profile_name = profile_name
    
    def get_profile_paths(self) -> Tuple[List[str], List[str]]:
        """
        Get profile-specific paths for schema and macro files
        
        Returns:
            Tuple of (schema_paths, macro_paths) in priority order
        """
        schema_paths = []
        macro_paths = []
        
        # Priority 1: .sqlbot/profiles/{profile}/
        qbot_profile_dir = Path('.sqlbot/profiles') / self.profile_name
        if qbot_profile_dir.exists():
            schema_paths.append(str(qbot_profile_dir / 'models' / 'schema.yml'))
            macro_paths.append(str(qbot_profile_dir / 'macros'))
        
        # Priority 2: profiles/{profile}/
        profiles_dir = Path('profiles') / self.profile_name
        if profiles_dir.exists():
            schema_paths.append(str(profiles_dir / 'models' / 'schema.yml'))
            macro_paths.append(str(profiles_dir / 'macros'))
        
        # Priority 3: Legacy models/schema.yml
        schema_paths.append('models/schema.yml')
        macro_paths.append('macros')
        
        return schema_paths, macro_paths
    
    def load_schema_info(self) -> Dict[str, Any]:
        """
        Load schema information from profile-specific or default locations
        
        Returns:
            Dictionary containing schema information
        """
        schema_paths, _ = self.get_profile_paths()
        
        for schema_path in schema_paths:
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, 'r') as f:
                        schema_data = yaml.safe_load(f)
                    
                    # Ensure schema is available to dbt by copying to models/
                    self._ensure_schema_available_to_dbt(schema_path)
                    
                    return schema_data
                except Exception as e:
                    print(f"Warning: Could not load schema from {schema_path}: {e}")
                    continue
        
        return {'version': 2, 'sources': []}
    
    def load_macro_info(self) -> List[Dict[str, Any]]:
        """
        Load macro information from profile-specific or default locations
        
        Returns:
            List of macro information dictionaries
        """
        _, macro_paths = self.get_profile_paths()
        macros = []
        
        for macro_path in macro_paths:
            if os.path.exists(macro_path):
                try:
                    for file_path in Path(macro_path).glob('*.sql'):
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # Extract macro names (simple regex)
                        import re
                        macro_names = re.findall(r'{%\s*macro\s+(\w+)', content)
                        
                        for macro_name in macro_names:
                            macros.append({
                                'name': macro_name,
                                'file': str(file_path),
                                'content': content
                            })
                except Exception as e:
                    print(f"Warning: Could not load macros from {macro_path}: {e}")
                    continue
        
        return macros
    
    def get_tables(self) -> List[TableInfo]:
        """
        Get list of available tables from schema
        
        Returns:
            List of TableInfo objects
        """
        schema_data = self.load_schema_info()
        tables = []
        
        for source in schema_data.get('sources', []):
            source_name = source.get('name', 'unknown')
            schema_name = source.get('schema', 'dbo')
            
            for table in source.get('tables', []):
                table_info = TableInfo(
                    name=table.get('name', 'unknown'),
                    schema=schema_name,
                    description=table.get('description', ''),
                    source_name=source_name
                )
                
                # Add column information if available
                columns = []
                for column in table.get('columns', []):
                    columns.append({
                        'name': column.get('name', ''),
                        'description': column.get('description', ''),
                        'data_type': column.get('data_type', '')
                    })
                table_info.columns = columns
                
                tables.append(table_info)
        
        return tables
    
    def get_profile_info(self) -> ProfileInfo:
        """
        Get information about the current profile
        
        Returns:
            ProfileInfo object with profile details
        """
        schema_paths, macro_paths = self.get_profile_paths()
        
        # Find the active schema path
        active_schema_path = None
        for path in schema_paths:
            if os.path.exists(path):
                active_schema_path = path
                break
        
        # Find existing macro paths
        existing_macro_paths = [path for path in macro_paths if os.path.exists(path)]
        
        return ProfileInfo(
            name=self.profile_name,
            target="default",  # Could be enhanced to read from profiles.yml
            schema_path=active_schema_path,
            macro_paths=existing_macro_paths,
            tables=self.get_tables()
        )
    
    def _ensure_schema_available_to_dbt(self, schema_path: str):
        """
        Verify schema file is accessible to dbt.
        With profile-specific dbt configuration, no copying is needed.
        
        Args:
            schema_path: Path to the schema file to verify
        """
        if os.path.exists(schema_path):
            print(f"✅ Schema available at: {schema_path}")
        else:
            print(f"⚠️ Schema not found at: {schema_path}")


# Global loader instance for backward compatibility
_default_loader = SchemaLoader()


def get_profile_paths(profile_name: str) -> Tuple[List[str], List[str]]:
    """Get profile paths (backward compatible function)"""
    loader = SchemaLoader(profile_name)
    return loader.get_profile_paths()


def load_schema_info(profile_name: str = "qbot") -> Dict[str, Any]:
    """Load schema info (backward compatible function)"""
    loader = SchemaLoader(profile_name)
    return loader.load_schema_info()


def load_macro_info(profile_name: str = "qbot") -> List[Dict[str, Any]]:
    """Load macro info (backward compatible function)"""
    loader = SchemaLoader(profile_name)
    return loader.load_macro_info()

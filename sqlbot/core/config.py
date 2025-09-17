"""
Configuration management for SQLBot Core SDK
"""

import os
from typing import Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from .types import LLMConfig

from dotyaml import load_config

@dataclass
class SQLBotConfig:
    """Configuration for SQLBot agent"""
    
    # dbt configuration - all database connection info comes from dbt profiles
    profile: str = None
    target: Optional[str] = None
    
    # LLM configuration
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Safety configuration
    dangerous: bool = False
    preview_mode: bool = False
    
    # Execution configuration
    query_timeout: int = 60
    max_rows: int = 1000
    
    @staticmethod
    def detect_dbt_profiles_dir() -> Tuple[str, bool]:
        """
        Detect dbt profiles directory with local .dbt folder support.

        Returns:
            Tuple of (profiles_dir_path, is_local) where:
            - profiles_dir_path: Path to the profiles directory to use
            - is_local: True if using local .dbt folder, False if using global ~/.dbt
        """
        # Check for local .dbt folder first
        local_dbt_dir = Path('.dbt')
        local_profiles_file = local_dbt_dir / 'profiles.yml'

        if local_profiles_file.exists():
            return str(local_dbt_dir.resolve()), True

        # Fall back to global ~/.dbt folder
        home_dbt_dir = Path.home() / '.dbt'
        return str(home_dbt_dir), False

    @staticmethod
    def load_dbt_profiles_with_dotyaml() -> bool:
        """
        Load dbt profiles.yml file using dotyaml to resolve environment variables.

        This processes the profiles.yml file and sets any interpolated environment
        variables that dbt will need.

        Returns:
            bool: True if profiles were loaded successfully, False otherwise
        """
        profiles_dir, _ = SQLBotConfig.detect_dbt_profiles_dir()
        profiles_file = Path(profiles_dir) / 'profiles.yml'

        if not profiles_file.exists():
            return False

        try:
            # Load the profiles.yml with dotyaml to process environment variable interpolation
            load_config(str(profiles_file))
            return True
        except Exception as e:
            # Debug: print the exception to see what's failing
            print(f"DEBUG: dotyaml loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def load_yaml_config() -> bool:
        """
        Load configuration from .sqlbot/config.yml file using dotyaml.

        Returns:
            bool: True if YAML config was loaded successfully, False otherwise
        """
        config_file = Path('.sqlbot/config.yml')
        if not config_file.exists():
            return False

        try:
            load_config(str(config_file), prefix='SQLBOT')
            return True
        except Exception:
            return False

    @classmethod
    def from_env(cls, profile: Optional[str] = None) -> 'SQLBotConfig':
        """Create configuration from environment variables and YAML config"""

        # Try to load YAML configuration first (this sets environment variables)
        cls.load_yaml_config()

        # Also load dbt profiles.yml with dotyaml to resolve environment variables
        cls.load_dbt_profiles_with_dotyaml()

        # LLM configuration from environment (may be set by YAML config)
        llm_config = LLMConfig(
            model=os.getenv('SQLBOT_LLM_MODEL', 'gpt-5'),
            max_tokens=int(os.getenv('SQLBOT_LLM_MAX_TOKENS', '50000')),
            temperature=float(os.getenv('SQLBOT_LLM_TEMPERATURE', '0.1')),
            verbosity=os.getenv('SQLBOT_LLM_VERBOSITY', 'low'),
            effort=os.getenv('SQLBOT_LLM_EFFORT', 'minimal'),
            api_key=os.getenv('OPENAI_API_KEY'),
            provider=os.getenv('SQLBOT_LLM_PROVIDER', 'openai')
        )

        # Handle profile priority: command line > config file > environment
        config_profile = profile or os.getenv('SQLBOT_DATABASE_PROFILE') or os.getenv('SQLBOT_PROFILE') or os.getenv('DBT_PROFILE_NAME')

        # Handle safety settings from config file
        safety_dangerous = os.getenv('SQLBOT_SAFETY_DANGEROUS', os.getenv('SQLBOT_DANGEROUS', '')).lower() in ('true', '1', 'yes')
        safety_preview_mode = os.getenv('SQLBOT_SAFETY_PREVIEW_MODE', os.getenv('SQLBOT_PREVIEW_MODE', '')).lower() in ('true', '1', 'yes')

        # Handle query settings from config file
        query_timeout = int(os.getenv('SQLBOT_QUERY_TIMEOUT', '60'))
        max_rows = int(os.getenv('SQLBOT_QUERY_MAX_ROWS', os.getenv('SQLBOT_MAX_ROWS', '1000')))

        return cls(
            profile=config_profile,
            target=os.getenv('SQLBOT_TARGET', os.getenv('DBT_TARGET')),
            llm=llm_config,
            dangerous=safety_dangerous,
            preview_mode=safety_preview_mode,
            query_timeout=query_timeout,
            max_rows=max_rows
        )
    
    def to_env_dict(self) -> dict:
        """Convert configuration to environment variables dictionary"""
        env_vars = {}
        
        if self.profile:
            env_vars['DBT_PROFILE_NAME'] = self.profile
        if self.target:
            env_vars['DBT_TARGET'] = self.target
        # Database credentials come from dbt profiles, not environment variables
            
        # LLM configuration
        env_vars['SQLBOT_LLM_MODEL'] = self.llm.model
        env_vars['SQLBOT_LLM_MAX_TOKENS'] = str(self.llm.max_tokens)
        env_vars['SQLBOT_LLM_TEMPERATURE'] = str(self.llm.temperature)
        env_vars['SQLBOT_LLM_VERBOSITY'] = self.llm.verbosity
        env_vars['SQLBOT_LLM_EFFORT'] = self.llm.effort
        env_vars['SQLBOT_LLM_PROVIDER'] = self.llm.provider
        if self.llm.api_key:
            env_vars['OPENAI_API_KEY'] = self.llm.api_key

        # Other configuration
        env_vars['SQLBOT_DANGEROUS'] = str(self.dangerous).lower()
        env_vars['SQLBOT_PREVIEW_MODE'] = str(self.preview_mode).lower()
        env_vars['SQLBOT_QUERY_TIMEOUT'] = str(self.query_timeout)
        env_vars['SQLBOT_MAX_ROWS'] = str(self.max_rows)
        
        return env_vars
    
    def apply_to_env(self):
        """Apply configuration to current environment"""
        env_dict = self.to_env_dict()
        for key, value in env_dict.items():
            os.environ[key] = value

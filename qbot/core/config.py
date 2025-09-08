"""
Configuration management for QBot Core SDK
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from .types import LLMConfig


@dataclass
class QBotConfig:
    """Configuration for QBot agent"""
    
    # dbt configuration - all database connection info comes from dbt profiles
    profile: str = "qbot"
    target: Optional[str] = None
    
    # LLM configuration
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Safety configuration
    read_only: bool = False
    preview_mode: bool = False
    
    # Execution configuration
    query_timeout: int = 60
    max_rows: int = 1000
    
    @classmethod
    def from_env(cls, profile: Optional[str] = None) -> 'QBotConfig':
        """Create configuration from environment variables"""
        
        # LLM configuration from environment
        llm_config = LLMConfig(
            model=os.getenv('QBOT_LLM_MODEL', 'gpt-5'),
            max_tokens=int(os.getenv('QBOT_LLM_MAX_TOKENS', '10000')),
            temperature=float(os.getenv('QBOT_LLM_TEMPERATURE', '0.1')),
            verbosity=os.getenv('QBOT_LLM_VERBOSITY', 'low'),
            effort=os.getenv('QBOT_LLM_EFFORT', 'minimal'),
            api_key=os.getenv('OPENAI_API_KEY'),
            provider=os.getenv('QBOT_LLM_PROVIDER', 'openai')
        )
        
        return cls(
            profile=profile or os.getenv('DBT_PROFILE_NAME', 'qbot'),
            target=os.getenv('DBT_TARGET'),
            llm=llm_config,
            read_only=os.getenv('QBOT_READ_ONLY', '').lower() in ('true', '1', 'yes'),
            preview_mode=os.getenv('QBOT_PREVIEW_MODE', '').lower() in ('true', '1', 'yes'),
            query_timeout=int(os.getenv('QBOT_QUERY_TIMEOUT', '60')),
            max_rows=int(os.getenv('QBOT_MAX_ROWS', '1000'))
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
        env_vars['QBOT_LLM_MODEL'] = self.llm.model
        env_vars['QBOT_LLM_MAX_TOKENS'] = str(self.llm.max_tokens)
        env_vars['QBOT_LLM_TEMPERATURE'] = str(self.llm.temperature)
        env_vars['QBOT_LLM_VERBOSITY'] = self.llm.verbosity
        env_vars['QBOT_LLM_EFFORT'] = self.llm.effort
        env_vars['QBOT_LLM_PROVIDER'] = self.llm.provider
        if self.llm.api_key:
            env_vars['OPENAI_API_KEY'] = self.llm.api_key
            
        # Other configuration
        env_vars['QBOT_READ_ONLY'] = str(self.read_only).lower()
        env_vars['QBOT_PREVIEW_MODE'] = str(self.preview_mode).lower()
        env_vars['QBOT_QUERY_TIMEOUT'] = str(self.query_timeout)
        env_vars['QBOT_MAX_ROWS'] = str(self.max_rows)
        
        return env_vars
    
    def apply_to_env(self):
        """Apply configuration to current environment"""
        env_dict = self.to_env_dict()
        for key, value in env_dict.items():
            os.environ[key] = value

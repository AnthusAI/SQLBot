"""
Unit tests for SQLBot Core SDK Configuration
"""

import os
import pytest
from unittest.mock import patch
from sqlbot.core.config import SQLBotConfig
from sqlbot.core.types import LLMConfig


class TestSQLBotConfig:
    """Test SQLBot configuration functionality"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = SQLBotConfig()
        
        assert config.profile == None
        assert config.target is None
        assert config.dangerous == False
        assert config.preview_mode == False
        assert config.query_timeout == 60
        assert config.max_rows == 1000
        
        # Test LLM defaults
        assert config.llm.model == "gpt-5"
        assert config.llm.max_tokens == 50000
        assert config.llm.temperature == 0.1
        assert config.llm.provider == "openai"
    
    def test_config_from_env(self):
        """Test creating configuration from environment variables"""
        env_vars = {
            'DBT_PROFILE_NAME': 'test_profile',
            'DBT_TARGET': 'test_target',
            'DB_SERVER': 'localhost',
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser',
            'DB_PASS': 'testpass',
            'SQLBOT_LLM_MODEL': 'gpt-5',
            'SQLBOT_LLM_MAX_TOKENS': '2000',
            'SQLBOT_LLM_TEMPERATURE': '0.2',
            'OPENAI_API_KEY': 'test-api-key',
            'SQLBOT_DANGEROUS': 'true',
            'SQLBOT_PREVIEW_MODE': 'yes',
            'SQLBOT_QUERY_TIMEOUT': '120',
            'SQLBOT_MAX_ROWS': '500'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SQLBotConfig.from_env()
            
            assert config.profile == 'test_profile'
            assert config.target == 'test_target'
            # Database credentials now come from dbt profiles, not environment variables
            assert config.dangerous == True
            assert config.preview_mode == True
            assert config.query_timeout == 120
            assert config.max_rows == 500
            
            # Test LLM config
            assert config.llm.model == 'gpt-5'
            assert config.llm.max_tokens == 2000
            assert config.llm.temperature == 0.2
            assert config.llm.api_key == 'test-api-key'
    
    def test_profile_override(self):
        """Test profile override in from_env"""
        with patch.dict(os.environ, {'DBT_PROFILE_NAME': 'env_profile'}):
            config = SQLBotConfig.from_env(profile='override_profile')
            assert config.profile == 'override_profile'
    
    def test_boolean_env_parsing(self):
        """Test boolean environment variable parsing"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('', False),
            ('random', False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'SQLBOT_DANGEROUS': env_value}):
                config = SQLBotConfig.from_env()
                assert config.dangerous == expected, f"'{env_value}' should parse to {expected}"
    
    def test_to_env_dict(self):
        """Test converting configuration to environment dictionary"""
        config = SQLBotConfig(
            profile='test_profile',
            target='test_target',
            dangerous=True,
            preview_mode=False
        )
        config.llm.api_key = 'test-key'
        
        env_dict = config.to_env_dict()
        
        assert env_dict['DBT_PROFILE_NAME'] == 'test_profile'
        assert env_dict['DBT_TARGET'] == 'test_target'
        # Database credentials come from dbt profiles, not environment variables
        assert env_dict['SQLBOT_DANGEROUS'] == 'true'
        assert env_dict['SQLBOT_PREVIEW_MODE'] == 'false'
        assert env_dict['OPENAI_API_KEY'] == 'test-key'
    
    def test_apply_to_env(self):
        """Test applying configuration to current environment"""
        config = SQLBotConfig(profile='test_profile', dangerous=True)
        
        # Clear any existing values
        if 'DBT_PROFILE_NAME' in os.environ:
            del os.environ['DBT_PROFILE_NAME']
        if 'SQLBOT_DANGEROUS' in os.environ:
            del os.environ['SQLBOT_DANGEROUS']
        
        config.apply_to_env()
        
        assert os.environ['DBT_PROFILE_NAME'] == 'test_profile'
        assert os.environ['SQLBOT_DANGEROUS'] == 'true'
        
        # Clean up
        del os.environ['DBT_PROFILE_NAME']
        del os.environ['SQLBOT_DANGEROUS']


class TestLLMConfig:
    """Test LLM configuration"""
    
    def test_llm_config_defaults(self):
        """Test LLM configuration defaults"""
        llm_config = LLMConfig()
        
        assert llm_config.model == "gpt-5"
        assert llm_config.max_tokens == 50000
        assert llm_config.temperature == 0.1
        assert llm_config.api_key is None
        assert llm_config.provider == "openai"
    
    def test_llm_config_custom(self):
        """Test custom LLM configuration"""
        llm_config = LLMConfig(
            model="gpt-5",
            max_tokens=2000,
            temperature=0.5,
            api_key="test-key",
            provider="anthropic"
        )
        
        assert llm_config.model == "gpt-5"
        assert llm_config.max_tokens == 2000
        assert llm_config.temperature == 0.5
        assert llm_config.api_key == "test-key"
        assert llm_config.provider == "anthropic"

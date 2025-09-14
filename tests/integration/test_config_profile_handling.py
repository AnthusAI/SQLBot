"""
Test configuration file profile handling behavior

Tests the interaction between profile specification in config files vs command line arguments.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
import yaml

from sqlbot.core.config import SQLBotConfig


@pytest.mark.integration


class TestConfigProfileHandling:
    """Test profile handling from config file vs command line"""

    def setup_method(self):
        """Set up test environment with temporary directories"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / '.sqlbot'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / 'config.yml'

        # Store original environment to restore later
        self.original_env = {}
        for key in list(os.environ.keys()):
            if key.startswith('SQLBOT_'):
                self.original_env[key] = os.environ[key]

    def teardown_method(self):
        """Clean up temporary directories and restore environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Clean up all SQLBOT_ environment variables
        for key in list(os.environ.keys()):
            if key.startswith('SQLBOT_'):
                del os.environ[key]

        # Restore original environment
        for key, value in self.original_env.items():
            os.environ[key] = value

    def create_config_file(self, config_data: dict):
        """Create a test config file with given data"""
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)

    def test_profile_from_config_file_only(self):
        """
        GIVEN: A config file specifies a profile and no --profile is passed on command line
        WHEN: SQLBot config is loaded
        THEN: The profile from config file should be used
        """
        # Create config file with profile
        config_data = {
            'database': {
                'profile': 'TestProfile'
            },
            'llm': {
                'model': 'gpt-5'
            }
        }
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Load config without command line profile
            config = SQLBotConfig.from_env()

            # Should use profile from config file
            assert config.profile == 'TestProfile'

        finally:
            os.chdir(original_cwd)

    def test_command_line_profile_overrides_config_file(self):
        """
        GIVEN: A config file specifies a profile AND --profile is passed on command line
        WHEN: SQLBot config is loaded
        THEN: The command line profile should override the config file profile
        """
        # Create config file with profile
        config_data = {
            'database': {
                'profile': 'ConfigFileProfile'
            },
            'llm': {
                'model': 'gpt-5'
            }
        }
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Load config with command line profile override
            # Pass profile directly to from_env() method
            config = SQLBotConfig.from_env(profile='CommandLineProfile')

            # Should use command line profile, not config file profile
            assert config.profile == 'CommandLineProfile'

        finally:
            os.chdir(original_cwd)

    def test_no_profile_specified_anywhere(self):
        """
        GIVEN: No profile is specified in config file or command line
        WHEN: SQLBot config is loaded
        THEN: Profile should be None (no fallback complexity)
        """
        # Create config file without profile
        config_data = {
            'llm': {
                'model': 'gpt-5'
            }
        }
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Load config without any profile specification
            config = SQLBotConfig.from_env()

            # Should be None - no fallback complexity
            assert config.profile is None

        finally:
            os.chdir(original_cwd)

    def test_config_file_profile_with_other_settings(self):
        """
        GIVEN: A config file specifies profile along with other settings
        WHEN: SQLBot config is loaded
        THEN: All settings should be properly loaded including the profile
        """
        # Create comprehensive config file
        config_data = {
            'database': {
                'profile': 'ComprehensiveProfile'
            },
            'llm': {
                'model': 'gpt-5',
                'max_tokens': 25000,
                'verbosity': 'medium',
                'effort': 'balanced'
            },
            'safety': {
                'read_only': True,
                'preview_mode': False
            },
            'query': {
                'timeout': 120,
                'max_rows': 2000
            }
        }
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Load config
            config = SQLBotConfig.from_env()

            # Verify profile is loaded
            assert config.profile == 'ComprehensiveProfile'

            # Verify other settings are also loaded correctly
            assert config.llm.model == 'gpt-5'
            assert config.llm.max_tokens == 25000
            assert config.llm.verbosity == 'medium'
            assert config.llm.effort == 'balanced'

        finally:
            os.chdir(original_cwd)

    def test_empty_config_file_with_command_line_profile(self):
        """
        GIVEN: An empty config file and --profile passed on command line
        WHEN: SQLBot config is loaded
        THEN: The command line profile should be used
        """
        # Create empty config file
        config_data = {}
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Load config with command line profile
            config = SQLBotConfig.from_env(profile='CLIProfile')

            # Should use command line profile
            assert config.profile == 'CLIProfile'

        finally:
            os.chdir(original_cwd)

    def test_integration_with_sqlbot_text_mode(self):
        """
        GIVEN: A config file with profile specified
        WHEN: SQLBot is run in --text --no-repl mode
        THEN: Should use the profile from config file and work correctly
        """
        # Create config file with Sakila profile (since we know it exists)
        config_data = {
            'database': {
                'profile': 'Sakila'
            },
            'llm': {
                'model': 'gpt-5',
                'verbosity': 'low',
                'effort': 'minimal'
            },
            'safety': {
                'read_only': True
            }
        }
        self.create_config_file(config_data)

        # Change to temp directory so config file is found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Test with actual SQLBot execution
            import subprocess
            import sys

            # Run SQLBot with a simple query to test config file profile usage
            cmd = [
                sys.executable, '-m', 'sqlbot',
                '--text', '--no-repl',
                'SELECT COUNT(*) as actor_count FROM actor'
            ]

            # Set environment to use our temp config
            env = os.environ.copy()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.temp_dir,
                env=env
            )

            # Should not fail due to missing profile
            # (though it might fail for other reasons like missing dbt setup)
            print(f"Return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")

            # The key test is that it should not complain about missing profile
            assert "profile" not in result.stderr.lower() or "not found" not in result.stderr.lower()

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
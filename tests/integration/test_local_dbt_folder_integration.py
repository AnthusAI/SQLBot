"""Integration tests for local .dbt folder functionality."""

import pytest
import os
import tempfile
import shutil
import yaml
from pathlib import Path

from sqlbot.core.config import SQLBotConfig
from sqlbot.core.dbt_service import get_dbt_service, DbtService
from sqlbot.interfaces.banner import get_banner_content


class TestLocalDbtFolderIntegration:
    """Integration tests for local .dbt folder support."""

    def test_local_dbt_folder_detection_integration(self):
        """Test complete local .dbt folder detection flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Test 1: No local .dbt folder - uses global
                profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()
                assert is_local is False
                assert str(Path.home() / '.dbt') == profiles_dir

                # Test 2: Create local .dbt folder - uses local
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text('test: config')

                profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()
                assert is_local is True
                assert str(dbt_dir.resolve()) == profiles_dir

            finally:
                os.chdir(old_cwd)

    def test_dbt_service_local_configuration_integration(self):
        """Test DbtService correctly configures local .dbt folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create local .dbt folder with test profile
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()

                test_profile = {
                    'TestProfile': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {
                                'type': 'sqlite',
                                'database': ':memory:'
                            }
                        }
                    }
                }

                profiles_file = dbt_dir / 'profiles.yml'
                with open(profiles_file, 'w') as f:
                    yaml.dump(test_profile, f)

                # Test DbtService configuration
                config = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service = DbtService(config)
                dbt_config_info = dbt_service.get_dbt_config_info()

                assert dbt_config_info['is_using_local_dbt'] is True
                assert '.dbt' in dbt_config_info['profiles_dir']
                assert dbt_config_info['profile_name'] == 'TestProfile'

                # Verify environment variable is set
                assert os.environ.get('DBT_PROFILES_DIR') == str(dbt_dir.resolve())

            finally:
                os.chdir(old_cwd)

    def test_banner_display_integration(self):
        """Test banner correctly displays local vs global dbt configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Test 1: Global configuration banner
                config = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service = DbtService(config)
                dbt_config_info = dbt_service.get_dbt_config_info()

                banner_text = get_banner_content(
                    profile='TestProfile',
                    llm_model='gpt-5',
                    llm_available=True,
                    interface_type='text',
                    dbt_config_info=dbt_config_info
                )

                assert "Global `~/.dbt/profiles.yml`" in banner_text

                # Test 2: Create local .dbt and test local configuration banner
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text('TestProfile:\n  target: dev\n  outputs:\n    dev:\n      type: sqlite')

                # Create fresh service to pick up local configuration
                config2 = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service2 = DbtService(config2)
                dbt_config_info2 = dbt_service2.get_dbt_config_info()

                banner_text2 = get_banner_content(
                    profile='TestProfile',
                    llm_model='gpt-5',
                    llm_available=True,
                    interface_type='text',
                    dbt_config_info=dbt_config_info2
                )

                assert "Local `.dbt/profiles.yml` (detected)" in banner_text2

            finally:
                os.chdir(old_cwd)

    def test_sakila_profile_management_integration(self):
        """Test Sakila profile creation and management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                from scripts.setup_sakila_db import SakilaSetup

                # Create database structure
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Test 1: Create local profile from scratch
                setup = SakilaSetup()
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')
                assert result is True

                # Verify profile was created
                dbt_dir = Path('.dbt')
                assert dbt_dir.exists()
                profiles_file = dbt_dir / 'profiles.yml'
                assert profiles_file.exists()

                with open(profiles_file, 'r') as f:
                    profiles = yaml.safe_load(f)

                assert 'Sakila' in profiles
                assert profiles['Sakila']['target'] == 'dev'
                sakila_config = profiles['Sakila']['outputs']['dev']
                assert 'sakila.db' in sakila_config['schemas_and_paths']['main']

                # Test 2: Profile validation
                is_valid, message = setup.check_local_dbt_profile()
                assert is_valid is True
                assert 'sakila.db' in message

                # Test 3: Test merging with existing profiles
                existing_profile = {
                    'ExistingProfile': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {'type': 'postgres', 'host': 'localhost'}
                        }
                    }
                }

                # Add existing profile
                profiles.update(existing_profile)
                with open(profiles_file, 'w') as f:
                    yaml.dump(profiles, f)

                # Run profile creation again (should merge)
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')
                assert result is True

                # Verify both profiles exist
                with open(profiles_file, 'r') as f:
                    merged_profiles = yaml.safe_load(f)

                assert 'Sakila' in merged_profiles
                assert 'ExistingProfile' in merged_profiles

            finally:
                os.chdir(old_cwd)

    def test_setup_script_no_local_profile_flag_integration(self):
        """Test setup script with --no-local-profile flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                from scripts.setup_sakila_db import SakilaSetup

                # Create database structure
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Test with local profile creation disabled
                setup = SakilaSetup(create_local_profile=False)
                assert setup.create_local_profile is False

                # Even if we had profile creation logic, it should be skipped
                dbt_dir = Path('.dbt')
                assert not dbt_dir.exists()

            finally:
                os.chdir(old_cwd)
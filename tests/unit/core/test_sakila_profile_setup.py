"""Unit tests for Sakila profile setup functionality."""

import pytest
import os
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import patch

from scripts.setup_sakila_db import SakilaSetup


class TestSakilaProfileSetup:
    """Test Sakila profile setup and management."""

    def test_create_local_dbt_profile_new_folder(self):
        """Test creating local dbt profile when .dbt folder doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create database file
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Create setup instance and run profile creation
                setup = SakilaSetup()
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')

                assert result is True, "Profile creation should succeed"

                # Verify .dbt folder was created
                dbt_dir = Path('.dbt')
                assert dbt_dir.exists(), "Local .dbt folder should be created"

                # Verify profiles.yml was created
                profiles_file = dbt_dir / 'profiles.yml'
                assert profiles_file.exists(), "profiles.yml should be created"

                # Verify Sakila profile exists
                with open(profiles_file, 'r') as f:
                    profiles = yaml.safe_load(f)

                assert 'Sakila' in profiles, "Sakila profile should exist"
                assert profiles['Sakila']['target'] == 'dev', "Target should be dev"

            finally:
                os.chdir(old_cwd)

    def test_create_local_dbt_profile_merge_existing(self):
        """Test merging Sakila profile with existing profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create existing .dbt folder with profiles
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()

                existing_profiles = {
                    'existing_profile': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {
                                'type': 'postgres',
                                'host': 'localhost'
                            }
                        }
                    }
                }

                profiles_file = dbt_dir / 'profiles.yml'
                with open(profiles_file, 'w') as f:
                    yaml.dump(existing_profiles, f)

                # Create database file
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Create setup instance and run profile creation
                setup = SakilaSetup()
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')

                assert result is True, "Profile creation should succeed"

                # Verify profiles were merged
                with open(profiles_file, 'r') as f:
                    profiles = yaml.safe_load(f)

                assert 'existing_profile' in profiles, "Existing profile should be preserved"
                assert 'Sakila' in profiles, "Sakila profile should be added"

            finally:
                os.chdir(old_cwd)

    def test_create_local_dbt_profile_update_existing_sakila(self):
        """Test updating existing Sakila profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create existing .dbt folder with old Sakila profile
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()

                existing_profiles = {
                    'Sakila': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {
                                'type': 'sqlite',
                                'schemas_and_paths': {
                                    'main': '/old/path/sakila.db'
                                }
                            }
                        }
                    }
                }

                profiles_file = dbt_dir / 'profiles.yml'
                with open(profiles_file, 'w') as f:
                    yaml.dump(existing_profiles, f)

                # Create database file
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Create setup instance and run profile creation
                setup = SakilaSetup()
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')

                assert result is True, "Profile creation should succeed"

                # Verify Sakila profile was updated
                with open(profiles_file, 'r') as f:
                    profiles = yaml.safe_load(f)

                sakila_config = profiles['Sakila']['outputs']['dev']
                db_path = sakila_config['schemas_and_paths']['main']

                assert '/old/path/sakila.db' not in db_path, "Old path should be updated"
                assert 'sakila.db' in db_path, "New path should contain sakila.db"

            finally:
                os.chdir(old_cwd)

    def test_check_local_dbt_profile_valid(self):
        """Test checking valid local dbt profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create valid .dbt folder and profile
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()

                # Create database file
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                sakila_profile = {
                    'Sakila': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {
                                'type': 'sqlite',
                                'schemas_and_paths': {
                                    'main': str(db_file.resolve())
                                }
                            }
                        }
                    }
                }

                profiles_file = dbt_dir / 'profiles.yml'
                with open(profiles_file, 'w') as f:
                    yaml.dump(sakila_profile, f)

                # Check profile
                setup = SakilaSetup()
                is_valid, message = setup.check_local_dbt_profile()

                assert is_valid is True, f"Profile should be valid: {message}"
                assert 'sakila.db' in message, "Message should contain database path"

            finally:
                os.chdir(old_cwd)

    def test_check_local_dbt_profile_missing_database(self):
        """Test checking profile with missing database file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create .dbt folder and profile without database file
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()

                sakila_profile = {
                    'Sakila': {
                        'target': 'dev',
                        'outputs': {
                            'dev': {
                                'type': 'sqlite',
                                'schemas_and_paths': {
                                    'main': '/nonexistent/sakila.db'
                                }
                            }
                        }
                    }
                }

                profiles_file = dbt_dir / 'profiles.yml'
                with open(profiles_file, 'w') as f:
                    yaml.dump(sakila_profile, f)

                # Check profile
                setup = SakilaSetup()
                is_valid, message = setup.check_local_dbt_profile()

                assert is_valid is False, "Profile should be invalid"
                assert 'not found' in message.lower(), "Message should indicate missing file"

            finally:
                os.chdir(old_cwd)

    def test_check_local_dbt_profile_no_file(self):
        """Test checking profile when no profiles.yml exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # No .dbt folder exists
                setup = SakilaSetup()
                is_valid, message = setup.check_local_dbt_profile()

                assert is_valid is False, "Profile should be invalid"
                assert 'does not exist' in message, "Message should indicate missing file"

            finally:
                os.chdir(old_cwd)

    def test_sakila_setup_with_local_profile_disabled(self):
        """Test SakilaSetup with local profile creation disabled."""
        setup = SakilaSetup(create_local_profile=False)
        assert setup.create_local_profile is False, "Local profile creation should be disabled"

    def test_sakila_setup_with_local_profile_enabled(self):
        """Test SakilaSetup with local profile creation enabled (default)."""
        setup = SakilaSetup()
        assert setup.create_local_profile is True, "Local profile creation should be enabled by default"
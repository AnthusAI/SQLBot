"""Unit tests for Sakila profile setup functionality."""

import pytest
import os
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import patch

from sqlbot.core.sakila import SakilaManager


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
                setup = SakilaManager()
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
                setup = SakilaManager()
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
                setup = SakilaManager()
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
                setup = SakilaManager()
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
                setup = SakilaManager()
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
                setup = SakilaManager()
                is_valid, message = setup.check_local_dbt_profile()

                assert is_valid is False, "Profile should be invalid"
                assert 'does not exist' in message, "Message should indicate missing file"

            finally:
                os.chdir(old_cwd)

    def test_sakila_setup_with_local_profile_disabled(self):
        """Test SakilaManager with local profile creation disabled."""
        setup = SakilaManager(create_local_profile=False)
        assert setup.create_local_profile is False, "Local profile creation should be disabled"

    def test_sakila_setup_with_local_profile_enabled(self):
        """Test SakilaManager with local profile creation enabled (default)."""
        setup = SakilaManager()
        assert setup.create_local_profile is True, "Local profile creation should be enabled by default"

    def test_create_profiles_backup_creates_timestamped_backup(self):
        """Test that create_profiles_backup creates a timestamped backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create a test profiles file
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                profiles_file = dbt_dir / 'profiles.yml'
                
                original_content = {
                    'test_profile': {
                        'target': 'dev',
                        'outputs': {'dev': {'type': 'postgres'}}
                    }
                }
                
                with open(profiles_file, 'w') as f:
                    yaml.dump(original_content, f)

                # Create backup
                setup = SakilaManager()
                backup_path = setup.create_profiles_backup(profiles_file)

                # Verify backup was created
                assert backup_path is not None, "Backup path should be returned"
                assert backup_path.exists(), "Backup file should exist"
                assert backup_path.name.startswith('profiles.backup.'), "Backup should have correct naming pattern"
                assert backup_path.suffix == '.yml', "Backup should preserve file extension"

                # Verify backup content matches original
                with open(backup_path, 'r') as f:
                    backup_content = yaml.safe_load(f)
                assert backup_content == original_content, "Backup content should match original"

            finally:
                os.chdir(old_cwd)

    def test_create_profiles_backup_handles_nonexistent_file(self):
        """Test that create_profiles_backup handles non-existent files gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Try to backup non-existent file
                nonexistent_file = Path('nonexistent.yml')
                setup = SakilaManager()
                backup_path = setup.create_profiles_backup(nonexistent_file)

                # Should return None for non-existent files
                assert backup_path is None, "Should return None for non-existent files"

            finally:
                os.chdir(old_cwd)

    def test_create_local_dbt_profile_creates_backup_before_changes(self):
        """Test that profile creation creates a backup of existing profiles.yml."""
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
                setup = SakilaManager()
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')

                assert result is True, "Profile creation should succeed"

                # Verify backup was created
                backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
                assert len(backup_files) == 1, "Should create exactly one backup file"
                
                backup_file = backup_files[0]
                assert backup_file.name.startswith('profiles.backup.'), "Backup should have correct naming pattern"

                # Verify backup content matches original
                with open(backup_file, 'r') as f:
                    backup_content = yaml.safe_load(f)
                assert 'existing_profile' in backup_content, "Backup should contain original profile"
                assert backup_content['existing_profile'] == existing_profiles['existing_profile'], "Backup should preserve original content"

                # Verify new profiles file has both old and new profiles
                with open(profiles_file, 'r') as f:
                    new_profiles = yaml.safe_load(f)
                assert 'existing_profile' in new_profiles, "New profiles should preserve existing profile"
                assert 'Sakila' in new_profiles, "New profiles should contain Sakila profile"

            finally:
                os.chdir(old_cwd)

    def test_backup_failure_does_not_prevent_profile_creation(self):
        """Test that backup failure doesn't prevent profile creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create .dbt directory with restricted permissions to cause backup failure
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                profiles_file = dbt_dir / 'profiles.yml'
                
                # Create initial profiles file
                with open(profiles_file, 'w') as f:
                    yaml.dump({'test': 'data'}, f)

                # Create database file
                db_dir = Path('profiles/Sakila/data')
                db_dir.mkdir(parents=True)
                db_file = db_dir / 'sakila.db'
                db_file.touch()

                # Mock the backup method to simulate failure
                setup = SakilaManager()
                original_backup = setup.create_profiles_backup
                
                def failing_backup(profiles_file):
                    raise Exception("Simulated backup failure")
                
                setup.create_profiles_backup = failing_backup

                # Profile creation should still succeed despite backup failure
                result = setup.create_local_dbt_profile('profiles/Sakila/data/sakila.db')
                assert result is True, "Profile creation should succeed even if backup fails"

                # Verify Sakila profile was still created
                with open(profiles_file, 'r') as f:
                    profiles = yaml.safe_load(f)
                assert 'Sakila' in profiles, "Sakila profile should be created despite backup failure"

            finally:
                os.chdir(old_cwd)
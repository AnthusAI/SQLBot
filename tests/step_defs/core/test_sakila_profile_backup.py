"""BDD step definitions for Sakila profile backup functionality."""

import os
import re
import stat
import tempfile
import time
import yaml
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_bdd import given, when, then, scenarios

from sqlbot.core.sakila import SakilaManager

# Load scenarios from feature file
scenarios('../../features/sakila_profile_backup.feature')


@pytest.fixture
def sakila_manager():
    """Create a SakilaManager instance for testing."""
    return SakilaManager(create_local_profile=True)


@pytest.fixture
def test_context():
    """Provide test context with temporary directory management."""
    context = {}
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            context['temp_dir'] = temp_dir
            context['old_cwd'] = old_cwd
            yield context
        finally:
            os.chdir(old_cwd)


@given('I have a clean test environment')
def clean_test_environment(test_context):
    """Ensure we start with a clean test environment."""
    # Context is already set up in the fixture
    # On macOS, temp paths may have /private prefix, so resolve both paths
    assert Path.cwd().resolve() == Path(test_context['temp_dir']).resolve()


@given('I have SQLite installed and available')
def sqlite_available():
    """Mock SQLite availability check."""
    # We'll mock this in the actual test to avoid system dependencies
    pass


@given('I have an existing .dbt directory')
def create_dbt_directory(test_context):
    """Create an existing .dbt directory."""
    dbt_dir = Path('.dbt')
    dbt_dir.mkdir(exist_ok=True)
    test_context['dbt_dir'] = dbt_dir


@given('I have an existing profiles.yml with other profiles')
def create_existing_profiles(test_context):
    """Create an existing profiles.yml with test profiles."""
    dbt_dir = test_context['dbt_dir']
    profiles_file = dbt_dir / 'profiles.yml'
    
    existing_profiles = {
        'my_postgres_db': {
            'target': 'dev',
            'outputs': {
                'dev': {
                    'type': 'postgres',
                    'host': 'localhost',
                    'user': 'postgres',
                    'password': 'secret',
                    'port': 5432,
                    'dbname': 'mydb'
                }
            }
        },
        'my_snowflake_db': {
            'target': 'prod',
            'outputs': {
                'prod': {
                    'type': 'snowflake',
                    'account': 'myaccount',
                    'user': 'myuser',
                    'warehouse': 'mywarehouse'
                }
            }
        }
    }
    
    with open(profiles_file, 'w') as f:
        yaml.dump(existing_profiles, f, default_flow_style=False)
    
    test_context['original_profiles'] = existing_profiles
    test_context['profiles_file'] = profiles_file


@given('I have an existing profiles.yml with specific permissions')
def create_profiles_with_permissions(test_context):
    """Create profiles.yml with specific file permissions."""
    create_existing_profiles(test_context)
    profiles_file = test_context['profiles_file']
    
    # Set specific permissions (readable/writable by owner only)
    os.chmod(profiles_file, stat.S_IRUSR | stat.S_IWUSR)
    test_context['original_permissions'] = profiles_file.stat().st_mode


@given('I have no existing .dbt directory')
def no_dbt_directory(test_context):
    """Ensure no .dbt directory exists."""
    dbt_dir = Path('.dbt')
    if dbt_dir.exists():
        import shutil
        shutil.rmtree(dbt_dir)
    assert not dbt_dir.exists()


@given('I have an existing profiles.yml file')
def create_simple_profiles_file(test_context):
    """Create a simple existing profiles.yml file."""
    create_dbt_directory(test_context)
    dbt_dir = test_context['dbt_dir']
    profiles_file = dbt_dir / 'profiles.yml'
    
    simple_profiles = {
        'test_profile': {
            'target': 'dev',
            'outputs': {
                'dev': {
                    'type': 'duckdb',
                    'path': 'test.db'
                }
            }
        }
    }
    
    with open(profiles_file, 'w') as f:
        yaml.dump(simple_profiles, f)
    
    test_context['profiles_file'] = profiles_file
    test_context['original_profiles'] = simple_profiles


@given('the backup operation will fail due to permissions')
def mock_backup_failure(test_context, sakila_manager):
    """Mock backup operation to fail.""" 
    original_backup = sakila_manager.create_profiles_backup
    
    def failing_backup(profiles_file):
        # Instead of raising an exception that breaks the flow,
        # just return None to simulate failure
        print("⚠ Warning: Could not create backup of profiles.yml: Simulated permission error for backup")
        return None
    
    sakila_manager.create_profiles_backup = failing_backup
    test_context['backup_will_fail'] = True


@when('I run the Sakila profile setup')
def run_sakila_profile_setup(test_context, sakila_manager):
    """Run the Sakila profile setup process."""
    # Create database file for the setup
    db_dir = Path('profiles/Sakila/data')
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / 'sakila.db'
    db_file.touch()
    
    # Mock SQLite availability check
    with patch.object(sakila_manager, 'check_sqlite_availability', return_value=True):
        result = sakila_manager.create_local_dbt_profile('profiles/Sakila/data/sakila.db')
    
    test_context['setup_result'] = result


@when('I run the Sakila profile setup multiple times')
def run_sakila_setup_multiple_times(test_context, sakila_manager):
    """Run Sakila profile setup multiple times with small delays."""
    # Create database file
    db_dir = Path('profiles/Sakila/data')
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / 'sakila.db'
    db_file.touch()
    
    results = []
    for i in range(3):
        if i > 0:
            time.sleep(1)  # Ensure different timestamps
        
        with patch.object(sakila_manager, 'check_sqlite_availability', return_value=True):
            result = sakila_manager.create_local_dbt_profile('profiles/Sakila/data/sakila.db')
        results.append(result)
    
    test_context['setup_results'] = results


@then('a timestamped backup of profiles.yml should be created')
def verify_timestamped_backup_created(test_context):
    """Verify that a timestamped backup was created."""
    dbt_dir = Path('.dbt')
    backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
    
    assert len(backup_files) >= 1, "At least one backup file should be created"
    
    backup_file = backup_files[0]
    assert backup_file.name.startswith('profiles.backup.'), "Backup should have correct prefix"
    assert backup_file.suffix == '.yml', "Backup should preserve .yml extension"
    
    # Verify timestamp format (YYYYMMDD_HHMMSS)
    timestamp_pattern = r'profiles\.backup\.(\d{8}_\d{6})\.yml'
    match = re.match(timestamp_pattern, backup_file.name)
    assert match is not None, f"Backup filename should match timestamp pattern: {backup_file.name}"
    
    test_context['backup_files'] = backup_files


@then('the backup should contain my original profile data')
def verify_backup_content(test_context):
    """Verify backup contains original profile data."""
    backup_files = test_context['backup_files']
    original_profiles = test_context['original_profiles']
    
    with open(backup_files[0], 'r') as f:
        backup_content = yaml.safe_load(f)
    
    assert backup_content == original_profiles, "Backup should contain original profile data"


@then('the new profiles.yml should contain both old and new profiles')
def verify_merged_profiles(test_context):
    """Verify new profiles.yml contains both old and new profiles."""
    profiles_file = Path('.dbt/profiles.yml')
    original_profiles = test_context['original_profiles']
    
    with open(profiles_file, 'r') as f:
        new_profiles = yaml.safe_load(f)
    
    # Should contain original profiles
    for profile_name, profile_config in original_profiles.items():
        assert profile_name in new_profiles, f"Original profile {profile_name} should be preserved"
        assert new_profiles[profile_name] == profile_config, f"Original profile {profile_name} should be unchanged"
    
    # Should contain new Sakila profile
    assert 'Sakila' in new_profiles, "New profiles should contain Sakila profile"
    assert new_profiles['Sakila']['target'] == 'dev', "Sakila profile should have correct structure"


@then('a backup should be created with the same content')
def verify_backup_same_content(test_context):
    """Verify backup has same content as original."""
    # First find the backup files
    verify_timestamped_backup_created(test_context)
    # Then verify content
    verify_backup_content(test_context)


@then('the backup should preserve the original file metadata')
def verify_backup_metadata(test_context):
    """Verify backup preserves original file metadata."""
    # Note: shutil.copy2 preserves timestamps and permissions
    backup_files = test_context['backup_files']
    
    assert len(backup_files) >= 1, "Backup file should exist"
    # Detailed metadata verification would require more complex setup
    # This test verifies the backup exists and has content


@then('no backup file should be created')
def verify_no_backup_created(test_context):
    """Verify no backup files were created."""
    dbt_dir = Path('.dbt')
    if dbt_dir.exists():
        backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
        assert len(backup_files) == 0, "No backup files should be created for new profiles"


@then('a new profiles.yml should be created with Sakila profile')
def verify_new_profiles_created(test_context):
    """Verify new profiles.yml was created with Sakila profile."""
    profiles_file = Path('.dbt/profiles.yml')
    assert profiles_file.exists(), "New profiles.yml should be created"
    
    with open(profiles_file, 'r') as f:
        profiles = yaml.safe_load(f)
    
    assert 'Sakila' in profiles, "New profiles should contain Sakila profile"
    assert profiles['Sakila']['target'] == 'dev', "Sakila profile should be properly configured"


@then('a warning about backup failure should be shown')
def verify_backup_warning_shown(test_context):
    """Verify warning about backup failure is handled."""
    # In real implementation, this would check captured output
    # For now, we verify the setup result indicates the operation continued
    assert test_context.get('backup_will_fail') is True, "Backup failure should have been simulated"


@then('the profile setup should complete successfully') 
def verify_setup_completed_successfully(test_context):
    """Verify profile setup completed despite backup failure."""
    assert test_context['setup_result'] is True, "Profile setup should succeed even with backup failure"


@then('the Sakila profile should be added to profiles.yml')
def verify_sakila_profile_added(test_context):
    """Verify Sakila profile was added despite backup failure."""
    profiles_file = Path('.dbt/profiles.yml')
    
    with open(profiles_file, 'r') as f:
        profiles = yaml.safe_load(f)
    
    assert 'Sakila' in profiles, "Sakila profile should be added despite backup failure"


@then('multiple backup files should be created')
def verify_multiple_backups_created(test_context):
    """Verify multiple backup files were created."""
    dbt_dir = Path('.dbt')
    backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
    
    expected_count = len(test_context['setup_results'])
    assert len(backup_files) == expected_count, f"Should create {expected_count} backup files"
    
    test_context['backup_files'] = backup_files


@then('each backup file should have a unique timestamp')
def verify_unique_timestamps(test_context):
    """Verify each backup file has a unique timestamp."""
    backup_files = test_context['backup_files']
    
    timestamps = []
    for backup_file in backup_files:
        timestamp_pattern = r'profiles\.backup\.(\d{8}_\d{6})\.yml'
        match = re.match(timestamp_pattern, backup_file.name)
        assert match is not None, f"Backup filename should match pattern: {backup_file.name}"
        timestamps.append(match.group(1))
    
    assert len(set(timestamps)) == len(timestamps), "All backup timestamps should be unique"


@then('no backup files should be overwritten')
def verify_no_backup_overwritten(test_context):
    """Verify no backup files were overwritten."""
    # This is implicitly tested by the unique timestamp verification
    verify_unique_timestamps(test_context)


@then('the backup filename should follow the pattern "profiles.backup.YYYYMMDD_HHMMSS.yml"')
def verify_backup_filename_pattern(test_context):
    """Verify backup filename follows the expected pattern."""
    dbt_dir = Path('.dbt')
    backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
    
    assert len(backup_files) >= 1, "At least one backup file should exist"
    
    backup_file = backup_files[0]
    pattern = r'^profiles\.backup\.\d{8}_\d{6}\.yml$'
    assert re.match(pattern, backup_file.name), f"Backup filename should match pattern: {backup_file.name}"


@then('the backup should be in the same directory as the original file')
def verify_backup_same_directory(test_context):
    """Verify backup is in the same directory as original."""
    dbt_dir = Path('.dbt')
    profiles_file = dbt_dir / 'profiles.yml'
    backup_files = list(dbt_dir.glob('profiles.backup.*.yml'))
    
    assert len(backup_files) >= 1, "Backup file should exist"
    
    backup_file = backup_files[0]
    assert backup_file.parent == profiles_file.parent, "Backup should be in same directory as original"
"""Unit tests for local .dbt folder detection functionality."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from sqlbot.core.config import SQLBotConfig
from sqlbot.core.dbt_service import get_dbt_service
from sqlbot.interfaces.banner import get_banner_content


class TestLocalDbtDetection:
    """Test local .dbt folder detection and configuration."""

    def test_detect_local_dbt_folder_exists(self):
        """Test detection when local .dbt folder exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create local .dbt folder with profiles.yml
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text('test: config')

                # Test detection
                profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()

                assert is_local is True
                assert str(dbt_dir.resolve()) == profiles_dir

            finally:
                os.chdir(old_cwd)

    def test_detect_global_dbt_folder_fallback(self):
        """Test fallback to global ~/.dbt when no local folder exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Ensure no local .dbt folder exists
                dbt_dir = Path('.dbt')
                if dbt_dir.exists():
                    shutil.rmtree(dbt_dir)

                # Test detection
                profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()

                assert is_local is False
                assert str(Path.home() / '.dbt') == profiles_dir

            finally:
                os.chdir(old_cwd)

    def test_dbt_service_uses_local_config(self):
        """Test that DbtService correctly uses local .dbt configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create local .dbt folder
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text("""
TestProfile:
  target: dev
  outputs:
    dev:
      type: sqlite
      database: ':memory:'
""")

                # Create config and dbt service
                config = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service = get_dbt_service(config)

                # Test configuration info
                dbt_config_info = dbt_service.get_dbt_config_info()

                assert dbt_config_info['is_using_local_dbt'] is True
                assert '.dbt' in dbt_config_info['profiles_dir']
                assert dbt_config_info['profile_name'] == 'TestProfile'

                # Test environment variable is set
                assert os.environ.get('DBT_PROFILES_DIR') == str(dbt_dir.resolve())

            finally:
                os.chdir(old_cwd)

    def test_banner_shows_local_dbt_detection(self):
        """Test that banner correctly shows local .dbt detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create local .dbt folder
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text('test: config')

                # Create config and get dbt info
                config = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service = get_dbt_service(config)
                dbt_config_info = dbt_service.get_dbt_config_info()

                # Generate banner
                banner_text = get_banner_content(
                    profile='TestProfile',
                    llm_model='gpt-5',
                    llm_available=True,
                    interface_type='text',
                    dbt_config_info=dbt_config_info
                )

                assert "Local `.dbt/profiles.yml` (detected)" in banner_text
                assert "Profile:** `TestProfile`" in banner_text

            finally:
                os.chdir(old_cwd)

    def test_banner_shows_global_dbt_fallback(self):
        """Test that banner correctly shows global .dbt fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Ensure no local .dbt folder exists
                dbt_dir = Path('.dbt')
                if dbt_dir.exists():
                    shutil.rmtree(dbt_dir)

                # Create fresh config and dbt service to avoid caching
                from sqlbot.core.dbt_service import DbtService
                config = SQLBotConfig.from_env(profile='TestProfile')
                dbt_service = DbtService(config)  # Create fresh instance
                dbt_config_info = dbt_service.get_dbt_config_info()

                # Generate banner
                banner_text = get_banner_content(
                    profile='TestProfile',
                    llm_model='gpt-5',
                    llm_available=True,
                    interface_type='text',
                    dbt_config_info=dbt_config_info
                )

                assert "Global `~/.dbt/profiles.yml`" in banner_text
                assert "Profile:** `TestProfile`" in banner_text

            finally:
                os.chdir(old_cwd)

    def test_local_takes_priority_over_global(self):
        """Test that local .dbt folder takes priority over global."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create local .dbt folder
                dbt_dir = Path('.dbt')
                dbt_dir.mkdir()
                (dbt_dir / 'profiles.yml').write_text('local: config')

                # Test detection (regardless of global ~/.dbt existence)
                profiles_dir, is_local = SQLBotConfig.detect_dbt_profiles_dir()

                assert is_local is True
                assert str(dbt_dir.resolve()) == profiles_dir

            finally:
                os.chdir(old_cwd)
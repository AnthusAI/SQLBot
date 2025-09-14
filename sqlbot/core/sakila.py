"""
Sakila Sample Database Management for SQLBot

This module provides functionality to download and set up the Sakila sample database
for use with SQLBot. The Sakila database is a well-known sample database containing
DVD rental store data, perfect for testing and demonstration purposes.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class SakilaManager:
    """Downloads and manages the Sakila sample database for SQLBot."""

    SAKILA_SQLITE_URL = "https://github.com/siara-cc/sakila_sqlite3/raw/master/sakila.db"

    def __init__(self, create_local_profile: bool = True):
        self.create_local_profile = create_local_profile
        self.temp_dir = None

    def check_sqlite_availability(self) -> bool:
        """Check if SQLite is installed and accessible."""
        try:
            result = subprocess.run(
                ['sqlite3', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ Found SQLite: {version}")
                return True
            else:
                print("✗ SQLite not responding properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("✗ SQLite not found")
            self.show_sqlite_install_help()
            return False
        except Exception as e:
            print(f"✗ Error checking SQLite: {e}")
            return False

    def show_sqlite_install_help(self):
        """Show SQLite installation instructions."""
        print("\nSQLite installation needed:")
        print("  Ubuntu/Debian: sudo apt-get install sqlite3")
        print("  macOS: brew install sqlite3 (or use built-in version)")
        print("  Windows: Download from https://sqlite.org/download.html")
        print("  Most systems: SQLite is usually pre-installed")

    def download_sakila_sqlite(self) -> Optional[Path]:
        """Download the pre-built Sakila SQLite database."""
        print("Downloading Sakila SQLite database...")

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="sakila_sqlite_setup_")
        temp_db_path = Path(self.temp_dir) / "sakila.db"

        try:
            # Download with progress
            def show_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100.0, (downloaded / total_size) * 100)
                    print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)

            urllib.request.urlretrieve(self.SAKILA_SQLITE_URL, temp_db_path, show_progress)
            print()  # New line after progress

            if temp_db_path.exists() and temp_db_path.stat().st_size > 0:
                print(f"✓ Downloaded Sakila SQLite database to {temp_db_path}")
                return temp_db_path
            else:
                print("✗ Downloaded file is empty or missing")
                return None

        except Exception as e:
            print(f"✗ Failed to download Sakila SQLite database: {e}")
            return None

    def install_sakila_sqlite(self, db_path: Path, target_dir: Optional[Path] = None) -> bool:
        """Install the Sakila SQLite database to the specified directory."""
        try:
            # Use provided target directory or default to .sqlbot/profiles/Sakila/data
            if target_dir is None:
                target_dir = Path(".sqlbot/profiles/Sakila/data")
            
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / "sakila.db"

            # Copy database file
            shutil.copy2(db_path, target_path)

            if target_path.exists():
                print(f"✓ Sakila SQLite database installed as {target_path}")
                return True
            else:
                print("✗ Failed to copy database file")
                return False

        except Exception as e:
            print(f"✗ Failed to install Sakila SQLite database: {e}")
            return False

    def verify_sqlite_installation(self, db_path: Optional[Path] = None) -> bool:
        """Verify the SQLite database installation."""
        if db_path is None:
            db_path = Path(".sqlbot/profiles/Sakila/data/sakila.db")

        print("Verifying Sakila SQLite database installation...")

        if not db_path.exists():
            print(f"✗ Database file not found: {db_path}")
            return False

        try:
            # Test database connectivity and content
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check tables
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            print(f"✓ Found {table_count} tables")

            # Check key data
            cursor.execute("SELECT COUNT(*) FROM film")
            film_count = cursor.fetchone()[0]
            print(f"✓ Found {film_count} films")

            cursor.execute("SELECT COUNT(*) FROM customer")
            customer_count = cursor.fetchone()[0]
            print(f"✓ Found {customer_count} customers")

            cursor.execute("SELECT COUNT(*) FROM rental")
            rental_count = cursor.fetchone()[0]
            print(f"✓ Found {rental_count} rentals")

            conn.close()

            # Verify expected data counts
            if film_count == 1000 and customer_count == 599 and rental_count > 15000:
                print("✓ Sakila database verification successful")
                return True
            else:
                print(f"✗ Unexpected data counts - films: {film_count}, customers: {customer_count}, rentals: {rental_count}")
                return False

        except Exception as e:
            print(f"✗ Database verification failed: {e}")
            return False

    def create_local_dbt_profile(self, database_path: str) -> bool:
        """Create or update local dbt profile for Sakila."""
        if not self.create_local_profile:
            return True

        try:
            # Create .dbt directory
            dbt_dir = Path('.dbt')
            dbt_dir.mkdir(exist_ok=True)

            profiles_file = dbt_dir / 'profiles.yml'

            # Create backup of existing profiles file before making changes
            if profiles_file.exists():
                try:
                    self.create_profiles_backup(profiles_file)
                except Exception as e:
                    print(f"⚠ Warning: Could not create backup of {profiles_file}: {e}")
                    # Continue with profile creation even if backup fails

            # Sakila profile configuration
            sakila_profile = {
                'Sakila': {
                    'target': 'dev',
                    'outputs': {
                        'dev': {
                            'type': 'sqlite',
                            'threads': 1,
                            'keepalives_idle': 0,
                            'search_path': 'main',
                            'database': 'database',
                            'schema': 'main',
                            'schemas_and_paths': {
                                'main': database_path
                            },
                            'schema_directory': str(Path(database_path).parent)
                        }
                    }
                }
            }

            # Handle existing profiles file
            existing_profiles = {}
            if profiles_file.exists():
                try:
                    with open(profiles_file, 'r') as f:
                        existing_profiles = yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"Warning: Could not read existing profiles.yml: {e}")
                    existing_profiles = {}

            # Merge profiles (Sakila profile takes precedence)
            existing_profiles.update(sakila_profile)

            # Write updated profiles
            with open(profiles_file, 'w') as f:
                yaml.dump(existing_profiles, f, default_flow_style=False, sort_keys=False)

            print(f"✓ Created local dbt profile: {profiles_file}")
            return True

        except Exception as e:
            print(f"✗ Failed to create local dbt profile: {e}")
            return False

    def check_local_dbt_profile(self) -> Tuple[bool, Optional[str]]:
        """Check if local dbt profile exists and is valid."""
        profiles_file = Path('.dbt/profiles.yml')

        if not profiles_file.exists():
            return False, "Local .dbt/profiles.yml does not exist"

        try:
            with open(profiles_file, 'r') as f:
                profiles = yaml.safe_load(f)

            if not profiles or 'Sakila' not in profiles:
                return False, "Sakila profile not found in local profiles.yml"

            sakila_config = profiles['Sakila']
            if 'outputs' not in sakila_config or 'dev' not in sakila_config['outputs']:
                return False, "Invalid Sakila profile configuration"

            # Check if database file exists
            dev_config = sakila_config['outputs']['dev']
            if 'schemas_and_paths' in dev_config and 'main' in dev_config['schemas_and_paths']:
                db_path = dev_config['schemas_and_paths']['main']
                if not Path(db_path).exists():
                    return False, f"Database file not found: {db_path}"
                return True, f"Local Sakila profile is valid (database: {db_path})"
            else:
                return True, "Local Sakila profile is valid (sakila.db configured)"

        except Exception as e:
            return False, f"Error reading local profiles.yml: {e}"

    def create_profiles_backup(self, profiles_file: Path) -> Optional[Path]:
        """Create a timestamped backup of the profiles.yml file before making changes."""
        if not profiles_file.exists():
            return None
        
        try:
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{profiles_file.stem}.backup.{timestamp}{profiles_file.suffix}"
            backup_path = profiles_file.parent / backup_name
            
            # Copy the original file to backup
            shutil.copy2(profiles_file, backup_path)
            
            print(f"✓ Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"⚠ Warning: Could not create backup of {profiles_file}: {e}")
            # Don't fail the entire operation due to backup failure
            return None

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def setup_sakila_database(self, target_dir: Optional[Path] = None) -> bool:
        """Download and install the Sakila database."""
        print("Setting up Sakila SQLite database...")
        print("=" * 50)

        try:
            # Check SQLite availability
            if not self.check_sqlite_availability():
                return False

            # Download database
            db_path = self.download_sakila_sqlite()
            if not db_path:
                return False

            # Install database
            if not self.install_sakila_sqlite(db_path, target_dir):
                return False

            # Verify installation
            target_path = (target_dir or Path(".sqlbot/profiles/Sakila/data")) / "sakila.db"
            if not self.verify_sqlite_installation(target_path):
                return False

            print("\n" + "=" * 50)
            print("✅ Sakila SQLite database setup complete!")
            return True

        except KeyboardInterrupt:
            print("\n\nSetup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            return False
        finally:
            self.cleanup()

    def setup_sakila_profile(self, database_path: Optional[str] = None) -> bool:
        """Set up the Sakila dbt profile."""
        if database_path is None:
            database_path = str(Path(".sqlbot/profiles/Sakila/data/sakila.db").resolve())

        print("Setting up Sakila dbt profile...")
        print("=" * 50)

        try:
            # Create local dbt profile
            if not self.create_local_dbt_profile(database_path):
                return False

            # Verify profile
            if self.create_local_profile:
                profile_valid, message = self.check_local_dbt_profile()
                if profile_valid:
                    print(f"✓ {message}")
                else:
                    print(f"⚠ {message}")
                    return False

            print("\n" + "=" * 50)
            print("✅ Sakila dbt profile setup complete!")
            return True

        except KeyboardInterrupt:
            print("\n\nSetup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Profile setup failed: {e}")
            return False

    def setup_sakila_complete(self, target_dir: Optional[Path] = None) -> bool:
        """Complete Sakila setup: download database and set up profile."""
        print("Complete Sakila Database Setup for SQLBot")
        print("=" * 50)

        try:
            # Setup database
            if not self.setup_sakila_database(target_dir):
                return False

            # Setup profile
            database_path = str((target_dir or Path(".sqlbot/profiles/Sakila/data")) / "sakila.db")
            if not self.setup_sakila_profile(database_path):
                return False

            print("\n" + "=" * 50)
            print("🎉 Complete Sakila setup successful!")
            print("\nNext steps:")
            print("  1. Run integration tests: pytest -m 'integration' tests/integration/")
            print("  2. Start SQLBot: sqlbot --profile Sakila")
            print("  3. Try queries like: 'How many films are in the database?'")

            return True

        except KeyboardInterrupt:
            print("\n\nSetup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Complete setup failed: {e}")
            return False


def download_sakila_database(target_dir: Optional[Path] = None) -> bool:
    """Convenience function to download Sakila database."""
    manager = SakilaManager(create_local_profile=False)
    return manager.setup_sakila_database(target_dir)


def setup_sakila_profile(database_path: Optional[str] = None) -> bool:
    """Convenience function to set up Sakila dbt profile."""
    manager = SakilaManager(create_local_profile=True)
    return manager.setup_sakila_profile(database_path)


def setup_sakila_complete(target_dir: Optional[Path] = None) -> bool:
    """Convenience function for complete Sakila setup."""
    manager = SakilaManager(create_local_profile=True)
    return manager.setup_sakila_complete(target_dir)
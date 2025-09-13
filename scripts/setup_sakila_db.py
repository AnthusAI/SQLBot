#!/usr/bin/env python3
"""
Sakila SQLite Database Setup Script

Downloads and installs the Sakila sample database as SQLite for SQLBot integration testing.
The Sakila database is a well-known sample database containing DVD rental store data.

Usage:
    python scripts/setup_sakila_db.py [--no-local-profile]
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import yaml
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class SakilaSetup:
    """Downloads and installs the Sakila sample database as SQLite."""

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

    def download_sakila_sqlite(self) -> Path:
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

    def install_sakila_sqlite(self, db_path: Path) -> bool:
        """Install the Sakila SQLite database to the profiles directory."""
        try:
            # Create target directory
            target_dir = Path("profiles/Sakila/data")
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

    def verify_sqlite_installation(self, db_path: Path = None) -> bool:
        """Verify the SQLite database installation."""
        if db_path is None:
            db_path = Path("profiles/Sakila/data/sakila.db")

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
        """Create or update local .dbt profile for Sakila."""
        if not self.create_local_profile:
            return True

        try:
            # Create .dbt directory
            dbt_dir = Path('.dbt')
            dbt_dir.mkdir(exist_ok=True)

            profiles_file = dbt_dir / 'profiles.yml'

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

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def run(self) -> bool:
        """Run the complete Sakila SQLite setup process."""
        print("Sakila Database Setup for Integration Testing")
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
            if not self.install_sakila_sqlite(db_path):
                return False

            # Verify installation
            if not self.verify_sqlite_installation():
                return False

            # Create local dbt profile
            target_db_path = str(Path("profiles/Sakila/data/sakila.db").resolve())
            if not self.create_local_dbt_profile(target_db_path):
                return False

            # Verify profile
            if self.create_local_profile:
                profile_valid, message = self.check_local_dbt_profile()
                if profile_valid:
                    print(f"✓ {message}")
                else:
                    print(f"⚠ {message}")

            print("\n" + "=" * 50)
            print("✅ Sakila SQLite database setup complete!")
            print("\nNext steps:")
            print("  1. Run integration tests: pytest -m 'integration' tests/integration/")
            print("  2. Start SQLBot: sqlbot --profile Sakila")
            print("  3. Try queries like: 'How many films are in the database?'")

            return True

        except KeyboardInterrupt:
            print("\n\nSetup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="Download and install Sakila sample database for SQLBot integration testing"
    )
    parser.add_argument(
        "--no-local-profile",
        action="store_true",
        help="Skip creating local .dbt/profiles.yml (use global ~/.dbt/profiles.yml instead)"
    )

    args = parser.parse_args()

    # Create and run setup
    setup = SakilaSetup(create_local_profile=not args.no_local_profile)

    try:
        success = setup.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nSetup interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
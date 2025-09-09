#!/usr/bin/env python3
"""
Sakila Database Reset Script

This script deletes and restores the Sakila sample database.
Supports both MySQL and SQLite backends.

Usage:
    python reset_sakila_db.py [--database {mysql,sqlite}] [--user USERNAME] [--password PASSWORD] [--host HOST] [--port PORT]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from setup_sakila_db import SakilaSetup


class SakilaReset:
    """Handles deleting and restoring the Sakila sample database."""
    
    def __init__(self, database_type: str = "sqlite", user: str = "root", password: Optional[str] = None, 
                 host: str = "localhost", port: int = 3306):
        self.database_type = database_type.lower()
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        
    def delete_sqlite_database(self) -> bool:
        """Delete the SQLite Sakila database file."""
        db_path = Path("profiles/Sakila/data/sakila.db")
        
        if db_path.exists():
            try:
                os.remove(db_path)
                print(f"✓ Deleted SQLite database: {db_path}")
                return True
            except Exception as e:
                print(f"✗ Failed to delete SQLite database: {e}")
                return False
        else:
            print("ℹ SQLite database file not found (already deleted or never existed)")
            return True
    
    def delete_mysql_database(self) -> bool:
        """Delete the MySQL Sakila database."""
        try:
            base_cmd = [
                "mysql",
                f"--user={self.user}",
                f"--host={self.host}",
                f"--port={self.port}"
            ]
            
            if self.password:
                base_cmd.append(f"--password={self.password}")
            
            # Check if database exists first
            check_cmd = base_cmd + ["--execute=SHOW DATABASES LIKE 'sakila';"]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"✗ Failed to check for database existence: {result.stderr}")
                return False
            
            if "sakila" not in result.stdout:
                print("ℹ MySQL Sakila database not found (already deleted or never existed)")
                return True
            
            # Drop the database
            drop_cmd = base_cmd + ["--execute=DROP DATABASE IF EXISTS sakila;"]
            result = subprocess.run(drop_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"✗ Failed to drop MySQL database: {result.stderr}")
                return False
            
            print("✓ Deleted MySQL Sakila database")
            return True
            
        except subprocess.TimeoutExpired:
            print("✗ Database deletion timed out")
            return False
        except Exception as e:
            print(f"✗ Failed to delete MySQL database: {e}")
            return False
    
    def clean_profile_artifacts(self) -> bool:
        """Clean up profile-related artifacts."""
        try:
            sakila_profile_dir = Path("profiles/Sakila")
            
            # Clean target directory
            target_dir = sakila_profile_dir / "target"
            if target_dir.exists():
                shutil.rmtree(target_dir)
                print("✓ Cleaned target directory")
            
            # Clean logs directory
            logs_dir = sakila_profile_dir / "logs"
            if logs_dir.exists():
                shutil.rmtree(logs_dir)
                print("✓ Cleaned logs directory")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to clean profile artifacts: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Delete and restore the Sakila database."""
        print("Sakila Database Reset")
        print("=" * 50)
        
        try:
            # Delete the database
            print("Step 1: Deleting existing database...")
            if self.database_type == "sqlite":
                if not self.delete_sqlite_database():
                    return False
            else:
                if not self.delete_mysql_database():
                    return False
            
            # Clean profile artifacts
            print("\nStep 2: Cleaning profile artifacts...")
            if not self.clean_profile_artifacts():
                print("⚠ Warning: Failed to clean some profile artifacts, continuing...")
            
            # Restore the database using the existing setup script
            print("\nStep 3: Restoring database...")
            setup = SakilaSetup(
                database_type=self.database_type,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            
            if not setup.run():
                print("✗ Failed to restore database")
                return False
            
            print("\n" + "=" * 50)
            print("✓ Sakila database reset completed successfully!")
            if self.database_type == "sqlite":
                print("Database file: profiles/Sakila/data/sakila.db")
            else:
                print("MySQL database 'sakila' has been restored")
            print("=" * 50)
            return True
            
        except KeyboardInterrupt:
            print("\n✗ Reset interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Reset failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Delete and restore Sakila sample database"
    )
    parser.add_argument(
        "--database", "-d",
        choices=["mysql", "sqlite"],
        default="sqlite",
        help="Database type to use (default: sqlite)"
    )
    parser.add_argument(
        "--user", "-u", 
        default="root", 
        help="MySQL username (default: root, ignored for SQLite)"
    )
    parser.add_argument(
        "--password", "-p", 
        help="MySQL password (will prompt if not provided and MySQL is available, ignored for SQLite)"
    )
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="MySQL host (default: localhost, ignored for SQLite)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=3306, 
        help="MySQL port (default: 3306, ignored for SQLite)"
    )
    
    args = parser.parse_args()
    
    # For SQLite, we can run directly
    if args.database == "sqlite":
        reset = SakilaReset(
            database_type=args.database,
            user=args.user,
            password=args.password,
            host=args.host,
            port=args.port
        )
        success = reset.reset_database()
        return 0 if success else 1
    
    # For MySQL, check availability and prompt for password if needed
    setup_checker = SakilaSetup(
        database_type=args.database,
        user=args.user,
        password=args.password,
        host=args.host,
        port=args.port
    )
    
    print("Sakila Database Reset")
    print("=" * 50)
    
    if not setup_checker.check_mysql_availability():
        setup_checker.show_mysql_install_help()
        return 1
    
    # Only prompt for password if MySQL is available and password not provided
    password = args.password
    if not password:
        import getpass
        try:
            password = getpass.getpass(f"Enter MySQL password for user '{args.user}': ")
        except KeyboardInterrupt:
            print("\nReset cancelled.")
            return 1
    
    # Create reset instance with password
    reset = SakilaReset(
        database_type=args.database,
        user=args.user,
        password=password,
        host=args.host,
        port=args.port
    )
    
    success = reset.reset_database()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
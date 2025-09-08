#!/usr/bin/env python3
"""
Sakila Database Setup Script for Integration Testing

This script downloads and installs the Sakila sample database.
Supports both MySQL and SQLite backends.

Usage:
    python setup_sakila_db.py [--database {mysql,sqlite}] [--user USERNAME] [--password PASSWORD] [--host HOST] [--port PORT]
"""

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


class SakilaSetup:
    """Handles downloading and installing the Sakila sample database."""
    
    SAKILA_MYSQL_URL = "https://downloads.mysql.com/docs/sakila-db.tar.gz"
    SAKILA_SQLITE_URL = "https://github.com/siara-cc/sakila_sqlite3/raw/master/sakila.db"
    MYSQL_INSTALL_URLS = {
        "general": "https://dev.mysql.com/downloads/mysql/",
        "ubuntu": "https://dev.mysql.com/doc/mysql-apt-repo-quick-guide/en/",
        "centos": "https://dev.mysql.com/doc/mysql-yum-repo-quick-guide/en/",
        "windows": "https://dev.mysql.com/doc/refman/8.0/en/windows-installation.html",
        "macos": "https://dev.mysql.com/doc/refman/8.0/en/macos-installation.html"
    }
    
    def __init__(self, database_type: str = "mysql", user: str = "root", password: Optional[str] = None, 
                 host: str = "localhost", port: int = 3306):
        self.database_type = database_type.lower()
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.temp_dir = None
    
    def check_sqlite_availability(self) -> bool:
        """Check if SQLite is installed and accessible."""
        try:
            result = subprocess.run(
                ["sqlite3", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                print(f"✓ Found SQLite: {result.stdout.strip()}")
                return True
            else:
                print("✗ SQLite not working properly")
                return False
                
        except FileNotFoundError:
            print("✗ SQLite command-line client not found")
            return False
        except subprocess.TimeoutExpired:
            print("✗ SQLite check timed out")
            return False
        except Exception as e:
            print(f"✗ Error checking SQLite: {e}")
            return False
    
    def show_sqlite_install_help(self):
        """Display helpful information about installing SQLite."""
        print("\n" + "="*60)
        print("SQLite Installation Required")
        print("="*60)
        print("SQLite is not installed. Please install SQLite first.")
        print("\nQuick installation commands:")
        print("Amazon Linux/CentOS/RHEL:")
        print("  sudo dnf install sqlite")
        print("  # or for older versions:")
        print("  sudo yum install sqlite")
        print("\nUbuntu/Debian:")
        print("  sudo apt update && sudo apt install sqlite3")
        print("\nmacOS (with Homebrew):")
        print("  brew install sqlite")
        print("\nNote: SQLite is often pre-installed on many systems.")
        print("="*60)

    def check_mysql_availability(self) -> bool:
        """Check if MySQL is installed and accessible."""
        try:
            # Try to run mysql --version first
            result = subprocess.run(
                ["mysql", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                return False
            
            print(f"✓ Found MySQL: {result.stdout.strip()}")
            
            # Try to connect to MySQL server
            cmd = [
                "mysql", 
                f"--user={self.user}",
                f"--host={self.host}",
                f"--port={self.port}",
                "--execute=SELECT VERSION();"
            ]
            
            if self.password:
                cmd.append(f"--password={self.password}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✓ Successfully connected to MySQL server")
                return True
            else:
                print(f"✗ Failed to connect to MySQL server: {result.stderr.strip()}")
                return False
                
        except FileNotFoundError:
            print("✗ MySQL command-line client not found")
            return False
        except subprocess.TimeoutExpired:
            print("✗ MySQL connection timed out")
            return False
        except Exception as e:
            print(f"✗ Error checking MySQL: {e}")
            return False
    
    def show_mysql_install_help(self):
        """Display helpful information about installing MySQL."""
        print("\n" + "="*60)
        print("MySQL Installation Required")
        print("="*60)
        print("MySQL is not installed or not accessible. Please install MySQL first.")
        print("\nHelpful installation guides:")
        print(f"• General MySQL Downloads: {self.MYSQL_INSTALL_URLS['general']}")
        print(f"• Ubuntu/Debian: {self.MYSQL_INSTALL_URLS['ubuntu']}")
        print(f"• CentOS/RHEL: {self.MYSQL_INSTALL_URLS['centos']}")
        print(f"• Windows: {self.MYSQL_INSTALL_URLS['windows']}")
        print(f"• macOS: {self.MYSQL_INSTALL_URLS['macos']}")
        
        print("\nQuick installation commands:")
        print("Ubuntu/Debian:")
        print("  sudo apt update && sudo apt install mysql-server")
        print("\nAmazon Linux 2023:")
        print("  sudo wget https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm")
        print("  sudo dnf install mysql80-community-release-el9-1.noarch.rpm -y")
        print("  sudo rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023")
        print("  sudo dnf install mysql-community-server -y")
        print("  sudo systemctl start mysqld")
        print("  sudo systemctl enable mysqld")
        print("\nAmazon Linux 2:")
        print("  sudo yum localinstall https://dev.mysql.com/get/mysql80-community-release-el7-1.noarch.rpm")
        print("  sudo yum install mysql-community-server -y")
        print("  sudo systemctl start mysqld")
        print("  sudo systemctl enable mysqld")
        print("\nCentOS/RHEL:")
        print("  sudo yum install mysql-server")
        print("  # or for newer versions:")
        print("  sudo dnf install mysql-server")
        print("\nmacOS (with Homebrew):")
        print("  brew install mysql")
        print("\nAfter installation, start the MySQL service and run:")
        print("  sudo mysql_secure_installation")
        print("\nNote: On Amazon Linux, MySQL generates a temporary root password.")
        print("Find it with: sudo grep 'temporary password' /var/log/mysqld.log")
        print("="*60)
    
    def download_sakila_sqlite(self) -> Path:
        """Download the Sakila SQLite database file."""
        print("Downloading Sakila SQLite database...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="sakila_sqlite_setup_")
        db_path = Path(self.temp_dir) / "sakila.db"
        
        try:
            with urllib.request.urlopen(self.SAKILA_SQLITE_URL) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(db_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="")
                
                print(f"\n✓ Downloaded Sakila SQLite database to {db_path}")
                return db_path
                
        except Exception as e:
            print(f"✗ Failed to download Sakila SQLite database: {e}")
            raise
    
    def install_sakila_sqlite(self, db_path: Path) -> bool:
        """Install the Sakila SQLite database by copying it to the current directory."""
        try:
            target_path = Path("sakila.db")
            
            # Copy the database file to current directory
            import shutil
            shutil.copy2(db_path, target_path)
            
            print(f"✓ Sakila SQLite database installed as {target_path.absolute()}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to install Sakila SQLite database: {e}")
            return False
    
    def verify_sqlite_installation(self, db_path: Path = None) -> bool:
        """Verify that the Sakila SQLite database was installed correctly."""
        print("Verifying Sakila SQLite database installation...")
        
        if db_path is None:
            db_path = Path("sakila.db")
        
        if not db_path.exists():
            print(f"✗ Database file {db_path} not found")
            return False
        
        try:
            # Check tables
            result = subprocess.run(
                ["sqlite3", str(db_path), ".tables"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"✗ Failed to query tables: {result.stderr}")
                return False
            
            tables = result.stdout.strip().split()
            table_count = len(tables)
            
            if table_count < 15:  # SQLite version might have fewer tables
                print(f"✗ Expected ~15+ tables, found {table_count}")
                return False
            
            print(f"✓ Found {table_count} tables")
            
            # Check film count
            result = subprocess.run(
                ["sqlite3", str(db_path), "SELECT COUNT(*) FROM film;"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"✗ Failed to count films: {result.stderr}")
                return False
            
            try:
                film_count = int(result.stdout.strip())
                if film_count != 1000:
                    print(f"✗ Expected 1000 films, found {film_count}")
                    return False
                print(f"✓ Found {film_count} films")
            except ValueError:
                print("✗ Could not parse film count")
                return False
            
            print("✓ Sakila SQLite database installation verified successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Verification failed: {e}")
            return False

    def download_sakila(self) -> Path:
        """Download the Sakila database archive."""
        print("Downloading Sakila database...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="sakila_setup_")
        archive_path = Path(self.temp_dir) / "sakila-db.tar.gz"
        
        try:
            with urllib.request.urlopen(self.SAKILA_MYSQL_URL) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(archive_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="")
                
                print(f"\n✓ Downloaded Sakila database to {archive_path}")
                return archive_path
                
        except Exception as e:
            print(f"✗ Failed to download Sakila database: {e}")
            raise
    
    def extract_sakila(self, archive_path: Path) -> Path:
        """Extract the Sakila database archive."""
        print("Extracting Sakila database...")
        
        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=self.temp_dir)
            
            extracted_dir = Path(self.temp_dir) / "sakila-db"
            if not extracted_dir.exists():
                raise FileNotFoundError(f"Expected directory {extracted_dir} not found after extraction")
            
            print(f"✓ Extracted to {extracted_dir}")
            return extracted_dir
            
        except Exception as e:
            print(f"✗ Failed to extract Sakila database: {e}")
            raise
    
    def install_sakila(self, sakila_dir: Path) -> bool:
        """Install the Sakila database into MySQL."""
        schema_file = sakila_dir / "sakila-schema.sql"
        data_file = sakila_dir / "sakila-data.sql"
        
        if not schema_file.exists() or not data_file.exists():
            print(f"✗ Required SQL files not found in {sakila_dir}")
            return False
        
        print("Installing Sakila database schema and data...")
        
        try:
            # Build base MySQL command
            base_cmd = [
                "mysql",
                f"--user={self.user}",
                f"--host={self.host}",
                f"--port={self.port}"
            ]
            
            if self.password:
                base_cmd.append(f"--password={self.password}")
            
            # Install schema
            print("Installing schema...")
            schema_cmd = base_cmd + [f"--execute=SOURCE {schema_file};"]
            result = subprocess.run(schema_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"✗ Failed to install schema: {result.stderr}")
                return False
            
            print("✓ Schema installed successfully")
            
            # Install data
            print("Installing data...")
            data_cmd = base_cmd + [f"--execute=SOURCE {data_file};"]
            result = subprocess.run(data_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"✗ Failed to install data: {result.stderr}")
                return False
            
            print("✓ Data installed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            print("✗ Installation timed out")
            return False
        except Exception as e:
            print(f"✗ Installation failed: {e}")
            return False
    
    def verify_installation(self) -> bool:
        """Verify that the Sakila database was installed correctly."""
        print("Verifying Sakila database installation...")
        
        try:
            base_cmd = [
                "mysql",
                f"--user={self.user}",
                f"--host={self.host}",
                f"--port={self.port}",
                "--database=sakila"
            ]
            
            if self.password:
                base_cmd.append(f"--password={self.password}")
            
            # Check tables
            tables_cmd = base_cmd + ["--execute=SHOW FULL TABLES;"]
            result = subprocess.run(tables_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"✗ Failed to query tables: {result.stderr}")
                return False
            
            # Count expected tables (should be 23 according to documentation)
            table_lines = [line for line in result.stdout.split('\n') if '|' in line and 'Tables_in_sakila' not in line]
            table_count = len([line for line in table_lines if line.strip()])
            
            if table_count < 20:  # Allow some flexibility
                print(f"✗ Expected ~23 tables, found {table_count}")
                return False
            
            print(f"✓ Found {table_count} tables")
            
            # Check film count (should be 1000)
            film_cmd = base_cmd + ["--execute=SELECT COUNT(*) FROM film;"]
            result = subprocess.run(film_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"✗ Failed to count films: {result.stderr}")
                return False
            
            # Extract count from result
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                try:
                    film_count = int(lines[1])
                    if film_count != 1000:
                        print(f"✗ Expected 1000 films, found {film_count}")
                        return False
                    print(f"✓ Found {film_count} films")
                except ValueError:
                    print("✗ Could not parse film count")
                    return False
            
            print("✓ Sakila database installation verified successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Verification failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temporary files from {self.temp_dir}")
    
    def run(self) -> bool:
        """Run the complete Sakila setup process."""
        try:
            print("Sakila Database Setup for Integration Testing")
            print("=" * 50)
            
            if self.database_type == "sqlite":
                # Check SQLite availability
                if not self.check_sqlite_availability():
                    self.show_sqlite_install_help()
                    return False
                return self.run_sqlite_installation()
            else:
                # Check MySQL availability
                if not self.check_mysql_availability():
                    self.show_mysql_install_help()
                    return False
                return self.run_installation_only()
            
        except KeyboardInterrupt:
            print("\n✗ Setup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def run_sqlite_installation(self) -> bool:
        """Run SQLite-specific installation."""
        try:
            # Download SQLite database
            db_path = self.download_sakila_sqlite()
            
            # Install SQLite database
            if not self.install_sakila_sqlite(db_path):
                return False
            
            # Verify installation
            if not self.verify_sqlite_installation():
                return False
            
            print("\n" + "=" * 50)
            print("✓ Sakila SQLite database setup completed successfully!")
            print("Database file: sakila.db")
            print("You can now run integration tests against this SQLite database.")
            print("Example: sqlite3 sakila.db \"SELECT COUNT(*) FROM film;\"")
            print("=" * 50)
            return True
            
        except KeyboardInterrupt:
            print("\n✗ Setup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def run_installation_only(self) -> bool:
        """Run only the installation part (assumes MySQL check already done)."""
        try:
            # Download Sakila
            archive_path = self.download_sakila()
            
            # Extract Sakila
            sakila_dir = self.extract_sakila(archive_path)
            
            # Install Sakila
            if not self.install_sakila(sakila_dir):
                return False
            
            # Verify installation
            if not self.verify_installation():
                return False
            
            print("\n" + "=" * 50)
            print("✓ Sakila database setup completed successfully!")
            print("You can now run integration tests against the 'sakila' database.")
            print("=" * 50)
            return True
            
        except KeyboardInterrupt:
            print("\n✗ Setup interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and install Sakila sample database for integration testing"
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
    
    # Create setup instance
    setup = SakilaSetup(
        database_type=args.database,
        user=args.user,
        password=args.password,  # May be None initially
        host=args.host,
        port=args.port
    )
    
    # For SQLite, we can run directly
    if args.database == "sqlite":
        success = setup.run()
        return 0 if success else 1
    
    # For MySQL, check availability before asking for password
    print("Sakila Database Setup for Integration Testing")
    print("=" * 50)
    
    if not setup.check_mysql_availability():
        setup.show_mysql_install_help()
        return 1
    
    # Only prompt for password if MySQL is available and password not provided
    if not args.password:
        import getpass
        try:
            password = getpass.getpass(f"Enter MySQL password for user '{args.user}': ")
            setup.password = password
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return 1
    
    # Run the rest of the setup (skip the initial checks since we already did them)
    success = setup.run_installation_only()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

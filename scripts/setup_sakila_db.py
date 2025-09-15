#!/usr/bin/env python3
"""
Sakila SQLite Database Setup Script

Downloads and installs the Sakila sample database as SQLite for SQLBot integration testing.
The Sakila database is a well-known sample database containing DVD rental store data.

Usage:
    python scripts/setup_sakila_db.py [--no-local-profile]
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path to import sqlbot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from sqlbot.core.sakila import SakilaManager


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
    setup = SakilaManager(create_local_profile=not args.no_local_profile)

    try:
        success = setup.setup_sakila_complete()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nSetup interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
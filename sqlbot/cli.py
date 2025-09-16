"""
Command Line Interface for SQLBot

This module provides CLI subcommands for SQLBot functionality including
Sakila database setup and other utilities.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core.sakila import SakilaManager


def handle_download_command(args):
    """Handle 'sqlbot download' subcommands."""
    if args.database == 'sakila':
        target_dir = None
        if args.target_dir:
            target_dir = Path(args.target_dir)
        
        manager = SakilaManager(create_local_profile=False)
        success = manager.setup_sakila_database(target_dir)
        return 0 if success else 1
    else:
        print(f"Unknown database: {args.database}")
        print("Available databases: sakila")
        return 1


def handle_setup_command(args):
    """Handle 'sqlbot setup' subcommands."""
    if args.component == 'sakila':
        # Complete Sakila setup (database + profile)
        target_dir = None
        if args.target_dir:
            target_dir = Path(args.target_dir)
        
        manager = SakilaManager(create_local_profile=True)
        success = manager.setup_sakila_complete(target_dir)
        return 0 if success else 1
    
    elif args.component == 'sakila-profile':
        # Setup only the dbt profile
        database_path = args.database_path
        if database_path is None:
            database_path = str(Path(".sqlbot/profiles/Sakila/data/sakila.db").resolve())
        
        manager = SakilaManager(create_local_profile=True)
        success = manager.setup_sakila_profile(database_path)
        return 0 if success else 1
    
    else:
        print(f"Unknown setup component: {args.component}")
        print("Available components: sakila, sakila-profile")
        return 1


def create_cli_parser():
    """Create the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='sqlbot',
        description='SQLBot: Database Query Bot with AI-powered natural language processing'
    )
    
    # Global arguments
    parser.add_argument('--context', action='store_true', help='Show LLM conversation context')
    parser.add_argument('--profile', help='dbt profile name to use (can be set in .sqlbot/config.yml)')
    parser.add_argument('--preview', action='store_true', help='Preview compiled SQL before executing query')
    parser.add_argument('--dangerous', action='store_true', help='Disable safeguards and allow dangerous SQL operations')
    parser.add_argument('--no-repl', '--norepl', action='store_true', help='Exit after executing query without starting interactive mode')
    parser.add_argument('--text', action='store_true', help='Use text-based REPL with shared session (for debugging)')
    parser.add_argument('--history', action='store_true', help='Show conversation history panel (for debugging)')
    parser.add_argument('--full-history', action='store_true', help='Show full conversation history without truncation (for debugging)')
    parser.add_argument('--theme', choices=['qbot', 'dark', 'light'], default='qbot', help='Color theme (default: qbot)')
    
    # Create subparsers (but make them optional)
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=False)
    
    # Download subcommand
    download_parser = subparsers.add_parser('download', help='Download sample databases')
    download_parser.add_argument('database', choices=['sakila'], help='Database to download')
    download_parser.add_argument('--target-dir', help='Target directory for database installation')
    download_parser.set_defaults(func=handle_download_command)
    
    # Setup subcommand
    setup_parser = subparsers.add_parser('setup', help='Set up databases and profiles')
    setup_parser.add_argument('component', choices=['sakila', 'sakila-profile'], 
                             help='Component to set up (sakila: complete setup, sakila-profile: profile only)')
    setup_parser.add_argument('--target-dir', help='Target directory for database installation')
    setup_parser.add_argument('--database-path', help='Path to existing database file (for profile setup)')
    setup_parser.set_defaults(func=handle_setup_command)
    
    # For backward compatibility, still support direct query execution
    parser.add_argument('query', nargs='*', help='Query to execute (if no subcommand provided)')
    
    return parser


def parse_args_with_subcommands(args=None):
    """Parse command line arguments with subcommand support."""
    # Handle case where args is None (from sys.argv)
    if args is None:
        args_list = sys.argv[1:]  # Exclude program name
    else:
        args_list = args if isinstance(args, list) else [args]
    
    # Check if the first argument is a known subcommand
    known_subcommands = ['download', 'setup']
    
    if args_list and args_list[0] in known_subcommands:
        # This is a subcommand - parse normally
        parser = create_cli_parser()
        parsed_args = parser.parse_args(args_list)
        return parsed_args
    else:
        # This might be a query or no arguments - use a simpler parser
        # Create a parser without subcommands for backward compatibility
        parser = argparse.ArgumentParser(
            prog='sqlbot',
            description='SQLBot: Database Query Bot with AI-powered natural language processing',
            add_help=False  # We'll handle help manually to maintain compatibility
        )
        
        # Add all the same global arguments
        parser.add_argument('--context', action='store_true', help='Show LLM conversation context')
        parser.add_argument('--profile', help='dbt profile name to use (can be set in .sqlbot/config.yml)')
        parser.add_argument('--preview', action='store_true', help='Preview compiled SQL before executing query')
        parser.add_argument('--dangerous', action='store_true', help='Disable safeguards and allow dangerous SQL operations')
        parser.add_argument('--no-repl', '--norepl', action='store_true', help='Exit after executing query without starting interactive mode')
        parser.add_argument('--text', action='store_true', help='Use text-based REPL with shared session (for debugging)')
        parser.add_argument('--history', action='store_true', help='Show conversation history panel (for debugging)')
        parser.add_argument('--full-history', action='store_true', help='Show full conversation history without truncation (for debugging)')
        parser.add_argument('--theme', choices=['qbot', 'dark', 'light'], default='qbot', help='Color theme (default: qbot)')
        parser.add_argument('--help', '-h', action='store_true', help='Show help')
        parser.add_argument('query', nargs='*', help='Query to execute')
        
        parsed_args = parser.parse_args(args_list)
        parsed_args.command = None  # No subcommand
        return parsed_args


def handle_cli_subcommands(args):
    """Handle CLI subcommands and return exit code."""
    if hasattr(args, 'func'):
        return args.func(args)
    return 0  # No subcommand, continue with normal operation
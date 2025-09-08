"""
Textual REPL Entry Point for QBot

This module provides the entry point for running QBot with the Textual TUI interface.
It integrates with the existing CLI argument parsing and configuration system.
"""

import asyncio
import sys
from typing import Optional

from qbot.core import QBotAgent, QBotConfig
from .textual_app import QBotTextualApp, create_textual_app_from_args


class QBotTextualREPL:
    """Textual REPL interface for QBot"""
    
    def __init__(self, agent: QBotAgent, initial_query: Optional[str] = None):
        """
        Initialize Textual REPL
        
        Args:
            agent: QBotAgent instance
            initial_query: Optional initial query to execute
        """
        self.agent = agent
        self.initial_query = initial_query
        self.app: Optional[QBotTextualApp] = None
    
    def run(self) -> None:
        """Run the Textual REPL application"""
        self.app = QBotTextualApp(self.agent, initial_query=self.initial_query)
        self.app.run()
    
    async def run_async(self) -> None:
        """Run the Textual REPL application asynchronously"""
        self.app = QBotTextualApp(self.agent, initial_query=self.initial_query)
        await self.app.run_async()


def create_textual_repl_from_args(args) -> QBotTextualREPL:
    """
    Create QBot Textual REPL from command line arguments
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured QBotTextualREPL instance
    """
    # For now, create a minimal agent that integrates with the original working system
    # TODO: Fix the core SDK integration later
    from qbot.core.agent import QBotAgentFactory
    
    try:
        # Try to create agent using factory
        agent = QBotAgentFactory.create_from_env(
            profile=args.profile if hasattr(args, 'profile') else 'qbot',
            read_only=args.read_only if hasattr(args, 'read_only') else False,
            preview_mode=args.preview if hasattr(args, 'preview') else False
        )
    except Exception:
        # Fallback to basic config if factory fails
        config = QBotConfig.from_env(args.profile if hasattr(args, 'profile') else 'qbot')
        if hasattr(args, 'read_only') and args.read_only:
            config.read_only = True
        if hasattr(args, 'preview') and args.preview:
            config.preview_mode = True
        agent = QBotAgent(config)
    
    # Get initial query if provided
    initial_query = None
    if hasattr(args, 'query') and args.query:
        initial_query = ' '.join(args.query)
    
    # Create Textual REPL
    return QBotTextualREPL(agent, initial_query=initial_query)


def main_textual():
    """Main entry point for QBot with Textual interface"""
    import argparse
    
    # Parse arguments exactly like the original qbot command
    parser = argparse.ArgumentParser(description='QBot: Database Query Bot', add_help=False)
    parser.add_argument('--context', action='store_true', help='Show LLM conversation context')
    parser.add_argument('--profile', default='qbot', help='dbt profile name to use (default: qbot)')
    parser.add_argument('--preview', action='store_true', help='Preview compiled SQL before executing query')
    parser.add_argument('--read-only', action='store_true', help='Enable read-only safeguard to block dangerous SQL operations')
    parser.add_argument('--no-repl', '--norepl', action='store_true', help='Exit after executing query without starting interactive mode')
    parser.add_argument('--help', '-h', action='store_true', help='Show help')
    parser.add_argument('query', nargs='*', help='Query to execute')
    
    args = parser.parse_args()
    
    # Handle help
    if args.help:
        parser.print_help()
        sys.exit(0)
    
    try:
        # Handle single query execution (like original qbot)
        if args.query:
            query_text = ' '.join(args.query)
            
            if args.no_repl:
                # Execute single query without starting Textual interface - use original working REPL
                # Import and call the original main function directly
                try:
                    # Set up the arguments for the original system
                    import sys
                    original_argv = sys.argv.copy()
                    sys.argv = ['qbot', '--no-repl', '--profile', args.profile]
                    if args.read_only:
                        sys.argv.append('--read-only')
                    if args.preview:
                        sys.argv.append('--preview')
                    sys.argv.append(query_text)
                    
                    # Import and run the original working main function
                    from qbot.repl import main as original_main
                    original_main()
                    
                finally:
                    # Restore original argv
                    sys.argv = original_argv
                return
            else:
                # Execute query then start Textual interface
                # We'll handle the initial query in the Textual app
                pass
        
        # Start Textual interface (interactive mode)
        repl = create_textual_repl_from_args(args)
        repl.run()
        
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting QBot: {e}")
        sys.exit(1)


def start_textual_interactive(profile: str = "Sakila"):
    """Start Textual interface for interactive mode"""
    import sys
    original_argv = sys.argv.copy()
    try:
        sys.argv = ['qbot', '--profile', profile]
        args = type('Args', (), {
            'profile': profile,
            'read_only': False,
            'preview': False,
            'query': None
        })()
        
        repl = create_textual_repl_from_args(args)
        repl.run()
    finally:
        sys.argv = original_argv


def start_textual_with_query(initial_query: str, profile: str = "Sakila"):
    """Start Textual interface with an initial query"""
    import sys
    original_argv = sys.argv.copy()
    try:
        sys.argv = ['qbot', '--profile', profile, initial_query]
        args = type('Args', (), {
            'profile': profile,
            'read_only': False,
            'preview': False,
            'query': [initial_query]
        })()
        
        repl = create_textual_repl_from_args(args)
        repl.run()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main_textual()

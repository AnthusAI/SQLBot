"""
Textual REPL Entry Point for SQLBot

This module provides the entry point for running SQLBot with the Textual TUI interface.
It integrates with the existing CLI argument parsing and configuration system.
"""

import asyncio
import sys
from typing import Optional

from sqlbot.core import SQLBotAgent, SQLBotConfig
from .textual_app import SQLBotTextualApp, create_textual_app_from_args
from .theme_system import ThemeMode


class SQLBotTextualREPL:
    """Textual REPL interface for SQLBot"""
    
    def __init__(self, agent: SQLBotAgent, initial_query: Optional[str] = None, theme_mode: ThemeMode = ThemeMode.DARK):
        """
        Initialize Textual REPL
        
        Args:
            agent: SQLBotAgent instance
            initial_query: Optional initial query to execute
            theme_mode: Theme mode to use
        """
        self.agent = agent
        self.initial_query = initial_query
        self.theme_mode = theme_mode
        self.app: Optional[SQLBotTextualApp] = None
    
    def run(self) -> None:
        """Run the Textual REPL application"""
        self.app = SQLBotTextualApp(self.agent, initial_query=self.initial_query, theme_mode=self.theme_mode)
        self.app.run()
    
    async def run_async(self) -> None:
        """Run the Textual REPL application asynchronously"""
        self.app = SQLBotTextualApp(self.agent, initial_query=self.initial_query, theme_mode=self.theme_mode)
        await self.app.run_async()


def create_textual_repl_from_args(args) -> SQLBotTextualREPL:
    """
    Create SQLBot Textual REPL from command line arguments
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Configured SQLBotTextualREPL instance
    """
    # For now, create a minimal agent that integrates with the original working system
    # TODO: Fix the core SDK integration later
    from sqlbot.core.agent import SQLBotAgentFactory
    
    try:
        # Try to create agent using factory
        agent = SQLBotAgentFactory.create_from_env(
            profile=args.profile if hasattr(args, 'profile') and args.profile else None,
            dangerous=args.dangerous if hasattr(args, 'dangerous') else False,
            preview_mode=args.preview if hasattr(args, 'preview') else False
        )
    except Exception:
        # Fallback to basic config if factory fails
        config = SQLBotConfig.from_env(args.profile if hasattr(args, 'profile') and args.profile else None)
        if hasattr(args, 'dangerous') and args.dangerous:
            config.dangerous = True
        if hasattr(args, 'preview') and args.preview:
            config.preview_mode = True
        agent = SQLBotAgent(config)
    
    # Get initial query if provided
    initial_query = None
    if hasattr(args, 'query') and args.query:
        initial_query = ' '.join(args.query)
    
    # Get theme from args if provided
    theme_mode = ThemeMode.DARK  # default
    if hasattr(args, 'theme'):
        # Try to find the theme mode by value
        for mode in ThemeMode:
            if mode.value == args.theme:
                theme_mode = mode
                break
    
    # Create Textual REPL
    return SQLBotTextualREPL(agent, initial_query=initial_query, theme_mode=theme_mode)


def main_textual():
    """Main entry point for SQLBot with Textual interface"""
    import argparse
    
    # Parse arguments exactly like the original qbot command
    parser = argparse.ArgumentParser(description='SQLBot: Database Query Bot', add_help=False)
    parser.add_argument('--context', action='store_true', help='Show LLM conversation context')
    parser.add_argument('--profile', help='dbt profile name to use (can be set in .sqlbot/config.yml)')
    parser.add_argument('--preview', action='store_true', help='Preview compiled SQL before executing query')
    parser.add_argument('--dangerous', action='store_true', help='Disable safeguards and allow dangerous SQL operations')
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
                    sys.argv = ['sqlbot', '--no-repl', '--profile', args.profile]
                    if args.dangerous:
                        sys.argv.append('--dangerous')
                    if args.preview:
                        sys.argv.append('--preview')
                    sys.argv.append(query_text)
                    
                    # Import and run the original working main function
                    from sqlbot.repl import main as original_main
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
        print(f"Error starting SQLBot: {e}")
        sys.exit(1)


def start_textual_interactive(profile: str = "Sakila"):
    """Start Textual interface for interactive mode"""
    import sys
    original_argv = sys.argv.copy()
    try:
        sys.argv = ['sqlbot', '--profile', profile]
        args = type('Args', (), {
            'profile': profile,
            'dangerous': False,
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
        sys.argv = ['sqlbot', '--profile', profile, initial_query]
        args = type('Args', (), {
            'profile': profile,
            'dangerous': False,
            'preview': False,
            'query': [initial_query]
        })()
        
        repl = create_textual_repl_from_args(args)
        repl.run()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main_textual()

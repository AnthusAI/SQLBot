"""
Command handling for SQLBot REPL interface
"""

import sys
from typing import Optional, Dict, Callable
from sqlbot.core import SQLBotAgent
from .formatting import ResultFormatter


class CommandHandler:
    """Handles slash commands in the REPL"""
    
    def __init__(self, agent: SQLBotAgent, formatter: ResultFormatter):
        self.agent = agent
        self.formatter = formatter
        self.commands: Dict[str, Callable] = {
            'help': self._cmd_help,
            'tables': self._cmd_tables,
            'schema': self._cmd_schema,
            'profile': self._cmd_profile,
            'readonly': self._cmd_readonly,
            'dangerous': self._cmd_dangerous,
            'preview': self._cmd_preview,
            'status': self._cmd_status,
            'exit': self._cmd_exit,
            'quit': self._cmd_exit,
            'no-repl': self._cmd_no_repl,
            'norepl': self._cmd_no_repl,
        }
    
    def handle_command(self, command_line: str) -> bool:
        """
        Handle a slash command
        
        Args:
            command_line: The command line starting with /
            
        Returns:
            True if should continue REPL, False if should exit
        """
        # Remove leading slash and split into command and args
        command_line = command_line[1:].strip()
        parts = command_line.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command in self.commands:
            return self.commands[command](args)
        else:
            self.formatter.format_error(f"Unknown command: /{command}")
            self.formatter.format_system_message("Type /help for available commands")
            return True
    
    def _cmd_help(self, args: str) -> bool:
        """Show help information"""
        help_text = """
[bold magenta2]SQLBot Commands:[/bold magenta2]

[bold cyan]/help[/bold cyan] - Show this help message
[bold cyan]/tables[/bold cyan] - List available database tables
[bold cyan]/schema[/bold cyan] - Show schema information
[bold cyan]/profile[/bold cyan] - Show current profile information
[bold cyan]/dangerous[/bold cyan] - Toggle dangerous operation mode
[bold cyan]/preview[/bold cyan] - Toggle preview mode (compile only)
[bold cyan]/status[/bold cyan] - Show SQLBot status and configuration
[bold cyan]/exit[/bold cyan] or [bold cyan]/quit[/bold cyan] - Exit SQLBot
[bold cyan]/no-repl[/bold cyan] - Exit interactive mode

[bold green]Query Types:[/bold green]
• [green]Natural Language[/green]: Just type your question
• [green]SQL/dbt[/green]: End queries with semicolon (;)

[bold blue]Examples:[/bold blue]
• How many users are active today?
• SELECT COUNT(*) FROM customer;
"""
        self.formatter.format_help_text(help_text)
        return True
    
    def _cmd_tables(self, args: str) -> bool:
        """List available tables"""
        try:
            tables = self.agent.get_tables()
            self.formatter.format_table_list([{
                'source_name': t.source_name,
                'name': t.name,
                'schema': t.schema,
                'description': t.description or 'No description'
            } for t in tables])
        except Exception as e:
            self.formatter.format_error(f"Could not load tables: {e}")
        return True
    
    def _cmd_schema(self, args: str) -> bool:
        """Show schema information"""
        try:
            schema_info = self.agent.get_schema_info()
            
            if not schema_info.get('sources'):
                self.formatter.format_warning("No schema information found")
                return True
            
            # Format schema info
            from rich.tree import Tree
            from rich.console import Console
            
            tree = Tree("📊 Database Schema")
            
            for source in schema_info['sources']:
                source_name = source.get('name', 'unknown')
                schema_name = source.get('schema', 'dbo')
                source_node = tree.add(f"[cyan]{source_name}[/cyan] ([blue]{schema_name}[/blue])")
                
                for table in source.get('tables', []):
                    table_name = table.get('name', 'unknown')
                    table_desc = table.get('description', 'No description')
                    table_node = source_node.add(f"[magenta]{table_name}[/magenta] - {table_desc}")
                    
                    # Add columns
                    for column in table.get('columns', []):
                        col_name = column.get('name', '')
                        col_desc = column.get('description', '')
                        if col_name:
                            table_node.add(f"[white]{col_name}[/white]: {col_desc}")
            
            self.formatter.console.print(tree)
            
        except Exception as e:
            self.formatter.format_error(f"Could not load schema: {e}")
        return True
    
    def _cmd_profile(self, args: str) -> bool:
        """Show profile information"""
        try:
            profile_info = self.agent.get_profile_info()
            
            info_text = f"""
[bold]Profile:[/bold] {profile_info.name}
[bold]Target:[/bold] {profile_info.target}
[bold]Schema Path:[/bold] {profile_info.schema_path or 'Not found'}
[bold]Macro Paths:[/bold] {len(profile_info.macro_paths)} found
[bold]Tables:[/bold] {len(profile_info.tables)} available
"""
            
            self.formatter.console.print(info_text)
            
        except Exception as e:
            self.formatter.format_error(f"Could not load profile info: {e}")
        return True
    
    def _cmd_readonly(self, args: str) -> bool:
        """Legacy read-only command - redirects to dangerous"""
        self.formatter.format_warning("The /readonly command is deprecated. Use /dangerous instead.")
        return self._cmd_dangerous("off" if args.strip().lower() in ['on', 'enable', 'true'] else "on")
    
    def _cmd_dangerous(self, args: str) -> bool:
        """Toggle dangerous mode (disables safeguards)"""
        # Import the global safeguard state
        import sqlbot.repl as repl_module
        
        if not args.strip():
            # Show current status
            if repl_module.READONLY_MODE:
                # Safeguards are enabled (safe mode)
                self.formatter.format_success("🔒 Safeguards are ENABLED")
                self.formatter.format_system_message("Dangerous operations are blocked.")
                self.formatter.format_system_message("Use '/dangerous on' to disable safeguards.")
            else:
                # Safeguards are disabled (dangerous mode)
                self.formatter.format_error("⚠️  Dangerous mode is ENABLED")
                self.formatter.format_system_message("All operations allowed - safeguards disabled.")
                self.formatter.format_system_message("Use '/dangerous off' to re-enable safeguards.")
        elif args.strip().lower() in ['on', 'enable', 'true']:
            repl_module.READONLY_MODE = False  # Disable safeguards = enable dangerous mode
            self.formatter.format_success("⚠️  Dangerous mode ENABLED")
            self.formatter.format_system_message("Safeguards are DISABLED - all operations allowed.")
        elif args.strip().lower() in ['off', 'disable', 'false']:
            repl_module.READONLY_MODE = True   # Enable safeguards = disable dangerous mode
            self.formatter.format_success("🔒 Safeguards ENABLED")
            self.formatter.format_system_message("Dangerous operations blocked.")
        else:
            self.formatter.format_error(f"Unknown dangerous option: {args}")
            self.formatter.format_system_message("Usage: /dangerous [on|off]")
        
        return True
    
    def _cmd_preview(self, args: str) -> bool:
        """Toggle preview mode"""
        self.agent.config.preview_mode = not self.agent.config.preview_mode
        
        status = "enabled" if self.agent.config.preview_mode else "disabled"
        self.formatter.format_success(f"Preview mode {status}")
        return True
    
    def _cmd_status(self, args: str) -> bool:
        """Show SQLBot status"""
        config = self.agent.config
        
        status_text = f"""
[bold]SQLBot Status:[/bold]

[bold]Configuration:[/bold]
• Profile: {config.profile}
• Dangerous mode: {'Yes' if config.dangerous else 'No'}
• Preview mode: {'Yes' if config.preview_mode else 'No'}
• Max rows: {config.max_rows}
• Query timeout: {config.query_timeout}s

[bold]Connections:[/bold]
• Database: {'Connected' if self.agent.test_connection() else 'Not connected'}
• LLM: {'Available' if self.agent.is_llm_available() else 'Not available'}

[bold]LLM Configuration:[/bold]
• Model: {config.llm.model}
• Max tokens: {config.llm.max_tokens}
• API key: {'Configured' if config.llm.api_key else 'Not configured'}
"""
        
        self.formatter.console.print(status_text)
        return True
    
    def _cmd_exit(self, args: str) -> bool:
        """Exit SQLBot"""
        self.formatter.format_system_message("Goodbye! 👋")
        return False
    
    def _cmd_no_repl(self, args: str) -> bool:
        """Exit interactive mode"""
        self.formatter.format_system_message("Exiting interactive mode...")
        return False

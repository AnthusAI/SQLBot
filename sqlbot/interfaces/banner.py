"""
Unified banner and welcome message system for SQLBot interfaces

This module provides consistent banner and help information across both text mode and Textual interface.
"""

import os
from typing import Optional, Dict, Any


def get_llm_config() -> Dict[str, Any]:
    """Get current LLM configuration parameters."""
    return {
        'model': os.getenv('SQLBOT_LLM_MODEL', 'gpt-5'),
        'max_tokens': int(os.getenv('SQLBOT_LLM_MAX_TOKENS', '50000')),
        'verbosity': os.getenv('SQLBOT_LLM_VERBOSITY', 'low'),
        'effort': os.getenv('SQLBOT_LLM_EFFORT', 'minimal'),
        'timeout': int(os.getenv('SQLBOT_LLM_TIMEOUT', '120'))
    }


def get_config_banner(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False, dbt_config_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Get configuration-only banner for --no-repl mode.
    Shows profile and LLM info without REPL help.

    Args:
        profile: Current dbt profile name
        llm_model: LLM model name (e.g., 'gpt-5')
        llm_available: Whether LLM integration is available
        dbt_config_info: Dictionary with dbt configuration details from DbtService

    Returns:
        Formatted configuration banner text
    """
    # Configuration section - separate lines for profile and LLM
    config_lines = []
    if profile:
        config_lines.append(f"Profile: {profile}")

    # Add dbt profiles directory information
    if dbt_config_info:
        if dbt_config_info.get('is_using_local_dbt', False):
            config_lines.append(f"Profiles: Local .dbt/profiles.yml (detected)")
        else:
            config_lines.append(f"Profiles: Global ~/.dbt/profiles.yml")

    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"LLM: {llm_model} (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("LLM: Not available")
    
    # Simple configuration banner for --no-repl mode
    title = "SQLBot CLI\nSQLBot: Database Query Interface"
    config_text = "\n".join(config_lines) if config_lines else ""
    
    content = f"{title}\n"
    if config_text:
        content += f"{config_text}\n\n"
    content += "Natural Language Queries (Default):\n• Just type your question in plain English\n• Example: How many customers are there?\n• Example: Show me sales data, then export to Excel\n\nSQL Queries:\n• End with semicolon for direct execution\n• SQL: SELECT COUNT(*) FROM customers;\n• SQL: SELECT * FROM customer LIMIT 10;\n\nCommands:\n• /help - Show all available commands\n• /preview - Preview SQL compilation before execution\n• /dangerous - Toggle dangerous mode (disables safeguards)\n• exit, quit, or q - Exit SQLBot"
    
    return content


def get_banner_content(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False, interface_type: str = "text", dbt_config_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Get unified banner content for both text and Textual interfaces.

    Args:
        profile: Current dbt profile name
        llm_model: LLM model name (e.g., 'gpt-5')
        llm_available: Whether LLM integration is available
        interface_type: 'text' for CLI mode, 'textual' for TUI mode
        dbt_config_info: Dictionary with dbt configuration details from DbtService

    Returns:
        Formatted banner text with modern Markdown formatting
    """

    # Configuration section with proper formatting
    config_lines = []
    if profile:
        config_lines.append(f"**Profile:** `{profile}`")

    # Add dbt profiles directory information
    if dbt_config_info:
        if dbt_config_info.get('is_using_local_dbt', False):
            config_lines.append(f"**Profiles:** Local `.dbt/profiles.yml` (detected)")
        else:
            config_lines.append(f"**Profiles:** Global `~/.dbt/profiles.yml`")

    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"**LLM:** `{llm_model}` (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("**LLM:** Not available")

    config_text = "\n".join(config_lines) if config_lines else ""
    
    # Interface-specific content
    if interface_type == "textual":
        title = "# Welcome to SQLBot!"
        interface_help = (
            "### Interface Tips\n"
            "- Press `Ctrl+\\` to open command palette (switch views)\n"
            "- Right panel shows query results by default\n"
            "- Press `Ctrl+C`, `Ctrl+Q`, or `Escape` to exit"
        )
    else:  # text mode
        title = "# SQLBot CLI\n## Database Query Interface"
        interface_help = (
            "### Tips\n"
            "- Use `↑`/`↓` arrows to navigate command history\n"
            "- Press `Ctrl+C` to interrupt running queries"
        )
    
    # Core help content with modern Markdown formatting
    core_help = (
        "## Natural Language Queries (Default)\n"
        "- Just type your question in plain English\n"
        "- **Example:** How many customers are there?\n"
        "- **Example:** Show me sales data, then export to CSV\n\n"
        
        "## SQL/dbt Queries\n"
        "- End with semicolon for direct execution\n"
        "- **SQL:** `SELECT COUNT(*) FROM customers;`\n"
        "- **SQL:** `SELECT * FROM customer LIMIT 10;`\n\n"
        
        "## Commands\n"
        "- `/help` - Show all available commands\n"
        "- `/preview` - Preview SQL compilation before execution\n"
        "- `/dangerous` - Toggle dangerous operation mode\n"
        "- `exit`, `quit`, or `q` - Exit SQLBot"
    )
    
    # Combine all sections with proper Markdown structure
    if interface_type == "textual":
        # For Textual interface
        content = f"{title}\n\n"
        if config_text:
            content += f"### Configuration\n{config_text}\n\n"
        content += f"{core_help}\n\n{interface_help}"
        return content
    else:
        # For text mode CLI
        content = f"{title}\n\n"
        if config_text:
            content += f"### Configuration\n{config_text}\n\n"
        content += f"{core_help}\n\n{interface_help}"
        return content


def get_interactive_banner_content(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False, dbt_config_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Get full interactive banner content for text mode REPL.

    Args:
        profile: Current dbt profile name
        llm_model: LLM model name
        llm_available: Whether LLM integration is available
        dbt_config_info: Dictionary with dbt configuration details from DbtService

    Returns:
        Full interactive banner with modern Markdown formatting
    """

    # Configuration info with proper formatting
    config_lines = []
    if profile:
        config_lines.append(f"**Profile:** `{profile}`")

    # Add dbt profiles directory information
    if dbt_config_info:
        if dbt_config_info.get('is_using_local_dbt', False):
            config_lines.append(f"**Profiles:** Local `.dbt/profiles.yml` (detected)")
        else:
            config_lines.append(f"**Profiles:** Global `~/.dbt/profiles.yml`")

    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"**LLM:** `{llm_model}` (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("**LLM:** Not available")

    config_text = "\n".join(config_lines) if config_lines else ""
    
    # Full interactive content with modern Markdown
    content = (
        "# SQLBot\n"
        "*An agent with a dbt query tool to help you with your SQL.*\n\n"
        "**Ready for questions.**\n\n"
    )
    
    if config_text:
        content += f"### Configuration\n{config_text}\n\n"
    
    content += (
        "## Default: Natural Language Queries\n"
        "- Just type your question in plain English\n"
        "- **Example:** How many calls were made today?\n"
        "- **Example:** Show me top customers, then export to Excel\n\n"
        
        "## SQL/dbt Queries: End with semicolon\n"
        "- **SQL:** `SELECT COUNT(*) FROM sys.tables;`\n"
        "- **SQL:** `SELECT * FROM film LIMIT 10;`\n\n"
        
        "## Commands\n"
        "- `/help` - Show all commands\n"
        "- `/preview` - Preview SQL compilation before execution\n"
        "- `/dangerous` - Toggle dangerous operation mode\n"
        "- `exit` - Quit\n\n"
        
        "### Tips\n"
        "- Use `↑`/`↓` arrows to navigate command history\n"
        "- Press `Ctrl+C` to interrupt running queries"
    )
    
    return content

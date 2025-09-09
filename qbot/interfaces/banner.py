"""
Unified banner and welcome message system for QBot interfaces

This module provides consistent banner and help information across both text mode and Textual interface.
"""

import os
from typing import Optional, Dict, Any


def get_llm_config() -> Dict[str, Any]:
    """Get current LLM configuration parameters."""
    return {
        'model': os.getenv('QBOT_LLM_MODEL', 'gpt-5'),
        'max_tokens': int(os.getenv('QBOT_LLM_MAX_TOKENS', '10000')),
        'verbosity': os.getenv('QBOT_LLM_VERBOSITY', 'low'),
        'effort': os.getenv('QBOT_LLM_EFFORT', 'minimal'),
        'timeout': int(os.getenv('QBOT_LLM_TIMEOUT', '120'))
    }


def get_config_banner(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False) -> str:
    """
    Get configuration-only banner for --no-repl mode.
    Shows profile and LLM info without REPL help.
    
    Args:
        profile: Current dbt profile name
        llm_model: LLM model name (e.g., 'gpt-5')
        llm_available: Whether LLM integration is available
        
    Returns:
        Formatted configuration banner text
    """
    # Configuration section - separate lines for profile and LLM
    config_lines = []
    if profile:
        config_lines.append(f"Profile: {profile}")
    
    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"LLM: {llm_model} (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("LLM: Not available")
    
    # Simple configuration banner for --no-repl mode
    title = "QBot CLI\nQBot: Database Query Interface"
    config_text = "\n".join(config_lines) if config_lines else ""
    
    content = f"{title}\n"
    if config_text:
        content += f"{config_text}\n\n"
    content += "Natural Language Queries (Default):\n• Just type your question in plain English\n• Example: How many customers are there?\n\nSQL/dbt Queries:\n• End with semicolon for direct execution\n• SQL: SELECT COUNT(*) FROM customers;\n• dbt: SELECT * FROM {{ source('sakila', 'customer') }} LIMIT 10;\n\nCommands:\n• /help - Show all available commands\n• /tables - List database tables\n• /preview - Preview SQL compilation before execution\n• /dangerous - Toggle dangerous mode (disables safeguards)\n• exit, quit, or q - Exit QBot"
    
    return content


def get_banner_content(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False, interface_type: str = "text") -> str:
    """
    Get unified banner content for both text and Textual interfaces.
    
    Args:
        profile: Current dbt profile name
        llm_model: LLM model name (e.g., 'gpt-5')
        llm_available: Whether LLM integration is available
        interface_type: 'text' for CLI mode, 'textual' for TUI mode
        
    Returns:
        Formatted banner text with configuration and help information
    """
    
    # Configuration section - separate lines for profile and LLM
    config_lines = []
    if profile:
        config_lines.append(f"Profile: {profile}")
    
    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"LLM: {llm_model} (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("LLM: Not available")
    
    config_text = "\n".join(config_lines) if config_lines else ""
    
    # Interface-specific content
    if interface_type == "textual":
        title = "QBot - Database Query Assistant"
        interface_help = (
            "• Press Ctrl+\\ to open command palette (switch views)\n"
            "• Right panel shows query results by default\n"
            "• Press Ctrl+C, Ctrl+Q, or Escape to exit"
        )
    else:  # text mode
        title = "QBot CLI\nQBot: Database Query Interface"
        interface_help = (
            "• Use ↑/↓ arrows to navigate command history\n"
            "• Press Ctrl+C to interrupt running queries"
        )
    
    # Core help content (same for both interfaces)
    core_help = (
        "Natural Language Queries (Default):\n"
        "• Just type your question in plain English\n"
        "• Example: How many customers are there?\n\n"
        
        "SQL/dbt Queries:\n"
        "• End with semicolon for direct execution\n"
        "• SQL: SELECT COUNT(*) FROM customers;\n"
        "• dbt: SELECT * FROM {{ source('sakila', 'customer') }} LIMIT 10;\n\n"
        
        "Commands:\n"
        "• /help - Show all available commands\n"
        "• /tables - List database tables\n"
        "• /preview - Preview SQL compilation before execution\n"
        "• /readonly - Toggle read-only safeguard mode\n"
        "• exit, quit, or q - Exit QBot"
    )
    
    # Combine all sections - SAME content for both interfaces
    if interface_type == "textual":
        # For Textual interface, return comprehensive content
        content = f"Welcome to QBot!\n\n"
        if config_text:
            content += f"Configuration: {config_text}\n\n"
        content += f"{core_help}\n\nInterface Tips:\n{interface_help}"
        return content
    else:
        # For text mode CLI, return comprehensive content with title
        content = f"{title}\n"
        if config_text:
            content += f"{config_text}\n\n"
        content += f"{core_help}\n\nTips:\n{interface_help}"
        return content


def get_interactive_banner_content(profile: Optional[str] = None, llm_model: Optional[str] = None, llm_available: bool = False) -> str:
    """
    Get full interactive banner content for text mode REPL.
    
    Args:
        profile: Current dbt profile name
        llm_model: LLM model name
        llm_available: Whether LLM integration is available
        
    Returns:
        Full interactive banner with all help information
    """
    
    # Configuration info - separate lines for profile and LLM
    config_lines = []
    if profile:
        config_lines.append(f"Profile: {profile}")
    
    if llm_available and llm_model:
        llm_config = get_llm_config()
        llm_info = f"LLM: {llm_model} (tokens={llm_config['max_tokens']}, verbosity={llm_config['verbosity']}, effort={llm_config['effort']})"
        config_lines.append(llm_info)
    else:
        config_lines.append("LLM: Not available")
    
    config_text = "\n".join(config_lines) if config_lines else ""
    
    # Full interactive content
    content = (
        "QBot: An agent with a dbt query tool to help you with your SQL.\n\n"
        "Ready for questions.\n\n"
    )
    
    if config_text:
        content += f"Configuration: {config_text}\n\n"
    
    content += (
        "Default: Natural Language Queries\n"
        "• Just type your question in plain English\n"
        "• Example: How many calls were made today?\n\n"
        
        "SQL/dbt Queries: End with semicolon\n"
        "• SQL: SELECT COUNT(*) FROM sys.tables;\n"
        "• dbt: SELECT * FROM {{ source('your_source', 'your_table') }} LIMIT 10;\n\n"
        
        "Commands:\n"
        "• /help - Show all commands\n"
        "• /tables - List database tables\n"
        "• /preview - Preview SQL compilation before execution\n"
        "• /readonly - Toggle read-only safeguard mode\n"
        "• exit - Quit\n\n"
        
        "Tips:\n"
        "• Use ↑/↓ arrows to navigate command history\n"
        "• Press Ctrl+C to interrupt running queries"
    )
    
    return content

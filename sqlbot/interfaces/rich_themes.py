"""
Rich CLI Themes for SQLBot

This module defines Rich themes for CLI output that coordinate with the main theme system.
The colors are imported from theme_system.py to maintain consistency.
"""

from rich.theme import Theme as RichTheme
from sqlbot.interfaces.theme_system import (
    DODGER_BLUE_DARK, DODGER_BLUE_LIGHT, MAGENTA1, DEEP_PINK_LIGHT
)


# Rich Themes for CLI mode - using colors from theme_system.py for consistency
qbot_dark_rich_theme = RichTheme({
    # User messages
    "user_message": f"{DODGER_BLUE_DARK} bold",
    "user_symbol": DODGER_BLUE_DARK,
    
    # AI responses
    "ai_response": MAGENTA1,
    "ai_symbol": MAGENTA1,
    
    # System messages
    "system_message": "#06b6d4",
    "system_symbol": "#0891b2",
    
    # Status messages
    "error_message": "#f87171 bold",
    "error_symbol": "#ef4444",
    "warning_message": "#fbbf24",
    "warning_symbol": "#f59e0b",
    "success_message": "#10b981 bold",
    "success_symbol": "#059669",
    "info_message": "#06b6d4",
    "info_symbol": "#0891b2",
    
    # Tool colors
    "tool_call": "#06b6d4",
    "tool_call_symbol": "#0891b2",
    "tool_result": "#10b981",
    "tool_result_symbol": "#059669",
    
    # Content formatting
    "thinking": "#6b7280 dim",               # Gray dim for agent thinking
    "user_prompt": f"{DODGER_BLUE_DARK} dim",
    "code_inline": "#06b6d4",
    "code_block": "#10b981",
    "heading_1": "#fbbf24 bold",
    "heading_2": f"{MAGENTA1} bold",
    "heading_3": "#06b6d4 bold"
})

qbot_light_rich_theme = RichTheme({
    # User messages  
    "user_message": f"{DODGER_BLUE_LIGHT} bold",
    "user_symbol": DODGER_BLUE_LIGHT,
    
    # AI responses
    "ai_response": DEEP_PINK_LIGHT,
    "ai_symbol": DEEP_PINK_LIGHT,
    
    # System messages
    "system_message": "#0891b2",
    "system_symbol": "#0e7490",
    
    # Status messages
    "error_message": "#dc2626 bold",
    "error_symbol": "#b91c1c",
    "warning_message": "#d97706",
    "warning_symbol": "#b45309",
    "success_message": "#059669 bold",
    "success_symbol": "#047857",
    "info_message": "#0891b2",
    "info_symbol": "#0e7490",
    
    # Tool colors
    "tool_call": "#0891b2",
    "tool_call_symbol": "#0e7490",
    "tool_result": "#059669",
    "tool_result_symbol": "#047857",
    
    # Content formatting
    "thinking": "#6b7280 dim",
    "user_prompt": f"{DODGER_BLUE_LIGHT} dim",
    "code_inline": "#0891b2",
    "code_block": "#059669",
    "heading_1": "#d97706 bold",
    "heading_2": f"{DEEP_PINK_LIGHT} bold", 
    "heading_3": "#0891b2 bold"
})

qbot_monokai_rich_theme = RichTheme({
    # User messages
    "user_message": "#66d9ef bold",
    "user_symbol": "#51c7e0",
    
    # AI responses
    "ai_response": "#f92672",
    "ai_symbol": "#e91e63",
    
    # System messages
    "system_message": "#a6e22e",
    "system_symbol": "#8bc34a",
    
    # Status messages
    "error_message": "#f92672 bold",
    "error_symbol": "#e91e63",
    "warning_message": "#e6db74",
    "warning_symbol": "#cddc39",
    "success_message": "#a6e22e bold",
    "success_symbol": "#8bc34a",
    "info_message": "#66d9ef",
    "info_symbol": "#51c7e0",
    
    # Tool colors
    "tool_call": "#66d9ef",
    "tool_call_symbol": "#51c7e0",
    "tool_result": "#a6e22e",
    "tool_result_symbol": "#8bc34a",
    
    # Content formatting
    "thinking": "#75715e dim",
    "user_prompt": "#66d9ef dim",
    "code_inline": "#e6db74",
    "code_block": "#a6e22e", 
    "heading_1": "#f92672 bold",
    "heading_2": "#66d9ef bold",
    "heading_3": "#a6e22e bold"
})

# Theme registry for easy access
QBOT_RICH_THEMES = {
    "dark": qbot_dark_rich_theme,
    "light": qbot_light_rich_theme,
    "monokai": qbot_monokai_rich_theme
}

"""
SQLBot Theme System - New Architecture

This module provides a unified theming system that leverages Textual's built-in themes
and adds SQLBot-specific message colors on top. Supports both built-in themes and 
user-defined themes in ~/.sqlbot/themes/.
"""

from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
import yaml
from pathlib import Path

# Optional textual imports - only needed for Textual app, not Rich CLI
try:
    from textual.design import ColorSystem
    from textual.app import App
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    # Dummy classes for when textual is not available
    class ColorSystem:
        pass
    class App:
        pass


# Textual's built-in themes (as of Textual 6.1.0) + SQLBot custom themes
BUILTIN_THEMES = [
    "catppuccin-latte",
    "catppuccin-mocha",
    "dracula",
    "flexoki",
    "gruvbox",
    "monokai",
    "nord",
    "solarized-dark",    # SQLBot custom theme using official Solarized palette
    "solarized-light",
    "textual-ansi",
    "textual-dark",
    "textual-light",
    "tokyo-night",
    "sqlbot-warm-light"         # SQLBot custom warm light theme
]

# Unified theme names mapping to Textual built-in themes
UNIFIED_THEME_MAP = {
    "dark": "tokyo-night",        # Default theme (warm dark with magentas/oranges)
    "light": "textual-light",     # Clean light theme
    "cool-dark": "catppuccin-mocha", # Cool dark (purple/blue tones)
    "cool-light": "catppuccin-latte", # Cool light (purple/blue tones)
    "warm-dark": "textual-dark",      # Warm dark (textual-dark with solarized overrides)
    "warm-light": "solarized-light",  # Warm light (solarized with overrides)
}

# Theme aliases - map friendly names to built-in themes
THEME_ALIASES = {
    "qbot": "tokyo-night",  # Default SQLBot theme
    # Legacy aliases for backward compatibility
    "tokyo": "tokyo-night",
    "catppuccin": "catppuccin-mocha",
    # Add unified theme aliases
    **UNIFIED_THEME_MAP,
}

class ThemeMode(Enum):
    """Available theme modes - includes unified themes and built-in themes"""
    # Unified theme names (primary interface)
    DARK = "dark"              # Default theme (tokyo-night)
    LIGHT = "light"            # Light theme (textual-light)
    COOL_DARK = "cool-dark"    # Cool dark (catppuccin-mocha)
    COOL_LIGHT = "cool-light"  # Cool light (catppuccin-latte)
    WARM_DARK = "warm-dark"    # Warm dark (solarized-dark)
    WARM_LIGHT = "warm-light"  # Warm light (solarized-light)

    # Legacy/specific theme names (for backward compatibility)
    QBOT = "qbot"  # Alias for tokyo-night
    CATPPUCCIN_LATTE = "catppuccin-latte"
    CATPPUCCIN_MOCHA = "catppuccin-mocha"
    DRACULA = "dracula"
    FLEXOKI = "flexoki"
    GRUVBOX = "gruvbox"
    MONOKAI = "monokai"
    NORD = "nord"
    SOLARIZED_DARK = "solarized-dark"
    SOLARIZED_LIGHT = "solarized-light"
    TEXTUAL_ANSI = "textual-ansi"
    TEXTUAL_DARK = "textual-dark"
    TEXTUAL_LIGHT = "textual-light"
    TOKYO_NIGHT = "tokyo-night"


# Standard SQLBot colors for consistency across themes (web-safe pure blue versions)
DODGER_BLUE_DARK = "#66ccff"   # Web-safe lighter blue - DEPRECATED, keeping for compatibility
DODGER_BLUE_LIGHT = "#6699ff"  # Web-safe lighter blue - for light themes
MAGENTA1 = "#ffaaff"           # Medium pink (more saturated) - for AI responses  
DEEP_PINK_LIGHT = "#ffccff"    # Web-safe lighter pink - for light themes

# New pure blue color scheme
PURE_BLUE_INPUT_BORDER = "#0000cc"  # Pure blue, lighter than panel borders (#000087)
PURE_BLUE_TEXT = "#ccccff"          # Very light blue, one notch down from white

# SQLBot-specific message colors for each built-in theme
# User messages use consistent dodger blue across all themes
QBOT_MESSAGE_COLORS = {
    "tokyo-night": {
        "user_message": PURE_BLUE_TEXT,      # Pure blue text for user messages
        "input_border": PURE_BLUE_INPUT_BORDER, # Pure blue border for input box
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": "cyan",            # Cyan for system messages
        "info_message": "blue",              # Blue for info messages
        "success_message": "green",          # Green for success messages
        "warning_message": "yellow",         # Yellow for warning messages
        "error_message": "red",              # Red for error messages
        "database_label": "violet",          # Violet for database labels
        "primary": "blue",                   # Primary color
        "panel_border": "#000087",           # Web-safe blue for panel borders
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "catppuccin-mocha": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": "cyan",            # Cyan for system messages
        "info_message": "blue",              # Blue for info messages
        "success_message": "green",          # Green for success messages
        "warning_message": "yellow",         # Yellow for warning messages
        "error_message": "red",              # Red for error messages
        "database_label": "violet",          # Violet for database labels
        "primary": "blue",                   # Primary color
        "panel_border": "#89b4fa",           # Catppuccin blue for panel borders
        "input_border": "#b4befe",           # Lighter catppuccin blue for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "catppuccin-latte": {
        "user_message": DODGER_BLUE_LIGHT,   # Consistent dodger blue for light themes
        "ai_response": DEEP_PINK_LIGHT,      # Consistent deep pink for light themes
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#1e66f5",           # Catppuccin blue for panel borders (light theme)
        "input_border": "#4c7ff9",           # Lighter catppuccin blue for input border (light theme)
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (light theme)
        "block_cursor_foreground": "#5A4A6C",  # Darker text for light theme
        "block_cursor_background": "#E0D0F0",  # Light purple background
        "block_cursor_blurred_foreground": "#6A5A7C",  # Slightly darker when not focused
        "block_cursor_blurred_background": "#F0E0FF",  # Even lighter when not focused
    },
    "dracula": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#6272a4",           # Dracula comment color for panel borders
        "input_border": "#8be9fd",           # Dracula cyan for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "gruvbox": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#83a598",           # Gruvbox blue for panel borders
        "input_border": "#b8bb26",           # Gruvbox bright green for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "nord": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        "panel_border": "#5e81ac",           # Nord blue for panel borders
        "input_border": "#81a1c1",           # Lighter nord blue for input border
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "monokai": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#66d9ef",           # Monokai cyan for panel borders
        "input_border": "#a6e22e",           # Monokai green for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "solarized-dark": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#268bd2",           # Solarized blue for panel borders
        "input_border": "#2aa198",           # Solarized cyan for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (dark theme)
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "solarized-light": {
        "user_message": DODGER_BLUE_LIGHT,   # Consistent dodger blue for light themes
        "ai_response": DEEP_PINK_LIGHT,      # Consistent deep pink for light themes
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#268bd2",           # Solarized blue for panel borders
        "input_border": "#2aa198",           # Solarized cyan for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (light theme)
        "block_cursor_foreground": "#5A4A6C",  # Darker text for light theme
        "block_cursor_background": "#E0D0F0",  # Light purple background
        "block_cursor_blurred_foreground": "#6A5A7C",  # Slightly darker when not focused
        "block_cursor_blurred_background": "#F0E0FF",  # Even lighter when not focused
    },
    "sqlbot-warm-light": {
        "user_message": DODGER_BLUE_LIGHT,   # Consistent dodger blue for light themes
        "ai_response": DEEP_PINK_LIGHT,      # Consistent deep pink for light themes
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#b58900",           # Solarized yellow for panel borders
        "input_border": "#cb4b16",           # Solarized orange for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (light theme)
        "block_cursor_foreground": "#5A4A6C",  # Darker text for light theme
        "block_cursor_background": "#E0D0F0",  # Light purple background
        "block_cursor_blurred_foreground": "#6A5A7C",  # Slightly darker when not focused
        "block_cursor_blurred_background": "#F0E0FF",  # Even lighter when not focused
    },
    # Remaining built-in themes
    "flexoki": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#4385be",           # Flexoki blue for panel borders
        "input_border": "#1eb2a6",           # Flexoki teal for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "textual-dark": {
        "user_message": DODGER_BLUE_DARK,    # Consistent dodger blue for dark themes
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#0178d4",           # Textual blue for panel borders
        "input_border": "#004578",           # Darker textual blue for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    },
    "textual-light": {
        "user_message": DODGER_BLUE_LIGHT,   # Consistent dodger blue for light themes
        "ai_response": DEEP_PINK_LIGHT,      # Consistent deep pink for light themes
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#0178d4",           # Textual blue for panel borders (light theme)
        "input_border": "#48a9e6",           # Lighter textual blue for input border (light theme)
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (light theme)
        "block_cursor_foreground": "#5A4A6C",  # Darker text for light theme
        "block_cursor_background": "#E0D0F0",  # Light purple background
        "block_cursor_blurred_foreground": "#6A5A7C",  # Slightly darker when not focused
        "block_cursor_blurred_background": "#F0E0FF",  # Even lighter when not focused
    },
    "textual-ansi": {
        "user_message": DODGER_BLUE_LIGHT,   # Consistent dodger blue for light themes
        "ai_response": DEEP_PINK_LIGHT,      # Consistent deep pink for light themes
        "system_message": None,              # No special styling - use default text color
        "panel_border": "#0000ff",           # Basic blue for ANSI panel borders
        "input_border": "#0080ff",           # Lighter blue for ANSI input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "error": None,                       # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash (light theme)
        "block_cursor_foreground": "#5A4A6C",  # Darker text for light theme
        "block_cursor_background": "#E0D0F0",  # Light purple background
        "block_cursor_blurred_foreground": "#6A5A7C",  # Slightly darker when not focused
        "block_cursor_blurred_background": "#F0E0FF",  # Even lighter when not focused
    },
    # Fallback colors for other themes
    "default": {
        "user_message": PURE_BLUE_TEXT,      # Pure blue text for user messages
        "ai_response": MAGENTA1,             # magenta1 for AI responses
        "system_message": "cyan",            # Cyan for system messages
        "info_message": "blue",              # Blue for info messages
        "success_message": "green",          # Green for success messages
        "warning_message": "yellow",         # Yellow for warning messages
        "error_message": "red",              # Red for error messages
        "database_label": "violet",          # Violet for database labels
        "primary": "blue",                   # Primary color
        "panel_border": "#0000cc",           # Default blue for panel borders
        "input_border": "#3333ff",           # Lighter default blue for input border
        "tool_call": None,                   # Use default system color for tool calls
        "tool_result": None,                 # Use default system color for tool results
        "success": "green",                  # Green for success messages (safeguard passes, etc.)
        "error": "red",                      # Red for error messages (safeguard failures, etc.)
        "thinking": None,                    # No special styling - use default text color
        "code_inline": None,                 # No special styling - use default text color
        # Block cursor colors for ListView selection flash
        "block_cursor_foreground": "#E0D0F0",  # Muted light purple text during selection
        "block_cursor_background": "#4A3A5C",  # Muted purple-gray background during selection
        "block_cursor_blurred_foreground": "#D0C0E0",  # More muted when not focused
        "block_cursor_blurred_background": "#3A2A4C",  # Darker when not focused
    }
}


class SQLBotTheme(BaseModel):
    """SQLBot theme definition - supports user themes only (built-in themes use Textual directly)"""
    name: str = Field(exclude=True)
    
    # For user themes: Textual ColorSystem fields (primary required, others optional)
    primary: str
    secondary: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    dark: bool = True
    
    # SQLBot-specific message colors (all optional - will use intelligent defaults)
    user_message: str | None = None
    ai_response: str | None = None
    system_message: str | None = None
    info_message: str | None = None
    code_inline: str | None = None
    code_block: str | None = None
    tool_call: str | None = None
    tool_result: str | None = None
    thinking: str | None = None

    def model_post_init(self, __context) -> None:
        """Fill in missing colors with intelligent defaults derived from base colors"""
        # User messages default to primary color
        if self.user_message is None:
            self.user_message = self.primary
        
        # AI responses default to secondary color
        if self.ai_response is None:
            self.ai_response = self.secondary or self.primary
            
        # System messages default to accent or success color
        if self.system_message is None:
            self.system_message = self.accent or self.success or "#10b981"
            
        # Info messages default to accent color
        if self.info_message is None:
            self.info_message = self.accent or self.primary
        
        # Content formatting defaults
        if self.code_inline is None:
            self.code_inline = self.warning or "#fbbf24"
        if self.code_block is None:
            self.code_block = self.success or "#10b981"
        
        # Tool colors
        if self.tool_call is None:
            self.tool_call = self.warning or "#f59e0b"
        if self.tool_result is None:
            self.tool_result = self.success or "#10b981"
        
        # Status colors
        if self.thinking is None:
            self.thinking = "#6b7280" if self.dark else "#9ca3af"

    def to_color_system(self) -> ColorSystem:
        """Convert this theme to a Textual ColorSystem"""
        return ColorSystem(
            **self.model_dump(
                exclude={
                    "user_message", "ai_response", "system_message", "info_message",
                    "code_inline", "code_block", "tool_call", "tool_result", "thinking"
                }
            )
        )


def load_user_themes() -> Dict[str, SQLBotTheme]:
    """Load user themes from ~/.sqlbot/themes/"""
    from sqlbot.locations import theme_directory
    
    user_themes = {}
    theme_dir = theme_directory()
    
    if not theme_dir.exists():
        return user_themes
    
    for theme_file in theme_dir.glob("*.yaml"):
        try:
            with open(theme_file, 'r') as f:
                theme_data = yaml.safe_load(f)
            
            if not theme_data or 'name' not in theme_data:
                continue
                
            theme_name = theme_data.pop('name')  # Remove name from theme_data to avoid duplicate
            theme = SQLBotTheme(name=theme_name, **theme_data)
            user_themes[theme_name] = theme
            
        except Exception as e:
            print(f"Warning: Failed to load theme from {theme_file}: {e}")
    
    return user_themes


def create_warm_light_theme() -> ColorSystem:
    """
    Create Warm Light theme using solarized light colors but with warm primary.
    """
    if not TEXTUAL_AVAILABLE:
        return None

    return ColorSystem(
        primary="#b58900",      # Solarized yellow (warm primary)
        secondary="#cb4b16",    # Solarized orange
        background="#fdf6e3",   # Solarized base3 (lightest)
        surface="#eee8d5",      # Solarized base2 (background highlights)
        panel="#eee8d5",        # Same as surface
        warning="#b58900",      # Solarized yellow
        error="#dc322f",        # Solarized red
        success="#859900",      # Solarized green
        accent="#d33682",       # Solarized magenta
        dark=False
    )


def create_solarized_dark_theme() -> ColorSystem:
    """
    Create Solarized Dark theme using official Solarized color palette.

    Official Solarized colors:
    - base03: #002b36 (darkest background)
    - base02: #073642 (dark background highlights)
    - base01: #586e75 (optional emphasized content)
    - base00: #657b83 (body text / default code / primary content)
    - base0: #839496 (comments / secondary content)
    - base1: #93a1a1 (comments / secondary content)
    - base2: #eee8d5 (background highlights)
    - base3: #fdf6e3 (lightest background)

    Accent colors:
    - yellow: #b58900, orange: #cb4b16, red: #dc322f, magenta: #d33682
    - violet: #6c71c4, blue: #268bd2, cyan: #2aa198, green: #859900
    """
    if not TEXTUAL_AVAILABLE:
        return None

    return ColorSystem(
        primary="#b58900",      # Solarized yellow (warm primary)
        secondary="#d33682",    # Solarized magenta
        background="#002b36",   # Solarized base03 (darkest)
        surface="#073642",      # Solarized base02 (background highlights)
        panel="#073642",        # Same as surface
        warning="#b58900",      # Solarized yellow
        error="#dc322f",        # Solarized red
        success="#859900",      # Solarized green
        accent="#d33682",       # Solarized magenta
        dark=True
    )


class SQLBotThemeManager:
    """Manages themes using Textual's built-in themes + SQLBot message colors"""
    
    def __init__(self, theme_mode: ThemeMode = ThemeMode.DARK):
        # Create a temporary Textual app to access built-in themes (only if textual is available)
        if TEXTUAL_AVAILABLE:
            self._temp_app = App()
            # Register custom themes with Textual
            self._register_custom_themes()
        else:
            self._temp_app = None

        self.current_mode = theme_mode
        self.current_textual_theme_name = self._resolve_theme_name(theme_mode.value)

        # Load user themes
        self.user_themes = load_user_themes()

        # Check if requested theme is a user theme
        if theme_mode.value in self.user_themes:
            self.current_theme = self.user_themes[theme_mode.value]
            self.is_builtin_theme = False
        else:
            self.current_theme = None  # Will use built-in theme + message colors
            self.is_builtin_theme = True
    
    def _register_custom_themes(self) -> None:
        """Register custom themes with Textual"""
        if not TEXTUAL_AVAILABLE:
            return

        # No custom theme registration needed - using overrides instead
        pass

    def _resolve_theme_name(self, theme_name: str) -> str:
        """Resolve theme aliases to actual Textual theme names"""
        return THEME_ALIASES.get(theme_name, theme_name)
    
    def set_theme(self, theme_mode: ThemeMode) -> None:
        """Change the current theme"""
        self.current_mode = theme_mode
        theme_name = theme_mode.value
        
        # Check if it's a user theme first
        if theme_name in self.user_themes:
            self.current_theme = self.user_themes[theme_name]
            self.current_textual_theme_name = None
            self.is_builtin_theme = False
        else:
            # It's a built-in theme
            resolved_name = self._resolve_theme_name(theme_name)
            if resolved_name in BUILTIN_THEMES:
                self.current_textual_theme_name = resolved_name
                self.current_theme = None
                self.is_builtin_theme = True
            else:
                raise ValueError(f"Theme '{theme_name}' not found")
    
    def set_theme_by_name(self, theme_name: str) -> None:
        """Change theme by name"""
        # Try to find corresponding ThemeMode
        for mode in ThemeMode:
            if mode.value == theme_name:
                self.set_theme(mode)
                return
        
        # Check if it's a user theme
        if theme_name in self.user_themes:
            self.current_theme = self.user_themes[theme_name]
            self.current_textual_theme_name = None
            self.is_builtin_theme = False
            # Set mode to a generic one since it's not in the enum
            self.current_mode = ThemeMode.DARK
        else:
            raise ValueError(f"Theme '{theme_name}' not found")
    
    def get_available_themes(self) -> Dict[str, str]:
        """Get all available themes with their type - prioritize unified themes"""
        available = {}

        # Add unified themes first (primary interface)
        for unified_name in UNIFIED_THEME_MAP.keys():
            available[unified_name] = "unified"

        # Add all built-in themes (including those mapped by unified themes)
        for theme in BUILTIN_THEMES:
            available[theme] = "built-in"

        # Add legacy aliases that aren't unified themes or built-in themes
        for alias, target in THEME_ALIASES.items():
            if alias not in UNIFIED_THEME_MAP and alias not in BUILTIN_THEMES:
                # Mark important SQLBot aliases as built-in
                if alias in ["qbot"]:
                    available[alias] = "built-in"
                else:
                    available[alias] = "alias"

        # Add user themes
        for name in self.user_themes:
            available[name] = "user"

        return available
    
    def get_textual_theme_name(self) -> str:
        """Get the Textual theme name to use for App.theme"""
        if self.is_builtin_theme:
            return self.current_textual_theme_name
        else:
            # User themes don't have a Textual equivalent, use default
            return "textual-dark"
    
    def get_color(self, color_type: str) -> str:
        """Get a specific color for the current theme"""
        if self.is_builtin_theme:
            # Get from built-in theme's message colors
            theme_colors = QBOT_MESSAGE_COLORS.get(
                self.current_textual_theme_name, 
                QBOT_MESSAGE_COLORS["default"]
            )
            color = theme_colors.get(color_type)
            
            # If color is None, return None to indicate no special styling
            if color is None:
                return None
                
            return color
        else:
            # Get from user theme
            return getattr(self.current_theme, color_type, None)
    
    def get_css_variables(self) -> Dict[str, str]:
        """Get CSS variables for the current theme"""
        if self.is_builtin_theme:
            # For built-in themes, we only provide SQLBot-specific message colors
            # The base theme colors come from Textual's built-in theme
            theme_colors = QBOT_MESSAGE_COLORS.get(
                self.current_textual_theme_name,
                QBOT_MESSAGE_COLORS["default"]
            )
            # Filter out None values to avoid CSS parsing errors
            variables = {}
            for key, value in theme_colors.items():
                if value is not None:
                    # Special handling for block cursor variables - use Textual's expected names
                    if key.startswith('block_cursor'):
                        # Convert block_cursor_foreground -> block-cursor-foreground
                        textual_key = key.replace('_', '-')
                        variables[textual_key] = value
                    else:
                        # Regular SQLBot variables with qbot- prefix
                        variables[f"qbot-{key.replace('_', '-')}"] = value

            # Special overrides for warm themes to use solarized colors
            if self.current_textual_theme_name == "solarized-light":
                variables["primary"] = "#b58900"  # Solarized yellow instead of blue
                variables["secondary"] = "#cb4b16"  # Solarized orange
            elif self.current_textual_theme_name == "textual-dark" and self.current_mode.value == "warm-dark":
                # Override textual-dark with official solarized-dark colors
                variables["primary"] = "#b58900"      # Solarized yellow
                variables["secondary"] = "#cb4b16"    # Solarized orange
                variables["background"] = "#002b36"   # Solarized base03 (darkest)
                variables["surface"] = "#073642"      # Solarized base02 (background highlights)
                variables["accent"] = "#d33682"       # Solarized magenta
                variables["warning"] = "#b58900"      # Solarized yellow
                variables["error"] = "#dc322f"        # Solarized red
                variables["success"] = "#859900"      # Solarized green
                # Override borders to use warm colors
                variables["qbot-panel-border"] = "#b58900"  # Solarized yellow
                variables["qbot-input-border"] = "#cb4b16"  # Solarized orange

            return variables
        else:
            # For user themes, provide both base colors and message colors
            base_vars = self.current_theme.to_color_system().get_variables()
            message_vars = {
                f"qbot-{key.replace('_', '-')}": getattr(self.current_theme, key)
                for key in ["user_message", "ai_response", "system_message", "info_message",
                           "code_inline", "code_block", "tool_call", "tool_result", "thinking", "panel_border", "input_border"]
                if getattr(self.current_theme, key) is not None
            }
            return {**base_vars, **message_vars}
    
    def format_user_message(self, text: str, prefix: str = ">") -> str:
        """Format a user message with theme styling"""
        color = self.get_color("user_message")
        if color:
            return f"[{color}]{prefix} {text}[/{color}]"
        return f"{prefix} {text}"
    
    def format_system_message(self, text: str, prefix: str = "◦") -> str:
        """Format a system message with theme styling"""
        color = self.get_color("system_message")
        if color:
            return f"[{color}]{prefix} {text}[/{color}]"
        return f"{prefix} {text}"
    
    def format_error(self, text: str, prefix: str = "▪") -> str:
        """Format an error message with theme styling"""
        color = self.get_color("error") or "red"  # Fallback to red for errors
        return f"[{color}]{prefix} {text}[/{color}]"


# Global theme manager instance
_theme_manager: Optional[SQLBotThemeManager] = None

def get_theme_manager() -> SQLBotThemeManager:
    """Get the global theme manager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = SQLBotThemeManager()
    return _theme_manager

def set_theme_manager(manager: SQLBotThemeManager) -> None:
    """Set the global theme manager instance"""
    global _theme_manager
    _theme_manager = manager



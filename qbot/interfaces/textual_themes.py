"""
Unified Themes for QBot

This module defines coordinated themes for both Textual TUI and Rich CLI output.
The themes use matching color palettes to ensure consistent appearance across interfaces.
"""

from textual.theme import Theme
from rich.theme import Theme as RichTheme


# QBot Dark Theme (default)
qbot_dark_theme = Theme(
    name="qbot_dark",
    primary="#0078d4",          # Blue for primary elements
    secondary="#8b5cf6",        # Purple for secondary elements  
    accent="#06b6d4",           # Cyan for accents
    background="#0f0f23",       # Very dark blue background
    surface="#1e1e2e",          # Slightly lighter surface
    
    # Message-specific colors via variables
    variables={
        # User messages
        "user-message": "#4fc3f7",           # Light blue
        "user-message-symbol": "#29b6f6",    # Slightly darker blue
        
        # AI responses  
        "ai-response": "#e879f9",            # Bright magenta
        "ai-response-symbol": "#d946ef",     # Magenta
        
        # System messages
        "system-message": "#06b6d4",         # Cyan
        "system-symbol": "#0891b2",          # Darker cyan
        
        # Status colors
        "error-message": "#f87171",          # Red
        "error-symbol": "#ef4444",           # Darker red
        "warning-message": "#fbbf24",        # Yellow
        "warning-symbol": "#f59e0b",         # Darker yellow
        "success-message": "#10b981",        # Green
        "success-symbol": "#059669",         # Darker green
        "info-message": "#06b6d4",           # Cyan
        "info-symbol": "#0891b2",            # Darker cyan
        
        # Tool colors
        "tool-call": "#06b6d4",              # Cyan for tool calls
        "tool-result": "#10b981",            # Green for results
        
        # Content formatting
        "thinking": "#6b7280",               # Gray for thinking/agent processing
        "user-prompt": "#4fc3f7",            # Light blue for user input prompt
        "code-inline": "#06b6d4",            # Cyan for inline code
        "code-block": "#10b981",             # Green for code blocks
        "heading-1": "#fbbf24",              # Yellow for H1
        "heading-2": "#e879f9",              # Magenta for H2
        "heading-3": "#06b6d4",              # Cyan for H3
    },
    dark=True
)


# QBot Light Theme
qbot_light_theme = Theme(
    name="qbot_light",
    primary="#0066cc",          # Darker blue for light theme
    secondary="#7c3aed",        # Purple
    accent="#0891b2",           # Darker cyan
    background="#ffffff",       # White background
    surface="#f8fafc",          # Very light gray surface
    
    variables={
        # User messages
        "user-message": "#0066cc",           # Blue
        "user-message-symbol": "#0052a3",    # Darker blue
        
        # AI responses
        "ai-response": "#9333ea",            # Purple  
        "ai-response-symbol": "#7c3aed",     # Darker purple
        
        # System messages
        "system-message": "#0891b2",         # Teal
        "system-symbol": "#0e7490",          # Darker teal
        
        # Status colors
        "error-message": "#dc2626",          # Red
        "error-symbol": "#b91c1c",           # Darker red
        "warning-message": "#d97706",        # Orange
        "warning-symbol": "#b45309",         # Darker orange
        "success-message": "#059669",        # Green
        "success-symbol": "#047857",         # Darker green
        "info-message": "#0891b2",           # Teal
        "info-symbol": "#0e7490",            # Darker teal
        
        # Tool colors
        "tool-call": "#0891b2",              # Teal
        "tool-result": "#059669",            # Green
        
        # Content formatting
        "thinking": "#6b7280",               # Gray for thinking/agent processing
        "user-prompt": "#0066cc",            # Blue for user input prompt
        "code-inline": "#0891b2",            # Teal
        "code-block": "#059669",             # Green
        "heading-1": "#d97706",              # Orange
        "heading-2": "#9333ea",              # Purple
        "heading-3": "#0891b2",              # Teal
    },
    dark=False
)


# QBot Monokai Theme
qbot_monokai_theme = Theme(
    name="qbot_monokai",
    primary="#f92672",          # Bright pink/red
    secondary="#66d9ef",        # Bright cyan
    accent="#a6e22e",           # Bright green
    background="#272822",       # Dark brown/gray
    surface="#3e3d32",          # Lighter brown
    
    variables={
        # User messages
        "user-message": "#66d9ef",           # Bright cyan
        "user-message-symbol": "#51c7e0",    # Slightly darker cyan
        
        # AI responses
        "ai-response": "#f92672",            # Bright pink
        "ai-response-symbol": "#e91e63",     # Darker pink
        
        # System messages  
        "system-message": "#a6e22e",         # Bright green
        "system-symbol": "#8bc34a",          # Darker green
        
        # Status colors
        "error-message": "#f92672",          # Bright pink (red)
        "error-symbol": "#e91e63",           # Darker pink
        "warning-message": "#e6db74",        # Bright yellow
        "warning-symbol": "#cddc39",         # Darker yellow
        "success-message": "#a6e22e",        # Bright green
        "success-symbol": "#8bc34a",         # Darker green
        "info-message": "#66d9ef",           # Bright cyan
        "info-symbol": "#51c7e0",            # Darker cyan
        
        # Tool colors
        "tool-call": "#66d9ef",              # Bright cyan
        "tool-result": "#a6e22e",            # Bright green
        
        # Content formatting
        "thinking": "#75715e",               # Muted gray for thinking/agent processing
        "user-prompt": "#66d9ef",            # Bright cyan for user input prompt
        "code-inline": "#e6db74",            # Bright yellow
        "code-block": "#a6e22e",             # Bright green
        "heading-1": "#f92672",              # Bright pink
        "heading-2": "#66d9ef",              # Bright cyan
        "heading-3": "#a6e22e",              # Bright green
    },
    dark=True
)


# Rich Themes (for CLI mode) that coordinate with Textual themes
qbot_dark_rich_theme = RichTheme({
    # User messages
    "user_message": "#4fc3f7 bold",
    "user_symbol": "#29b6f6",
    
    # AI responses
    "ai_response": "#e879f9",
    "ai_symbol": "#d946ef",
    
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
    "user_prompt": "#4fc3f7 dim",            # Light blue dim for user prompt
    "code_inline": "#06b6d4",
    "code_block": "#10b981",
    "heading_1": "#fbbf24 bold",
    "heading_2": "#e879f9 bold",
    "heading_3": "#06b6d4 bold"
})

qbot_light_rich_theme = RichTheme({
    # User messages  
    "user_message": "#0066cc bold",
    "user_symbol": "#0052a3",
    
    # AI responses
    "ai_response": "#9333ea",
    "ai_symbol": "#7c3aed",
    
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
    "thinking": "#6b7280 dim",               # Gray dim for agent thinking
    "user_prompt": "#0066cc dim",            # Blue dim for user prompt
    "code_inline": "#0891b2",
    "code_block": "#059669",
    "heading_1": "#d97706 bold",
    "heading_2": "#9333ea bold", 
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
    "thinking": "#75715e dim",               # Muted gray dim for agent thinking
    "user_prompt": "#66d9ef dim",            # Bright cyan dim for user prompt
    "code_inline": "#e6db74",
    "code_block": "#a6e22e", 
    "heading_1": "#f92672 bold",
    "heading_2": "#66d9ef bold",
    "heading_3": "#a6e22e bold"
})

# Theme registries for easy access
QBOT_TEXTUAL_THEMES = {
    "dark": qbot_dark_theme,
    "light": qbot_light_theme, 
    "monokai": qbot_monokai_theme
}

QBOT_RICH_THEMES = {
    "dark": qbot_dark_rich_theme,
    "light": qbot_light_rich_theme,
    "monokai": qbot_monokai_rich_theme
}

# Legacy alias for backward compatibility
QBOT_THEMES = QBOT_TEXTUAL_THEMES
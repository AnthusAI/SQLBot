"""
Rich Theme Generator for SQLBot

This module dynamically generates Rich themes from Textual ColorSystem themes,
ensuring consistency between the Textual app and CLI text interfaces without
requiring code file translation or duplication.
"""

from typing import Dict, Optional
from rich.theme import Theme as RichTheme

# Optional textual imports - only needed when generating from Textual themes
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


class RichThemeGenerator:
    """
    Generates Rich themes dynamically from Textual ColorSystem themes
    combined with SQLBot-specific message colors.
    """

    def __init__(self):
        self._temp_app = None
        if TEXTUAL_AVAILABLE:
            # Create temporary app to access Textual's built-in themes
            self._temp_app = App()

    def generate_rich_theme(self, textual_theme_name: str, message_colors: Dict[str, str]) -> RichTheme:
        """
        Generate a Rich theme from a Textual theme name and SQLBot message colors.

        Args:
            textual_theme_name: Name of Textual built-in theme (e.g., "tokyo-night")
            message_colors: SQLBot message colors from QBOT_MESSAGE_COLORS

        Returns:
            Rich Theme object ready for use with Console
        """
        if not TEXTUAL_AVAILABLE:
            # Fallback to basic theme if Textual not available
            return self._create_fallback_theme(message_colors)

        # Get base colors from Textual theme
        base_colors = self._extract_textual_colors(textual_theme_name)

        # Build Rich theme dictionary
        rich_theme_dict = {}

        # Add SQLBot message colors
        rich_theme_dict.update(self._build_message_styles(message_colors))

        # Add derived colors from Textual theme
        rich_theme_dict.update(self._build_base_styles(base_colors, message_colors))

        return RichTheme(rich_theme_dict)

    def generate_rich_theme_from_user_theme(self, user_theme) -> RichTheme:
        """
        Generate a Rich theme from a user-defined SQLBotTheme object.

        Args:
            user_theme: SQLBotTheme object from user YAML file

        Returns:
            Rich Theme object ready for use with Console
        """
        # Extract colors from user theme
        message_colors = {
            'user_message': user_theme.user_message,
            'ai_response': user_theme.ai_response,
            'system_message': user_theme.system_message,
            'info_message': user_theme.info_message,
            'code_inline': user_theme.code_inline,
            'code_block': user_theme.code_block,
            'tool_call': user_theme.tool_call,
            'tool_result': user_theme.tool_result,
            'thinking': user_theme.thinking,
            'success': user_theme.success,
            'error': user_theme.error,
            'warning': user_theme.warning,
        }

        base_colors = {
            'primary': user_theme.primary,
            'secondary': user_theme.secondary,
            'background': user_theme.background,
            'surface': user_theme.surface,
            'panel': user_theme.panel,
            'accent': user_theme.accent,
        }

        # Build Rich theme dictionary
        rich_theme_dict = {}

        # Add SQLBot message colors
        rich_theme_dict.update(self._build_message_styles(message_colors))

        # Add base colors
        rich_theme_dict.update(self._build_base_styles(base_colors, message_colors))

        return RichTheme(rich_theme_dict)

    def _extract_textual_colors(self, theme_name: str) -> Dict[str, str]:
        """
        Extract key colors from a Textual built-in theme.

        This is a simplified extraction since we can't easily access Textual's
        internal ColorSystem. We'll use known good colors for the main themes.
        """
        # Known color mappings for key Textual themes
        # These are extracted from Textual's source or documentation
        theme_colors = {
            'tokyo-night': {
                'primary': '#7aa2f7',
                'secondary': '#bb9af7',
                'background': '#1a1b26',
                'surface': '#24283b',
                'accent': '#73daca',
                'success': '#9ece6a',
                'warning': '#e0af68',
                'error': '#f7768e',
            },
            'textual-dark': {
                'primary': '#0178d4',
                'secondary': '#004578',
                'background': '#121212',
                'surface': '#1e1e1e',
                'accent': '#03dac6',
                'success': '#4caf50',
                'warning': '#ff9800',
                'error': '#f44336',
            },
            'textual-light': {
                'primary': '#0178d4',
                'secondary': '#48a9e6',
                'background': '#ffffff',
                'surface': '#f5f5f5',
                'accent': '#018786',
                'success': '#2e7d32',
                'warning': '#f57c00',
                'error': '#d32f2f',
            },
            'catppuccin-mocha': {
                'primary': '#89b4fa',
                'secondary': '#b4befe',
                'background': '#1e1e2e',
                'surface': '#313244',
                'accent': '#94e2d5',
                'success': '#a6e3a1',
                'warning': '#f9e2af',
                'error': '#f38ba8',
            },
            'catppuccin-latte': {
                'primary': '#1e66f5',
                'secondary': '#4c7ff9',
                'background': '#eff1f5',
                'surface': '#e6e9ef',
                'accent': '#179299',
                'success': '#40a02b',
                'warning': '#df8e1d',
                'error': '#d20f39',
            },
            'solarized-light': {
                'primary': '#268bd2',
                'secondary': '#2aa198',
                'background': '#fdf6e3',
                'surface': '#eee8d5',
                'accent': '#859900',
                'success': '#859900',
                'warning': '#b58900',
                'error': '#dc322f',
            },
            'solarized-dark': {
                'primary': '#268bd2',
                'secondary': '#2aa198',
                'background': '#002b36',
                'surface': '#073642',
                'accent': '#859900',
                'success': '#859900',
                'warning': '#b58900',
                'error': '#dc322f',
            }
        }

        return theme_colors.get(theme_name, theme_colors['tokyo-night'])

    def _build_message_styles(self, message_colors: Dict[str, str]) -> Dict[str, str]:
        """Build Rich theme styles for SQLBot message types."""
        styles = {}

        # User messages
        if message_colors.get('user_message'):
            styles['user_message'] = f"{message_colors['user_message']} bold"
            styles['user_symbol'] = message_colors['user_message']

        # AI responses
        if message_colors.get('ai_response'):
            styles['ai_response'] = message_colors['ai_response']
            styles['ai_symbol'] = message_colors['ai_response']

        # System messages
        if message_colors.get('system_message'):
            styles['system_message'] = message_colors['system_message']
            styles['system_symbol'] = message_colors['system_message']

        # Status messages
        if message_colors.get('error'):
            styles['error_message'] = f"{message_colors['error']} bold"
            styles['error_symbol'] = message_colors['error']

        if message_colors.get('warning'):
            styles['warning_message'] = message_colors['warning']
            styles['warning_symbol'] = message_colors['warning']

        if message_colors.get('success'):
            styles['success_message'] = f"{message_colors['success']} bold"
            styles['success_symbol'] = message_colors['success']

        # Tool colors
        if message_colors.get('tool_call'):
            styles['tool_call'] = message_colors['tool_call']
            styles['tool_call_symbol'] = message_colors['tool_call']

        if message_colors.get('tool_result'):
            styles['tool_result'] = message_colors['tool_result']
            styles['tool_result_symbol'] = message_colors['tool_result']

        # Content formatting
        if message_colors.get('thinking'):
            styles['thinking'] = f"{message_colors['thinking']} dim"

        if message_colors.get('code_inline'):
            styles['code_inline'] = message_colors['code_inline']

        if message_colors.get('code_block'):
            styles['code_block'] = message_colors['code_block']

        # User prompt styling
        if message_colors.get('user_message'):
            styles['user_prompt'] = f"{message_colors['user_message']} dim"

        return styles

    def _build_base_styles(self, base_colors: Dict[str, str], message_colors: Dict[str, str]) -> Dict[str, str]:
        """Build additional Rich theme styles from base colors."""
        styles = {}

        # Info messages default to accent or primary
        info_color = message_colors.get('info_message') or base_colors.get('accent') or base_colors.get('primary')
        if info_color:
            styles['info_message'] = info_color
            styles['info_symbol'] = info_color

        # Headings using various colors
        if base_colors.get('accent'):
            styles['heading_1'] = f"{base_colors['accent']} bold"
        if message_colors.get('ai_response'):
            styles['heading_2'] = f"{message_colors['ai_response']} bold"
        if base_colors.get('primary'):
            styles['heading_3'] = f"{base_colors['primary']} bold"

        return styles

    def _create_fallback_theme(self, message_colors: Dict[str, str]) -> RichTheme:
        """Create a basic fallback theme when Textual is not available."""
        fallback_dict = {
            'user_message': '#66ccff bold',
            'user_symbol': '#66ccff',
            'ai_response': '#ffaaff',
            'ai_symbol': '#ffaaff',
            'system_message': '#06b6d4',
            'system_symbol': '#0891b2',
            'error_message': '#f87171 bold',
            'error_symbol': '#ef4444',
            'warning_message': '#fbbf24',
            'warning_symbol': '#f59e0b',
            'success_message': '#10b981 bold',
            'success_symbol': '#059669',
            'info_message': '#06b6d4',
            'info_symbol': '#0891b2',
            'thinking': '#6b7280 dim',
            'user_prompt': '#66ccff dim',
            'code_inline': '#06b6d4',
            'code_block': '#10b981',
        }

        # Override with provided message colors
        for key, value in message_colors.items():
            if value and key in ['user_message', 'ai_response', 'system_message', 'error', 'warning', 'success']:
                style_key = f"{key}_message" if key not in ['error', 'warning', 'success'] else f"{key}_message"
                symbol_key = f"{key}_symbol" if key not in ['error', 'warning', 'success'] else f"{key}_symbol"

                if 'message' in key or key in ['error', 'warning', 'success']:
                    fallback_dict[style_key] = f"{value} bold" if key in ['error', 'success'] else value
                    fallback_dict[symbol_key] = value

        return RichTheme(fallback_dict)


# Global instance for easy access
_theme_generator: Optional[RichThemeGenerator] = None


def get_rich_theme_generator() -> RichThemeGenerator:
    """Get the global Rich theme generator instance."""
    global _theme_generator
    if _theme_generator is None:
        _theme_generator = RichThemeGenerator()
    return _theme_generator
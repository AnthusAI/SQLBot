"""
Unit tests for the QBot theme system.

This test suite ensures that the theme system works correctly and provides
consistent colors across both Textual TUI and Rich CLI interfaces.
"""

import pytest
from unittest.mock import patch, MagicMock

from qbot.interfaces.theme_system import (
    QBotThemeManager, ThemeMode, 
    DODGER_BLUE_DARK, DODGER_BLUE_LIGHT, MAGENTA1, DEEP_PINK_LIGHT,
    PURE_BLUE_TEXT, PURE_BLUE_INPUT_BORDER,
    QBOT_MESSAGE_COLORS, get_theme_manager
)


class TestThemeConstants:
    """Test that theme color constants are properly defined"""
    
    def test_color_constants_are_valid_hex(self):
        """Test that all color constants are valid hex colors"""
        colors = [DODGER_BLUE_DARK, DODGER_BLUE_LIGHT, MAGENTA1, DEEP_PINK_LIGHT]
        
        for color in colors:
            assert color.startswith('#'), f"Color {color} should start with #"
            assert len(color) == 7, f"Color {color} should be 7 characters long"
            # Test that it's valid hex
            int(color[1:], 16)  # Will raise ValueError if not valid hex
    
    def test_colors_are_web_safe_or_appropriate(self):
        """Test that colors are appropriate for their use case"""
        # User message colors should be blue-ish
        assert 'ff' in DODGER_BLUE_DARK.lower() or 'cc' in DODGER_BLUE_DARK.lower()
        assert 'ff' in DODGER_BLUE_LIGHT.lower() or 'cc' in DODGER_BLUE_LIGHT.lower()
        
        # AI response colors should be pink/magenta-ish
        assert 'ff' in MAGENTA1.lower()
        assert 'ff' in DEEP_PINK_LIGHT.lower()
    
    def test_color_constants_are_lighter_versions(self):
        """Test that the current colors are appropriately light"""
        # These should be light colors (high RGB values)
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # All colors should have high brightness
        for color in [DODGER_BLUE_DARK, MAGENTA1, DEEP_PINK_LIGHT]:
            r, g, b = hex_to_rgb(color)
            brightness = (r + g + b) / 3
            assert brightness > 150, f"Color {color} should be light (brightness > 150), got {brightness}"


class TestQBotThemeManager:
    """Test the QBotThemeManager class"""
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_initialization(self, mock_app):
        """Test that theme manager initializes correctly"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        assert manager.current_mode == ThemeMode.QBOT
        assert manager.is_builtin_theme is True
        assert manager.current_textual_theme_name == "tokyo-night"
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_get_color_builtin_theme(self, mock_app):
        """Test getting colors from built-in themes"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        # Test getting AI response color
        ai_color = manager.get_color('ai_response')
        assert ai_color == MAGENTA1
        
        # Test getting user message color
        user_color = manager.get_color('user_message')
        assert user_color == PURE_BLUE_TEXT
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_get_color_unknown_type(self, mock_app):
        """Test getting unknown color type returns None"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        unknown_color = manager.get_color('nonexistent_color')
        assert unknown_color is None
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_set_theme(self, mock_app):
        """Test changing themes"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        # Change to light theme
        manager.set_theme(ThemeMode.TEXTUAL_LIGHT)
        assert manager.current_mode == ThemeMode.TEXTUAL_LIGHT
        assert manager.current_textual_theme_name == "textual-light"
        
        # AI color should be different for light theme
        ai_color = manager.get_color('ai_response')
        assert ai_color == DEEP_PINK_LIGHT
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_get_textual_theme_name(self, mock_app):
        """Test getting Textual theme name"""
        manager = QBotThemeManager(ThemeMode.TOKYO_NIGHT)
        
        theme_name = manager.get_textual_theme_name()
        assert theme_name == "tokyo-night"
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_manager_get_available_themes(self, mock_app):
        """Test getting list of available themes"""
        manager = QBotThemeManager()
        
        available = manager.get_available_themes()
        
        # Should include built-in themes
        assert "tokyo-night" in available
        assert "textual-dark" in available
        assert "textual-light" in available
        
        # Should include aliases
        assert "qbot" in available
        assert "dark" in available
        assert "light" in available
        
        # All should be marked as built-in
        assert available["tokyo-night"] == "built-in"
        assert available["qbot"] == "built-in"


class TestThemeMessageColors:
    """Test the QBOT_MESSAGE_COLORS mapping"""
    
    def test_message_colors_structure(self):
        """Test that message colors have the expected structure"""
        # Should have default theme
        assert "default" in QBOT_MESSAGE_COLORS
        
        # Should have tokyo-night theme (QBot default)
        assert "tokyo-night" in QBOT_MESSAGE_COLORS
        
        # Each theme should have required color types
        required_colors = ["user_message", "ai_response"]
        
        for theme_name, colors in QBOT_MESSAGE_COLORS.items():
            for color_type in required_colors:
                assert color_type in colors, f"Theme {theme_name} missing {color_type}"
    
    def test_message_colors_use_constants(self):
        """Test that message colors use the defined constants"""
        # Tokyo-night should use our constants
        tokyo_colors = QBOT_MESSAGE_COLORS["tokyo-night"]
        
        assert tokyo_colors["user_message"] == PURE_BLUE_TEXT
        assert tokyo_colors["ai_response"] == MAGENTA1
        
        # Default should also use our constants if it exists
        if "default" in QBOT_MESSAGE_COLORS:
            default_colors = QBOT_MESSAGE_COLORS["default"]
            assert default_colors["user_message"] == PURE_BLUE_TEXT
            assert default_colors["ai_response"] == MAGENTA1
    
    def test_light_themes_use_appropriate_colors(self):
        """Test that light themes use light-appropriate colors"""
        light_themes = ["textual-light", "textual-ansi"]
        
        for theme_name in light_themes:
            if theme_name in QBOT_MESSAGE_COLORS:
                colors = QBOT_MESSAGE_COLORS[theme_name]
                # Light themes should use different colors than dark themes
                if "ai_response" in colors:
                    assert colors["ai_response"] == DEEP_PINK_LIGHT


class TestGlobalThemeManager:
    """Test the global theme manager singleton"""
    
    @patch('qbot.interfaces.theme_system.QBotThemeManager')
    def test_get_theme_manager_singleton(self, mock_theme_manager_class):
        """Test that get_theme_manager returns a singleton"""
        mock_instance = MagicMock()
        mock_theme_manager_class.return_value = mock_instance
        
        # Clear any existing global instance
        import qbot.interfaces.theme_system as theme_module
        theme_module._theme_manager = None
        
        # First call should create instance
        manager1 = get_theme_manager()
        assert manager1 == mock_instance
        mock_theme_manager_class.assert_called_once()
        
        # Second call should return same instance
        manager2 = get_theme_manager()
        assert manager2 == mock_instance
        assert manager1 is manager2
        # Should not create a new instance
        mock_theme_manager_class.assert_called_once()


class TestThemeIntegration:
    """Integration tests for theme system"""
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_system_provides_consistent_colors(self, mock_app):
        """Test that theme system provides consistent colors across different themes"""
        manager = QBotThemeManager()
        
        # Test different themes
        themes_to_test = [ThemeMode.QBOT, ThemeMode.TEXTUAL_DARK, ThemeMode.TEXTUAL_LIGHT]
        
        for theme_mode in themes_to_test:
            manager.set_theme(theme_mode)
            
            # Should always get some color for user messages and AI responses
            user_color = manager.get_color('user_message')
            ai_color = manager.get_color('ai_response')
            
            assert user_color is not None, f"Theme {theme_mode} should provide user_message color"
            assert ai_color is not None, f"Theme {theme_mode} should provide ai_response color"
            
            # Colors should be valid hex
            if user_color:
                assert user_color.startswith('#') and len(user_color) == 7
            if ai_color:
                assert ai_color.startswith('#') and len(ai_color) == 7
    
    @patch('qbot.interfaces.theme_system.App')
    def test_theme_system_handles_missing_colors_gracefully(self, mock_app):
        """Test that theme system handles missing colors gracefully"""
        manager = QBotThemeManager()
        
        # Test getting a color that might not exist in all themes
        tool_color = manager.get_color('tool_call')
        # Should either return a color or None, not crash
        if tool_color is not None:
            assert isinstance(tool_color, str)


class TestThemeSystemRegression:
    """Regression tests for theme system issues"""
    
    @patch('qbot.interfaces.theme_system.App')
    def test_ai_messages_not_white_regression(self, mock_app):
        """Regression test: AI messages should not be pure white"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        ai_color = manager.get_color('ai_response')
        
        # Should not be pure white
        assert ai_color != "#ffffff", "AI messages should not be pure white"
        assert ai_color != "#FFFFFF", "AI messages should not be pure white"
        
        # Should be a visible color (not too close to white)
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        r, g, b = hex_to_rgb(ai_color)
        # At least one component should be significantly less than 255
        assert min(r, g, b) < 240, f"AI color {ai_color} is too close to white"
    
    @patch('qbot.interfaces.theme_system.App')
    def test_colors_are_appropriately_light(self, mock_app):
        """Regression test: Colors should be light but still visible"""
        manager = QBotThemeManager(ThemeMode.QBOT)
        
        ai_color = manager.get_color('ai_response')
        user_color = manager.get_color('user_message')
        
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Colors should be light (high brightness) but not pure white
        for color_name, color in [("ai_response", ai_color), ("user_message", user_color)]:
            r, g, b = hex_to_rgb(color)
            brightness = (r + g + b) / 3
            
            # Should be light (brightness > 150) but not too light (< 240)
            assert 150 < brightness < 240, f"{color_name} color {color} brightness {brightness} should be between 150-240"

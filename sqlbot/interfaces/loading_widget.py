"""
Loading Widget for SQLBot Textual Interface

Provides fallback text-based thinking indicators for CLI mode and rebuilds.
"""

from rich.text import Text
from rich.spinner import Spinner
from textual.widgets import Static


# Simple static version for fallback and CLI
def create_thinking_text(message: str = "...", style: str = "dim") -> Text:
    """Create a static thinking indicator as Rich Text for CLI mode and fallbacks"""
    # Simple dots for fallback - no robot emoji
    text = Text()
    text.append("• • • • •", style=style)
    
    return text


class AnimatedSpinnerWidget(Static):
    """Custom Textual widget that displays an animated Rich Spinner"""
    
    def __init__(self, spinner_name: str = "star", text: str = ""):
        super().__init__()
        self.spinner = Spinner(spinner_name, text=text)
        self.update(self.spinner)
    
    def on_mount(self) -> None:
        """Start the spinner animation when the widget is mounted"""
        # Update 10 times per second for smooth animation
        self.set_interval(1 / 10, self.update_spinner)
    
    def update_spinner(self) -> None:
        """Update the spinner display to show next animation frame"""
        self.update(self.spinner)
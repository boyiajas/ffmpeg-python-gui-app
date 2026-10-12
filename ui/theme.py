"""
theme.py - Colors, styling, and design constants for Video Audio Merger.
Matches Ubuntu GNOME / Yaru aesthetics with dynamic Dark/Light theme adaptability.
"""

UBUNTU_ORANGE = "#E95420"
UBUNTU_DARK_AUBERGINE = "#2C001E"
UBUNTU_WARM_GREY = "#AEA79F"
ACCENT_COLOR = "#E95420"
ACCENT_HOVER = "#D14414"

# Status colors
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_INFO = "#38BDF8"

# Neutral colors
COLOR_BG = "#F5F5F7"
COLOR_PANEL_BG = "#FFFFFF"
COLOR_BORDER = "#E5E7EB"
COLOR_TEXT_PRIMARY = "#F9FAFB"
COLOR_TEXT_MUTED = "#D1D5DB"
COLOR_CONSOLE_BG = "#1E1E2E"
COLOR_CONSOLE_FG = "#CDD6F4"

# Dimensions
WINDOW_WIDTH = 980
WINDOW_HEIGHT = 740
MIN_WIDTH = 840
MIN_HEIGHT = 650


def is_dark_mode() -> bool:
    """Detects whether system GTK/Ubuntu theme is currently in dark mode."""
    try:
        import wx
        bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        lum = 0.299 * bg.Red() + 0.587 * bg.Green() + 0.114 * bg.Blue()
        return lum < 128
    except Exception:
        return False


def get_text_primary() -> str:
    """High-contrast main text color."""
    return "#F9FAFB" if is_dark_mode() else "#111827"


def get_text_muted() -> str:
    """Crisp secondary text color for media details."""
    return "#D1D5DB" if is_dark_mode() else "#4B5563"


def get_processing_color() -> str:
    """Vivid, high-contrast color for processing status."""
    return "#38BDF8" if is_dark_mode() else "#0284C7"  # Electric Sky Blue / Deep Sky Blue


def get_success_color() -> str:
    """Vivid emerald green for completion."""
    return "#34D399" if is_dark_mode() else "#059669"


def get_danger_color() -> str:
    """Vivid coral red for errors."""
    return "#F87171" if is_dark_mode() else "#DC2626"


def get_warning_color() -> str:
    """Vivid amber/orange for alerts."""
    return "#FBBF24" if is_dark_mode() else "#D97706"

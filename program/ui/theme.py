"""Light/dark tokens and global stylesheet for glass UI (system / light / dark)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, cast

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QGuiApplication, QPalette

ThemeMode = Literal["system", "light", "dark"]

_SETTINGS_KEY = "appearance/mode"
_appearance_mode: ThemeMode = "system"


def get_appearance_mode() -> ThemeMode:
    return _appearance_mode


def set_appearance_mode(mode: str) -> None:
    global _appearance_mode
    m = str(mode).lower()
    if m not in ("system", "light", "dark"):
        m = "system"
    _appearance_mode = cast(ThemeMode, m)
    s = QSettings()
    s.setValue(_SETTINGS_KEY, m)
    s.sync()


def load_saved_appearance() -> None:
    """Call after QApplication exists and org/app name are set."""
    global _appearance_mode
    s = QSettings()
    v = s.value(_SETTINGS_KEY, "system")
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="replace")
    v = str(v).lower() if v else "system"
    if v not in ("system", "light", "dark"):
        v = "system"
    _appearance_mode = cast(ThemeMode, v)


def _is_dark_palette() -> bool:
    app = QGuiApplication.instance()
    if app is None:
        return False
    bg = app.palette().color(QPalette.ColorRole.Window)
    return bg.lightness() < 128


def effective_dark() -> bool:
    if _appearance_mode == "light":
        return False
    if _appearance_mode == "dark":
        return True
    return _is_dark_palette()


def _font_family() -> str:
    return (
        '-apple-system, "SF Pro Text", "SF Pro Display", '
        '"Helvetica Neue", Helvetica, Arial, sans-serif'
    )


def _token_map_dark() -> dict[str, str]:
    return {
        "FONT_FAMILY": _font_family(),
        "BG_TOP": "#1c1d22",
        "BG_BOTTOM": "#0f1014",
        "GLASS_BG": "rgba(255,255,255,0.08)",
        "GLASS_BORDER": "rgba(255,255,255,0.14)",
        "TEXT_PRIMARY": "#ffffff",
        "TEXT_SECONDARY": "rgba(255,255,255,0.62)",
        "ACCENT": "#0a84ff",
        "ACCENT_HOVER": "#409cff",
        "ACCENT_TEXT": "#ffffff",
        "SUCCESS": "#32d74b",
        "ERROR": "#ff453a",
        "FIELD_BG": "rgba(255,255,255,0.06)",
        "FIELD_BORDER": "rgba(255,255,255,0.12)",
        "LOG_BG": "rgba(0,0,0,0.25)",
        "BTN_SECONDARY_BG": "rgba(255,255,255,0.08)",
        "BTN_SECONDARY_BORDER": "rgba(255,255,255,0.14)",
        "BTN_SECONDARY_HOVER": "rgba(255,255,255,0.12)",
        "BTN_DISABLED_BG": "rgba(255,255,255,0.06)",
        "BTN_DISABLED_TEXT": "rgba(245,245,247,0.35)",
        "BTN_DISABLED_BORDER": "rgba(255,255,255,0.08)",
        "SCROLL_HANDLE": "rgba(255,255,255,0.25)",
        "SPLITTER_HANDLE": "rgba(255,255,255,0.12)",
    }


def _token_map_light() -> dict[str, str]:
    return {
        "FONT_FAMILY": _font_family(),
        "BG_TOP": "#e8eef8",
        "BG_BOTTOM": "#d4e0f5",
        "GLASS_BG": "rgba(255,255,255,0.55)",
        "GLASS_BORDER": "rgba(255,255,255,0.75)",
        "TEXT_PRIMARY": "#000000",
        "TEXT_SECONDARY": "rgba(0,0,0,0.58)",
        "ACCENT": "#0071e3",
        "ACCENT_HOVER": "#0077ed",
        "ACCENT_TEXT": "#ffffff",
        "SUCCESS": "#1e8e3e",
        "ERROR": "#b00020",
        "FIELD_BG": "rgba(255,255,255,0.72)",
        "FIELD_BORDER": "rgba(0,0,0,0.10)",
        "LOG_BG": "rgba(255,255,255,0.45)",
        "BTN_SECONDARY_BG": "rgba(255,255,255,0.55)",
        "BTN_SECONDARY_BORDER": "rgba(0,0,0,0.12)",
        "BTN_SECONDARY_HOVER": "rgba(255,255,255,0.85)",
        "BTN_DISABLED_BG": "rgba(0,0,0,0.06)",
        "BTN_DISABLED_TEXT": "rgba(29,29,31,0.35)",
        "BTN_DISABLED_BORDER": "rgba(0,0,0,0.08)",
        "SCROLL_HANDLE": "rgba(0,0,0,0.20)",
        "SPLITTER_HANDLE": "rgba(0,0,0,0.08)",
    }


def build_token_map() -> dict[str, str]:
    return _token_map_dark() if effective_dark() else _token_map_light()


def _styles_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        direct = base / "ui" / "styles"
        if direct.exists():
            return direct
        resources = base.parent / "Resources" / "ui" / "styles"
        if resources.exists():
            return resources
        return direct
    return Path(__file__).resolve().parent / "styles"


def load_global_stylesheet() -> str:
    path = _styles_dir() / "glass.qss"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = _FALLBACK_MINIMAL_QSS
    tokens = build_token_map()
    for key, value in tokens.items():
        text = text.replace(f"<<{key}>>", value)
    return text


def _palette_light() -> QPalette:
    p = QPalette()
    black = QColor(0, 0, 0)
    dim = QColor(60, 60, 67)
    base = QColor(255, 255, 255)
    window = QColor(232, 238, 248)
    p.setColor(QPalette.ColorRole.Window, window)
    p.setColor(QPalette.ColorRole.WindowText, black)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 247, 250))
    p.setColor(QPalette.ColorRole.Text, black)
    p.setColor(QPalette.ColorRole.ButtonText, black)
    p.setColor(QPalette.ColorRole.PlaceholderText, dim)
    p.setColor(QPalette.ColorRole.ToolTipBase, base)
    p.setColor(QPalette.ColorRole.ToolTipText, black)
    return p


def _palette_dark() -> QPalette:
    p = QPalette()
    white = QColor(255, 255, 255)
    soft = QColor(245, 245, 247)
    dim = QColor(180, 180, 188)
    base = QColor(40, 42, 48)
    window = QColor(28, 29, 34)
    p.setColor(QPalette.ColorRole.Window, window)
    p.setColor(QPalette.ColorRole.WindowText, soft)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 52, 60))
    p.setColor(QPalette.ColorRole.Text, white)
    p.setColor(QPalette.ColorRole.ButtonText, soft)
    p.setColor(QPalette.ColorRole.PlaceholderText, dim)
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(50, 50, 55))
    p.setColor(QPalette.ColorRole.ToolTipText, white)
    return p


def apply_to_application() -> None:
    app = QGuiApplication.instance()
    if app is None:
        return
    mode = get_appearance_mode()
    if mode == "light":
        app.setPalette(_palette_light())
    elif mode == "dark":
        app.setPalette(_palette_dark())
    else:
        style = app.style()
        if style is not None:
            app.setPalette(style.standardPalette())
    app.setStyleSheet(load_global_stylesheet())


_FALLBACK_MINIMAL_QSS = """
#AppRoot { background: <<BG_TOP>>; }
* { font-family: <<FONT_FAMILY>>; color: <<TEXT_PRIMARY>>; }
"""

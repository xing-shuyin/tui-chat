from __future__ import annotations

import os
import sys
from typing import Optional
from textual.binding import Binding


def is_macos() -> bool:
    """Return True if running on macOS (darwin)."""
    return sys.platform == "darwin"


def get_terminal_environment() -> dict[str, str]:
    """Inspect environment variables for terminal emulator details."""
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")
    colorterm = os.environ.get("COLORTERM", "")

    name = "Standard Terminal"
    if "iTerm" in term_program or term_program == "iTerm.app":
        name = "iTerm2"
    elif term_program == "Apple_Terminal":
        name = "Apple Terminal"
    elif term_program == "vscode":
        name = "VS Code Terminal"
    elif "kitty" in term or "KITTY_PID" in os.environ:
        name = "Kitty"
    elif "alacritty" in term or "ALACRITTY_LOG" in os.environ:
        name = "Alacritty"
    elif "wezterm" in term_program.lower():
        name = "WezTerm"

    return {
        "name": name,
        "term_program": term_program,
        "term": term,
        "colorterm": colorterm,
        "is_macos": str(is_macos()),
    }


def get_chat_bindings() -> list[Binding]:
    """Generate cross-platform terminal bindings with macOS-specific display and Option/Alt meta keys."""
    macos = is_macos()

    return [
        # New chat
        Binding(
            "ctrl+n",
            "new_chat",
            "新建对话",
            key_display="^N / ⌥N" if macos else "Ctrl+N",
            priority=True,
        ),
        Binding("alt+n", "new_chat", "新建对话", show=False, priority=True),

        # Toggle sidebar
        Binding(
            "ctrl+b",
            "toggle_sidebar",
            "侧边栏",
            key_display="^B / ⌥B" if macos else "Ctrl+B",
            priority=True,
        ),
        Binding("alt+b", "toggle_sidebar", "侧边栏", show=False, priority=True),

        # Delete session
        Binding(
            "ctrl+d",
            "delete_current_session",
            "删除会话",
            key_display="^D / ⌥D" if macos else "Ctrl+D",
            priority=True,
        ),
        Binding("alt+d", "delete_current_session", "删除会话", show=False, priority=True),

        # Copy last message
        Binding(
            "ctrl+y",
            "copy_last_message",
            "复制消息",
            key_display="^Y / ⌥C" if macos else "Ctrl+Y",
            priority=True,
        ),
        Binding("alt+c", "copy_last_message", "复制消息", show=False, priority=True),

        # Copy code block
        Binding(
            "ctrl+k",
            "copy_last_code",
            "复制代码",
            key_display="^K / ⌥K" if macos else "Ctrl+K",
            priority=True,
        ),
        Binding("alt+k", "copy_last_code", "复制代码", show=False, priority=True),

        # Paste from system clipboard
        Binding(
            "ctrl+v",
            "paste_clipboard",
            "剪贴板粘贴",
            key_display="^V / ⌥V" if macos else "Ctrl+V",
            priority=True,
        ),
        Binding("alt+v", "paste_clipboard", "剪贴板粘贴", show=False, priority=True),

        # Quit
        Binding(
            "ctrl+q",
            "quit",
            "退出",
            key_display="^Q" if macos else "Ctrl+Q",
            priority=True,
        ),
    ]

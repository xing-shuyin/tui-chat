import sys
from unittest.mock import patch

from tui_chat.keymap import get_chat_bindings, get_terminal_environment, is_macos


def test_is_macos():
    assert is_macos() == (sys.platform == "darwin")


def test_get_terminal_environment():
    with patch.dict("os.environ", {"TERM_PROGRAM": "iTerm.app", "TERM": "xterm-256color"}):
        env = get_terminal_environment()
        assert env["name"] == "iTerm2"
        assert env["term_program"] == "iTerm.app"

    with patch.dict("os.environ", {"TERM_PROGRAM": "Apple_Terminal"}):
        env = get_terminal_environment()
        assert env["name"] == "Apple Terminal"

    with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
        env = get_terminal_environment()
        assert env["name"] == "VS Code Terminal"


def test_get_chat_bindings_macos():
    with patch("tui_chat.keymap.is_macos", return_value=True):
        bindings = get_chat_bindings()
        keys = [b.key for b in bindings]
        actions = [b.action for b in bindings]

        assert "ctrl+n" in keys
        assert "alt+n" in keys
        assert "ctrl+y" in keys
        assert "alt+c" in keys
        assert "ctrl+k" in keys
        assert "alt+k" in keys
        assert "ctrl+v" in keys
        assert "alt+v" in keys

        assert "new_chat" in actions
        assert "copy_last_message" in actions
        assert "copy_last_code" in actions
        assert "paste_clipboard" in actions

        # Check key_display contains macOS style symbols (^ or ⌥)
        displays = [b.key_display for b in bindings if b.key_display]
        assert any("⌥" in d for d in displays)


def test_get_chat_bindings_non_macos():
    with patch("tui_chat.keymap.is_macos", return_value=False):
        bindings = get_chat_bindings()
        displays = [b.key_display for b in bindings if b.key_display]
        assert all("⌥" not in d for d in displays)
        assert any("Ctrl+" in d for d in displays)

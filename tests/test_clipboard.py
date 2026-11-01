import subprocess
import sys
from unittest.mock import MagicMock, patch
import pytest

from tui_chat.clipboard import (
    BaseClipboardBackend,
    ClipboardService,
    LinuxClipboardBackend,
    MacOSClipboardBackend,
    MemoryClipboardBackend,
    WindowsClipboardBackend,
    extract_code_blocks,
    get_last_code_block,
)


def test_extract_code_blocks_empty():
    assert extract_code_blocks("") == []
    assert extract_code_blocks("Just plain text with no code") == []


def test_extract_code_blocks_single():
    text = "Intro\n```python\nprint('hello world')\n```\nOutro"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "python"
    assert "print('hello world')" in blocks[0][1]


def test_extract_code_blocks_multiple_and_no_lang():
    text = """
```python
def foo():
    return 42
```

Here is a shell script:
```bash
echo "test"
```

And generic:
```
raw block
```
"""
    blocks = extract_code_blocks(text)
    assert len(blocks) == 3
    assert blocks[0] == ("python", "def foo():\n    return 42")
    assert blocks[1] == ("bash", 'echo "test"')
    assert blocks[2] == ("", "raw block")

    last = get_last_code_block(text)
    assert last == ("", "raw block")


def test_memory_clipboard_backend():
    backend = MemoryClipboardBackend()
    assert backend.is_available() is True
    assert backend.paste() == ""
    backend.copy("test string")
    assert backend.paste() == "test string"


def test_macos_clipboard_backend():
    backend = MacOSClipboardBackend()
    if sys.platform == "darwin":
        assert backend.is_available() is True
        success = backend.copy("macOS clipboard test content")
        assert success is True
        val = backend.paste()
        assert "macOS clipboard test content" in val
    else:
        assert backend.is_available() is False


def test_macos_clipboard_backend_error_handling():
    backend = MacOSClipboardBackend()
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("Failed")):
        assert backend.copy("fail") is False
        assert backend.paste() == ""


def test_linux_clipboard_backend_simulation():
    with patch("sys.platform", "linux"), patch("shutil.which") as mock_which, patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-0"}):
        mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd == "wl-copy" else None
        assert LinuxClipboardBackend.is_available() is True

        backend = LinuxClipboardBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="linux text")
            backend.copy("linux text")
            mock_run.assert_called_with(
                ["wl-copy"],
                input="linux text".encode("utf-8"),
                check=True,
                timeout=2.0,
            )
            val = backend.paste()
            assert val == "linux text"


def test_windows_clipboard_backend_simulation():
    with patch("sys.platform", "win32"):
        assert WindowsClipboardBackend.is_available() is True
        backend = WindowsClipboardBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="win text\r\n")
            backend.copy("win text")
            mock_run.assert_called_with(
                ["clip.exe"],
                input="win text".encode("utf-8"),
                check=True,
                timeout=2.0,
            )
            assert backend.paste() == "win text"


def test_clipboard_service_with_memory_backend():
    service = ClipboardService(backend=MemoryClipboardBackend())
    assert service.backend_name == "MemoryClipboardBackend"
    assert service.copy("hello clipboard service") is True
    assert service.paste() == "hello clipboard service"


def test_clipboard_service_fallback_on_empty_paste():
    mock_backend = MagicMock(spec=BaseClipboardBackend)
    mock_backend.copy.return_value = True
    mock_backend.paste.return_value = ""  # empty from system

    service = ClipboardService(backend=mock_backend)
    service.copy("saved to memory")
    # paste should fall back to memory
    assert service.paste() == "saved to memory"

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

CODE_BLOCK_PATTERN = re.compile(
    r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\r?\n(?P<code>[\s\S]*?)\r?\n?```"
)


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract all code blocks from Markdown text.

    Returns:
        List of tuples: (language, code_content)
    """
    blocks: list[tuple[str, str]] = []
    if not text:
        return blocks
    for match in CODE_BLOCK_PATTERN.finditer(text):
        lang = match.group("lang").strip()
        code = match.group("code")
        blocks.append((lang, code))
    return blocks


def get_last_code_block(text: str) -> Optional[tuple[str, str]]:
    """Extract the last code block from Markdown text."""
    blocks = extract_code_blocks(text)
    return blocks[-1] if blocks else None


class BaseClipboardBackend(ABC):
    """Abstract base class for platform clipboard implementations."""

    @abstractmethod
    def copy(self, text: str) -> bool:
        """Copy text to system clipboard."""
        raise NotImplementedError

    @abstractmethod
    def paste(self) -> str:
        """Paste text from system clipboard."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend can operate in the current environment."""
        raise NotImplementedError


class MacOSClipboardBackend(BaseClipboardBackend):
    """macOS native pasteboard implementation using pbcopy and pbpaste."""

    @classmethod
    def is_available(cls) -> bool:
        return sys.platform == "darwin" and shutil.which("pbcopy") is not None

    def copy(self, text: str) -> bool:
        try:
            subprocess.run(
                ["pbcopy"],
                input=text.encode("utf-8"),
                check=True,
                timeout=2.0,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"macOS pbcopy failed: {e}")
            return False

    def paste(self) -> str:
        try:
            proc = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2.0,
            )
            return proc.stdout
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"macOS pbpaste failed: {e}")
            return ""


class LinuxClipboardBackend(BaseClipboardBackend):
    """Linux clipboard implementation supporting Wayland (wl-clipboard) and X11 (xclip/xsel)."""

    def __init__(self) -> None:
        self._mode: Optional[str] = None
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
            self._mode = "wayland"
        elif shutil.which("xclip"):
            self._mode = "xclip"
        elif shutil.which("xsel"):
            self._mode = "xsel"

    @classmethod
    def is_available(cls) -> bool:
        if sys.platform != "linux":
            return False
        return (
            (bool(os.environ.get("WAYLAND_DISPLAY")) and shutil.which("wl-copy") is not None)
            or shutil.which("xclip") is not None
            or shutil.which("xsel") is not None
        )

    def copy(self, text: str) -> bool:
        try:
            if self._mode == "wayland":
                cmd = ["wl-copy"]
            elif self._mode == "xclip":
                cmd = ["xclip", "-selection", "clipboard"]
            elif self._mode == "xsel":
                cmd = ["xsel", "--clipboard", "--input"]
            else:
                return False

            subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                check=True,
                timeout=2.0,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Linux clipboard copy failed: {e}")
            return False

    def paste(self) -> str:
        try:
            if self._mode == "wayland":
                cmd = ["wl-paste", "--no-newline"]
            elif self._mode == "xclip":
                cmd = ["xclip", "-selection", "clipboard", "-o"]
            elif self._mode == "xsel":
                cmd = ["xsel", "--clipboard", "--output"]
            else:
                return ""

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=2.0,
            )
            return proc.stdout
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Linux clipboard paste failed: {e}")
            return ""


class WindowsClipboardBackend(BaseClipboardBackend):
    """Windows clipboard implementation using clip.exe and PowerShell Get-Clipboard."""

    @classmethod
    def is_available(cls) -> bool:
        return sys.platform == "win32"

    def copy(self, text: str) -> bool:
        try:
            subprocess.run(
                ["clip.exe"],
                input=text.encode("utf-8"),
                check=True,
                timeout=2.0,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Windows clip failed: {e}")
            return False

    def paste(self) -> str:
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2.0,
            )
            return proc.stdout.rstrip("\r\n")
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Windows Get-Clipboard failed: {e}")
            return ""


class MemoryClipboardBackend(BaseClipboardBackend):
    """In-memory fallback clipboard backend."""

    def __init__(self) -> None:
        self._buffer: str = ""

    @classmethod
    def is_available(cls) -> bool:
        return True

    def copy(self, text: str) -> bool:
        self._buffer = text
        return True

    def paste(self) -> str:
        return self._buffer


class ClipboardService:
    """Unified cross-platform clipboard service with automatic platform detection and fallback."""

    def __init__(self, backend: Optional[BaseClipboardBackend] = None) -> None:
        self._memory_fallback = MemoryClipboardBackend()
        if backend is not None:
            self._backend: BaseClipboardBackend = backend
        else:
            self._backend = self._detect_backend()

    def _detect_backend(self) -> BaseClipboardBackend:
        if MacOSClipboardBackend.is_available():
            return MacOSClipboardBackend()
        if LinuxClipboardBackend.is_available():
            return LinuxClipboardBackend()
        if WindowsClipboardBackend.is_available():
            return WindowsClipboardBackend()
        return self._memory_fallback

    @property
    def backend_name(self) -> str:
        return self._backend.__class__.__name__

    def copy(self, text: str) -> bool:
        """Copy text to clipboard.

        Always updates in-memory buffer as a safe fallback.
        """
        self._memory_fallback.copy(text)
        if self._backend is not self._memory_fallback:
            success = self._backend.copy(text)
            return success
        return True

    def paste(self) -> str:
        """Paste text from clipboard.

        Falls back to in-memory buffer if backend returns empty or fails.
        """
        if self._backend is not self._memory_fallback:
            val = self._backend.paste()
            if val:
                return val
        return self._memory_fallback.paste()


# Global default instance
clipboard_service = ClipboardService()

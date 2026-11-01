from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    storage_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("TUI_CHAT_HOME", Path.home() / ".tui-chat"))
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    base_url: str = Field(
        default_factory=lambda: os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    default_model: str = Field(
        default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    )
    system_prompt: str = "You are a helpful, concise AI assistant in a modern terminal UI."
    theme: str = "textual-dark"

    def ensure_directories(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "sessions").mkdir(parents=True, exist_ok=True)


config = AppConfig()

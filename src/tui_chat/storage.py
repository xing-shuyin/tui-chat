from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from tui_chat.schemas import Session, Message


class SessionStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.sessions_dir = root_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def save_session(self, session: Session) -> None:
        file_path = self._session_file(session.id)
        temp_path = file_path.with_suffix(".tmp")
        data = session.model_dump_json(indent=2)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(data)
        temp_path.replace(file_path)

    def load_session(self, session_id: str) -> Optional[Session]:
        file_path = self._session_file(session_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Session.model_validate(data)

    def list_sessions(self) -> list[Session]:
        sessions: list[Session] = []
        for file in self.sessions_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(Session.model_validate(data))
            except Exception:
                continue
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        file_path = self._session_file(session_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

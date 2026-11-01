from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    content: str
    timestamp: float = Field(default_factory=time.time)
    model: Optional[str] = None

    def to_api_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "新对话"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    model: str = "default"
    messages: list[Message] = Field(default_factory=list)

    def add_message(self, role: Role, content: str, model: Optional[str] = None) -> Message:
        msg = Message(role=role, content=content, model=model)
        self.messages.append(msg)
        self.updated_at = time.time()
        return msg


class StreamChunk(BaseModel):
    delta: str
    finish_reason: Optional[str] = None

from __future__ import annotations

import abc
import asyncio
import json
from typing import AsyncIterator, Optional
import httpx
from tui_chat.schemas import Message, StreamChunk


class BaseProvider(abc.ABC):
    @abc.abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks from the model."""
        yield StreamChunk(delta="")


class MockProvider(BaseProvider):
    """Mock provider for local testing and demonstration without API keys."""

    def __init__(self, reply_template: Optional[str] = None) -> None:
        self.reply_template = reply_template or (
            "你好！这是来自 **TUI-Chat** 的模拟回复。\n\n"
            "系统架构具有以下特点：\n"
            "- **响应式流式渲染**：平滑流式输出，避免控制台闪烁。\n"
            "- **跨平台支持**：统一兼容 Windows 与 macOS 终端。\n"
            "- **多会话持久化**：原子写入，防止状态破坏。\n\n"
            "```python\n"
            "# 示例代码块\n"
            "def hello_tui():\n"
            "    print('Hello, Terminal User Interface!')\n"
            "```\n"
            "随时可以提问其他问题！"
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[StreamChunk]:
        # Split into small chunks to simulate streaming
        words = self.reply_template.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield StreamChunk(delta=chunk)
            await asyncio.sleep(0.02)
        yield StreamChunk(delta="", finish_reason="stop")


class OpenAIProvider(BaseProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[StreamChunk]:
        api_messages: list[dict[str, str]] = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            api_messages.append(msg.to_api_dict())

        payload = {
            "model": model,
            "messages": api_messages,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    error_msg = f"API Error {response.status_code}: {body.decode(errors='replace')}"
                    yield StreamChunk(delta=error_msg, finish_reason="error")
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {}).get("content", "")
                            finish_reason = choice.get("finish_reason")
                            if delta:
                                yield StreamChunk(delta=delta, finish_reason=finish_reason)
                        except json.JSONDecodeError:
                            continue
        yield StreamChunk(delta="", finish_reason="stop")

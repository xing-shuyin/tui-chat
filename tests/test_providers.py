import pytest
from tui_chat.providers import MockProvider
from tui_chat.schemas import Message, Role


@pytest.mark.asyncio
async def test_mock_provider_streaming():
    provider = MockProvider(reply_template="Hello World Test")
    messages = [Message(role=Role.USER, content="Hi")]

    chunks = []
    async for chunk in provider.stream_chat(messages, model="test-model"):
        if chunk.delta:
            chunks.append(chunk.delta)

    result = "".join(chunks)
    assert result == "Hello World Test"

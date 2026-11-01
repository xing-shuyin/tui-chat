import asyncio
import tempfile
from pathlib import Path
import pytest
from textual.widgets import Button, Input

from tui_chat.app import ChatApp, MessageItem
from tui_chat.clipboard import ClipboardService, MemoryClipboardBackend
from tui_chat.config import AppConfig
from tui_chat.providers import MockProvider
from tui_chat.schemas import Message, Role, Session
from tui_chat.storage import SessionStore


@pytest.mark.asyncio
async def test_app_startup_and_new_chat():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        provider = MockProvider(reply_template="OK")
        clip = ClipboardService(backend=MemoryClipboardBackend())

        app = ChatApp(app_config=app_cfg, provider=provider, store=store, clipboard=clip)

        async with app.run_test() as pilot:
            assert app.current_session is not None
            app.action_new_chat()
            assert len(store.list_sessions()) >= 1


@pytest.mark.asyncio
async def test_app_message_flow_and_copy_actions():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        code_reply = "Here is the code:\n```python\ndef solve():\n    return 42\n```\nDone."
        provider = MockProvider(reply_template=code_reply)
        clip = ClipboardService(backend=MemoryClipboardBackend())

        app = ChatApp(app_config=app_cfg, provider=provider, store=store, clipboard=clip)

        async with app.run_test() as pilot:
            input_box = app.query_one("#chat-input", Input)
            input_box.value = "Hello assistant"
            await app.handle_user_submit()
            await pilot.pause(0.2)

            # Wait for mock streaming to finish
            for _ in range(20):
                if not app._is_generating:
                    break
                await pilot.pause(0.05)

            assert len(app.current_session.messages) == 2
            assert app.current_session.messages[1].role == Role.ASSISTANT

            # Test copying latest code block via action
            app.action_copy_last_code()
            assert clip.paste() == "def solve():\n    return 42"

            # Test copying latest message via action
            app.action_copy_last_message()
            assert code_reply in clip.paste()


@pytest.mark.asyncio
async def test_app_paste_clipboard_action():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        clip = ClipboardService(backend=MemoryClipboardBackend())
        clip.copy("Pasted query from clipboard")

        app = ChatApp(app_config=app_cfg, store=store, clipboard=clip)

        async with app.run_test() as pilot:
            app.action_paste_clipboard()
            input_box = app.query_one("#chat-input", Input)
            assert input_box.value == "Pasted query from clipboard"


@pytest.mark.asyncio
async def test_message_item_button_clicks():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        clip = ClipboardService(backend=MemoryClipboardBackend())

        app = ChatApp(app_config=app_cfg, store=store, clipboard=clip)

        async with app.run_test() as pilot:
            msg = Message(
                role=Role.ASSISTANT,
                content="Sample text with ```bash\nls -la\n``` code block.",
            )
            item = MessageItem(msg)
            scroll = app.query_one("#messages-scroll")
            await scroll.mount(item)
            await pilot.pause(0.05)

            # Click copy message button
            copy_msg_btn = item.query_one(".copy-msg-btn", Button)
            copy_msg_btn.press()
            await pilot.pause(0.05)
            assert clip.paste() == msg.content

            # Click copy code button
            copy_code_btn = item.query_one(".copy-code-btn", Button)
            copy_code_btn.press()
            await pilot.pause(0.05)
            assert clip.paste() == "ls -la"


@pytest.mark.asyncio
async def test_empty_clipboard_actions():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        clip = ClipboardService(backend=MemoryClipboardBackend())

        app = ChatApp(app_config=app_cfg, store=store, clipboard=clip)

        async with app.run_test() as pilot:
            # Clear messages
            app.current_session.messages.clear()
            # Calling actions should not raise exceptions
            app.action_copy_last_message()
            app.action_copy_last_code()
            app.action_paste_clipboard()

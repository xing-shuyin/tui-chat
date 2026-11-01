import tempfile
from pathlib import Path
import pytest
from tui_chat.app import ChatApp
from tui_chat.config import AppConfig
from tui_chat.providers import MockProvider
from tui_chat.storage import SessionStore
from tui_chat.schemas import Session


@pytest.mark.asyncio
async def test_app_startup_and_new_chat():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        app_cfg = AppConfig(storage_dir=tmp_path)
        store = SessionStore(tmp_path)
        provider = MockProvider(reply_template="OK")

        app = ChatApp(app_config=app_cfg, provider=provider, store=store)

        async with app.run_test() as pilot:
            # Check app mounted properly
            assert app.current_session is not None
            # Press new chat button or trigger action
            app.action_new_chat()
            assert len(store.list_sessions()) >= 1

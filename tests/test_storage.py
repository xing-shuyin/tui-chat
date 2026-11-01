import tempfile
from pathlib import Path
from tui_chat.storage import SessionStore
from tui_chat.schemas import Session, Role


def test_session_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))
        session = Session(title="测试对话", model="gpt-4o")
        session.add_message(Role.USER, "你好")
        session.add_message(Role.ASSISTANT, "你好！有什么我可以帮你的？")

        # Save
        store.save_session(session)

        # Load
        loaded = store.load_session(session.id)
        assert loaded is not None
        assert loaded.title == "测试对话"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "你好"
        assert loaded.messages[1].role == Role.ASSISTANT

        # List
        all_sessions = store.list_sessions()
        assert len(all_sessions) == 1
        assert all_sessions[0].id == session.id

        # Delete
        assert store.delete_session(session.id) is True
        assert store.load_session(session.id) is None
        assert len(store.list_sessions()) == 0

from __future__ import annotations

import asyncio
from typing import Optional
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from tui_chat.clipboard import (
    ClipboardService,
    clipboard_service as default_clipboard_service,
    extract_code_blocks,
    get_last_code_block,
)
from tui_chat.config import AppConfig, config
from tui_chat.keymap import get_chat_bindings, get_terminal_environment
from tui_chat.providers import BaseProvider, MockProvider, OpenAIProvider
from tui_chat.schemas import Message, Role, Session
from tui_chat.storage import SessionStore


class MessageItem(Static):
    """Widget displaying a single chat message with copy toolbar."""

    def __init__(self, message: Message, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        if self.message.role == Role.USER:
            yield Static(f"[bold cyan]You[/bold cyan]:\n{self.message.content}", classes="user-msg")
            with Horizontal(classes="msg-toolbar"):
                btn = Button("📋 复制", classes="copy-btn copy-msg-btn")
                btn.can_focus = False
                yield btn
        else:
            model_info = f" ({self.message.model})" if self.message.model else ""
            yield Static(f"[bold magenta]Assistant{model_info}[/bold magenta]:", classes="assistant-header")
            yield Static(Markdown(self.message.content), classes="assistant-msg")

            code_blocks = extract_code_blocks(self.message.content)
            with Horizontal(classes="msg-toolbar"):
                msg_btn = Button("📋 复制文本", classes="copy-btn copy-msg-btn")
                msg_btn.can_focus = False
                yield msg_btn

                for idx, (lang, code) in enumerate(code_blocks):
                    lang_label = f" ({lang})" if lang else ""
                    code_btn = Button(f"💻 代码 {idx+1}{lang_label}", classes="copy-btn copy-code-btn")
                    code_btn.can_focus = False
                    code_btn._code_content = code
                    code_btn._code_lang = lang
                    yield code_btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if "copy-msg-btn" in event.button.classes:
            event.stop()
            self.app.copy_to_system_clipboard(self.message.content)
            self.notify("消息内容已复制到系统剪贴板", title="系统剪贴板")
        elif "copy-code-btn" in event.button.classes:
            event.stop()
            code = getattr(event.button, "_code_content", "")
            lang = getattr(event.button, "_code_lang", "")
            if code:
                self.app.copy_to_system_clipboard(code)
                title = f"代码块 [{lang}]" if lang else "代码块"
                self.notify(f"{title} 已复制到系统剪贴板", title="系统剪贴板")


class StreamingMessageItem(Static):
    """Widget displaying a live streaming assistant response."""

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.content = ""
        self._text_widget = Static("", classes="assistant-msg")

    def compose(self) -> ComposeResult:
        yield Static(f"[bold magenta]Assistant ({self.model})[/bold magenta] [italic yellow]生成中...[/italic yellow]:", classes="assistant-header")
        yield self._text_widget

    def append_chunk(self, chunk: str) -> None:
        self.content += chunk
        self._text_widget.update(Markdown(self.content))


class SessionListItem(ListItem):
    """Sidebar item representing a chat session."""

    def __init__(self, session: Session, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session

    def compose(self) -> ComposeResult:
        yield Label(f"💬 {self.session.title}", classes="session-label")


class ChatApp(App):
    """Main Textual Chat Application with cross-platform and macOS terminal adaptations."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #sidebar {
        width: 32;
        dock: left;
        background: $panel;
        border-right: vkey $primary;
        padding: 1;
    }

    #sidebar.hidden {
        display: none;
    }

    #new-chat-btn {
        width: 100%;
        margin-bottom: 1;
    }

    #session-list {
        height: 1fr;
        background: $panel;
    }

    #chat-area {
        width: 1fr;
        height: 100%;
        padding: 0 1;
    }

    #messages-scroll {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #input-container {
        height: auto;
        dock: bottom;
        padding: 1 0;
    }

    #chat-input {
        width: 1fr;
    }

    #send-btn {
        width: 12;
        margin-left: 1;
    }

    .user-msg {
        background: $primary-darken-3;
        color: $text;
        padding: 1;
        margin-top: 1;
        margin-bottom: 0;
        border-left: wide cyan;
    }

    .assistant-header {
        margin-top: 1;
    }

    .assistant-msg {
        background: $surface-darken-1;
        padding: 1;
        margin-bottom: 0;
        border-left: wide magenta;
    }

    .msg-toolbar {
        height: auto;
        margin-top: 0;
        margin-bottom: 1;
        align-horizontal: right;
    }

    .copy-btn {
        height: 1;
        min-width: 8;
        border: none;
        padding: 0 1;
        margin-left: 1;
        background: $panel-lighten-1;
        color: $text-muted;
    }

    .copy-btn:hover {
        background: $accent;
        color: $text;
    }

    .copy-code-btn {
        background: $success-darken-3;
    }

    .copy-code-btn:hover {
        background: $success;
        color: $text;
    }
    """

    BINDINGS = get_chat_bindings()

    sidebar_visible = reactive(True)

    def __init__(
        self,
        app_config: Optional[AppConfig] = None,
        provider: Optional[BaseProvider] = None,
        store: Optional[SessionStore] = None,
        clipboard: Optional[ClipboardService] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.app_config = app_config or config
        self.app_config.ensure_directories()
        self.store = store or SessionStore(self.app_config.storage_dir)
        self.clipboard_service = clipboard or default_clipboard_service

        if provider is not None:
            self.provider = provider
        elif self.app_config.api_key:
            self.provider = OpenAIProvider(
                api_key=self.app_config.api_key,
                base_url=self.app_config.base_url,
            )
        else:
            self.provider = MockProvider()

        self.current_session: Optional[Session] = None
        self._is_generating = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield Button("+ 新建对话", id="new-chat-btn", variant="primary")
                yield ListView(id="session-list")
            with Vertical(id="chat-area"):
                yield VerticalScroll(id="messages-scroll")
                with Horizontal(id="input-container"):
                    yield Input(placeholder="输入消息，按 Enter 发送...", id="chat-input")
                    yield Button("发送", id="send-btn", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        term_info = get_terminal_environment()
        term_name = term_info["name"]
        term_desc = f" ({term_name})" if term_name != "Standard Terminal" else ""
        self.title = f"TUI-Chat{term_desc}"
        self.sub_title = (
            f"Model: {self.app_config.default_model} | "
            f"Provider: {self.provider.__class__.__name__} | "
            f"Clipboard: {self.clipboard_service.backend_name}"
        )
        self.refresh_session_list()
        # Create or load first session
        sessions = self.store.list_sessions()
        if sessions:
            self.switch_to_session(sessions[0])
        else:
            self.action_new_chat()

    def copy_to_system_clipboard(self, text: str) -> bool:
        """Copy text to both Textual's internal clipboard and OS system clipboard."""
        self.copy_to_clipboard(text)
        return self.clipboard_service.copy(text)

    def action_copy_last_message(self) -> None:
        """Copy the content of the most recent message to the system clipboard."""
        if not self.current_session or not self.current_session.messages:
            self.notify("当前会话没有可复制的消息", title="剪贴板", severity="warning")
            return

        target_msg = None
        for msg in reversed(self.current_session.messages):
            if msg.role == Role.ASSISTANT:
                target_msg = msg
                break
        if not target_msg:
            target_msg = self.current_session.messages[-1]

        self.copy_to_system_clipboard(target_msg.content)
        role_label = "回答" if target_msg.role == Role.ASSISTANT else "消息"
        self.notify(f"最新{role_label}已复制到系统剪贴板", title="系统剪贴板")

    def action_copy_last_code(self) -> None:
        """Copy the most recent Markdown code block to the system clipboard."""
        if not self.current_session or not self.current_session.messages:
            self.notify("当前会话没有消息", title="剪贴板", severity="warning")
            return

        for msg in reversed(self.current_session.messages):
            last_block = get_last_code_block(msg.content)
            if last_block:
                lang, code = last_block
                self.copy_to_system_clipboard(code)
                lang_desc = f" [{lang}]" if lang else ""
                self.notify(f"最新代码块{lang_desc}已复制到系统剪贴板", title="系统剪贴板")
                return

        self.notify("当前会话中未检测到 Markdown 代码块", title="剪贴板", severity="warning")

    def action_paste_clipboard(self) -> None:
        """Paste text from system clipboard into the chat input."""
        text = self.clipboard_service.paste()
        if not text:
            self.notify("系统剪贴板为空", title="剪贴板", severity="warning")
            return

        input_widget = self.query_one("#chat-input", Input)
        input_widget.insert_text_at_cursor(text)
        input_widget.focus()
        self.notify("已从系统剪贴板粘贴文本", title="系统剪贴板")

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        if "hidden" in sidebar.classes:
            sidebar.remove_class("hidden")
        else:
            sidebar.add_class("hidden")

    def refresh_session_list(self) -> None:
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        sessions = self.store.list_sessions()
        for s in sessions:
            session_list.append(SessionListItem(s))

    def switch_to_session(self, session: Session) -> None:
        self.current_session = session
        scroll = self.query_one("#messages-scroll", VerticalScroll)
        scroll.remove_children()

        for msg in session.messages:
            scroll.mount(MessageItem(msg))

        scroll.scroll_end(animate=False)

    def action_new_chat(self) -> None:
        new_session = Session(
            title=f"对话 {len(self.store.list_sessions()) + 1}",
            model=self.app_config.default_model,
        )
        self.store.save_session(new_session)
        self.refresh_session_list()
        self.switch_to_session(new_session)
        self.query_one("#chat-input", Input).focus()

    def action_delete_current_session(self) -> None:
        if not self.current_session:
            return
        self.store.delete_session(self.current_session.id)
        sessions = self.store.list_sessions()
        self.refresh_session_list()
        if sessions:
            self.switch_to_session(sessions[0])
        else:
            self.action_new_chat()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-chat-btn":
            self.action_new_chat()
        elif event.button.id == "send-btn":
            await self.handle_user_submit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            await self.handle_user_submit()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, SessionListItem):
            self.switch_to_session(event.item.session)

    async def handle_user_submit(self) -> None:
        if self._is_generating:
            return

        input_widget = self.query_one("#chat-input", Input)
        text = input_widget.value.strip()
        if not text:
            return

        input_widget.value = ""
        if not self.current_session:
            self.action_new_chat()

        assert self.current_session is not None
        user_msg = self.current_session.add_message(Role.USER, text)
        if len(self.current_session.messages) == 1:
            self.current_session.title = text[:15] + ("..." if len(text) > 15 else "")
            self.refresh_session_list()

        self.store.save_session(self.current_session)

        scroll = self.query_one("#messages-scroll", VerticalScroll)
        scroll.mount(MessageItem(user_msg))
        scroll.scroll_end(animate=True)

        asyncio.create_task(self.generate_response())

    async def generate_response(self) -> None:
        if not self.current_session:
            return
        self._is_generating = True
        scroll = self.query_one("#messages-scroll", VerticalScroll)
        stream_item = StreamingMessageItem(self.current_session.model)
        await scroll.mount(stream_item)
        scroll.scroll_end(animate=True)

        full_content = ""
        try:
            async for chunk in self.provider.stream_chat(
                messages=self.current_session.messages,
                model=self.current_session.model,
                system_prompt=self.app_config.system_prompt,
            ):
                if chunk.delta:
                    full_content += chunk.delta
                    stream_item.append_chunk(chunk.delta)
                    scroll.scroll_end(animate=False)
        except Exception as e:
            full_content += f"\n\n[出错了: {e}]"
            stream_item.append_chunk(f"\n\n[出错了: {e}]")
        finally:
            self._is_generating = False
            assistant_msg = self.current_session.add_message(
                Role.ASSISTANT,
                full_content,
                model=self.current_session.model,
            )
            self.store.save_session(self.current_session)
            await stream_item.remove()
            await scroll.mount(MessageItem(assistant_msg))
            scroll.scroll_end(animate=True)


def main() -> None:
    app = ChatApp()
    app.run()


if __name__ == "__main__":
    main()

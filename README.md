# TUI-Chat

现代、异步、轻量级终端对话交互工具（Terminal User Interface Chat），基于 Python 3.12+、`uv`、[Textual](https://github.com/Textualize/textual) 与 [Rich](https://github.com/Textualize/rich) 构建。

设计理念跳出传统命令行脚本“修补表象、头痛医头”的粗放模式，从事件驱动与响应式 UI 视角彻底解决流式大文本输出渲染卡顿、控制台闪烁及跨平台按键差异等核心痛点。

---

## ✨ 核心特性

- ⚡ **异步响应式渲染**：采用 Textual 响应式框架，模型流式 SSE 数据与 UI 差量刷新解耦，彻底杜绝闪烁与丢帧。
- 💬 **会话全生命周期管理**：支持多会话快速切换、自动会话命名、新建对话与会话安全持久化（原子文件写入防止异常崩溃损坏）。
- 🎨 **现代化 Rich 排版**：支持多角色气泡、语法高亮代码块、Markdown 实时渲染与状态反馈。
- 🔌 **统一 Provider 架构**：无缝对接 OpenAI、DeepSeek、Ollama、vLLM 等兼容接口，内置无需 API Key 的离线 Mock 测试环境。
- 🖥️ **跨平台原生支持**：统一按键映射与 ANSI 渲染，完美支持 Windows Terminal、macOS Terminal / iTerm2 以及 Linux 终端。

---

## ⌨️ 快捷键指南

| 快捷键 (Windows / Linux) | 快捷键 (macOS Terminal / iTerm2) | 功能说明 |
| :--- | :--- | :--- |
| `Ctrl + N` | `^N` / `⌥N` | 新建对话（New Chat） |
| `Ctrl + B` | `^B` / `⌥B` | 折叠 / 展开侧边栏会话列表 |
| `Ctrl + D` | `^D` / `⌥D` | 删除当前选中会话 |
| `Ctrl + Y` | `^Y` / `⌥C` | 复制最新回答到系统剪贴板 |
| `Ctrl + K` | `^K` / `⌥K` | 复制最新代码块到系统剪贴板 |
| `Ctrl + V` | `^V` / `⌥V` | 从系统原生剪贴板粘贴到输入框 |
| `Ctrl + Q` | `^Q` | 退出程序 |
| `Enter` | `Enter` | 发送输入框消息 |

> 💡 **剪贴板交互增强**：每个消息卡片均内置紧凑操作栏，可直接点击「📋 复制文本」或「💻 复制代码」将内容同步至系统原生剪贴板（macOS 原生 Pasteboard、Linux Wayland/X11 或 Windows）。

---

## 🚀 快速上手

### 1. 依赖安装与启动（推荐使用 `uv`）

```bash
# 克隆仓库
git clone https://github.com/xing-shuyin/tui-chat.git
cd tui-chat

# 使用 uv 一键运行（自动准备虚拟环境与依赖）
uv run tui-chat
```

### 2. 配置自定义模型（可选）

通过环境变量配置 OpenAI 或 DeepSeek / 本地 Ollama 接口：

```bash
# 示例：配置 DeepSeek / OpenAI
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-chat"

# 启动
uv run tui-chat
```

若未配置 `OPENAI_API_KEY`，程序将自动进入内置 Mock 体验模式，方便在无网络/无密钥环境下快速体验与测试 TUI 交互。

---

## 🧪 自动化测试

项目内置完整的单元测试与 Textual 异步 UI 测试：

```bash
uv run pytest
```

---

## 🏗️ 架构概览

```
src/tui_chat/
├── __init__.py       # 包入口及主程序暴露
├── app.py            # Textual TUI 应用主体（布局、事件响应、流式挂载）
├── clipboard.py      # 系统原生剪贴板服务（macOS pbcopy/paste、Linux、Windows及代码块提取）
├── config.py         # 全局配置管理（环境变量与存储目录）
├── keymap.py         # 终端输入层与跨平台快捷键映射（macOS iTerm2/Terminal适配）
├── providers.py      # 模型 Provider 抽象（OpenAI-compatible、Mock）
├── schemas.py        # Pydantic 核心数据模型（Message, Session, Role）
└── storage.py        # 会话持久化引擎（原子替换防损坏）
```

---

## 📄 开源许可

[MIT License](LICENSE)

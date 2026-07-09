"""Agent Runtime — backward-compat wrappers.

All execution now flows through MotherRuntime (runtime/kernel.py).
This file retains:
  - StandardMessage dataclass (used by gateway modules)
  - agent_run() wrapper → MotherRuntime.run()
  - _build_context + AGENT_PROMPT (temporary compat)

MotherAgent and get_mother() have been REMOVED.
Use runtime.get_runtime() instead.
"""

import json, os, re
from app.llm import LLMClient
from app.memory import MemoryRepo
from app.tools import execute as exec_tool, bump_usage, list_tools
from app.models import Message, Session as SessionModel
from sqlalchemy.orm import Session as DBSession

AGENT_PROMPT = """你是"母体-小梦"，由孟白创造的 AI 助手，通过 QQ 和用户聊天。

你是聊天机器人，不是工具执行器。直接回应用户提问，只在以下情况才用工具:
- 用户明确要求执行操作（打开App、执行命令、查设备状态等）
- 需要查文件内容

严禁为自我介绍、问候、闲聊、感谢等日常对话使用任何工具。你是谁、你的名字、你有什么功能等问题直接从系统提示回答，不要搜记忆。

始终用中文回复。短小精炼，三句话以内。

工具格式: <tool>名称</tool><content>参数</content>
每轮最多一个工具。收到工具结果后必须直接回复，禁止继续调用工具。

工具速查:
- search_memory: 搜索记忆库 <tool>search_memory</tool><content>关键词</content>
- read_file: 读取文件 <tool>read_file</tool><content>路径</content>
- run_command: 执行命令 <tool>run_command</tool><content>命令</content>
- device_status: 查设备 <tool>device_status</tool><content>设备调试码</content>
- toggle_wifi: 开关WiFi <tool>toggle_wifi</tool><content>设备调试码 true/false</content>
- open_app: 打开App <tool>open_app</tool><content>设备调试码 包名</content>
- take_screenshot: 截图 <tool>take_screenshot</tool><content>/tmp/s.png</content>

规则:
- QQ纯文本，禁用Markdown、表格、代码块
- 短句分行，三行以内

可用工具完整列表:
{tools_list}

你有上面全部工具。被问工具数量时回答54。"""



TOOL_RE = re.compile(r'<tool>(.*?)</tool>\s*<content>(.*?)</content>', re.DOTALL)
THINK_RE = re.compile(r'<thinking>(.*?)</thinking>', re.DOTALL)



from dataclasses import dataclass, field
from typing import Optional

@dataclass
class StandardMessage:
    """跨渠道统一消息"""
    role: str = 'user'
    content: str = ''
    channel: str = 'unknown'
    user_id: str = ''
    user_name: str = ''
    session_id: str = ''
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

def _build_context(db: DBSession, session_id: int, user_msg: str) -> str:
    """Assemble context: memory hits + recent messages + tools."""
    parts = []

    # Memory
    hits = MemoryRepo(db).query(user_msg, top_n=3)
    if hits:
        parts.append("## 相关记忆")
        for h in hits:
            parts.append(f"- [#{h.session_id}] {h.summary[:200]}")
            if h.keywords:
                parts.append(f"  关键词: {', '.join(h.keywords[:5])}")
        parts.append("")

    # Recent messages
    recent = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(10).all()
    if recent:
        parts.append("## 对话历史")
        for m in reversed(recent):
            role = "用户" if m.role == "user" else "助手" if m.role == "assistant" else m.role
            parts.append(f"[{role}]: {m.content[:300]}")
        parts.append("")

    return "\n".join(parts)


def agent_run(db: DBSession, session_id: int, user_message: str, llm: LLMClient, max_turns: int = 5) -> dict:
    """Backward-compat wrapper → MotherRuntime.run().

    All execution now delegates to the single Runtime Kernel.
    This wrapper preserves the original return format for api.py compatibility.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    if session.status == "closed":
        raise ValueError("Session is closed")

    # Record user message (preserve original behavior)
    db.add(Message(session_id=session_id, role="user", content=user_message))
    db.commit()

    # Delegate to MotherRuntime
    from app.runtime import get_runtime
    result = get_runtime().run(message=user_message, session_id=session_id,
                               max_turns=max_turns, llm_client=llm)

    # Record assistant message
    db.add(Message(session_id=session_id, role="assistant", content=result.output))
    db.commit()

    return {
        "session_id": session_id,
        "response": result.output,
        "tools_used": result.metadata.get("tool_calls", []),
        "turns": result.metadata.get("turns", 0),
        "thinking": result.metadata.get("thinking", []),
        "messages_added": 2,
    }



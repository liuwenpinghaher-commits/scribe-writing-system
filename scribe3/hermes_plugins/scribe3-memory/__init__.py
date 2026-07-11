"""scribe3-memory · 可选 Hermes MemoryProvider 适配层(统一上下文与记忆系统 Task 12)。

它是什么(以及不是什么):
  · 让【直接用 Hermes 会话】(如 `hermes -p scribe3 chat`,非 Scribe Web)也能读写 Scribe 记忆。
  · Scribe Web 的写作/主编对话【主路不依赖它】——主路走 app 内 ContextAssembler /
    MemoryRetriever / MemoryCapture 直调。本 provider 是边缘增强,优先级最低,可选启用。

工作方式(全部经 Scribe 的 /memory/* REST,不直连 DB):
  · prefetch  → POST /memory/prefetch   取组装好的记忆块文本注入 prompt;
  · sync_turn → POST /memory/capture-turn 幂等捕获一轮对话(**后台 daemon 线程,非阻塞**);
  · on_pre_compress / on_session_end → POST /memory/flush 固化线程工作摘要。

硬红线:
  · work-scoped —— work 从稳定 session key `scribe3|work:{work}|thread:{thread_id}` 解出,
    每个请求都带 work;服务端按 per-work db 隔离 + work 绑定校验(跨 work→409)。绝不串书。
  · 非阻塞 —— sync_turn 用 daemon 线程后台捕获,主调用立即返回,绝不等网络。
  · 只读工具 —— get_tool_schemas 只暴露只读检索/溯源;显式"记住偏好"走 Scribe 待批 API,
    不在 provider 内直写设定/事实。

依赖:仅 Python 标准库(插件运行在 Hermes 进程内,不共享 Scribe venv)。
启用:见同目录 README.md 与 scribe3/scripts/install_hermes_scribe3_memory.sh(默认不自动启用)。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from threading import Thread

__all__ = ["Scribe3MemoryProvider", "ScribeMemoryApi", "parse_scribe_session_id",
           "MemoryProvider"]


# ---------------------------------------------------------------------------
# MemoryProvider 基类:优先 import Hermes SDK,缺失则本地 duck-typed 兜底。
# vendor 已删、Hermes 装在 ~/.hermes,本仓测试进程不一定能 import hermes——
# provider 是【鸭子类型适配层】,不强制继承,实现同名方法即可被 Hermes 装载。
# ---------------------------------------------------------------------------
def _resolve_memory_provider_base():
    for module_name, attr in (
        ("hermes.memory", "MemoryProvider"),
        ("hermes.providers", "MemoryProvider"),
        ("hermes.plugins", "MemoryProvider"),
        ("hermes_agent.memory", "MemoryProvider"),
    ):
        try:
            module = __import__(module_name, fromlist=[attr])
            base = getattr(module, attr, None)
            if isinstance(base, type):
                return base
        except Exception:
            continue

    class _DuckMemoryProvider:
        """Hermes SDK 不可 import 时的 duck-typed 基类占位(定义生命周期契约签名)。"""

        name = "memory-provider"

        def is_available(self) -> bool:  # noqa: D401
            return False

        def initialize(self, session_id: str, **kwargs) -> None:
            ...

        def prefetch(self, query: str, *, session_id: str = "") -> str:
            return ""

        def sync_turn(self, user: str, assistant: str, *, session_id: str = "",
                      messages=None) -> None:
            ...

        def on_pre_compress(self, messages) -> None:
            ...

        def on_session_end(self, messages) -> None:
            ...

        def get_tool_schemas(self):
            return []

    return _DuckMemoryProvider


MemoryProvider = _resolve_memory_provider_base()


# ---------------------------------------------------------------------------
# session key 反解:`scribe3|work:{work}|thread:{thread_id}` → (work, thread_id)
# 正向格式的唯一源在 scribe3.hermes_runtime.scribe3_session_key;此处是反向解析,
# 插件自带(保持插件对 Scribe 内部模块零 import 依赖,可独立随 Hermes 装载)。
# ---------------------------------------------------------------------------
def parse_scribe_session_id(session_id: str):
    """从稳定 session key 解 (work, thread_id)。畸形/缺省容错:work→'main'、thread→None,不抛。"""
    work, thread_id = "main", None
    if not session_id or not isinstance(session_id, str):
        return work, thread_id
    for part in session_id.split("|"):
        if part.startswith("work:"):
            work = part[len("work:"):] or "main"
        elif part.startswith("thread:"):
            thread_id = part[len("thread:"):] or None
    return work, thread_id


# ---------------------------------------------------------------------------
# 薄 HTTP 客户端:调 Scribe 的 /memory/* REST(work 恒进 query string)。
# 只用 urllib(标准库);失败向上抛,由 provider 的 best-effort 包裹层吞掉。
# ---------------------------------------------------------------------------
class ScribeMemoryApi:
    def __init__(self, base: str, *, timeout: float = 10.0):
        self.base = (base or "").rstrip("/")
        self.timeout = timeout

    def _url(self, path: str, work: str) -> str:
        return f"{self.base}{path}?work={urllib.parse.quote(work or 'main')}"

    def _post(self, url: str, body: dict) -> dict:
        data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def prefetch(self, *, work: str, thread_id, query: str) -> dict:
        return self._post(self._url("/memory/prefetch", work),
                          {"thread_id": thread_id, "query": query})

    def capture_turn(self, work: str, thread_id, payload: dict) -> dict:
        body = {"thread_id": thread_id, **(payload or {})}
        return self._post(self._url("/memory/capture-turn", work), body)

    def flush(self, work: str, thread_id, *, reason: str) -> dict:
        return self._post(self._url("/memory/flush", work),
                          {"thread_id": thread_id, "reason": reason})


# ---------------------------------------------------------------------------
# provider:最小且完整的 Hermes MemoryProvider 生命周期(计划 Task 12 Step 3)。
# ---------------------------------------------------------------------------
class Scribe3MemoryProvider(MemoryProvider):
    name = "scribe3-memory"

    def is_available(self) -> bool:
        """门控:仅当 SCRIBE3_API_BASE 指向可达的 Scribe 后端时才启用(边缘增强,默认不介入)。"""
        return bool(os.environ.get("SCRIBE3_API_BASE"))

    def initialize(self, session_id: str, **kwargs) -> None:
        self.api = ScribeMemoryApi(os.environ["SCRIBE3_API_BASE"])
        self.session_id = session_id
        self.work, self.thread_id = parse_scribe_session_id(session_id)
        self._sync_thread = None

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        work, thread_id = parse_scribe_session_id(session_id or self.session_id)
        try:
            result = self.api.prefetch(work=work, thread_id=thread_id, query=query) or {}
        except Exception:
            return ""   # 边缘增强:取记忆失败不该让直连会话崩,降级空块
        return result.get("context", "") or ""

    def sync_turn(self, user: str, assistant: str, *, session_id: str = "",
                  messages=None) -> None:
        """幂等捕获本轮对话——**非阻塞**:daemon 后台线程捕获,主调用立即返回,绝不等网络。"""
        work, thread_id = (parse_scribe_session_id(session_id) if session_id
                           else (self.work, self.thread_id))
        payload = {"event_id": uuid.uuid4().hex, "user": user,
                   "assistant": assistant, "messages": messages or []}
        self._sync_thread = Thread(
            target=self._safe_capture, args=(work, thread_id, payload), daemon=True)
        self._sync_thread.start()

    def _safe_capture(self, work, thread_id, payload) -> None:
        try:
            self.api.capture_turn(work, thread_id, payload)
        except Exception:
            pass   # 后台 best-effort:捕获失败绝不冒泡进 Hermes 会话

    def on_pre_compress(self, messages) -> None:
        self._safe_flush(reason="pre_compress")

    def on_session_end(self, messages) -> None:
        self._safe_flush(reason="session_end")

    def _safe_flush(self, *, reason: str) -> None:
        try:
            self.api.flush(self.work, self.thread_id, reason=reason)
        except Exception:
            pass   # 固化失败不阻断压缩/会话结束

    def get_tool_schemas(self):
        """Step 4:只读工具白名单。写入(记住偏好/改设定)走 Scribe pending-approval,
        不在 provider 内直写库——直连会话仍受 Scribe 的待批闸约束。"""
        return [
            {"name": "scribe_memory_search",
             "description": "在当前作品(work)内检索经验记忆与正典命题(只读)。",
             "parameters": {"type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"]}},
            {"name": "scribe_memory_trace",
             "description": "查某条记忆为什么被选中/被弃(溯源,只读)。",
             "parameters": {"type": "object",
                            "properties": {"revision": {"type": "integer"}}}},
            {"name": "scribe_context_current",
             "description": "读当前主编上下文快照(work/focus/证据/记忆,只读)。",
             "parameters": {"type": "object", "properties": {}}},
        ]

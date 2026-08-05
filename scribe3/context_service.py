"""统一上下文与记忆系统 · Task 4:Context API 校验服务层。

职责:把 Task 3 store 的上下文原语(create/advance/get)包成 API 语义——
work 绑定校验、快照过期(revision+hash)判定、chat 绑定强制(开关门控)。
只 import context_models(合同层),不 import app/llm,保持无环。

错误合同(app.py 据 code 映射 HTTP 状态):
- ContextBindingRequired  → 400(开关开而 chat 请求缺绑定字段)
- ContextSessionNotFound  → 404
- ContextSnapshotNotFound → 404(session 在、指定 revision 不在)
- ContextSessionEnded     → 409
- ContextWorkMismatch     → 409(请求 work 与 session 落库 work 不符,
                                Task 16 的 work 绑定校验语义前置)
- StaleContextError       → 409(来自 context_models,带 expected/actual/latest)
"""
from __future__ import annotations

from pydantic import ValidationError

from scribe3.context_models import ContextSnapshot, StaleContextError

# 开关:每次调用时读 env(而非 import 时固化),便于测试 monkeypatch 与运行时灰度
FLAG_ENV = "SCRIBE3_CONTEXT_SNAPSHOT_V1"

# I-1:与 body 三件套等价的请求头绑定通道(api.js contextHeaders 产出;
# Starlette headers 大小写不敏感,此处按规范用全小写键读)
HEADER_SESSION = "x-scribe-context-session"
HEADER_REVISION = "x-scribe-context-revision"
HEADER_HASH = "x-scribe-context-hash"


def context_snapshot_flag_enabled() -> bool:
    """SCRIBE3_CONTEXT_SNAPSHOT_V1 是否开启。

    产品默认**开**(见 settings.REGISTRY);显式 env/DB=0 可关(测试/运维隔离)。
    统一走 context_cache.flag_enabled(设置中心 DB 覆盖→env→默认,热生效),
    消除与 capabilities 上报的双路径分裂。延迟 import 防环。
    """
    from scribe3.context_cache import flag_enabled
    return flag_enabled(FLAG_ENV)


class ContextServiceError(Exception):
    """服务层错误基类:code 是 API 透传的稳定错误码(detail.code)。"""
    code = "context_error"


class ContextBindingRequired(ContextServiceError):
    code = "context_binding_required"


class ContextSessionNotFound(ContextServiceError):
    code = "context_session_not_found"


class ContextSnapshotNotFound(ContextServiceError):
    code = "context_snapshot_not_found"


class ContextSessionEnded(ContextServiceError):
    code = "context_session_ended"


class ContextWorkMismatch(ContextServiceError):
    code = "context_work_mismatch"

    def __init__(self, session_id: str, expected: str, actual: str):
        self.session_id = session_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"context_session '{session_id}' 属于 work '{actual}',请求 work '{expected}' 不符")


class ContextService:
    """上下文会话的 API 校验门面(每请求轻量构造,store 由调用方按 work 取)。"""

    def __init__(self, store):
        self.store = store

    # ---- 内部:store dict → 模型(store 返回含模型外字段 reason,先过滤) ----

    @staticmethod
    def _to_snapshot(raw: dict) -> ContextSnapshot:
        data = {k: v for k, v in raw.items() if k in ContextSnapshot.model_fields}
        return ContextSnapshot.model_validate(data)

    @staticmethod
    def _check_work(raw: dict, work: str, session_id: str) -> None:
        """work 绑定校验以 session 落库的 work 为准(?work= 只用于定位 store)。"""
        actual = raw.get("work")
        if actual != work:
            raise ContextWorkMismatch(session_id, expected=work, actual=actual)

    # ---- 读路径 ----

    def get(self, session_id: str, work: str, revision: int | None = None) -> dict:
        """读当前/指定 revision 快照(dict,含 reason);不存在→404 语义异常。"""
        raw = self.store.get_context_snapshot(session_id, revision=revision)
        if raw is None:
            if revision is not None \
                    and self.store.get_context_snapshot(session_id) is not None:
                raise ContextSnapshotNotFound(
                    f"context_session '{session_id}' 无 revision={revision} 的快照")
            raise ContextSessionNotFound(f"context_session '{session_id}' 不存在")
        self._check_work(raw, work, session_id)
        return raw

    # ---- 写路径 ----

    def navigate(self, session_id: str, work: str, intent: dict) -> dict:
        """CAS 推进:store.advance_context 的 API 包装。
        StaleContextError 原样上抛(app 映射 409);store 的 ValueError
        按文案分流为 not-found / ended 语义异常。"""
        current = self.store.get_context_snapshot(session_id)
        if current is None:
            raise ContextSessionNotFound(f"context_session '{session_id}' 不存在")
        self._check_work(current, work, session_id)
        try:
            return self.store.advance_context(session_id, intent)
        except StaleContextError:
            raise
        except ValidationError:
            # I-3:pydantic ValidationError 是 ValueError 的子类——不先拦截会掉进
            # 下面的分支被误映射成 404"会话不存在"。原样上抛:API 路径由 FastAPI
            # 在端点层已 422 拦截(到不了这里);Task 13 等直调 service 的调用方
            # 也能看到真实的载荷校验错误而非假 not-found。
            raise
        except ValueError as e:
            if "已结束" in str(e):
                raise ContextSessionEnded(str(e)) from e
            raise ContextSessionNotFound(str(e)) from e

    # ---- chat 绑定校验 ----

    def require_current(self, session_id: str, revision: int,
                        context_hash: str, work: str) -> ContextSnapshot:
        """校验 (session, revision, hash) 是否为当前快照:
        work 不符 → ContextWorkMismatch;revision 或 hash 失配 → StaleContextError
        (latest 带服务端最新快照,前端可直接对齐免再读)。"""
        raw = self.store.get_context_snapshot(session_id)
        if raw is None:
            raise ContextSessionNotFound(f"context_session '{session_id}' 不存在")
        snapshot = self._to_snapshot(raw)
        if snapshot.work != work:
            raise ContextWorkMismatch(session_id, expected=work, actual=snapshot.work)
        if snapshot.revision != revision or snapshot.context_hash != context_hash:
            # I-2:latest 用 store 的 raw dict(含 reason、captured_at 为库内 ISO 串)
            # ——与 navigate 路径(store.advance_context 内部同样取 raw)同源同形,
            # 前端对齐逻辑不必分辨"哪条 409 来的 latest"。
            raise StaleContextError(expected=revision, actual=snapshot.revision,
                                    latest=raw)
        return snapshot

    def enforce(self, req, work: str, headers=None) -> ContextSnapshot | None:
        """chat 请求的绑定强制(开关门控)。req 鸭子类型:只读
        context_session_id / context_revision / context_hash 三个属性。

        - 开关关(须显式 env/DB=0):完全不碰这些字段,返回 None;
        - 产品默认开:chat 写路径强制 context 绑定三件套;
        - 开关开:三件套按字段取 body,缺失时回退请求头(I-1 双通道,
          headers 为 Starlette Headers 或 dict,键大小写不敏感/全小写);
          两通道都缺任一件 → ContextBindingRequired(400);
          否则走 require_current(404/409 语义见各异常)。
        thread_id 不参与过期判定(线程归属由 Task 6 的线程表接管)。"""
        if not context_snapshot_flag_enabled():
            return None
        headers = headers if headers is not None else {}
        session_id = getattr(req, "context_session_id", None) \
            or headers.get(HEADER_SESSION)
        context_hash = getattr(req, "context_hash", None) or headers.get(HEADER_HASH)
        revision = getattr(req, "context_revision", None)
        if revision is None:
            raw_rev = headers.get(HEADER_REVISION)
            try:
                # 非法数字(None/空串/非整数)一律视为"该件缺失"→ 走 400,
                # 而不是 500——header 通道没有 pydantic 兜底,得自己收口
                revision = int(raw_rev) if raw_rev not in (None, "") else None
            except (TypeError, ValueError):
                revision = None
        if session_id is None or revision is None or context_hash is None:
            raise ContextBindingRequired(
                "SCRIBE3_CONTEXT_SNAPSHOT_V1 开启:chat 请求必须携带 context 绑定三件套"
                "(body 字段 context_session_id/context_revision/context_hash,"
                "或等价请求头 X-Scribe-Context-Session/Revision/Hash)")
        return self.require_current(session_id, revision, context_hash, work)

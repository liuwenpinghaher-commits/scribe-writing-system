"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['settings_gateway'])


# Import app_impl constants/models used as signature defaults (late-safe for 

def _request_is_admin(request: Request | None = None) -> bool:
    """True if current request user is admin; auth disabled → treat as admin for local dev."""
    try:
        from scribe3.settings import get_setting
        auth_on = bool(get_setting("SCRIBE3_AUTH_ENABLED"))
    except Exception:
        auth_on = False
    if not auth_on:
        return True  # 未开鉴权：本地/测试全权限(与现网单用户一致)
    try:
        from scribe3.auth.admin_routes import resolve_username
        from scribe3.auth.users import is_admin
        # resolve_username may need request
    except Exception:
        pass
    try:
        from scribe3.auth.context import current_user_id
        from scribe3.auth.users import is_admin
        uid = current_user_id.get()
        return bool(uid and is_admin(uid))
    except Exception:
        return False


def _require_admin_api() -> None:
    # Call via module attribute so rebind to app_impl still works if both are bound
    try:
        from scribe3.api import app_impl as _core
        _check = getattr(_core, '_request_is_admin', None)
    except Exception:
        _check = None
    if _check is None:
        _check = globals().get('_request_is_admin')
    if _check is None or not _check():
        from fastapi import HTTPException
        raise HTTPException(403, "admin role required")

def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def ai_runtime_status():
    return _hermes_runtime_status()

def capabilities():
    """能力下发:只读各运行时 flag(不下发任何秘密)。

    前端以后端 capabilities 为准——不允许只靠 localStorage 开启未就绪的服务端能力。
    产品默认:snapshot / memory_fabric / context_inspector = 开;editorial_thread 仍默认关;
    assembler_v1 恒 True(统一写作内核);emergency_rest_write 默认关。
    capabilities 只上报运行时事实。"""
    from scribe3 import context_cache, embed
    try:
        from scribe3.ingest_policy import policy_mode
        _ingest_policy = policy_mode()
    except Exception:
        _ingest_policy = "auto_if_pass"
    return {
        "flags": {
            "snapshot_v1": _flag_enabled("SCRIBE3_CONTEXT_SNAPSHOT_V1"),
            "editorial_thread_v1": _flag_enabled("SCRIBE3_EDITORIAL_THREAD_V1"),
            "memory_fabric_v1": _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"),
            "context_inspector_v1": _flag_enabled("SCRIBE3_CONTEXT_INSPECTOR_V1"),
            # 兼容旧前端字段名；Creative Context Engine 已是唯一生产写作内核。
            "assembler_v1": True,
            # 紧急 REST 世界写后门(默认关;测试/运维显式开)。
            "emergency_rest_write": _flag_enabled("SCRIBE3_EMERGENCY_REST_WRITE"),
            # 章节流水线闭环(PR-1/2)
            "ingest_lease": True,
            "ingest_policy": True,
            "mcp_craft_gate": True,
        },
        "ingest_policy_default": _ingest_policy,
        "versions": {
            "retrieval_policy": context_cache.RETRIEVAL_POLICY_VERSION,
            "embedding_model": embed.model_version(),
        },
    }

def settings_all():
    """全量设置:值(secret 掩码)+来源+默认+元数据+pending_restart+audience。只读。"""
    from scribe3 import settings as S
    admin = _request_is_admin()
    return {"settings": S.settings_snapshot_for(is_admin_user=admin),
            "categories": ["connection", "llm", "craft", "flags", "gateway"],
            "is_admin": admin}

def settings_audit(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    # 双侧夹紧在校验层:SQLite 里 LIMIT -1 = 不限量(全表),负数必须 422 而非透传
    from scribe3 import settings_store
    return {"rows": settings_store.audit_rows(limit=limit, offset=offset)}

def settings_put(key: str, req: SettingPutReq):
    from scribe3 import settings as S
    try:
        S.assert_setting_writable(key, is_admin_user=_request_is_admin())
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    except PermissionError as e:
        raise HTTPException(403, str(e))
    try:
        return S.put_setting(key, req.value)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))

def settings_reset(key: str):
    from scribe3 import settings as S
    try:
        S.assert_setting_writable(key, is_admin_user=_request_is_admin())
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    except PermissionError as e:
        raise HTTPException(403, str(e))
    try:
        S.reset_setting(key)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    return {"key": key, "status": "reset"}

def gateway_status():
    """已登记 Hermes 网关探活(GET {base}/models,1.5s 超时)。只读,不落库。

    online=端口有 HTTP 响应(<500),不代表鉴权/服务正常。
    """
    import httpx
    from scribe3.settings import get_setting
    targets = [
        ("default", get_setting("HERMES_API"), "(default)"),
        ("responses", get_setting("HERMES_RESPONSES_API"), get_setting("HERMES_RESPONSES_PROFILE")),
        ("runs", get_setting("HERMES_RUNS_API"), get_setting("HERMES_RUNS_PROFILE")),
        ("deduce", get_setting("HERMES_DEDUCE_RUNS_API"), "scribe3_deduce"),
        ("deduce_preview", get_setting("HERMES_DEDUCE_PREVIEW_RUNS_API"), "scribe3_deduce_preview"),
    ]
    out = []
    for name, base, profile in targets:
        online = False
        try:
            online = httpx.get(f"{base.rstrip('/')}/models", timeout=1.5).status_code < 500
        except Exception:
            pass
        out.append({"name": name, "api": base, "profile": profile, "online": online})
    return {"gateways": out}

def gateway_files_list():
    """白名单内 Hermes profile 文件;author 仅元数据, content 仅 admin。"""
    from scribe3 import gateway_files as gf
    files = gf.list_files()
    if not _request_is_admin():
        slim = []
        for f in files or []:
            row = {k: f.get(k) for k in ("id", "exists", "path", "error") if k in f or True}
            row = {"id": f.get("id"), "exists": f.get("exists"), "path": f.get("path"),
                   "error": f.get("error"), "content": None, "content_hidden": True}
            slim.append(row)
        return {"files": slim, "content_hidden": True}
    return {"files": files, "content_hidden": False}

def gateway_files_put(req: GatewayFilePutReq):
    _require_admin_api()
    from scribe3 import gateway_files as gf
    try:
        return gf.write_file(req.id, req.content, base_sha256=req.base_sha256)
    except gf.NotAllowedError as e:
        raise HTTPException(403, str(e))
    except gf.StaleFileError as e:
        raise HTTPException(409, str(e))

def gateway_restart(req: GatewayRestartReq):
    """重启指定 profile 的 Hermes 网关并确认重启动作本身成功。

    Hermes 在 macOS 下通常由 launchd 托管。对此再执行 ``gateway run --replace`` 会被
    拒绝，但旧进程仍在线，若只轮询端口便会产生“已重启”的假成功。因此必须调用官方
    ``gateway restart`` 子命令，并将其退出状态与后续探活分别返回。
    """
    _require_admin_api()
    import subprocess
    import time
    import httpx
    from scribe3.settings import get_setting
    apis = {"scribe3": get_setting("HERMES_RESPONSES_API"),
            "scribe3_write": get_setting("HERMES_RUNS_API"),
            "scribe3_deduce": get_setting("HERMES_DEDUCE_RUNS_API"),
            "scribe3_deduce_preview": get_setting("HERMES_DEDUCE_PREVIEW_RUNS_API")}
    if req.profile not in apis:
        raise HTTPException(422, "未知 profile: " + req.profile +
                            "(仅支持 scribe3/scribe3_write/scribe3_deduce/scribe3_deduce_preview)")
    hermes = os.path.expanduser(get_setting("gateway.hermes_bin"))
    log = f"/tmp/scribe3-hermes-{req.profile}.log"
    if not (os.path.isfile(hermes) and os.access(hermes, os.X_OK)):
        # 预检:注定失败的场景毫秒级如实报错,不空等 30s 轮询、不拉起进程。
        return {"profile": req.profile, "online": False, "log": log,
                "message": f"hermes CLI 不存在或不可执行: {hermes}"}
    try:
        restart_result = subprocess.run(
            [hermes, "-p", req.profile, "gateway", "restart"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"profile": req.profile, "online": False, "restarted": False, "log": log,
                "message": f"重启命令未成功执行:{exc}"}
    if getattr(restart_result, "returncode", 0) != 0:
        return {"profile": req.profile, "online": False, "restarted": False, "log": log,
                "message": "Hermes 重启命令失败,未将旧进程在线误报为已重启"}
    base = apis[req.profile].rstrip("/")
    online = False
    for _ in range(30):   # 轮询至多 ~30s
        time.sleep(1)
        try:
            if httpx.get(f"{base}/models", timeout=1.5).status_code < 500:
                online = True
                break
        except Exception:
            continue
    return {"profile": req.profile, "online": online, "restarted": True, "log": log,
            "message": "已重启" if online else "重启命令成功，但 30s 内未探活成功,请查看日志"}

def dashboard_status():
    """Hermes 官方 Dashboard 探活(GET {url},1.5s 超时)。online=有 HTTP 响应(<500)。"""
    import httpx
    from scribe3.settings import get_setting
    url = get_setting("gateway.dashboard_url")
    online = False
    try:
        online = httpx.get(url, timeout=1.5).status_code < 500
    except Exception:
        pass
    return {"online": online, "url": url}

def dashboard_start():
    _require_admin_api()
    """一键拉起本机 Hermes 官方 Dashboard。铁律同 /gateway/restart:nohup 后台 +
    轮询探活,绝不前台阻塞;轮询超时如实报失败,不假成功。无请求参数,无注入面。

    「启动」= 幂等的"确保运行"(区别于 restart 的"总是重建"):已在线直接短路返回,
    不 Popen、不写日志。"""
    import subprocess
    import time
    import httpx
    from scribe3.settings import get_setting
    hermes = os.path.expanduser(get_setting("gateway.hermes_bin"))
    url = get_setting("gateway.dashboard_url")
    log = "/tmp/scribe3-hermes-dashboard.log"
    try:
        if httpx.get(url, timeout=1.5).status_code < 500:
            return {"online": True, "url": url, "log": log, "message": "管理台已在运行"}
    except Exception:
        pass   # 探活失败 = 未运行,继续走启动流程
    if not (os.path.isfile(hermes) and os.access(hermes, os.X_OK)):
        # 预检:注定失败的场景毫秒级如实报错,不空等 30s 轮询、不拉起进程。
        return {"online": False, "url": url, "log": log,
                "message": f"hermes CLI 不存在或不可执行: {hermes}"}
    cmd = f"nohup {hermes} dashboard --no-open >> {log} 2>&1 &"
    subprocess.Popen(cmd, shell=True)
    online = False
    for _ in range(30):   # 轮询至多 ~30s
        time.sleep(1)
        try:
            if httpx.get(url, timeout=1.5).status_code < 500:
                online = True
                break
        except Exception:
            continue
    return {"online": online, "url": url, "log": log,
            "message": "已启动" if online else "启动后 30s 内未探活成功,请查看日志"}

def gateway_model_summary():
    """全部写作阶段网关的主模型只读摘要。只读,不登记台账。
    绝不解析/返回 api_key 或 base_url。"""
    from scribe3 import gateway_files as gf
    return {"gateways": gf.model_summary()}

def ai_usage(work: str = "main", days: int = 7):
    """H-10 全系统预算面板:日帽(跨进程共享台账)+ token 真实用量(trace 聚合)。

    - cap:计"发起的 LLM 调用笔数"。scope=shared 表示 app 与 MCP 进程同记一本
      SQLite 台账(SCRIBE3_LLM_LEDGER);=process 表示台账故障已回退进程内计数。
    - tokens:Hermes 各响应体回传的真实 usage,按天聚合(Responses/Runs 分列)。
      fail-soft:聚合挂了回空列表带 error,帽信息照常返回。
    - provider_usage:Qwen 官方服务直连逻辑调用的独立聚合；不与 tokens 相加，
      未配置价格时显式返回 cost_amount=null/pricing_status=not_configured。
    """
    from scribe3 import usage as usage_mod
    from scribe3 import llm as llm_mod
    from scribe3 import settings as settings_mod

    model = settings_mod.get_public_setting("llm.model")
    identity = llm_mod.official_qwen_provider_identity(model)
    key_present = settings_mod.is_explicitly_configured("DEEPSEEK_API_KEY")
    # 严格 allowlist：不返回 identity/设置对象本身，更不读取 key 内容。
    provider = {
        "provider": identity["provider"],
        "api_base": identity["api_base"],
        "model": identity["model"],
        "official": identity["official"],
        # identity 里的 httpx 是实现细节；此 API 稳定暴露产品路由语义。
        "transport": "direct",
        "key_present": key_present,
    }
    cap_value = settings_mod.get_public_setting("SCRIBE3_DAILY_CALL_CAP")
    used, scope = usage_mod.used_today()
    unlimited = cap_value == 0
    remaining = None if unlimited else max(0, cap_value - used)
    try:
        tokens = _store_for(work).usage_summary(days=days)
    except Exception:
        tokens = {"days": [], "error": "usage_summary_unavailable"}
    try:
        provider_usage = usage_mod.provider_usage_summary(days=days)
    except Exception:
        provider_usage = {
            "days": [],
            "cost_amount": None,
            "pricing_status": "not_configured",
            "error": "provider_usage_unavailable",
        }
    return {
        "work": work,
        "cap": {"cap": cap_value, "used_today": used,
                "remaining": remaining, "unlimited": unlimited,
                "scope": scope},
        "tokens": tokens,
        "provider_usage": provider_usage,
        "provider": provider,
    }

def ai_run_create(req: AIRunCreateReq, work: str = "main"):
    """创建 Hermes Run。用于需要人类审批/可恢复事件流的 agentic 长任务。"""
    from scribe3.run_stage_policy import (
        explicit_book_tool_contract,
        native_tool_call_guidance,
        native_stage_tool_guidance,
        resolve_run_stage_policy,
        tool_contract_snapshot,
    )

    try:
        policy = resolve_run_stage_policy(req.run_scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # 章节阶段已有静态 required_tools；书级 Run 仅在作者明确点名 s3_* 调用时
    # 生成合同，避免把一般性工具提及误判成必须写入。
    tool_contract = None if policy is not None else explicit_book_tool_contract(
        req.input, req.instructions,
    )
    ins = (req.instructions or "").strip()
    ins = (ins + _s3_work_scope_block(work)) if ins else _s3_work_scope_block(work).lstrip()
    if policy is not None and policy.required_tools:
        ins = f"{ins}\n{native_stage_tool_guidance(policy)}"
    elif tool_contract is not None:
        ins = f"{ins}\n{native_tool_call_guidance(tool_contract)}"
    session_key = _run_session_key(work, req.run_scope or "runs")
    runtime = _hermes_runs_runtime(policy) if policy is not None else _hermes_runs_runtime()
    result = runtime.create_run(
        req.input,
        instructions=ins,
        session_id=req.session_id,
        conversation_history=req.conversation_history,
        previous_response_id=req.previous_response_id,
        session_key=session_key,
    )
    run_id = result.get("run_id") or result.get("id")
    _record_ai_run_trace(
        work,
        run_id,
        status=result.get("status") or "created",
        session_key=session_key,
        input_text=req.input,
        instructions=ins,
        response=result,
    )
    if policy is not None:
        _store_for(work).update_ai_run_context(
            run_id,
            stage_policy={
                "phase": policy.phase,
                "profile": policy.profile,
                "allowed_tools": sorted(policy.allowed_tools),
                "max_tool_calls": policy.max_tool_calls,
                "required_tools": sorted(policy.required_tools),
            },
        )
    if tool_contract is not None:
        _store_for(work).update_ai_run_context(
            run_id,
            tool_contract=tool_contract_snapshot(tool_contract),
        )
    # Task 13:把 run 链回作品级主编线程,并快照"发起时的上下文"(session/revision/hash/focus)。
    # best-effort:绑定失败只告警,绝不阻断 run 创建(与 trace 留痕同纪律)。
    _bind_run_origin_context(work, run_id, req)
    # Run 创建是服务端持有生命周期的起点，而不是浏览器 SSE 的前置条件。若作者在
    # POST 成功后、建立 events 流前刷新或断线，collector 仍须消费并落库完整审计尾部。
    if run_id:
        _ensure_ai_run_event_collector(work, run_id)
    return result

def ai_run_pending_approvals(chapter: int | None = None, phase: str | None = None,
                             work: str = "main", limit: int = 100):
    """恢复当前作品范围内待审批 Run。

    章节阶段传完整 ``chapter + phase``；作品级主编 Run 不传二者。两者只传其一
    必须拒绝，避免刷新时把其它 scope 的审批卡错误贴到当前作者界面。
    """
    normalized_phase = (phase or "").strip().lower()
    has_chapter_scope = chapter is not None or bool(normalized_phase)
    if has_chapter_scope:
        if chapter is None or chapter < 1 or not normalized_phase:
            raise HTTPException(status_code=422, detail="chapter 与 phase 必须同时有效")
        expected_session_key = _run_session_key(work, f"chapter:{chapter}:{normalized_phase}")
    else:
        expected_session_key = _run_session_key(work)
    runs = []
    for trace in _store_for(work).list_ai_run_traces(limit=limit):
        if trace.get("session_key") != expected_session_key:
            continue
        if has_chapter_scope and (trace.get("stage_policy") or {}).get("phase") != normalized_phase:
            continue
        pending = _pending_approval_from_trace(trace)
        if pending:
            runs.append(pending)
    return {"runs": runs}

def ai_run_status(run_id: str, work: str = "main"):
    runtime, session_key, _policy, _tool_contract, trace = _runtime_for_traced_run(work, run_id)
    local_status = str(trace.get("status") or "").lower()
    try:
        result = runtime.run_status(run_id, session_key=session_key)
    except httpx.HTTPStatusError as exc:
        # Hermes 会在 Run 完成后回收远端记录；此时状态轮询也可能得到 404。
        # 本地 trace 已是终态时，持久化审计才是作者可见的权威，不能把回收竞态放大为 500。
        response_status = exc.response.status_code if exc.response is not None else None
        if response_status == 404 and local_status in _AI_RUN_TERMINAL_STATUSES:
            stored_response = trace.get("response")
            result = dict(stored_response) if isinstance(stored_response, dict) else {}
            result.setdefault("run_id", run_id)
            result["status"] = local_status
        else:
            raise
    remote_status = str(result.get("status") or result.get("state") or "").lower()
    # collector 已持久化终态后，任何远端状态轮询都不能改写本地审计裁决：不仅
    # waiting/resumed 会重开已完成 Run，remote completed 也不能掩盖 required_tool_missing
    # 或 completed_unverified。状态端点不是新的审计证据，作者必须看到 collector 的结论。
    if local_status in _AI_RUN_TERMINAL_STATUSES:
        response = dict(result)
        response["status"] = local_status
        _record_ai_run_trace(work, run_id, status=local_status, response=result)
        return response
    # 状态端点不是审计事件端点。若 Hermes 已清理事件历史，直接把远端
    # completed 写成 local completed 会让没有 tool.completed/run.completed 证据的
    # Run 假绿；保留为可继续订阅/回收的中间状态，交由 collector 最终定性。
    if remote_status == "completed" and local_status not in {
        "completed", "completed_unverified",
    }:
        status = "remote_completed_pending_audit"
    else:
        status = remote_status or trace.get("status") or "started"
    _record_ai_run_trace(work, run_id, status=status, response=result)
    return result

def ai_run_trace(run_id: str, work: str = "main"):
    store = _store_for(work)
    trace = store.get_ai_run_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="ai_run_trace not found")
    # Task 16-A 纵深(spec 审):对齐其他 surface 的 work 绑定。ai_run_trace.work 存的是
    # 物理库名(db_name)——生产 db-per-work 下 _store_for(work)→db=work,恒成立故为 tautology
    # (跨 work 早在 get_ai_run_trace 读不到→404);仅在 store 与请求同库时校验,测试注入
    # (set_store 使 db_name≠work)下跳过避免误报。真正的逻辑-work 绑定待 Task 13 把逻辑 work
    # 落进 ai_run_trace(现存 db_name)后随多 work 并库一并加固。
    if store.db_name == work:
        _assert_work_binding(trace.get("work"), work,
                             kind="ai_run_trace", ident=run_id)
    return trace

def ai_run_events(run_id: str, work: str = "main"):
    _runtime_for_traced_run(work, run_id)  # 校验 trace/profile 绑定后才允许订阅。
    key = _ai_run_collector_key(work, run_id)
    subscriber: Queue = Queue(maxsize=256)
    # collector 可能在浏览器建立 SSE 前已经把 approval.requested 写入审计链；
    # 订阅者必须先从这份权威 trace 回放待审批卡，否则作者刚发起 Run 就会因时序
    # 看不到批准入口，只能依赖刷新恢复。
    pending = _pending_approval_from_trace(_store_for(work).get_ai_run_trace(run_id) or {})
    with _ai_run_collector_lock:
        _ai_run_event_subscribers.setdefault(key, []).append(subscriber)
    if pending:
        subscriber.put_nowait({
            "event": {"kind": "approval.requested", **pending},
            "policy_violations": [],
        })
    _ensure_ai_run_event_collector(work, run_id)

    def gen():
        try:
            while True:
                try:
                    payload = subscriber.get(timeout=25)
                except Empty:
                    trace = _store_for(work).get_ai_run_trace(run_id) or {}
                    if trace.get("status") in _AI_RUN_TERMINAL_STATUSES:
                        yield 'data: {"done": true}\n\n'
                        return
                    continue
                app_ev = payload.get("event") or {}
                policy_violations = payload.get("policy_violations") or []
                kind = app_ev.get("kind")
                if kind == "text.delta":
                    yield f"data: {json.dumps({'delta': app_ev.get('delta', '')}, ensure_ascii=False)}\n\n"
                elif kind == "tool.started":
                    yield f"data: {json.dumps({'tool': app_ev.get('name', ''), 'tool_args': app_ev.get('arguments', '')}, ensure_ascii=False)}\n\n"
                elif kind == "tool.output":
                    yield f"data: {json.dumps({'tool_output': app_ev.get('output', ''), 'tool_call_id': app_ev.get('call_id')}, ensure_ascii=False)}\n\n"
                elif kind == "approval.requested":
                    yield f"data: {json.dumps({'approval': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'message')}}, ensure_ascii=False)}\n\n"
                    # 同一 Run 可以串行出现多张审批卡。collector 是 Hermes 流的唯一消费者，
                    # 浏览器只是订阅者，必须持续接收 approval.resolved/下一张卡/最终终态。
                elif kind == "approval.resolved":
                    yield f"data: {json.dumps({'approval_resolved': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'decision')}}, ensure_ascii=False)}\n\n"
                elif kind == "run.completed":
                    if policy_violations:
                        yield f"data: {json.dumps({'error': '阶段工具策略校验失败', 'policy_violations': policy_violations}, ensure_ascii=False)}\n\n"
                        return
                    yield f"data: {json.dumps({'run': {'run_id': app_ev.get('run_id'), 'status': 'completed', 'usage': app_ev.get('usage')}}, ensure_ascii=False)}\n\n"
                elif kind == "run.failed":
                    yield f"data: {json.dumps({'error': app_ev.get('error') or 'run failed'}, ensure_ascii=False)}\n\n"
                elif kind == "run.reconciliation_required":
                    yield f"data: {json.dumps({'error': app_ev.get('error') or 'Run 需要审计复核'}, ensure_ascii=False)}\n\n"
                elif kind == "run.done":
                    yield 'data: {"done": true}\n\n'
                    return
                else:
                    yield f"data: {json.dumps({'raw': app_ev}, ensure_ascii=False)}\n\n"
        except Exception as e:
            _record_ai_run_trace(work, run_id, status="failed", error=str(e)[:160])
            yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        finally:
            with _ai_run_collector_lock:
                subscribers = _ai_run_event_subscribers.get(key) or []
                if subscriber in subscribers:
                    subscribers.remove(subscriber)
                if not subscribers:
                    _ai_run_event_subscribers.pop(key, None)

    from scribe3.api.sse import sse_response
    return sse_response(gen())

@_serialize_ai_run_approval
def ai_run_approval(run_id: str, req: AIRunApprovalReq, work: str = "main"):
    payload = req.model_dump(exclude_none=True)
    choice = _hermes_approval_choice(req)
    # Task 13:写入前重校验发起时上下文快照(限知写入安全闸)。校验通过后原 approve 流程一字不改;
    # RunContextChanged(409)在此前抛出,绝不进 Hermes approve——旧 run 的过期写入被物理拦下。
    store = _store_for(work)
    runtime, session_key, policy, _tool_contract, trace = _runtime_for_traced_run(work, run_id)
    # 同一决定的刷新重放在首个请求完整落库后不再触碰 Hermes。这个检查必须在
    # 上述同 Run 串行锁内，才能覆盖两个浏览器同时点击时首个请求尚未写 trace 的窗口。
    if _already_resolved_approval(trace, payload.get("approval_id"), choice):
        return {
            "run_id": run_id,
            "status": trace.get("status") or "approval_submitted",
            "already_resolved": True,
        }
    completion_rev = _recheck_run_origin_context(store, run_id, trace, req, choice)
    # Hermes 0.18.2 的 Runs approval 由 URL 中的 run_id 绑定活跃审批，只要求
    # choice；live MCP elicitation 事件可以没有 approval_id。仅在上游真实给出
    # approval_id 时透传，禁止发送 null 冒充必填字段。
    hermes_payload = {"choice": choice}
    if payload.get("approval_id"):
        hermes_payload["approval_id"] = payload["approval_id"]
    # 刷新恢复的审批卡可能没有活着的浏览器 SSE；先确保服务端唯一 collector
    # 已经在 Hermes 事件流上等待，随后才允许 author approval 触发写工具继续执行。
    _ensure_ai_run_event_collector(work, run_id)
    try:
        result = runtime.approve_run(
            run_id,
            hermes_payload,
            session_key=session_key,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        # 刷新恢复、浏览器重试会重放同一个 author decision。Hermes 已消费它时返回
        # approval_not_pending；只有本地审计链已证明同 approval_id、同决定已决时，
        # 该请求才是幂等成功，不能误记 approval_failed 或向 UI 伪报 502。
        if "approval_not_pending" in detail and _already_resolved_approval(
            trace, payload.get("approval_id"), choice,
        ):
            return {
                "run_id": run_id,
                "status": trace.get("status") or "approval_submitted",
                "already_resolved": True,
            }
        if "approval_not_active" in detail or "approval_not_pending" in detail:
            message = "审批已过期，请重新发起写入请求"
            _record_ai_run_trace(
                work, run_id, status="approval_expired",
                error=f"approval_expired: {detail}",
            )
            raise HTTPException(
                status_code=409,
                detail={"code": "approval_expired", "message": message},
            ) from exc
        _record_ai_run_trace(work, run_id, status="approval_failed", error=detail)
        raise HTTPException(status_code=502, detail=f"Hermes approval failed: {detail}") from exc
    _record_ai_run_event(work, run_id, {
        "kind": "approval.resolved",
        "run_id": run_id,
        "approval_id": payload.get("approval_id"),
        "decision": payload.get("decision"),
        "choice": choice,
    }, source="user")
    # 审批 HTTP 仅确认“作者的决定已交给 Hermes”，并不代表 Run 的生命周期状态。
    # SSE 可能已经先写入 completed/failed；此处若把 Hermes 的 resumed/running
    # 覆盖回 trace，会让真实完成的 Run 永远停在 approval_submitted。
    _record_ai_run_trace(work, run_id, response=result)
    # Task 13:记完成时上下文 revision + write_effects 台账(仅 approve 类且有 origin 绑定时)。
    # Minor:同一审批重放时按 (approval_id, revision, kind) 去重,不叠重复台账
    # (读改写非 CAS,能挡幂等重放;真并发双批准极罕见,同 approval_id 亦会命中去重)。
    if choice != "deny" and completion_rev is not None:
        try:
            effects = list(trace.get("write_effects") or [])
            new_effect = {
                "kind": "approval",
                "approval_id": payload.get("approval_id"),
                "choice": choice,
                "stale_confirmed": bool(req.approve_stale),
                "context_revision": completion_rev,
            }
            key = (new_effect["approval_id"], new_effect["context_revision"], new_effect["kind"])
            if not any((e.get("approval_id"), e.get("context_revision"), e.get("kind")) == key
                       for e in effects):
                effects.append(new_effect)
            store.update_ai_run_context(
                run_id,
                completion_context_revision=completion_rev,
                write_effects=effects,
            )
        except Exception:
            logging.getLogger("scribe3").warning("run completion context 记账失败(忽略)", exc_info=True)
    return result

def ai_run_stop(run_id: str, work: str = "main"):
    # 前端可能在 run.completed 已到达、组件随后卸载的极窄窗口再发 stop。
    # Hermes 此时已回收该 run 并返回 404；本地审计链已有终态时，停止应幂等成功，
    # 不能把正常清理路径放大为 Scribe 500。
    runtime, session_key, _policy, _tool_contract, trace = _runtime_for_traced_run(work, run_id)
    try:
        result = runtime.stop_run(run_id, session_key=session_key)
    except httpx.HTTPStatusError as exc:
        status = trace.get("status")
        response_status = exc.response.status_code if exc.response is not None else None
        # Hermes 对已回收的完成 Run 既可能回 404，也可能回
        # 400 {error:{code:"run_not_found"}}。后者不是作者的停止失败；只有本地
        # 审计链已是终态时才可幂等吞掉，避免把真实的活跃 Run 错误伪装成成功。
        remote_pruned = response_status == 404
        if response_status == 400 and exc.response is not None:
            try:
                payload = exc.response.json()
            except (TypeError, ValueError):
                payload = None
            remote_pruned = isinstance(payload, dict) and (
                (payload.get("error") or {}).get("code") == "run_not_found"
            )
        # remote_completed_pending_audit 不能加入全局 terminal 集合：collector 仍需补齐
        # 本地工具审计。但远端已明确完成且已被 Hermes 回收，对作者的 stop 操作必须
        # 与终态等价幂等，不能把正常的 stop/完成竞态报成 502。
        if remote_pruned and (
            status in _AI_RUN_TERMINAL_STATUSES
            or status == "remote_completed_pending_audit"
        ):
            return {"run_id": run_id, "status": status, "already_finished": True}
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        _record_ai_run_trace(work, run_id, status="stop_failed", error=detail)
        raise HTTPException(status_code=502, detail=f"Hermes stop failed: {detail}") from exc
    _record_ai_run_trace(work, run_id, status=result.get("status") or "stopped", response=result)
    return result



def craft_skills_list():
    """技法库索引(craft_skills.list_skills 薄封装)。"""
    from scribe3.craft_skills import list_skills
    return {"skills": list_skills()}


def craft_skills_read(slug: str):
    """技法全文。"""
    from scribe3.craft_skills import read_skill
    try:
        return {"slug": slug, "content": read_skill(slug)}
    except ValueError as e:
        raise HTTPException(404, str(e))


def mcp_catalog():
    """s3_* 工具能力地图(只读清单,非 /capabilities flags)。"""
    import re
    from pathlib import Path
    try:
        from scribe3.mcp._common import WRITE_GATED
    except Exception:
        WRITE_GATED = set()
    tools = []
    import scribe3 as _s3pkg
    mcp_dir = Path(_s3pkg.__file__).resolve().parent / "mcp"
    seen = set()
    for py in sorted(mcp_dir.glob("tools*.py")):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^def (s3_[a-z0-9_]+)\(", text, re.M):
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            # docstring first line
            rest = text[m.end():]
            doc = ""
            dm = re.match(r"\s*:\s*(?:\n\s*)?\"\"\"(.*?)\"\"\"", rest, re.S)
            if dm:
                doc = dm.group(1).strip().split("\n")[0][:160]
            try:
                gated = name in set(WRITE_GATED or [])
            except Exception:
                gated = False
            tools.append({
                "name": name,
                "write_gated": gated,
                "group": "write" if gated else "read",
                "doc": doc,
                "module": py.name,
            })
    return {"tools": tools, "count": len(tools)}


def data_health(work: str = "main"):
    """Surreal A: work-scoped 健康(非固定 main 的 /ready)。"""
    from scribe3.store import SurrealStore
    ok = False
    detail = ""
    try:
        st = SurrealStore(db=work or "main")
        # light touch
        try:
            st.list_volumes()
            ok = True
            detail = "list_volumes ok"
        except Exception as e1:
            try:
                ch = st.get_chapter(1)
                ok = True
                detail = f"get_chapter(1) reachable ({'hit' if ch else 'empty'})"
            except Exception as e2:
                detail = f"{e1}; {e2}"
    except Exception as e:
        detail = str(e)
    return {"work": work or "main", "ok": ok, "detail": detail}


def admin_data_tables(work: str = "main"):
    """Surreal B: admin 表白名单。"""
    _require_admin_api()
    # fixed product whitelist labels → not raw Surreal table dump
    tables = [
        {"id": "chapter", "label": "章节", "store": "get_chapter/list"},
        {"id": "volume", "label": "分卷", "store": "list_volumes"},
        {"id": "lesson", "label": "教训 lesson", "store": "list_lessons"},
        {"id": "craft_rule", "label": "工艺规则", "store": "list_craft_rules"},
        {"id": "entity", "label": "设定实体", "store": "characters/entities"},
    ]
    return {"work": work, "tables": tables}


def admin_data_rows(table: str, work: str = "main", limit: int = Query(50, ge=1, le=200)):
    """Surreal B: admin 白名单表只读预览。"""
    _require_admin_api()
    from scribe3.store import SurrealStore
    st = SurrealStore(db=work or "main")
    limit = min(int(limit or 50), 200)
    rows = []
    try:
        if table == "volume":
            rows = (st.list_volumes() or [])[:limit]
        elif table == "lesson":
            rows = (st.list_lessons() if hasattr(st, "list_lessons") else [])[:limit]
        elif table == "craft_rule":
            rows = (st.list_craft_rules() if hasattr(st, "list_craft_rules") else [])[:limit]
        elif table == "chapter":
            try:
                outline = st.outline() or {}
                rows = (outline.get("chapters") or [])[:limit]
            except Exception:
                for i in range(1, limit + 1):
                    ch = st.get_chapter(i)
                    if ch:
                        rows.append({k: ch.get(k) for k in ("seq", "title", "label", "volume", "synopsis") if k in ch or True})
                        rows[-1] = {"seq": ch.get("seq"), "title": ch.get("title"), "label": ch.get("label"),
                                    "volume": ch.get("volume"),
                                    "synopsis": ((ch.get("synopsis") or "")[:120])}
        elif table == "entity":
            try:
                rows = (st.characters() or [])[:limit]
                rows = [{"id": getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None),
                         "name": getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else str(c))}
                        for c in rows]
            except Exception as e:
                raise HTTPException(500, str(e))
        else:
            raise HTTPException(404, f"未在白名单: {table}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"读取失败: {e}")
    return {"work": work, "table": table, "rows": rows, "count": len(rows)}


def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working.

    RBAC helpers (_request_is_admin / _require_admin_api) MUST live on core.__dict__
    because FunctionType-rebound handlers resolve LOAD_GLOBAL from app_impl, not
    this module — otherwise settings_put/gateway_*/admin_data_* NameError at runtime.
    """
    from scribe3.api import app_impl as core
    g = globals()
    for _hname in ('_request_is_admin', '_require_admin_api'):
        _h = g[_hname]
        setattr(core, _hname, _h)
        core.__dict__[_hname] = _h
    _fn = g['ai_runtime_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_runtime_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_runtime_status', _re)
    g['ai_runtime_status'] = _re
    router.add_api_route('/ai/runtime-status', _re, methods=['GET'], name='ai_runtime_status')

    _fn = g['capabilities']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'capabilities', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'capabilities', _re)
    g['capabilities'] = _re
    router.add_api_route('/capabilities', _re, methods=['GET'], name='capabilities')

    _fn = g['settings_all']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'settings_all', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'settings_all', _re)
    g['settings_all'] = _re
    router.add_api_route('/settings', _re, methods=['GET'], name='settings_all')
    


    _fn = g['settings_audit']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'settings_audit', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'settings_audit', _re)
    g['settings_audit'] = _re
    router.add_api_route('/settings/audit', _re, methods=['GET'], name='settings_audit')

    _fn = g['settings_put']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'settings_put', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'settings_put', _re)
    g['settings_put'] = _re
    router.add_api_route('/settings/{key}', _re, methods=['PUT'], name='settings_put')

    _fn = g['settings_reset']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'settings_reset', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'settings_reset', _re)
    g['settings_reset'] = _re
    router.add_api_route('/settings/{key}/reset', _re, methods=['POST'], name='settings_reset')

    # System Hub: craft skills / mcp catalog / data plane
    for _path, _fn, _methods, _name in [
        ('/craft-skills', craft_skills_list, ['GET'], 'craft_skills_list'),
        ('/craft-skills/{slug}', craft_skills_read, ['GET'], 'craft_skills_read'),
        ('/mcp/catalog', mcp_catalog, ['GET'], 'mcp_catalog'),
        ('/data/health', data_health, ['GET'], 'data_health'),
        ('/admin/data/tables', admin_data_tables, ['GET'], 'admin_data_tables'),
        ('/admin/data/rows', admin_data_rows, ['GET'], 'admin_data_rows'),
    ]:
        _re = types.FunctionType(_fn.__code__, core.__dict__, _fn.__name__, _fn.__defaults__, _fn.__closure__)
        if getattr(_fn, '__kwdefaults__', None):
            _re.__kwdefaults__ = dict(_fn.__kwdefaults__)
        setattr(core, _fn.__name__, _re)
        g[_fn.__name__] = _re
        router.add_api_route(_path, _re, methods=_methods, name=_name)


    _fn = g['gateway_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'gateway_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'gateway_status', _re)
    g['gateway_status'] = _re
    router.add_api_route('/gateway/status', _re, methods=['GET'], name='gateway_status')

    _fn = g['gateway_files_list']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'gateway_files_list', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'gateway_files_list', _re)
    g['gateway_files_list'] = _re
    router.add_api_route('/gateway/files', _re, methods=['GET'], name='gateway_files_list')

    _fn = g['gateway_files_put']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'gateway_files_put', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'gateway_files_put', _re)
    g['gateway_files_put'] = _re
    router.add_api_route('/gateway/files', _re, methods=['PUT'], name='gateway_files_put')

    _fn = g['gateway_restart']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'gateway_restart', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'gateway_restart', _re)
    g['gateway_restart'] = _re
    router.add_api_route('/gateway/restart', _re, methods=['POST'], name='gateway_restart')

    _fn = g['dashboard_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'dashboard_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'dashboard_status', _re)
    g['dashboard_status'] = _re
    router.add_api_route('/gateway/dashboard/status', _re, methods=['GET'], name='dashboard_status')

    _fn = g['dashboard_start']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'dashboard_start', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'dashboard_start', _re)
    g['dashboard_start'] = _re
    router.add_api_route('/gateway/dashboard/start', _re, methods=['POST'], name='dashboard_start')

    _fn = g['gateway_model_summary']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'gateway_model_summary', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'gateway_model_summary', _re)
    g['gateway_model_summary'] = _re
    router.add_api_route('/gateway/model-summary', _re, methods=['GET'], name='gateway_model_summary')

    _fn = g['ai_usage']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_usage', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_usage', _re)
    g['ai_usage'] = _re
    router.add_api_route('/ai/usage', _re, methods=['GET'], name='ai_usage')

    _fn = g['ai_run_create']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_create', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_create', _re)
    g['ai_run_create'] = _re
    router.add_api_route('/ai/runs', _re, methods=['POST'], name='ai_run_create')

    _fn = g['ai_run_pending_approvals']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_pending_approvals', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_pending_approvals', _re)
    g['ai_run_pending_approvals'] = _re
    router.add_api_route('/ai/runs/pending-approvals', _re, methods=['GET'], name='ai_run_pending_approvals')

    _fn = g['ai_run_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_status', _re)
    g['ai_run_status'] = _re
    router.add_api_route('/ai/runs/{run_id}', _re, methods=['GET'], name='ai_run_status')

    _fn = g['ai_run_trace']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_trace', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_trace', _re)
    g['ai_run_trace'] = _re
    router.add_api_route('/ai/runs/{run_id}/trace', _re, methods=['GET'], name='ai_run_trace')

    _fn = g['ai_run_events']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_events', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_events', _re)
    g['ai_run_events'] = _re
    router.add_api_route('/ai/runs/{run_id}/events', _re, methods=['GET'], name='ai_run_events')

    _fn = g['ai_run_approval']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_approval', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_approval', _re)
    g['ai_run_approval'] = _re
    router.add_api_route('/ai/runs/{run_id}/approval', _re, methods=['POST'], name='ai_run_approval')

    _fn = g['ai_run_stop']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'ai_run_stop', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ai_run_stop', _re)
    g['ai_run_stop'] = _re
    router.add_api_route('/ai/runs/{run_id}/stop', _re, methods=['POST'], name='ai_run_stop')

_bind_and_register()

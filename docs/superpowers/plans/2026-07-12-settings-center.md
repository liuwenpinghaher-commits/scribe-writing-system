# 统一设置中心(Settings Center)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 scribe3 建统一设置中心:配置注册表 + SQLite 权威源 + 热生效,前端七分区设置视图,全套防护(掩码/默认恢复/审计/二次确认/备份)。

**Architecture:** 后端新增 `settings.py`(声明式注册表 + `get_setting()` 三级优先 DB→env→默认)与 `settings_store.py`(跨进程 SQLite,沿用 usage.py 范式);热生效项读点改走 `get_setting()`,restart 项启动期 `apply_restart_overrides()` 灌 env;REST 四端点 + 网关三端点;前端 `settings/` 目录元数据驱动渲染,入口为顶栏齿轮 → 横切视图 `viewKey:'settings'`。

**Tech Stack:** FastAPI + SurrealDB(业务)/SQLite(设置)、React + vitest、pytest。spec:`docs/superpowers/specs/2026-07-12-settings-center-design.md`。

**仓库纪律(每个任务都适用):**
- 后端测试:`scribe3/.venv/bin/python -m pytest scribe3/tests/<file> -q`(在仓根运行);前端:`cd scribe3/web && npx vitest run <file>`。
- 涉及 LLM 的测试必须 patch `scribe3.llm`,防烧真网关。
- 新写路由必须登记 `scribe3/tests/test_consistency.py` 的 `KNOWN_REST_WRITE_ROUTES`(不登记门禁红)。
- Hermes 起停必须 nohup 后台 + 轮询,绝不前台阻塞。
- 提交信息中文,尾行 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

---

## Phase 1:后端配置核心

### Task 1:SQLite 设置存储层 `settings_store.py`

**Files:**
- Create: `scribe3/settings_store.py`
- Test: `scribe3/tests/test_settings_store.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_settings_store.py
import json
from scribe3 import settings_store as ss


def test_override_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    assert ss.get_all_overrides() == {}
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(800), old_json=None)
    assert json.loads(ss.get_all_overrides()["SCRIBE3_DAILY_CALL_CAP"]) == 800
    ss.delete_override("SCRIBE3_DAILY_CALL_CAP", old_json=json.dumps(800))
    assert ss.get_all_overrides() == {}


def test_audit_rows_masked_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_API_TOKEN", json.dumps("tok-123"), old_json=None, mask=True)
    rows = ss.audit_rows(limit=10)
    assert rows[0]["key"] == "SCRIBE3_API_TOKEN"
    assert "tok-123" not in json.dumps(rows, ensure_ascii=False)  # 审计绝不落明文
    assert rows[0]["new"] == "«secret»"


def test_read_fail_soft(tmp_path, monkeypatch):
    # 路径指向不可写目录仍不抛:读回空 dict(fail-soft),写才抛
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", "/dev/null/nope/s.sqlite3")
    assert ss.get_all_overrides() == {}
```

- [ ] **Step 2: 跑测确认失败**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_store.py -q`
Expected: FAIL `ModuleNotFoundError: scribe3.settings_store`

- [ ] **Step 3: 实现**

```python
# scribe3/settings_store.py
"""设置中心的跨进程权威源:单文件 SQLite(沿用 usage.py 日帽台账范式)。

- 路径:env SCRIBE3_SETTINGS_DB,缺省 ~/.scribe2-surreal/scribe3_settings.sqlite3
  (与 SurrealDB 生产数据同目录,备份一起走)。
- 为什么不是 SurrealDB:DB 连接参数本身是设置项(自举悖论);且 app 与 MCP
  stdio 进程要共享同一份设置。
- fail-soft 边界:读故障回空(系统回落 env/默认值照常工作,告警一次);
  写故障原样抛(修改必须显式失败,不能假装成功)。
- value 一律 JSON 编码字符串;secret 项审计只记 «secret»,绝不落明文。
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path

_log = logging.getLogger("scribe3.settings_store")
_warned = False
_MASKED = "«secret»"


def db_path() -> Path:
    p = os.environ.get("SCRIBE3_SETTINGS_DB")
    if p:
        return Path(p).expanduser()
    return Path.home() / ".scribe2-surreal" / "scribe3_settings.sqlite3"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=2.0)
    conn.execute("CREATE TABLE IF NOT EXISTS setting ("
                 "key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS setting_audit ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
                 "key TEXT NOT NULL, old TEXT, new TEXT)")
    return conn


def _warn_once(e: Exception) -> None:
    global _warned
    if not _warned:
        _warned = True
        _log.warning("设置台账不可用,回落 env/默认值(fail-soft): %s", e)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def get_all_overrides() -> dict[str, str]:
    """全部覆盖值 {key: json_str}。读故障回空 dict(fail-soft)。"""
    try:
        with _connect() as c:
            return {k: v for k, v in c.execute("SELECT key, value FROM setting")}
    except Exception as e:
        _warn_once(e)
        return {}


def set_override(key: str, value_json: str, *, old_json: str | None, mask: bool = False) -> None:
    with _connect() as c:
        c.execute("INSERT INTO setting(key, value, updated_at) VALUES(?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                  (key, value_json, _now()))
        c.execute("INSERT INTO setting_audit(ts, key, old, new) VALUES(?,?,?,?)",
                  (_now(), key, _MASKED if (mask and old_json is not None) else old_json,
                   _MASKED if mask else value_json))


def delete_override(key: str, *, old_json: str | None, mask: bool = False) -> None:
    with _connect() as c:
        c.execute("DELETE FROM setting WHERE key=?", (key,))
        c.execute("INSERT INTO setting_audit(ts, key, old, new) VALUES(?,?,?,?)",
                  (_now(), key, _MASKED if (mask and old_json is not None) else old_json, None))


def audit_rows(limit: int = 50, offset: int = 0) -> list[dict]:
    try:
        with _connect() as c:
            rows = c.execute("SELECT ts, key, old, new FROM setting_audit "
                             "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            return [{"ts": t, "key": k, "old": o, "new": n} for t, k, o, n in rows]
    except Exception as e:
        _warn_once(e)
        return []
```

- [ ] **Step 4: 跑测确认通过**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_store.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit** `feat: 设置中心 SQLite 存储层(跨进程覆盖值+审计,fail-soft 读)`

### Task 2:配置注册表 + `get_setting()` `settings.py`

**Files:**
- Create: `scribe3/settings.py`
- Test: `scribe3/tests/test_settings.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_settings.py
import json
import pytest
from scribe3 import settings, settings_store


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    settings.invalidate_cache()
    yield
    settings.invalidate_cache()


def test_priority_default_env_db(monkeypatch):
    # 默认值
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 500
    # env 覆盖默认
    monkeypatch.setenv("SCRIBE3_DAILY_CALL_CAP", "600")
    settings.invalidate_cache()
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 600
    # DB 覆盖 env
    settings.put_setting("SCRIBE3_DAILY_CALL_CAP", 800)
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 800


def test_bool_flag_env_semantics(monkeypatch):
    # 与 context_cache._TRUE 口径逐字一致:'1'/'true'/'yes'/'on' 为真
    assert settings.get_setting("SCRIBE3_MEMORY_FABRIC_V1") is False
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "on")
    settings.invalidate_cache()
    assert settings.get_setting("SCRIBE3_MEMORY_FABRIC_V1") is True


def test_validation_rejects_out_of_range():
    with pytest.raises(ValueError):
        settings.put_setting("SCRIBE3_DAILY_CALL_CAP", -1)
    with pytest.raises(ValueError):
        settings.put_setting("craft.near_dup_sim", 2.0)   # max 1.0
    with pytest.raises(KeyError):
        settings.put_setting("no.such.key", 1)


def test_reset_falls_back():
    settings.put_setting("craft.near_dup_sim", 0.9)
    assert settings.get_setting("craft.near_dup_sim") == 0.9
    settings.reset_setting("craft.near_dup_sim")
    assert settings.get_setting("craft.near_dup_sim") == 0.7


def test_dotted_keys_ignore_env(monkeypatch):
    # 点分新键不受同名 env 影响(env 只对全大写既有键生效)
    monkeypatch.setenv("craft.near_dup_sim", "0.1")
    settings.invalidate_cache()
    assert settings.get_setting("craft.near_dup_sim") == 0.7


def test_snapshot_masks_secret():
    settings.put_setting("SCRIBE3_API_TOKEN", "tok-abc")
    snap = {s["key"]: s for s in settings.settings_snapshot()}
    item = snap["SCRIBE3_API_TOKEN"]
    assert item["value"] is None and item["is_set"] is True
    assert "tok-abc" not in json.dumps(snap, ensure_ascii=False)
    # 内部读取仍拿真值
    assert settings.get_setting("SCRIBE3_API_TOKEN") == "tok-abc"


def test_hot_write_invalidates_same_process():
    settings.put_setting("craft.banned_density_per_k", 5.0)
    assert settings.get_setting("craft.banned_density_per_k") == 5.0  # 无需等 TTL
```

- [ ] **Step 2: 跑测确认失败**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings.py -q`
Expected: FAIL `ModuleNotFoundError: scribe3.settings`

- [ ] **Step 3: 实现注册表与读写**

```python
# scribe3/settings.py
"""统一设置中心:声明式配置注册表 + 三级优先读取(DB 覆盖 → env → 代码默认)。

- 热生效(effect='hot'):读点每次调 get_setting();写入即失效进程内缓存,
  跨进程靠 2s TTL 自然收敛。
- 重启生效(effect='restart'):读点不改(仍读 env);进程启动最早期调
  apply_restart_overrides() 把 DB 覆盖灌进 os.environ,再走原读取路径。
- secret:DB 存真值(内部可用),settings_snapshot()/审计对外一律掩码。
- env 只对全大写既有键生效;点分新键(craft.* / llm.* / memory.*)只认 DB→默认。
- 门禁:tests/test_settings_gate.py 保证代码里新增的 SCRIBE3_*/HERMES_* env
  读取必须登记本注册表。
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field

from scribe3 import settings_store

_TRUE = {"1", "true", "yes", "on"}   # 与 context_cache._TRUE 逐字一致


@dataclass(frozen=True)
class Setting:
    key: str
    category: str          # connection | llm | craft | flags | gateway
    type: str              # 'int' | 'float' | 'str' | 'bool' | 'secret'
    default: object
    effect: str            # 'hot' | 'restart'
    label: str
    desc: str = ""
    min: float | None = None
    max: float | None = None
    danger: bool = False   # 前端二次确认


REGISTRY: tuple[Setting, ...] = (
    # ── connection(连接与服务;除 SSE 配额外均 restart)──
    Setting("SCRIBE3_SURREAL_URL", "connection", "str", "ws://127.0.0.1:8001/rpc", "restart", "SurrealDB 地址"),
    Setting("SCRIBE3_SURREAL_USER", "connection", "str", "root", "restart", "SurrealDB 用户名"),
    Setting("SCRIBE3_SURREAL_PASS", "connection", "secret", "root", "restart", "SurrealDB 密码"),
    Setting("SCRIBE3_CORS_ORIGINS", "connection", "str", "http://127.0.0.1:3311,http://localhost:3311", "restart", "CORS 白名单", "逗号分隔"),
    Setting("SCRIBE3_API_TOKEN", "connection", "secret", "", "restart", "后端 API token", "空 = 不鉴权(/health 除外)"),
    Setting("SCRIBE3_LIVE_MAX", "connection", "int", 5, "restart", "SSE /live 并发配额", min=1, max=64),
    Setting("SCRIBE3_WORK", "connection", "str", "main", "restart", "默认书 slug"),
    Setting("SCRIBE3_LOOP_JOURNAL_DIR", "connection", "str", "", "restart", "循环日志目录", "空 = ~/.scribe3-loop-journals"),
    Setting("SCRIBE3_IMPORT_JOURNAL_DIR", "connection", "str", "", "restart", "导入日志目录", "空 = 系统临时目录"),
    Setting("SCRIBE3_LLM_LEDGER", "connection", "str", "", "restart", "日帽台账路径", "空 = ~/.scribe2-surreal/scribe3_llm_ledger.sqlite3"),
    Setting("SCRIBE3_READ_MCP_LABEL", "connection", "str", "scribe3_read", "restart", "只读 MCP 工具集标签"),
    # ── llm(LLM 与用量;全热)──
    Setting("llm.model", "llm", "str", "doubao-seed-2.0-pro", "hot", "补全模型名"),
    Setting("llm.timeout_seconds", "llm", "float", 600.0, "hot", "LLM 请求超时(秒)", min=30, max=3600),
    Setting("llm.max_retries", "llm", "int", 3, "hot", "瞬时错误重试次数", min=0, max=10),
    Setting("SCRIBE3_DAILY_CALL_CAP", "llm", "int", 500, "hot", "每日 LLM 调用日帽", "系统级成本保险丝(计笔数非 token)", min=0, max=100000, danger=True),
    # ── craft(工艺阈值;全热,对应 critique.py 常量)──
    Setting("craft.banned_density_per_k", "craft", "float", 3.0, "hot", "禁词密度/千字", min=0, max=50),
    Setting("craft.banned_min_sents", "craft", "int", 3, "hot", "禁词判定最少句数", min=1, max=20),
    Setting("craft.contextual_per_k", "craft", "float", 1.5, "hot", "语境禁词密度/千字", min=0, max=50),
    Setting("craft.contextual_min_hits", "craft", "int", 2, "hot", "语境禁词最少命中", min=1, max=20),
    Setting("craft.wandai_block_hits", "craft", "int", 2, "hot", "顽固禁词阻断命中数", min=1, max=20),
    Setting("craft.max_negative_span", "craft", "int", 80, "hot", "负向情绪连续跨度上限", min=10, max=500),
    Setting("craft.max_positive_span", "craft", "int", 80, "hot", "正向情绪连续跨度上限", min=10, max=500),
    Setting("craft.oversaturation_per_k", "craft", "float", 3.0, "hot", "直说情绪密度/千字(留白)", min=0, max=50),
    Setting("craft.adverb_per_k_max", "craft", "float", 3.0, "hot", "副词密度上限/千字", min=0, max=50),
    Setting("craft.rule_of_three_item_max", "craft", "int", 6, "hot", "三段式条目上限", min=2, max=20),
    Setting("craft.rule_of_three_gate_per_k", "craft", "float", 2.0, "hot", "三段式密度门槛/千字", min=0, max=50),
    Setting("craft.near_dup_sim", "craft", "float", 0.7, "hot", "近似重复段落相似度阈值", min=0.3, max=1.0),
    Setting("craft.near_dup_min_len", "craft", "int", 25, "hot", "近似重复最短段长", min=10, max=500),
    # ── craft:记忆检索(memory_retrieval.py 常量)──
    Setting("memory.weight_structured", "craft", "float", 2.0, "hot", "检索权重:正典直查", min=0, max=10),
    Setting("memory.weight_bm25", "craft", "float", 1.0, "hot", "检索权重:BM25", min=0, max=10),
    Setting("memory.weight_vector", "craft", "float", 1.0, "hot", "检索权重:向量", min=0, max=10),
    Setting("memory.weight_graph", "craft", "float", 1.2, "hot", "检索权重:图", min=0, max=10),
    Setting("memory.weight_recency", "craft", "float", 0.8, "hot", "检索权重:recency(预留)", min=0, max=10),
    Setting("memory.half_life_working", "craft", "int", 3, "hot", "半衰期(天):working", min=1, max=3650),
    Setting("memory.half_life_episodic", "craft", "int", 30, "hot", "半衰期(天):episodic", min=1, max=3650),
    Setting("memory.half_life_procedural", "craft", "int", 180, "hot", "半衰期(天):procedural", min=1, max=3650),
    Setting("memory.half_life_reference", "craft", "int", 90, "hot", "半衰期(天):reference", min=1, max=3650),
    Setting("memory.half_life_uncertainty", "craft", "int", 14, "hot", "半衰期(天):uncertainty", min=1, max=3650),
    # ── flags(灰度开关;全热,danger)──
    Setting("SCRIBE3_CONTEXT_SNAPSHOT_V1", "flags", "bool", False, "hot", "统一上下文快照 v1", danger=True),
    Setting("SCRIBE3_EDITORIAL_THREAD_V1", "flags", "bool", False, "hot", "主编讨论线程 v1", danger=True),
    Setting("SCRIBE3_MEMORY_FABRIC_V1", "flags", "bool", False, "hot", "记忆织网检索 v1", danger=True),
    Setting("SCRIBE3_CONTEXT_INSPECTOR_V1", "flags", "bool", False, "hot", "上下文检查器 v1", danger=True),
    Setting("SCRIBE3_SPECTRON_SHADOW", "flags", "bool", False, "hot", "Spectron 影子双跑", danger=True),
    Setting("SCRIBE3_CONTEXT_ASSEMBLER_V1", "flags", "bool", False, "hot", "上下文装配器 v1", danger=True),
    # ── gateway(Hermes 网关;地址类 restart)──
    Setting("HERMES_API", "gateway", "str", "http://127.0.0.1:8642/v1", "restart", "速答网关(default)"),
    Setting("HERMES_RESPONSES_API", "gateway", "str", "http://127.0.0.1:8643/v1", "restart", "agentic 读网关"),
    Setting("HERMES_RESPONSES_PROFILE", "gateway", "str", "scribe3", "restart", "读网关 profile"),
    Setting("HERMES_RUNS_API", "gateway", "str", "http://127.0.0.1:8644/v1", "restart", "写入 Runs 网关"),
    Setting("HERMES_RUNS_PROFILE", "gateway", "str", "scribe3_write", "restart", "写网关 profile"),
    Setting("HERMES_HOME", "gateway", "str", "", "restart", "Hermes 根目录", "空 = ~/.hermes"),
    Setting("gateway.hermes_bin", "gateway", "str", "~/.local/bin/hermes", "restart", "hermes CLI 路径", "一键重启用"),
)
_BY_KEY: dict[str, Setting] = {s.key: s for s in REGISTRY}

_cache_lock = threading.Lock()
_cache: dict = {"ts": 0.0, "overrides": None}
_CACHE_TTL = 2.0   # 跨进程收敛窗口:另一进程写入后本进程最迟 2s 见到


def invalidate_cache() -> None:
    with _cache_lock:
        _cache["ts"] = 0.0
        _cache["overrides"] = None


def _overrides() -> dict[str, str]:
    with _cache_lock:
        if _cache["overrides"] is None or time.monotonic() - _cache["ts"] > _CACHE_TTL:
            _cache["overrides"] = settings_store.get_all_overrides()
            _cache["ts"] = time.monotonic()
        return _cache["overrides"]


def _coerce(s: Setting, value):
    """类型归一 + 校验;非法抛 ValueError。env 字符串与 JSON 原生值都走这里。"""
    if s.type == "bool":
        if isinstance(value, str):
            value = value.strip().lower() in _TRUE
        value = bool(value)
    elif s.type == "int":
        value = int(value)
    elif s.type == "float":
        value = float(value)
    else:   # str / secret
        value = str(value)
    if s.min is not None and isinstance(value, (int, float)) and value < s.min:
        raise ValueError(f"{s.key} 低于下限 {s.min}")
    if s.max is not None and isinstance(value, (int, float)) and value > s.max:
        raise ValueError(f"{s.key} 高于上限 {s.max}")
    return value


def get_setting(key: str):
    s = _BY_KEY[key]
    raw = _overrides().get(key)
    if raw is not None:
        try:
            return _coerce(s, json.loads(raw))
        except Exception:
            pass   # 台账里的坏值不炸系统:回落 env/默认
    if key.isupper():   # env 只对全大写既有键生效
        env = os.environ.get(key)
        if env is not None and env != "":
            try:
                return _coerce(s, env)
            except Exception:
                pass
    return s.default


def put_setting(key: str, value) -> dict:
    s = _BY_KEY[key]   # 未登记 → KeyError,调用方转 404
    coerced = _coerce(s, value)
    old = _overrides().get(key)
    settings_store.set_override(key, json.dumps(coerced, ensure_ascii=False),
                                old_json=old, mask=(s.type == "secret"))
    invalidate_cache()
    return {"key": key, "value": None if s.type == "secret" else coerced, "effect": s.effect}


def reset_setting(key: str) -> None:
    s = _BY_KEY[key]
    old = _overrides().get(key)
    settings_store.delete_override(key, old_json=old, mask=(s.type == "secret"))
    invalidate_cache()


def _source(s: Setting) -> str:
    if s.key in _overrides():
        return "db"
    if s.key.isupper() and os.environ.get(s.key):
        return "env"
    return "default"


def _pending_restart(s: Setting) -> bool:
    """restart 项:DB 已存值 ≠ 当前进程 env 生效值 → 待重启。"""
    if s.effect != "restart" or s.key not in _overrides():
        return False
    try:
        db_val = _coerce(s, json.loads(_overrides()[s.key]))
    except Exception:
        return False
    env = os.environ.get(s.key)
    cur = _coerce(s, env) if env not in (None, "") else s.default
    return db_val != cur


def settings_snapshot() -> list[dict]:
    """GET /settings 的序列化:secret 掩码(value=None + is_set),永不回显明文。"""
    out = []
    for s in REGISTRY:
        val = get_setting(s.key)
        secret = s.type == "secret"
        out.append({
            "key": s.key, "category": s.category, "type": s.type,
            "label": s.label, "desc": s.desc, "effect": s.effect, "danger": s.danger,
            "default": None if secret else s.default,
            "value": None if secret else val,
            "is_set": bool(val) if secret else None,
            "source": _source(s), "min": s.min, "max": s.max,
            "pending_restart": _pending_restart(s),
        })
    return out


def apply_restart_overrides() -> None:
    """进程启动最早期调用(app.py / mcp.py 顶部):把 restart 项的 DB 覆盖灌进
    os.environ,后续模块按原 env 路径读取。DB 是持久层,env 是进程生效层。"""
    ov = settings_store.get_all_overrides()
    for s in REGISTRY:
        if s.effect != "restart" or s.key not in ov or not s.key.isupper():
            continue
        try:
            v = _coerce(s, json.loads(ov[s.key]))
        except Exception:
            continue
        os.environ[s.key] = str(v).lower() if s.type == "bool" else str(v)
```

- [ ] **Step 4: 跑测确认通过**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings.py scribe3/tests/test_settings_store.py -q`
Expected: 全 passed

- [ ] **Step 5: Commit** `feat: 配置注册表+get_setting 三级优先+secret 掩码快照+restart 灌注`

### Task 3:REST 四端点 + 写路由台账登记

**Files:**
- Modify: `scribe3/app.py`(在 `GET /capabilities`(约 :710)之后加设置端点;文件顶部 import 区加启动灌注)
- Modify: `scribe3/tests/test_consistency.py`(`KNOWN_REST_WRITE_ROUTES` 登记)
- Test: `scribe3/tests/test_settings_api.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_settings_api.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    from scribe3 import settings
    settings.invalidate_cache()
    from scribe3.app import app
    return TestClient(app)


def test_get_settings_metadata(client):
    r = client.get("/settings")
    assert r.status_code == 200
    items = {i["key"]: i for i in r.json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 500
    assert items["SCRIBE3_DAILY_CALL_CAP"]["category"] == "llm"
    assert items["SCRIBE3_SURREAL_PASS"]["value"] is None   # secret 永不回显


def test_put_validate_and_reset(client):
    assert client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": 800}).status_code == 200
    items = {i["key"]: i for i in client.get("/settings").json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 800
    assert items["SCRIBE3_DAILY_CALL_CAP"]["source"] == "db"
    assert client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": -5}).status_code == 422
    assert client.put("/settings/no.such.key", json={"value": 1}).status_code == 404
    assert client.post("/settings/SCRIBE3_DAILY_CALL_CAP/reset").status_code == 200
    items = {i["key"]: i for i in client.get("/settings").json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 500


def test_audit_endpoint(client):
    client.put("/settings/craft.near_dup_sim", json={"value": 0.8})
    rows = client.get("/settings/audit").json()["rows"]
    assert rows[0]["key"] == "craft.near_dup_sim"
```

- [ ] **Step 2: 跑测确认失败**(404 路由不存在)

- [ ] **Step 3: 实现端点(app.py,capabilities 端点后)**

```python
# ── 统一设置中心(spec: docs/superpowers/specs/2026-07-12-settings-center-design.md)──
from pydantic import BaseModel as _BM

class SettingPutReq(_BM):
    value: object = None

@app.get("/settings")
def settings_all():
    """全量设置:值(secret 掩码)+来源+默认+元数据+pending_restart。只读。"""
    from scribe3 import settings as S
    return {"settings": S.settings_snapshot(),
            "categories": ["connection", "llm", "craft", "flags", "gateway"]}

@app.put("/settings/{key}")
def settings_put(key: str, req: SettingPutReq):
    from scribe3 import settings as S
    try:
        return S.put_setting(key, req.value)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))

@app.post("/settings/{key}/reset")
def settings_reset(key: str):
    from scribe3 import settings as S
    try:
        S.reset_setting(key)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    return {"key": key, "status": "reset"}

@app.get("/settings/audit")
def settings_audit(limit: int = 50, offset: int = 0):
    from scribe3 import settings_store
    return {"rows": settings_store.audit_rows(limit=min(limit, 200), offset=offset)}
```

注意 FastAPI 路由顺序:`/settings/audit` 必须注册在 `/settings/{key}` 的 GET 之前(本设计 `{key}` 只有 PUT/POST,无冲突,但保持 audit 端点先注册以防未来加 GET)。

app.py **顶部 import 区之后、`app = FastAPI(...)` 之前**加启动灌注(CORS 读取在 app 构造时,必须先灌):

```python
from scribe3 import settings as _settings
_settings.apply_restart_overrides()   # restart 类 DB 覆盖灌 env,必须在 CORS/token 读取前
```

- [ ] **Step 4: 登记写路由台账(test_consistency.py,`KNOWN_REST_WRITE_ROUTES` 尾部)**

```python
        # 统一设置中心:PUT 写 SQLite 设置台账(带校验+审计,secret 掩码);
        # reset 删覆盖值回落 env/默认。不碰正典数据。
        ("PUT", "/settings/{key}"),
        ("POST", "/settings/{key}/reset"),
```

- [ ] **Step 5: 跑测确认通过**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_api.py scribe3/tests/test_consistency.py -q`
Expected: 全 passed

- [ ] **Step 6: Commit** `feat: /settings CRUD+审计 REST + 台账登记 + 启动期 restart 灌注`

### Task 4:注册表门禁测试

**Files:**
- Test: `scribe3/tests/test_settings_gate.py`

- [ ] **Step 1: 写门禁测试(直接写实现——门禁本身就是测试)**

```python
# scribe3/tests/test_settings_gate.py
"""注册表完备性门禁(与 KNOWN_REST_WRITE_ROUTES 同范式):
代码里新增 SCRIBE3_*/HERMES_* 环境变量读取,必须登记 settings.REGISTRY,
否则本测试红——配置从此不再散落。"""
import re
from pathlib import Path

from scribe3.settings import REGISTRY

SRC = Path(__file__).resolve().parent.parent   # scribe3/
# 测试/工具/插件专用 env,不进设置中心(见 spec「明确不做」)
EXEMPT = {
    "SCRIBE3_SETTINGS_DB",     # 设置台账自身路径(自举,不能存在自己里面)
    "SCRIBE3_API_BASE",        # hermes 插件回调(插件进程 env)
    "SURREAL_BIN",             # 测试专用
    "API_SERVER_KEY",          # Hermes 鉴权链(HermesAuth 多级回退,非本系统配置)
}
_PAT = re.compile(r"os\.(?:environ\.get|getenv|environ\[)\(?\s*['\"]([A-Z][A-Z0-9_]+)['\"]")


def test_all_env_reads_registered():
    registered = {s.key for s in REGISTRY}
    offenders = []
    for py in SRC.glob("*.py"):
        for name in _PAT.findall(py.read_text(encoding="utf-8")):
            if not (name.startswith("SCRIBE3_") or name.startswith("HERMES_")):
                continue
            if name not in registered and name not in EXEMPT:
                offenders.append(f"{py.name}: {name}")
    assert not offenders, f"发现未登记设置注册表的 env 读取: {offenders}"
```

- [ ] **Step 2: 跑测**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_gate.py -q`
Expected: PASS(注册表已覆盖全部现存 env;若红,把漏项补进 REGISTRY 或 EXEMPT——漏项本身就是门禁价值)

- [ ] **Step 3: Commit** `test: 设置注册表完备性门禁(env 读取必须登记)`

---

## Phase 2:热生效读点迁移

### Task 5:灰度 flags 迁移(字节等价关键)

**Files:**
- Modify: `scribe3/context_cache.py:46-49`(`flag_enabled`)
- Test: `scribe3/tests/test_settings_migration.py`(新)

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_settings_migration.py
import pytest
from scribe3 import settings


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    settings.invalidate_cache()
    yield
    settings.invalidate_cache()


def test_flag_enabled_reads_settings_db():
    from scribe3.context_cache import flag_enabled
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is False   # 字节等价:无覆盖=关
    settings.put_setting("SCRIBE3_MEMORY_FABRIC_V1", True)
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True    # 热生效,无需重启


def test_flag_enabled_env_still_works(monkeypatch):
    from scribe3.context_cache import flag_enabled
    monkeypatch.setenv("SCRIBE3_SPECTRON_SHADOW", "on")
    settings.invalidate_cache()
    assert flag_enabled("SCRIBE3_SPECTRON_SHADOW") is True     # env 路径不破坏


def test_flag_enabled_unknown_name_falls_back_env(monkeypatch):
    from scribe3.context_cache import flag_enabled
    monkeypatch.setenv("SOME_FUTURE_FLAG", "1")
    assert flag_enabled("SOME_FUTURE_FLAG") is True            # 未登记名回落旧 env 语义
```

- [ ] **Step 2: 跑测确认失败**(put 后 flag_enabled 仍 False)

- [ ] **Step 3: 改 `flag_enabled`(context_cache.py)**

```python
def flag_enabled(name: str) -> bool:
    """统一开关判定:先读设置中心(DB 覆盖→env→默认,热生效),未登记名
    回落旧 env 语义(向前兼容)。默认关 → 与开关引入前【字节等价】。"""
    try:
        from scribe3.settings import get_setting
        return bool(get_setting(name))
    except KeyError:
        return os.environ.get(name, "").strip().lower() in _TRUE
```

- [ ] **Step 4: 跑测确认通过 + flags 既有回归**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_migration.py scribe3/tests/test_context_assembler.py scribe3/tests/test_capabilities.py -q`(capabilities 测试文件名以 `grep -rl "capabilities" scribe3/tests` 实际为准)
Expected: 全 passed

- [ ] **Step 5: Commit** `feat: 灰度 flags 接设置中心(界面开关热生效,env/字节等价保持)`

### Task 6:llm.py 迁移(模型/超时/重试/日帽)

**Files:**
- Modify: `scribe3/llm.py`
- Test: `scribe3/tests/test_settings_migration.py`(追加)

- [ ] **Step 1: 追加失败测试**

```python
def test_llm_daily_cap_hot(monkeypatch):
    import scribe3.llm as llm
    calls = {}
    monkeypatch.setattr("scribe3.usage.tick", lambda cap: calls.setdefault("cap", cap))
    settings.put_setting("SCRIBE3_DAILY_CALL_CAP", 42)
    llm._tick_daily()
    assert calls["cap"] == 42          # 改日帽下一次调用即生效,无需重启


def test_llm_model_default_from_settings():
    import scribe3.llm as llm
    settings.put_setting("llm.model", "test-model-x")
    assert llm.default_model() == "test-model-x"
    assert llm.max_retries() == 3
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 改 llm.py**

模块常量 `_DAILY_CALL_CAP = int(os.environ.get(...))`(llm.py:28)删除,新增三个读取函数;`_tick_daily`/`daily_remaining` 与两处 `model: str = "doubao-seed-2.0-pro", timeout: float = 600.0` 签名(llm.py:91,122)改为 `model: str | None = None, timeout: float | None = None` + 函数体首行解析:

```python
def _cap() -> int:
    from scribe3.settings import get_setting
    return get_setting("SCRIBE3_DAILY_CALL_CAP")

def default_model() -> str:
    from scribe3.settings import get_setting
    return get_setting("llm.model")

def default_timeout() -> float:
    from scribe3.settings import get_setting
    return get_setting("llm.timeout_seconds")

def max_retries() -> int:
    from scribe3.settings import get_setting
    return get_setting("llm.max_retries")
```

```python
def _tick_daily() -> None:
    from scribe3 import usage as _usage
    _usage.tick(_cap())

def daily_remaining() -> int:
    from scribe3 import usage as _usage
    used, _scope = _usage.used_today()
    return max(0, _cap() - used)
```

补全函数体首行(hermes_complete / hermes_complete_stream):

```python
    model = model or default_model()
    timeout = timeout if timeout is not None else default_timeout()
```

`_MAX_RETRIES` 的每个使用点(grep `_MAX_RETRIES` 全部替换)改调 `max_retries()`;常量保留删除。
网关地址常量(`HERMES` / `HERMES_RESPONSES` / `HERMES_RUNS` / 两 profile)**不动**——registry 已登记为 restart 类,启动灌注生效。

- [ ] **Step 4: 跑测 + LLM 相关回归**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_migration.py scribe3/tests/test_llm*.py -q`
Expected: 全 passed

- [ ] **Step 5: Commit** `feat: llm 模型/超时/重试/日帽接设置中心热生效`

### Task 7:critique.py 阈值迁移(13 项)

**Files:**
- Modify: `scribe3/critique.py`
- Test: `scribe3/tests/test_settings_migration.py`(追加)

**常量 ↔ 设置键映射表(全部;行号以当前 HEAD 为准,执行时 grep 确认):**

| critique.py 常量/默认参 | 位置 | 设置键 |
|---|---|---|
| `_BANNED_DENSITY_PER_K` | :553 | `craft.banned_density_per_k` |
| `_BANNED_MIN_SENTS` | :554 | `craft.banned_min_sents` |
| `_CONTEXTUAL_PER_K` | :555 | `craft.contextual_per_k` |
| `_CONTEXTUAL_MIN_HITS` | :556 | `craft.contextual_min_hits` |
| `_WANDAI_BLOCK_HITS` | :557 | `craft.wandai_block_hits` |
| `_MAX_NEGATIVE_SPAN` | :398 | `craft.max_negative_span` |
| `_MAX_POSITIVE_SPAN` | :399 | `craft.max_positive_span` |
| `find_oversaturation(per_k_explain=3.0)` | :706 | `craft.oversaturation_per_k` |
| `find_adverb_density(per_k_max=3.0)` | :730 | `craft.adverb_per_k_max` |
| `_RULE_OF_THREE_ITEM_MAX` | :757 | `craft.rule_of_three_item_max` |
| `_RULE_OF_THREE_GATE_PER_K` | :789 | `craft.rule_of_three_gate_per_k` |
| `find_near_duplicate_paragraphs(sim=0.7)` | :159 | `craft.near_dup_sim` |
| `find_near_duplicate_paragraphs(min_len=25)` | :159 | `craft.near_dup_min_len` |

- [ ] **Step 1: 追加失败测试(抽 2 个代表:模块常量型 + 默认参数型)**

```python
def test_critique_thresholds_hot():
    from scribe3.critique import find_near_duplicate_paragraphs
    a = "他躺在自己的棺材里,数着头顶的木纹,一直数到天亮才闭眼。"
    b = "他躺在自己的棺材里,数着头顶的木纹,数到三更便闭了眼。"
    text = a + "\n" + b
    assert find_near_duplicate_paragraphs(text) != []          # 默认 0.7 命中
    settings.put_setting("craft.near_dup_sim", 0.99)
    assert find_near_duplicate_paragraphs(text) == []          # 调高阈值热生效


def test_critique_banned_density_hot():
    from scribe3 import critique
    settings.put_setting("craft.banned_density_per_k", 99.0)
    assert critique._th("craft.banned_density_per_k") == 99.0
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 改 critique.py**

文件顶部加取值 helper(模块常量保留为注册表 default 的镜像注释,不再被引用后删除):

```python
def _th(key: str):
    """工艺阈值取值:设置中心热生效(DB→env→注册表默认)。"""
    from scribe3.settings import get_setting
    return get_setting(key)
```

按映射表逐项机械替换:
- 模块常量型(`_BANNED_DENSITY_PER_K` 等 7 项):删除常量定义,使用点改 `_th("craft.banned_density_per_k")`(grep 每个常量名找全使用点);
- 默认参数型(`per_k_explain=3.0` / `per_k_max=3.0` / `sim=0.7` / `min_len=25`):签名改 `=None`,函数体首行 `per_k_explain = per_k_explain if per_k_explain is not None else _th("craft.oversaturation_per_k")`(显式传参的调用方行为不变);
- `_RULE_OF_THREE_*` 两项同模块常量型处理。

- [ ] **Step 4: 跑测 + critique 全回归**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_migration.py scribe3/tests/test_critique.py -q`
Expected: 全 passed

- [ ] **Step 5: Commit** `feat: critique 13 项检测器阈值接设置中心热生效`

### Task 8:memory_retrieval.py 权重/半衰期迁移

**Files:**
- Modify: `scribe3/memory_retrieval.py:33-37`
- Test: `scribe3/tests/test_settings_migration.py`(追加)

- [ ] **Step 1: 追加失败测试**

```python
def test_memory_weights_hot():
    from scribe3 import memory_retrieval as mr
    assert mr.channel_weights()["structured"] == 2.0
    settings.put_setting("memory.weight_structured", 5.0)
    assert mr.channel_weights()["structured"] == 5.0
    settings.put_setting("memory.half_life_working", 7)
    assert mr.half_life_days()["working"] == 7
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 改 memory_retrieval.py**

`CHANNEL_WEIGHTS` / `HALF_LIFE_DAYS` 两个 dict 常量改为函数(保留原注释):

```python
def channel_weights() -> dict[str, float]:
    from scribe3.settings import get_setting
    return {c: get_setting(f"memory.weight_{c}")
            for c in ("structured", "bm25", "vector", "graph", "recency")}

def half_life_days() -> dict[str, int]:
    from scribe3.settings import get_setting
    return {c: get_setting(f"memory.half_life_{c}")
            for c in ("working", "episodic", "procedural", "reference", "uncertainty")}
```

grep `CHANNEL_WEIGHTS` / `HALF_LIFE_DAYS` 全部使用点(本文件内 fuse/decay,及可能的跨文件引用)改调函数;若有测试直接 import 常量,同步改。

- [ ] **Step 4: 跑测 + 检索回归**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings_migration.py scribe3/tests/test_memory_retrieval.py -q`
Expected: 全 passed

- [ ] **Step 5: 全量后端回归(Phase 2 收口)**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests -q`
Expected: 全绿(基线 1566+新增)

- [ ] **Step 6: Commit** `feat: 记忆检索权重/半衰期接设置中心热生效`

---

## Phase 3:Hermes 网关管控端点

### Task 9:`GET /gateway/status`(三网关探活)

**Files:**
- Modify: `scribe3/app.py`(设置端点区之后)
- Test: `scribe3/tests/test_gateway_api.py`(新)

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_gateway_api.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    from scribe3 import settings
    settings.invalidate_cache()
    from scribe3.app import app
    return TestClient(app)


def test_gateway_status_shape(client, monkeypatch):
    import httpx
    def fake_get(url, timeout):
        class R: status_code = 200
        if "8643" in url:
            return R()
        raise httpx.ConnectError("down")
    monkeypatch.setattr("httpx.get", fake_get)
    r = client.get("/gateway/status")
    assert r.status_code == 200
    by = {g["name"]: g for g in r.json()["gateways"]}
    assert by["responses"]["online"] is True
    assert by["default"]["online"] is False
    assert by["runs"]["profile"] == "scribe3_write"
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现**

```python
@app.get("/gateway/status")
def gateway_status():
    """三 Hermes 网关探活(GET {base}/models,1.5s 超时)。只读。"""
    import httpx
    from scribe3.settings import get_setting
    targets = [
        ("default", get_setting("HERMES_API"), "(default)"),
        ("responses", get_setting("HERMES_RESPONSES_API"), get_setting("HERMES_RESPONSES_PROFILE")),
        ("runs", get_setting("HERMES_RUNS_API"), get_setting("HERMES_RUNS_PROFILE")),
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
```

- [ ] **Step 4: 跑测确认通过;Commit** `feat: /gateway/status 三网关探活`

### Task 10:`GET/PUT /gateway/files`(白名单+备份+掩码+409)

**Files:**
- Create: `scribe3/gateway_files.py`
- Modify: `scribe3/app.py`(两端点)、`scribe3/tests/test_consistency.py`(登记 `("PUT", "/gateway/files")`)
- Test: `scribe3/tests/test_gateway_files.py`(新)

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_gateway_files.py
import hashlib
import pytest
from scribe3 import gateway_files as gf


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    d = tmp_path / "profiles" / "scribe3"
    d.mkdir(parents=True)
    (d / "SOUL.md").write_text("我是主编", encoding="utf-8")
    (d / ".env").write_text("API_SERVER_PORT=8643\nAPI_SERVER_KEY=sk-secret\n", encoding="utf-8")
    return tmp_path


def test_list_masks_env_secrets(home):
    files = {f["id"]: f for f in gf.list_files()}
    soul = files["scribe3/SOUL.md"]
    assert soul["content"] == "我是主编" and soul["exists"]
    env = files["scribe3/.env"]
    assert "sk-secret" not in env["content"]
    assert "API_SERVER_KEY=••••" in env["content"]


def test_write_requires_hash_and_backs_up(home):
    files = {f["id"]: f for f in gf.list_files()}
    soul = files["scribe3/SOUL.md"]
    gf.write_file("scribe3/SOUL.md", "我是新主编", base_sha256=soul["sha256"])
    assert (home / "profiles" / "scribe3" / "SOUL.md").read_text(encoding="utf-8") == "我是新主编"
    baks = list((home / "profiles" / "scribe3").glob("SOUL.md.bak.*"))
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "我是主编"
    with pytest.raises(gf.StaleFileError):
        gf.write_file("scribe3/SOUL.md", "再改", base_sha256=soul["sha256"])   # hash 已变 → 409


def test_masked_env_lines_restored_on_save(home):
    files = {f["id"]: f for f in gf.list_files()}
    env = files["scribe3/.env"]
    edited = env["content"].replace("API_SERVER_PORT=8643", "API_SERVER_PORT=9999")
    gf.write_file("scribe3/.env", edited, base_sha256=env["sha256"])
    saved = (home / "profiles" / "scribe3" / ".env").read_text(encoding="utf-8")
    assert "API_SERVER_PORT=9999" in saved
    assert "API_SERVER_KEY=sk-secret" in saved   # 掩码行原样还原,密钥不丢


def test_whitelist_rejects_traversal(home):
    with pytest.raises(gf.NotAllowedError):
        gf.write_file("../outside.txt", "x", base_sha256="")
    with pytest.raises(gf.NotAllowedError):
        gf.write_file("scribe3/config.yaml/../../../etc/passwd", "x", base_sha256="")
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现 gateway_files.py**

```python
# scribe3/gateway_files.py
"""Hermes profile 文件的白名单读写(设置中心网关区)。

安全边界:
- 白名单硬编码:profiles/{scribe3,scribe3_write}/{config.yaml,SOUL.md,.env},
  id 必须精确命中,resolve 后必须仍在 HERMES_HOME 下(双保险防穿越)。
- .env 读取时掩码含 KEY/TOKEN/PASS/SECRET 的行(value → ••••);保存时凡值为
  «••••» 的行按原文件还原(密钥永不经网络明文往返)。
- 写前自动备份 <file>.bak.<ts>;base_sha256 失配抛 StaleFileError(→409)。
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path

_PROFILES = ("scribe3", "scribe3_write")
_NAMES = ("config.yaml", "SOUL.md", ".env")
_MASK = "••••"
_SECRET_LINE = re.compile(r"^(\s*[A-Za-z0-9_]*(?:KEY|TOKEN|PASS|SECRET)[A-Za-z0-9_]*\s*=).*$")


class NotAllowedError(Exception): ...
class StaleFileError(Exception): ...


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()


def _resolve(file_id: str) -> Path:
    parts = file_id.split("/")
    if len(parts) != 2 or parts[0] not in _PROFILES or parts[1] not in _NAMES:
        raise NotAllowedError(f"白名单外文件: {file_id}")
    p = (_home() / "profiles" / parts[0] / parts[1]).resolve()
    if not str(p).startswith(str(_home().resolve())):
        raise NotAllowedError(f"路径越界: {file_id}")
    return p


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mask_env(text: str) -> str:
    return "\n".join(_SECRET_LINE.sub(rf"\g<1>{_MASK}", ln) for ln in text.split("\n"))


def list_files() -> list[dict]:
    out = []
    for prof in _PROFILES:
        for name in _NAMES:
            fid = f"{prof}/{name}"
            p = _resolve(fid)
            if p.exists():
                raw = p.read_text(encoding="utf-8")
                shown = _mask_env(raw) if name == ".env" else raw
                out.append({"id": fid, "path": str(p), "exists": True,
                            "content": shown, "sha256": _sha(raw)})
            else:
                out.append({"id": fid, "path": str(p), "exists": False,
                            "content": "", "sha256": _sha("")})
    return out


def write_file(file_id: str, content: str, *, base_sha256: str) -> dict:
    p = _resolve(file_id)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    if _sha(old) != base_sha256:
        raise StaleFileError("文件已被外部修改,请重新加载后再编辑")
    if file_id.endswith("/.env"):
        # 掩码行还原:值为 •••• 的行,用原文件同名行替换(密钥不经网络往返)
        orig = {m.group(1): ln for ln in old.split("\n")
                if (m := _SECRET_LINE.match(ln))}
        restored = []
        for ln in content.split("\n"):
            m = _SECRET_LINE.match(ln)
            if m and ln.strip().endswith(_MASK) and m.group(1) in orig:
                restored.append(orig[m.group(1)])
            else:
                restored.append(ln)
        content = "\n".join(restored)
    if p.exists():
        bak = p.with_name(f"{p.name}.bak.{time.strftime('%Y%m%d%H%M%S')}")
        bak.write_text(old, encoding="utf-8")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"id": file_id, "sha256": _sha(content), "backup": p.exists()}
```

- [ ] **Step 4: app.py 两端点 + 台账登记**

```python
class GatewayFilePutReq(_BM):
    id: str
    content: str
    base_sha256: str

@app.get("/gateway/files")
def gateway_files_list():
    from scribe3 import gateway_files as gf
    return {"files": gf.list_files()}

@app.put("/gateway/files")
def gateway_files_put(req: GatewayFilePutReq):
    from scribe3 import gateway_files as gf
    try:
        return gf.write_file(req.id, req.content, base_sha256=req.base_sha256)
    except gf.NotAllowedError as e:
        raise HTTPException(403, str(e))
    except gf.StaleFileError as e:
        raise HTTPException(409, str(e))
```

台账登记(test_consistency.py):

```python
        # 设置中心网关区:白名单内 profile 文件写(自动 .bak 备份 + sha 冲突 409;
        # .env 掩码行按原文件还原,密钥不经网络往返);restart 由独立端点显式触发。
        ("PUT", "/gateway/files"),
```

- [ ] **Step 5: 跑测确认通过**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_gateway_files.py scribe3/tests/test_consistency.py -q`
Expected: 全 passed

- [ ] **Step 6: Commit** `feat: 网关 profile 文件白名单读写(备份/掩码还原/409)`

### Task 11:`POST /gateway/restart`(nohup 后台 + 轮询)

**Files:**
- Modify: `scribe3/app.py`、`scribe3/tests/test_consistency.py`(登记)
- Test: `scribe3/tests/test_gateway_api.py`(追加)

- [ ] **Step 1: 追加失败测试**

```python
def test_gateway_restart_polls(client, monkeypatch):
    import httpx
    ran = {}
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/restart", json={"profile": "scribe3"})
    assert r.status_code == 200 and r.json()["online"] is True
    assert "nohup" in ran["cmd"] and "-p scribe3" in ran["cmd"]


def test_gateway_restart_rejects_unknown_profile(client):
    assert client.post("/gateway/restart", json={"profile": "evil"}).status_code == 422
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现**

```python
class GatewayRestartReq(_BM):
    profile: str

@app.post("/gateway/restart")
def gateway_restart(req: GatewayRestartReq):
    """重启指定 profile 的 Hermes 网关。铁律:nohup 后台拉起 + 轮询探活,
    绝不前台阻塞;轮询超时如实报失败,不假成功。"""
    import subprocess, time as _t
    import httpx
    from scribe3.settings import get_setting
    apis = {"scribe3": get_setting("HERMES_RESPONSES_API"),
            "scribe3_write": get_setting("HERMES_RUNS_API")}
    if req.profile not in apis:
        raise HTTPException(422, f"未知 profile: {req.profile}(仅支持 scribe3/scribe3_write)")
    hermes = os.path.expanduser(get_setting("gateway.hermes_bin"))
    log = f"/tmp/scribe3-hermes-{req.profile}.log"
    cmd = f"nohup {hermes} -p {req.profile} gateway run --replace >> {log} 2>&1 &"
    subprocess.Popen(cmd, shell=True)
    base = apis[req.profile].rstrip("/")
    online = False
    for _ in range(30):   # 轮询至多 30s
        _t.sleep(1)
        try:
            if httpx.get(f"{base}/models", timeout=1.5).status_code < 500:
                online = True
                break
        except Exception:
            continue
    return {"profile": req.profile, "online": online, "log": log,
            "message": "已重启" if online else "重启后 30s 内未探活成功,请查看日志"}
```

台账登记:

```python
        # 设置中心:一键重启网关(nohup 后台+轮询探活;失败如实报,不假成功)
        ("POST", "/gateway/restart"),
```

- [ ] **Step 4: 跑测确认通过;Commit** `feat: /gateway/restart 一键重启(nohup+轮询铁律)`

---

## Phase 4:前端设置中心

### Task 12:api.js 客户端 + 视图路由接线(齿轮入口)

**Files:**
- Modify: `scribe3/web/src/api.js`(追加 8 个方法)
- Modify: `scribe3/web/src/AppRail.jsx`(主题按钮旁加齿轮)
- Modify: `scribe3/web/src/DetailPane.jsx:63-71`(view 路由加 settings 分支)
- Test: `scribe3/web/src/__tests__/settingsRoute.test.jsx`(新)

- [ ] **Step 1: 写失败测试**

```jsx
// scribe3/web/src/__tests__/settingsRoute.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AppRail } from '../AppRail'

vi.mock('../api', () => ({ api: { settings: vi.fn(() => Promise.resolve({ settings: [], categories: [] })) } }))

describe('设置中心入口', () => {
  it('顶栏齿轮触发 onView(settings),当前视图时高亮', () => {
    const onView = vi.fn()
    const { rerender } = render(<AppRail current={{ slug: 'b', title: '书' }} view={null} onView={onView}
      onOpenLibrary={() => {}} theme="light" onTheme={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: '设置' }))
    expect(onView).toHaveBeenCalledWith('settings')
    rerender(<AppRail current={{ slug: 'b', title: '书' }} view="settings" onView={onView}
      onOpenLibrary={() => {}} theme="light" onTheme={() => {}} />)
    expect(screen.getByRole('button', { name: '设置' }).getAttribute('aria-current')).toBe('page')
  })
})
```

- [ ] **Step 2: 跑测确认失败**(无「设置」按钮)

- [ ] **Step 3: 实现**

api.js 追加(跟随文件内既有 fetch 封装惯例,以实际 helper 名为准):

```js
  // ── 统一设置中心 ──
  settings: () => j(`${BASE}/settings`),
  putSetting: (key, value) => j(`${BASE}/settings/${encodeURIComponent(key)}`, { method: 'PUT', body: { value } }),
  resetSetting: (key) => j(`${BASE}/settings/${encodeURIComponent(key)}/reset`, { method: 'POST' }),
  settingsAudit: (offset = 0) => j(`${BASE}/settings/audit?offset=${offset}`),
  gatewayStatus: () => j(`${BASE}/gateway/status`),
  gatewayFiles: () => j(`${BASE}/gateway/files`),
  putGatewayFile: (id, content, base_sha256) => j(`${BASE}/gateway/files`, { method: 'PUT', body: { id, content, base_sha256 } }),
  gatewayRestart: (profile) => j(`${BASE}/gateway/restart`, { method: 'POST', body: { profile } }),
```

AppRail.jsx:import 加 `Settings` 图标(lucide);主题按钮前加:

```jsx
        <button onClick={() => onView('settings')} aria-current={view === 'settings' ? 'page' : undefined}
          title="设置" aria-label="设置"
          className={`h-7 w-7 rounded-md inline-flex items-center justify-center cursor-pointer ${
            view === 'settings' ? 'bg-soft text-brand' : 'text-faint hover:text-ink hover:bg-soft'}`}>
          <Settings size={15} />
        </button>
```

DetailPane.jsx view 分支(`overview` 行后):

```jsx
    if (k === 'settings') return <SettingsView key="settings" work={work} />
```

顶部 import:`import { SettingsView } from './settings/SettingsView'`(下一任务创建;本任务先建占位:

```jsx
// scribe3/web/src/settings/SettingsView.jsx(占位,Task 13 替换)
export function SettingsView() { return <div data-testid="settings-view" className="p-8">设置中心</div> }
```

- [ ] **Step 4: 跑测确认通过;Commit** `feat: 设置中心入口(顶栏齿轮→横切视图)+ api 客户端`

### Task 13:SettingsView 骨架 + 元数据驱动表单(SettingField)

**Files:**
- Create: `scribe3/web/src/settings/SettingsView.jsx`(替换占位)
- Create: `scribe3/web/src/settings/SettingField.jsx`
- Test: `scribe3/web/src/settings/__tests__/settingsView.test.jsx`(新)

- [ ] **Step 1: 写失败测试**

```jsx
// scribe3/web/src/settings/__tests__/settingsView.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  settings: vi.fn(), putSetting: vi.fn(), resetSetting: vi.fn(),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [] })),
  gatewayStatus: vi.fn(() => Promise.resolve({ gateways: [] })),
  gatewayFiles: vi.fn(() => Promise.resolve({ files: [] })),
  intent: vi.fn(() => Promise.resolve({})), putIntent: vi.fn(),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { SettingsView } from '../SettingsView'

const ITEMS = [
  { key: 'SCRIBE3_DAILY_CALL_CAP', category: 'llm', type: 'int', label: '每日 LLM 调用日帽',
    value: 500, default: 500, source: 'default', effect: 'hot', danger: true, pending_restart: false },
  { key: 'SCRIBE3_SURREAL_URL', category: 'connection', type: 'str', label: 'SurrealDB 地址',
    value: 'ws://x', default: 'ws://127.0.0.1:8001/rpc', source: 'db', effect: 'restart', danger: false, pending_restart: true },
  { key: 'SCRIBE3_MEMORY_FABRIC_V1', category: 'flags', type: 'bool', label: '记忆织网检索 v1',
    value: false, default: false, source: 'default', effect: 'hot', danger: true, pending_restart: false },
]

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.settings.mockResolvedValue({ settings: ITEMS, categories: ['connection', 'llm', 'craft', 'flags', 'gateway'] })
  apiMock.putSetting.mockResolvedValue({})
})

describe('SettingsView', () => {
  it('元数据驱动渲染:分区导航 + 项 + 待重启黄标 + 来源徽章', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
    expect(screen.getByText('连接与服务')).toBeTruthy()
    fireEvent.click(screen.getByText('连接与服务'))
    expect(screen.getByText('重启后生效')).toBeTruthy()   // pending_restart 黄标
    expect(screen.getByText('已自定义')).toBeTruthy()      // source=db 徽章
  })

  it('danger 项修改需二次确认后才 PUT', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('灰度开关')).toBeTruthy())
    fireEvent.click(screen.getByText('灰度开关'))
    fireEvent.click(screen.getByRole('switch', { name: '记忆织网检索 v1' }))
    expect(apiMock.putSetting).not.toHaveBeenCalled()      // 先确认
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.putSetting).toHaveBeenCalledWith('SCRIBE3_MEMORY_FABRIC_V1', true))
  })

  it('恢复默认按钮调 resetSetting 并重拉', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    fireEvent.click(screen.getByRole('button', { name: '恢复默认:SurrealDB 地址' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledWith('SCRIBE3_SURREAL_URL'))
  })
})
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现 SettingsView + SettingField**

SettingsView 结构(样式 token 沿用仓内 `text-f13/text-ink/bg-surface/border-line` 体系;ConfirmDialog 复用 `ui/Dialog.jsx`):

```jsx
// scribe3/web/src/settings/SettingsView.jsx
import { useEffect, useState } from 'react'
import { api } from '../api'
import { SettingField } from './SettingField'
import { GatewaySection } from './GatewaySection'
import { BookSection } from './BookSection'
import { PrefsSection } from './PrefsSection'
import { AuditSection } from './AuditSection'

// 七分区 + 审计。backend 五类(connection/llm/craft/flags/gateway)由 /settings
// 元数据驱动;book/prefs/audit 为前端本地分区。
const SECTIONS = [
  { key: 'connection', label: '连接与服务' },
  { key: 'llm', label: 'LLM 与用量' },
  { key: 'craft', label: '工艺阈值' },
  { key: 'flags', label: '灰度开关' },
  { key: 'gateway', label: 'Hermes 网关' },
  { key: 'book', label: '本书设置' },
  { key: 'prefs', label: '个人偏好' },
  { key: 'audit', label: '变更历史' },
]

export function SettingsView({ work }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [section, setSection] = useState('llm')
  const reload = () => api.settings().then((r) => { setItems(r.settings); setError(null) }).catch((e) => setError(e))
  useEffect(() => { reload() }, [])
  if (error) return (
    <div className="h-full grid place-items-center text-f13 text-faint">
      <div>设置加载失败 <button className="text-brand cursor-pointer" onClick={reload}>重试</button></div>
    </div>
  )
  const byCat = (c) => (items || []).filter((i) => i.category === c)
  return (
    <div className="flex h-full min-h-0" data-testid="settings-view">
      <nav className="w-44 shrink-0 border-r border-line bg-surface/60 p-2" aria-label="设置分区">
        {SECTIONS.map((s) => (
          <button key={s.key} onClick={() => setSection(s.key)}
            className={`block w-full text-left rounded-md px-3 py-2 text-f13 cursor-pointer ${
              section === s.key ? 'bg-soft text-brand' : 'text-ink hover:bg-soft'}`}>
            {s.label}
          </button>
        ))}
      </nav>
      <div className="flex-1 min-w-0 overflow-auto p-6">
        <div className="mx-auto max-w-3xl">
          {section === 'gateway' && <GatewaySection items={byCat('gateway')} onChanged={reload} />}
          {section === 'book' && <BookSection work={work} />}
          {section === 'prefs' && <PrefsSection work={work} />}
          {section === 'audit' && <AuditSection />}
          {['connection', 'llm', 'craft', 'flags'].includes(section) &&
            byCat(section).map((it) => <SettingField key={it.key} item={it} onChanged={reload} />)}
        </div>
      </div>
    </div>
  )
}
```

(本任务先为 GatewaySection/BookSection/PrefsSection/AuditSection 建最小占位组件——各自 `export function X(){ return <div/> }` 的独立文件,后续任务逐个充实;避免本任务测试被未实现分区卡住。)

SettingField 要点(完整实现):

```jsx
// scribe3/web/src/settings/SettingField.jsx
import { useState } from 'react'
import { api } from '../api'
import { ConfirmDialog } from '../ui/Dialog.jsx'

const SOURCE_LABEL = { db: '已自定义', env: 'env', default: '默认' }

export function SettingField({ item, onChanged }) {
  const [draft, setDraft] = useState(null)          // null = 未编辑
  const [confirm, setConfirm] = useState(null)      // {value} 待确认
  const [err, setErr] = useState(null)
  const commit = async (value) => {
    try { await api.putSetting(item.key, value); setDraft(null); setErr(null); onChanged?.() }
    catch (e) { setErr(e?.body?.detail || e.message) }
  }
  const submit = (value) => item.danger ? setConfirm({ value }) : commit(value)
  const reset = () => setConfirm({ reset: true })
  return (
    <div className="flex items-start gap-3 border-b border-line py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-f13 text-ink">{item.label}</span>
          <span className="text-meta text-muted rounded bg-soft px-1.5">{SOURCE_LABEL[item.source]}</span>
          {item.pending_restart && <span className="text-meta rounded bg-amber-500/15 text-amber-600 px-1.5">重启后生效</span>}
          {item.effect === 'restart' && !item.pending_restart && <span className="text-meta text-faint">重启生效项</span>}
        </div>
        {item.desc && <div className="text-meta text-muted mt-0.5">{item.desc}</div>}
        {err && <div className="text-meta text-red-500 mt-0.5" role="alert">{err}</div>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {item.type === 'bool' ? (
          <button role="switch" aria-checked={item.value} aria-label={item.label}
            onClick={() => submit(!item.value)}
            className={`h-5 w-9 rounded-full transition-colors cursor-pointer ${item.value ? 'bg-brand' : 'bg-line'}`}>
            <span className={`block h-4 w-4 rounded-full bg-surface transition-transform ${item.value ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </button>
        ) : item.type === 'secret' ? (
          <input type="password" placeholder={item.is_set ? '已设置(输入以更换)' : '未设置'}
            className="w-48 rounded-md border border-line bg-surface px-2 py-1 text-f13"
            value={draft ?? ''} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => draft && submit(draft)} />
        ) : (
          <input type={item.type === 'str' ? 'text' : 'number'} step={item.type === 'float' ? '0.1' : '1'}
            min={item.min ?? undefined} max={item.max ?? undefined}
            className="w-48 rounded-md border border-line bg-surface px-2 py-1 text-f13 tnum"
            value={draft ?? String(item.value ?? '')} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              if (draft === null || draft === String(item.value)) return
              submit(item.type === 'int' ? parseInt(draft, 10) : item.type === 'float' ? parseFloat(draft) : draft)
            }} />
        )}
        {item.source === 'db' && (
          <button onClick={reset} aria-label={`恢复默认:${item.label}`} title={`恢复默认(${String(item.default)})`}
            className="text-meta text-faint hover:text-ink cursor-pointer">恢复默认</button>
        )}
      </div>
      <ConfirmDialog open={!!confirm} title={confirm?.reset ? `恢复默认「${item.label}」?` : `修改「${item.label}」?`}
        body={confirm?.reset ? `将回落为默认值 ${String(item.default)}` : `该项为高危设置,确认改为 ${String(confirm?.value)}`}
        danger confirmText="确认"
        onConfirm={() => { const c = confirm; setConfirm(null); c.reset ? api.resetSetting(item.key).then(onChanged) : commit(c.value) }}
        onClose={() => setConfirm(null)} />
    </div>
  )
}
```

(ConfirmDialog 的 props 形状以 `ui/Dialog.jsx` 实际导出为准——ChapterStudio.jsx 已用 `open/title/body/danger/confirmText/onConfirm/onClose`,照抄。)

- [ ] **Step 4: 跑测确认通过;Commit** `feat: 设置视图骨架+元数据驱动表单(来源徽章/待重启黄标/二次确认/恢复默认)`

### Task 14:网关区 GatewaySection(状态灯/文件编辑/重启)

**Files:**
- Create: `scribe3/web/src/settings/GatewaySection.jsx`(替换占位)
- Test: `scribe3/web/src/settings/__tests__/gatewaySection.test.jsx`(新)

- [ ] **Step 1: 写失败测试**

```jsx
// scribe3/web/src/settings/__tests__/gatewaySection.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  gatewayStatus: vi.fn(), gatewayFiles: vi.fn(), putGatewayFile: vi.fn(), gatewayRestart: vi.fn(),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { GatewaySection } from '../GatewaySection'

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.gatewayStatus.mockResolvedValue({ gateways: [
    { name: 'responses', api: 'http://127.0.0.1:8643/v1', profile: 'scribe3', online: true },
    { name: 'runs', api: 'http://127.0.0.1:8644/v1', profile: 'scribe3_write', online: false },
  ] })
  apiMock.gatewayFiles.mockResolvedValue({ files: [
    { id: 'scribe3/SOUL.md', path: '/x/SOUL.md', exists: true, content: '我是主编', sha256: 'h1' },
  ] })
  apiMock.putGatewayFile.mockResolvedValue({ sha256: 'h2' })
  apiMock.gatewayRestart.mockResolvedValue({ online: true })
})

describe('GatewaySection', () => {
  it('渲染状态灯与文件;保存走确认并带 base_sha256', async () => {
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('scribe3')).toBeTruthy())
    expect(screen.getByText('在线')).toBeTruthy()
    expect(screen.getByText('离线')).toBeTruthy()
    fireEvent.click(screen.getByText('scribe3/SOUL.md'))
    const ta = await screen.findByRole('textbox')
    fireEvent.change(ta, { target: { value: '我是新主编' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.putGatewayFile).toHaveBeenCalledWith('scribe3/SOUL.md', '我是新主编', 'h1'))
  })

  it('重启走确认;结果如实显示', async () => {
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('scribe3')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: '重启 scribe3' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.gatewayRestart).toHaveBeenCalledWith('scribe3'))
  })
})
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现 GatewaySection**

结构:上半——`items`(gateway 类设置项,复用 SettingField 渲染地址/profile);状态卡(轮询 `api.gatewayStatus()` 挂载拉一次 + 手动刷新按钮;绿点「在线」/灰点「离线」);中半——文件列表(点击展开 textarea 编辑器,`保存` 按钮 → ConfirmDialog → `api.putGatewayFile(id, content, sha256)`;409 时提示「文件已被外部修改」+ 重载按钮);下半——两个重启按钮(`重启 scribe3` / `重启 scribe3_write` → ConfirmDialog → `api.gatewayRestart(profile)`,结果 toast 如实显示 online 与日志路径)。文件编辑态本地 state:`{id, content, sha256}`;保存成功后更新 sha256。约 120 行,全部沿用 SettingField 的样式 token 与 ConfirmDialog。

- [ ] **Step 4: 跑测确认通过;Commit** `feat: 网关区(状态灯/SOUL.md·config 在线编辑/一键重启)`

### Task 15:本书设置区 + 个人偏好区 + 审计页

**Files:**
- Create: `scribe3/web/src/settings/BookSection.jsx`、`PrefsSection.jsx`、`AuditSection.jsx`(替换占位)
- Modify: `scribe3/web/src/App.jsx`(监听 `s3-pref-changed` 让主题热切)
- Test: `scribe3/web/src/settings/__tests__/settingsSections.test.jsx`(新)

- [ ] **Step 1: 写失败测试**

```jsx
// scribe3/web/src/settings/__tests__/settingsSections.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  intent: vi.fn(() => Promise.resolve({ total_word_goal: 100000, red_lines: '不写穿越' })),
  putIntent: vi.fn(() => Promise.resolve({})),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [
    { ts: '2026-07-12T10:00:00', key: 'craft.near_dup_sim', old: '0.7', new: '0.8' },
  ] })),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { BookSection } from '../BookSection'
import { PrefsSection } from '../PrefsSection'
import { AuditSection } from '../AuditSection'

describe('BookSection', () => {
  it('渲染 intent 并保存', async () => {
    render(<BookSection work="demo" />)
    await waitFor(() => expect(screen.getByLabelText('整稿目标字数').value).toBe('100000'))
    fireEvent.change(screen.getByLabelText('整稿目标字数'), { target: { value: '120000' } })
    fireEvent.blur(screen.getByLabelText('整稿目标字数'))
    await waitFor(() => expect(apiMock.putIntent).toHaveBeenCalledWith(
      expect.objectContaining({ total_word_goal: 120000 })))
  })
})

describe('PrefsSection', () => {
  beforeEach(() => localStorage.clear())
  it('护栏默认开;切换写 localStorage 并派发事件', () => {
    const seen = []
    window.addEventListener('s3-pref-changed', (e) => seen.push(e.detail?.key), { once: true })
    render(<PrefsSection work="demo" />)
    const sw = screen.getByRole('switch', { name: '写作护栏默认开启' })
    expect(sw.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(sw)
    expect(localStorage.getItem('scribe3:guardOn')).toBe('0')
    expect(seen).toContain('scribe3:guardOn')
  })
  it('脉搏静音清单可逐条解除', () => {
    localStorage.setItem('s3.pulse.mute.demo.promise', '1')
    render(<PrefsSection work="demo" />)
    fireEvent.click(screen.getByRole('button', { name: /解除静音/ }))
    expect(localStorage.getItem('s3.pulse.mute.demo.promise')).toBeNull()
  })
})

describe('AuditSection', () => {
  it('渲染审计行', async () => {
    render(<AuditSection />)
    await waitFor(() => expect(screen.getByText('craft.near_dup_sim')).toBeTruthy())
    expect(screen.getByText(/0\.7/)).toBeTruthy()
  })
})
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现三分区**

- **BookSection**:挂载 `api.intent()`;字段:reader_feeling(textarea)/emotional_arc(textarea)/red_lines(textarea)/overdue_threshold(number)/total_word_goal(number,label「整稿目标字数」)/daily_word_goal(number);失焦保存 `api.putIntent({...仅变更字段})`(MERGE 语义,与 NorthStarPanel 同惯例——若 api.js 无 intent/putIntent 方法名,以实际为准或补齐)。
- **PrefsSection**:声明式偏好清单渲染:

```jsx
const PREFS = [
  { key: 's3-theme', label: '深色主题', type: 'bool', on: 'dark', off: 'light', def: 'light' },
  { key: 's3.layout.v2', label: '四栏布局(关=旧三栏)', type: 'bool', on: '1', off: '0', def: '1' },
  { key: 'scribe3:guardOn', label: '写作护栏默认开启', type: 'bool', on: '1', off: '0', def: '1' },
  { key: 'scribe3:serif', label: '正文衬线字体', type: 'bool', on: '1', off: '0', def: '0' },
]
```

每项 role=switch;切换 `localStorage.setItem(key, next)` + `window.dispatchEvent(new CustomEvent('s3-pref-changed', { detail: { key } }))`。脉搏静音:扫 `Object.keys(localStorage)` 前缀 `s3.pulse.mute.{work}.`,列表 + 「解除静音」按钮 removeItem。布局类改动提示「刷新后生效」。
- **App.jsx**:主题 state 处加监听——`s3-pref-changed` 且 key==='s3-theme' 时 `setTheme(localStorage.getItem('s3-theme') || 'light')`(挂在既有 theme useEffect 旁)。
- **AuditSection**:`api.settingsAudit()` → 表格(时间/项/旧值→新值),「加载更多」按 offset 翻页。

- [ ] **Step 4: 跑测确认通过;Commit** `feat: 本书设置/个人偏好收拢/审计页三分区`

### Task 16:LLM 用量面板内嵌(llm 分区)

**Files:**
- Modify: `scribe3/web/src/settings/SettingsView.jsx`(llm 分区顶部内嵌用量卡)
- Test: `scribe3/web/src/settings/__tests__/settingsView.test.jsx`(追加)

- [ ] **Step 1: 追加失败测试**

```jsx
  it('llm 分区内嵌用量面板', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({ cap: 500, used: 42 }))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText(/今日已用/)).toBeTruthy())
    expect(screen.getByText(/42/)).toBeTruthy()
  })
```

- [ ] **Step 2: 跑测确认失败**

- [ ] **Step 3: 实现**:api.js 若无 `aiUsage: () => j(\`${BASE}/ai/usage\`)` 则补;SettingsView llm 分区顶部加卡片:`今日已用 {used} / 日帽 {cap}`,拉取失败静默隐藏(fail-soft)。`/ai/usage` 真实响应字段以 `curl -s :3321/ai/usage` 实测为准,测试 mock 同步。

- [ ] **Step 4: 跑测确认通过;Commit** `feat: 设置 llm 分区内嵌日帽用量面板`

---

## Phase 5:收口验收

### Task 17:全量回归 + 真机验收

- [ ] **Step 1: 后端全量**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests -q`
Expected: 全绿(基线 1566 + 本计划新增约 30)

- [ ] **Step 2: 前端全量**

Run: `cd scribe3/web && npx vitest run`
Expected: 全绿(基线 398 + 新增约 10)

- [ ] **Step 3: 真机验收(Playwright,pw.mjs 同款 harness;后端 :3321 前端 :3311 已跑)**

写临时脚本(放 `scribe3/web/__verify_settings.tmp.mjs`,验收完删除)依次验证并截图:
1. 顶栏齿轮 → 设置视图打开,七分区导航可见;
2. 工艺阈值区把 `craft.near_dup_sim` 改 0.9 → `curl -s :3321/settings` 确认 source=db → `curl -s -X POST ':3321/draft-check?...'`(或直接 python 调 `find_near_duplicate_paragraphs`)确认热生效;
3. 灰度开关区开 `SCRIBE3_CONTEXT_INSPECTOR_V1`(过二次确认)→ `curl -s :3321/capabilities` 反映为 true → 关回;
4. 网关区三状态灯与实际进程一致(8643 在线);
5. 改回 `craft.near_dup_sim` 恢复默认,审计页出现全部变更记录。

Expected: 全部通过,零 pageerror;验收后临时脚本删除,`craft.near_dup_sim` 与 flag 均已复原。

- [ ] **Step 4: Commit(如有验收产生的修复)** + 汇报:改了什么、验证结果、遗留项

### Task 18:文档与记忆收尾

- [ ] **Step 1:** `scribe3/DEPLOY.md` 加「设置中心」小节:配置优先级(DB→env→默认)、SQLite 路径、restart 项生效机制、网关文件备份位置。
- [ ] **Step 2:** 若 `/capabilities` 消费方(前端 ContextSnapshotContext)对 flags 语义有注释断言「仅 env」,同步更新注释为「设置中心(DB→env)」。grep `仅.*env|只.*env` 于 context 相关文件确认。
- [ ] **Step 3: Commit** `docs: 设置中心部署说明与注释对齐`

---

## 自审记录(写计划时已核)

- **Spec 覆盖**:七分区 ✓(connection/llm/craft/flags/gateway=Task 13、gateway 深化=Task 14、book/prefs/audit=Task 15、用量=Task 16);热生效 ✓(Task 5-8);restart 灌注 ✓(Task 3);全套防护 ✓(掩码 Task 1-2、恢复默认 Task 2/13、审计 Task 1/15、二次确认 Task 13-14、备份 Task 10);门禁 ✓(Task 4);真机验收 ✓(Task 17)。
- **类型一致性**:`get_setting/put_setting/reset_setting/settings_snapshot/apply_restart_overrides/invalidate_cache`(Task 2 定义,Task 3/5-8 引用);`list_files/write_file/StaleFileError/NotAllowedError`(Task 10);api.js 方法名(Task 12 定义,Task 13-16 引用)。
- **执行时校准点**(非占位,是防 drift 的显式指令):critique.py 行号、api.js fetch helper 名、`/ai/usage` 响应字段、ConfirmDialog props——均标注「以实际为准」并给出查证命令。

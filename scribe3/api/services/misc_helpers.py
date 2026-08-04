"""Misc API helpers (import jobs, codex field checks, small prompt blocks)."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, create_model

from scribe3.codex_schema import (
    all_storage_keys as codex_all_storage_keys,
    fields_for as codex_fields_for,
    secret_flag_key as codex_secret_flag_key,
)

# rebound: app_impl may define a richer mask; default placeholder for isolation.
_SECRET_MASK = "🔒"

_FACTION_TYPE_MAP: dict[str, type] = {
    "text": str, "textarea": str, "enum": str, "int": int, "bool": bool,
    "array<string>": list, "array<object>": list, "object": dict,
}


def _fact_item(f, reveal_secret: bool = False) -> dict:
    """命题序列化(单条,列表/单条端点共用)。
    批E-A1 无损化:回全字段 valid_from/valid_to/leak_markers,让前端能整行安全编辑
    (此前只回 value,现有命题只能 supersede/删除)。私密门控:secret 且未解锁时,
    value 与 leak_markers 一并屏蔽——leak_markers 是私密的"破绽词",本身即敏感,
    与 value 同级隐藏。"""
    hide = f.secret and not reveal_secret
    return {
        "id": f.id,
        "entity": f.entity_id,
        "attribute": f.attribute,
        "is_secret": f.secret,
        "value": None if hide else f.value,   # 私密 value 屏蔽,前端只知"此处有私密"
        "valid_from": f.valid_from,
        "valid_to": f.valid_to,
        "leak_markers": [] if hide else list(f.leak_markers or []),
    }


def _facts(fs, reveal_secret: bool = False):
    return [_fact_item(f, reveal_secret) for f in fs]


def _mask_field(row: dict, field: str, secret_field: str, reveal: bool) -> dict:
    """若 row[secret_field] 为 True 且未解锁,将 row[field] 替换为锁占位符。"""
    if row.get(secret_field) and not reveal:
        row = {**row, field: _SECRET_MASK}
    return row


def _search_excerpt(text: str, q: str, limit: int = 96) -> str:
    text = text or ""
    q = q or ""
    if not text:
        return ""
    idx = text.lower().find(q.lower()) if q else -1
    if idx < 0:
        return text[:limit]
    start = max(0, idx - 24)
    end = min(len(text), idx + len(q) + 48)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def _build_faction_in() -> type[BaseModel]:
    field_defs: dict[str, tuple] = {}
    for f in codex_fields_for("faction"):
        if f.key == "name":
            field_defs["name"] = (str, ...)
            continue
        py_type = _FACTION_TYPE_MAP.get(f.type, str)
        field_defs[f.key] = (py_type | None, None)
        if f.secret_capable:
            field_defs[codex_secret_flag_key(f.key)] = (bool | None, None)
    return create_model("FactionIn", __config__=ConfigDict(extra="allow"), **field_defs)


def _field_violations(fields, value: dict, prefix: str = "") -> list[str]:
    """按 codex_schema 字段定义校验取值合法性(enum 取值 + 数组元素类型),数据驱动、
    不硬编码字段名——注册表新增字段自动获得校验,无需在此加分支。返回违规描述列表,
    空即合法。app 层是唯一防线,漏掉的畸形值会一路走到 DB 炸成裸 500:

    - enum:顶层 + array<object>/object 内一层子字段(SurrealDB 对 FLEXIBLE 子字段不做
      取值校验,尽力而为:只探一层,不递归更深);
    - array<object> 的元素必须是对象:migration 083 把这些字段的 `.*` 定义为
      `TYPE object FLEXIBLE`,传字符串元素会 coercion 失败(Expected `object`);
    - array<string> 的元素必须是字符串:DB 类型是 `array<string>`,传 dict/int 同样
      coercion 失败。
    这两类元素类型错误 pydantic 拦不住——FactionIn 里它们只是裸 `list`,元素不带类型。
    """
    errors: list[str] = []
    for f in fields:
        if f.key not in value or value[f.key] is None:
            continue
        v = value[f.key]
        path = f"{prefix}{f.key}"
        if f.type == "enum" and f.enum is not None:
            if v not in f.enum:
                errors.append(f"{path}={v!r} 非法(合法值: {list(f.enum)})")
        elif f.type == "array<object>" and isinstance(v, list):
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    errors.append(
                        f"{path}[{i}] 应为对象,实际是 {type(item).__name__}: {item!r}")
                elif f.item_schema:
                    errors.extend(_field_violations(f.item_schema, item, prefix=f"{path}[{i}]."))
        elif f.type == "array<string>" and isinstance(v, list):
            for i, item in enumerate(v):
                if not isinstance(item, str):
                    errors.append(
                        f"{path}[{i}] 应为字符串,实际是 {type(item).__name__}: {item!r}")
        elif f.type == "object" and f.item_schema and isinstance(v, dict):
            errors.extend(_field_violations(f.item_schema, v, prefix=f"{path}."))
    return errors


def _import_job_get(job_id: str, work: str | None = None) -> dict | None:
    job = _import_jobs.get(job_id)
    if job is not None:
        return job
    # 持久层回源
    try:
        st = _store_for(work or "main")
        row = st.get_import_job(job_id)
        if not row:
            return None
        job = {
            "stage": row.get("stage") or "",
            "done": bool(row.get("done")),
            "total": int(row.get("total") or 0),
            "items": list(row.get("items") or []),
            "error": row.get("error") or "",
            "work": row.get("work") or work or "main",
            "source": row.get("source"),
        }
        _import_jobs[job_id] = job
        return job
    except Exception:
        return None


def _run_import(job_id: str, markdown: str, source: str | None, work: str = "main") -> None:
    """后台流水线:AI 切分打标摘要 → 结果存 job 待预览(不直接落库)。fail-soft。"""
    from scribe3.llm import hermes_complete
    from scribe3.material_import import split_and_tag
    job = _import_job_get(job_id, work) or {
        "stage": "", "done": False, "total": 0, "items": [], "error": "", "work": work}
    try:
        job["stage"] = "AI 切分打标中"
        job["work"] = work
        _import_job_save(job_id, job)
        job["items"] = split_and_tag(
            markdown, lambda p: hermes_complete(p, max_tokens=4000), source)
        job["total"] = len(job["items"])
        job["stage"] = "待预览确认"
    except Exception as e:
        job["stage"], job["error"] = "error", str(e)[:200]
    finally:
        job["done"] = True
        _import_job_save(job_id, job)


def _current_tail_block(st, chapter: int) -> str:
    """续写衔接块:当前章已写部分的末段(~400字),让 append 续写自然接上,不另起炉灶。
    若当前章无 prose(全新章)则返回空串,不干扰全新章的生成。"""
    try:
        ch = st.get_chapter(chapter)
        if not ch:
            return ""
        prose = ch.get("prose") or ""
        tail = prose[-400:].strip()
        if not tail:
            return ""
        return (
            "\n\n## 本章已写到这里(若续写,从此处自然接上,别另起炉灶/别重复)\n" + tail
        )
    except Exception:
        raise   # U-011: fail-loud(_current_tail_block 续写衔接)


def _focalizer_sincerity_block() -> str:
    """方案B任务13b:叙述者真诚视角硬约束(与 focalizer 限知引擎同向,是防
    "知情POV倒灌"的又一道文字层约束)——不管本章是否标注了反转/是否限知,
    叙述者的措辞都不得带上只有事后才成立的"知情腔",否则等于提前剧透。
    始终附带,不因参数为空而跳过(与 _final_reminder 同类,恒定注入)。"""
    return (
        "\n\n【叙述者真诚视角】叙述者必须真诚相信自己当前视角的认知,"
        "不得写出暗示后文反转的知情语气(如提前埋「果然」「殊不知」「万万没想到」式的"
        "预告腔,或用只有揭示之后才成立的措辞去描述当下场景)。"
    )


def _phase_role_block(phase: str) -> str:
    """阶段角色提示块(Phase0-BE2 四阶段):按写作阶段微调主编侧重。
    phase 空 → 返回空串(默认行为不变)。plan/draft/final 各加一句角色提示,挂 instructions 末尾。"""
    p = (phase or "").strip().lower()
    roles = {
        "plan": "## 阶段角色(规划期)\n你此刻是规划者:重事件因果与结构骨架——先把这章要发生什么、"
                "推动哪条线、落哪些伏笔/弧光说清,暂不雕字句。",
        "draft": "## 阶段角色(草稿期)\n你此刻是写手:重限知帧——严格贴焦点者所知所感铺陈,"
                 "先把场景与节拍落成连贯草稿,允许糙,但不得越界写焦点者不知之事。",
        "final": "## 阶段角色(正文期)\n你此刻是编审:重 QC——逐句收紧文风、清复读与 AI 腔、"
                 "查情感直说与限知泄露,把草稿打磨成定稿。",
    }
    block = roles.get(p)
    return f"\n\n{block}" if block else ""


def _loop_journal_path(work: str, chapter: int):
    """loop 编排 journal 路径(北极星任务4,台账 D-012)。与 _import_journal_path 的
    临时目录语义**刻意不同**:loop journal 兼任秘密审计(任务13)的抽查数据源
    ("哪章被自动回炉了几轮、为什么"),须持久——默认 ~/.scribe3-loop-journals/{work}/,
    SCRIBE3_LOOP_JOURNAL_DIR 可覆盖(测试指 tmp_path)。每次调用新开带纳秒时间戳的
    文件:重复 loop 同章不串账(journal 的 should_skip 语义只在单次运行内成立)。"""
    import time
    from pathlib import Path
    base = os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR") or os.path.expanduser("~/.scribe3-loop-journals")
    d = Path(base) / work
    d.mkdir(parents=True, exist_ok=True)
    return d / f"loop_ch{chapter}_{time.time_ns()}.json"


def _import_journal_path(work: str):
    """story-import 断点续跑 journal 文件路径(方案B任务24)。
    取舍记录:scribe3 一书一 DB(SurrealDB),没有天然的"该书的磁盘目录"可挂 journal——
    另起一套按书的文件系统目录纯为 journal 服务不值当。journal 的语义本就是"短生命周期的
    崩溃恢复提示"(见 pipeline_journal.py docstring),故落在系统临时目录、按 work 名隔离
    即可;可用 SCRIBE3_IMPORT_JOURNAL_DIR 环境变量覆盖(测试用它指到 tmp_path,避免与其他
    测试/其他 work 撞车)。"""
    import tempfile
    from pathlib import Path
    base = Path(os.environ.get("SCRIBE3_IMPORT_JOURNAL_DIR") or tempfile.gettempdir())
    return base / f"scribe3_import_{work}.json"


def _is_selection_candidate_version(ver: dict) -> bool:
    """终选只接受选择环候选留版:stage=candidate 或 label 前缀「选择环候选·」。
    击杀稿 label 含 ·filtered,不得定稿。"""
    label = str(ver.get("label") or "")
    if "·filtered" in label or label.endswith("filtered"):
        return False
    stage = ver.get("stage") or ""
    if stage == "candidate":
        return True
    # 兼容早期 stage=draft 但 label 已钉「选择环候选·」的留版
    return label.startswith("选择环候选·") or label.startswith("选择环候选")


def _pilot_llm_gen(st, work: str, seq: int, phase: str, ask: str, focalizer: str = "",
                   max_tokens: int | None = 1600) -> str:
    """pilot 生成通道:同一 _assemble_write_instructions 组装链(宪法:不另起简化 prompt)。"""
    outcome_binding = _WriteOutcomeBinding(st)
    ins = _assemble_write_instructions(
        st, chapter=seq, focalizer=focalizer, phase=phase,
        with_tools=False, seed_words=[], short_mode=False, work=work,
        envelope_trace=outcome_binding.manifest_trace, request_text=ask)
    return _collect_write(
        ask, ins, with_tools=False, on_terminal=outcome_binding.persist,
        text_mode=True, max_tokens=max_tokens,
    )


def _pilot_journal(work: str, seq: int):
    """审查 P1-5:pilot 审计留痕(每章一份 pilot_ch{n}.json,stage=pilot_ch{n}_{action})。
    fail-soft:journal 建不起来不阻塞编排。"""
    try:
        from scribe3.pipeline_journal import PipelineJournal
        base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
                or os.path.expanduser("~/.scribe3-loop-journals"))
        d = os.path.join(base, work)
        os.makedirs(d, exist_ok=True)
        return PipelineJournal(os.path.join(d, f"pilot_ch{seq}.json"))
    except Exception as e:
        logging.getLogger("scribe3").warning("pilot journal 建立失败(忽略): %s", e)
        return None


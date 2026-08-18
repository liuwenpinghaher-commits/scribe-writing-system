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


def _fact_item(f, reveal_secret: bool = False, *, extra: dict | None = None) -> dict:
    """命题序列化(单条,列表/单条端点共用)。
    批E-A1 无损化:回全字段 valid_from/valid_to/leak_markers,让前端能整行安全编辑
    (此前只回 value,现有命题只能 supersede/删除)。私密门控:secret 且未解锁时,
    value 与 leak_markers 一并屏蔽——leak_markers 是私密的"破绽词",本身即敏感,
    与 value 同级隐藏。

    PR-4 增量: source / bucket（classify_bucket）；extra 可附 knowers / reader_knows。
    支持 Fact 或 dict 行（history 路径）。
    """
    from scribe3.truth_surface import classify_bucket, row_source

    if isinstance(f, dict):
        fid = f.get("id") or (
            f"fact:{f['local']}" if f.get("local") else f.get("id")
        )
        if fid and not str(fid).startswith("fact:") and ":" not in str(fid):
            fid = f"fact:{fid}"
        entity = f.get("entity") or f.get("entity_id") or ""
        attribute = f.get("attribute") or ""
        secret = bool(f.get("secret") if "secret" in f else f.get("is_secret"))
        value = f.get("value")
        valid_from = f.get("valid_from")
        valid_to = f.get("valid_to")
        leak_markers = f.get("leak_markers") or []
        src = row_source(f)
        archived = bool(f.get("archived")) if f.get("archived") is not None else False
    else:
        fid = f.id
        entity = f.entity_id
        attribute = f.attribute
        secret = bool(f.secret)
        value = f.value
        valid_from = f.valid_from
        valid_to = f.valid_to
        leak_markers = list(f.leak_markers or [])
        src = getattr(f, "source", None)
        if src is not None:
            src = (str(src).strip() or None)
        archived = bool(getattr(f, "archived", False) or False)

    hide = secret and not reveal_secret
    item = {
        "id": fid,
        "entity": entity,
        "attribute": attribute,
        "is_secret": secret,
        "value": None if hide else value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "leak_markers": [] if hide else list(leak_markers or []),
        "source": src,
        "bucket": classify_bucket(src, attribute, is_secret=secret),
        "archived": archived,
    }
    if extra:
        item.update(extra)
    return item


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
    """阶段角色提示块:按写作阶段微调主编侧重（主要服务 chat_write assemble）。

    phase 空 → 返回空串。outline 与 plan 同句映射。覆盖地板写进合同，禁止「建议≥3 条」。
    world_write Hermes 主路径**不依赖**本函数（用 resolve instruction_suffix）。
    """
    p = (phase or "").strip().lower()
    # outline ↔ plan：前端偶发仍把 outline 映射为 plan
    if p == "outline":
        p = "plan"
    if p in ("plan", "beats", "design", "chapter_design"):
        p = "design"
    roles = {
        "design": "## 阶段角色(章设计)\n你此刻必须用 LLM 一次写出 14 槽章纲（禁令可空）+ ≥3 拍台阶。"
                "选择必须 A vs B；默认拍2演出这个选择，可用「选拍：N」改指定；禁止再发明第二个选择。"
                "动哪条线必须 promise:<id> 或 storyline:<id>。"
                "用 s3_generate_stage(stage=design) 或一次提交 spine+beats 的 s3_patch_chapter_plan。"
                "禁止只写大纲留下空节拍。禁止场面预演、禁止口号。",
        "plan": "## 阶段角色(规划期/大纲)\n你此刻必须用 LLM 写出 13 短槽章纲："
                "时空/在场/咬上章/本章要/挡/触发/升级/选择/决断/代价/信息差/动哪条线/钩。"
                "选择必须 A vs B；动哪条线必须 promise:<id> 或 storyline:<id>。"
                "禁止场面预演、禁止口号。用 s3_generate_stage 或 s3_patch_chapter_plan(chapter_spine)。",
        "beats": "## 阶段角色(节拍)\n你此刻必须用 LLM 写 ≥3 拍台阶：每拍只要/挡/变/付，全章至少一拍有选（A vs B）。"
                "GCD 是主合同，禁止千字进场。用 s3_generate_stage 或 s3_patch_chapter_plan 写 beats。禁止大纲切句充数。",
        "deduce": "## 阶段角色(演绎)\n你此刻必须用 LLM 写 scene_truth + 每人五层限知投影，抽出至少 1 条矿。"
                  "禁止摘录占位、禁止空白五栏。字数不是通过条件。"
                  "用 s3_patch_chapter_plan 写 scene_truth/deductions；"
                  "勿把场景真相写成 s3_add_fact 世界命题。",
        "draft": "## 阶段角色(排演)\n你此刻走场面排演：糙可改，只落 chapter.draft"
                 "（s3_save_chapter_draft），禁止写入 prose，禁止越界写焦点者不知之事。"
                 "字数不是通过条件。",
        "final": "## 阶段角色(正文期)\n你此刻写读者正文：冰山齐才开写。"
                 "材料全文在提示词里；读者正文另写，勿复读排演，守限知。"
                 "字数不是通过条件。用 s3_save_chapter 落 prose。",
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
    """pilot 生成通道。章设计只给一张纸；正文仍走组装链。"""
    from contextlib import nullcontext

    from scribe3.pipeline_trace_hooks import write_chain_guard

    outcome_binding = _WriteOutcomeBinding(st)
    from scribe3.api.services.write_stream import bind_pilot_trace
    nested = bind_pilot_trace(outcome_binding, st, work, seq, phase)
    ctx = nullcontext() if nested else write_chain_guard(st, outcome_binding.manifest_trace)
    with ctx:
        stg = (phase or "").strip().lower()
        if stg in ("design", "chapter_design", "outline", "plan", "beats"):
            from scribe3.stage_generate import planning_system_prompt
            ins = planning_system_prompt()
            from scribe3.deepseek_client import DeepSeekResponseError
            from scribe3.llm import default_model, hermes_complete_result
            text = ""
            used_model = default_model()
            last_err: Exception | None = None
            last_usage = None
            for _attempt in range(3):
                try:
                    result = hermes_complete_result(
                        ask, system=ins, model=used_model, max_tokens=max_tokens,
                        thinking="disabled",
                    )
                    text = (result.content if result is not None else "") or ""
                    used_model = getattr(result, "model", None) or used_model
                    last_usage = getattr(result, "usage", None)
                    if str(text).strip():
                        break
                except DeepSeekResponseError as exc:
                    last_err = exc
                    text = ""
                    continue
            if not str(text).strip():
                if last_err is not None:
                    raise last_err
                raise RuntimeError("规划补全为空")
            try:
                outcome_binding.persist({
                    "status": "completed",
                    "response_id": None,
                    "usage": last_usage,
                    "provider": {
                        "provider": "official_complete",
                        "phase": stg,
                        "model": used_model,
                    },
                    "model": used_model,
                })
            except Exception:
                pass
            return text
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


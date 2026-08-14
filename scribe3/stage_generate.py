"""冰山阶段生成合同：怎么问、怎么解析、怎么验收。生成必须走 LLM。

闸（薄了不让存、薄了不让开写）在 iceberg.py。
本模块是链：StageSpec + 解析 + stage_ready + thicken_*（llm_fn 必填）。

禁止：切句充数、逐字摘录当投影、空白五栏占位、见薄就 skip。
字数 = 信息覆盖地板，不是文学分，不进 may_claim_*。
"""
from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from scribe3.iceberg import (
    BEAT_EACH_FLOOR,
    BEAT_SUM_FLOOR,
    DEDUCTION_FLOOR,
    DRAFT_FLOOR,
    SYNOPSIS_FLOOR,
    cn_len,
    evaluate_iceberg,
)

# 分阶段「正式输出」预算。思考开着时 DeepSeekClient 再加 headroom，见 with_thinking_headroom。
STAGE_MAX_TOKENS: dict[str, int] = {
    "outline": 2048,
    "plan": 2048,
    "beats": 4096,
    "deduce": 8192,
    "draft": 16384,
    "final": 16384,
    "write": 16384,
}

OUTLINE_PARTS: tuple[str, ...] = ("日子", "必须发生", "因", "不能说", "章末未决")
BEAT_SLOTS: tuple[str, ...] = ("进场", "事件", "翻转", "出场", "水下")

_HEADING_LINE = re.compile(
    r"^\s{0,3}(?:#{1,3}|【)\s*(?P<h>.+?)(?:】)?\s*$",
    re.MULTILINE,
)
_BEAT_SPLIT = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:拍\s*|第)\s*(\d+)\s*(?:拍|场)?\s*[:：.、)]?\s*",
    re.IGNORECASE,
)
_FENCE = re.compile(r"^```(?:\w+)?\s*|\s*```$", re.MULTILINE)
_WS = re.compile(r"\s+")

LlmFn = Callable[..., str]
PersistFn = Callable[[dict], Any]


def normalize_stage(phase: str | None) -> str:
    p = (phase or "").strip().lower()
    if p == "plan":
        return "outline"
    if p in ("write", "prose"):
        return "final"
    return p


def stage_max_tokens(phase: str | None) -> int:
    p = (phase or "").strip().lower()
    return int(STAGE_MAX_TOKENS.get(p) or STAGE_MAX_TOKENS.get(normalize_stage(p), 4096))


def stage_spec(phase: str | None) -> dict[str, Any]:
    """给生成器用的完整合同；assemble 只取 short_kernel。"""
    p = normalize_stage(phase)
    if p == "outline":
        return {
            "stage": "outline",
            "floor": SYNOPSIS_FLOOR,
            "persist_tool": "s3_patch_chapter_plan",
            "persist_field": "synopsis",
            "max_tokens": STAGE_MAX_TOKENS["outline"],
            "must_parts": list(OUTLINE_PARTS),
            "short_kernel": (
                f"【大纲合同】因果大纲 ≥{SYNOPSIS_FLOOR} 字，必须含：日子、必须发生、"
                f"因→果、不能说、章末未决。禁止一句口号。落库 s3_patch_chapter_plan(synopsis)。"
            ),
            "ask": _OUTLINE_ASK,
        }
    if p == "beats":
        return {
            "stage": "beats",
            "floor_each": BEAT_EACH_FLOOR,
            "floor_sum": BEAT_SUM_FLOOR,
            "min_count": 3,
            "persist_tool": "s3_patch_chapter_plan",
            "persist_field": "beats",
            "max_tokens": STAGE_MAX_TOKENS["beats"],
            "must_parts": list(BEAT_SLOTS),
            "short_kernel": (
                f"【节拍合同】≥3 拍；每拍场面纸 ≥{BEAT_EACH_FLOOR} 字（进场/事件/翻转/出场/水下）；"
                f"合计 ≥{BEAT_SUM_FLOOR}。GCD 短字段不能代替 text。落库 s3_patch_chapter_plan(beats)。"
            ),
            "ask": _BEATS_ASK,
        }
    if p == "deduce":
        return {
            "stage": "deduce",
            "floor": DEDUCTION_FLOOR,
            "persist_tool": "s3_patch_chapter_plan",
            "persist_field": "deductions",
            "max_tokens": STAGE_MAX_TOKENS["deduce"],
            "short_kernel": (
                f"【演绎合同】scene_truth + 每人五层限知（看到/听到、知道、以为、做了/说了、没察觉的）；"
                f"投影合计 ≥{DEDUCTION_FLOOR}。落库 s3_patch_chapter_plan。禁止摘录占位。"
            ),
            "ask": _DEDUCE_ASK,
        }
    if p == "draft":
        return {
            "stage": "draft",
            "floor": DRAFT_FLOOR,
            "persist_tool": "s3_save_chapter_draft",
            "persist_field": "draft",
            "max_tokens": STAGE_MAX_TOKENS["draft"],
            "short_kernel": (
                f"【排演合同】按节拍走一遍场面，糙可改，≥{DRAFT_FLOOR} 字。"
                f"只落 chapter.draft（s3_save_chapter_draft），禁止写入 prose。"
            ),
            "ask": _DRAFT_ASK,
        }
    if p == "final":
        return {
            "stage": "final",
            "floor": 5000,
            "persist_tool": "s3_save_chapter",
            "persist_field": "prose",
            "max_tokens": STAGE_MAX_TOKENS["final"],
            "short_kernel": (
                "【正文合同】冰山齐才开写。材料全文在提示词里；读者正文另写，"
                "勿复读排演，守限知。水面可见字 ≥5000。落库 s3_save_chapter。"
            ),
            "ask": _FINAL_ASK,
        }
    return {
        "stage": p or "",
        "short_kernel": "",
        "max_tokens": 4096,
        "ask": "",
    }


def stage_craft_kernel(phase: str | None) -> str:
    """assemble 短核（≤400）。完整合同不进 final。"""
    txt = str(stage_spec(phase).get("short_kernel") or "")
    return txt[:400]


_NEED_PREV: dict[str, tuple[str, ...]] = {
    "outline": (),
    "beats": ("synopsis",),
    "deduce": ("synopsis", "beats"),
    "draft": ("synopsis", "beats", "deduction"),
    "final": ("synopsis", "beats", "deduction", "draft"),
}


def _missing_bucket(mid: str) -> str:
    if mid in ("beat_count", "beat_each", "beat_sum"):
        return "beats"
    return mid


def stage_ready(ch: Mapping[str, Any] | None, stage: str | None) -> dict[str, Any]:
    """进下一阶段：只验已经该齐的上一层。加厚本阶段不走这里。"""
    st = normalize_stage(stage)
    needed = _NEED_PREV.get(st)
    if needed is None:
        return {"ok": True, "missing": [], "stage": st, "message": ""}
    ev = evaluate_iceberg(ch if isinstance(ch, dict) else {}, for_phase="final")
    missing = [
        m for m in (ev.get("missing") or [])
        if _missing_bucket(str(m.get("id") or "")) in needed
    ]
    ok = not missing
    bits = [f"{m.get('id')} {m.get('got')}<{m.get('need')}" for m in missing]
    return {
        "ok": ok,
        "missing": missing,
        "stage": st,
        "measures": ev.get("measures") or {},
        "message": (
            "" if ok else f"还不能进{st}：上一阶段未齐：" + "；".join(bits)
        ),
        "code": "" if ok else "stage_not_ready",
    }


def stage_not_ready_http(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "code": report.get("code") or "stage_not_ready",
        "message": report.get("message") or "上一阶段未齐",
        "missing": list(report.get("missing") or []),
        "stage": report.get("stage"),
        "hint": "先让主编把上一阶段用 LLM 写厚；或 skip_iceberg / danger_draft 旁路。",
    }


def iceberg_ok_for(ch: Mapping[str, Any] | None, field: str) -> bool:
    """该块覆盖是否已达地板（有则 skip 加厚）。"""
    ev = evaluate_iceberg(ch if isinstance(ch, dict) else {}, for_phase="final")
    miss = {str(m.get("id")) for m in (ev.get("missing") or [])}
    if field == "synopsis":
        return "synopsis" not in miss
    if field == "beats":
        return not ({"beat_count", "beat_each", "beat_sum"} & miss)
    if field == "deduction":
        return "deduction" not in miss
    if field == "draft":
        return "draft" not in miss
    return False


# ── 解析 ──────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    return _FENCE.sub("", text or "").strip()


def parse_outline_payload(text: str) -> dict[str, Any]:
    body = _strip_fence(text)
    found = []
    for part in OUTLINE_PARTS:
        if part in body:
            found.append(part)
    cn = cn_len(body)
    return {
        "synopsis": body,
        "parts": found,
        "cn": cn,
        "ok": cn >= SYNOPSIS_FLOOR,
        "warn_parts": [p for p in OUTLINE_PARTS if p not in found],
        "source": "llm",
    }


def _extract_slot(block: str, names: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        m = re.search(
            rf"(?:^|\n)\s*(?:#+\s*)?{re.escape(name)}\s*[:：]?\s*(.+?)(?=\n\s*(?:#+\s*)?(?:{'|'.join(map(re.escape, names))})\s*[:：]|\Z)",
            block,
            re.S,
        )
        if m:
            out[name] = m.group(1).strip()
    return out


def parse_beats_payload(text: str) -> dict[str, Any]:
    body = _strip_fence(text)
    chunks: list[str] = []
    parts = [p for p in _BEAT_SPLIT.split(body) if p is not None]
    # split keeps capture groups: [preamble, n1, body1, n2, body2, ...]
    if len(parts) >= 3:
        i = 1
        while i + 1 < len(parts):
            chunk = str(parts[i + 1]).strip()
            if chunk:
                chunks.append(chunk)
            i += 2
    if not chunks:
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if cn_len(p) >= 80]
        chunks = paras
    beats: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks, 1):
        slots = _extract_slot(chunk, BEAT_SLOTS)
        gcd = _extract_slot(chunk, ("目标", "冲突", "结果", "代价", "钩子"))
        text_body = chunk.strip()
        item: dict[str, Any] = {"id": f"b{i}", "text": text_body}
        if slots.get("事件"):
            item["goal"] = slots["事件"][:80]
        if gcd.get("目标"):
            item["goal"] = gcd["目标"][:80]
        if gcd.get("冲突"):
            item["conflict"] = gcd["冲突"][:80]
        if gcd.get("结果"):
            item["turn"] = gcd["结果"][:80]
        if gcd.get("代价"):
            item["cost"] = gcd["代价"][:80]
        if gcd.get("钩子"):
            item["hook"] = gcd["钩子"][:80]
        beats.append(item)
    lens = [cn_len(b.get("text")) for b in beats]
    thin = [i + 1 for i, n in enumerate(lens) if n < BEAT_EACH_FLOOR]
    return {
        "beats": beats,
        "cn": sum(lens),
        "each": lens,
        "ok": (
            len(beats) >= 3
            and not thin
            and sum(lens) >= BEAT_SUM_FLOOR
        ),
        "thin": thin,
        "source": "llm",
    }


def parse_deduce_payload(text: str, *, involved: list[str] | None = None) -> dict[str, Any]:
    from scribe3.deduce_helpers import DEDUCTION_HEADINGS, normalize_role_id

    body = _strip_fence(text)
    truth = ""
    deds: list[dict[str, Any]] = []
    sections = re.split(r"(?=(?:^|\n)\s*#{1,3}\s+)", "\n" + body)
    current_role = ""
    current_buf: list[str] = []

    def flush_role() -> None:
        nonlocal current_role, current_buf
        prose = "\n".join(current_buf).strip()
        if current_role and prose:
            deds.append({
                "character_id": normalize_role_id(current_role),
                "character_name": current_role.split(":")[-1],
                "prose": prose,
            })
        current_role = ""
        current_buf = []

    for sec in sections:
        raw = sec.strip()
        if not raw:
            continue
        first = raw.splitlines()[0]
        title = re.sub(r"^#+\s*", "", first).strip()
        rest = "\n".join(raw.splitlines()[1:]).strip()
        if any(k in title for k in ("场景真相", "scene_truth", "真相")):
            flush_role()
            truth = rest or title
            continue
        if title and not any(h in title for h in DEDUCTION_HEADINGS):
            flush_role()
            current_role = title
            current_buf = [raw]
        elif current_role:
            current_buf.append(raw)
        elif not truth:
            truth = raw
    flush_role()
    if not deds and involved:
        # 整篇当作单人投影（测试/短输出）
        only = involved[0]
        deds = [{
            "character_id": normalize_role_id(only),
            "character_name": str(only).split(":")[-1],
            "prose": body,
        }]
    dsum = sum(cn_len(d.get("prose")) for d in deds)
    return {
        "scene_truth": truth,
        "deductions": deds,
        "cn": dsum,
        "ok": dsum >= DEDUCTION_FLOOR,
        "source": "llm",
    }


def parse_draft_payload(text: str) -> dict[str, Any]:
    body = _strip_fence(text)
    cn = cn_len(body)
    return {"draft": body, "cn": cn, "ok": cn >= DRAFT_FLOOR, "source": "llm"}


def draft_full_block(draft: str | None) -> str:
    """排演全文进 draft/final 提示词；纪律是另写，不是截前 2400。"""
    from scribe3.iceberg import clip_for
    raw = (draft or "").strip()
    if not raw:
        return ""
    body = clip_for("draft", raw)
    return (
        "【排演全文·禁止复读当定稿】下面是场面走位，读者正文必须另写，"
        "不得逐句搬运；限知仍守焦点者所知。\n"
        + body
    )


def draft_tip(draft: str | None, *, cap: int = 12000) -> str:
    """兼容旧名：现为全文注入。"""
    return draft_full_block(draft)


# ── 生成提示 ──────────────────────────────────────────────────────

def _ctx_bits(ch: Mapping[str, Any] | None) -> str:
    meta = ch if isinstance(ch, dict) else {}
    syn = str(meta.get("synopsis") or "").strip()
    beats = meta.get("beats") or []
    beat_lines = []
    from scribe3.iceberg import clip_for
    for i, b in enumerate(beats, 1):
        t = b.get("text") if isinstance(b, dict) else str(b or "")
        beat_lines.append(f"{i}. {clip_for('beat', t or '')}")
    truth = str(meta.get("scene_truth") or "").strip()
    involved = meta.get("involved_characters") or []
    bits = []
    if syn:
        bits.append("现有大纲（可改厚，勿缩成口号）：\n" + clip_for("synopsis", syn))
    if beat_lines:
        bits.append("现有节拍（薄拍必须加厚覆盖）：\n" + "\n".join(beat_lines))
    if truth:
        bits.append("场景真相：\n" + clip_for("scene_truth", truth))
    if involved:
        bits.append("在场：" + "、".join(str(x) for x in involved))
    return "\n\n".join(bits)


_OUTLINE_ASK = (
    "写本章因果大纲，不是一句剧情简介。必须用小标题写出：\n"
    "1. 日子：村里/场上正在过什么（具体，能看见）\n"
    "2. 必须发生：那一下（动作，不是主题词）\n"
    "3. 因 → 果：为什么非发生不可\n"
    "4. 不能说：本章禁令\n"
    "5. 章末未决：留给下一章的动作或把柄\n"
    f"全文去掉空白后必须 ≥{SYNOPSIS_FLOOR} 字。禁止完成灯、禁止「材料够了」、禁止口号当全文。\n"
    "只输出大纲正文。"
)

_BEATS_ASK = (
    "把本章拆成 ≥3 拍场面纸。每拍用下列结构，且每拍正文去掉空白后 "
    f"≥{BEAT_EACH_FLOOR} 字，合计 ≥{BEAT_SUM_FLOOR} 字：\n"
    "## 拍1\n进场：谁在哪，空气里有什么\n事件：必须发生的那一下\n"
    "翻转：相对上拍升级或反转\n出场：留下什么物件/把柄/未说完的话\n"
    "水下：本拍不写进正文、作者必须知道的一句\n"
    "禁止一行口号。GCD 短句只能当附注。只输出场面纸。"
)

_DEDUCE_ASK = (
    "先写 ## 场景真相（全知冷叙，客观发生）。再为每个在场角色写一篇限知投影，"
    "标题用角色名，其下五个小标题：看到/听到、知道、以为(误读)、做了/说了、没察觉的。\n"
    f"全部投影去掉空白后合计 ≥{DEDUCTION_FLOOR} 字。禁止逐字摘录充数，禁止「未能确认」五栏占位。\n"
    "只输出真相与投影。"
)

_DRAFT_ASK = (
    "按节拍把场面走一遍：糙、可越界待改，用来发现节拍漏洞。"
    f"去掉空白后 ≥{DRAFT_FLOOR} 字。这是排演，不是读者正文。只输出排演正文。"
)

_FINAL_ASK = (
    "写读者正文。大纲/节拍/演绎/排演全文都在材料里；读者正文必须另写，"
    "禁止复读排演句，守限知横幅。水面可见字 ≥5000。只输出正文。"
)


def build_stage_prompt(
    stage: str,
    ch: Mapping[str, Any] | None,
    *,
    seq: int | None = None,
    extra: str = "",
    strict: bool = False,
    previous: str = "",
    bible: str = "",
) -> str:
    spec = stage_spec(stage)
    ask = str(spec.get("ask") or "")
    if strict:
        ask = "【重试·必须达到覆盖地板，禁止短稿】\n" + ask
    bits = [ask]
    if seq:
        bits.append(f"章号：第{seq}章")
    ctx = _ctx_bits(ch)
    if ctx:
        bits.append(ctx)
    if extra:
        bits.append(extra.strip())
    if (bible or "").strip():
        bits.append(str(bible).strip())
    if previous:
        bits.append("上次输出过短或结构不够，不要复述口号，按合同重写：\n" + previous[:800])
    return "\n\n".join(bits)


def _bible_for_thicken(st, work, ch, extra: str, focalizer: str, seq) -> str:
    """有 store 才挂点名圣经；无 st 返回空串（单测字节兼容）。"""
    if st is None:
        return ""
    names: list[str] = []
    for x in list((ch or {}).get("involved_characters") or []):
        if isinstance(x, dict):
            names.append(str(x.get("name") or x.get("id") or ""))
        else:
            names.append(str(x or ""))
    request_text = " ".join(p for p in (extra or "", *names) if p)
    from scribe3.api.services.write_assemble_blocks import _codex_segments
    from scribe3.iceberg import named_pack_soft_cap
    named, cards, _stats = _codex_segments(
        st, reveal=True, focalizer=focalizer or "",
        chapter=seq, for_generation=True,
        request_text=request_text, work=work,
        named_soft_cap=named_pack_soft_cap(work=work),
    )
    return "\n".join(p for p in (named, cards) if p)


def _call_llm(llm_fn: LlmFn | None, prompt: str, max_tokens: int) -> str:
    if llm_fn is None or not callable(llm_fn):
        raise ValueError("stage_generate 必须提供 llm_fn，禁止模板/切句回退")
    try:
        raw = llm_fn(prompt, max_tokens)
    except TypeError:
        raw = llm_fn(prompt)
    return str(raw or "").strip()


def _blocked_or_none(fields: dict) -> dict[str, Any] | None:
    from scribe3.iceberg import persist_fields_blocked
    return persist_fields_blocked(fields)


def thicken_outline(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    if iceberg_ok_for(ch, "synopsis"):
        return {
            "skipped": "大纲已达覆盖地板，不覆盖",
            "source": "existing",
            "synopsis": (ch or {}).get("synopsis"),
        }
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    prompt = build_stage_prompt("outline", ch, seq=seq, extra=extra, bible=bible)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["outline"])
    parsed = parse_outline_payload(raw)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt("outline", ch, seq=seq, extra=extra, strict=True, previous=raw, bible=bible),
            STAGE_MAX_TOKENS["outline"],
        )
        parsed = parse_outline_payload(raw)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": SYNOPSIS_FLOOR,
            "message": f"大纲 LLM 仍不足 {SYNOPSIS_FLOOR} 字（got={parsed['cn']}），禁止切句/口号落库",
            "parsed": parsed,
        }
    fields = {"synopsis": parsed["synopsis"]}
    blocked = _blocked_or_none(fields)
    if blocked:
        return {"ok": False, "code": blocked["code"], "message": blocked["message"], "source": "llm"}
    if persist_fn:
        persist_fn(fields)
    return {"ok": True, "source": "llm", **fields, "cn": parsed["cn"], "parts": parsed["parts"]}


def thicken_beats(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "beats")
    if not ready["ok"]:
        return {"ok": False, **ready}
    if iceberg_ok_for(ch, "beats"):
        return {
            "skipped": "节拍已达覆盖地板，不覆盖",
            "source": "existing",
            "beats": (ch or {}).get("beats"),
        }
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    prompt = build_stage_prompt("beats", ch, seq=seq, extra=extra, bible=bible)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["beats"])
    parsed = parse_beats_payload(raw)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt("beats", ch, seq=seq, extra=extra, strict=True, previous=raw, bible=bible),
            STAGE_MAX_TOKENS["beats"],
        )
        parsed = parse_beats_payload(raw)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "thin": parsed.get("thin"),
            "need": {"each": BEAT_EACH_FLOOR, "sum": BEAT_SUM_FLOOR, "count": 3},
            "message": "节拍 LLM 未达每拍 500 / 合计 2000，禁止大纲切句充数",
            "parsed": parsed,
        }
    fields = {"beats": parsed["beats"]}
    blocked = _blocked_or_none(fields)
    if blocked:
        return {"ok": False, "code": blocked["code"], "message": blocked["message"], "source": "llm"}
    if persist_fn:
        persist_fn(fields)
    return {"ok": True, "source": "llm", **fields, "cn": parsed["cn"]}


def thicken_deduce(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "deduce")
    if not ready["ok"]:
        return {"ok": False, **ready}
    if iceberg_ok_for(ch, "deduction"):
        return {
            "skipped": "演绎已达覆盖地板，不覆盖",
            "source": "existing",
            "deductions": (ch or {}).get("deductions"),
        }
    involved = list((ch or {}).get("involved_characters") or [])
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    prompt = build_stage_prompt("deduce", ch, seq=seq, extra=extra, bible=bible)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["deduce"])
    parsed = parse_deduce_payload(raw, involved=involved)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt("deduce", ch, seq=seq, extra=extra, strict=True, previous=raw, bible=bible),
            STAGE_MAX_TOKENS["deduce"],
        )
        parsed = parse_deduce_payload(raw, involved=involved)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": DEDUCTION_FLOOR,
            "message": "演绎 LLM 合计未达 5000 字，禁止摘录/空白五栏充数",
            "parsed": parsed,
        }
    fields: dict[str, Any] = {"deductions": parsed["deductions"]}
    if parsed.get("scene_truth"):
        fields["scene_truth"] = parsed["scene_truth"]
    blocked = _blocked_or_none(fields)
    if blocked:
        return {"ok": False, "code": blocked["code"], "message": blocked["message"], "source": "llm"}
    if persist_fn:
        persist_fn(fields)
    return {"ok": True, "source": "llm", **fields, "cn": parsed["cn"]}


def thicken_draft(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "draft")
    if not ready["ok"]:
        return {"ok": False, **ready}
    if iceberg_ok_for(ch, "draft"):
        return {
            "skipped": "排演已达覆盖地板，不覆盖",
            "source": "existing",
            "draft": (ch or {}).get("draft") or (ch or {}).get("draft_prose"),
        }
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    prompt = build_stage_prompt("draft", ch, seq=seq, extra=extra, bible=bible)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["draft"])
    parsed = parse_draft_payload(raw)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt("draft", ch, seq=seq, extra=extra, strict=True, previous=raw, bible=bible),
            STAGE_MAX_TOKENS["draft"],
        )
        parsed = parse_draft_payload(raw)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": DRAFT_FLOOR,
            "message": "排演 LLM 未达 10000 字，禁止把短稿当 chapter.draft",
            "parsed": parsed,
        }
    if persist_fn:
        persist_fn({"draft": parsed["draft"]})
    return {"ok": True, "source": "llm", "draft": parsed["draft"], "cn": parsed["cn"]}


def thicken_stage(
    stage: str,
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    kind = normalize_stage(stage)
    fns = {
        "outline": thicken_outline,
        "beats": thicken_beats,
        "deduce": thicken_deduce,
        "draft": thicken_draft,
    }
    fn = fns.get(kind)
    if fn is None:
        return {"ok": False, "code": "unknown_stage", "message": f"无独立生成链: {stage}"}
    return fn(
        ch, llm_fn=llm_fn, persist_fn=persist_fn, seq=seq, extra=extra,
        st=st, work=work, focalizer=focalizer,
    )

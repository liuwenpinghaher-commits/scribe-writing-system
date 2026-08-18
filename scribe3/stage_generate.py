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
    PROSE_SURFACE,
    SYNOPSIS_FLOOR,
    cn_len,
    evaluate_iceberg,
)

# 分阶段「正式输出」预算。思考开着时 DeepSeekClient 再加 headroom，见 with_thinking_headroom。
STAGE_MAX_TOKENS: dict[str, int] = {
    "outline": 2048,
    "plan": 2048,
    "design": 4096,
    "beats": 4096,
    "deduce": 8192,
    "draft": 16384,
    "final": 16384,
    "write": 16384,
}

OUTLINE_PARTS: tuple[str, ...] = (
    "时空", "在场", "咬上章", "本章要", "挡", "触发", "升级",
    "选择", "决断", "代价", "信息差", "动哪条线", "钩", "禁令",
)
OUTLINE_PARTS_V1: tuple[str, ...] = ("日子", "必须发生", "因", "不能说", "章末未决")
BEAT_SLOTS: tuple[str, ...] = ("要", "挡", "变", "付", "选", "水下")
BEAT_SLOTS_V1: tuple[str, ...] = ("进场", "事件", "翻转", "出场", "水下")
_BEAT_LABEL_TO_KEY = {
    "要": "goal", "挡": "conflict", "变": "turn", "付": "cost",
    "选": "choice", "水下": "underwater",
    "事件": "goal", "翻转": "turn", "出场": "cost",
}

_HEADING_LINE = re.compile(
    r"^\s{0,3}(?:#{1,3}|【)\s*(?P<h>.+?)(?:】)?\s*$",
    re.MULTILINE,
)
_BEAT_SPLIT = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:拍\s*|第)\s*(\d+)\s*(?:拍|场)?\s*[:：.、)]?\s*",
    re.IGNORECASE,
)
_FENCE = re.compile(r"^```(?:\w+)?\s*|\s*```$", re.MULTILINE)
_PROPOSAL_FENCE = re.compile(r"⟦/?PROPOSAL[^⟧]*⟧")
_WS = re.compile(r"\s+")

LlmFn = Callable[..., str]
PersistFn = Callable[[dict], Any]


def normalize_stage(phase: str | None) -> str:
    p = (phase or "").strip().lower()
    if p == "plan":
        p = "outline"
    if p in ("write", "prose"):
        return "final"
    if p in ("chapter_design", "outline", "beats"):
        return "design"
    return p


def stage_skips_editor_chrome(phase: str | None) -> bool:
    """大纲/节拍/演绎/排演：不要灌主编讨论与改稿说明书。正文 final 仍保留身份。"""
    return normalize_stage(phase) in ("outline", "beats", "design", "deduce", "draft")


def stage_skips_drama_vacuum(phase: str | None) -> bool:
    """规划/演绎阶段合同本就空，灌「缺目标」会和正在生成的场面打架。"""
    return normalize_stage(phase) in ("outline", "beats", "design", "deduce")


def stage_skips_craft_engine(phase: str | None) -> bool:
    """规划/演绎不要灌身体先行/温度曲线；排演和正文才要。"""
    return normalize_stage(phase) in ("outline", "beats", "design", "deduce")


def stage_skips_structure_diversity(phase: str | None) -> bool:
    """规划/演绎不要灌结构多样性红线。"""
    return normalize_stage(phase) in ("outline", "beats", "design", "deduce")


def stage_skips_continue_snapshot(phase: str | None) -> bool:
    """设计/大纲/节拍不要灌续写快照。"""
    return normalize_stage(phase) in ("outline", "beats", "design")


def stage_is_planning_paper(phase: str | None) -> bool:
    """章设计只给一张纸，不灌写正文的说明书。"""
    return normalize_stage(phase) in ("outline", "beats", "design", "plan", "chapter_design")


def planning_system_prompt() -> str:
    return (
        "你在写这一章怎么发生，不是读者正文。"
        "先看硬卡上的本章责任：该在的人必须各做各的事；只办那一件事；世界收的账必须是那一笔。"
        "第1章写章开始前的状态，不要假装有上一章。"
        "后面的章接住上一章没做完的事。"
        "换了地方，让人看得出他怎么到的。"
        "不要编户口里没有的人。"
        "只输出标签行。"
    )


def stage_skips_secret_guard(phase: str | None) -> bool:
    """设计纸上禁止出现密语里的锁眼/拨锁。"""
    return stage_is_planning_paper(phase)


def stage_max_tokens(phase: str | None) -> int:
    p = (phase or "").strip().lower()
    return int(STAGE_MAX_TOKENS.get(p) or STAGE_MAX_TOKENS.get(normalize_stage(p), 4096))


def stage_spec(phase: str | None) -> dict[str, Any]:
    """给生成器用的完整合同；assemble 只取 short_kernel。"""
    p = normalize_stage(phase)
    if p == "design":
        return {
            "stage": "design",
            "persist_tool": "s3_patch_chapter_plan",
            "persist_field": "chapter_spine+beats",
            "max_tokens": STAGE_MAX_TOKENS["design"],
            "must_parts": list(OUTLINE_PARTS) + ["拍"],
            "short_kernel": (
                "【章设计合同】一次写出 14 槽章纲（禁令可空）+ ≥3 拍台阶。"
                "章：选择必须 A vs B；动哪条线必须 promise:<id>/storyline:<id>；钩悬着。"
                "拍：默认拍2演出上面那个 A vs B；可用「选拍：N」改指定；每拍只要/挡/变/付；禁止再发明第二个选择。"
                "落库 chapter_spine + beats。禁止场面预演。"
            ),
            "ask": _DESIGN_ASK,
        }
    if p == "outline":
        return {
            "stage": "outline",
            "floor": SYNOPSIS_FLOOR,
            "persist_tool": "s3_patch_chapter_plan",
            "persist_field": "synopsis",
            "max_tokens": STAGE_MAX_TOKENS["outline"],
            "must_parts": list(OUTLINE_PARTS),
            "short_kernel": (
                "【大纲合同】13 短槽章纲（时空/在场/咬上章/要/挡/触发/升级/选择/决断/代价/信息差/动哪条线/钩）。"
                "选择必须 A vs B；动哪条线必须 promise:<id> 或 storyline:<id>。禁止场面预演。落库 chapter_spine。"
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
                "【节拍合同】≥3 拍台阶；每拍只写要/挡/变/付，全章至少一拍有选（A vs B）。"
                "必须兑现本章选择/决断/代价，禁止复演上章 GCD。禁止千字进场。"
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
                "【演绎合同】scene_truth + 每人五层限知（看到/听到、知道、以为、做了/说了、没察觉的）；"
                "每人五层必须齐，且至少抽出 1 条矿。落库 s3_patch_chapter_plan。禁止摘录占位。"
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
                "【排演合同】按节拍走一遍场面，糙可改。"
                "只落 chapter.draft（s3_save_chapter_draft），禁止写入 prose。字数不是通过条件。"
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
                "勿复读排演，守限知。字数不是通过条件。落库 s3_save_chapter。"
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


_NEED_PREV_DENSITY: dict[str, tuple[str, ...]] = {
    "outline": (),
    "beats": ("spine",),
    "deduce": ("spine", "beats"),
    "draft": ("spine", "beats", "deduction"),
    "final": ("spine", "beats", "deduction", "draft"),
}
_NEED_PREV_WORDS: dict[str, tuple[str, ...]] = {
    "outline": (),
    "beats": ("synopsis",),
    "deduce": ("synopsis", "beats"),
    "draft": ("synopsis", "beats", "deduction"),
    "final": ("synopsis", "beats", "deduction", "draft"),
}


def _need_prev_map() -> dict[str, tuple[str, ...]]:
    from scribe3.clue_density import chapter_design_mode, clue_density_mode
    if chapter_design_mode() == "on":
        return {
            "design": (),
            "outline": (),
            "beats": ("design",),
            "deduce": ("design",),
            "draft": ("design", "deduction"),
            "final": ("design", "deduction", "draft"),
        }
    return _NEED_PREV_WORDS if clue_density_mode() == "off" else _NEED_PREV_DENSITY


# 兼容旧名（测试/外部若直接读）
_NEED_PREV = _NEED_PREV_DENSITY


def _missing_bucket(mid: str) -> str:
    from scribe3.clue_density import chapter_design_mode, clue_density_mode
    if chapter_design_mode() == "on" and (
        mid.startswith("spine_") or mid in (
            "lines_unbound", "beat_count", "beat_each", "beat_sum",
            "choice_not_staged", "second_choice", "design_half",
            "cast_invented", "place_name_mismatch", "place_travel_unsaid",
            "clock_jump_unsaid", "bite_false_prev", "bite_off_hook",
            "line_delta_empty", "line_off_topic", "line_wrong_bind",
            "choice_mirror", "who_unmet", "event_unmet", "bill_unmet", "design_book_missing",
        ) or mid.startswith("beat_") or mid.startswith("place_") or mid.startswith("line_") or mid.startswith("bite_")
    ):
        return "design"
    if mid.startswith("spine_") or mid == "lines_unbound":
        return "spine"
    if mid == "synopsis":
        return "spine" if clue_density_mode() != "off" else "synopsis"
    if mid.startswith("beat_") or mid in ("beat_count", "beat_each", "beat_sum"):
        return "beats"
    return mid


def stage_ready(
    ch: Mapping[str, Any] | None,
    stage: str | None,
    *,
    store=None,
    seq: int | None = None,
) -> dict[str, Any]:
    """进下一阶段：只验已经该齐的上一层。加厚本阶段不走这里。"""
    st = normalize_stage(stage)
    needed = _need_prev_map().get(st)
    if needed is None:
        return {"ok": True, "missing": [], "stage": st, "message": ""}
    ev = evaluate_iceberg(
        ch if isinstance(ch, dict) else {},
        for_phase="final",
        st=store,
        seq=seq,
    )
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
        "hint": "先让主编把上一阶段用 LLM 补情节原子（选择/代价/线）；或 skip_iceberg / danger_draft 旁路。",
    }


def iceberg_ok_for(
    ch: Mapping[str, Any] | None,
    field: str,
    *,
    store=None,
    seq: int | None = None,
) -> bool:
    """该块覆盖是否已达地板（有则 skip 加厚）。破绽词未清不算够厚。"""
    ev = evaluate_iceberg(
        ch if isinstance(ch, dict) else {},
        for_phase="final",
        st=store,
        seq=seq,
    )
    miss = {str(m.get("id")) for m in (ev.get("missing") or [])}
    src = ch if isinstance(ch, dict) else {}
    from scribe3.iceberg_leak import scan_persist_fields_for_leaks
    from scribe3.clue_density import chapter_design_mode
    from scribe3.chapter_spine import is_v1
    if chapter_design_mode() == "on" and field in ("synopsis", "spine", "beats", "design"):
        field = "design"
    if field == "design":
        if any(
            m.startswith("spine_") or m.startswith("beat_")
            or m in (
                "synopsis", "lines_unbound", "beat_count", "beat_each", "beat_sum",
                "choice_not_staged", "second_choice", "design_half",
                "cast_invented", "place_name_mismatch", "place_travel_unsaid",
                "clock_jump_unsaid", "bite_false_prev", "bite_off_hook",
                "line_delta_empty", "line_off_topic", "line_wrong_bind",
                "choice_mirror", "who_unmet", "event_unmet", "bill_unmet", "design_book_missing",
            )
            for m in miss
        ):
            return False
        if not is_v1(src.get("chapter_spine")):
            return False
        if len([b for b in (src.get("beats") or []) if b]) < 3:
            return False
        return not scan_persist_fields_for_leaks({
            "chapter_spine": src.get("chapter_spine"),
            "beats": src.get("beats"),
        })
    if field in ("synopsis", "spine"):
        if any(m.startswith("spine_") or m in ("synopsis", "lines_unbound") for m in miss):
            return False
        return not scan_persist_fields_for_leaks({
            "synopsis": src.get("synopsis"),
            "chapter_spine": src.get("chapter_spine"),
        })
    if field == "beats":
        if any(m.startswith("beat_") or m in ("beat_count", "beat_each", "beat_sum") for m in miss):
            return False
        return not scan_persist_fields_for_leaks({"beats": src.get("beats")})
    if field == "deduction":
        if "deduction" in miss or "deduction_layers" in miss or "deduction_ore" in miss:
            return False
        if _deduce_dirty(src):
            return False
        return not scan_persist_fields_for_leaks({
            "scene_truth": src.get("scene_truth"),
            "deductions": src.get("deductions"),
        })
    if field == "draft":
        if "draft" in miss or "ore_unlanded" in miss:
            return False
        raw = src.get("draft") or src.get("draft_prose") or ""
        if not str(raw).strip():
            return False
        return not scan_persist_fields_for_leaks({"draft": raw})
    return False


def _deduce_dirty(ch: Mapping[str, Any] | None) -> bool:
    src = ch if isinstance(ch, dict) else {}
    if not str(src.get("scene_truth") or "").strip():
        return True
    from scribe3.deduce_helpers import is_heading_noise_role
    for d in src.get("deductions") or []:
        if not isinstance(d, dict):
            continue
        who = d.get("character_name") or d.get("character_id") or ""
        if is_heading_noise_role(who):
            return True
    return False


def _extra_force(extra: str) -> bool:
    blob = (extra or "").lower()
    return "force=1" in blob or "force：1" in extra or "force:1" in blob


# ── 解析 ──────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    body = _FENCE.sub("", text or "")
    body = _PROPOSAL_FENCE.sub("", body)
    return body.strip()


def parse_outline_payload(
    text: str,
    *,
    known_line_ids: set | None = None,
) -> dict[str, Any]:
    from scribe3.chapter_spine import (
        assemble_synopsis_from_spine,
        looks_like_13slot,
        parse_spine_labels,
    )
    from scribe3.chapter_spine import empty_spine
    from scribe3.clue_density import clue_density_mode, evaluate_spine

    body = _strip_fence(text)
    found_new = [p for p in OUTLINE_PARTS if p in body]
    cn = cn_len(body)
    if looks_like_13slot(body):
        spine = parse_spine_labels(body)
        source = "llm_13slot"
        synopsis = assemble_synopsis_from_spine(spine)
    else:
        spine = empty_spine()
        source = "llm"
        synopsis = body
    dens = evaluate_spine(spine, known_line_ids=known_line_ids)
    mode = clue_density_mode()
    if mode == "on":
        ok = bool(dens.ok) and source == "llm_13slot"
    else:
        ok = cn >= SYNOPSIS_FLOOR
    return {
        "synopsis": synopsis,
        "chapter_spine": spine,
        "parts": found_new,
        "cn": cn,
        "ok": ok,
        "density": dens.as_dict(),
        "warn_parts": [p for p in OUTLINE_PARTS if p not in body],
        "source": source,
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


_BEAT_HEAD = _BEAT_SPLIT
_XUAN_PAI = re.compile(
    r"(?:^|\n)\s*(?:选拍|指定拍|带选拍)\s*[:：]\s*(\d+)",
    re.I,
)


def _split_beat_chunks(text: str, *, fallback: bool = True) -> list[str]:
    """按拍头切块。design 路径 fallback=False，禁止把章标签收成假拍。"""
    body = text or ""
    parts = [p for p in _BEAT_HEAD.split(body) if p is not None]
    chunks: list[str] = []
    if len(parts) >= 3:
        i = 1
        while i + 1 < len(parts):
            chunk = str(parts[i + 1]).strip()
            if chunk:
                chunks.append(chunk)
            i += 2
    if not chunks and fallback:
        chunks = [p.strip() for p in re.split(r"\n\s*\n", body) if cn_len(p) >= 40]
    return chunks


def parse_designated_beat(text: str, n_beats: int) -> int:
    """1-based 拍号。未写 / 非数字 / 越界 → 当没写，回退 2（不足 2 拍则 1）。"""
    default = 2 if n_beats >= 2 else max(1, n_beats)
    m = _XUAN_PAI.search(text or "")
    if not m:
        return default
    try:
        n = int(m.group(1))
    except ValueError:
        return default
    if n < 1 or n > n_beats:
        return default
    return n


def _beats_from_chunks(chunks: list[str]) -> tuple[list[dict[str, Any]], bool]:
    from scribe3.chapter_spine import assemble_beat_text, normalize_choice

    beats: list[dict[str, Any]] = []
    new_style = False
    for i, chunk in enumerate(chunks, 1):
        slots_new = _extract_slot(chunk, BEAT_SLOTS)
        slots_old = _extract_slot(chunk, BEAT_SLOTS_V1)
        gcd = _extract_slot(chunk, ("目标", "冲突", "结果", "代价", "钩子"))
        item: dict[str, Any] = {"id": f"b{i}"}
        if any(slots_new.get(k) for k in ("要", "挡", "变", "付", "选")):
            new_style = True
            for lab, key in _BEAT_LABEL_TO_KEY.items():
                if slots_new.get(lab):
                    item[key] = slots_new[lab].split("\n", 1)[0].strip()
            item["choice"] = normalize_choice(item.get("choice"))
            item["text"] = assemble_beat_text(item)
        else:
            item["text"] = chunk.strip()
            if slots_old.get("事件"):
                item["goal"] = slots_old["事件"].split("\n", 1)[0].strip()
            if slots_old.get("翻转"):
                item["turn"] = slots_old["翻转"].split("\n", 1)[0].strip()
            if slots_old.get("出场"):
                item["cost"] = slots_old["出场"].split("\n", 1)[0].strip()
            if slots_old.get("水下"):
                item["underwater"] = slots_old["水下"].split("\n", 1)[0].strip()
            if gcd.get("目标"):
                item["goal"] = gcd["目标"].split("\n", 1)[0].strip()
            if gcd.get("冲突"):
                item["conflict"] = gcd["冲突"].split("\n", 1)[0].strip()
            if gcd.get("结果"):
                item["turn"] = gcd["结果"].split("\n", 1)[0].strip()
            if gcd.get("代价"):
                item["cost"] = gcd["代价"].split("\n", 1)[0].strip()
            if gcd.get("钩子"):
                item["hook"] = gcd["钩子"].split("\n", 1)[0].strip()
            if "dilemma" in item and "choice" not in item:
                item["choice"] = item.get("dilemma")
            item["choice"] = normalize_choice(item.get("choice"))
        beats.append(item)
    return beats, new_style


def parse_chapter_design_payload(
    text: str,
    *,
    known_line_ids: set | None = None,
) -> dict[str, Any]:
    """一份稿拆【章】+【拍】。ok 只看结构，密度不进 parse.ok。"""
    from scribe3.chapter_spine import (
        assemble_synopsis_from_spine,
        looks_like_13slot,
        parse_spine_labels,
    )
    from scribe3.fate_dearer import parse_clock_place_labels, parse_world_fact_label

    body = _strip_fence(text)
    head = _BEAT_HEAD.search(body)
    if head:
        preamble = body[:head.start()]
        beats_body = body[head.start():]
    else:
        preamble = body
        beats_body = ""
    spine = parse_spine_labels(preamble)
    spine_ok = looks_like_13slot(preamble)
    chunks = _split_beat_chunks(beats_body, fallback=False)
    beats, new_style = _beats_from_chunks(chunks)
    designated = parse_designated_beat(body, len(chunks))
    clock, place = parse_clock_place_labels(preamble)
    wf = parse_world_fact_label(preamble)
    struct_ok = spine_ok and len(chunks) >= 3
    if not struct_ok:
        code = "design_spine_unparsed" if not spine_ok else "design_beats_unparsed"
    else:
        code = ""
    return {
        "ok": struct_ok,
        "code": code,
        "chapter_spine": spine,
        "beats": beats,
        "designated_beat": designated,
        "synopsis": assemble_synopsis_from_spine(spine) if spine_ok else "",
        "clock": clock,
        "place": place,
        "world_fact": wf,
        "cn": cn_len(body),
        "source": "llm_gcd" if new_style else "llm",
    }


def merge_chapter_design(
    base_spine: Mapping[str, Any] | None,
    base_beats: list | None,
    patch_spine: Mapping[str, Any] | None,
    patch_beats: list | None,
    *,
    allow_keys: set[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """已过的格子保留，只覆盖补丁里非空的格。allow_keys 外的非空补丁丢掉。"""
    from scribe3.chapter_spine import assemble_beat_text, slot_text

    spine = dict(base_spine or {})
    for k, v in (patch_spine or {}).items():
        if str(k).startswith("_"):
            continue
        if allow_keys is not None and k not in allow_keys:
            continue
        if k == "lines":
            if v:
                spine[k] = v
            continue
        if slot_text(v):
            spine[k] = v
    beats: list[dict[str, Any]] = []
    for b in base_beats or []:
        beats.append(dict(b) if isinstance(b, dict) else {"text": b})
    # 点名格子时只盖章纲；节拍另走 _merge_beats_by_head，免得洗掉已钉的场。
    if allow_keys is not None:
        return spine, beats
    beat_fields = ("goal", "conflict", "turn", "choice", "cost", "underwater")
    for i, pb in enumerate(patch_beats or []):
        if not isinstance(pb, dict):
            continue
        if i >= len(beats):
            beats.append(dict(pb))
            continue
        merged = dict(beats[i])
        for k in beat_fields:
            if slot_text(pb.get(k)):
                merged[k] = pb[k]
        merged["text"] = assemble_beat_text(merged)
        beats[i] = merged
    return spine, beats


def merge_clock_place_patch(
    base_c: Mapping[str, Any] | None,
    base_p: Mapping[str, Any] | None,
    patch_c: Mapping[str, Any] | None,
    patch_p: Mapping[str, Any] | None,
    *,
    allow_keys: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """只盖 allow_keys 里出现的 clock/place 键。None = 补丁非空全盖。"""
    clock = dict(base_c or {})
    place = dict(base_p or {})

    def _ok(dotted: str) -> bool:
        return allow_keys is None or dotted in allow_keys

    for k, v in (patch_c or {}).items():
        if v in (None, "", []):
            continue
        if _ok(f"clock.{k}"):
            clock[k] = v
    for k, v in (patch_p or {}).items():
        if v in (None, "", []):
            continue
        if _ok(f"place.{k}"):
            place[k] = v
    return clock, place


def _beat_heads(text: str) -> list[int]:
    out: list[int] = []
    for n in _BEAT_HEAD.findall(text or ""):
        try:
            out.append(int(n))
        except (TypeError, ValueError):
            continue
    return out


def _merge_beats_by_head(
    base_beats: list | None,
    patch_beats: list | None,
    raw: str,
) -> list[dict[str, Any]]:
    """只盖补丁里写明的那一拍。模型写「拍2」就盖第 2 场，不冲第 1 场。"""
    from scribe3.chapter_spine import assemble_beat_text, slot_text

    beats: list[dict[str, Any]] = []
    for b in base_beats or []:
        beats.append(dict(b) if isinstance(b, dict) else {"text": b})
    heads = _beat_heads(raw)
    beat_fields = ("goal", "conflict", "turn", "choice", "cost", "underwater")
    for i, pb in enumerate(patch_beats or []):
        if not isinstance(pb, dict):
            continue
        idx = heads[i] - 1 if i < len(heads) else i
        if idx < 0:
            continue
        while idx >= len(beats):
            beats.append({"id": f"b{len(beats) + 1}"})
        merged = dict(beats[idx])
        for k in beat_fields:
            if slot_text(pb.get(k)):
                merged[k] = pb[k]
        merged["text"] = assemble_beat_text(merged)
        beats[idx] = merged
    return beats


def _design_keep_block(spine: Mapping[str, Any] | None, beats: list | None) -> str:
    from scribe3.chapter_spine import SLOT_LABELS, slot_text

    lines: list[str] = ["【已过·原样保留，禁止改写】"]
    src = spine if isinstance(spine, dict) else {}
    for k, lab in SLOT_LABELS.items():
        body = slot_text(src.get(k))
        if body:
            lines.append(f"{lab}：{body}")
    for i, b in enumerate(beats or [], 1):
        if not isinstance(b, dict):
            continue
        bits = []
        for key, lab in (
            ("goal", "要"), ("conflict", "挡"), ("turn", "变"),
            ("choice", "选"), ("cost", "付"), ("underwater", "水下"),
        ):
            val = slot_text(b.get(key))
            if val:
                bits.append(f"{lab}：{val}")
        if bits:
            lines.append(f"## 拍{i}")
            lines.extend(bits)
    return "\n".join(lines) if len(lines) > 1 else ""


def parse_beats_payload(text: str, *, spine: dict | None = None) -> dict[str, Any]:
    from scribe3.clue_density import clue_density_mode, evaluate_beats

    body = _strip_fence(text)
    chunks = _split_beat_chunks(body, fallback=True)
    beats, new_style = _beats_from_chunks(chunks)
    lens = [cn_len(b.get("text")) for b in beats]
    thin = [i + 1 for i, n in enumerate(lens) if n < BEAT_EACH_FLOOR]
    dens = evaluate_beats(beats, spine=spine)
    mode = clue_density_mode()
    if mode == "on":
        ok = bool(dens.ok)
    else:
        ok = len(beats) >= 3 and not thin and sum(lens) >= BEAT_SUM_FLOOR
    return {
        "beats": beats,
        "cn": sum(lens),
        "each": lens,
        "ok": ok,
        "thin": thin,
        "density": dens.as_dict(),
        "source": "llm_gcd" if new_style else "llm",
    }


def parse_deduce_payload(text: str, *, involved: list[str] | None = None) -> dict[str, Any]:
    from scribe3.deduce_helpers import (
        is_heading_noise_role,
        is_layer_heading,
        normalize_role_id,
    )

    body = _strip_fence(text)
    truth = ""
    deds: list[dict[str, Any]] = []
    sections = re.split(r"(?=(?:^|\n)\s*#{1,3}\s+)", "\n" + body)
    current_role = ""
    current_buf: list[str] = []

    def flush_role() -> None:
        nonlocal current_role, current_buf
        prose = "\n".join(current_buf).strip()
        if current_role and prose and not is_heading_noise_role(current_role):
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
        if is_layer_heading(title) and any(
            k in title for k in ("场景真相", "scene_truth", "真相")
        ) and not current_role:
            flush_role()
            truth = rest or title
            continue
        if any(k in title for k in ("场景真相", "scene_truth")):
            flush_role()
            truth = rest or title
            continue
        if title and not is_layer_heading(title):
            flush_role()
            current_role = title
            current_buf = [raw]
        elif current_role:
            current_buf.append(raw)
        elif is_layer_heading(title):
            # 无角色头的五层标题：不另开角色，也不把「以为」写成真相
            continue
        elif not truth:
            truth = raw
    flush_role()
    if not deds and involved:
        # 整篇当作单人投影（测试/短输出）
        only = next(
            (x for x in involved if not is_heading_noise_role(x)),
            involved[0],
        )
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
        "ok": bool(deds) and dsum > 0,
        "source": "llm",
    }


def parse_draft_payload(text: str) -> dict[str, Any]:
    from scribe3.chapter_spine import strip_spine_labels_from_prose
    body = strip_spine_labels_from_prose(_strip_fence(text))
    cn = cn_len(body)
    return {"draft": body, "cn": cn, "ok": bool(body.strip()), "source": "llm"}


def parse_final_payload(text: str) -> dict[str, Any]:
    from scribe3.chapter_spine import strip_spine_labels_from_prose
    body = strip_spine_labels_from_prose(_strip_fence(text))
    cn = cn_len(body)
    return {"prose": body, "cn": cn, "ok": bool(body.strip()), "source": "llm"}


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

def _line_text_from_row(row: Mapping[str, Any] | None, *, kind: str) -> str:
    src = row if isinstance(row, dict) else {}
    if kind == "storyline":
        return str(src.get("title") or src.get("notes") or "").strip()
    return str(src.get("text") or src.get("title") or "").strip()


def _open_lines_block(st) -> str:
    if st is None:
        return ""
    from scribe3.chapter_spine import known_line_ids_from_store
    ids = known_line_ids_from_store(st)
    if not ids:
        return (
            "可绑定的线：本书尚无 promise/storyline。"
            "先在设定库补 1–2 条再写「动哪条线」；禁止无 id 短句。"
        )
    bits: list[str] = []
    for kind, pid in sorted(ids):
        text = ""
        try:
            if kind == "promise" and hasattr(st, "get_promise"):
                text = _line_text_from_row(st.get_promise(pid), kind="promise")
            elif kind == "storyline" and hasattr(st, "get_storyline"):
                text = _line_text_from_row(st.get_storyline(pid), kind="storyline")
        except Exception:
            text = ""
        if not text:
            try:
                if kind == "promise" and hasattr(st, "list_promises"):
                    for row in st.list_promises() or []:
                        if str((row or {}).get("id") or "") == pid:
                            text = _line_text_from_row(row, kind="promise")
                            break
                elif kind == "storyline" and hasattr(st, "list_storylines"):
                    for row in st.list_storylines() or []:
                        if str((row or {}).get("id") or "") == pid:
                            text = _line_text_from_row(row, kind="storyline")
                            break
            except Exception:
                text = ""
        bits.append(f"{kind}:{pid} {text}".strip())
    return (
        "可绑定的线（选本章正在办的那条，id 后必须跟一句本章推进）：\n"
        + "\n".join(bits)
    )


def load_design_book(st, seq: int | None, ch: Mapping[str, Any] | None, extra: str = "") -> "DesignBook":
    from scribe3.clue_density import BindableLine, DesignBook, extract_focus_names, extract_duty
    from scribe3.fate_dearer import load_place
    from scribe3.narrative_drive import resolve_prev_end_hook

    src = ch if isinstance(ch, dict) else {}
    try:
        nseq = int(seq or src.get("seq") or 1)
    except (TypeError, ValueError):
        nseq = 1
    char_names: set[str] = set()
    item_names: set[str] = set()
    place_names: set[str] = set()
    term_names: set[str] = set()
    lines: list[BindableLine] = []
    if st is not None:
        try:
            for c in (st.characters() or []):
                name = ""
                if isinstance(c, dict):
                    name = str(c.get("name") or c.get("label") or "")
                else:
                    name = str(getattr(c, "name", "") or "")
                if name.strip():
                    char_names.add(name.strip())
        except Exception:
            pass
        try:
            for it in (st.list_items() or []):
                name = str((it or {}).get("name") or "")
                if name.strip():
                    item_names.add(name.strip())
        except Exception:
            pass
        try:
            for e in (st.all_entities() or []):
                if getattr(e, "kind", None) == "place" and getattr(e, "name", None):
                    place_names.add(str(e.name))
        except Exception:
            pass
        try:
            for t in (st.list_terms() or []):
                name = str((t or {}).get("name") or "")
                if name.strip():
                    term_names.add(name.strip())
        except Exception:
            pass
        try:
            for row in (st.list_promises() or []):
                pid = str((row or {}).get("id") or "")
                if pid:
                    lines.append(BindableLine(
                        "promise", pid, _line_text_from_row(row, kind="promise"),
                    ))
        except Exception:
            pass
        try:
            for row in (st.list_storylines() or []):
                pid = str((row or {}).get("id") or "")
                if pid:
                    lines.append(BindableLine(
                        "storyline", pid, _line_text_from_row(row, kind="storyline"),
                    ))
        except Exception:
            pass
    prev_place = ""
    prev_hook = ""
    prev_setting = ""
    if st is not None and nseq > 1:
        try:
            prev = st.get_chapter(nseq - 1) or {}
            prev_place = str(load_place(prev).get("name") or "")
            prev_hook = str(resolve_prev_end_hook(prev) or "")
            psp = prev.get("chapter_spine") if isinstance(prev.get("chapter_spine"), dict) else {}
            prev_setting = str((psp or {}).get("setting") or "")
        except Exception:
            pass
    who, event, bill = extract_duty(extra, src)
    return DesignBook(
        seq=nseq,
        title=str(src.get("title") or ""),
        focus_names=extract_focus_names(extra, src),
        character_names=frozenset(char_names),
        item_names=frozenset(item_names),
        place_names=frozenset(place_names),
        term_names=frozenset(term_names),
        bindable_lines=tuple(lines),
        prev_place_name=prev_place,
        prev_hook=prev_hook,
        prev_setting=prev_setting,
        must_happen=event,
        duty_who=who,
        duty_event=event,
        duty_bill=bill,
    )


def _book_card_block(st, ch: Mapping[str, Any] | None, *, extra: str = "") -> str:
    from scribe3.clue_density import design_book_mode
    if design_book_mode() != "on" or st is None:
        return ""
    book = load_design_book(st, (ch or {}).get("seq") if isinstance(ch, dict) else None, ch, extra)
    bits: list[str] = ["【本书硬卡】"]
    if book.character_names:
        names = "、".join(sorted(book.character_names)[:24])
        bits.append("已有人名：" + names)
    else:
        bits.append("已有人名：无。禁止新造人名。对手/见证用物件或地点或机制。")
    extras: list[str] = []
    if book.item_names:
        extras.append("物件：" + "、".join(sorted(book.item_names)[:16]))
    if book.place_names:
        extras.append("地点：" + "、".join(sorted(book.place_names)[:16]))
    if book.term_names:
        extras.append("术语：" + "、".join(sorted(book.term_names)[:16]))
    if extras:
        bits.extend(extras)
    if book.focus_names:
        bits.append("主编点名的焦点：" + "、".join(book.focus_names))
    if book.prev_hook:
        bits.append("上章钩：" + book.prev_hook)
    if book.prev_place_name:
        bits.append("上章地点：" + book.prev_place_name)
    if book.duty_who or book.duty_event or book.duty_bill:
        bits.append("本章责任：")
        if book.duty_who:
            bits.append("谁：" + book.duty_who)
        if book.duty_event:
            bits.append("事：" + book.duty_event)
        if book.duty_bill:
            bits.append("账：" + book.duty_bill)
        from scribe3.clue_density import topics_overlap
        probe = book.duty_event or book.duty_bill
        if probe:
            same = [
                f"{ln.kind}:{ln.id} {ln.text}".strip()
                for ln in book.bindable_lines
                if topics_overlap(probe, ln.text, book)
            ]
            if same:
                bits.append("这件事正在办的线：\n" + "\n".join(same[:6]))
    return "\n".join(bits)


def _prev_hook_block(st, ch: Mapping[str, Any] | None) -> str:
    if st is None or not isinstance(ch, dict):
        return ""
    try:
        seq = int(ch.get("seq") or 0)
    except (TypeError, ValueError):
        seq = 0
    if seq <= 1:
        return ""
    try:
        prev = st.get_chapter(seq - 1) or {}
    except Exception:
        return ""
    from scribe3.narrative_drive import resolve_prev_end_hook
    hook = resolve_prev_end_hook(prev)
    bits: list[str] = []
    if hook:
        bits.append("上章钩（本章「咬上章」必须接这一口）：\n" + hook)
    meta = prev.get("beats_meta") if isinstance(prev.get("beats_meta"), dict) else {}
    seeds = meta.get("seeds") if isinstance(meta.get("seeds"), list) else []
    atoms = [str(s.get("atom") or "").strip() for s in seeds if isinstance(s, dict)]
    from scribe3.fate_dearer import is_seed_atom
    names: set[str] = set()
    prev_spine = prev.get("chapter_spine") if isinstance(prev.get("chapter_spine"), dict) else {}
    for n in re.split(r"[、，,；;/／]", str((prev_spine or {}).get("cast") or "")):
        if n.strip():
            names.add(n.strip())
    atoms = [a for a in atoms if a and is_seed_atom(a, known_names=names)]
    if atoms:
        bits.append(
            "上章无户口种子（必须写进 bite/info_gap/lines/hook，或在禁令里作废）：\n"
            + "\n".join(atoms)
        )
    return "\n\n".join(bits)


def _ctx_bits(ch: Mapping[str, Any] | None, st=None) -> str:
    meta = ch if isinstance(ch, dict) else {}
    from scribe3.chapter_spine import (
        SLOT_LABELS,
        SPINE_SLOTS,
        is_v1,
        slot_text,
    )
    from scribe3.iceberg import clip_for
    bits = []
    if is_v1(meta.get("chapter_spine")):
        spine = meta.get("chapter_spine") or {}
        lines = []
        for k in SPINE_SLOTS:
            body = slot_text(spine.get(k))
            if body:
                lines.append(f"{SLOT_LABELS[k]}：{body}")
        if lines:
            bits.append("现有章纲（短槽，可改，勿写成场面）：\n" + "\n".join(lines))
        beat_lines = []
        for i, b in enumerate(meta.get("beats") or [], 1):
            if not isinstance(b, dict):
                continue
            parts = []
            for key, lab in (
                ("goal", "要"), ("conflict", "挡"), ("turn", "变"),
                ("choice", "选"), ("cost", "付"), ("underwater", "水下"),
            ):
                if slot_text(b.get(key)):
                    parts.append(f"{lab}：{slot_text(b.get(key))}")
            if parts:
                beat_lines.append(f"{i}. " + "；".join(parts))
        if beat_lines:
            bits.append("现有台阶（GCD，勿灌进场）：\n" + "\n".join(beat_lines))
        from scribe3.chapter_spine import format_must_land
        land = format_must_land(spine, chapter=meta)
        if land:
            bits.append(land)
    # 无 spine：不灌肥 synopsis。跨章咬合见 _prev_hook_block
    prev_bite = _prev_hook_block(st, meta)
    if prev_bite:
        bits.append(prev_bite)
    truth = str(meta.get("scene_truth") or "").strip()
    involved = meta.get("involved_characters") or []
    if truth:
        bits.append("场景真相：\n" + clip_for("scene_truth", truth))
    if involved:
        from scribe3.deduce_helpers import is_heading_noise_role
        names = [str(x) for x in involved if not is_heading_noise_role(x)]
        if names:
            bits.append("在场：" + "、".join(names))
    cat = _open_lines_block(st)
    if cat:
        bits.append(cat)
    return "\n\n".join(bits)


def _fate_ask_header(ch: Mapping[str, Any] | None, *, st=None, seq: int | None = None) -> str:
    from scribe3.fate_dearer import load_fate_context
    from scribe3.chapter_spine import slot_text
    src = ch if isinstance(ch, dict) else {}
    n = int(seq or src.get("seq") or 1)
    ctx = load_fate_context(st, n, src)
    pays = (ctx.who_pays or "").strip() or "（未设 — 先 s3_set_intent）"
    axis = " / ".join(ctx.axis_terms) if ctx.axis_terms else "（未设）"
    start = (ctx.clock_start or "").strip() or "（未设）"
    end = (ctx.clock_end or "").strip() or "（未设）"
    prev_cost = "（第 1 章，无）"
    if ctx.prev_spine:
        prev_cost = slot_text(ctx.prev_spine.get("cost")) or "（上章无代价）"
    return (
        f"本书在惩罚：{pays}\n"
        f"代价轴用语：{axis}\n"
        f"本书钟：{start} → {end}\n"
        f"上章代价：{prev_cost}\n"
        "禁止与上章同一物件同一动作；代价须点名轴用语或设定库专名。\n"
        "时长/增量/笔墨：见故事钟合同（span 必填；delta=0 只许一章）。\n"
        "地点/地点增量：见地点合同（name+delta 必填；place_delta=0 只许一章）。"
    )


def _world_name_block(st) -> str:
    if st is None:
        return ""
    names: list[str] = []
    for meth in ("list_world_rules", "list_terms", "list_items"):
        try:
            fn = getattr(st, meth, None)
            rows = fn() if callable(fn) else []
            for row in rows or []:
                if isinstance(row, dict) and row.get("name"):
                    names.append(str(row["name"]))
        except Exception:
            pass
    if not names:
        return ""
    return "设定库专名（代价可点名，禁止虚构 id）：\n" + "、".join(names[:24])


def _world_contract_block(st, ch=None) -> str:
    from scribe3.world_surface import load_world_claim
    claim = load_world_claim(ch if isinstance(ch, dict) else None)
    names = _world_name_block(st)
    if claim:
        bits = [
            "【世界合同】扩写不得覆盖本章命题：" + (claim.claim or "（见分组词）") + "。",
            "禁止改成帘、丝、黑针、看清水。"
            "禁止 extra 命令「必须原样 / 必须有一句 / 必须以时空」。",
        ]
        for k, v in claim.groups.items():
            if v:
                bits.append(f"{k}组：{'/'.join(v)}")
        bits.append("定稿水面必须付清 goal 组与 hook 组各至少一个登记词。")
    else:
        bits = [
            "【世界合同】extra / 扩写不得覆盖本章要、代价、世界事实里的世界词；"
            "禁止改成帘、丝、看清水、涌出的东西。"
            "本章要与代价必须各点名至少一个世界机制词（大遮蔽/成核点/指针态/场核/金縢/相位锚）。",
        ]
    if names:
        bits.append(names)
    return "\n".join(bits)


_OUTLINE_ASK = (
    "写这一章怎么发生。不是读者正文，不是填表。\n"
    "硬卡若有本章责任：该在的人必须各做各的事；只办那一件事；代价必须是那一笔账。\n"
    "第1章写章前状态。后面的章接住上一章没做完的事。换了地方，让人看得出他怎么到的。\n"
    "不要编户口里没有的人。\n"
    "\n"
    "下面标签是给机器读稿用的，不是写好的标准。用这些标签交卷：\n"
    "时空：何时何地\n"
    "在场：谁在做事（该在的人不能只站着）\n"
    "咬上章：接住的那件没做完的事\n"
    "本章要：责任里那一件事怎么动手\n"
    "挡：谁或什么使它变贵\n"
    "触发：打破平衡的一下\n"
    "升级：原办法失败或新信息\n"
    "选择：他面对的两难，两边都有损失；能拆开最好\n"
    "决断：他选了哪边\n"
    "代价：世界因此怎么变，必须是责任里那一笔账\n"
    "信息差：谁新知道 / 仍不知\n"
    "动哪条线：正在办的那条的编号，后面跟一句本章推进\n"
    "钩：还没做完的动作\n"
    "禁令：本章不能说出口的（可写「无」）\n"
    "时长：这一场有多长\n"
    "增量：钟走了没有\n"
    "地点：还在哪\n"
    "地点增量：换没换地方\n"
    "世界事实：世界因此可核对的变化\n"
    "只输出上述标签行。"
)

_DESIGN_ASK = (
    "写这一章怎么发生，并拆成几场上台的压力。不是读者正文，不是填表。\n"
    "硬卡若有本章责任：该在的人必须各做各的事；只办那一件事；代价必须是那一笔账。\n"
    "第1章写章前状态。后面的章接住上一章没做完的事。换了地方，让人看得出他怎么到的。\n"
    "不要编户口里没有的人。\n"
    "先写【章】，再写【拍】。拍头单独一行「## 拍1」「## 拍2」「## 拍3」。\n"
    "\n"
    "【章】标签是给机器读稿用的：\n"
    "时空：何时何地\n"
    "在场：谁在做事\n"
    "咬上章：接住的那件没做完的事\n"
    "本章要：责任里那一件事怎么动手\n"
    "挡：谁或什么使它变贵\n"
    "触发：打破平衡的一下\n"
    "升级：原办法失败或新信息\n"
    "选择：他面对的两难，两边都有损失；能拆开最好\n"
    "决断：他选了哪边\n"
    "代价：世界因此怎么变，必须是责任里那一笔账\n"
    "信息差：谁新知道 / 仍不知\n"
    "动哪条线：正在办的那条的编号，后面跟一句本章推进\n"
    "钩：还没做完的动作\n"
    "禁令：本章不能说出口的（可写「无」）\n"
    "时长：这一场有多长\n"
    "增量：钟走了没有\n"
    "地点：还在哪\n"
    "地点增量：换没换地方\n"
    "世界事实：世界因此可核对的变化\n"
    "\n"
    "【拍】至少三场上台的压力，每场都推进那一件事。带选择的那场把账付清。\n"
    "## 拍1\n要：\n挡：\n变：\n付：\n选：无\n水下：\n"
    "## 拍2\n要：\n挡：\n变：\n付：\n选：与【章】里同一道两难\n水下：\n"
    "## 拍3\n要：\n挡：\n变：\n付：\n选：无\n水下：\n"
    "默认第二场演出那道两难。其余场的选写「无」。\n"
    "只输出上述标签行。"
)

_BEATS_ASK = (
    "把这一章拆成至少三场上台的压力。每场都要推进责任里那一件事。"
    "带选择的那场把账付清。不要逛场，不要把上一章再演一遍。\n"
    "每场用这些标签交卷：\n"
    "要：这一场要办成什么\n"
    "挡：谁或什么使它变贵\n"
    "变：新信息或原办法失败\n"
    "付：这一场付出去的东西\n"
    "选：若是做决定的那场，写出那道两难；其余写「无」\n"
    "水下：作者知道、正文不写的一句\n"
    "只输出各场标签行。"
)

_DEDUCE_ASK = (
    "先写 ## 场景真相（全知冷叙，客观发生）。再为每个在场角色写一篇限知投影，"
    "标题用角色名（以章纲「在场」为准），其下五个小标题必须写成半角括号："
    "看到/听到、知道、以为(误读)、做了/说了、没察觉的。\n"
    "禁止把小标题当成角色名。禁止另开「以为」「知道」这种角色。\n"
    "每人「知道 / 没察觉的」必须覆盖章纲信息差（谁新知道、仍不知）。\n"
    "每人五层必须齐，且至少抽出 1 条矿（动作+物件或时间+物件）。"
    "禁止逐字摘录充数，禁止「未能确认」五栏占位。字数不是通过条件。\n"
    "只输出真相与投影。"
)

_DRAFT_ASK = (
    "按节拍把场面走一遍：糙、可越界待改，用来发现节拍漏洞。"
    "【必须落地】里的选择必须在场面里发生一次，决断与代价必须看得见；"
    "禁令不得说出口。禁止只写巷/门/烟。"
    "字数不是通过条件。这是排演，不是读者正文。只输出排演正文。"
)

_FINAL_ASK = (
    "写读者正文。大纲/节拍/演绎/排演全文都在材料里；读者正文必须另写，"
    "禁止复读排演句，守限知横幅。"
    "兑现【必须落地】：选择发生一次，代价落地，钩仍悬着，禁令不说出口。"
    "禁止输出标签行，禁止正文以「时空：」开头。"
    "字数不是通过条件。只输出正文。"
)


MAX_THICKEN_ROUNDS = 4


def _design_fail_hint(parsed: Mapping[str, Any] | None, dens) -> str:
    """重试只回失败点。禁止把上次超长稿再塞回去教模型继续超槽。"""
    bits: list[str] = []
    if not parsed or not parsed.get("ok"):
        code = str((parsed or {}).get("code") or "")
        if code == "design_beats_unparsed":
            bits.append("缺 ## 拍1 / ## 拍2 / ## 拍3 三个拍头")
        elif code == "design_spine_unparsed":
            bits.append("【章】标签不齐")
        else:
            bits.append("结构缺：先【章】标签，再 ## 拍1/拍2/拍3")
    errs = list(getattr(dens, "errors", None) or [])
    for e in errs[:10]:
        if e == "choice_not_staged":
            bits.append("拍2的选必须写成与【章】选择同一组短 A vs B，禁止只写「B——」")
        elif e == "second_choice":
            bits.append("只有指定拍能有选，其余拍写「选：无」")
        elif e == "beat_leak":
            bits.append("拍里删掉锁眼/匙孔/门芯")
        elif e == "lines_unbound":
            bits.append("动哪条线抄本章正在办的那条 id，后面跟一句本章推进")
        elif e == "cast_invented":
            bits.append("在场里的人名必须来自硬卡；库空把对手改成物件/地点")
        elif e == "line_wrong_bind":
            bits.append("本章标题咬住的那条线必须绑上；标题对不上任何线时，再看本章要。delta 写本章推进")
        elif e == "place_name_mismatch":
            bits.append("delta=0 必须沿用上章地名；换了就报换域并写怎么到的")
        elif e == "place_travel_unsaid":
            bits.append("换了地方必须写怎么到的（到/搬/换域/送至）")
        elif e == "clock_jump_unsaid":
            bits.append("增量：2 且没换地，必须写留驻或跳切理由")
        elif e == "bite_false_prev":
            bits.append("第1章咬上章写章前状态，禁止接上章/上一口/余烬")
        elif e == "bite_off_hook":
            bits.append("咬上章必须接住上章钩里的核心物")
        elif e == "line_delta_empty":
            bits.append("动哪条线的 id 后面必须跟一句本章实际推进")
        elif e == "line_off_topic":
            bits.append("推进必须在说这条线本身，不要挂错线")
        elif e == "choice_mirror":
            bits.append("选择两边不能只是左右互换，后果必须不同")
        elif e == "who_unmet":
            bits.append("责任里点名的人必须在场并做事，不能只站着")
        elif e == "event_unmet":
            bits.append("本章要办的是责任里那一件事，不要另编一场")
        elif e == "bill_unmet":
            bits.append("代价必须是责任里那一笔账")
        elif e.startswith("beat_gcd") or e.startswith("beat_slots"):
            bits.append(f"{e}：这一格写空了或没写出动作/变化")
        elif e == "spine_goal_thin":
            bits.append("本章要写清可核对的动作或世界变化")
        elif e == "spine_cost_thin":
            bits.append("代价写清世界因此怎么变")
        elif e == "spine_choice":
            bits.append("【章】选择写成短 A vs B")
        elif e == "beat_off_spine":
            bits.append("决断/代价里的动词必须落在拍2的要/挡/变/付")
        else:
            bits.append(str(e))
    return "；".join(bits) if bits else "每槽一句把该写的写清；拍2选对上章选择；禁锁眼"


def _slot_play_reason(slot: str, book, dens) -> str:
    """只说这场戏这一格该承担什么。禁止词表。"""
    who = str(getattr(book, "duty_who", "") or "") if book else ""
    event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "") if book else ""
    bill = str(getattr(book, "duty_bill", "") or "") if book else ""
    hook = str(getattr(book, "prev_hook", "") or "") if book else ""
    if slot == "who":
        if who:
            return f"这一章该做事的是：{who}。你现在没让他们在场做事。"
        return "该在的人必须各做各的事，不能只站着，也不能编户口里没有的人。"
    if slot == "event":
        if event:
            return f"这一章要办的是：{event}。你现在写的是另一件事，或选择没在场上发生。"
        return "本章要、选择、决断必须是同一件正在发生的事。"
    if slot == "bill":
        if bill:
            return f"这一章的账是：{bill}。你现在写的代价是另一笔账。"
        return "代价必须是这一章让世界变贵的那一笔，不是另一场戏的结果。"
    if slot == "bite":
        if hook:
            return f"上一章没做完的是：{hook}。咬上章要接住这件事，不是另起一句。"
        return "第1章写章前状态；后面的章接住上一章没做完的事。"
    if slot == "place":
        return "换了地方，让人看得出他怎么到的；没换就还在上一个地。"
    if slot == "line":
        return "动哪条线必须是本章正在办的那条，并写清本章推进了什么。"
    if slot == "beat":
        if event:
            return f"这几场上台的压力都要推进：{event}。做决定的那场要把账付清。"
        return "每场都要推进这一章那一件事。做决定的那场把账付清。"
    return "只改不像这场戏的那一格。"


def _slot_edit_hint(slot: str, spine, beats, book, dens) -> str:
    from scribe3.design_attempt import SLOT_OUT_LINES
    keep = _design_keep_block(spine, beats)
    title = {
        "who": "在场和挡", "event": "本章要、选择、决断", "bill": "代价",
        "bite": "咬上章", "place": "时空和地点", "line": "动哪条线",
        "beat": "没演出的那一场",
    }.get(slot, slot)
    reason = _slot_play_reason(slot, book, dens)
    out_lines = SLOT_OUT_LINES.get(slot, "")
    return (
        "【只改这一格】别的格子已经钉住，一个字都不要动。\n"
        + (keep + "\n" if keep else "")
        + f"只改「{title}」。\n"
        + reason + "\n"
        f"只输出这些行：\n{out_lines}\n"
    )


def _apply_slot_patch(slot: str, parsed: dict, patch: dict, raw: str) -> dict[str, Any]:
    """只把被点名的那一格盖上工作稿。别的格子保持原样。"""
    from scribe3.chapter_spine import assemble_synopsis_from_spine
    from scribe3.design_attempt import slot_allow_keys
    from scribe3.fate_dearer import parse_clock_place_labels

    allow = slot_allow_keys(slot)
    if slot == "beat":
        spine = dict(parsed.get("chapter_spine") or {})
        beats = _merge_beats_by_head(parsed.get("beats"), (patch or {}).get("beats"), raw)
    else:
        spine, beats = merge_chapter_design(
            parsed.get("chapter_spine"), parsed.get("beats"),
            (patch or {}).get("chapter_spine"), [],
            allow_keys=allow,
        )
    clock = dict(parsed.get("clock") or {})
    place = dict(parsed.get("place") or {})
    if slot == "place":
        pc, pp = parse_clock_place_labels(raw or "")
        if not pc and isinstance((patch or {}).get("clock"), dict):
            pc = (patch or {}).get("clock") or {}
        if not pp and isinstance((patch or {}).get("place"), dict):
            pp = (patch or {}).get("place") or {}
        clock, place = merge_clock_place_patch(clock, place, pc, pp, allow_keys=None)
    return {
        **parsed,
        "ok": True,
        "code": "",
        "chapter_spine": spine,
        "beats": beats,
        "clock": clock,
        "place": place,
        "synopsis": assemble_synopsis_from_spine(spine),
        "source": (patch or {}).get("source") or parsed.get("source") or "llm",
    }


def _blocked_error_ids(blocked: Mapping[str, Any] | None) -> list[str]:
    from scribe3.design_attempt import error_ids

    if not isinstance(blocked, dict):
        return []
    out = error_ids(blocked.get("missing"))
    fate = blocked.get("fate")
    if isinstance(fate, dict):
        out.extend(error_ids(fate.get("errors")))
    return out


def build_stage_prompt(
    stage: str,
    ch: Mapping[str, Any] | None,
    *,
    seq: int | None = None,
    extra: str = "",
    strict: bool = False,
    previous: str = "",
    bible: str = "",
    continue_write: bool = False,
    floor: int | None = None,
    st=None,
    retry_hint: str = "",
) -> str:
    spec = stage_spec(stage)
    ask = str(spec.get("ask") or "")
    stg = normalize_stage(stage)
    from scribe3.clue_density import clue_density_mode
    density_on = clue_density_mode() == "on" and stg in ("outline", "beats", "design")
    if continue_write and (previous or "").strip():
        if stg in ("deduce", "draft", "final") or density_on:
            ask = (
                "【续写·情节薄】缺结构原子（选择未演 / 矿未落地 / 同一动作复读）。"
                "补情节，禁止用烟/锅/巷凑句，禁止重写开头，"
                "禁止同一只手对同一物件做同一件事写第二遍。"
                "禁止「还差 N 字写新场面」。字数不是通过条件。\n" + ask
            )
        else:
            got = cn_len(previous)
            need = int(floor or spec.get("floor") or 0)
            ask = (
                f"【续写加厚】已有 {got} 字，还差约 {max(0, need - got)} 字才到覆盖地板。"
                "从已有结尾接着写新场面，禁止重写开头，禁止复读已有段落，禁止口号充数。\n"
                + ask
            )
    elif strict:
        if density_on:
            ask = (
                "【重试·情节薄】选择必须写成 A vs B；"
                "必须有 ## 拍1/拍2/拍3；拍2选必须对上章的选择；"
                "动哪条线必须抄可绑定的线 id。禁止口号/烟锅巷凑句。字数不是通过条件。\n" + ask
            )
        else:
            ask = "【重试·必须达到覆盖地板，禁止短稿】\n" + ask
    bits = [ask]
    src = dict(ch) if isinstance(ch, dict) else {}
    if seq and not src.get("seq"):
        src["seq"] = seq
    planning = stg in ("outline", "design")
    slot_only = bool(
        retry_hint and ("只改这一格" in retry_hint or "只补没过" in retry_hint)
    )
    if planning or (slot_only and stg == "beats"):
        if slot_only:
            bits = [retry_hint]
        lines = _open_lines_block(st)
        if lines:
            bits.insert(0, lines)
        card = _book_card_block(st, src, extra=extra)
        if card:
            bits.insert(0, card)
        if not slot_only:
            bits.insert(0, (
                "先写这场戏：该在的人做事，只办责任里那一件，账按责任来付。"
                "标签是给机器读的。"
            ))
            if retry_hint:
                bits.insert(0, retry_hint)
        hook = _prev_hook_block(st, src)
        if hook:
            bits.insert(0, hook)
    if seq:
        bits.append(f"章号：第{seq}章")
    if not planning:
        try:
            from scribe3.world_surface import load_world_claim
            wc = load_world_claim(src)
            if wc:
                bits.append(
                    "【世界命题卡】" + (wc.claim or "") + "\n"
                    + "\n".join(f"{k}组：{'/'.join(v)}" for k, v in wc.groups.items() if v)
                    + "\n禁止用黑针/帘/丝付账。"
                )
        except Exception:
            pass
        ctx = _ctx_bits(src, st=st)
        if ctx:
            bits.append(ctx)
        if (bible or "").strip():
            bits.append(str(bible).strip())
        world = _world_contract_block(st, ch if isinstance(ch, dict) else src)
        if world:
            bits.append(world)
    elif extra:
        pass
    if extra:
        bits.append(extra.strip())
    if continue_write and (previous or "").strip():
        bits.append("【已有结尾·接着往下】\n" + previous[-2400:])
    elif previous and stg != "design":
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
    text = str(raw or "").strip()
    try:
        from scribe3.pipeline_trace_hooks import note_llm_output
        note_llm_output(text)
    except Exception:
        pass
    return text


def resolve_stage_focalizer(req_focalizer: str | None, chapter: Mapping[str, Any] | None) -> str:
    """请求焦点优先，否则用章上已钉的 focalizer。"""
    hit = str(req_focalizer or "").strip()
    if hit:
        return hit
    ch = chapter if isinstance(chapter, dict) else {}
    return str(ch.get("focalizer") or "").strip()


def _blocked_or_none(
    fields: dict,
    *,
    existing: dict | None = None,
    st=None,
    seq: int | None = None,
    extra: str = "",
    book=None,
) -> dict[str, Any] | None:
    from scribe3.chapter_spine import known_line_ids_from_store
    from scribe3.clue_density import design_book_mode
    from scribe3.fate_dearer import persist_fate_kwargs
    from scribe3.iceberg import persist_fields_blocked
    ids = known_line_ids_from_store(st) if st is not None else None
    if book is None and st is not None and design_book_mode() == "on":
        book = load_design_book(st, seq, existing or {}, extra=extra)
    return persist_fields_blocked(
        fields,
        existing=existing,
        known_line_ids=ids,
        book=book,
        store=st,
        **persist_fate_kwargs(st, int(seq or 1), fields, existing),
    )


def _attach_fate(
    out: dict[str, Any],
    ch: Mapping[str, Any] | None,
    *,
    st=None,
    seq: int | None = None,
    kind: str = "outline",
    persist: bool = False,
) -> dict[str, Any]:
    from scribe3.fate_dearer import (
        contract_blocked,
        evaluate_fate_beats,
        evaluate_fate_prose,
        evaluate_fate_spine,
        evaluate_write_contract,
        load_fate_context,
        prose_fate_blocked,
        spine_fate_blocked,
    )
    keys = (
        "chapter_spine", "beats", "deductions", "scene_truth",
        "draft", "prose", "beats_meta", "clock", "place",
    )
    src = {**(ch if isinstance(ch, dict) else {}), **{k: out[k] for k in keys if k in out}}
    ctx = load_fate_context(st, int(seq or 1), src)
    if kind == "outline":
        rep = evaluate_fate_spine(src.get("chapter_spine"), ctx, ch=src)
        raw_beats = src.get("beats")
        beats_for_contract = raw_beats if raw_beats else None
        blocked = (
            contract_blocked(src.get("chapter_spine"), beats_for_contract, ctx, src)
            if persist else None
        )
    elif kind == "design":
        from scribe3.fate_dearer import WAVE_1_IDS, FateReport, _fate_block_message
        spine_rep = evaluate_fate_spine(src.get("chapter_spine"), ctx, ch=src)
        raw_beats = src.get("beats")
        beats_for_contract = raw_beats if isinstance(raw_beats, list) else []
        beats_rep = evaluate_fate_beats(
            beats_for_contract, src.get("chapter_spine"), ctx, ch=src,
        )
        errs = list(spine_rep.errors or []) + list(beats_rep.errors or [])
        seen: list[str] = []
        for e in errs:
            if e not in seen:
                seen.append(e)
        rep = FateReport(
            ok=not seen,
            errors=seen,
            mode=spine_rep.mode or beats_rep.mode,
            overlap={**(spine_rep.overlap or {}), **(beats_rep.overlap or {})},
            ore_n=int(spine_rep.ore_n or 0) + int(beats_rep.ore_n or 0),
            seeds_n=int(spine_rep.seeds_n or 0) + int(beats_rep.seeds_n or 0),
        )
        blocked = None
        if persist:
            blocked = contract_blocked(
                src.get("chapter_spine"), beats_for_contract, ctx, src,
            )
            wave = getattr(ctx, "wave", None) or WAVE_1_IDS
            hard = [e for e in (beats_rep.errors or []) if e in wave]
            if hard:
                miss = list((blocked or {}).get("missing") or [])
                for h in hard:
                    if h not in miss:
                        miss.append(h)
                blocked = {
                    "code": "fate_blocked",
                    "missing": miss,
                    "message": (blocked or {}).get("message") or _fate_block_message(miss),
                    "fate": (blocked or {}).get("fate") or {
                        **beats_rep.as_dict(),
                        "errors": seen,
                    },
                }
    elif kind == "beats":
        rep = evaluate_fate_beats(src.get("beats"), src.get("chapter_spine"), ctx, ch=src)
        blocked = (
            contract_blocked(src.get("chapter_spine"), src.get("beats"), ctx, src)
            if persist else None
        )
    else:
        text = str(src.get("draft") if kind == "draft" else src.get("prose") or "")
        if kind == "deduce":
            text = ""
        rep = evaluate_fate_prose(text, src, ctx, kind="final" if kind == "final" else "draft")
        blocked = None
        if persist and kind in ("draft", "final"):
            blocked = prose_fate_blocked(text, src, ctx, kind="final" if kind == "final" else "draft")
        elif persist and kind == "deduce":
            blocked = spine_fate_blocked(src.get("chapter_spine"), ctx, ch=src)
            if blocked is None:
                from scribe3.fate_dearer import WAVE_1_IDS, fate_dearer_mode
                if fate_dearer_mode() == "on":
                    ice3 = frozenset({"deduction_layers", "deduction_ore"})
                    hard = [e for e in rep.errors if e in (ctx.wave or WAVE_1_IDS) and e in ice3]
                    if hard:
                        from scribe3.fate_dearer import _fate_block_message
                        blocked = {
                            "code": "fate_blocked",
                            "missing": hard,
                            "message": _fate_block_message(hard),
                            "fate": rep.as_dict(),
                        }
    out = dict(out)
    out["fate"] = rep.as_dict()
    if blocked:
        return {
            "ok": False,
            "code": blocked.get("code") or "fate_blocked",
            "message": blocked.get("message") or "命运闸",
            "missing": blocked.get("missing") or [],
            "fate": blocked.get("fate") or rep.as_dict(),
            "source": out.get("source") or "llm",
        }
    return out


def thicken_outline(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    """旧入口。写大纲就是写这一章。"""
    return thicken_chapter_design(
        ch, llm_fn=llm_fn, persist_fn=persist_fn, seq=seq, extra=extra,
        st=st, work=work, focalizer=focalizer,
    )


def thicken_beats(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    """旧入口。写节拍就是写这一章。"""
    return thicken_chapter_design(
        ch, llm_fn=llm_fn, persist_fn=persist_fn, seq=seq, extra=extra,
        st=st, work=work, focalizer=focalizer,
    )


def dispatch_design_stage(stg: str, ch, *, extra: str = "") -> dict | None:
    """返回 skip 字典 / error 字典 / None=继续 thicken。

    调用方：_reject_stage_not_ready、thicken_stage、s3_generate_stage。
    大纲/节拍都走写这一章，不再另起旧两步。
    """
    from scribe3.world_surface import extra_authors, extra_gold

    if extra_authors(extra):
        return {
            "ok": False,
            "code": "extra_authors",
            "missing": ["extra_authors"],
            "message": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
            "stage": stg,
        }
    if stg in ("design", "outline", "beats") and extra_gold(extra):
        return {
            "ok": False,
            "code": "extra_gold",
            "missing": ["extra_gold"],
            "message": "规划 extra 不得交 14 槽金样或标题形拍头试卷",
            "stage": stg,
        }
    return None


def thicken_chapter_design(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    from scribe3.world_surface import extra_authors, extra_gold

    if extra_authors(extra):
        return {
            "ok": False,
            "code": "extra_authors",
            "missing": ["extra_authors"],
            "message": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
        }
    if extra_gold(extra):
        return {
            "ok": False,
            "code": "extra_gold",
            "missing": ["extra_gold"],
            "message": "规划 extra 不得交 14 槽金样或标题形拍头试卷",
        }
    if iceberg_ok_for(ch, "design", store=st, seq=seq) and not _extra_force(extra):
        from scribe3.narrative_contract import merge_iceberg_contract
        extra_fields = merge_iceberg_contract(ch, {})
        if persist_fn and extra_fields.get("narrative_contract"):
            persist_fn(extra_fields)
        return _attach_fate({
            "ok": True,
            "skipped": "章设计已过，不覆盖",
            "source": "existing",
            "synopsis": (ch or {}).get("synopsis"),
            "chapter_spine": (ch or {}).get("chapter_spine"),
            "beats": (ch or {}).get("beats"),
            "beats_meta": (ch or {}).get("beats_meta"),
            "contract_backfill": bool(extra_fields.get("narrative_contract")),
        }, ch, st=st, seq=seq, kind="design", persist=False)
    from scribe3.chapter_spine import assemble_synopsis_from_spine, known_line_ids_from_store
    from scribe3.clue_density import evaluate_chapter_design
    from scribe3.design_attempt import (
        first_open_slot, record_attempt, slim_attempts,
    )
    from scribe3.fate_dearer import parse_clock_place_labels
    known = known_line_ids_from_store(st) if st is not None else None
    book = load_design_book(st, seq, ch if isinstance(ch, dict) else {}, extra=extra) if st is not None else None

    def _run(retry_hint: str = "") -> tuple[str, dict[str, Any]]:
        prompt = build_stage_prompt(
            "design", ch, seq=seq, extra=extra, bible="", st=st,
            retry_hint=retry_hint,
        )
        raw_text = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["design"])
        return raw_text, parse_chapter_design_payload(raw_text, known_line_ids=known)

    def _eval(p: dict[str, Any]):
        if not p.get("ok"):
            return None
        return evaluate_chapter_design(
            p.get("chapter_spine"), p.get("beats"),
            known_line_ids=known,
            designated_beat=p.get("designated_beat"),
            book=book,
            clock=p.get("clock") or None,
            place=p.get("place") or None,
        )

    attempts: list[dict[str, Any]] = []
    raw, parsed = _run()
    if parsed.get("ok"):
        parsed["synopsis"] = assemble_synopsis_from_spine(parsed.get("chapter_spine") or {})
    dens = _eval(parsed)
    attempts.append(record_attempt(1, parsed, dens, raw=raw))
    if st is not None and hasattr(st, "save_design_attempt") and seq:
        try:
            st.save_design_attempt(int(seq), attempts[-1])
        except Exception:
            pass

    for rnd in range(4):
        if parsed.get("ok") and dens is not None and dens.ok:
            break
        if not parsed.get("ok"):
            raw, parsed = _run("结构还缺：先整份写出【章】和 ## 拍1/拍2/拍3。")
            if parsed.get("ok"):
                parsed["synopsis"] = assemble_synopsis_from_spine(parsed.get("chapter_spine") or {})
            dens = _eval(parsed)
            attempts.append(record_attempt(len(attempts) + 1, parsed, dens, raw=raw))
            if st is not None and hasattr(st, "save_design_attempt") and seq:
                try:
                    st.save_design_attempt(int(seq), attempts[-1])
                except Exception:
                    pass
            continue
        slot = first_open_slot(list(getattr(dens, "errors", None) or []), struct_ok=True)
        if not slot:
            break
        hint = _slot_edit_hint(
            slot, parsed.get("chapter_spine"), parsed.get("beats"), book, dens,
        )
        raw2, patch = _run(retry_hint=hint)
        parsed = _apply_slot_patch(slot, parsed, patch, raw2)
        dens = _eval(parsed)
        rec = record_attempt(len(attempts) + 1, parsed, dens, raw=raw2)
        rec["slot"] = slot
        attempts.append(rec)
        if st is not None and hasattr(st, "save_design_attempt") and seq:
            try:
                st.save_design_attempt(int(seq), rec)
            except Exception:
                pass
        raw = raw2

    best_clock = dict(parsed.get("clock") or {})
    best_place = dict(parsed.get("place") or {})
    if not parsed.get("ok") or dens is None or not dens.ok:
        thin_code = parsed.get("code") or ""
        if dens is not None and not dens.ok:
            if "choice_not_staged" in dens.errors:
                thin_code = "choice_not_staged"
            elif "second_choice" in dens.errors:
                thin_code = "second_choice"
            else:
                thin_code = "llm_thin"
        return _attach_fate({
            "ok": False,
            "code": thin_code or "llm_thin",
            "source": parsed.get("source") or "llm",
            "got": parsed.get("cn"),
            "need": "chapter_design",
            "message": "整份还没过：留下的几稿一块看过了，没有一整份能进书",
            "parsed": parsed,
            "chapter_spine": parsed.get("chapter_spine"),
            "beats": parsed.get("beats"),
            "density": (dens.as_dict() if dens is not None else parsed.get("density")),
            "missing": (dens.as_missing() if dens is not None else []),
            "attempts": slim_attempts(attempts),
        }, ch, st=st, seq=seq, kind="design", persist=False)
    fields: dict[str, Any] = {
        "chapter_spine": parsed["chapter_spine"],
        "beats": parsed["beats"],
    }
    if parsed.get("synopsis"):
        fields["synopsis"] = parsed["synopsis"]
    from scribe3.fate_dearer import (
        merge_clock_place,
        merge_world_fact,
        parse_world_fact_label,
    )
    clock, place = best_clock, best_place
    wf = parse_world_fact_label(raw)
    meta = merge_clock_place(ch if isinstance(ch, dict) else {}, clock, place)
    if wf:
        meta = merge_world_fact({"beats_meta": meta}, wf)
    meta = dict(meta or {})
    meta["schema_design"] = "chapter_design.v1"
    if parsed.get("designated_beat"):
        meta["designated_beat"] = parsed["designated_beat"]
    if book and (getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or getattr(book, "duty_who", "") or getattr(book, "duty_bill", "")):
        meta["duty"] = {
            "who": getattr(book, "duty_who", "") or "",
            "event": getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "",
            "bill": getattr(book, "duty_bill", "") or "",
        }
        meta["must_happen"] = meta["duty"]["event"]
    fields["beats_meta"] = meta
    try:
        from scribe3.world_surface import coerce_world_claim, groups_from_spine, merge_world_claim
        merged_ch = {**(ch if isinstance(ch, dict) else {}), **fields}
        derived = coerce_world_claim({
            "id": "wc.design",
            "claim": (wf or {}).get("text") or "",
            "groups": groups_from_spine(merged_ch),
        }, merged_ch)
        if derived:
            meta = merge_world_claim({"beats_meta": fields.get("beats_meta")}, derived)
            fields["beats_meta"] = meta
    except Exception:
        pass
    from scribe3.iceberg import sync_design_surface
    fields = sync_design_surface(fields, ch if isinstance(ch, dict) else None, store=st)
    blocked = _blocked_or_none(
        fields, existing=ch if isinstance(ch, dict) else None, st=st, seq=seq,
        extra=extra, book=book,
    )
    for _fate_rnd in range(3):
        if not blocked:
            break
        slot = first_open_slot(_blocked_error_ids(blocked), struct_ok=True)
        if not slot:
            break
        hint = _slot_edit_hint(
            slot, parsed.get("chapter_spine"), parsed.get("beats"), book, dens,
        )
        raw2, patch = _run(retry_hint=hint)
        parsed = _apply_slot_patch(slot, parsed, patch, raw2)
        dens = _eval(parsed)
        rec = record_attempt(len(attempts) + 1, parsed, dens, raw=raw2)
        rec["slot"] = slot
        attempts.append(rec)
        if st is not None and hasattr(st, "save_design_attempt") and seq:
            try:
                st.save_design_attempt(int(seq), rec)
            except Exception:
                pass
        raw = raw2
        if not parsed.get("ok") or dens is None or not dens.ok:
            break
        fields = {
            "chapter_spine": parsed["chapter_spine"],
            "beats": parsed["beats"],
        }
        if parsed.get("synopsis"):
            fields["synopsis"] = parsed["synopsis"]
        clock, place = dict(parsed.get("clock") or {}), dict(parsed.get("place") or {})
        wf = parse_world_fact_label(raw)
        meta = merge_clock_place(ch if isinstance(ch, dict) else {}, clock, place)
        if wf:
            meta = merge_world_fact({"beats_meta": meta}, wf)
        meta = dict(meta or {})
        meta["schema_design"] = "chapter_design.v1"
        if parsed.get("designated_beat"):
            meta["designated_beat"] = parsed["designated_beat"]
        if book and (getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or getattr(book, "duty_who", "") or getattr(book, "duty_bill", "")):
            meta["duty"] = {
                "who": getattr(book, "duty_who", "") or "",
                "event": getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "",
                "bill": getattr(book, "duty_bill", "") or "",
            }
            meta["must_happen"] = meta["duty"]["event"]
        fields["beats_meta"] = meta
        fields = sync_design_surface(fields, ch if isinstance(ch, dict) else None, store=st)
        blocked = _blocked_or_none(
            fields, existing=ch if isinstance(ch, dict) else None, st=st, seq=seq,
            extra=extra, book=book,
        )
    if blocked:
        return {
            "ok": False, "code": blocked["code"], "message": blocked["message"],
            "source": "llm", "fate": blocked.get("fate"),
            "missing": blocked.get("missing"),
            "chapter_spine": parsed.get("chapter_spine"),
            "beats": parsed.get("beats"),
            "attempts": slim_attempts(attempts),
        }
    from scribe3.narrative_contract import merge_iceberg_contract
    fields = merge_iceberg_contract({**(ch or {}), **fields}, fields)
    attached = _attach_fate(
        {"ok": True, "source": parsed.get("source") or "llm", **fields,
         "cn": parsed.get("cn"), "density": dens.as_dict(),
         "attempts": slim_attempts(attempts)},
        {**(ch or {}), **fields},
        st=st, seq=seq, kind="design", persist=bool(persist_fn),
    )
    if attached.get("ok") is False:
        attached = dict(attached)
        attached.setdefault("attempts", slim_attempts(attempts))
        return attached
    if persist_fn:
        persist_fn(fields)
        _emit_fate_artifacts("design", attached, fields, ch)
    return attached


def thicken_deduce(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "deduce", store=st, seq=seq)
    if not ready["ok"]:
        return {"ok": False, **ready}
    if iceberg_ok_for(ch, "deduction", store=st, seq=seq) and not _extra_force(extra):
        from scribe3.fate_dearer import extract_ore, load_ore, merge_ore
        ore = load_ore(ch if isinstance(ch, dict) else {})
        if not ore:
            ore = extract_ore(
                (ch or {}).get("deductions"),
                str((ch or {}).get("scene_truth") or ""),
                spine=(ch or {}).get("chapter_spine") if isinstance((ch or {}).get("chapter_spine"), dict) else None,
            )
        meta = merge_ore(ch if isinstance(ch, dict) else {}, ore)
        if persist_fn:
            persist_fn({"beats_meta": meta})
            _emit_fate_artifacts("deduce", {"beats_meta": meta}, {"beats_meta": meta}, ch)
        return _attach_fate({
            "ok": True,
            "skipped": "演绎已达覆盖地板，不覆盖正文；补抽 ore",
            "source": "existing",
            "deductions": (ch or {}).get("deductions"),
            "beats_meta": meta,
        }, {**(ch or {}), "beats_meta": meta}, st=st, seq=seq, kind="deduce", persist=False)
    from scribe3.deduce_helpers import is_heading_noise_role, resolve_against_cast
    involved = [
        x for x in list((ch or {}).get("involved_characters") or [])
        if not is_heading_noise_role(x)
    ]
    cast: list[Any] = []
    try:
        if st is not None and hasattr(st, "characters"):
            for c in (st.characters() or []):
                cast.append({
                    "id": getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None),
                    "name": getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else None),
                })
    except Exception:
        cast = []
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    prompt = build_stage_prompt("deduce", ch, seq=seq, extra=extra, bible=bible, st=st)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["deduce"])
    parsed = parse_deduce_payload(raw, involved=involved)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt(
                "deduce", ch, seq=seq, extra=extra, strict=True,
                previous=raw, bible=bible, st=st,
            ),
            STAGE_MAX_TOKENS["deduce"],
        )
        parsed = parse_deduce_payload(raw, involved=involved)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": "deduction_structure",
            "message": "演绎缺五层或空投影，禁止摘录/空白五栏充数。字数不是通过条件。",
            "parsed": parsed,
        }
    cleaned_deds: list[dict[str, Any]] = []
    for d in parsed.get("deductions") or []:
        if not isinstance(d, dict):
            continue
        if is_heading_noise_role(d.get("character_id") or d.get("character_name") or ""):
            continue
        d["character_id"] = resolve_against_cast(
            d.get("character_id") or d.get("character_name") or "", cast
        )
        if is_heading_noise_role(d.get("character_id") or ""):
            continue
        if d.get("character_id"):
            d["character_name"] = str(d["character_id"]).split(":", 1)[-1]
        cleaned_deds.append(d)
    parsed["deductions"] = cleaned_deds
    fields: dict[str, Any] = {"deductions": cleaned_deds}
    if parsed.get("scene_truth"):
        fields["scene_truth"] = parsed["scene_truth"]
    known = {resolve_against_cast(c.get("id") or c.get("name"), cast) for c in cast if c}
    seen: list[str] = []
    for d in parsed.get("deductions") or []:
        cid = str((d or {}).get("character_id") or "").strip()
        if not cid or cid in seen:
            continue
        if is_heading_noise_role(cid):
            continue
        if known and cid not in known:
            continue
        seen.append(cid)
    if seen:
        fields["involved_characters"] = seen
    from scribe3.fate_dearer import extract_ore, merge_ore
    ore = extract_ore(
        cleaned_deds,
        str(fields.get("scene_truth") or ""),
        spine=(ch or {}).get("chapter_spine") if isinstance((ch or {}).get("chapter_spine"), dict) else None,
    )
    fields["beats_meta"] = merge_ore(ch if isinstance(ch, dict) else {}, ore)
    blocked = _blocked_or_none(fields, existing=ch if isinstance(ch, dict) else None, st=st, seq=seq)
    if blocked:
        return {
            "ok": False, "code": blocked["code"], "message": blocked["message"],
            "source": "llm", "fate": blocked.get("fate"),
            "missing": blocked.get("missing"),
        }
    attached = _attach_fate(
        {"ok": True, "source": "llm", **fields, "cn": parsed["cn"]},
        {**(ch or {}), **fields},
        st=st, seq=seq, kind="deduce", persist=bool(persist_fn),
    )
    if attached.get("ok") is False:
        return attached
    if persist_fn:
        persist_fn(fields)
        _emit_fate_artifacts("deduce", attached, fields, ch)
    return attached


def thicken_draft(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "draft", store=st, seq=seq)
    if not ready["ok"]:
        return {"ok": False, **ready}
    if iceberg_ok_for(ch, "draft", store=st, seq=seq) and not _extra_force(extra):
        from scribe3.world_surface import claim_paid, load_world_claim, surface_of, world_surface_mode
        skip = True
        if world_surface_mode() == "on":
            claim = load_world_claim(ch if isinstance(ch, dict) else {})
            if claim and not claim_paid(surface_of(ch), claim).paid:
                skip = False
        if skip:
            return _attach_fate({
                "ok": True,
                "skipped": "排演已有结构稿，不覆盖",
                "source": "existing",
                "draft": (ch or {}).get("draft") or (ch or {}).get("draft_prose"),
            }, ch, st=st, seq=seq, kind="draft", persist=False)
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    parsed: dict[str, Any] = {"draft": "", "cn": 0, "ok": False}
    prompt = build_stage_prompt("draft", ch, seq=seq, extra=extra, bible=bible, st=st)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["draft"])
    parsed = parse_draft_payload(raw)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt(
                "draft", ch, seq=seq, extra=extra, bible=bible,
                strict=True, previous=raw, st=st,
            ),
            STAGE_MAX_TOKENS["draft"],
        )
        parsed = parse_draft_payload(raw)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": "draft_structure",
            "rounds": 2,
            "message": "排演为空，禁止把空稿当 chapter.draft。字数不是通过条件。",
            "parsed": parsed,
        }
    attached = _attach_fate(
        {"ok": True, "source": "llm", "draft": parsed["draft"], "cn": parsed["cn"]},
        {**(ch or {}), "draft": parsed["draft"]},
        st=st, seq=seq, kind="draft", persist=bool(persist_fn),
    )
    if attached.get("ok") is False:
        return attached
    if persist_fn:
        persist_fn({"draft": parsed["draft"]})
        _persist_reextracted_ore(persist_fn, ch)
        _emit_fate_artifacts("draft", attached, {"draft": parsed["draft"]}, ch)
    return attached


def thicken_final(
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    ready = stage_ready(ch, "final", store=st, seq=seq)
    if not ready["ok"]:
        return {"ok": False, **ready}
    existing = str((ch or {}).get("prose") or "").strip()
    if existing and not _extra_force(extra):
        from scribe3.world_surface import claim_paid, load_world_claim, surface_of, world_surface_mode
        skip = True
        if world_surface_mode() == "on":
            claim = load_world_claim(ch if isinstance(ch, dict) else {})
            if claim and not claim_paid(surface_of(ch), claim).paid:
                skip = False
        if skip:
            return _attach_fate({
                "ok": True,
                "skipped": "定稿已有正文，不覆盖",
                "source": "existing",
                "prose": existing,
            }, ch, st=st, seq=seq, kind="final", persist=False)
    bible = _bible_for_thicken(st, work, ch, extra, focalizer, seq)
    parsed: dict[str, Any] = {"prose": "", "cn": 0, "ok": False}
    prompt = build_stage_prompt("final", ch, seq=seq, extra=extra, bible=bible, st=st)
    raw = _call_llm(llm_fn, prompt, STAGE_MAX_TOKENS["final"])
    parsed = parse_final_payload(raw)
    if not parsed["ok"]:
        raw = _call_llm(
            llm_fn,
            build_stage_prompt(
                "final", ch, seq=seq, extra=extra, bible=bible,
                strict=True, previous=raw, st=st,
            ),
            STAGE_MAX_TOKENS["final"],
        )
        parsed = parse_final_payload(raw)
    if not parsed["ok"]:
        return {
            "ok": False,
            "code": "llm_thin",
            "source": "llm",
            "got": parsed["cn"],
            "need": "final_structure",
            "rounds": 2,
            "message": "定稿为空，禁止把空稿当 prose。字数不是通过条件。",
            "parsed": parsed,
        }
    attached = _attach_fate(
        {"ok": True, "source": "llm", "prose": parsed["prose"], "cn": parsed["cn"]},
        {**(ch or {}), "prose": parsed["prose"]},
        st=st, seq=seq, kind="final", persist=bool(persist_fn),
    )
    if attached.get("ok") is False:
        return attached
    if persist_fn:
        persist_fn({"prose": parsed["prose"]})
        _persist_reextracted_ore(persist_fn, ch)
        _emit_fate_artifacts("final", attached, {"prose": parsed["prose"]}, ch)
    return attached


def _persist_reextracted_ore(persist_fn, ch) -> None:
    try:
        from scribe3.fate_dearer import extract_ore, merge_ore
        from scribe3.world_surface import load_world_claim, world_surface_mode
        if world_surface_mode() != "on":
            return
        src = ch if isinstance(ch, dict) else {}
        claim = load_world_claim(src)
        if not claim:
            return
        ore = extract_ore(
            src.get("deductions"), str(src.get("scene_truth") or ""),
            spine=src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else None,
            claim=claim,
        )
        persist_fn({"beats_meta": merge_ore(src, ore)})
    except Exception:
        return


def _emit_fate_artifacts(kind: str, out: Mapping[str, Any], fields: dict, ch) -> None:
    try:
        from scribe3.pipeline_recorder import put_fate_artifact
        from scribe3.chapter_spine import assemble_synopsis_from_spine, format_must_land, is_v1
    except Exception:
        return
    src = {**(ch if isinstance(ch, dict) else {}), **(fields or {})}
    try:
        from scribe3.world_surface import gesture_fingerprint, load_world_claim
        import json as _json
        claim = load_world_claim(src)
        put_fate_artifact(
            "gate_input", "gate_input",
            (_json.dumps({
                "kind": kind,
                "claim": {
                    "id": getattr(claim, "id", None),
                    "groups": getattr(claim, "groups", None),
                } if claim else None,
                "fate": (out.get("fate") if isinstance(out, dict) else None),
            }, ensure_ascii=False) + "\n" + str((out or {}).get("message") or ""))[:2000],
        )
        prints = gesture_fingerprint(
            src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else None,
            src.get("beats") if isinstance(src.get("beats"), list) else None,
        )
        if prints:
            put_fate_artifact(
                "gesture_print", "gesture",
                "; ".join(
                    f"{p.actor}:{','.join(sorted(p.roles))}/{p.obj_class}"
                    for p in prints
                )[:400],
            )
    except Exception:
        pass
    spine = src.get("chapter_spine") if is_v1(src.get("chapter_spine")) else None
    if kind in ("outline", "design"):
        if spine:
            put_fate_artifact("spine_card", "spine", assemble_synopsis_from_spine(spine)[:400])
        fate = out.get("fate") if isinstance(out, dict) else {}
        put_fate_artifact(
            "fate_delta", "fate",
            "fate " + " / ".join((fate or {}).get("errors") or ["ok"])[:200],
        )
        land = format_must_land(spine, chapter=src)
        if land:
            put_fate_artifact("must_land", "must_land", land[:800])
    elif kind in ("beats", "design", "deduce"):
        land = format_must_land(spine, chapter=src)
        if land:
            put_fate_artifact("must_land", "must_land", land[:800])
        if kind == "deduce":
            ore = (src.get("beats_meta") or {}).get("ore") if isinstance(src.get("beats_meta"), dict) else None
            if ore:
                put_fate_artifact("ore_atoms", "ore", str(ore)[:800])
    elif kind in ("draft", "final"):
        put_fate_artifact(
            "choice_span", "choice",
            (fields.get("draft") or fields.get("prose") or "")[:400],
        )
    meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
    seeds = meta.get("seeds")
    if seeds:
        put_fate_artifact("seed_census", "seeds", str(seeds)[:400])


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
    from scribe3.world_surface import extra_authors
    if extra_authors(extra):
        return {
            "ok": False,
            "code": "extra_authors",
            "missing": ["extra_authors"],
            "message": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
        }
    kind = normalize_stage(stage)
    hit = dispatch_design_stage(kind, ch, extra=extra)
    if hit is not None:
        return hit
    fns = {
        "design": thicken_chapter_design,
        "outline": thicken_chapter_design,
        "beats": thicken_chapter_design,
        "deduce": thicken_deduce,
        "draft": thicken_draft,
        "final": thicken_final,
    }
    fn = fns.get(kind)
    if fn is None:
        return {"ok": False, "code": "unknown_stage", "message": f"无独立生成链: {stage}"}
    return fn(
        ch, llm_fn=llm_fn, persist_fn=persist_fn, seq=seq, extra=extra,
        st=st, work=work, focalizer=focalizer,
    )

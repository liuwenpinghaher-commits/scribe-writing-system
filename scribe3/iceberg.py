"""冰山前置：写厚水下质量，正文只露出水面。

字数在这里 = 「这块材料够不够撑一场戏」，不是文学分、不是宣称。
不进 GATE-B 的 80 字「可开写」口径，不进 may_claim_*。
空字段 = 还没写，允许。一旦写入大纲/节拍/演绎，必须达到覆盖地板——
80 字口号不能落库，否则系统会把它当成「已经有大纲」。
"""
from __future__ import annotations

import os
import re
from typing import Any

# 水下质量地板（覆盖/信息量，不是评分）
SYNOPSIS_FLOOR = 500
BEAT_EACH_FLOOR = 500
BEAT_SUM_FLOOR = 2000
DEDUCTION_FLOOR = 5000
DRAFT_FLOOR = 10000
PROSE_SURFACE = 5000  # 水面：正文要有足够面积让冰山露出来

# 注入帽：刚过闸必须全给；只砍「写超了很多」的尾巴。final 与 thicken 同档。
# 设定 kind 与章字段共用本表；讨论/写作/名片/秘密由组装层决定，clip_for 不加 purpose。
INJECT_CAP = {
    "synopsis": 2500,
    "beat": 1200,
    "scene_truth": 2500,
    "deduction": 6000,
    "draft": 12000,
    "character_public": 2500,
    "faction_public": 2500,
    "item": 1200,
    "term": 1200,
    "world_rule": 1200,
}
DEDUCTION_PACK_CAP = 8500  # 5000 闸 + 2500 真相 + ≤1000 头尾
NEAR_FLOOR_RATIO = 1.2
# 包级帽（不是 INJECT_CAP 行）
CARD_LINE_CAP = 80
CARDS_PACK_CAP = 1500
NAMED_PACK_SOFT_CAP_NARROW = 4500
NAMED_PACK_SOFT_CAP_WIDE = 12000

_WS = re.compile(r"\s+")

# 这些阶段是在写厚冰山，不得用冰山闸卡住
_THICKEN_PHASES = frozenset({
    "outline", "plan", "beats", "design", "chapter_design", "deduce", "scaffold", "meta",
})
_PROSE_PHASES = frozenset({"", "draft", "final", "write", "prose"})


def cn_len(text: str | None) -> int:
    from scribe3.llm_visible import strip_thinking_markup
    return len(_WS.sub("", strip_thinking_markup(text or "")))


def _floor_for(field: str) -> int:
    if field in ("synopsis", "beat"):
        return 0
    return {
        "synopsis": SYNOPSIS_FLOOR,
        "beat": BEAT_EACH_FLOOR,
        "scene_truth": 0,
        "deduction": 0,
        "draft": 0,
    }.get(field, 0)


def clip_for(field: str, text: str | None) -> str:
    """唯一冰山裁切：近地板不裁；否则裁到 INJECT_CAP 且不低于地板。"""
    raw = text or ""
    if not raw:
        return ""
    n = cn_len(raw)
    floor = _floor_for(field)
    cap = int(INJECT_CAP.get(field) or 0)
    if floor and n <= int(floor * NEAR_FLOOR_RATIO):
        return raw
    if not cap or n <= cap:
        return raw
    # 按字符裁到 cap，尽量不拆到地板以下
    keep = max(cap, floor)
    if len(raw) <= keep:
        return raw
    return raw[:keep]


def named_pack_soft_cap(*, work: str | None) -> int:
    """点名包软顶。走 resolve_write_caps(work)：48k→4500，96k→12000。

    显式 ``SCRIBE3_CODEX_INJECT_CAP`` 正整数覆盖两档（运维逃生）。
    禁止 ``get_codex_inject_cap()`` 无 work 各算各的。
    """
    raw = (os.environ.get("SCRIBE3_CODEX_INJECT_CAP") or "").strip()
    if raw.isdigit():
        return max(500, int(raw))
    from scribe3.context_budget import resolve_write_caps
    caps = resolve_write_caps(work)
    ph = int(caps.get("prompt_hard") or 0)
    if ph >= 90_000:
        return NAMED_PACK_SOFT_CAP_WIDE
    return NAMED_PACK_SOFT_CAP_NARROW


def iceberg_enabled() -> bool:
    raw = os.environ.get("SCRIBE3_ICEBERG_WRITE")
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def _beat_lens(ch: dict) -> list[int]:
    out: list[int] = []
    for b in ch.get("beats") or []:
        if isinstance(b, dict):
            out.append(cn_len(b.get("text")))
        else:
            out.append(cn_len(str(b or "")))
    return [n for n in out if n > 0]


def _deduction_sum(ch: dict) -> int:
    total = 0
    for d in ch.get("deductions") or []:
        if isinstance(d, dict):
            total += cn_len(d.get("prose") or d.get("text"))
        else:
            total += cn_len(str(d or ""))
    return total


def _draft_len(ch: dict) -> int:
    """排演稿：独立字段优先，避免把读者正文误当成草稿。"""
    for k in ("draft_prose", "rehearsal", "draft"):
        v = ch.get(k)
        if isinstance(v, str) and v.strip():
            return cn_len(v)
    return 0


def evaluate_iceberg(
    ch: dict | None,
    *,
    for_phase: str = "draft",
    known_line_ids: set | None = None,
    st=None,
    seq: int | None = None,
    fate_ctx=None,
) -> dict[str, Any]:
    """返回 {ok, missing, measures, message}。密度旗 on/shadow 时 Ice1/Ice2 不验字数。

    命运闸必须经 ``load_fate_context(st, seq, ch)``（或显式 ``fate_ctx``）。
    禁止空 FateCtx：否则旗 on 时齐全章也会恒报 who_pays_missing。

    play-contract：evaluate_iceberg 语义闸已废，只保留函数壳给旧调用点。
    """
    return {"ok": True, "missing": [], "measures": {}, "message": "", "code": ""}
    meta = ch if isinstance(ch, dict) else {}
    phase = (for_phase or "draft").strip().lower()
    syn = cn_len(meta.get("synopsis"))
    beats = _beat_lens(meta)
    bsum = sum(beats)
    thin_beats = [i + 1 for i, n in enumerate(beats) if n < BEAT_EACH_FLOOR]
    dsum = _deduction_sum(meta)
    draft_n = _draft_len(meta)
    prose_n = cn_len(meta.get("prose"))

    from scribe3.clue_density import (
        clue_density_mode,
        evaluate_beats,
        evaluate_spine,
    )
    from scribe3.chapter_spine import is_v1

    mode = clue_density_mode()
    missing: list[dict[str, Any]] = []
    density: dict[str, Any] = {"mode": mode}

    if mode == "off":
        if syn < SYNOPSIS_FLOOR:
            missing.append({"id": "synopsis", "got": syn, "need": SYNOPSIS_FLOOR})
        if len(beats) < 3:
            missing.append({"id": "beat_count", "got": len(beats), "need": 3})
        if thin_beats:
            missing.append({
                "id": "beat_each", "got": beats, "need": BEAT_EACH_FLOOR,
                "thin": thin_beats,
            })
        if bsum < BEAT_SUM_FLOOR:
            missing.append({"id": "beat_sum", "got": bsum, "need": BEAT_SUM_FLOOR})
    else:
        if is_v1(meta.get("chapter_spine")):
            spine_rep = evaluate_spine(meta.get("chapter_spine"), known_line_ids=known_line_ids)
            density["spine"] = spine_rep.as_dict()
            missing.extend(spine_rep.as_missing())
        else:
            missing.append({"id": "spine_slots", "detail": "empty", "got": 0, "need": 1})
        beat_rows = [b for b in (meta.get("beats") or []) if b]
        if beat_rows:
            spine_for_beats = meta.get("chapter_spine") if is_v1(meta.get("chapter_spine")) else None
            beat_rep = evaluate_beats(beat_rows, spine=spine_for_beats)
            density["beats"] = beat_rep.as_dict()
            missing.extend(beat_rep.as_missing())
        else:
            missing.append({"id": "beat_count", "got": 0, "need": 3})
        try:
            from scribe3.clue_density import (
                chapter_design_mode,
                design_book_mode,
                evaluate_design_continuity,
            )
            if chapter_design_mode() == "on" and design_book_mode() == "on" and st is not None:
                from scribe3.stage_generate import load_design_book
                from scribe3.fate_dearer import load_clock, load_place
                book = load_design_book(st, seq, meta)
                for e in evaluate_design_continuity(
                    meta.get("chapter_spine") if is_v1(meta.get("chapter_spine")) else None,
                    book=book,
                    clock=load_clock(meta),
                    place=load_place(meta),
                ):
                    missing.append({"id": e, "detail": e})
        except Exception:
            pass

    # Ice3/4/6：空仍不过；字数只进 measures，不进 missing。
    if not (meta.get("deductions") or []) or dsum == 0:
        missing.append({"id": "deduction", "got": 0, "need": 1, "detail": "empty"})
    if phase in ("final", "write") and draft_n == 0:
        missing.append({"id": "draft", "got": 0, "need": 1, "detail": "empty"})

    fate_rep: dict[str, Any] = {}
    try:
        from scribe3.fate_dearer import (
            deduction_layers_ok,
            evaluate_fate_prose,
            evaluate_fate_spine,
            extract_ore,
            fate_dearer_mode,
            fate_wave_ids,
            load_fate_context,
            load_ore,
        )
        fmode = fate_dearer_mode()
        n = int(seq or meta.get("seq") or 1)
        fctx = fate_ctx if fate_ctx is not None else load_fate_context(st, n, meta)
        spine_f = evaluate_fate_spine(
            meta.get("chapter_spine") if isinstance(meta.get("chapter_spine"), dict) else {},
            fctx,
            ch=meta,
        )
        prose_txt = str(meta.get("prose") or meta.get("draft") or "")
        prose_f = evaluate_fate_prose(prose_txt, meta, fctx, kind="draft")
        fate_ids = list(dict.fromkeys(list(spine_f.errors) + list(prose_f.errors)))
        fate_rep = {
            "mode": fmode,
            "errors": fate_ids,
            "ok": not fate_ids,
            "spine": spine_f.as_dict(),
            "prose": prose_f.as_dict(),
        }
        if fmode == "on":
            wave = fate_wave_ids(mode="on")
            deds = [d for d in (meta.get("deductions") or []) if isinstance(d, dict)]
            if deds and not deduction_layers_ok(deds):
                if "deduction_layers" not in {m.get("id") for m in missing}:
                    missing.append({"id": "deduction_layers", "detail": "fate"})
            if deds and not (load_ore(meta) or extract_ore(deds, str(meta.get("scene_truth") or ""))):
                if "deduction_ore" not in {m.get("id") for m in missing}:
                    missing.append({"id": "deduction_ore", "detail": "fate"})
            for eid in fate_ids:
                if eid in wave and eid not in {m.get("id") for m in missing}:
                    missing.append({"id": eid, "detail": "fate"})
    except Exception:
        fate_rep = {}

    try:
        from scribe3.design_play import play_design_ready
        from scribe3.stage_generate import _missing_bucket
        if play_design_ready(meta):
            missing = [
                m for m in missing
                if _missing_bucket(str(m.get("id") or "")) != "design"
            ]
    except Exception:
        pass

    ok = not missing
    bits = []
    for m in missing:
        if "got" in m and "need" in m:
            bits.append(f"{m['id']} {m['got']}<{m['need']}")
        else:
            bits.append(str(m.get("detail") or m.get("id") or ""))
    if mode == "off":
        msg = (
            "冰山已厚，可以进正文。"
            if ok else
            "冰山未厚，先进大纲/节拍/演绎写厚（不是刷字数，是把水下质量堆够）："
            + "；".join(bits)
        )
    else:
        msg = (
            "线索密度已过，可以进正文。"
            if ok else
            "情节薄：补原子（选择/代价/线），禁止烟/锅/巷凑句："
            + "；".join(bits)
        )
    return {
        "ok": ok,
        "missing": missing,
        "measures": {
            "synopsis": syn,
            "beats": beats,
            "beat_sum": bsum,
            "deduction": dsum,
            "draft": draft_n,
            "prose": prose_n,
        },
        "floors": {
            "synopsis": SYNOPSIS_FLOOR,
            "beat_each": BEAT_EACH_FLOOR,
            "beat_sum": BEAT_SUM_FLOOR,
            "deduction": DEDUCTION_FLOOR,
            "draft": DRAFT_FLOOR,
            "prose_surface": PROSE_SURFACE,
        },
        "density": density,
        "fate": fate_rep,
        "message": msg,
        "role": "iceberg_substrate",
    }


def should_block_prose_write(phase: str | None, *, write_intent: bool) -> bool:
    if not write_intent:
        return False
    p = (phase or "draft").strip().lower()
    if p in _THICKEN_PHASES:
        return False
    return p in _PROSE_PHASES


def design_half_block(detail: str) -> dict[str, Any]:
    """旧半稿闸已废。"""
    return {
        "code": "stage_gone",
        "http": 410,
        "message": "章纲/节拍半稿已废。请走 duty → design。",
        "missing": [{"id": "design_half", "detail": detail}],
    }


def sync_design_surface(
    fields: dict[str, Any] | None,
    existing: dict[str, Any] | None = None,
    *,
    store=None,
) -> dict[str, Any]:
    """设计落库一张嘴：本次带 chapter_spine 且旗 on 才覆盖简介/四义；只 PATCH 简介不动。"""
    return dict(fields or {})
    out = dict(fields or {})
    from scribe3.clue_density import design_book_mode
    if design_book_mode() != "on":
        return out
    if "chapter_spine" not in out:
        return out
    spine = out.get("chapter_spine")
    from scribe3.chapter_spine import assemble_synopsis_from_spine, is_v1
    if is_v1(spine):
        out["synopsis"] = assemble_synopsis_from_spine(spine)
    prev = (existing or {}).get("narrative_contract")
    if isinstance(prev, dict) and (prev.get("locked") or str(prev.get("source") or "") == "author"):
        pass
    else:
        try:
            from scribe3.narrative_contract import (
                extract_contract_from_spine,
                validate_narrative_contract,
            )
            extracted = extract_contract_from_spine(spine)
            nxt = dict(prev) if isinstance(prev, dict) else {}
            nxt.update({k: v for k, v in extracted.items() if v})
            nxt["source"] = "iceberg"
            nxt["schema"] = nxt.get("schema") or "narrative_contract.v1"
            out["narrative_contract"] = validate_narrative_contract(nxt)
        except Exception:
            pass
    involved: list[str] = []
    if store is not None and hasattr(store, "characters"):
        from scribe3.chapter_spine import slot_text
        cast_blob = slot_text((spine or {}).get("cast") if isinstance(spine, dict) else "")
        try:
            for c in (store.characters() or []):
                name = ""
                cid = ""
                if isinstance(c, dict):
                    name = str(c.get("name") or "")
                    cid = str(c.get("id") or c.get("oid") or "")
                else:
                    name = str(getattr(c, "name", "") or "")
                    cid = str(getattr(c, "id", "") or getattr(c, "oid", "") or "")
                if name and name in cast_blob:
                    involved.append(cid if cid.startswith("role:") else (f"role:{name}" if name else cid))
        except Exception:
            involved = []
    out["involved_characters"] = involved
    return out


def persist_fields_blocked(
    fields: dict | None,
    *,
    existing: dict | None = None,
    known_line_ids: set | None = None,
    fate_ctx=None,
    chapter: dict | None = None,
    book=None,
    store=None,
) -> dict[str, Any] | None:
    """写入大纲/节拍/演绎时的硬闸。None=放行。

    空串/空列表 = 尚未写，允许。旗 on 验线索原子；shadow 只报告不 422；off 走旧字数。

    play-contract：persist 语义闸已废。
    """
    return None
    if not iceberg_enabled() or not isinstance(fields, dict):
        return None
    from scribe3.chapter_spine import is_v1, slot_text
    from scribe3.clue_density import (
        chapter_design_mode,
        clue_density_mode,
        design_book_mode,
        evaluate_beats,
        evaluate_chapter_design,
        evaluate_spine,
    )

    mode = clue_density_mode()
    missing: list[dict[str, Any]] = []
    warnings: list[str] = []

    def _block(msg: str) -> dict[str, Any]:
        bits = []
        for m in missing:
            if "got" in m and "need" in m:
                bits.append(f"{m['id']} {m['got']}<{m['need']}")
            else:
                bits.append(str(m.get("detail") or m.get("id") or ""))
        top = "iceberg_thin_persist"
        if any((m.get("id") if isinstance(m, dict) else None) == "design_half" for m in missing):
            top = "design_half"
        return {
            "code": top,
            "message": msg + ("：" + "；".join(bits) if bits else ""),
            "missing": missing,
            "warnings": warnings,
            "role": "iceberg_thin_persist" if top == "design_half" else "iceberg_substrate",
        }

    def _check_deductions() -> None:
        if "deductions" not in fields or fields.get("deductions") is None:
            return
        deds = [d for d in (fields.get("deductions") or []) if isinstance(d, dict)]
        if not deds:
            return
        try:
            from scribe3.fate_dearer import (
                deduction_layers_ok,
                extract_ore,
                fate_dearer_mode,
            )
        except Exception:
            return
        if fate_dearer_mode() != "on":
            return
        if not deduction_layers_ok(deds):
            missing.append({"id": "deduction_layers", "detail": "fate"})
        truth = str(fields.get("scene_truth") or (existing or {}).get("scene_truth") or "")
        if not extract_ore(deds, truth):
            missing.append({"id": "deduction_ore", "detail": "fate"})

    def _fate_hit() -> dict[str, Any] | None:
        if fate_ctx is None:
            return None
        try:
            from scribe3.fate_dearer import (
                WAVE_1_IDS,
                contract_blocked,
                evaluate_fate_prose,
                fate_dearer_mode,
                spine_fate_blocked,
            )
        except Exception:
            return None
        if fate_dearer_mode() != "on":
            return None
        merged = {**(chapter or existing or {}), **(fields or {})}
        writing_design = (
            fields.get("chapter_spine") is not None or fields.get("beats") is not None
        )
        try:
            from scribe3.design_play import play_design_ready
            play_ok = play_design_ready(chapter or existing) or play_design_ready(merged)
        except Exception:
            play_ok = False
        if play_ok and not writing_design:
            pass
        elif fields.get("chapter_spine") or "beats_meta" in (fields or {}) or "beats" in (fields or {}):
            if "beats" in (fields or {}):
                beats_for_contract = fields.get("beats")
            else:
                beats_for_contract = (existing or {}).get("beats")
            from scribe3.clue_density import chapter_design_mode
            kind_hint = "design" if (
                chapter_design_mode() == "on"
                and (fields.get("chapter_spine") is not None or fields.get("beats") is not None)
            ) else ""
            if kind_hint == "design":
                if not isinstance(beats_for_contract, list):
                    beats_for_contract = []
            elif not beats_for_contract:
                beats_for_contract = None
            hit = contract_blocked(
                fields.get("chapter_spine") or (existing or {}).get("chapter_spine"),
                beats_for_contract,
                fate_ctx,
                merged,
            )
            if hit:
                return hit
            if kind_hint == "design" and isinstance(beats_for_contract, list):
                try:
                    from scribe3.fate_dearer import evaluate_fate_beats
                    brep = evaluate_fate_beats(
                        beats_for_contract,
                        fields.get("chapter_spine") or (existing or {}).get("chapter_spine"),
                        fate_ctx,
                        ch=merged,
                    )
                    wave = getattr(fate_ctx, "wave", None) or WAVE_1_IDS
                    hard = [e for e in (brep.errors or []) if e in wave]
                    if hard:
                        from scribe3.fate_dearer import _fate_block_message
                        return {
                            "code": "fate_blocked",
                            "missing": hard,
                            "message": _fate_block_message(hard),
                            "fate": brep.as_dict(),
                        }
                except Exception:
                    pass
        if "deductions" in (fields or {}):
            rep = evaluate_fate_prose("", merged, fate_ctx)
            wave = getattr(fate_ctx, "wave", None) or WAVE_1_IDS
            # Ice3 persist 只拦五层/矿抽取；落地是 draft/final 的事
            ice3 = frozenset({"deduction_layers", "deduction_ore"})
            hard = [e for e in rep.errors if e in wave and e in ice3]
            if hard:
                from scribe3.fate_dearer import _fate_block_message
                return {
                    "code": "fate_blocked",
                    "missing": hard,
                    "message": _fate_block_message(hard),
                    "fate": rep.as_dict(),
                }
        return None

    spine_in = fields.get("chapter_spine") if "chapter_spine" in fields else None
    has_spine_now = is_v1(spine_in)
    has_spine_existing = is_v1((existing or {}).get("chapter_spine"))

    if chapter_design_mode() == "on" and (
        "chapter_spine" in (fields or {}) or "beats" in (fields or {})
    ):
        if design_book_mode() == "on" and store is not None and book is None:
            missing.append({"id": "design_book_missing", "detail": "store_without_book"})
            return _block("有书却没带上户口，禁止只考表格")
        merged_spine = (
            fields["chapter_spine"] if "chapter_spine" in fields
            else (existing or {}).get("chapter_spine")
        )
        merged_beats = (
            fields["beats"] if "beats" in fields
            else (existing or {}).get("beats")
        )
        have_s = is_v1(merged_spine)
        have_b = bool(merged_beats)
        if not have_s or not have_b:
            missing.append({
                "id": "design_half",
                "detail": "spine_without_beats" if have_s else "beats_without_spine",
            })
            return _block(
                "旗 on：禁止只写一半。请一次提交 spine+beats，或 s3_generate_stage(stage=design)"
            )
        want = None
        meta = (fields.get("beats_meta") or (existing or {}).get("beats_meta") or {})
        if not isinstance(meta, dict):
            meta = {}
        play_txt = str(meta.get("play") or "")
        if not play_txt and isinstance((existing or {}).get("beats_meta"), dict):
            play_txt = str(((existing or {}).get("beats_meta") or {}).get("play") or "")
        if play_txt:
            from scribe3.design_play import persist_play_design_blocked
            packed = {
                "chapter_spine": merged_spine,
                "beats": merged_beats,
                "beats_meta": {**meta, "play": play_txt},
            }
            hit = persist_play_design_blocked(
                packed, book=book, store=store, existing=existing,
            )
            if hit:
                return {
                    "code": hit.get("code") or "extract_thin",
                    "message": hit.get("message") or "表还不是这篇戏",
                    "missing": hit.get("missing") or [],
                    "warnings": warnings,
                    "role": "iceberg_substrate",
                }
            _check_deductions()
            if missing:
                return _block("不能把薄材料存成大纲/节拍/演绎。补情节原子（选择/代价/线），禁止烟/锅/巷凑句")
            return _fate_hit()
        if isinstance(meta, dict) and meta.get("designated_beat"):
            want = meta.get("designated_beat")
        ev_clock = ev_place = None
        if design_book_mode() == "on":
            from scribe3.fate_dearer import load_clock, load_place
            meta_ch = {"beats_meta": meta if isinstance(meta, dict) else {}}
            ev_clock = load_clock(meta_ch)
            ev_place = load_place(meta_ch)
        rep = evaluate_chapter_design(
            merged_spine, merged_beats,
            known_line_ids=known_line_ids,
            designated_beat=want,
            book=book,
            clock=ev_clock,
            place=ev_place,
        )
        if mode == "on" and not rep.ok:
            missing.extend(rep.as_missing())
        _check_deductions()
        if missing:
            return _block("不能把薄材料存成大纲/节拍/演绎。补情节原子（选择/代价/线），禁止烟/锅/巷凑句")
        return _fate_hit()

    # 1) 本次含 chapter_spine
    if has_spine_now:
        rep = evaluate_spine(spine_in, known_line_ids=known_line_ids)
        if mode == "on" and not rep.ok:
            missing.extend(rep.as_missing())
        if "beats" in fields and fields.get("beats") is not None:
            beat_rows = [b for b in (fields.get("beats") or []) if b]
            if beat_rows:
                brep = evaluate_beats(beat_rows, spine=spine_in)
                if mode == "on" and not brep.ok:
                    missing.extend(brep.as_missing())
        _check_deductions()
        if missing:
            return _block("不能把薄材料存成大纲/节拍/演绎。补情节原子（选择/代价/线），禁止烟/锅/巷凑句")
        return _fate_hit()

    # 2) 章上已有 spine，本次只改 beats/其它
    if has_spine_existing and "chapter_spine" not in fields:
        if "beats" in fields and fields.get("beats") is not None:
            beat_rows = [b for b in (fields.get("beats") or []) if b]
            if beat_rows:
                brep = evaluate_beats(beat_rows, spine=(existing or {}).get("chapter_spine"))
                if mode == "on" and not brep.ok:
                    missing.extend(brep.as_missing())
        _check_deductions()
        if missing:
            return _block("不能把薄材料存成大纲/节拍/演绎。补情节原子（选择/代价/线），禁止烟/锅/巷凑句")
        return _fate_hit()

    # 3) 直写 synopsis 且无 spine
    if "synopsis" in fields:
        raw = fields.get("synopsis")
        if raw is not None and str(raw).strip():
            warnings.append("please_use_chapter_spine")
            if mode == "on":
                missing.append({
                    "id": "please_use_chapter_spine",
                    "detail": "直写 synopsis 不算章纲，请写 chapter_spine",
                    "got": 0, "need": 1,
                })
            elif mode == "off":
                n = cn_len(str(raw))
                if n < SYNOPSIS_FLOOR:
                    missing.append({"id": "synopsis", "got": n, "need": SYNOPSIS_FLOOR})
            # shadow：不 422

    # 4) 本次写 beats
    if "beats" in fields and fields.get("beats") is not None:
        beat_rows = [b for b in (fields.get("beats") or []) if b]
        if beat_rows:
            if mode == "on":
                brep = evaluate_beats(beat_rows, spine=None)
                if not brep.ok:
                    missing.extend(brep.as_missing())
            elif mode == "off":
                lens = _beat_lens({"beats": fields.get("beats")})
                if lens:
                    thin = [i + 1 for i, n in enumerate(lens) if n < BEAT_EACH_FLOOR]
                    if thin:
                        missing.append({
                            "id": "beat_each", "got": lens, "need": BEAT_EACH_FLOOR, "thin": thin,
                        })
                    bsum = sum(lens)
                    if bsum < BEAT_SUM_FLOOR:
                        missing.append({"id": "beat_sum", "got": bsum, "need": BEAT_SUM_FLOOR})
                    if len(lens) < 3:
                        missing.append({"id": "beat_count", "got": len(lens), "need": 3})
            # shadow：不因密度 422

    _check_deductions()
    if not missing:
        return _fate_hit()
    return _block("不能把薄材料存成大纲/节拍/演绎。补情节原子（选择/代价/线），禁止烟/锅/巷凑句")


# ── 设定库 persist 闸（独立旗；不写入 _floor_for）────────────────
CODEX_PACK_FLOOR: dict[str, int] = {
    "character": 1200,
    "faction": 1200,
    "item": 1200,
    "term": 1200,
    "world_rule": 1200,
}
CODEX_FIELD_FLOOR: dict[str, dict[str, int]] = {
    "character": {
        "personality_detail": 200, "surface_goal": 80, "deep_need": 80,
        "fear": 80, "internal_conflict": 80, "appearance": 40, "backstory": 200,
    },
    "faction": {
        "ideology": 200, "public_face": 80, "recruitment": 80,
        "secret_agenda": 80, "origin": 80,
        "artifact_operation": 80, "external_manipulation": 80,
        "acceleration_methods": 80,
    },
    "item": {"description": 400},
    "term": {"definition": 1200},
    "world_rule": {"cost": 80, "source": 1},
    "motif": {"theme": 40, "unfolding": 80},
    "voice": {"style_summary": 80},
}
CODEX_MIN_ITEMS: dict[str, dict[str, int]] = {
    "character": {"abilities": 1, "weaknesses": 1},
    "faction": {"goals": 1},
    "item": {"special_properties": 1},
    "world_rule": {"limitations": 1, "exceptions": 1, "capabilities": 1},
    "motif": {"echo_terms": 3},
}
_CODEX_PACK_SKIP_KEYS = frozenset({
    "name", "id", "kind", "archived", "category", "scope", "symbolic_state",
    "importance", "first_appearance", "first_chapter", "first_mention_chapter",
    "status", "leader", "phase", "tier",
})
_SENTINEL_NONE = frozenset({"无", "无人", "遗失"})


def codex_thicken_gate_enabled() -> bool:
    raw = os.environ.get("SCRIBE3_CODEX_THICKEN_GATE")
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def field_cn(value: Any) -> int:
    """只计正文。dict/list 用 json.dumps 去空白。不走 clip_for。"""
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set)):
        items = [x for x in value if str(x).strip()]
        if not items:
            return 0
        import json as _json
        return cn_len(_json.dumps(list(items), ensure_ascii=False, separators=(",", ":")))
    if isinstance(value, dict):
        if not value:
            return 0
        import json as _json
        return cn_len(_json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return cn_len(str(value))


def _is_empty_codex_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return not str(value).strip()


def pack_cn(kind: str, public_fields: dict | None) -> int:
    """公开包长 = 各公开厚字段 field_cn 之和（不含 name/枚举/旗标）。"""
    if not isinstance(public_fields, dict):
        return 0
    total = 0
    for key, val in public_fields.items():
        k = str(key or "")
        if not k or k in _CODEX_PACK_SKIP_KEYS or k.endswith("_secret"):
            continue
        if k in ("secret_agenda",):
            continue
        total += field_cn(val)
    return total


def persist_codex_fields_blocked(
    kind: str,
    submitted: dict | None,
    *,
    existing: dict | None = None,
    mode: str = "incremental",
) -> dict[str, Any] | None:
    """None=放行。incremental 只评本次非空厚字段；pack 评整包+must。"""
    del existing  # L1 不并包；保留形参对照「即将写入」
    if not codex_thicken_gate_enabled() or not isinstance(submitted, dict):
        return None
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    missing: list[dict[str, Any]] = []
    floors = CODEX_FIELD_FLOOR.get(k) or {}
    mins = CODEX_MIN_ITEMS.get(k) or {}
    if (mode or "incremental") == "pack":
        cn = pack_cn(k, submitted)
        need = int(CODEX_PACK_FLOOR.get(k) or 0)
        if need and cn < need:
            missing.append({"id": "pack", "got": cn, "need": need})
        if k == "term":
            definition = str(submitted.get("definition") or "")
            for part in ("是什么", "不是什么", "本书用法", "边界"):
                if part not in definition:
                    missing.append({"id": f"part:{part}", "got": 0, "need": 1})
        if k == "character":
            for key, n in (
                ("personality_detail", 200), ("surface_goal", 80), ("deep_need", 80),
                ("fear", 80), ("internal_conflict", 80),
            ):
                got = field_cn(submitted.get(key))
                if got < n:
                    missing.append({"id": key, "got": got, "need": n})
            for key in ("abilities", "weaknesses"):
                items = submitted.get(key) or []
                if not isinstance(items, (list, tuple)) or len([x for x in items if str(x).strip()]) < 1:
                    missing.append({"id": key, "got": 0, "need": 1})
        if k == "faction":
            if field_cn(submitted.get("ideology")) < 200:
                missing.append({"id": "ideology", "got": field_cn(submitted.get("ideology")), "need": 200})
            if field_cn(submitted.get("public_face")) < 80:
                missing.append({"id": "public_face", "got": field_cn(submitted.get("public_face")), "need": 80})
            struct_cn = max(field_cn(submitted.get("structure")), field_cn(submitted.get("recruitment")))
            if struct_cn < 80:
                missing.append({"id": "structure", "got": struct_cn, "need": 80})
            if _is_empty_codex_value(submitted.get("leader")):
                missing.append({"id": "leader", "got": 0, "need": 1})
            goals = submitted.get("goals") or []
            has_target = False
            if isinstance(goals, list):
                for g in goals:
                    if isinstance(g, dict) and str(g.get("target") or "").strip():
                        has_target = True
                    elif str(g or "").strip():
                        has_target = True
            if not has_target:
                missing.append({"id": "goals", "got": 0, "need": 1})
        if k == "item":
            if field_cn(submitted.get("description")) < 400:
                missing.append({"id": "description", "got": field_cn(submitted.get("description")), "need": 400})
            if _is_empty_codex_value(submitted.get("current_owner")):
                missing.append({"id": "current_owner", "got": 0, "need": 1})
            props = submitted.get("special_properties") or []
            if not isinstance(props, (list, tuple)) or not [x for x in props if str(x).strip()]:
                missing.append({"id": "special_properties", "got": 0, "need": 1})
        if k == "world_rule":
            if field_cn(submitted.get("cost")) < 80:
                missing.append({"id": "cost", "got": field_cn(submitted.get("cost")), "need": 80})
            for key in ("limitations", "exceptions", "capabilities"):
                items = submitted.get(key) or []
                if not isinstance(items, (list, tuple)) or not [x for x in items if str(x).strip()]:
                    missing.append({"id": key, "got": 0, "need": 1})
            if _is_empty_codex_value(submitted.get("source")):
                missing.append({"id": "source", "got": 0, "need": 1})
        if k == "motif":
            if field_cn(submitted.get("theme")) < 40:
                missing.append({"id": "theme", "got": field_cn(submitted.get("theme")), "need": 40})
            echoes = submitted.get("echo_terms") or submitted.get("echoes") or []
            n = 0
            if isinstance(echoes, (list, tuple)):
                n = len([x for x in echoes if len(str(x).strip()) >= 2])
            elif isinstance(echoes, str):
                n = len([x for x in re.split(r"[,，、;；]", echoes) if len(x.strip()) >= 2])
            if n < 3:
                missing.append({"id": "echo_terms", "got": n, "need": 3})
            if field_cn(submitted.get("unfolding")) < 80:
                missing.append({"id": "unfolding", "got": field_cn(submitted.get("unfolding")), "need": 80})
        if k == "voice":
            if field_cn(submitted.get("style_summary")) < 80:
                missing.append({"id": "style_summary", "got": field_cn(submitted.get("style_summary")), "need": 80})
            sections = 0
            for key in ("catchphrases", "tone_rules", "internal_monologue_style", "sentence_patterns"):
                if not _is_empty_codex_value(submitted.get(key)):
                    sections += 1
            if sections < 2:
                missing.append({"id": "voice_sections", "got": sections, "need": 2})
    else:
        for key, val in submitted.items():
            if _is_empty_codex_value(val):
                continue
            if key == "private_operation":
                missing.append({
                    "id": "private_operation",
                    "got": 1,
                    "need": 0,
                    "hint": "拆到 artifact_operation / external_manipulation / acceleration_methods",
                })
                continue
            floor = int(floors.get(key) or 0)
            if floor and field_cn(val) < floor:
                missing.append({"id": key, "got": field_cn(val), "need": floor})
            min_n = int(mins.get(key) or 0)
            if min_n:
                items = val if isinstance(val, (list, tuple)) else []
                got = len([x for x in items if str(x).strip()])
                if key == "special_properties" and any(str(x).strip() in _SENTINEL_NONE for x in items):
                    continue
                if got < min_n:
                    missing.append({"id": key, "got": got, "need": min_n})
    if not missing:
        return None
    bits = [f"{m['id']} {m['got']}<{m['need']}" for m in missing]
    return {
        "code": "codex_thin_persist",
        "message": "不能把薄设定存成已有档案：" + "；".join(bits),
        "missing": missing,
        "kind": k,
        "mode": mode,
        "role": "codex_substrate",
    }


def codex_l1_error(kind: str, submitted: dict | None) -> dict[str, Any] | None:
    hit = persist_codex_fields_blocked(kind, submitted, mode="incremental")
    if not hit:
        return None
    return {
        "status": "error",
        "code": hit["code"],
        "error": hit["message"],
        "missing": hit.get("missing"),
        "kind": kind,
    }


def evaluate_codex_ready(kind: str, row: dict | None) -> dict[str, Any]:
    """合并后整行。stub / thin / ready。只决定 skip 与灯，不挡 L1。"""
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    src = dict(row or {})
    thick_keys = set((CODEX_FIELD_FLOOR.get(k) or {})) | set((CODEX_MIN_ITEMS.get(k) or {}))
    if k == "character":
        thick_keys |= {"abilities", "weaknesses", "personality_detail"}
    has_thick = False
    for key in thick_keys:
        if not _is_empty_codex_value(src.get(key)):
            has_thick = True
            break
    if k == "term" and str(src.get("definition") or "").strip():
        has_thick = True
    blocked = persist_codex_fields_blocked(k, src, mode="pack")
    if not has_thick:
        status = "stub"
        ok = False
    elif blocked:
        status = "thin"
        ok = False
    else:
        status = "ready"
        ok = True
    return {
        "ok": ok,
        "status": status,
        "kind": k,
        "pack_cn": pack_cn(k, src),
        "blocked": blocked,
        "role": "codex_ready",
    }


def attach_codex_ready(
    kind: str,
    row: dict | None,
    *,
    evaluate_from: dict | None = None,
) -> dict[str, Any]:
    """给档案响应挂 ``codex_ready``。``evaluate_from`` 用于掩码前的真值。"""
    src = dict(row or {})
    ev = evaluate_codex_ready(kind, evaluate_from if evaluate_from is not None else src)
    src["codex_ready"] = {
        "ok": bool(ev.get("ok")),
        "status": ev.get("status"),
        "pack_cn": int(ev.get("pack_cn") or 0),
    }
    return src


def codex_ready_badge(kind: str, row: dict | None) -> dict[str, Any]:
    ev = evaluate_codex_ready(kind, row)
    status = str(ev.get("status") or "stub")
    labels = {"stub": "空壳", "thin": "偏薄", "ready": "已齐"}
    tones = {"stub": "faint", "thin": "warn", "ready": "ok"}
    return {
        "kind": "codex_ready",
        "value": labels.get(status, status),
        "tone": tones.get(status, "faint"),
        "status": status,
    }


def iceberg_http_detail(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": "iceberg_thin",
        "message": report.get("message") or "冰山未厚",
        "iceberg": report,
        "hint": "补情节原子（选择/代价/线），禁止烟/锅/巷凑句；或 danger_draft / skip_iceberg 旁路（会写成口号戏）。",
    }

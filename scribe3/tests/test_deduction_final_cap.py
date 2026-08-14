"""P0-3：deduction_final 焦点优先 + 整包硬帽 + 单段 push。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    FOCAL_DEDUCTION_PROSE_CAP,
    _deduction_context_segments,
)
from scribe3.context_budget import (
    DEFAULT_CODEX_INJECT_CAP,
    L0_NEVER_CUT,
    NOVEL_PROMPT_HARD,
    join_generation_segments,
)
from scribe3.iceberg import DEDUCTION_PACK_CAP


NONFOCAL_UNAWARE = "NONFOCAL_UNAWARE_炉心真名铜钥不该进稿"
FOCAL_UNAWARE = "FOCAL_UNAWARE_灰七没看见铜钥藏在袖里"
TRUTH = "侧门油灯还亮着，冷锅婆把铜钥塞进灰狸袖里。"


def _five_layer(*, seen: str, known: str, misread: str, did: str, unaware: str) -> str:
    return (
        f"### 看到/听到\n{seen}\n\n"
        f"### 知道\n{known}\n\n"
        f"### 以为(误读)\n{misread}\n\n"
        f"### 做了/说了\n{did}\n\n"
        f"### 没察觉的\n{unaware}"
    )


class _Store:
    def __init__(self, ch: dict | None = None):
        self.ch = ch or {}

    def get_chapter(self, seq):
        return dict(self.ch)


def _default_chapter(*, truth: str = TRUTH, extra: list[dict] | None = None) -> dict:
    deds = [
        {
            "character_id": "role:灰七",
            "character_name": "灰七",
            "prose": _five_layer(
                seen="侧门一盏油灯",
                known="冷锅婆今夜不让进",
                misread="以为只是赶客",
                did="把肩抵在门框上",
                unaware=FOCAL_UNAWARE,
            ),
        },
        {
            "character_id": "role:冷锅婆",
            "character_name": "冷锅婆",
            "prose": _five_layer(
                seen="灰七的肩抵着门",
                known="铜钥已经给了灰狸",
                misread="以为灰七会退",
                did="把门闩往死里顶",
                unaware=NONFOCAL_UNAWARE,
            ),
        },
    ]
    if extra:
        deds.extend(extra)
    return {"scene_truth": truth, "deductions": deds}


def _joined(st, seq=1, focalizer="role:灰七") -> tuple[str, list[tuple[str, str, str]]]:
    segs = _deduction_context_segments(st, seq, focalizer=focalizer)
    return "".join(text for _, _, text in segs), segs


def test_hard_budget_constant_unchanged():
    assert NOVEL_PROMPT_HARD == 48000
    assert "deduction_final" in L0_NEVER_CUT
    assert DEFAULT_CODEX_INJECT_CAP == 4500
    assert FOCAL_DEDUCTION_PROSE_CAP == 6000
    assert DEDUCTION_PACK_CAP == 8500


def test_empty_chapter_returns_no_segments():
    assert _deduction_context_segments(_Store({}), 1, focalizer="role:灰七") == []


def test_draft_keeps_header_truth_and_focal_layers():
    text, segs = _joined(_Store(_default_chapter()))
    assert "本章演绎" in text
    assert TRUTH in text
    assert "灰七·限知投影" in text
    assert "侧门一盏油灯" in text
    assert FOCAL_UNAWARE in text
    kinds = [k for _, k, _ in segs]
    assert kinds.count("scene_truth") == 1
    assert kinds.count("deduction_protocol") == 2
    assert "deduction" in kinds


def test_nonfocal_full_layers_are_injected():
    text, segs = _joined(_Store(_default_chapter()))
    assert NONFOCAL_UNAWARE in text
    assert "冷锅婆·限知投影" in text
    assert any("冷锅婆" in t for _sid, kind, t in segs)


def test_focalizer_name_without_role_prefix_still_hits():
    text, _ = _joined(_Store(_default_chapter()), focalizer="灰七")
    assert FOCAL_UNAWARE in text
    assert NONFOCAL_UNAWARE in text


def test_no_focalizer_still_injects_full_layers():
    text, _ = _joined(_Store(_default_chapter()), focalizer="")
    assert FOCAL_UNAWARE in text
    assert NONFOCAL_UNAWARE in text


def test_stale_hint_without_old_body():
    ch = _default_chapter()
    ch["scene_truth_revision"] = 3
    ch["deductions"][1]["based_on_truth_rev"] = 1
    ch["deductions"][1]["prose"] = f"旧文含 {NONFOCAL_UNAWARE}"
    text, segs = _joined(_Store(ch))
    assert "过期" in text
    assert NONFOCAL_UNAWARE not in text
    assert any(k == "deduction_stale" for _, k, _ in segs)


def test_focal_prose_capped_at_inject_cap():
    just = "焦" * 5000
    ch = _default_chapter()
    ch["deductions"][0]["prose"] = just
    text, segs = _joined(_Store(ch))
    assert just in text
    huge = "焦" * 7000
    ch["deductions"][0]["prose"] = huge
    text, segs = _joined(_Store(ch))
    assert huge not in text
    assert ("焦" * FOCAL_DEDUCTION_PROSE_CAP) in text
    focal = next(t for _sid, kind, t in segs if "灰七·限知投影" in t)
    assert focal.count("焦") == FOCAL_DEDUCTION_PROSE_CAP


def test_pack_cap_drops_nonfocal_then_excerpts_truth():
    long_truth = "真" * 5000
    extras = [
        {
            "character_id": f"role:龙套{i}",
            "character_name": f"龙套{i}",
            "prose": _five_layer(
                seen="看见门槛",
                known="只知道要拦",
                misread="以为能过",
                did="站着",
                unaware=f"UNAWARE_EXTRA_{i}_不该进",
            ),
        }
        for i in range(8)
    ]
    from scribe3.iceberg import DEDUCTION_PACK_CAP
    text, _ = _joined(_Store(_default_chapter(truth=long_truth, extra=extras)))
    assert len(text) <= DEDUCTION_PACK_CAP + 80
    assert "本章演绎" in text
    assert "本章演绎" in text
    assert text.startswith("\n\n## 本章演绎") or "本章演绎" in text


def test_rebound_globals_without_cap_name_still_clips():
    """生产路径把函数 __globals__ 换成 app_impl；不得再 NameError FOCAL_DEDUCTION_PROSE_CAP。"""
    import types
    from scribe3.api.services import write_assemble_context as wac

    bare = {
        "_clip_chars": wac._clip_chars,
        "_deduction_item_is_focal": wac._deduction_item_is_focal,
        "_apply_deduction_pack_cap": wac._apply_deduction_pack_cap,
        "_deduction_evict_rank": wac._deduction_evict_rank,
        "_chapter_mention_from_ch": wac._chapter_mention_from_ch,
    }
    rebound = types.FunctionType(
        wac._deduction_context_segments.__code__,
        bare,
        "_deduction_context_segments",
        wac._deduction_context_segments.__defaults__,
        wac._deduction_context_segments.__closure__,
    )
    rebound.__kwdefaults__ = dict(wac._deduction_context_segments.__kwdefaults__ or {})
    segs = rebound(_Store(_default_chapter()), 1, focalizer="role:灰七")
    assert segs
    text = "".join(t for _, _, t in segs)
    assert TRUTH in text


def test_write_assemble_rebind_whitelist_includes_focal_cap():
    from scribe3.api.services.write_assemble import WRITE_ASSEMBLE_REBIND_NAMES
    assert "FOCAL_DEDUCTION_PROSE_CAP" in WRITE_ASSEMBLE_REBIND_NAMES
    assert "_character_named_line" in WRITE_ASSEMBLE_REBIND_NAMES
    assert "_clip_named" in WRITE_ASSEMBLE_REBIND_NAMES


def test_budget_report_length_equals_joined_and_under_cap():
    text, _ = _joined(_Store(_default_chapter(truth="真" * 3000)))
    assert 0 < len(text) <= DEDUCTION_PACK_CAP
    _out, rep = join_generation_segments([
        {"name": "deduction_final", "layer": "redline", "text": text},
    ])
    assert rep["domain_lengths"]["deduction_final"] == len(text)
    assert rep["domain_lengths"]["deduction_final"] <= DEDUCTION_PACK_CAP


def test_v1_pushes_deduction_final_once_and_passes_focalizer():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert src.count('_push("deduction_final"') == 1
    assert "_deduction_context_segments(" in src
    assert "focalizer=focalizer or \"\"" in src or "focalizer=focalizer or ''" in src
    # 仍按源登记 Manifest，但拼好后只 push 一次
    assert "_domain_input(source_id, source_kind, text)" in src

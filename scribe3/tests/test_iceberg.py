"""冰山前置：字数=水下覆盖，不是文学分。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import (
    BEAT_EACH_FLOOR,
    BEAT_SUM_FLOOR,
    DEDUCTION_FLOOR,
    SYNOPSIS_FLOOR,
    evaluate_iceberg,
    should_block_prose_write,
)


def _thick_chapter() -> dict:
    beat = "炉前青砖上摊开灯册。" + ("甲" * 680)
    ded = "沈拾灯此时只知道灯册缺页烫腕。" + ("乙" * 2600)
    return {
        "synopsis": "清册官入镇核册，三笔夜税未入炉。" + ("丙" * 500),
        "beats": [{"text": beat}, {"text": beat}, {"text": beat}],
        "deductions": [
            {"character_id": "role:沈拾灯", "prose": ded},
            {"character_id": "role:阿绣", "prose": ded},
        ],
        "draft_prose": "排演。" + ("丁" * 10000),
    }


def test_slogan_scaffold_is_not_iceberg():
    ch = {
        "synopsis": "灯火门清册官入镇要封炉核册，沈拾灯把缺页灯册贴在腕上旧烫疤里。",
        "beats": [
            {"text": "清册官在炉前摊开灯册要封炉。"},
            {"text": "阿绣把三户假账麻纸藏进木匣夹层。"},
            {"text": "霍三刀巷口按鞘观望不肯进场。"},
        ],
        "deductions": [
            {"prose": "沈拾灯腕上旧烫疤发烫。"},
        ],
    }
    r = evaluate_iceberg(ch, for_phase="draft")
    assert r["ok"] is False
    ids = {m["id"] for m in r["missing"]}
    assert "synopsis" in ids
    assert "beat_each" in ids
    assert "beat_sum" in ids
    assert "deduction" in ids
    assert r["measures"]["synopsis"] < SYNOPSIS_FLOOR
    assert r["measures"]["beat_sum"] < BEAT_SUM_FLOOR
    assert r["measures"]["deduction"] < DEDUCTION_FLOOR
    assert "冰山未厚" in r["message"]
    assert r["role"] == "iceberg_substrate"


def test_thick_substrate_passes_draft_iceberg():
    r = evaluate_iceberg(_thick_chapter(), for_phase="draft")
    assert r["ok"] is True
    assert r["measures"]["synopsis"] >= SYNOPSIS_FLOOR
    assert all(n >= BEAT_EACH_FLOOR for n in r["measures"]["beats"])
    assert r["measures"]["beat_sum"] >= BEAT_SUM_FLOOR
    assert r["measures"]["deduction"] >= DEDUCTION_FLOOR


def test_final_requires_draft_mass():
    ch = _thick_chapter()
    ch.pop("draft_prose")
    r = evaluate_iceberg(ch, for_phase="final")
    assert r["ok"] is False
    assert any(m["id"] == "draft" for m in r["missing"])
    r2 = evaluate_iceberg(_thick_chapter(), for_phase="final")
    assert r2["ok"] is True


def test_thicken_phases_are_not_blocked():
    assert should_block_prose_write("outline", write_intent=True) is False
    assert should_block_prose_write("beats", write_intent=True) is False
    assert should_block_prose_write("deduce", write_intent=True) is False
    assert should_block_prose_write("draft", write_intent=True) is True
    assert should_block_prose_write("final", write_intent=True) is True
    assert should_block_prose_write("draft", write_intent=False) is False


def test_outline_inject_keeps_each_beat():
    from scribe3.api.services.write_assemble_context import _clip_chars, _outline_block

    long = "甲" * 600
    class _St:
        def get_chapter(self, _n):
            return {
                "synopsis": "乙" * 500,
                "beats": [{"text": long}, {"text": long}, {"text": long}],
            }
    blk = _outline_block(_St(), 6, focalizer="role:沈拾灯")
    # 三段都在，不是三拍挤进 1200 后只剩第一段
    assert blk.count("甲") >= 3 * 500
    assert "乙" * 100 in blk
    assert _clip_chars("丙" * 10, 4) == "丙" * 4


if __name__ == "__main__":
    test_slogan_scaffold_is_not_iceberg()
    test_thick_substrate_passes_draft_iceberg()
    test_final_requires_draft_mass()
    test_thicken_phases_are_not_blocked()
    test_outline_inject_keeps_each_beat()
    print("PASS test_iceberg")

#!/usr/bin/env python3
"""v6.3.4 / playbook.3.2.1 部署冒烟。默认只做入口级检查，不烧模型。"""
from __future__ import annotations

import argparse
import json
import os
import sys


def smoke_imports() -> list[tuple[str, bool, str]]:
    rows: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, ok, detail))

    try:
        from scribe3.playbook.quote import PLAYBOOK_VERSION
        add("playbook_version", PLAYBOOK_VERSION == "playbook.3.2.4", PLAYBOOK_VERSION)
    except Exception as e:
        add("playbook_version", False, type(e).__name__)

    try:
        from scribe3.api.services.write_stream import bind_pilot_trace
        add("bind_pilot_trace", callable(bind_pilot_trace), "")
    except Exception as e:
        add("bind_pilot_trace", False, type(e).__name__)

    try:
        from scribe3.playbook.judge import _normalize
        bad = _normalize({"verdict": "???", "answers": []})
        add("judge_fail_closed", bad.get("verdict") == "needs_human", str(bad.get("verdict")))
    except Exception as e:
        add("judge_fail_closed", False, type(e).__name__)

    try:
        from scribe3.playbook.structural import check_draft_struct, check_final_last_mile
        play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 80
        copy = check_draft_struct(play + "他又看了一眼裂口。" * 20, play_text=play)
        add("draft_copy_gate", copy.get("ok") is False and copy.get("code") == "draft_copy_play", copy.get("code") or "")
        meta = check_final_last_mile(("他按回碎片，袖口发烫。" * 120) + "上一章末他就数过。")
        add("chapter_boundary_gate", meta.get("code") == "meta_chapter_ref", meta.get("code") or "")
    except Exception as e:
        add("struct_gates", False, type(e).__name__)

    try:
        from scribe3.anti_meta_narration import scan_anti_meta
        hit = scan_anti_meta("这一章里没有人开口。")
        add("m8_scan", "M8" in (hit.get("claim_blocking_ids") or []), "")
    except Exception as e:
        add("m8_scan", False, type(e).__name__)

    try:
        from scribe3.playbook.prompts import draft_generate, duty_generate
        d = draft_generate({"play_text": "戏", "bite_quote": "钩"})
        add("draft_prompt_delta", "必须比戏多出三样" in d, "")
        u = duty_generate({})
        add("duty_prompt_second", "至少还要有一个有意志的人" in u, "")
        add("duty_prev_state", "上一章结束时世界变成了什么样" in u, "")
    except Exception as e:
        add("prompts", False, type(e).__name__)

    try:
        from scribe3.playbook.structural import (
            check_chapter_state_struct,
            check_final_last_mile,
            check_gender_pronoun,
        )
        flip = check_gender_pronoun(
            "柳岸青她把断指扔在地上，腕上的裂口还在渗。她说这根指头不再跳了。",
            [{"name": "柳岸青", "gender": "男"}],
        )
        add("gender_pronoun_gate", flip.get("ok") is False and flip.get("code") == "gender_pronoun", flip.get("code") or "")
        fake = check_chapter_state_struct(
            {
                "seq": 2,
                "characters": [{"name": "柳岸青", "gender": "男", "state": "右腕内嵌断指", "quote": "这段话正文里根本没有"}],
                "objects": [],
                "open_loops": [],
                "timeline": {"at": "夜", "elapsed_from_prev": ""},
                "imagery": [],
            },
            "柳岸青把断指按进右腕。它寄在他手腕里面。",
        )
        add("state_quote_gate", fake.get("ok") is False and fake.get("code") == "state_quote", fake.get("code") or "")
        dense = check_final_last_mile("他按回碎片。像火。仿佛夜。似的冷。" * 80)
        add(
            "simile_density_gate",
            dense.get("ok") is False and dense.get("code") == "final_metaphor",
            dense.get("code") or "",
        )
        good = check_chapter_state_struct(
            {
                "seq": 2,
                "characters": [{"name": "柳岸青", "gender": "男", "state": "右腕内嵌断指", "quote": "寄在他手腕里面"}],
                "objects": [{"name": "断指", "location": "右腕内", "state": "不再跳", "quote": "按进右腕"}],
                "open_loops": [],
                "timeline": {"at": "夜", "elapsed_from_prev": ""},
                "imagery": ["黑屋"],
            },
            "柳岸青把断指按进右腕。它寄在他手腕里面。",
        )
        add("state_quote_pass", good.get("ok") is True, good.get("code") or "ok")
    except Exception as e:
        add("continuity_gates", False, type(e).__name__)

    try:
        from scribe3.playbook.structural import (
            check_draft_struct,
            check_pov_consistency,
            thin_metaphors,
        )
        first = ("「按回去。」我说。\n我把盒子按进胸口，听见最后一下。袖口发烫。\n" * 80)
        d13 = check_pov_consistency(first, "third")
        add(
            "d13_pov_gate",
            d13.get("ok") is False and d13.get("code") == "pov_consistency",
            d13.get("code") or "",
        )
        play = "完全另一场戏，沈烛若没有按回碎片。" * 40
        draft_flip = check_draft_struct(first, play_text=play, expected_pov="third")
        add(
            "d13_draft_pov",
            draft_flip.get("ok") is False and draft_flip.get("code") == "pov_consistency",
            draft_flip.get("code") or "",
        )
        silent = ("他按回碎片，袖口发烫。沈烛把盒子推过来。柳岸青没说话。任务书摊在桌上。\n" * 80)
        floor = check_draft_struct(silent, play_text=play)
        add(
            "dialogue_floor_gate",
            floor.get("ok") is False and floor.get("code") == "dialogue_floor",
            floor.get("code") or "",
        )
        cleaned = thin_metaphors("那温度不像是他自己的了。袖口发烫。" * 120)
        add("thin_unlike_is", "不似乎" not in cleaned and "不似" in cleaned, cleaned[40:80])
        from scribe3.playbook.structural import residue_hits
        rolled = thin_metaphors("它裂开，像又烧过的骨片。袖口发烫。" * 120)
        add(
            "d14_residue",
            "不似乎" not in rolled and "像又烧过" in rolled and bool(residue_hits("裂开，又烧过的骨片。")),
            rolled[20:80],
        )
    except Exception as e:
        add("playbook31_gates", False, type(e).__name__)

    try:
        from scribe3.playbook.structural import check_syntax_tics
        two = check_syntax_tics("这不是明火，是碳粉。袖口发烫。那不是灯火是磷光。他站着。")
        add(
            "d15_syntax_tics",
            two.get("ok") is False and two.get("code") == "syntax_tics",
            two.get("code") or "",
        )
        dlg = check_syntax_tics("「这不是明火，是碳粉。」他说。\n「那不是灯火是磷光。」柳岸青说。")
        add("d15_dialogue_skip", dlg.get("ok") is True, dlg.get("code") or "ok")
        from scribe3.playbook.diagnose import sentence_rhythm
        rh = sentence_rhythm("他走了。门响。灯灭了。夜还在。然后他在走廊里把盒子按回胸口，听见最后一下。")
        add(
            "craft_rhythm",
            "short_ratio" in rh and "long_ratio" in rh and "short_bursts" in rh,
            str(rh),
        )
        from scribe3.playbook.prompts import (
            draft_generate, duty_generate, final_generate, final_judge, play_generate,
        )
        add("duty_chapter_duty_slot", "【本章责】" in duty_generate({}), "")
        d = draft_generate({"play_text": "戏", "bite_quote": "钩"})
        add("draft_no_tactile_quota", "可听可触" not in d and "摸到或听到" in d, "")
        f = final_generate({})
        add("final_no_texture_patch", "补上画面的质感与声音" not in f and "宁可糙着" in f, "")
        j = final_judge({})
        add("final_judge_read_aloud", "念出声" in j and "在使劲" in j, "")
        p = play_generate({"seq": 1, "duty": {}})
        add(
            "play_is_design",
            "800-2000" not in p and "400-900" in p and "留给糙稿" in p,
            "",
        )
    except Exception as e:
        add("playbook32_gates", False, type(e).__name__)

    return rows


def smoke_live(n_chapters: int = 1, slug: str | None = None, title: str | None = None) -> list[tuple[str, bool, str]]:
    from scribe3.tools.v634_live_run import run_live
    rep = run_live(n_chapters=n_chapters, slug=slug, title=title)
    rows: list[tuple[str, bool, str]] = [
        ("playbook3", str(rep.get("playbook") or "").startswith("playbook."), str(rep.get("playbook"))),
        ("created_or_resumed", bool(rep.get("slug")), str(rep.get("slug") or "")),
        ("layers_ok", bool(rep.get("ok") or rep.get("gate0")), ""),
        ("gate0", bool(rep.get("gate0")), ""),
        ("source_consistent", bool(rep.get("source_consistent")), str(rep.get("latest_sources"))),
    ]
    for v in rep.get("verify") or []:
        m = v.get("metrics") or {}
        rows.append((
            f"ch{v.get('seq')}_frozen",
            int(v.get("play_n") or 0) >= 200 and int(v.get("draft_n") or 0) >= 200,
            f"play={v.get('play_n')} draft={v.get('draft_n')} src={v.get('latest_source')}",
        ))
        rows.append((
            f"ch{v.get('seq')}_overlap",
            float(m.get("overlap") or 1) <= 0.15,
            str(m.get("overlap")),
        ))
        rows.append((
            f"ch{v.get('seq')}_boundary",
            int(m.get("boundary_hits") or 0) == 0,
            str(m.get("boundary_hits")),
        ))
        if n_chapters > 1:
            rows.append((f"ch{v.get('seq')}_cmust", bool(m.get("ok")), json.dumps(m, ensure_ascii=False)[:240]))
            rows.append((f"ch{v.get('seq')}_pov", bool(m.get("pov_ok", True)), str(m.get("narrative_pov") or "")))
            rows.append((f"ch{v.get('seq')}_state_api", int(v.get("state_api") or 0) == 200, str(v.get("state_api"))))
            res = [x for x in (m.get("residue_hits") or []) if x == "不似乎" or str(x).startswith("，又")]
            rows.append((f"ch{v.get('seq')}_residue", not res, str(res)))
        rows.append((
            f"ch{v.get('seq')}_state",
            bool(v.get("state_ok")),
            str(v.get("state_detail") or ""),
        ))
    if n_chapters > 1:
        rows.append(("pov_cross_chapter", bool(rep.get("pov_consistent", True)), str(rep.get("povs"))))
        rows.append(("state_api_ok", bool(rep.get("state_api_ok", True)), ""))
    # persist report next to caller if requested
    out = os.environ.get("V634_LIVE_REPORT")
    if out:
        open(out, "w").write(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("imports", "live"), default="imports")
    p.add_argument("--chapters", type=int, default=1)
    p.add_argument("--slug", default="")
    p.add_argument("--title", default="")
    args = p.parse_args(argv)
    if args.mode == "imports":
        rows = smoke_imports()
    else:
        rows = smoke_live(n_chapters=args.chapters, slug=args.slug or None, title=args.title or None)
    failed = 0
    print("V634_SMOKE", args.mode, "chapters", args.chapters)
    for name, ok, detail in rows:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  {mark}  {name}" + (f"  {detail}" if detail else ""))
    print("RESULT", "FAIL" if failed else "PASS", f"{len(rows) - failed}/{len(rows)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

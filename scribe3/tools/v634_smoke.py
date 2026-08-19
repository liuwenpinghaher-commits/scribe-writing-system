#!/usr/bin/env python3
"""v6.3.4 / playbook.2 部署冒烟。默认只做入口级检查，不烧模型。"""
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
        add("playbook_version", PLAYBOOK_VERSION == "playbook.2", PLAYBOOK_VERSION)
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
    except Exception as e:
        add("prompts", False, type(e).__name__)

    return rows


def smoke_live(n_chapters: int = 1, slug: str | None = None, title: str | None = None) -> list[tuple[str, bool, str]]:
    from scribe3.tools.v634_live_run import run_live
    rep = run_live(n_chapters=n_chapters, slug=slug, title=title)
    rows: list[tuple[str, bool, str]] = [
        ("playbook2", rep.get("playbook") == "playbook.2", str(rep.get("playbook"))),
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

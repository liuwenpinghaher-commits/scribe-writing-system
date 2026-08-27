"""从北极星长出全书卷纲，以及逐卷对账。

这一层此前是空的：`s3_plan_volumes` 只把现有卷章列给主编看，返回 `planned: True`，
不调 LLM 也不写任何东西，卷纲全靠主编在对话里手写。3000 章不可能这么走。

《万界概率战争》25 章实测证明这就是「设定不长新东西」的根：种子只有一卷，
拿同一份卷纲生成 200 章，模型没有新推进方向输入，只能在既有元素上加细节
（第 14 章起每章新增实体恒为 0）。接上卷纲契约后，26-35 章回到每 10 章 7 个新实体。

生成与核对的实现在 `scribe3/charter.py`，本文件只是 CLI 壳。

用法：
    python -m scribe3.tools.plan_charter --db wanjie_scale --volumes 10 --total 200
    python -m scribe3.tools.plan_charter --db wanjie_scale --audit
    python -m scribe3.tools.plan_charter --db wanjie_scale --freshness 26 35
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scribe3.charter import (
    audit_volume,
    build_charter_prompt,
    freshness,
    generate_charters,
    normalize_charter,
    parse_charters,
    persist_charters,
    validate_charter,
)
from scribe3.store import SurrealStore


def show(charters: list[dict]) -> None:
    for c in charters:
        rng = c["chapter_range"] or ["?", "?"]
        print(f"卷{c['sort_order']}《{c['title']}》第 {rng[0]}-{rng[1]} 章"
              f"　引入 {len(c['introduces'])} 新实体　收 {len(c['pays'])} 条线")
        print(f"  办：{c['duty']}")
        for i in c["introduces"]:
            print(f"  + {i['oid']}　{i['why']}")
        for p in c["pays"]:
            print(f"  收：{p}")
        for k in c["knowledge_end"]["must_know"]:
            print(f"  卷末该知道［{k['key']}］：{k['what']}")
        for k in c["knowledge_end"]["must_not_know"]:
            print(f"  卷末仍不许知道［{k['key']}］：{k['what']}")
        problems = validate_charter(c)
        if problems:
            print("  ✗ " + "；".join(problems))
        print()


def run_audit(st, hero: str) -> int:
    """核对每一卷：纲说的 vs 库里真有的。返回不合格卷数。"""
    vols = st.list_volumes() or []
    if not vols:
        print("库里没有卷。")
        return 0
    bad = 0
    for v in vols:
        if not normalize_charter(v.get("charter"))["chapter_range"]:
            print(f"卷《{v.get('title')}》没有契约，跳过。")
            continue
        a = audit_volume(st, v, hero)
        print(a.report(), end="\n\n")
        bad += 0 if a.ok else 1
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8123/rpc")
    ap.add_argument("--ns", default="scribe3")
    ap.add_argument("--db", default="wanjie_scale")
    ap.add_argument("--volumes", type=int, default=10)
    ap.add_argument("--total", type=int, default=200)
    ap.add_argument("--hero", default="role:柳岸青")
    ap.add_argument("--audit", action="store_true", help="只核对已有契约，不生成")
    ap.add_argument("--freshness", nargs=2, type=int, metavar=("LO", "HI"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prompt-only", action="store_true")
    ap.add_argument("--out", default=None, help="把生成的 JSON 存下来")
    ap.add_argument("--from-json", default=None, help="复用已生成的 JSON，不再调模型")
    a = ap.parse_args()

    st = SurrealStore(url=a.url, ns=a.ns, db=a.db)
    try:
        if a.prompt_only:
            print(build_charter_prompt(st, a.volumes, a.total))
        elif a.freshness:
            print(json.dumps(freshness(st, *a.freshness), ensure_ascii=False, indent=2))
        elif a.audit:
            print(f"不合格 {run_audit(st, a.hero)} 卷。")
        else:
            if a.from_json:
                charters = parse_charters(Path(a.from_json).read_text(encoding="utf-8"))
            else:
                from scribe3.llm import hermes_complete

                def _complete(prompt: str) -> str:
                    raw = hermes_complete(prompt, max_tokens=8000)
                    if a.out:
                        Path(a.out).write_text(raw, encoding="utf-8")
                    return raw

                charters, left = generate_charters(st, a.volumes, a.total, _complete)
                if left:
                    print("重写后仍不合格：\n  " + "\n  ".join(left) + "\n")
            show(charters)
            print(persist_charters(st, charters, a.total) if not a.dry_run
                  else {"volumes": len(charters), "persisted": False})
    finally:
        st.close()


if __name__ == "__main__":
    raise SystemExit(main())

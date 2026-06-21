"""把 109k《九原渡》迁移到 scribe2 SurrealDB(:8001 持久化):
圣经(bible JSON)+ 正文(out/九原渡/*.md)+ 记忆(scribe_mcp :3320)。非破坏:旧 scribe.db 保留。
跑:cd scribe && SURREAL_URL=ws://127.0.0.1:8001/rpc .venv/bin/python tools/migrate_jiuyuandu.py
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SURREAL_URL", "ws://127.0.0.1:8001/rpc")

import httpx  # noqa: E402
from scribe2.conn import connect, domain_from  # noqa: E402
from scribe2.domain import _cjk  # noqa: E402

HERE = Path(__file__).resolve().parent
BIBLE = json.loads((HERE / "bible_jiuyuandu.json").read_text(encoding="utf-8"))
OUT = HERE.parent / "out" / "九原渡"
OLD_WID = "eac58155-1ef2-4cc0-9aea-ac65a1f87c94"


def main():
    d = domain_from(connect())
    d.s.init_schema()
    # 幂等:已迁过则跳过
    if any(w.get("title") == BIBLE["title"] for w in d.list_works("u1")):
        print("《九原渡》已在 SurrealDB,跳过。")
        return
    nw = d.create_work(BIBLE["title"], BIBLE["genre"])
    it = BIBLE["intent"]
    d.set_intent(nw, it["reader_feeling"], it["core_emotional_arc"],
                 it.get("why_write", ""), it.get("central_promise", ""), it["do_not_betray"])
    for c in BIBLE["characters"]:
        d.add_character(nw, c["name"], c.get("motivation", ""), c.get("voice", ""))
    for s in BIBLE["settings"]:
        d.add_setting(nw, s["name"], s["description"], s["type"])
    for f in BIBLE["foreshadows"]:
        d.plant_foreshadow(nw, f["summary"], f["chapter"], f["importance"])
    for v in BIBLE["volumes"]:
        d.create_volume(nw, v["seq"], v["title"])
    nchap = nword = 0
    for ch in BIBLE["chapters"]:
        seq = ch["seq"]
        f = OUT / f"第{seq:02d}章_{ch['title']}.md"
        if not f.exists():
            continue
        cid = d.add_chapter(nw, seq, ch["title"])
        body = re.sub(r"^#.*\n", "", f.read_text(encoding="utf-8")).strip()
        d.save_prose(nw, cid, body, locked=True)
        nchap += 1
        nword += _cjk(body)
    # 记忆:从 scribe_mcp :3320 取(若在跑)
    try:
        mem = httpx.get(f"http://127.0.0.1:3320/works/{OLD_WID}/memory",
                        headers={"X-Owner-Id": "jiuyuandu-author"}, timeout=5).json()
        for m in mem.get("chapters", []):
            d.save_chapter_memory(nw, m["seq"], m.get("summary_text", ""))
        if mem.get("global"):
            d.set_global_memory(nw, mem["global"])
        memn = len(mem.get("chapters", []))
    except Exception as e:
        memn = 0
        print("  (记忆迁移跳过:", str(e)[:60], ")")
    print(f"迁移完成: work_id={nw}, 章={nchap}, 字={nword}, 章记忆={memn}")
    summ = next(x for x in d.work_summaries("u1") if x["id"] == nw)
    print(f"SurrealDB 校验汇总: {summ['chapter_count']} 章 / {summ['word_count']} 字 / "
          f"{len(d.list_characters(nw))} 角色 / {len(d.list_settings(nw))} 设定 / "
          f"{len(d.list_open_foreshadows(nw))} 伏笔")


if __name__ == "__main__":
    main()

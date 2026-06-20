"""把已写各章按卷/序组装成单一全本 + 统计字数。
跑:cd scribe && .venv/bin/python tools/assemble_novel.py
输出:out/九原渡_全本.md,并打印各卷/全书 CJK 字数。
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIBLE = HERE / "bible_jiuyuandu.json"
OUT_DIR = HERE.parent / "out" / "九原渡"
FULL = HERE.parent / "out" / "九原渡_全本.md"


def cjk(s):
    return len(re.findall(r"[一-鿿]", s or ""))


def main():
    b = json.loads(BIBLE.read_text(encoding="utf-8"))
    vol_title = {v["seq"]: v["title"] for v in b["volumes"]}
    parts = [f"# {b['title']}\n", f"> {b['premise']}\n"]
    total = 0
    per_vol = {}
    cur_vol = None
    for ch in sorted(b["chapters"], key=lambda c: c["seq"]):
        seq = ch["seq"]
        f = OUT_DIR / f"第{seq:02d}章_{ch['title']}.md"
        if not f.exists():
            continue
        vs = ch.get("volume_seq")
        if vs != cur_vol:
            cur_vol = vs
            parts.append(f"\n\n## 卷{['一','二','三'][vs-1] if vs and vs<=3 else vs} {vol_title.get(vs,'')}\n")
        body = re.sub(r"^#.*\n", "", f.read_text(encoding="utf-8")).strip()
        n = cjk(body)
        total += n
        per_vol[vs] = per_vol.get(vs, 0) + n
        parts.append(f"\n### 第{seq}章 {ch['title']}\n\n{body}\n")
    FULL.write_text("\n".join(parts), encoding="utf-8")
    print(f"全本已写出: {FULL}")
    for vs in sorted(per_vol):
        print(f"  卷{vs} {vol_title.get(vs,'')}: {per_vol[vs]} 字")
    written = sum(1 for ch in b["chapters"] if (OUT_DIR / f"第{ch['seq']:02d}章_{ch['title']}.md").exists())
    print(f"全书: {total} 字 / {written} 章(共设计 {len(b['chapters'])} 章)")
    if total >= 100000:
        print("✓ 已达 10 万字")
    else:
        print(f"距 10 万字还差 {100000 - total} 字")


if __name__ == "__main__":
    main()

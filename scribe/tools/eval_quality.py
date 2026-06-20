"""质量评估:用系统自己的 8 维 critique 量表,给『九原渡』各章与基准『乱世铜炉』
节选同标尺打分,做 apples-to-apples 对比——客观回答"是否达到乱世铜炉质量"。

跑:cd scribe && .venv/bin/python tools/eval_quality.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scribe_mcp import llm as _llm
from scribe_mcp.critique import build_critique_prompt, parse_critique

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "out" / "九原渡"
BENCH = HERE.parent.parent / "乱世铜炉.md"
READER_FEELING = "苍凉、克制,乱世里被小人物不肯泯灭的良心刺痛,读罢久久不能言语"


def _load_volc():
    import re as _re
    base, model, key = "", "doubao-seed-2.0-pro", ""
    try:
        t = (Path.home() / ".hermes" / "config.yaml").read_text(encoding="utf-8")
        m = _re.search(r"base_url:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); base = m.group(1) if m else ""
        m = _re.search(r"^\s*default:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); model = m.group(1) if m else model
        m = _re.search(r"api_key:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); key = m.group(1) if m else ""
    except Exception:
        pass
    return base, model, key


_BASE, _MODEL, _KEY = _load_volc()


def _cjk(s):
    return len(re.findall(r"[一-鿿]", s or ""))


def score_text(text: str) -> dict:
    reply = _llm.complete(_BASE, _KEY, _MODEL, build_critique_prompt(text, READER_FEELING))["content"]
    return parse_critique(reply)


def bench_excerpts(n_each=3200, count=3):
    """从乱世铜炉切几段 ~n_each 字的连续节选当『章』对比。跳过开头目录区。"""
    raw = BENCH.read_text(encoding="utf-8")
    paras = [p for p in raw.split("\n") if _cjk(p) > 20]
    chunks, cur = [], ""
    for p in paras:
        cur += p + "\n"
        if _cjk(cur) >= n_each:
            chunks.append(cur.strip()); cur = ""
            if len(chunks) >= count + 1:
                break
    return chunks[1:count + 1]  # 跳过第一段(引子开头),取中段更代表持续质量


def main():
    if not (_BASE and _KEY):
        print("无火山参数,评估中止"); return
    rows = []
    # 九原渡 已写章
    for f in sorted(OUT_DIR.glob("第*.md")):
        text = f.read_text(encoding="utf-8")
        text = re.sub(r"^#.*\n", "", text).strip()
        c = score_text(text)
        rows.append((f.stem, _cjk(text), c.get("overall"), c.get("pass"), c.get("worst_dims")))
        print(f"[九原渡] {f.stem:16s} {_cjk(text):5d}字 overall={c.get('overall')} "
              f"pass={c.get('pass')} 弱={c.get('worst_dims')}", flush=True)
    # 乱世铜炉 基准节选
    for i, ex in enumerate(bench_excerpts(), 1):
        c = score_text(ex)
        rows.append((f"乱世铜炉节选{i}", _cjk(ex), c.get("overall"), c.get("pass"), c.get("worst_dims")))
        print(f"[基准]   乱世铜炉节选{i:<8d} {_cjk(ex):5d}字 overall={c.get('overall')} "
              f"pass={c.get('pass')} 弱={c.get('worst_dims')}", flush=True)
    # 汇总
    jy = [r[2] for r in rows if r[0].startswith("第") and r[2]]
    bm = [r[2] for r in rows if "铜炉" in r[0] and r[2]]
    if jy:
        print(f"\n九原渡 均分 {sum(jy)/len(jy):.2f}({len(jy)}章)")
    if bm:
        print(f"乱世铜炉 均分 {sum(bm)/len(bm):.2f}({len(bm)}节)")


if __name__ == "__main__":
    main()

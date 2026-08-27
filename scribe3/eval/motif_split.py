"""Split shared craft from book-specific motifs. Zero LLM."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
TONGLU_CARDS = ROOT / "docs/worlds/乱世铜炉-拆文/章卡"
LOTM_CARDS = ROOT / "docs/worlds/诡秘之主-拆文/章卡"
OUT_MD = ROOT / "docs/worlds/两本对照/母题分层.md"
OUT_BLACKLIST = EVAL / "motif_blacklist.json"

GAP = 0.15
HIGH = 0.08

# Surface strings counted in whole cards. Names are report labels.
FEATURES: tuple[tuple[str, str], ...] = (
    ("账", "账"),
    ("盘点", "盘点"),
    ("对账", "对账"),
    ("银子", "银子"),
    ("钱", "钱"),
    ("人情", "人情"),
    ("眼睛", "眼睛"),
    ("翻了", "翻了"),
    ("没翻", "没翻"),
    ("回不去", "回不去"),
    ("日子", "日子"),
    ("办事", "办事"),
    ("开坛", "开坛"),
    ("酒宴", "酒宴"),
    ("井", "井"),
    ("灯", "灯"),
    ("墓", "墓"),
    ("魔药", "魔药"),
    ("序列", "序列"),
    ("非凡", "非凡"),
    ("说书", "说书"),
    ("旁白", "旁白"),
    ("假", "假 → 破"),
    ("破功", "破功"),
)

BLACKLIST_TERMS: tuple[str, ...] = (
    "账",
    "盘点",
    "清算",
    "对账",
    "欠款",
    "差钱",
)


def classify_feature(
    rate_tonglu: float,
    rate_lotm: float,
    n_tonglu: int | None = None,
    n_lotm: int | None = None,
) -> str:
    del n_tonglu, n_lotm
    gap = abs(rate_tonglu - rate_lotm)
    mx = max(rate_tonglu, rate_lotm)
    if mx < HIGH:
        return "不确定"
    if gap >= GAP:
        return "单本母题"
    return "通则"


def _card_dir(path: Path) -> list[str]:
    texts = []
    for p in sorted(path.glob("*.md"), key=lambda x: int(x.stem) if x.stem.isdigit() else 10**9):
        texts.append(p.read_text(encoding="utf-8"))
    return texts


def _rate(texts: list[str], needle: str) -> tuple[int, float]:
    hits = sum(1 for t in texts if needle in t)
    n = len(texts) or 1
    return hits, hits / n


def split_motifs() -> list[dict]:
    tonglu = _card_dir(TONGLU_CARDS)
    lotm = _card_dir(LOTM_CARDS)
    rows = []
    for needle, name in FEATURES:
        ht, rt = _rate(tonglu, needle)
        hl, rl = _rate(lotm, needle)
        rows.append(
            {
                "name": name if name != "假 → 破" else "假",
                "needle": needle,
                "n_tonglu": len(tonglu),
                "n_lotm": len(lotm),
                "hits_tonglu": ht,
                "hits_lotm": hl,
                "rate_tonglu": round(rt, 4),
                "rate_lotm": round(rl, 4),
                "gap": round(abs(rt - rl), 4),
                "bucket": classify_feature(rt, rl),
            }
        )
    # keep 账 label exact
    for r in rows:
        if r["needle"] == "账":
            r["name"] = "账"
    return rows


def render_md(rows: list[dict]) -> str:
    buckets = {"通则": [], "单本母题": [], "不确定": []}
    for r in rows:
        buckets[r["bucket"]].append(r)

    def block(title: str, items: list[dict], note: str) -> str:
        lines = [f"## {title}", note, ""]
        if not items:
            lines.append("（本档暂无条目）")
            lines.append("")
            return "\n".join(lines)
        lines.append("| 特征 | 铜炉 | 诡秘 | 差距 |")
        lines.append("|---|---|---|---|")
        for r in items:
            lines.append(
                f"| {r['name']} | {r['hits_tonglu']}/{r['n_tonglu']} ({r['rate_tonglu']:.1%}) "
                f"| {r['hits_lotm']}/{r['n_lotm']} ({r['rate_lotm']:.1%}) | {r['gap']:.1%} |"
            )
        lines.append("")
        return "\n".join(lines)

    parts = [
        "# 两本对照 · 母题分层",
        "",
        "纯脚本统计章卡用词。零 LLM。",
        "",
        "- **通则**：两本都常见，差距 < 15 个百分点 → 允许进写作提示（事后检查表也只用这些）。",
        "- **单本母题**：一本高一本低，差距 ≥ 15 个百分点 → **禁止**进写作提示。",
        "- **不确定**：两边都少 → 暂不使用。",
        "",
        "「账」是铜炉题材母题，不是写法通则。写作提示与样章核心冲突不得使用单本母题。",
        "",
        block("通则", buckets["通则"], "两本都高。写下一本时可以学。"),
        block("单本母题", buckets["单本母题"], "只属于其中一本的题材气味。禁止当作法搬走。"),
        block("不确定", buckets["不确定"], "样本太少或两边都稀，先不用。"),
    ]
    return "\n".join(parts).rstrip() + "\n"


def write_outputs() -> dict:
    rows = split_motifs()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_md(rows), encoding="utf-8")
    OUT_BLACKLIST.write_text(
        json.dumps(
            {
                "note": "写作提示与生成结果的核心冲突禁止命中。命中=作废重写。",
                "source": "motif_split.py",
                "terms": list(BLACKLIST_TERMS),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"n": len(rows), "path": str(OUT_MD)}


if __name__ == "__main__":
    print(json.dumps(write_outputs(), ensure_ascii=False))

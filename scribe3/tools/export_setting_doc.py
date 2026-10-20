"""把库里的设定导成人能读的一份文档。

分两块，对应「设定文」底下压着的两样东西：
  A 世界观设定集 —— 常量，写全书都在查
  B 信息调度账   —— 每章谁知道什么、埋什么收什么，只有系统记得住

用法：
    python -m scribe3.tools.export_setting_doc --db wanjie_scale --out docs/worlds/万界/设定文.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scribe3.knowledge import project_frame
from scribe3.store import SurrealStore


def _g(row, key, default=None):
    """store 各查询的返回形态不统一：有的给 dict，有的给 Entity 对象。"""
    if isinstance(row, dict):
        return row.get(key, default)
    val = getattr(row, key, None)
    if val is None:
        val = (getattr(row, "traits", None) or {}).get(key)
    return default if val is None else val


def _codex_block(st) -> list[str]:
    out: list[str] = []
    intent = st.get_intent() or {}
    if intent.get("north_star"):
        out += ["## 北极星", "", intent["north_star"], ""]
    if intent.get("red_lines"):
        out += ["## 红线", "", *[f"- {ln}" for ln in str(intent["red_lines"]).split("\n") if ln.strip()], ""]

    rules = st.list_world_rules() or []
    if rules:
        out += ["## 世界规则", ""]
        for r in rules:
            out.append(f"**{_g(r, 'name', '')}**" + (f"（{_g(r, 'category')}）" if _g(r, "category") else ""))
            for label, key in (("能做到", "capabilities"), ("做不到", "limitations"),
                               ("代价", "cost"), ("例外", "exceptions"), ("适用", "scope")):
                val = _g(r, key)
                if not val:
                    continue
                out.append(f"　{label}：{'；'.join(val) if isinstance(val, list) else val}")
            out.append("")

    chars = st.characters() or []
    if chars:
        out += ["## 人物", ""]
        for c in chars:
            tags = _g(c, "personality_tags") or []
            out.append(f"**{_g(c, 'name', '')}**"
                       + (f"　{'、'.join(tags)}" if tags else ""))
            for label, key in (("要什么", "surface_goal"), ("其实要", "deep_need"),
                               ("怕什么", "fear"), ("拧巴在", "internal_conflict"),
                               ("软肋", "weaknesses"), ("会什么", "abilities"),
                               ("[密] 底细", "backstory_secret")):
                val = _g(c, key)
                if not val:
                    continue
                out.append(f"　{label}：{'；'.join(val) if isinstance(val, list) else val}")
            out.append("")

    factions = st.list_factions() or []
    if factions:
        out += ["## 势力", ""]
        for f in factions:
            out.append(f"**{_g(f, 'name', '')}**"
                       + (f"　当家：{_g(f, 'leader')}" if _g(f, "leader") else ""))
            for label, key in (("明面上", "public_face"), ("信什么", "ideology"),
                               ("[密] 真图谋", "secret_agenda_secret")):
                if _g(f, key):
                    out.append(f"　{label}：{_g(f, key)}")
            goals = _g(f, "goals") or []
            for g in goals:
                if isinstance(g, dict):
                    out.append(f"　目标（{g.get('phase', '')}）：{g.get('target', '')}")
            out.append("")

    for label, fn, keys in (("物品", "list_items", ("description", "significance")),
                            ("术语", "list_terms", ("definition", "meaning", "description"))):
        rows = (getattr(st, fn)() or []) if hasattr(st, fn) else []
        if not rows:
            continue
        out += [f"## {label}", ""]
        for r in rows:
            desc = next((_g(r, k) for k in keys if _g(r, k)), "")
            out.append(f"- **{_g(r, 'name', '')}**：{desc}")
        out.append("")
    return out


def _ledger_block(st, hero: str) -> list[str]:
    out: list[str] = ["# B · 信息调度账", "",
                      "每章一条。「他此刻知道」是从库里按限知帧算出来的，不是抄的。", ""]
    chapters = sorted(st.chapters_lite() or [], key=lambda c: c.get("seq") or 0)
    for ch in chapters:
        seq = ch.get("seq")
        out.append(f"## 第 {seq} 章　{ch.get('title', '')}")
        out.append("")
        if ch.get("synopsis"):
            out.append(ch["synopsis"])
            out.append("")
        facts = [f for f in (st.facts_at(seq) or []) if f.valid_from == seq]
        if facts:
            out.append("**这章立的账**")
            for f in facts:
                out.append(f"- {'[密] ' if f.secret else ''}{f.entity_id}·{f.attribute}：{f.value}")
            out.append("")
        try:
            known = list(project_frame(st, hero, seq).facts)
            secrets = [f for f in known if f.secret]
            out.append(f"**{hero.replace('role:', '')}此刻知道 {len(known)} 条**"
                       + (f"（含 {len(secrets)} 条秘密）" if secrets else ""))
            out.append("")
        except Exception:
            pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8123/rpc")
    ap.add_argument("--ns", default="scribe3")
    ap.add_argument("--db", default="wanjie_scale")
    ap.add_argument("--hero", default="role:柳岸青")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    st = SurrealStore(url=a.url, ns=a.ns, db=a.db)
    try:
        lines = ["# 《万界概率战争》设定文", "",
                 "由系统从库导出。A 是常量，B 是每章的信息调度。", "",
                 "---", "", "# A · 世界观设定集", ""]
        lines += _codex_block(st)
        lines += ["---", ""]
        lines += _ledger_block(st, a.hero)
    finally:
        st.close()

    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    out_text = "\n".join(lines)
    p.write_text(out_text, encoding="utf-8")
    print(f"写出 {p}（{len(out_text)} 字）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

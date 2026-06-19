"""质量度量(工程6 · C6-2)—— 可机检指标 + 章/全书质量报告。

实现可从现有数据确定性计算的指标(纯函数/查询,可单测):
- Q1 反AI腔密度(slop_density,复用 antislop)
- M2 一致性错误(按 19 类 severity 加权计数)
- M3 伏笔回收率(time-aware:截至某章)
- 章/全书 QualityReport 聚合
LLM 主观维(Q2 意外性/Q3 北极星共鸣/Q4 质感)由 critique 评改环按 rubric 产出(见 critique.py),此处聚合其分数。
"""
from __future__ import annotations

from .antislop import slop_density

_SEV_WEIGHT = {"critical": 3.0, "major": 2.0, "minor": 1.0}


def foreshadow_payoff_rate(db, work_id: str, upto_seq: int | None = None) -> dict:
    """M3:回收率 = paid / (planted - abandoned)。time-aware:只计 foreshadow_chapter ≤ upto。"""
    rows = db.conn.execute("SELECT state, foreshadow_chapter FROM foreshadows WHERE work_id=?",
                           (work_id,)).fetchall()
    planted = paid = abandoned = 0
    for r in rows:
        if upto_seq is not None and (r["foreshadow_chapter"] or 0) > upto_seq:
            continue
        planted += 1
        if r["state"] == "paid":
            paid += 1
        elif r["state"] == "abandoned":
            abandoned += 1
    denom = max(1, planted - abandoned)
    return {"planted": planted, "paid": paid, "abandoned": abandoned,
            "payoff_rate": round(paid / denom, 3)}


def consistency_score(db, work_id: str) -> dict:
    """M2 代理:未决一致性问题按 severity 加权;score=1/(1+加权数)(越接近1越干净)。"""
    flags = db.list_consistency_flags(work_id, "open")
    by_class: dict[str, int] = {}
    weighted = 0.0
    for f in flags:
        by_class[f["error_class"]] = by_class.get(f["error_class"], 0) + 1
        weighted += _SEV_WEIGHT.get(f.get("severity", "minor"), 1.0)
    return {"open_flags": len(flags), "weighted": weighted,
            "by_class": by_class, "score": round(1.0 / (1.0 + weighted), 3)}


def chapter_quality(db, work_id: str, seq: int) -> dict:
    """单章可机检质量:字数、AI腔密度、本章相关未决一致性问题数。"""
    ch = db.get_chapter(work_id, seq)
    if not ch:
        return {}
    snaps = db.list_snapshots(ch["id"])
    text = snaps[-1]["content"] if snaps else ""
    flags = [f for f in db.list_consistency_flags(work_id, "open")
             if f.get("chapter_seq") == seq]
    return {"seq": seq, "words": len(text), "slop_density": round(slop_density(text), 2),
            "open_flags": len(flags)}


def work_quality_report(db, work_id: str) -> dict:
    """全书质量报告:规模 + 回收率 + 一致性 + 平均 AI腔密度 + 成本(若有 ledger)。"""
    chapters = db.list_chapters(work_id)
    per = [chapter_quality(db, work_id, c["seq"]) for c in chapters]
    per = [p for p in per if p]
    total_words = sum(p["words"] for p in per)
    avg_slop = round(sum(p["slop_density"] for p in per) / len(per), 2) if per else 0.0
    return {
        "chapters": len(chapters),
        "words": total_words,
        "avg_slop_density": avg_slop,
        "foreshadow": foreshadow_payoff_rate(db, work_id),
        "consistency": consistency_score(db, work_id),
        "weakest_chapters": sorted(per, key=lambda p: -p["slop_density"])[:5],
    }

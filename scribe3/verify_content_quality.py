"""内容质量轨 · 与 craft gates 分离。

存正文走 finalize_gate；本模块证明「像不像一章能用的稿」。
默认门槛 intentionally 偏严：达不到 → quality_ok=False，不得宣称高质量 PASS。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityThresholds:
    min_prose_chars: int = 1500          # 净文（去空白）
    min_dialogue_quotes: int = 1         # 至少一对引号对话或「」
    min_paragraphs: int = 3
    require_promise_hook_terms: bool = True
    # 伏笔 text 分词后至少命中 1 个实质词（长度≥2）
    min_motif_echo_hits: int = 1


DEFAULT_Q = QualityThresholds()


@dataclass
class QualityCheck:
    id: str
    ok: bool
    detail: str
    score: float | None = None  # 1-5 optional
    hard: bool = True


@dataclass
class ContentQualityReport:
    work: str
    seq: int
    ok: bool
    checks: list[QualityCheck] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "work": self.work,
            "seq": self.seq,
            "ok": self.ok,
            "quality_pass": self.ok,
            "checks": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "score": c.score, "hard": c.hard}
                for c in self.checks
            ],
            "scores": self.scores,
            "summary": self.summary,
            # 明确：与 craft gate 解耦
            "note": "quality_ok 独立于 craft gates；闸绿不得自动 quality_pass",
        }


def _strip_ws(s: str) -> str:
    return "".join((s or "").split())


def _work_name(st) -> str:
    return getattr(st, "db_name", None) or "unknown"


def review_chapter_quality(
    st, seq: int, *,
    thresholds: QualityThresholds | None = None,
    prose: str | None = None,
) -> ContentQualityReport:
    t = thresholds or DEFAULT_Q
    ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else None
    if not ch:
        return ContentQualityReport(
            work=_work_name(st), seq=seq, ok=False,
            checks=[QualityCheck("Q0", False, f"章 {seq} 不存在")],
            summary="无章可评",
        )
    body = prose if prose is not None else (ch.get("prose") or "")
    net = _strip_ws(body)
    checks: list[QualityCheck] = []
    scores: dict[str, float] = {}

    # Q1 篇幅 — dual-lamp：长度 soft，不再单独否决 quality_ok（防灌水刷绿）
    if len(net) < t.min_prose_chars:
        checks.append(QualityCheck(
            "Q1_LENGTH", False,
            f"净文 {len(net)} < {t.min_prose_chars}（偏短提示，非充分否决）",
            score=max(1.0, min(5.0, len(net) / t.min_prose_chars * 3)),
            hard=False,
        ))
        scores["length"] = checks[-1].score or 1.0
    else:
        checks.append(QualityCheck(
            "Q1_LENGTH", True, f"净文 {len(net)}",
            score=min(5.0, 3.0 + len(net) / 2000),
            hard=False,
        ))
        scores["length"] = checks[-1].score or 4.0

    # Q2 段落结构
    paras = [p for p in (body or "").split("\n") if p.strip()]
    if len(paras) < t.min_paragraphs:
        checks.append(QualityCheck(
            "Q2_PARAS", False, f"段落 {len(paras)} < {t.min_paragraphs}", score=2.0))
        scores["structure"] = 2.0
    else:
        checks.append(QualityCheck(
            "Q2_PARAS", True, f"段落 {len(paras)}", score=4.0, hard=False))
        scores["structure"] = 4.0

    # Q3 对白存在
    dialogue = body.count("「") + body.count("」") + body.count("“") + body.count("\"")
    # 也认：说/道 + 冒号短句
    if dialogue < t.min_dialogue_quotes * 2 and "半句" in body and "「" not in body:
        checks.append(QualityCheck(
            "Q3_DIALOGUE", False,
            "宣称对话/半句但无实际引语对白，人物声音虚",
            score=2.0,
        ))
        scores["voice"] = 2.0
    elif dialogue >= 2:
        checks.append(QualityCheck("Q3_DIALOGUE", True, "有引语对白", score=4.0))
        scores["voice"] = 4.0
    else:
        checks.append(QualityCheck(
            "Q3_DIALOGUE", False, "对白不足，冲突难落地", score=2.5))
        scores["voice"] = 2.5

    # Q4 伏笔可追踪：open promise 关键词
    opens = []
    if hasattr(st, "open_promises"):
        opens = st.open_promises() or []
    miss_p = []
    for p in opens:
        text = (p.get("text") or "").strip()
        if not text:
            continue
        # 取长度≥2 的连续汉字/词粗探针
        tokens = []
        for i in range(len(text) - 1):
            tok = text[i:i + 2]
            if tok.strip():
                tokens.append(tok)
        # 特殊：反噬、立契
        for key in ("反噬", "立契", "灰契"):
            if key in text:
                tokens.insert(0, key)
        hit = any(tok in body for tok in tokens[:12])
        if not hit and t.require_promise_hook_terms:
            miss_p.append(text[:30])
    if opens and miss_p:
        checks.append(QualityCheck(
            "Q4_PROMISE_HOOK", False,
            f"open 伏笔未在正文形成可追踪钩子: {miss_p}",
            score=2.0,
        ))
        scores["promise"] = 2.0
    elif opens:
        checks.append(QualityCheck(
            "Q4_PROMISE_HOOK", True, "伏笔钩子有字面/近义命中", score=3.5, hard=False))
        scores["promise"] = 3.5
    else:
        checks.append(QualityCheck(
            "Q4_PROMISE_HOOK", False, "无 open 伏笔可评（应先 GATE-A）", score=1.0))
        scores["promise"] = 1.0

    # Q5 母题回声 + 主题词「代价」类
    motifs = st.list_motifs() if hasattr(st, "list_motifs") else []
    echo_ok = 0
    theme_ok = False
    for m in motifs or []:
        echoes = (m.get("echoes") or "").replace("、", "/").replace(",", "/")
        for part in echoes.split("/"):
            part = part.strip()
            if part and part in body:
                echo_ok += 1
        theme = (m.get("theme") or "")
        for k in ("代价", "契约", "反噬", "债"):
            if k in theme and k in body:
                theme_ok = True
    if motifs and echo_ok < t.min_motif_echo_hits:
        checks.append(QualityCheck(
            "Q5_MOTIF", False, "母题回声词未进入正文", score=2.0))
        scores["motif"] = 2.0
    elif motifs and not theme_ok:
        checks.append(QualityCheck(
            "Q5_MOTIF", False,
            "有回声词但主题（代价/契约）未戏剧化",
            score=2.5, hard=False,
        ))
        scores["motif"] = 2.5
    elif motifs:
        checks.append(QualityCheck("Q5_MOTIF", True, "母题回声+主题有着落", score=4.0, hard=False))
        scores["motif"] = 4.0
    else:
        checks.append(QualityCheck("Q5_MOTIF", False, "无母题", score=1.0))
        scores["motif"] = 1.0

    # Q6 投影卫生：焦点投影不得含 secret leak markers
    foc = (ch.get("focalizer") or "").strip()
    deds = ch.get("deductions") or []
    leak_markers = []
    if hasattr(st, "facts_at"):
        for f in st.facts_at(seq) or []:
            if getattr(f, "secret", False):
                leak_markers.extend(getattr(f, "leak_markers", None) or [])
    dirty = []
    for d in deds:
        if not isinstance(d, dict):
            continue
        if foc and str(d.get("character_id")) != foc:
            continue
        prose_d = d.get("prose") or ""
        for m in leak_markers:
            if m and m in prose_d:
                dirty.append(m)
    if dirty:
        checks.append(QualityCheck(
            "Q6_DED_CLEAN", False,
            f"焦点投影含私密破绽词 {dirty}（演绎未接地）",
            score=1.0,
        ))
        scores["deduction"] = 1.0
    else:
        checks.append(QualityCheck(
            "Q6_DED_CLEAN", True, "焦点投影未见 leak_markers", score=4.0))
        scores["deduction"] = 4.0

    # Q7 关系戏：关系类型词或双方名字共现冲突
    rel_ok = False
    if hasattr(st, "_all_relations"):
        try:
            for r in st._all_relations() or []:
                # 双方名在正文
                src, dst = r.get("src"), r.get("dst")
                if src and dst and src in body and dst in body:
                    rel_ok = True
        except Exception:
            pass
    # 名字可能带 role 剥掉
    if "沈砚" in body and "老道" in body:
        rel_ok = True
    if not rel_ok:
        checks.append(QualityCheck(
            "Q7_RELATION", False, "正文未同时激活关系双方", score=2.0, hard=False))
        scores["relation"] = 2.0
    else:
        checks.append(QualityCheck(
            "Q7_RELATION", True, "关系双方在场", score=3.5, hard=False))
        scores["relation"] = 3.5

    hard_fails = [c for c in checks if c.hard and not c.ok]
    ok = not hard_fails
    # 额外：均分 < 3.5 也否（高质量线）
    if scores:
        avg = sum(scores.values()) / len(scores)
        scores["average"] = round(avg, 2)
        if avg < 3.5:
            ok = False
            checks.append(QualityCheck(
                "Q8_AVG", False, f"维度均分 {avg:.2f} < 3.5（高质量线）",
                score=avg, hard=True,
            ))

    summary = (
        "内容质量通过" if ok else
        "内容质量不通过：闸绿不能代替章级完成度/辅信戏剧化"
    )
    return ContentQualityReport(
        work=_work_name(st), seq=seq, ok=ok, checks=checks,
        scores=scores, summary=summary,
    )

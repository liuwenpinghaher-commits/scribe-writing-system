"""人物选择可信问诊 + 确定性种子建议。"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# 中文/英文专名粗启发:连续 2+ 汉字专名或大写词
_PROPER_RE = re.compile(
    r"[\u4e00-\u9fff]{2,4}(?:真名|秘方|灰契|令牌|铜炉|剑|印)?"
    r"|[A-Z][a-z]{2,12}"
)
_UNANSWERED_RE = re.compile(
    r"[「『“][^」』”]{2,40}[？?][」』”]|[^。！？\n]{2,30}[？?]"
)


def build_choice_audit(
    *,
    quote: str,
    character_id: str = "",
    anchors: dict | None = None,
    recent_synopsis: str = "",
) -> dict[str, Any]:
    """固定模板质疑 + 证据摘录;无 likeness 分数。"""
    anchors = anchors or {}
    quote = (quote or "").strip()[:300]
    cid = (character_id or anchors.get("id") or anchors.get("name") or "焦点者")[:60]
    want = (anchors.get("surface_goal") or anchors.get("want")
            or anchors.get("desire") or "")[:80]
    fear = (anchors.get("fear") or "")[:80]
    lie = (anchors.get("lie") or anchors.get("internal_conflict") or "")[:80]
    name = (anchors.get("name") or cid)[:40]

    evidence = []
    if want:
        evidence.append({"field": "want_or_goal", "text": want})
    if fear:
        evidence.append({"field": "fear", "text": fear})
    if lie:
        evidence.append({"field": "lie_or_conflict", "text": lie})
    if recent_synopsis:
        evidence.append({"field": "recent_synopsis", "text": recent_synopsis[:160]})
    if quote:
        evidence.append({"field": "choice_quote", "text": quote})

    question = (
        f"关键选择可信度:「{name}」做出「{(quote or '（未摘录）')[:40]}」时,"
        f"是否与已建立的欲望「{want or '—'}」/恐惧「{fear or '—'}」形成合理张力?"
        f"若属性格叛变,前文是否赚够?（无评分,请作者判断）"
    )
    return {
        "character_id": cid,
        "quote": quote,
        "question": question,
        "evidence": evidence,
        # 明确无分
        "likeness_score": None,
        "note": "模板问诊,非模型打分;作者终裁。",
    }


def suggest_seeds(prose: str, *, existing_promise_texts: list[str] | None = None,
                  seq: int | None = None) -> list[dict[str, Any]]:
    """确定性启发:反复专名/物件、未答之问。不写正典。"""
    text = prose or ""
    existing = {(t or "").strip() for t in (existing_promise_texts or []) if t}
    # 候选:2–3 字中文滑窗 + 英文专名;用 str.count 计真实出现
    candidates: set[str] = set()
    chars = list(text)
    for i, ch in enumerate(chars):
        if "\u4e00" <= ch <= "\u9fff":
            if i + 1 < len(chars) and "\u4e00" <= chars[i + 1] <= "\u9fff":
                candidates.add(ch + chars[i + 1])
            if i + 2 < len(chars) and all("\u4e00" <= chars[i + j] <= "\u9fff" for j in (1, 2)):
                candidates.add(ch + chars[i + 1] + chars[i + 2])
    for m in re.finditer(r"[A-Z][a-z]{2,12}", text):
        candidates.add(m.group(0))
    counts: dict[str, int] = {}
    for term in candidates:
        n = text.count(term)
        if n >= 2 and len(term) >= 2:
            counts[term] = n

    def _tracked(term: str) -> bool:
        """仅当已有伏笔文本与种子实质等同才跳过(避免「灰契」被「灰契背面真名」误杀)。"""
        for e in existing:
            e = (e or "").strip()
            if not e:
                continue
            if e == term or term == e:
                return True
            # 伏笔以该词开头且很短后缀(「灰契。」类)
            if e.startswith(term) and len(e) <= len(term) + 2:
                return True
        return False

    seeds: list[dict[str, Any]] = []
    # 优先更长、更高频
    for term, n in sorted(counts.items(), key=lambda x: (-x[1], -len(x[0]))):
        if _tracked(term):
            continue
        # 短串若被同频更长串包含则跳过
        if len(term) == 2 and any(
            len(t2) > 2 and term in t2 and counts.get(t2, 0) >= n for t2 in counts
        ):
            continue
        sid = "seed-" + hashlib.sha1(f"{seq}:{term}".encode()).hexdigest()[:10]
        seeds.append({
            "id": sid,
            "kind": "repeated_marker",
            "text": term,
            "count": n,
            "seq": seq,
            "promoted": False,
            "detail": f"正文出现 {n} 次,可能是可登记种子",
        })
        if len(seeds) >= 8:
            break

    for m in _UNANSWERED_RE.finditer(text):
        q = m.group(0).strip()[:60]
        if any(q in e for e in existing):
            continue
        sid = "seed-" + hashlib.sha1(f"{seq}:q:{q}".encode()).hexdigest()[:10]
        if any(s["id"] == sid for s in seeds):
            continue
        seeds.append({
            "id": sid,
            "kind": "unanswered",
            "text": q,
            "count": 1,
            "seq": seq,
            "promoted": False,
            "detail": "疑似未答之问/悬置,可升格为伏笔",
        })
        if len(seeds) >= 12:
            break
    return seeds


def promote_seed_payload(seed: dict) -> dict[str, Any]:
    """生成走现有 promise 登记通道的 payload;调用方必须再走审批/API。

    本函数**不**写 store。
    """
    if not seed or seed.get("promoted"):
        raise ValueError("seed 无效或已 promote")
    text = (seed.get("text") or "").strip()
    if len(text) < 2:
        raise ValueError("seed text 过短")
    return {
        "text": text[:120],
        "setup_chapter": seed.get("seq"),
        "source": "seed_miner",
        "seed_id": seed.get("id"),
        "requires_approval": True,
        "note": "须经现有伏笔/promise 门控写入,禁止自动 plant",
    }

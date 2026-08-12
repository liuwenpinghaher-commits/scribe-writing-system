"""结构多样性 / 反 AI 味检测（无 POS · rev.1.2 WS-2）。

纯函数、零 store I/O。默认 advisory；不硬拦 finalize。
"""
from __future__ import annotations

import os
import re
from typing import Any


def structure_diversity_inject_enabled() -> bool:
    v = (os.environ.get("SCRIBE3_STRUCTURE_DIVERSITY_INJECT") or "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def ending_formula_blocking() -> bool:
    v = (os.environ.get("SCRIBE3_ENDING_FORMULA_BLOCKING") or "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def structure_diversity_block() -> str:
    """生成前 ≤200 字纪律段。"""
    return (
        "【结构多样性】段型轮换：长短交错、对白与叙述交替，避免连续三段同构。"
        "章末禁止默认「短句收束+意象回扣」公式；比喻克制（「像」字勿过密）。"
        "用物象推进情绪，少用排比收束。"
    )


def paragraph_fingerprint(para: str) -> tuple:
    """无 POS 段指纹：(len_bucket, sent_bucket, open_pat, dlg_bucket)。"""
    text = para or ""
    lines = [l for l in text.splitlines() if l.strip()]
    n = len(text.strip())
    len_bucket = 0 if n <= 40 else 1 if n <= 120 else 2 if n <= 280 else 3
    sents = re.split(r"[。！？…]+", text)
    sents = [s for s in sents if s.strip()]
    sent_bucket = min(len(sents), 6)
    head = text.strip()
    if head[:1] in "「『\"“":
        open_pat = "Q"
    elif head.startswith(("—", "…")):
        open_pat = "D"
    else:
        hans = re.findall(r"[\u4e00-\u9fff]", head)
        open_pat = "".join(hans[:2]) if hans else "?"
    if not lines:
        dlg_bucket = 0
    else:
        dlg = sum(1 for l in lines if any(q in l for q in "「」『』\"“”"))
        ratio = dlg / len(lines)
        dlg_bucket = 0 if ratio < 0.25 else 1 if ratio < 0.75 else 2
    return (len_bucket, sent_bucket, open_pat, dlg_bucket)


def find_paragraph_isomorphism(
    text: str, min_run: int = 3,
) -> list[dict[str, Any]]:
    """连续 ≥min_run 段指纹相同 → 同构 run。"""
    paras = [p for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    fps = [paragraph_fingerprint(p) for p in paras]
    out: list[dict[str, Any]] = []
    i, n = 0, len(fps)
    while i < n:
        j = i + 1
        while j < n and fps[j] == fps[i]:
            j += 1
        if j - i >= min_run:
            out.append({
                "start": i,
                "count": j - i,
                "fp": fps[i],
                "sample": paras[i][:40],
            })
        i = j if j > i else i + 1
    return out


def _high_freq_noun_candidates(body: str, min_freq: int = 2) -> set[str]:
    """前 80% 正文中频次≥2 的 2–4 字汉字窗（弱名词候选，无 POS）。"""
    hans = "".join(re.findall(r"[\u4e00-\u9fff]", body or ""))
    if len(hans) < 4:
        return set()
    cut = max(1, int(len(hans) * 0.8))
    prefix = hans[:cut]
    counts: dict[str, int] = {}
    for w in (2, 3, 4):
        for i in range(0, max(0, len(prefix) - w + 1)):
            tok = prefix[i : i + w]
            counts[tok] = counts.get(tok, 0) + 1
    return {k for k, v in counts.items() if v >= min_freq}


def detect_ending_formula(text: str) -> dict[str, Any]:
    """末 1–3 非空行：存在 ≤12 字短行，且其中 ≥1 个 ≥2 字汉字串出现在前 80% 高频候选。"""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return {"hit": False, "line": "", "matched": []}
    tail = lines[-3:] if len(lines) >= 3 else lines
    body_for_freq = "\n".join(lines)
    # 排除末行本身参与频次：用全文但依赖 min_freq≥2 与前文重复
    cands = _high_freq_noun_candidates(body_for_freq, min_freq=2)
    for line in reversed(tail):
        if len(line) > 12:
            continue
        hans = re.findall(r"[\u4e00-\u9fff]+", line)
        matched = []
        for h in hans:
            if len(h) >= 2 and h in cands:
                matched.append(h)
            else:
                for w in (2, 3, 4):
                    for i in range(0, max(0, len(h) - w + 1)):
                        tok = h[i : i + w]
                        if tok in cands:
                            matched.append(tok)
        if matched:
            return {
                "hit": True,
                "line": line,
                "matched": list(dict.fromkeys(matched))[:5],
            }
    return {"hit": False, "line": "", "matched": []}


def evaluate_structure_style(text: str) -> dict[str, Any]:
    """综合结构风格报告（默认 advisory）。"""
    iso = find_paragraph_isomorphism(text)
    ending = detect_ending_formula(text)
    # 宽松「像」密度
    body = text or ""
    chars = max(1, len("".join(body.split())))
    like_count = len(re.findall(r"像", body))
    simile_per_1k = round(like_count * 1000 / chars, 2)
    blocking = ending_formula_blocking() and ending.get("hit")
    return {
        "paragraph_isomorphism": iso,
        "isomorphism_hit": bool(iso),
        "ending_formula": ending,
        "ending_formula_hit": bool(ending.get("hit")),
        "simile_like_per_1k": simile_per_1k,
        "severity": "blocking" if blocking else "advisory",
        "blocks_finalize": bool(blocking),
    }

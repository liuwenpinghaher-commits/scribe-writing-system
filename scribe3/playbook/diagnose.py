"""Post-persist craft diagnostic. Never blocks persist."""
from __future__ import annotations

import re
from typing import Any, Callable

from scribe3.playbook.structural import list_syntax_tics

_SENT_SPLIT = re.compile(r"(?<=[。！？\n])")
_WS = re.compile(r"\s+")


def sentence_rhythm(prose: str) -> dict[str, Any]:
    """短句/长句占比与连续短句段数。只记账，不当及格线。"""
    parts = [p.strip() for p in _SENT_SPLIT.split(prose or "") if _WS.sub("", p or "")]
    n = len(parts)
    if n == 0:
        return {
            "sentences": 0,
            "short_n": 0,
            "long_n": 0,
            "short_ratio": 0.0,
            "long_ratio": 0.0,
            "short_bursts": 0,
        }
    lengths = [len(_WS.sub("", p)) for p in parts]
    shorts = [x <= 15 for x in lengths]
    longs = [x >= 40 for x in lengths]
    bursts = 0
    run = 0
    for is_short in shorts:
        if is_short:
            run += 1
            continue
        if run >= 4:
            bursts += 1
        run = 0
    if run >= 4:
        bursts += 1
    return {
        "sentences": n,
        "short_n": sum(shorts),
        "long_n": sum(longs),
        "short_ratio": sum(shorts) / n,
        "long_ratio": sum(longs) / n,
        "short_bursts": bursts,
    }


def style_judge_fields(prose: str) -> dict[str, str]:
    """定稿法官旁边的机器底：装腔原句 + 节奏三个数字。"""
    hits = list_syntax_tics(prose)
    if hits:
        tics = "\n".join(f"- {str(h.get('phrase') or '')[:80]}" for h in hits[:8])
    else:
        tics = "无"
    r = sentence_rhythm(prose)
    rhythm = (
        f"短句（≤15字）{r['short_n']}/{r['sentences']}={r['short_ratio']:.0%}；"
        f"长句（≥40字）{r['long_n']}/{r['sentences']}={r['long_ratio']:.0%}；"
        f"连续四句及以上短句 {r['short_bursts']} 段"
    )
    return {"syntax_tics_block": tics, "rhythm_block": rhythm}


def craft_diagnostic(prose: str, *, llm_fn: Callable | None = None) -> dict[str, Any]:
    """定稿冻住后记账。blocking 永远 False。默认不算模型。"""
    text = prose or ""
    rhythm = sentence_rhythm(text)
    report: dict[str, Any] = {
        "kind": "craft_diagnostic",
        "blocking": False,
        "chars": len(text),
        "sentence_rhythm": rhythm,
        "notes": [],
    }
    if llm_fn is None:
        report["notes"].append("未调用模型：只记句子长短，不做技法评审。")
        return report
    prompt = (
        "这是一篇已落库正文的事后技法诊断，不改稿、不判过不过。"
        "用三五行说节奏、声口、感官细节分布。不要给配额。"
        f"\n\n【正文】\n{text[:6000]}"
    )
    try:
        try:
            from scribe3.llm_temps import TEMP_DIAGNOSE
            note = llm_fn(prompt, max_tokens=600, temperature=TEMP_DIAGNOSE) or ""
        except TypeError:
            note = llm_fn(prompt) or ""
        report["notes"].append(str(note).strip()[:1200])
    except Exception as exc:
        report["notes"].append(f"诊断调用失败（不阻塞）: {exc}")
    return report

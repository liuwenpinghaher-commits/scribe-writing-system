"""Post-persist craft diagnostic. Never blocks persist."""
from __future__ import annotations

from typing import Any, Callable


def craft_diagnostic(prose: str, *, llm_fn: Callable | None = None) -> dict[str, Any]:
    """Async-shaped report. Empty llm_fn → structural stub only."""
    text = prose or ""
    report = {
        "kind": "craft_diagnostic",
        "blocking": False,
        "chars": len(text),
        "notes": [],
    }
    if llm_fn is None:
        report["notes"].append("未调用模型：只记字数，不做技法评审。")
        return report
    prompt = (
        "这是一篇已落库正文的事后技法诊断，不改稿、不判过不过。"
        "用三五行说节奏、声口、感官细节分布。不要给配额。"
        f"\n\n【正文】\n{text[:6000]}"
    )
    try:
        try:
            note = llm_fn(prompt, max_tokens=600, temperature=0.3) or ""
        except TypeError:
            note = llm_fn(prompt) or ""
        report["notes"].append(str(note).strip()[:1200])
    except Exception as exc:
        report["notes"].append(f"诊断调用失败（不阻塞）: {exc}")
    return report

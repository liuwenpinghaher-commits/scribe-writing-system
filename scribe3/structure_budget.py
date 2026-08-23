"""长篇结构预算建议。只建议，不挡写。"""
from __future__ import annotations


def word_goal_accepted(twg) -> bool:
    """全书目标字数是否合法。

    短卷旧档仍是 4–6 万；长篇/百万字 ≥20 万也算过。
    不得把 100 万判死、改回 5 万。
    """
    try:
        n = int(twg)
    except (TypeError, ValueError):
        return False
    if 40_000 <= n <= 60_000:
        return True
    if n >= 200_000:
        return True
    return False


def suggest_budget(total_word_goal: int | None, words_per_chapter: int = 3000) -> dict:
    goal = int(total_word_goal or 0)
    wpc = int(words_per_chapter or 3000) or 3000
    if goal >= 200_000:
        chapters = max(1, round(goal / wpc))
        volumes = max(4, round(chapters / 60))
        note = "百万字量级：卷数和章数只是建议，作者可改。"
    elif goal <= 0:
        chapters = 10
        volumes = 3
        note = "还没定全书字数，先按短卷建议。"
    else:
        chapters = max(3, round(goal / wpc))
        volumes = 3 if goal <= 80_000 else max(2, round(chapters / 12))
        note = "短卷建议：三卷左右，章数跟着字数走。"
    return {
        "total_word_goal": goal or None,
        "words_per_chapter": wpc,
        "volumes": int(volumes),
        "chapters": int(chapters),
        "advisory": True,
        "note": note,
    }

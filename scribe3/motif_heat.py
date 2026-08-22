"""MOT-05：同一母题连着碰太多次就告警。"""
from __future__ import annotations

from typing import Any

OVERHEAT_STREAK = 5


def motif_overheat_advisory(instances: list[dict] | None, *, streak: int = OVERHEAT_STREAK) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for it in instances or []:
        name = str((it or {}).get("motif") or (it or {}).get("name") or "")
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    out = []
    for name, n in counts.items():
        if n >= int(streak):
            out.append({
                "blocking": False,
                "kind": "motif_overheat",
                "motif": name,
                "count": n,
                "message": f"母题「{name}」连碰 {n} 次，过热了",
            })
    return out

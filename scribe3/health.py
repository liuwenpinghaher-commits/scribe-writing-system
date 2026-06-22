"""体检(cron 调):把"连贯性=可跑查询"聚合成跨章健康报告。

干净 → [SILENT](cron 只在异常时通知)。可扩展:后续加伏笔超期、跨章泄露扫描、声音一致性。
"""
from __future__ import annotations

from dataclasses import dataclass

from scribe3.verify import causal_complete


@dataclass
class HealthReport:
    chapters_checked: list[int]
    causal_violations: list   # [(chapter, event_id, reason)]

    @property
    def clean(self) -> bool:
        return not self.causal_violations


def health_report(store, up_to: int) -> HealthReport:
    """检查 1..up_to 章的连贯性(每事件须因果入边+目标)。"""
    chapters = list(range(1, max(up_to, 0) + 1))
    viols: list = []
    for ch in chapters:
        for v in causal_complete(store, ch):
            viols.append((ch, v.event_id, v.reason))
    return HealthReport(chapters, viols)


def render_markdown(rep: HealthReport) -> str:
    if rep.clean:
        return "[SILENT]"
    lines = [f"# scribe3 体检 · {len(rep.causal_violations)} 处连贯性问题"]
    for ch, ev, reason in rep.causal_violations:
        lines.append(f"- 第{ch}章 · {ev}:{reason}")
    return "\n".join(lines)

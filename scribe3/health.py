"""体检(cron 调):把"连贯性=可跑查询""伏笔超期=可跑查询"聚合成跨章健康报告。

干净 → [SILENT](cron 只在异常时通知)。伏笔超期告警是护城河(无竞品自动做)。
"""
from __future__ import annotations

from dataclasses import dataclass

from scribe3.verify import causal_complete

OVERDUE_SPAN = 3   # 伏笔埋下超过这么多章仍未回收 = 超期


@dataclass
class HealthReport:
    chapters_checked: list[int]
    causal_violations: list    # [(chapter, event_id, reason)]
    overdue_promises: list     # [promise dict]

    @property
    def clean(self) -> bool:
        return not self.causal_violations and not self.overdue_promises


def health_report(store, up_to: int) -> HealthReport:
    """检查 1..up_to 章连贯性 + 伏笔超期。"""
    chapters = list(range(1, max(up_to, 0) + 1))
    viols: list = []
    for ch in chapters:
        for v in causal_complete(store, ch):
            viols.append((ch, v.event_id, v.reason))
    overdue = [p for p in store.open_promises()
               if p["setup_chapter"] + OVERDUE_SPAN < up_to]
    return HealthReport(chapters, viols, overdue)


def render_markdown(rep: HealthReport) -> str:
    if rep.clean:
        return "[SILENT]"
    n = len(rep.causal_violations) + len(rep.overdue_promises)
    lines = [f"# scribe3 体检 · {n} 处问题"]
    for ch, ev, reason in rep.causal_violations:
        lines.append(f"- 连贯性 · 第{ch}章 {ev}:{reason}")
    for p in rep.overdue_promises:
        lines.append(f"- 伏笔超期 · 「{p['text']}」(第{p['setup_chapter']}章埋,至今未回收)")
    return "\n".join(lines)

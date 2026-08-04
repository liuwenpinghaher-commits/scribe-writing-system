"""体检(cron 调):把"连贯性=可跑查询""伏笔超期=可跑查询"聚合成跨章健康报告。

干净 → [SILENT](cron 只在异常时通知)。伏笔超期告警是护城河(无竞品自动做)。

门B · KR5 扩展:因果 + 超期伏笔 + ingest 失败 backlog + 文体漂移 proxy(可选)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from scribe3.store import OVERDUE_SLACK, _overdue_flag
from scribe3.verify import causal_complete


@dataclass
class HealthReport:
    chapters_checked: list[int]
    causal_violations: list    # [(chapter, event_id, reason)]
    overdue_promises: list     # [promise dict]
    ingest_failures: list = field(default_factory=list)  # [{seq, status, error}]
    style_drift_alerts: list = field(default_factory=list)
    pressure_jumps: list = field(default_factory=list)

    @property
    def clean(self) -> bool:
        # 文体漂移/压力跳变为观察项,不单独脏污 clean(与 scorecard 面板口径一致)
        return (not self.causal_violations and not self.overdue_promises
                and not self.ingest_failures)


def health_report(store, up_to: int) -> HealthReport:
    """检查 1..up_to 章连贯性 + 伏笔超期 + ingest 失败 + 可选文体/张弛 proxy。"""
    chapters = list(range(1, max(up_to, 0) + 1))
    viols: list = []
    for ch in chapters:
        for v in causal_complete(store, ch):
            viols.append((ch, v.event_id, v.reason))
    # H-1:cron 也走 _overdue_flag 单源(与 /promises、/quality、/promises/ledger、timeline 一致):
    # book 级伏笔永不超期、red_herring 不判、窗口口径统一——不再对它们永久误报。
    intent = store.get_intent()
    slack = (intent.get("overdue_threshold")
             if intent.get("overdue_threshold") is not None else OVERDUE_SLACK)
    overdue = [p for p in store.open_promises() if _overdue_flag(p, up_to, slack)]

    ingest_failures: list = []
    for ch in chapters:
        try:
            rows = store._query(
                "SELECT ingest_status, ingest_error FROM type::thing('chapter',$seq)",
                {"seq": ch}) if hasattr(store, "_query") else []
            row = rows[0] if rows else {}
            stt = row.get("ingest_status")
            if stt in ("failed", "parse_failed"):
                ingest_failures.append({
                    "seq": ch, "status": stt,
                    "error": (row.get("ingest_error") or "")[:200],
                })
        except Exception:
            continue

    style_alerts: list = []
    try:
        from scribe3.qd import style_drift_alerts
        if hasattr(store, "list_style_profiles"):
            style_alerts = list(style_drift_alerts(store.list_style_profiles() or []) or [])
    except Exception:
        style_alerts = []

    pressure_jumps: list = []
    try:
        from scribe3.brief import chapter_draft_text, parse_chapter_meta
        from scribe3.critique import find_pressure_adjacent_jumps
        metas = []
        lite = store.chapters_lite() if hasattr(store, "chapters_lite") else []
        for c in lite or []:
            if int(c.get("seq") or 0) > up_to:
                continue
            m = parse_chapter_meta(chapter_draft_text(c))
            if m and m.get("pressure") is not None:
                metas.append({"seq": c["seq"], "pressure": m["pressure"]})
        pressure_jumps = find_pressure_adjacent_jumps(metas)
    except Exception:
        pressure_jumps = []

    return HealthReport(chapters, viols, overdue,
                        ingest_failures=ingest_failures,
                        style_drift_alerts=style_alerts,
                        pressure_jumps=pressure_jumps)


def render_markdown(rep: HealthReport) -> str:
    if rep.clean and not rep.style_drift_alerts and not rep.pressure_jumps:
        return "[SILENT]"
    n = (len(rep.causal_violations) + len(rep.overdue_promises)
         + len(rep.ingest_failures))
    lines = [f"# scribe3 体检 · {n} 处问题"]
    for ch, ev, reason in rep.causal_violations:
        lines.append(f"- 连贯性 · 第{ch}章 {ev}:{reason}")
    for p in rep.overdue_promises:
        lines.append(f"- 伏笔超期 · 「{p['text']}」(第{p['setup_chapter']}章埋,至今未回收)")
    for it in rep.ingest_failures:
        lines.append(f"- 反哺失败 · 第{it['seq']}章 {it.get('status')}:{it.get('error') or ''}")
    for a in rep.style_drift_alerts[:8]:
        lines.append(f"- 文体漂移 · {a}")
    for j in rep.pressure_jumps[:8]:
        lines.append(f"- 张弛跳变 · {j.get('note') or j}")
    if n == 0 and (rep.style_drift_alerts or rep.pressure_jumps):
        lines[0] = "# scribe3 体检 · 观察项(无硬伤)"
    return "\n".join(lines)

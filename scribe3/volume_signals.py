"""卷级信号 · 伏笔超期 / 母题未回声(纯函数 + 薄 store 壳)。

门B · KR4:伏笔闭环可运营 + 母题卷级「无回声/未使用」信号。
不进 blocking;供 health / 面板 / 卷复盘只读消费。
"""
from __future__ import annotations

from typing import Any


def volume_chapter_seqs(chapters: list[dict], volume_id: str | None = None,
                        seq_from: int | None = None,
                        seq_to: int | None = None) -> list[int]:
    """从章节行筛卷内/区间内 seq 列表(升序)。volume_id 优先;否则用 seq 区间。"""
    rows = list(chapters or [])
    if volume_id:
        out = []
        for c in rows:
            vol = c.get("volume") or c.get("volume_id")
            if vol is None:
                continue
            # Surreal 可能返回 record id 字符串
            vs = str(vol).split(":")[-1] if ":" in str(vol) else str(vol)
            want = str(volume_id).split(":")[-1] if ":" in str(volume_id) else str(volume_id)
            if vs == want or str(vol) == str(volume_id):
                if c.get("seq") is not None:
                    out.append(int(c["seq"]))
        return sorted(set(out))
    lo = seq_from if seq_from is not None else 1
    hi = seq_to if seq_to is not None else 10**9
    return sorted(int(c["seq"]) for c in rows
                  if c.get("seq") is not None and lo <= int(c["seq"]) <= hi)


def overdue_promises_in_range(
    promises: list[dict],
    *,
    up_to: int,
    seqs: list[int] | None = None,
    slack: int = 3,
) -> list[dict]:
    """筛 open 且已超期的伏笔;可选限定 setup 落在卷内 seqs。

    超期口径:setup_chapter + window_window + slack < up_to 且无 payoff。
    与 store._overdue_flag 对齐的轻量版(无 book 级豁免时由调用方先滤)。
    """
    seq_set = set(seqs) if seqs is not None else None
    out: list[dict] = []
    for p in promises or []:
        if (p.get("status") or "open") != "open":
            continue
        if p.get("payoff_chapter"):
            continue
        setup = p.get("setup_chapter")
        if setup is None:
            continue
        setup = int(setup)
        if seq_set is not None and setup not in seq_set:
            continue
        # book 级 / red_herring 不判超期(与 health 单源语义对齐)
        span = str(p.get("span") or p.get("scope") or "")
        if span in ("book", "red_herring") or p.get("kind") == "red_herring":
            continue
        window = p.get("resolve_by")
        if window is None:
            window = p.get("window")
            if isinstance(window, dict):
                window = window.get("resolve_by") or window.get("expected_by")
        if window is None:
            # 默认窗口:setup + 5(与 OVERDUE_SLACK 常见用法相容的保守值)
            window = setup + 5
        try:
            due = int(window) + int(slack)
        except (TypeError, ValueError):
            continue
        if int(up_to) > due:
            out.append(dict(p, _overdue_by=int(up_to) - due))
    return out


def motifs_without_echo(
    motifs: list[dict],
    touch_by_motif: dict[str, list[int]],
    *,
    seqs: list[int] | None = None,
    min_registered: int = 1,
) -> list[dict]:
    """卷内/区间内从未被触及(无 echo)的已注册母题。

    motifs: [{id, name, ...}]
    touch_by_motif: motif_id -> [chapter_seq, ...]
    seqs: 若给定,只认落在该区间的触及。
    """
    if not motifs or len(motifs) < min_registered:
        return []
    seq_set = set(seqs) if seqs is not None else None
    unused: list[dict] = []
    for m in motifs:
        mid = str(m.get("id") or m.get("motif_id") or "")
        if not mid:
            continue
        touches = list(touch_by_motif.get(mid) or [])
        if seq_set is not None:
            touches = [t for t in touches if int(t) in seq_set]
        if not touches:
            unused.append({
                "motif_id": mid,
                "name": m.get("name") or mid,
                "signal": "no_echo",
                "detail": "卷/区间内无母题触及记录",
            })
    return unused


def volume_review_signals(
    *,
    chapters: list[dict],
    promises: list[dict],
    motifs: list[dict],
    touch_by_motif: dict[str, list[int]],
    volume_id: str | None = None,
    seq_from: int | None = None,
    seq_to: int | None = None,
    up_to: int | None = None,
    slack: int = 3,
) -> dict[str, Any]:
    """聚合卷复盘只读信号(无总分)。"""
    seqs = volume_chapter_seqs(chapters, volume_id=volume_id,
                               seq_from=seq_from, seq_to=seq_to)
    if up_to is None:
        up_to = max(seqs) if seqs else 0
    overdue = overdue_promises_in_range(promises, up_to=int(up_to), seqs=seqs, slack=slack)
    unused = motifs_without_echo(motifs, touch_by_motif, seqs=seqs)
    return {
        "seqs": seqs,
        "up_to": int(up_to),
        "overdue_promises": overdue,
        "overdue_count": len(overdue),
        "motifs_no_echo": unused,
        "motifs_no_echo_count": len(unused),
        "has_stale_signal": bool(overdue or unused),
    }


def store_volume_review(st, *, volume_id: str | None = None,
                        seq_from: int | None = None,
                        seq_to: int | None = None) -> dict[str, Any]:
    """从 store 拉数据算卷信号(fail-soft 单项)。"""
    chapters = []
    promises = []
    motifs = []
    touch_by_motif: dict[str, list[int]] = {}
    try:
        if hasattr(st, "chapters_lite"):
            chapters = list(st.chapters_lite() or [])
        elif hasattr(st, "list_chapters"):
            chapters = list(st.list_chapters() or [])
    except Exception:
        chapters = []
    try:
        if hasattr(st, "open_promises"):
            promises = list(st.open_promises() or [])
        if hasattr(st, "promises_with_lifecycle"):
            # 合并 open + 有生命周期字段
            pl = list(st.promises_with_lifecycle() or [])
            if pl:
                promises = pl
    except Exception:
        pass
    try:
        if hasattr(st, "list_motifs"):
            motifs = list(st.list_motifs() or [])
        elif hasattr(st, "all_motifs"):
            motifs = list(st.all_motifs() or [])
    except Exception:
        motifs = []
    try:
        # motif_instance / touches:尽量从 store 已有 API 取
        if hasattr(st, "motif_touch_map"):
            touch_by_motif = dict(st.motif_touch_map() or {})
        elif hasattr(st, "list_motif_instances"):
            for row in st.list_motif_instances() or []:
                mid = str(row.get("motif_id") or row.get("motif") or "")
                ch = row.get("chapter") or row.get("seq")
                if mid and ch is not None:
                    touch_by_motif.setdefault(mid, []).append(int(ch))
    except Exception:
        touch_by_motif = {}

    from scribe3.store import OVERDUE_SLACK
    slack = OVERDUE_SLACK
    try:
        intent = st.get_intent() if hasattr(st, "get_intent") else {}
        if intent and intent.get("overdue_threshold") is not None:
            slack = int(intent["overdue_threshold"])
    except Exception:
        pass

    return volume_review_signals(
        chapters=chapters, promises=promises, motifs=motifs,
        touch_by_motif=touch_by_motif, volume_id=volume_id,
        seq_from=seq_from, seq_to=seq_to, slack=slack,
    )

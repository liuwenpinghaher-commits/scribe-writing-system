"""铺章跟伏笔窗口走，不跟全书占比走。

对象有寿命：未到 payoff_min 不许收，过了 payoff_max 必须收，
book 线本卷没点名不许收。写厚只问本卷有没有用到，不问是不是满 3 条新键。
"""
from __future__ import annotations

from scribe3.charter import STORY_PREFIXES, normalize_charter


def promise_ref(p: dict) -> str:
    pid = str((p or {}).get("id") or "")
    return "L" + (pid.split(":")[-1] if ":" in pid else pid)


def _pmin(p: dict) -> int | None:
    pmin = p.get("payoff_min")
    if pmin is not None:
        return int(pmin)
    setup = p.get("setup_chapter")
    if setup is None:
        return None
    from scribe3.store.core_preamble import _TIER_WINDOW

    tier = str(p.get("tier") or "chapter")
    lo, _hi = _TIER_WINDOW.get(tier, _TIER_WINDOW["chapter"])
    return int(setup) + int(lo)


def payoff_skip_reason(promise: dict | None, chapter: int, *,
                       pays_refs: set[str] | None = None) -> str | None:
    """None = 这一章可以收。返回原因则 persist 跳过。不看 status（早收复查也要用）。"""
    if not promise:
        return None
    pays = {str(x).strip().upper() for x in (pays_refs or ()) if x}
    ref = promise_ref(promise).upper()
    tier = str(promise.get("tier") or "")
    if tier == "book" and ref not in pays:
        return "book 线本卷未点名，不许收"
    pmin = _pmin(promise)
    if pmin is not None and int(chapter) < pmin:
        return f"未到 payoff_min={pmin}，不许收"
    return None


def is_overdue(promise: dict, at_chapter: int) -> bool:
    if str(promise.get("status") or "open") != "open":
        return False
    pmax = promise.get("payoff_max")
    if pmax is None:
        return False
    return int(at_chapter) > int(pmax)


def pays_refs_for_volume(st, vol_id: str | None) -> set[str]:
    if not vol_id or not hasattr(st, "list_volumes"):
        return set()
    out: set[str] = set()
    for v in st.list_volumes() or []:
        if (v.get("id") or "") != vol_id:
            continue
        c = normalize_charter(v.get("charter"))
        for item in c.get("pays") or []:
            if isinstance(item, dict) and item.get("ref"):
                out.add(str(item["ref"]).strip().upper())
            elif isinstance(item, str) and item.strip().upper().startswith("L"):
                out.add(item.strip().upper())
    return out


def thicken_unused(st, oids: list[str], lo: int, hi: int) -> list[str]:
    """本卷 valid_from 落在 [lo,hi] 且没有任何故事命题的点名实体。"""
    want = [o for o in oids if o]
    seen: set[str] = set()
    for f in list(st.facts_at(hi) or []):
        eid = str(getattr(f, "entity_id", "") or "")
        ch = int(getattr(f, "valid_from", 0) or 0)
        if eid in want and eid.startswith(STORY_PREFIXES) and lo <= ch <= hi:
            seen.add(eid)
    return [o for o in want if o not in seen]


def assert_volume_lifetime(st, vol: dict, lo: int, hi: int,
                           top3: list[str] | None = None, *,
                           hero: str = "role:柳岸青") -> None:
    """卷末：点名实体必须被用到；逾期必须已收；前 3 名占比不抛。"""
    del top3  # 不再把关
    c = normalize_charter((vol or {}).get("charter"))
    rng = c["chapter_range"] or [lo, hi]
    vol_lo, vol_hi = int(rng[0]), int(rng[1])
    if hi >= vol_hi:
        oids = [i["oid"] for i in c["thickens"] if i.get("oid")]
        unused = thicken_unused(st, oids, vol_lo, hi)
        if unused:
            raise ValueError("本卷点名写厚的实体还没办事：" + "、".join(unused))
        overdue = [promise_ref(p) for p in (st.list_promises() or [])
                   if is_overdue(p, hi)]
        if overdue:
            raise ValueError("逾期未收：" + "、".join(overdue))
        pays = pays_refs_for_volume(st, (vol or {}).get("id"))
        early = []
        for p in st.list_promises() or []:
            if str(p.get("status") or "open") == "open":
                continue
            ch = p.get("payoff_chapter")
            if ch is None:
                continue
            ch = int(ch)
            if not (vol_lo <= ch <= vol_hi):
                continue
            reason = payoff_skip_reason(p, ch, pays_refs=pays)
            if reason:
                early.append(p)
        if early:
            if hasattr(st, "update_promise"):
                for p in early:
                    pid = str(p.get("id") or "")
                    local = pid.split(":")[-1] if ":" in pid else pid
                    if local:
                        st.update_promise(local, {"status": "open"})
            bits = "、".join(promise_ref(p) for p in early)
            raise ValueError(f"本卷不许收的长线被收掉了：{bits}")
        from scribe3.plot_rules import plot_deficits

        plot_msgs = plot_deficits(st, vol, lo, hi, hero=hero)
        if plot_msgs:
            raise ValueError("；".join(plot_msgs))

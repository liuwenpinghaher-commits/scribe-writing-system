"""校验层 · 兜底判官(查询,不是主防线)。

find_leaks:限知渲染已在生成前结构性防住 POV 泄露;这是第二道 POV 修订 pass——
  扫散文里是否冒出了 focalizer 帧外某私密的破绽词。craft 验证:别指望初稿自律,
  可靠层是检测 pass(+ 精修)。
causal_complete:把"连贯性"从噪声大的 LLM 评审,前移成可跑的结构查询。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from scribe3.knowledge import project_frame
from scribe3.ontology import World


@dataclass
class Leak:
    fact_id: str
    marker: str                                    # 命中的破绽词
    subject: str                                   # 私密属于谁
    range: tuple[int, int] | None = field(default=None)  # prose 字符 offset [start,end) (F-05)


@dataclass
class CausalViolation:
    event_id: str
    reason: str


def find_leaks(
    prose: str,
    world: World,
    focalizer: str,
    chapter: int,
    *,
    focal_deduction: str | None = None,
) -> list[Leak]:
    """扫 focalizer 视角散文里冒出的【帧外私密】破绽词。focalizer 自己知道的不算。
    F-05: 用 re.finditer 定位每处 marker 在 prose 中的字符 offset,存入 Leak.range。

    D13: 若提供焦点者限知投影 ``focal_deduction``，额外用其「没察觉的」层短语
    作限知边界——正文若写出这些盲区内容，记为演绎边界泄露（与知识帧泄露互补）。
    """
    frame = project_frame(world, focalizer, chapter)
    leaks: list[Leak] = []
    for f in world.facts_at(chapter):
        if not f.secret or frame.knows(f.id):
            continue
        for m in (f.leak_markers or [f.value]):
            if not m:
                continue
            # 用 finditer 找第一处命中,白送 offset
            match = next(re.finditer(re.escape(m), prose), None)
            if match:
                leaks.append(Leak(f.id, m, f.entity_id, range=(match.start(), match.end())))
                break
    # 工艺泄露：侧门开法 / 炉契全文 / 无铺垫怎知 / 刀鞘双真
    try:
        from scribe3.craft_leak_scan import scan_craft_leaks
        for row in scan_craft_leaks(prose, focalizer):
            mk = str(row.get("marker") or "")
            rng = row.get("range")
            leaks.append(Leak(
                str(row.get("id") or "craft"),
                mk,
                str(row.get("kind") or "craft"),
                range=tuple(rng) if rng else None,
            ))
    except Exception:
        pass
    # 演绎边界：焦点投影「没察觉的」
    if focal_deduction and (prose or "").strip():
        from scribe3.deduce_helpers import normalize_role_id, unaware_leak_markers

        foc = normalize_role_id(focalizer) or (focalizer or "")
        for m in unaware_leak_markers(focal_deduction):
            match = next(re.finditer(re.escape(m), prose), None)
            if match:
                leaks.append(Leak(
                    f"deduction:unaware:{foc}",
                    m,
                    foc or focalizer,
                    range=(match.start(), match.end()),
                ))
    return leaks


def focal_deduction_prose_for_leaks(ch: dict | None, focalizer: str | None) -> str | None:
    """取可用于 find_leaks 的焦点投影全文；过期投影不采用（避免旧盲区误报/漏报）。"""
    if not focalizer:
        return None
    from scribe3.deduce_helpers import (
        deduction_for_role,
        is_stale_deduction,
        truth_revision,
    )

    d = deduction_for_role(ch, focalizer)
    if not d:
        return None
    prose = (d.get("prose") or "").strip()
    if not prose:
        return None
    if is_stale_deduction(d, truth_revision(ch)):
        return None
    return prose


def find_leaks_for_chapter(
    prose: str,
    store,
    focalizer: str,
    chapter: int,
) -> list[Leak]:
    """章级封装：自动附带未过期的焦点限知投影边界。"""
    ch = store.get_chapter(chapter) if hasattr(store, "get_chapter") else None
    return find_leaks(
        prose,
        store,
        focalizer,
        chapter,
        focal_deduction=focal_deduction_prose_for_leaks(ch, focalizer),
    )


def proposition_local_id(fact_id: str | None) -> str:
    """归一命题本地 id：fact:治眼 / proposition:治眼 / 治眼 → 治眼。"""
    s = str(fact_id or "").strip()
    if not s:
        return ""
    if ":" in s:
        prefix, rest = s.split(":", 1)
        if prefix in ("fact", "proposition", "prop"):
            return rest.strip()
    return s


def enrich_leak_payload(
    leak: Leak | dict,
    store,
    chapter: int,
) -> dict:
    """序列化层：Leak → dict + knowers 富化（不改 Leak dataclass / 不改检测合同）。

    knowers 失败 → ``knowers=[]`` + ``knowers_status=error|unavailable``，永不抛穿。
    """
    if isinstance(leak, Leak):
        row = {
            "fact_id": leak.fact_id,
            "marker": leak.marker,
            "subject": leak.subject,
            "range": list(leak.range) if leak.range else None,
        }
    else:
        row = {
            "fact_id": (leak or {}).get("fact_id"),
            "marker": (leak or {}).get("marker"),
            "subject": (leak or {}).get("subject"),
            "range": (leak or {}).get("range"),
        }
    plocal = proposition_local_id(row.get("fact_id"))
    knowers: list = []
    status = "ok"
    if not plocal:
        status = "no_prop"
    elif not hasattr(store, "list_knowers_for_proposition"):
        status = "unavailable"
    else:
        try:
            knowers = list(store.list_knowers_for_proposition(plocal, int(chapter)) or [])
            # 不泄露 value；仅 id/name 等
            slim = []
            for k in knowers:
                if not isinstance(k, dict):
                    continue
                slim.append({
                    "id": k.get("id"),
                    "name": k.get("name"),
                    "since_chapter": k.get("since_chapter"),
                })
            knowers = slim
        except Exception:
            knowers = []
            status = "error"
    row["knowers"] = knowers
    row["knowers_status"] = status
    row["proposition_local"] = plocal
    # 交叉：焦点者是否在 knowers（仅提示，不改 S1）
    row["knowers_count"] = len(knowers)
    return row


def causal_complete(world: World, chapter: int) -> list[CausalViolation]:
    """每事件须 motivated_by_goal 非空；非首事件须有因果入边，或有可审计的新场景根理由。"""
    evs = sorted(world.events_at(chapter), key=lambda e: e.id)
    viols: list[CausalViolation] = []
    for i, ev in enumerate(evs):
        if not ev.motivated_by_goal:
            viols.append(CausalViolation(ev.id, "missing motivated_by_goal"))
        if not ev.causal_in and i > 0 and not (ev.causal_root_reason or "").strip():
            viols.append(CausalViolation(ev.id, "missing causal_in (非首事件须有因果入边)"))
    return viols

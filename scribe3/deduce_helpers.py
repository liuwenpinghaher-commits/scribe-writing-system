"""演绎(场景真相 · 多棱镜)纯函数：role id 规范化、真相 revision、投影 stale、五层标题。

无 IO。store / pilot / MCP / 前端逻辑应调用本模块，避免各处各写一套 id 比较。
"""
from __future__ import annotations

from typing import Any, Iterable

# 与 app_impl._DEDUCTION_HEADINGS 保持一致；写路径/检测以此为准。
DEDUCTION_HEADINGS: tuple[str, ...] = (
    "看到/听到",
    "知道",
    "以为(误读)",
    "做了/说了",
    "没察觉的",
)

_DEDUCTION_BLANK = "未能从场景真相确认。"


def normalize_role_id(value: Any) -> str:
    """稳定化为 `role:{bare}`；空串 / None → `""`。

    接受 `role:沈砚` / `沈砚` / 其它前缀取冒号后段再加 `role:`。
    非角色实体(如 `fact:x`)也会变成 `role:x`——调用方应只对角色 id 调用。
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    bare = s.split(":", 1)[-1].strip()
    if not bare:
        return ""
    return f"role:{bare}"


def role_id_keys(value: Any) -> set[str]:
    """同一角色的可互认键集合：原串、裸名、`role:裸名`。"""
    s = str(value or "").strip()
    if not s:
        return set()
    bare = s.split(":", 1)[-1].strip()
    if not bare:
        return {s}
    return {s, bare, f"role:{bare}"}


def normalize_involved(ids: Iterable[Any] | None) -> list[str]:
    """涉及角色列表：normalize + 去重（保序）。"""
    out: list[str] = []
    seen: set[str] = set()
    for raw in ids or []:
        nid = normalize_role_id(raw)
        if not nid or nid in seen:
            continue
        seen.add(nid)
        out.append(nid)
    return out


def truth_revision(ch: dict | None) -> int:
    """读章上的 scene_truth_revision；缺省 0。"""
    if not ch:
        return 0
    raw = ch.get("scene_truth_revision")
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def stamp_deduction(d: dict, rev: int) -> dict:
    """返回带 based_on_truth_rev 的投影副本；保留其它键。"""
    out = dict(d or {})
    cid = normalize_role_id(out.get("character_id") or out.get("character") or out.get("role"))
    if cid:
        out["character_id"] = cid
    try:
        out["based_on_truth_rev"] = max(0, int(rev))
    except (TypeError, ValueError):
        out["based_on_truth_rev"] = 0
    return out


def is_stale_deduction(d: dict | None, current_rev: int) -> bool:
    """投影是否相对当前真相 revision 过期。

    - 无 prose → 不算 stale（算 missing）
    - 缺 based_on_truth_rev：若 current_rev > 0 则 stale（真相已 bump 过、旧数据未 stamp）
    - based_on != current → stale
    """
    if not isinstance(d, dict):
        return False
    prose = (d.get("prose") or "").strip()
    if not prose:
        return False
    try:
        cur = max(0, int(current_rev))
    except (TypeError, ValueError):
        cur = 0
    if "based_on_truth_rev" not in d:
        return cur > 0
    try:
        based = int(d.get("based_on_truth_rev"))
    except (TypeError, ValueError):
        return True
    return based != cur


def normalize_deductions(deds: Iterable[Any] | None, *, current_rev: int | None = None,
                         stamp_missing_rev: bool = False) -> list[dict]:
    """规范化投影列表：character_id 统一；可选 stamp 缺失的 based_on。

    同一 normalize id 后出现多条时保留**最后**一条（后写覆盖）。

    注意：store 写路径应优先用 prepare_deductions_for_write，避免「全文重存」
    把缺 based_on 的旧 prose 误 stamp 成当前 rev、静默洗掉 stale。
    """
    by_id: dict[str, dict] = {}
    order: list[str] = []
    for raw in deds or []:
        if not isinstance(raw, dict):
            continue
        d = dict(raw)
        cid = normalize_role_id(d.get("character_id") or d.get("character") or d.get("role"))
        if not cid:
            continue
        d["character_id"] = cid
        if stamp_missing_rev and current_rev is not None and "based_on_truth_rev" not in d:
            d = stamp_deduction(d, current_rev)
        if cid not in by_id:
            order.append(cid)
        by_id[cid] = d
    return [by_id[i] for i in order]


def prepare_deductions_for_write(
    incoming: Iterable[Any] | None,
    existing: Iterable[Any] | None,
    next_rev: int,
) -> list[dict]:
    """写库前准备投影列表（不静默洗 stale）。

    规则：
    - character_id normalize；同 id 后写覆盖
    - **新角色**或 **prose 实质变化** → stamp based_on_truth_rev = next_rev
    - prose 未变：
      - 入参已带 based_on → 保留入参
      - 入参缺 based_on、库内有 → 继承库内 based_on
      - 入参与库内皆缺 based_on → **保持缺省**（rev>0 时 is_stale_deduction 仍为 stale）
    """
    try:
        rev = max(0, int(next_rev))
    except (TypeError, ValueError):
        rev = 0
    # 保留库内完整条目（含 based_on）
    existing_full: dict[str, dict] = {}
    for d in normalize_deductions(existing, stamp_missing_rev=False):
        existing_full[d["character_id"]] = d

    out: list[dict] = []
    for d in normalize_deductions(incoming, stamp_missing_rev=False):
        cid = d["character_id"]
        prose = (d.get("prose") or "").strip()
        old = existing_full.get(cid)
        is_new = old is None
        old_prose = ((old.get("prose") or "").strip() if old else "")
        prose_changed = (not is_new) and prose != old_prose

        if is_new or prose_changed:
            out.append(stamp_deduction(d, rev))
            continue

        # prose 未变：不得仅因「缺 based_on」而 stamp 到当前 rev
        if "based_on_truth_rev" in d and d.get("based_on_truth_rev") is not None:
            try:
                d["based_on_truth_rev"] = max(0, int(d["based_on_truth_rev"]))
            except (TypeError, ValueError):
                d["based_on_truth_rev"] = 0
            out.append(d)
            continue
        if old is not None and "based_on_truth_rev" in old and old.get("based_on_truth_rev") is not None:
            try:
                d["based_on_truth_rev"] = max(0, int(old["based_on_truth_rev"]))
            except (TypeError, ValueError):
                pass  # 保持缺省
            out.append(d)
            continue
        # 旧文无 stamp：保持缺省 based_on → rev>0 仍 stale
        d.pop("based_on_truth_rev", None)
        out.append(d)
    return out


def deduction_map(deds: Iterable[Any] | None) -> dict[str, dict]:
    """character_id(normalized) → 最后一条非空 prose 优先的投影。"""
    out: dict[str, dict] = {}
    for d in normalize_deductions(deds):
        cid = d["character_id"]
        if (d.get("prose") or "").strip() or cid not in out:
            out[cid] = d
    return out


def missing_roles(involved: Iterable[Any] | None,
                  deductions: Iterable[Any] | None) -> list[str]:
    """involved 中尚无非空 prose 投影的角色（normalize 后）。"""
    dmap = deduction_map(deductions)
    done = {cid for cid, d in dmap.items() if (d.get("prose") or "").strip()}
    missing: list[str] = []
    for raw in normalize_involved(involved):
        if raw not in done:
            missing.append(raw)
    return missing


def stale_roles(involved: Iterable[Any] | None,
                deductions: Iterable[Any] | None,
                current_rev: int) -> list[str]:
    """involved 中有 prose 但相对 current_rev 过期的角色。"""
    dmap = deduction_map(deductions)
    inv = normalize_involved(involved)
    stale: list[str] = []
    for cid in inv:
        d = dmap.get(cid)
        if d and is_stale_deduction(d, current_rev):
            stale.append(cid)
    return stale


def has_five_layer_headings(prose: str | None) -> bool:
    """五个 markdown 三级标题是否齐全（标题文本精确匹配）。"""
    text = prose or ""
    return all(f"### {h}" in text for h in DEDUCTION_HEADINGS)


def missing_layer_headings(prose: str | None) -> list[str]:
    text = prose or ""
    return [h for h in DEDUCTION_HEADINGS if f"### {h}" not in text]


def soft_gate_issues(ch: dict | None) -> dict[str, Any]:
    """进草稿软门诊断：missing / stale / empty_truth / weak_layers。

    不阻断写作；调用方只做提示。
    """
    ch = ch or {}
    rev = truth_revision(ch)
    truth = (ch.get("scene_truth") or "").strip()
    involved = ch.get("involved_characters") or []
    deds = ch.get("deductions") or []
    missing = missing_roles(involved, deds)
    stale = stale_roles(involved, deds, rev)
    weak: list[str] = []
    for cid, d in deduction_map(deds).items():
        prose = (d.get("prose") or "").strip()
        if prose and not has_five_layer_headings(prose):
            weak.append(cid)
    return {
        "empty_truth": not bool(truth),
        "missing": missing,
        "stale": stale,
        "weak_layers": weak,
        "truth_revision": rev,
        "needs_attention": bool(
            (not truth and bool(normalize_involved(involved)))
            or missing
            or stale
        ),
    }


def should_bump_truth_revision(old_truth: str | None, new_truth: str | None) -> bool:
    """仅当真相正文实质变化时 bump revision。"""
    return (old_truth or "").strip() != (new_truth or "").strip()


def infer_involved_candidates(
    text: str,
    characters: Iterable[Any],
    *,
    limit: int = 4,
) -> list[str]:
    """从大纲/节拍文本推断涉及角色（不落库）。

    characters 项需有 .id / .name，或为 dict。
    """
    blob = text or ""
    hits: list[str] = []
    for c in characters or []:
        if hasattr(c, "id"):
            cid, name = getattr(c, "id", None), getattr(c, "name", None)
        elif isinstance(c, dict):
            cid, name = c.get("id"), c.get("name")
        else:
            continue
        if name and str(name) in blob:
            nid = normalize_role_id(cid or name)
            if nid and nid not in hits:
                hits.append(nid)
        if len(hits) >= limit:
            break
    return hits


def extract_layer_body(prose: str | None, heading: str) -> str:
    """取 `### {heading}` 至下一 `###` 之间的正文。"""
    text = prose or ""
    mark = f"### {heading}"
    idx = text.find(mark)
    if idx < 0:
        return ""
    rest = text[idx + len(mark):]
    # 吃掉标题行尾换行
    if rest.startswith("\n"):
        rest = rest[1:]
    nxt = rest.find("\n### ")
    if nxt >= 0:
        rest = rest[:nxt]
    return rest.strip()


def unaware_leak_markers(deduction_prose: str | None, *, min_len: int = 4) -> list[str]:
    """从「没察觉的」层抽出可作泄露探针的短语（跳过留白句）。"""
    import re

    body = extract_layer_body(deduction_prose, "没察觉的")
    if not body:
        return []
    blank = "未能从场景真相确认。"
    if body.strip() == blank:
        return []
    parts = re.split(r"[。！？\n；;]+", body)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        s = (p or "").strip().lstrip("-·•* ")
        if len(s) < min_len or s == blank:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def deduction_for_role(ch: dict | None, role_id: Any) -> dict | None:
    """取某角色投影 dict；无则 None。"""
    key = normalize_role_id(role_id)
    if not key:
        return None
    return deduction_map((ch or {}).get("deductions")).get(key)


def inject_deduction_items(ch: dict | None) -> list[dict[str, Any]]:
    """草稿注入用：每条投影标注 fresh|stale，stale 默认不给全文。

    返回 [{character_id, name, prose|None, status, based_on_truth_rev?}...]
    """
    ch = ch or {}
    rev = truth_revision(ch)
    items: list[dict[str, Any]] = []
    for d in normalize_deductions((ch.get("deductions") or []), stamp_missing_rev=False):
        prose = (d.get("prose") or "").strip()
        if not prose:
            continue
        cid = d["character_id"]
        name = d.get("character_name") or cid.split(":", 1)[-1]
        stale = is_stale_deduction(d, rev)
        items.append({
            "character_id": cid,
            "name": name,
            "status": "stale" if stale else "fresh",
            "prose": None if stale else prose,
            "based_on_truth_rev": d.get("based_on_truth_rev"),
            "truth_revision": rev,
        })
    return items


def pilot_deduce_observation(
    *,
    made: int = 0,
    skipped: str | None = None,
    missing: list[str] | None = None,
    stale: list[str] | None = None,
    truth_revision: int = 0,
    scene_truth_chars: int = 0,
    deductions_count: int = 0,
    inferred_involved: list[str] | None = None,
    involved_written: bool = False,
    park: str | None = None,
) -> dict[str, Any]:
    """pilot deduce 结构化观测字段（稳定键，供日志/前端）。"""
    out: dict[str, Any] = {
        "made": made,
        "missing": list(missing or []),
        "stale": list(stale or []),
        "scene_truth_revision": truth_revision,
        "scene_truth_chars": scene_truth_chars,
        "deductions": deductions_count,
        "inferred_involved": list(inferred_involved or []),
        "involved_written": bool(involved_written),
    }
    if skipped:
        out["skipped"] = skipped
    if park:
        out["pilot_park"] = park
    return out

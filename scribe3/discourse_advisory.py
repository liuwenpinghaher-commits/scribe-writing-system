"""话语层聚合出口：soft + post-check annotate（Week-1 · 永不抛出）。"""
from __future__ import annotations

from typing import Any

from scribe3.discourse_craft_ssot import product_label, tip_text
from scribe3.discourse_detectors import (
    aggregate_breath,
    detect_hook_on_page,
    detect_hook_plan,
    detect_info_delta,
    finding,
)


def _flag(name: str, default: bool = True) -> bool:
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy(name)
    except Exception:
        import os
        raw = (os.environ.get(name) or ("1" if default else "0")).strip().lower()
        return raw in ("1", "true", "yes", "on")


def _display_severity() -> str:
    """DISCOURSE_BLOCKING 仅改展示级 severity，不进 is_blocking_issue。"""
    if _flag("SCRIBE3_DISCOURSE_BLOCKING", default=False):
        return "warning"  # 展示级；非 finalize blocking
    return "advisory"


def _soft_fail(op: str, err: BaseException) -> None:
    try:
        from scribe3.soft_fail import soft_fail
        import logging
        soft_fail(op, err, logger="scribe3.discourse", level=logging.DEBUG)
    except Exception:
        pass


def annotate_post_check_surfaces(
    post: dict[str, Any],
    *,
    prose: str = "",
) -> dict[str, Any]:
    """Finding Dedup：只 annotate 既有挂载面，不 append 同 family 新条。

    返回 annotations 列表 + 就地修改 post 中的 emotion_telling / issues / structure_style。
    """
    annotations: list[dict[str, Any]] = []
    # telling → 顶键 emotion_telling[]
    et = post.get("emotion_telling")
    if isinstance(et, list):
        for i, hit in enumerate(et):
            if not isinstance(hit, dict):
                continue
            if hit.get("product_label") or hit.get("discourse_tip"):
                continue
            hit["product_label"] = product_label("telling")
            hit["discourse_tip"] = tip_text("telling")
            annotations.append({
                "family": "telling",
                "mount": "emotion_telling",
                "hit_index": i,
            })
    # issues: god_view / rhythm / oversat
    issues = post.get("issues")
    if isinstance(issues, list):
        for i, iss in enumerate(issues):
            if not isinstance(iss, dict):
                continue
            t = str(iss.get("type") or "")
            family = None
            if t == "god_view":
                family = "god_view"
            elif t == "rhythm" or t == "rhythm_uniformity":
                family = "rhythm"
            elif "oversat" in t or t in ("oversaturation", "over_explain"):
                family = "oversat"
            if not family:
                continue
            if iss.get("product_label") or iss.get("discourse_tip"):
                continue
            iss["product_label"] = product_label(family)
            iss["discourse_tip"] = tip_text(family)
            annotations.append({
                "family": family,
                "mount": "issues",
                "issue_index": i,
            })
    # structure_style tip
    ss = post.get("structure_style")
    if isinstance(ss, dict) and ss.get("ending_formula_hit"):
        if not ss.get("discourse_tip"):
            # DET-P0-4：若钩子落地弱，用联合文案
            joint = False
            try:
                from scribe3.chapter_hooks import resolve_chapter_hook
                ch = post.get("_chapter_dict") if isinstance(post.get("_chapter_dict"), dict) else None
                hook = resolve_chapter_hook(ch) if ch else ""
                hop = detect_hook_on_page(prose, hook)
                if hop.get("emit"):
                    joint = True
            except Exception:
                pass
            if joint:
                ss["product_label"] = product_label("ending_formula")
                ss["discourse_tip"] = "公式收束≠真钩子；" + tip_text("hook_on_page")
            else:
                ss["product_label"] = product_label("ending_formula")
                ss["discourse_tip"] = tip_text("ending_formula")
            annotations.append({
                "family": "ending_formula",
                "mount": "structure_style",
            })
    return {"annotations": annotations, "annotations_applied": len(annotations)}


def run_discourse_advisory(
    prose: str | None = None,
    chapter: dict | None = None,
    *,
    near_chapters: list[dict] | None = None,
    mode: str = "soft",
    existing_post: dict | None = None,
) -> dict[str, Any]:
    """聚合出口。mode=soft 全量白话；mode=post_check_annotate 纯新增 findings + annotate。

    永不抛出；永不产生 issues[].type=discourse.*
    """
    if not _flag("SCRIBE3_DISCOURSE_ADVISORY", default=True):
        return {
            "severity": "advisory",
            "not_a_kpi": True,
            "status": "off",
            "findings": [],
            "breath": {},
            "serial": {},
            "meso": {},
            "annotations": [],
            "annotations_applied": 0,
            "enabled": False,
        }
    try:
        return _run_inner(
            prose, chapter,
            near_chapters=near_chapters,
            mode=mode,
            existing_post=existing_post,
        )
    except Exception as e:
        _soft_fail("discourse_run", e)
        return {
            "severity": _display_severity(),
            "not_a_kpi": True,
            "status": "degraded",
            "findings": [],
            "breath": {},
            "serial": {},
            "meso": {},
            "annotations": [],
            "annotations_applied": 0,
            "error": str(e)[:160],
            "enabled": True,
        }


def _run_inner(
    prose: str | None,
    chapter: dict | None,
    *,
    near_chapters: list[dict] | None,
    mode: str,
    existing_post: dict | None,
) -> dict[str, Any]:
    ch = chapter if isinstance(chapter, dict) else {}
    body = str(prose if prose is not None else (ch.get("prose") or ch.get("draft") or ""))
    has_prose = bool(body.strip())
    status = "ok" if has_prose else "no_prose"
    sev = _display_severity()
    findings: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    annotations_applied = 0

    # --- serial pure findings ---
    plan = detect_hook_plan(ch)
    hook_text = str(plan.get("hook_text") or "")
    if plan.get("emit"):
        findings.append(finding(
            "hook_plan",
            "本章还没有章末钩规划（节拍 hook / beats_meta.chapter_hook）",
            meta={"reason": plan.get("reason"), "product_label": product_label("hook_plan")},
            severity=sev,
        ))

    hop: dict[str, Any] = {"status": "skip", "emit": False, "hook_on_page_ok": None}
    if has_prose and hook_text:
        hop = detect_hook_on_page(body, hook_text)
        if hop.get("emit"):
            findings.append(finding(
                "hook_on_page",
                tip_text("hook_on_page") or "规划有钩、正文痕迹弱（启发，可误报）",
                meta={
                    "overlap": hop.get("overlap"),
                    "threshold": hop.get("threshold"),
                    "tail_n": hop.get("tail_n"),
                    "product_label": product_label("hook_on_page"),
                },
                severity=sev,
            ))

    info: dict[str, Any] = {"status": "skip", "emit": False}
    if _flag("SCRIBE3_DISCOURSE_INFO_DELTA", default=True):
        focus_syn = str(ch.get("synopsis") or ch.get("outline") or "")
        near_syn = []
        for nc in near_chapters or []:
            if isinstance(nc, dict):
                near_syn.append(str(nc.get("synopsis") or nc.get("outline") or ""))
        # no_prose 时仍可算 synopsis delta
        if focus_syn.strip():
            info = detect_info_delta(focus_syn, near_syn)
            if info.get("emit"):
                findings.append(finding(
                    "info_delta",
                    tip_text("info_delta") or "本章相对近章信息增量偏低（启发）",
                    meta={
                        "score": info.get("score"),
                        "threshold": info.get("threshold"),
                        "new_tokens_sample": info.get("new_tokens_sample"),
                        "product_label": product_label("info_delta"),
                    },
                    severity=sev,
                ))

    # stakes optional if flag（检测可做；Month 产品化）
    if _flag("SCRIBE3_DISCOURSE_STAKES", default=True) and has_prose:
        try:
            from scribe3.execution_contract import parse_stakes_presence
            syn = str(ch.get("synopsis") or "")
            sp = parse_stakes_presence(syn) if syn else {"present": False}
            if isinstance(sp, dict) and sp.get("present"):
                stakes = str(sp.get("stakes") or "").strip()
                parts = [
                    p.strip()
                    for p in re_split_parts(stakes)
                    if len(p.strip()) >= 2
                ]
                if not parts and len(stakes) >= 2:
                    parts = [stakes]
                if parts and not any(p in body for p in parts):
                    findings.append(finding(
                        "stakes_on_page",
                        tip_text("stakes_on_page"),
                        meta={"product_label": product_label("stakes_on_page")},
                        severity=sev,
                    ))
        except Exception as e:
            _soft_fail("discourse_stakes", e)

    # breath（soft 主面；post_check 也带摘要）
    god_n = 0
    if isinstance(existing_post, dict):
        for iss in existing_post.get("issues") or []:
            if isinstance(iss, dict) and iss.get("type") == "god_view":
                god_n += 1
    breath = {}
    if has_prose:
        et = None
        if isinstance(existing_post, dict) and isinstance(existing_post.get("emotion_telling"), list):
            et = existing_post["emotion_telling"]
        breath = aggregate_breath(body, emotion_hits=et, god_view_count=god_n)
    elif mode == "soft":
        breath = {"telling_count": 0, "tips": [], "tight": False, "note": "no_prose"}

    # post_check annotate
    if mode == "post_check_annotate" and isinstance(existing_post, dict):
        # 允许探测器读 chapter
        existing_post = dict(existing_post)
        existing_post["_chapter_dict"] = ch
        ann = annotate_post_check_surfaces(existing_post, prose=body)
        annotations = ann.get("annotations") or []
        annotations_applied = int(ann.get("annotations_applied") or 0)
        # 纯新增 only in findings（已装）
        # post-check soft 全量 breath tips 可保留但不进 issues

    serial = {
        "hook_plan": plan,
        "hook_on_page": hop,
        "info_delta": info,
    }
    meso = {
        "default_tip": tip_text("god_view"),
        "meso_default": __import__(
            "scribe3.discourse_craft_ssot", fromlist=["MESO_DEFAULT"]
        ).MESO_DEFAULT,
        "note": "Week-1 无 L3 注入；写前一句见 Week-2",
    }

    # post_check 模式：findings 仅纯新增（hook/info/stakes）；不含 telling 假 issues
    if mode == "post_check_annotate":
        # already only pure-new in findings
        pass

    return {
        "severity": sev,
        "not_a_kpi": True,
        "status": status,
        "findings": findings,
        "breath": breath,
        "serial": serial,
        "meso": meso,
        "annotations": annotations,
        "annotations_applied": annotations_applied,
        "enabled": True,
        "surface": "discourse.advisory",
        "week": 1,
    }


def re_split_parts(stakes: str) -> list[str]:
    import re
    return re.split(r"[，,。；;、|/\n\s]+", stakes or "")

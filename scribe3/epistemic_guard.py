"""记忆质量 D6：限知 / 认知边界守卫（质量向，非敏感词表）。

职责：
  1. 收集本章 secret 明文与 leak_markers（应用层权威）
  2. 扫描 **即将送给模型的写路径 instructions** 是否含帧外 secret 明文
  3. 讨论全知 vs 写作限知 的人格横幅文案
  4. 成稿侧可复用 find_leaks；此处偏「生成前 prompt 不泄密」

不替代 project_frame / find_leaks；是第三道：组装事故时 fail-loud 或擦除。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import logging
import re
from typing import Any

_log = logging.getLogger("scribe3")


def discussion_omniscient_banner() -> str:
    """讨论态（作者全知）横幅：可看全貌，禁止当限知章素材粘贴。"""
    return (
        "\n【认知分身·讨论态｜作者全知】"
        "你现在与作者讨论，可使用全知信息。"
        "这些内容 **不得** 被作者原样粘贴进限知章正文；"
        "若作者要求「按限知写章」，须切换到焦点者帧，帧外私密只许疑惧/误判/物象暗示，禁止直说。\n"
    )


def writing_limited_banner(focalizer: str) -> str:
    """写作限知横幅。"""
    foc = (focalizer or "").replace("role:", "") or "焦点者"
    return (
        f"\n【认知分身·写作限知｜焦点={foc}】"
        f"叙事贴 {foc} 所知所感；其知识帧外的私密 **不得出现在你的内部草稿说明里向读者泄露**，"
        "更不得写进 ⟦PROPOSAL⟧ 正文。不知则猜错、错过或误读——悬念来自认知差，不是审查词表。\n"
    )


def writing_omniscient_author_banner() -> str:
    return (
        "\n【认知分身·作者视角写作】本章未钉限知焦点；可用作者视角，"
        "但仍勿无端倪地剧透尚未建立的知识边。"
        "secret 命题仍受 secret_guard 约束，未揭示的破绽词不得明写。\n"
    )


def collect_secret_surface_strings(store, chapter: int | None) -> list[dict[str, Any]]:
    """本章有效 secret 命题的明文表面：value + leak_markers。

    返回 [{fact_id, entity_id, strings: [str], secret: True}]
    """
    out: list[dict[str, Any]] = []
    ch = int(chapter) if chapter is not None else 99999
    if not hasattr(store, "facts_at"):
        return out
    for f in store.facts_at(ch) or []:
        if not getattr(f, "secret", False):
            continue
        strings: list[str] = []
        val = (getattr(f, "value", None) or "").strip()
        if val and len(val) >= 2:
            strings.append(val)
        for m in (getattr(f, "leak_markers", None) or []):
            m = (m or "").strip()
            if m and len(m) >= 2 and m not in strings:
                strings.append(m)
        if not strings:
            continue
        out.append({
            "fact_id": getattr(f, "id", "") or "",
            "entity_id": getattr(f, "entity_id", "") or "",
            "strings": strings,
            "secret": True,
        })
    return out


def frame_known_fact_ids(store, focalizer: str, chapter: int) -> set[str]:
    if not focalizer or not hasattr(store, "facts_at"):
        return set()
    try:
        from scribe3.knowledge import project_frame
        frame = project_frame(store, focalizer, int(chapter) or 1)
        facts = getattr(frame, "facts", None) or []
        return {getattr(x, "id", "") for x in facts if getattr(x, "id", None)}
    except Exception as e:
        _log.warning("frame_known_fact_ids failed: %s", e)
        return set()


def partition_facts_for_focalizer(
    store,
    facts: list,
    *,
    focalizer: str,
    chapter: int,
) -> dict[str, list]:
    """Wave-C1：按焦点者认知切分注入事实。

    返回 {
      known: 帧内可当作「已知」写入的 fact,
      observable_only: secret/帧外 — 不得进「已知」块（仅可环境暗示，由调用方决定是否丢弃）,
      known_ids: set[str],
    }
    无 focalizer 时全部进 known（作者/全知路径）。
    """
    rows = list(facts or [])
    if not focalizer:
        return {"known": rows, "observable_only": [], "known_ids": set()}
    known_ids = frame_known_fact_ids(store, focalizer, int(chapter) or 1)
    known, obs = [], []
    for f in rows:
        fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else "") or ""
        secret = bool(
            getattr(f, "secret", None)
            if not isinstance(f, dict)
            else f.get("secret")
        )
        if secret and fid and fid not in known_ids:
            obs.append(f)
        elif secret and not known_ids:
            # 有 secret 但帧投影失败：fail-closed 进 observable
            obs.append(f)
        else:
            known.append(f)
    return {"known": known, "observable_only": obs, "known_ids": known_ids}


def discuss_epistemic_guard_enabled() -> bool:
    """GAP-9：讨论/全知出口 soft 扫描（默认开）。"""
    import os
    raw = (get_flag("SCRIBE3_EPISTEMIC_DISCUSS_GUARD") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def scan_prompt_for_any_secrets(
    prompt: str,
    store,
    *,
    chapter: int | None = None,
) -> list[dict[str, Any]]:
    """GAP-9：扫描任意出口是否含 secret 明文（不依赖 focalizer）。

    用于讨论/全知作者路径 soft 告警；不阻断。
    """
    if not (prompt or "").strip():
        return []
    ch = int(chapter) if chapter is not None else 1
    hits: list[dict[str, Any]] = []
    for row in collect_secret_surface_strings(store, ch):
        for s in row.get("strings") or []:
            if s and s in prompt:
                hits.append({
                    "fact_id": row.get("fact_id") or "",
                    "entity_id": row.get("entity_id"),
                    "marker": s[:80],
                    "off_frame": True,
                    "severity": "secret_plaintext_in_discuss_or_any_path",
                    "soft": True,
                })
    return hits


def guard_discuss_instructions(
    instructions: str,
    store,
    *,
    chapter: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """讨论路径 soft 守卫：命中则 WARNING 日志 + soft_leaked 元数据，不擦除不阻断。"""
    if not discuss_epistemic_guard_enabled():
        return instructions or "", []
    hits = scan_prompt_for_any_secrets(instructions, store, chapter=chapter)
    if hits:
        _log.warning(
            "GAP-9 discuss epistemic soft: %d secret plaintext hit(s) chapter=%s markers=%s",
            len(hits), chapter, [h.get("marker") for h in hits][:5],
        )
    return instructions or "", hits


def scan_prompt_for_off_frame_secrets(
    prompt: str,
    store,
    *,
    focalizer: str = "",
    chapter: int | None = None,
) -> list[dict[str, Any]]:
    """扫描写路径 prompt：若含 **焦点者帧外** secret 明文 → 返回命中列表。

    无 focalizer 时不做帧外 hard 裁决（作者视角限知 hard 路径）。
    讨论/全知 soft 请用 :func:`scan_prompt_for_any_secrets`。
    """
    if not (prompt or "").strip() or not focalizer:
        return []
    ch = int(chapter) if chapter is not None else 1
    known = frame_known_fact_ids(store, focalizer, ch)
    hits: list[dict[str, Any]] = []
    for row in collect_secret_surface_strings(store, ch):
        fid = row.get("fact_id") or ""
        if fid and fid in known:
            pass
        off_frame = (not fid) or (fid not in known)
        for s in row.get("strings") or []:
            if s and s in prompt:
                hits.append({
                    "fact_id": fid,
                    "entity_id": row.get("entity_id"),
                    "marker": s[:80],
                    "off_frame": off_frame,
                    "severity": "secret_plaintext_in_write_prompt",
                })
    return [h for h in hits if h.get("off_frame")]


def scrub_secrets_from_text(text: str, hits: list[dict[str, Any]]) -> str:
    """用占位符擦除命中的 secret 明文（fail-closed 兜底，避免带毒 prompt 出站）。"""
    out = text or ""
    for h in hits:
        m = h.get("marker") or ""
        if m and m in out:
            out = out.replace(m, "【帧外私密·已擦除】")
    return out


class EpistemicLeakError(RuntimeError):
    """限知出口守卫 fail-loud：帧外 secret 明文进入写 prompt。"""

    def __init__(self, message: str, hits: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.hits = list(hits or [])


def epistemic_fail_loud_enabled() -> bool:
    """SCRIBE3_EPISTEMIC_FAIL_LOUD=1 时命中帧外 secret 直接抛 EpistemicLeakError。"""
    import os
    raw = (get_flag("SCRIBE3_EPISTEMIC_FAIL_LOUD") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def guard_write_instructions(
    instructions: str,
    store,
    *,
    focalizer: str = "",
    chapter: int | None = None,
    scrub: bool = True,
    fail_loud: bool | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """写路径出口守卫。返回 (可能已擦除的 instructions, hits)。

    hits 非空时记 error；默认 scrub=True 擦除后放行。
    ``fail_loud=True`` 或 env ``SCRIBE3_EPISTEMIC_FAIL_LOUD=1`` 时改为抛
    :class:`EpistemicLeakError`（O17；默认关以免阻断 demo 写路径）。
    """
    hits = scan_prompt_for_off_frame_secrets(
        instructions, store, focalizer=focalizer, chapter=chapter,
    )
    if hits:
        _log.error(
            "D6 epistemic guard: %d off-frame secret plaintext(s) in write prompt "
            "focalizer=%s chapter=%s markers=%s",
            len(hits), focalizer, chapter,
            [h.get("marker") for h in hits][:5],
        )
        loud = epistemic_fail_loud_enabled() if fail_loud is None else bool(fail_loud)
        if loud:
            raise EpistemicLeakError(
                f"epistemic leak: {len(hits)} off-frame secret(s) in write prompt "
                f"focalizer={focalizer!r} chapter={chapter}",
                hits=hits,
            )
        if scrub:
            instructions = scrub_secrets_from_text(instructions, hits)
            instructions += (
                "\n\n【系统限知守卫】检测到内部上下文曾含焦点者不应直见的私密明文，"
                "已擦除。正文中禁止还原这些私密；仅允许疑惧、误判或物象暗示。\n"
            )
    return instructions, hits

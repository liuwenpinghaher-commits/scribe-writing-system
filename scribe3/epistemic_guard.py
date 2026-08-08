"""记忆质量 D6：限知 / 认知边界守卫（质量向，非敏感词表）。

职责：
  1. 收集本章 secret 明文与 leak_markers（应用层权威）
  2. 扫描 **即将送给模型的写路径 instructions** 是否含帧外 secret 明文
  3. 讨论全知 vs 写作限知 的人格横幅文案
  4. 成稿侧可复用 find_leaks；此处偏「生成前 prompt 不泄密」

不替代 project_frame / find_leaks；是第三道：组装事故时 fail-loud 或擦除。
"""
from __future__ import annotations

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
        "但仍勿无端倪地剧透尚未建立的知识边。\n"
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


def scan_prompt_for_off_frame_secrets(
    prompt: str,
    store,
    *,
    focalizer: str = "",
    chapter: int | None = None,
) -> list[dict[str, Any]]:
    """扫描写路径 prompt：若含 **焦点者帧外** secret 明文 → 返回命中列表。

    无 focalizer 时不做帧外裁决（作者视角）；仍可扫描但默认不报（避免讨论全知误报）。
    质量事故 = 限知写路径 instructions 里出现帧外 secret 真值。
    """
    if not (prompt or "").strip() or not focalizer:
        return []
    ch = int(chapter) if chapter is not None else 1
    known = frame_known_fact_ids(store, focalizer, ch)
    hits: list[dict[str, Any]] = []
    for row in collect_secret_surface_strings(store, ch):
        fid = row.get("fact_id") or ""
        if fid and fid in known:
            # 焦点者知道：value 仍可能被渲染层屏蔽；若 prompt 出现明文，属渲染 bug，仍报
            # 但优先级低于帧外
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
    # 只把帧外命中当硬事故；帧内明文另计 soft
    return [h for h in hits if h.get("off_frame")]


def scrub_secrets_from_text(text: str, hits: list[dict[str, Any]]) -> str:
    """用占位符擦除命中的 secret 明文（fail-closed 兜底，避免带毒 prompt 出站）。"""
    out = text or ""
    for h in hits:
        m = h.get("marker") or ""
        if m and m in out:
            out = out.replace(m, "【帧外私密·已擦除】")
    return out


def guard_write_instructions(
    instructions: str,
    store,
    *,
    focalizer: str = "",
    chapter: int | None = None,
    scrub: bool = True,
) -> tuple[str, list[dict[str, Any]]]:
    """写路径出口守卫。返回 (可能已擦除的 instructions, hits)。

    hits 非空时记 warning；scrub=True 时擦除后放行（不静默吞事故：调用方可读 hits）。
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
        if scrub:
            instructions = scrub_secrets_from_text(instructions, hits)
            instructions += (
                "\n\n【系统限知守卫】检测到内部上下文曾含焦点者不应直见的私密明文，"
                "已擦除。正文中禁止还原这些私密；仅允许疑惧、误判或物象暗示。\n"
            )
    return instructions, hits

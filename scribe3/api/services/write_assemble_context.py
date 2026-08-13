"""Write-assemble context blocks (outline/drama/brief/…); re-exported by write_assemble."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from functools import wraps
from typing import Any, Optional

from scribe3.api.services.write_assemble_blocks import (  # noqa: F401
    _faction_prompt_block,
    _codex_block,
    _editor_system,
    _editor_identity_block,
    _write_protocol_block,
    _write_revision_block,
    inject_floor_env_enabled,
    _anti_slop_floor_block,
    provenance_in_prompt_enabled,
    generation_forbidden_source_kinds,
)

def _editor_write_system(st, focalizer: str = "", chapter: int = None) -> str:
    # 旧路径字节一致:_editor_system(身份+设定数据) + _write_protocol_block(静态硬协议/文风)
    # U-003:这是唯一的"生成"入口——限知章续写(_stream_write/_collect_write 最终都靠
    # 本函数组装 instructions)。for_generation=True 是本函数存在的意义,别的调用点
    # (chat_stream/chat_agentic_stream,作者/主编纯讨论)都不该传它,吃 _editor_system
    # 的默认值 False 即可。
    base = (_editor_system(st, focalizer=focalizer, chapter=chapter, for_generation=True)
            + _write_protocol_block() + _secret_guard_block(st, chapter))
    # Task7:章前简报注入(chapter 已知才组装;fail-safe——组装异常只 warning 不阻断写作)
    brief_txt = ""
    if chapter is not None:
        try:
            from scribe3.brief import assemble_chapter_brief
            _brief = assemble_chapter_brief(st, chapter, focalizer=focalizer)
            sec = _brief.get("sections") or {}
            _pd = sec.get("promises") or {}
            # 空简报判 sections 各桶(text 恒含标题行,不能判 text)
            if (sec.get("arcs") or _pd.get("reminders") or _pd.get("directives")
                    or _pd.get("decisions") or (sec.get("loops") or {}).get("weighted")
                    or sec.get("heartbeat")):
                brief_txt = _brief.get("text") or ""
        except Exception as _bf_e:
            import logging
            logging.getLogger("scribe3").warning("章前简报组装失败(non-fatal): %s", _bf_e)
    # Task7:M8 修订纪律(恒注入,与是否有简报无关) + 内核3 反平庸下限
    revision = _write_revision_block() + _anti_slop_floor_block()
    return base + revision + (("\n\n" + brief_txt) if brief_txt else "")


def _voice_anchor_block(st, focalizer: str = "") -> str:
    """构建声音锚注入块:焦点者完整 voice_profile(含3节死字段) + 所有角色对白声音速记。
    用于 /chat/write 的 instructions 末尾,让生成时已在声而非事后 check_ooc。"""
    parts = []

    # 焦点者声音锚(叙述/内心独白贴这个声音)
    if focalizer:
        vp = st.get_voice_profile(focalizer)
        if vp and vp.get("style_summary"):
            line = (f"\n\n## 本章焦点者声音锚\n"
                    f"叙述与内心独白贴「{focalizer}」的声音:{vp['style_summary']}")
            cp = vp.get("catchphrases")
            if cp and isinstance(cp, list):
                line += f" 口头禅:{'、'.join(str(x) for x in cp if x)}。"
            tr = vp.get("tone_rules")
            if tr and isinstance(tr, list):
                line += f" 语气规则:{'；'.join(str(x) for x in tr if x)}。"
            # P3-d: 注入3个此前未用的声音节点
            im = vp.get("internal_monologue_style")
            if im:
                line += f" 内心独白风格:{im}。"
            sp = vp.get("sentence_patterns")
            if sp and isinstance(sp, dict):
                sp_str = "、".join(f"{k}={v}" for k, v in sp.items() if v)
                if sp_str:
                    line += f" 句式:{sp_str}。"
            voc = vp.get("vocabulary_profile")
            if voc and isinstance(voc, dict):
                voc_str = "、".join(str(v) for v in voc.values() if v)
                if voc_str:
                    line += f" 词汇倾向:{voc_str}。"
            rl = vp.get("reference_lines")
            # P3-e1 Fix 2: reference_lines schema 是 object 但消费时须兼容 dict/list 两种形状
            if rl:
                if isinstance(rl, dict):
                    rl_items = list(rl.values())[:2]
                elif isinstance(rl, list):
                    rl_items = rl[:2]
                else:
                    rl_items = []
                if rl_items:
                    line += f" 参考语感:{'｜'.join(str(x) for x in rl_items if x)}"
            # 声音待演变提示:该角色有 open voice_evolution_flag 时附加
            try:
                flags = st.list_voice_flags("open") or []
                focal_flags = [f for f in flags if f.get("character") == focalizer]
                if focal_flags:
                    reasons = "、".join(
                        str(f.get("reason") or f.get("trigger_chapter") or "")
                        for f in focal_flags if f.get("reason") or f.get("trigger_chapter")
                    )
                    if reasons:
                        line += (f"\n\n## 声音待演变提示\n"
                                 f"{focalizer} 因下列情节声音正在转变,行文可体现这种变化:{reasons}")
            except Exception as _sf_e:
                from scribe3.soft_fail import soft_fail
                import logging as _sf_logging
                soft_fail('write_assemble_context_soft_1', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
            parts.append(line)

    # 对白声音速记——所有有 profile 的角色,各自对白在声,别串味
    profiles = st.list_voice_profiles() or []
    digests = []
    for p in profiles[:6]:
        cid = p.get("character_id") or ""
        ss = (p.get("style_summary") or "").strip()
        if cid and ss:
            digests.append(f"{cid}—{ss[:30]}")
    if digests:
        parts.append("\n\n## 登场角色对白声音(各自在声,别串味)\n" + "；".join(digests))

    return "".join(parts)


_VOLUME_INTRO_BUDGET = 400  # 卷纲摘要注入字符上限


def _clip_chars(text: str, n: int) -> str:
    """本模块可单测的截断（不依赖 app_impl 重绑的 ``_clip``）。"""
    s = str(text or "")
    try:
        lim = int(n)
    except (TypeError, ValueError):
        lim = 0
    if lim <= 0:
        return ""
    return s if len(s) <= lim else s[:lim]


def _volume_intro_inject_enabled() -> bool:
    """SCRIBE3_VOLUME_INTRO_INJECT 默认开；显式 0/false/no/off 关闭。"""
    v = (os.environ.get("SCRIBE3_VOLUME_INTRO_INJECT") or "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def _outline_block(st, chapter: int, focalizer: str = "", *, mode: str = "write") -> str:
    """本章大纲(synopsis)+节拍(beats)契约注入。

    mode:
      - ``write`` (draft/final 写栈默认): 〔大纲〕/〔节拍〕clip + 有 beats 时笔墨句
        + 限知免责。**不含**「生成/调整大纲或节拍」协议三尾段。
      - ``plan`` (outline/beats 讨论): write 内容 + 情节点字数预算契约 + 章节定位
        + 反转标注规范(reversal_type 等)。

    空(无 synopsis 且无 beats)→ 空串。限知章(focalizer 非空)附作者视角免责。
    历史: 早期生产写栈未挂接本函数,仅 focus [:220] 旁路;现由
    ``_assemble_write_instructions_v1`` domain fail-soft 挂 write 模式。
    自带前导 \\n\\n(与 _motif_block/_recap_block 同约定,caller 直接 += 即可)。
    PR-4:戏剧 GCD 执行块见 ``_drama_block``(置顶,先于记忆);本块仍拼 synopsis/text。
    """
    if chapter is None:
        return ""
    try:
        ch = st.get_chapter(chapter) or {}
    except Exception:
        raise   # U-011: fail-loud(_outline_block 大纲/节拍)
    synopsis = (ch.get("synopsis") or "").strip()
    beat_texts = []
    for b in ch.get("beats") or []:
        t = ((b.get("text") if isinstance(b, dict) else str(b)) or "").strip()
        if t:
            beat_texts.append(t)
    if not synopsis and not beat_texts:
        return ""
    parts = ["## 本章大纲/节拍(据此展开正文,勿另起炉灶)"]
    if synopsis:
        parts.append("〔大纲〕" + _clip(synopsis, _OUTLINE_BUDGET))
    if beat_texts:
        parts.append("〔节拍〕" + _clip(" ".join(f"{i}.{t}" for i, t in enumerate(beat_texts, 1)),
                                       _OUTLINE_BUDGET))
        parts.append("写作要求:严格按各情节点字数预算分配笔墨,预算内欠账的密点优先补足,不得均匀注水。")
    if focalizer:
        parts.append("(以上为作者视角大纲,写限知视角时只呈现焦点者可感知的部分;"
                     "帧外私密留作伏笔,不得由焦点者知晓或道破。)")
    plan_mode = (mode or "write").strip().lower() == "plan"
    if plan_mode:
        parts.append(
            "情节点字数预算契约:生成/调整节拍时,每个情节点须标注「密度:密|疏」与"
            "「字数预算:N字」(密≥250字,慢镜头爽点400-600字,疏≈40字过场);"
            "全部情节点预算求和必须落在[章目标字数, ×1.1]区间;"
            "节拍列表末尾输出一行「预算合计:X字」。"
        )
        # 方案B任务11:章节定位六型 + 卷级张弛基线
        parts.append(
            "章节定位标注:生成/调整大纲或节拍时,每章须标注「压力级:1-5」与"
            "「chapter_role:高压|推进|修炼|关系回收|低压|信息整理」;"
            "低压/关系回收章允许无显性爽点,但须保留追读拉力(未解悬念或未了结的关系张力仍须推进);"
            "均衡基线非硬配额,严肃志怪基调整体取克制档,但同一 chapter_role 不得连排超过 2-3 章。"
        )
        # 方案B任务13b:反转标注规范
        parts.append(
            "反转标注规范:若本章含反转,节拍须标注「reversal_type:七类之一(身份反转/"
            "动机反转/因果反转/立场反转/信息差反转/时间线反转/道德反转)」+「setup_clues」"
            "(≥3 处铺垫,须引用前文对应片段)+「reveal_position_pct」(建议落在 50-85 区间)。"
        )
    return "\n\n" + "\n".join(parts)


def _volume_intro_block(st, chapter: int, focalizer: str = "") -> str:
    """当前卷 intro 摘要注入写路径(作者备忘;不经 epistemic SQL 门)。

    无卷 / 空 intro / flag 关 → 空串。clip ≤ _VOLUME_INTRO_BUDGET。fail-soft。
    """
    if chapter is None or not _volume_intro_inject_enabled():
        return ""
    try:
        ch = st.get_chapter(chapter) or {}
        vid = ch.get("volume")
        if vid in (None, ""):
            return ""
        intro = ""
        for v in (st.list_volumes() or []):
            if str(v.get("id")) == str(vid):
                intro = (v.get("intro") or "").strip()
                break
        if not intro:
            # 有 volume 归属但 intro 空 → 不注入（S2 / R-Vol-5）
            return ""
        # 预算常量与 clip 必须同值（KD-VOL-4）；用本模块 _clip_chars 可纯测
        body = _clip_chars(intro, _VOLUME_INTRO_BUDGET)
        parts = [
            "## 本卷卷纲摘要(作者备忘·氛围与卷级冲突;不得覆盖本章大纲/场景真相)",
            body,
        ]
        if focalizer:
            parts.append(
                "(以上为作者卷纲备忘,写限知视角时只呈现焦点者可感知的部分;"
                "帧外私密留作伏笔,不得由焦点者知晓或道破。)"
            )
        return "\n\n" + "\n".join(parts)
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 volume_intro 注入失败(fail-soft): %s", e)
        return ""

def _event_drive_block(st, chapter: int, focalizer: str = "") -> str:
    """叙事引擎：本章冲突/事件驱动引导块（≤220 字），置顶于 ``_drama_block`` 前。

    ``SCRIBE3_NARRATIVE_ENGINE=1`` 且章上有实质 drive 字段时注入；
    引导优先：强调冲突/事件推动，允许服务戏的跟主角。fail-soft。
    """
    if chapter is None:
        return ""
    try:
        from scribe3.novel_quality_flags import narrative_engine_enabled
        if not narrative_engine_enabled():
            return ""
    except Exception:
        return ""
    try:
        ch = st.get_chapter(int(chapter)) or {}
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 _event_drive_block 读章失败(fail-soft): %s", e)
        return ""
    drive = ch.get("narrative_drive") or {}
    if not isinstance(drive, dict) or not drive:
        return ""
    try:
        from scribe3.narrative_contract import contract_has_scene_fields
        if contract_has_scene_fields(ch.get("narrative_contract")):
            from scribe3.narrative_drive import format_event_drive_hook_only
            return format_event_drive_hook_only(drive) or ""
        from scribe3.narrative_drive import format_event_drive_block
        return format_event_drive_block(
            drive, focalizer=focalizer or "",
        ) or ""
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 _event_drive_block 格式化失败(fail-soft): %s", e)
        return ""


def _drama_block(st, chapter: int, focalizer: str = "") -> str:
    """PR-4：本章戏剧合同（GCD 压缩 + MRU 三行，≤400 字）。

    置顶注入点：``_assemble_write_instructions_v1`` 在 envelope（重记忆）之前。
    无 GCD/钩子 → 空串。限知免责与 ``_outline_block`` 同口径（Issue 14）。
    章末钩子经 ``chapter_hooks.resolve_chapter_hook`` SSOT（与 ensure 同源）。
    fail-soft：取数异常只 warning，不阻断写作。
    """
    if chapter is None:
        return ""
    try:
        ch = st.get_chapter(int(chapter)) or {}
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 _drama_block 读章失败(fail-soft): %s", e)
        return ""
    beats = ch.get("beats") or []
    try:
        from scribe3.chapter_hooks import resolve_chapter_hook
        hook = resolve_chapter_hook(ch)
    except Exception:
        hook = ""
        meta = ch.get("beats_meta") or {}
        if isinstance(meta, dict):
            hook = str(meta.get("chapter_hook") or "").strip()
        if not hook:
            for b in reversed(list(beats)):
                if isinstance(b, dict) and str(b.get("hook") or "").strip():
                    hook = str(b.get("hook") or "").strip()
                    break
    try:
        from scribe3.drama_beats import format_drama_block
        return format_drama_block(
            beats, chapter_hook=hook, focalizer=focalizer or "",
        ) or ""
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 _drama_block 格式化失败(fail-soft): %s", e)
        return ""


FOCAL_DEDUCTION_PROSE_CAP = 1800  # 焦点者五层单条字帽（整包另有 DEFAULT_CODEX_INJECT_CAP）


def _deduction_item_is_focal(item: dict, focalizer: str) -> bool:
    """焦点者命中：character_id / 显示名与 focalizer 的 role 键有交集。"""
    from scribe3.deduce_helpers import role_id_keys

    if not str(focalizer or "").strip():
        return False
    keys = role_id_keys(focalizer)
    if not keys:
        return False
    cid = item.get("character_id") or ""
    name = item.get("name") or ""
    return bool(keys & (role_id_keys(cid) | role_id_keys(name)))


def _nonfocal_boundary_line(name: str, prose: str) -> str:
    """非焦点一行边界（可见/已做）；禁止注入其「没察觉的」长文。"""
    from scribe3.deduce_helpers import extract_layer_body

    seen = (extract_layer_body(prose, "看到/听到") or "").replace("\n", " ").strip()
    known = (extract_layer_body(prose, "知道") or "").replace("\n", " ").strip()
    did = (extract_layer_body(prose, "做了/说了") or "").replace("\n", " ").strip()
    vis = "；".join(part for part in (seen, known) if part)
    if not vis and not did:
        unaware = extract_layer_body(prose, "没察觉的") or ""
        leftover = prose or ""
        if unaware:
            leftover = leftover.replace(unaware, "")
        leftover = leftover.replace("### 没察觉的", "")
        vis = leftover.replace("\n", " ").strip()
    vis = _clip_chars(vis, 80)
    did = _clip_chars(did, 60)
    bits: list[str] = []
    if vis:
        bits.append(f"可见:{vis}")
    if did:
        bits.append(f"已做:{did}")
    body = "；".join(bits) if bits else "言行以场面可见为准"
    return f"\n〔{name}·限知边界〕{body}。勿写其不知之事。"


def _apply_deduction_pack_cap(parts: list[dict], cap: int) -> None:
    """整包硬帽。超帽顺序：砍非焦点行 → 真相摘录 → 焦点半裁。原地改 parts。"""

    def total() -> int:
        return sum(len(p.get("text") or "") for p in parts)

    while total() > cap:
        drop_at = next(
            (i for i in range(len(parts) - 1, -1, -1) if parts[i].get("role") == "nonfocal"),
            None,
        )
        if drop_at is None:
            break
        parts.pop(drop_at)

    if total() > cap:
        for p in parts:
            if p.get("role") != "truth":
                continue
            room = max(0, cap - (total() - len(p.get("text") or "")))
            p["text"] = _clip_chars(p.get("text") or "", room)
            break

    while total() > cap:
        focals = [p for p in parts if p.get("role") == "focal" and len(p.get("text") or "") > 1]
        if not focals:
            break
        victim = max(focals, key=lambda p: len(p.get("text") or ""))
        text = victim.get("text") or ""
        victim["text"] = text[: max(1, len(text) // 2)]

    if total() > cap:
        for p in reversed(parts):
            if p.get("role") in ("header", "footer"):
                continue
            room = max(0, cap - (total() - len(p.get("text") or "")))
            p["text"] = _clip_chars(p.get("text") or "", room)
            if total() <= cap:
                break


def _deduction_context_segments(
    st, seq: int, *, focalizer: str = "",
) -> list[tuple[str, str, str]]:
    """把场景真相、每条限知投影与固定协议分开，供 Manifest 逐源追溯。

    stale 投影默认**不注入全文**（只标过期提示），避免草稿采信旧限知。
    焦点者 fresh 保留五层（单条 ≤ FOCAL_DEDUCTION_PROSE_CAP）；其余 fresh 只给
    一行可见/已做边界，禁止其「没察觉的」。整包对齐 DEFAULT_CODEX_INJECT_CAP。
    """
    from scribe3.context_budget import DEFAULT_CODEX_INJECT_CAP
    from scribe3.deduce_helpers import inject_deduction_items

    ch = st.get_chapter(seq) or {}
    truth = (ch.get("scene_truth") or "").strip()
    items = inject_deduction_items(ch)
    if not truth and not items:
        return []
    parts: list[dict] = [{
        "source_id": "protocol:scribe3-deduction-context:v1:header",
        "source_kind": "deduction_protocol",
        "role": "header",
        "text": "\n\n## 本章演绎(据此以作者视角写限知初稿)",
    }]
    if truth:
        parts.append({
            "source_id": f"chapter:{seq}:scene-truth",
            "source_kind": "scene_truth",
            "role": "truth",
            "text": f"\n〔场景真相·全知〕{truth}",
        })
    for ordinal, item in enumerate(items):
        identity = item.get("character_id") or "unknown"
        name = item.get("name") or identity
        if item.get("status") == "stale":
            based = item.get("based_on_truth_rev")
            cur = item.get("truth_revision")
            parts.append({
                "source_id": f"chapter:{seq}:deduction:{ordinal:04d}:{identity}:stale",
                "source_kind": "deduction_stale",
                "role": "stale",
                "text": (
                    f"\n〔{name}·限知投影·过期〕基于真相 rev {based}，当前 rev {cur}；"
                    f"请重演后再采信。正文勿将该角色旧限知当有效边界。"
                ),
            })
            continue
        prose = (item.get("prose") or "").strip()
        if not prose:
            continue
        if _deduction_item_is_focal(item, focalizer):
            clipped = _clip_chars(prose, FOCAL_DEDUCTION_PROSE_CAP)
            parts.append({
                "source_id": f"chapter:{seq}:deduction:{ordinal:04d}:{identity}",
                "source_kind": "deduction",
                "role": "focal",
                "text": f"\n〔{name}·限知投影〕{clipped}",
            })
        else:
            parts.append({
                "source_id": f"chapter:{seq}:deduction:{ordinal:04d}:{identity}",
                "source_kind": "deduction",
                "role": "nonfocal",
                "text": _nonfocal_boundary_line(str(name), prose),
            })
    parts.append({
        "source_id": "protocol:scribe3-deduction-context:v1:footer",
        "source_kind": "deduction_protocol",
        "role": "footer",
        "text": (
            "\n要求:以场景真相为事实骨架;焦点者**未过期**投影当 POV、他人投影约束其言行并埋反讽;"
            "过期投影仅提示勿采信;不写角色不知道的私密。"
        ),
    })
    _apply_deduction_pack_cap(parts, DEFAULT_CODEX_INJECT_CAP)
    return [
        (str(p["source_id"]), str(p["source_kind"]), str(p.get("text") or ""))
        for p in parts
        if p.get("text")
    ]


def _purpose_and_lessons_write_block(st, chapter: int, with_tools: bool = False,
                                    work: str | None = None) -> str:
    """生产写 prompt 注入:目的合同清单(真数据) + 教训召回(真数据)。
    不再谎称「见简报必达清单」——v1 写路径不走章前简报,清单必须内联。"""
    parts: list[str] = []
    try:
        from scribe3.purpose import parse_deltas, render_purpose_section
        cur = parse_deltas((st.get_chapter(chapter) or {}).get("deltas"))
        prev_ch = chapter - 1 if chapter and chapter > 1 else None
        prev = parse_deltas((st.get_chapter(prev_ch) or {}).get("deltas")) if prev_ch else []
        cur_keys = {(d.get("kind"), d.get("predicate")) for d in cur}
        pu = render_purpose_section(
            cur,
            [d for d in prev if d.get("status") == "carried"
             and (d.get("kind"), d.get("predicate")) not in cur_keys],
        )
        if pu.get("text"):
            parts.append("\n\n" + pu["text"])
        elif not cur:
            w = _normalize_work(work)
            register_hint = (
                f"有 s3_register_purpose 工具就调用它走待批登记;调用时必须传 work=\"{w}\"。"
                if with_tools else "请作者在章面板登记(本对话未挂联查工具)。")
            parts.append(
                "\n\n【目的合同工序】本章尚未登记目的合同:与作者聊定本章目的后,可列 "
                "delta 草单(≤7 条)。" + register_hint + "空合同也可正常写作。")
    except Exception:
        raise
    try:
        from scribe3.lesson import render_lessons_section
        max_ch = max(0, int(chapter) - 1)
        last_ls = (st.list_lessons(chapter=max_ch) if max_ch else [])[-3:]
        ch_meta = st.get_chapter(chapter) or {}
        qtxt = " ".join(filter(None, [
            (ch_meta.get("synopsis") or "").strip(),
            " ".join(
                ((b.get("text") if isinstance(b, dict) else str(b)) or "")
                for b in (ch_meta.get("beats") or [])),
        ])).strip()
        recalled = st.recall_lessons(qtxt, k=3) if qtxt else []
        seen = {l.get("id") for l in last_ls}
        recalled = [r for r in recalled if r.get("id") not in seen]
        ls = render_lessons_section(last_ls, recalled)
        if ls.get("text"):
            parts.append("\n\n" + ls["text"])
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 lessons 注入失败(fail-soft): %s", e)
    return "".join(parts)


def _pressure_drive_write_block(st, chapter: int) -> str:
    """PDC 注入块：SCRIBE3_PDC=1 且章有 pressure_drive 时渲染 ≤400 字力学钉。

    插入点：brief_must 后、author_prefs 前。不经 _outline_block。
    flag 关 / 无合同 / 校验 ok=None → 空串（字节级无新增）。
    """
    try:
        from scribe3.pressure_drive import (
            load_pdc,
            pdc_flag_enabled,
            render_pressure_drive_block,
            validate_pdc,
        )
        if not pdc_flag_enabled():
            return ""
        ch = None
        try:
            ch = st.get_chapter(int(chapter)) if chapter is not None else None
        except Exception:
            ch = None
        contract = load_pdc(ch) if ch else None
        if not contract:
            return ""
        v = validate_pdc(contract)
        if v.get("ok") is False:
            # 结构非法：仍注入短警告钉，避免静默当无合同
            errs = "；".join((v.get("errors") or [])[:2])
            warn = f"## 压力驱动合同\n- 合同结构待修：{errs}"
            return warn[:400]
        if v.get("ok") is None:
            return ""
        return render_pressure_drive_block(contract) or ""
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 pressure_drive 注入失败(fail-soft): %s", e)
        return ""


def _brief_must_sections_write_block(
    st, chapter: int, focalizer: str = "",
    *, must_link_already_pinned: bool | None = None,
) -> str:
    """生产写路径:章前简报**操作必达段**(伏笔/开环/心跳/弧光/因果/stale)。

    单源 assemble_chapter_brief;刻意剔除 purpose/lessons(已由
    _purpose_and_lessons_write_block 内联)与 injection 回显(codex 块另注),
    避免双份圣经/双份目的合同。空操作段 → 空串。fail-soft:组装故障不阻断写作。

    D3 / IA：前置「戏剧必需锚」与 context_assembler must_link 同源；
    默认信封 pin 已占全文时（``must_link_already_pinned`` / 注入去重开）brief 短路。
    """
    must_prefix = ""
    try:
        from scribe3.memory_must_link import build_must_prefix, inject_dedup_enabled
        # 生产写路径 envelope 恒会 _pin_must_link；DEDUP 开则 brief 不再出全文。
        pinned = must_link_already_pinned
        if pinned is None:
            pinned = inject_dedup_enabled()
        must_prefix = build_must_prefix(
            st, int(chapter), focalizer=focalizer or "",
            must_link_already_pinned=bool(pinned),
        )
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 must_link 注入失败(fail-soft): %s", e)
    try:
        from scribe3.brief import assemble_chapter_brief, render_brief
        brief = assemble_chapter_brief(st, int(chapter), focalizer=focalizer or "")
        sec = dict(brief.get("sections") or {})
        sec.pop("purpose", None)
        sec.pop("lessons", None)
        sec.pop("injection", None)
        # 戏剧合同已在 envelope 前由 _drama_block 置顶注入；此处去重避免双份稀释。
        sec.pop("drama_contract", None)
        pd = sec.get("promises") or {}
        has_ops = bool(
            sec.get("arcs")
            or pd.get("reminders") or pd.get("directives") or pd.get("decisions")
            or (sec.get("loops") or {}).get("weighted")
            or sec.get("heartbeat")
            or (sec.get("causal") or {}).get("directives")
            or (sec.get("stale") or {}).get("text")
            or (sec.get("emotion_module") or {}).get("text")
        )
        if not has_ops:
            return must_prefix
        text = (render_brief(sec) or "").strip()
        if not text or text == "## 本章创作简报(章前组装,遵守但不复述)":
            return must_prefix
        return must_prefix + "\n\n" + text
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 brief 必达段注入失败(fail-soft): %s", e)
        return must_prefix


def _material_recall_block(st, chapter: int, phase: str, focalizer: str = "", llm=None,
                           request_text: str = "") -> str:
    """写作总闸素材注入:聚焦 query → material_recall → 重排 → 参考段 + 溯源。

    llm 参数:
      - 显式传入可调用对象 → LLM 重排理由(测试/显式调用);
      - 默认 None → **确定性**路径(强度加权 top-k,不调网关),供生产写组装零网络阻塞。
    门控:无草料/空库/无命中 → 空串。参考语义:借鉴非事实。全 try/except fail-soft。"""
    try:
        from scribe3.brief import chapter_draft_text, detect_mentions
        from scribe3.material_recall import (apply_strength, extract_focus_query, gate,
                                             render_material_block, rerank_materials)
        # 已落库章草料是长期锚点；作者本轮请求则是当前意图信号。
        # 后者只参与检索 query，不作为任何故事事实或设定写入正文上下文。
        chapter_text = chapter_draft_text(st.get_chapter(chapter) or {})
        draft = "\n".join(part for part in (chapter_text, (request_text or "").strip()) if part)
        if not (draft or "").strip():
            return ""
        entities = [{"id": e.id, "name": e.name,
                     "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                    for e in st.all_entities()]
        mentioned = detect_mentions(draft, entities)
        query = extract_focus_query({"beats": [draft[:200]], "mentioned": list(mentioned)})
        if not query:
            return ""
        raw = st.material_recall(query, chapter, k=5, mentioned_entities=mentioned)
        cands = gate(raw, budget_chars=800)
        if not cands:
            return ""   # 门控:空库/无命中/预算裁空 → 不调 LLM 重排
        if llm is None:
            ranked = apply_strength(list(cands))[:3]
            for c in ranked:
                c.setdefault("reason", "检索命中")
        else:
            ranked = rerank_materials(cands, query, llm, k=3)
        block = render_material_block(ranked, budget_chars=800)
        if block:
            for c in ranked:   # 溯源反哺(recall_count++/last_recalled_at)
                try:
                    st.add_material_reference(
                        c["material_id"], chapter,
                        dimension=(c.get("ref_tags") or [None])[0],
                        reason=c.get("reason"), via=f"phase:{phase}")
                except Exception as _sf_e:
                    from scribe3.soft_fail import soft_fail
                    import logging as _sf_logging
                    soft_fail('write_assemble_context_soft_2', _sf_e, logger='scribe3.write_assemble', level=_sf_logging.DEBUG)
        return "\n\n" + block if block else ""
    except Exception:
        logging.getLogger("scribe3").debug("素材召回块失败(不阻断写作)", exc_info=True)
        return ""


def _record_story_soft_fail(kind: str) -> None:
    try:
        from scribe3.api.services.write_assemble import record_write_soft_fail
        record_write_soft_fail(kind)
    except Exception:
        pass


def _query_from_contract_and_synopsis(st, chapter: int) -> str:
    """召回 query：合同 turn/desire + 大纲首句，截 200。"""
    try:
        ch = st.get_chapter(int(chapter)) or {}
    except Exception:
        return ""
    nc = ch.get("narrative_contract") if isinstance(ch.get("narrative_contract"), dict) else {}
    bits = [
        str(nc.get("turn") or "").strip(),
        str(nc.get("desire") or "").strip(),
        str(ch.get("synopsis") or "").strip().splitlines()[0] if ch.get("synopsis") else "",
    ]
    q = " ".join(b for b in bits if b)
    return q[:200]


def _hybrid_recall_for_write(st, chapter: int) -> str:
    """限知写作用世界此刻。secret 恒掩码。失败记 empty_story_recall。"""
    try:
        q = _query_from_contract_and_synopsis(st, chapter)
        if not q or not hasattr(st, "hybrid_recall"):
            return ""
        facts = st.hybrid_recall(q, int(chapter), k=5)
    except Exception:
        _record_story_soft_fail("empty_story_recall")
        return ""
    lines: list[str] = []
    for f in facts or []:
        if isinstance(f, dict):
            ent = str(f.get("entity") or f.get("entity_id") or "")
            attr = str(f.get("attribute") or "")
            val = str(f.get("value") or "")
            secret = bool(f.get("secret") or f.get("is_secret"))
        else:
            ent = str(getattr(f, "entity_id", "") or "")
            attr = str(getattr(f, "attribute", "") or "")
            val = str(getattr(f, "value", "") or "")
            secret = bool(getattr(f, "secret", False))
        if secret:
            val = "🔒 私密"
        label = ".".join(x for x in (ent, attr) if x) or "事实"
        lines.append(f"- {label}：{val}")
        if len(lines) >= 8:
            break
    return "\n".join(lines)


def _event_id_local(ev) -> str:
    if ev is None:
        return ""
    if isinstance(ev, dict):
        raw = str(ev.get("id") or ev.get("event_id") or "")
    else:
        raw = str(getattr(ev, "id", "") or "")
    if raw.startswith("ev:"):
        raw = raw.split(":", 1)[-1]
    return raw.strip()


def _causal_chain_for_write(st, chapter: int) -> str:
    """本章/上章事件的回溯链。查询失败记 empty_story_causal（与「无链」区分）。"""
    try:
        events: list = []
        if hasattr(st, "events_at"):
            if int(chapter) > 1:
                events.extend(list(st.events_at(int(chapter) - 1) or []))
            events.extend(list(st.events_at(int(chapter)) or []))
        seeds = [e for e in events if _event_id_local(e)][:3]
        if not seeds or not hasattr(st, "causal_chain"):
            return ""
        lines: list[str] = []
        seen: set[str] = set()
        for ev in seeds:
            eid = _event_id_local(ev)
            chain = st.causal_chain(eid, direction="backward", max_depth=3) or []
            for node in chain:
                if isinstance(node, dict):
                    nid = str(node.get("id") or "")
                    title = str(node.get("title") or "").strip()
                    seq = node.get("seq")
                else:
                    nid = str(getattr(node, "id", "") or "")
                    title = str(getattr(node, "title", "") or "").strip()
                    seq = getattr(node, "seq", None)
                key = nid or title
                if not key or key in seen:
                    continue
                seen.add(key)
                prefix = f"第{seq}章 " if seq not in (None, "") else ""
                lines.append(f"- {prefix}{title or key}")
                if len(lines) >= 8:
                    break
            if len(lines) >= 8:
                break
        return "\n".join(lines)
    except Exception:
        _record_story_soft_fail("empty_story_causal")
        return ""


def collect_story_fuel_segments(inputs: dict | None) -> list[dict]:
    """assemble 真入口：format_story_fuel_parts → supplemental 段。空则记 soft_fail。"""
    from scribe3.story_constraint_prompt import format_story_fuel_parts
    inp = inputs if isinstance(inputs, dict) else {}
    fuel = format_story_fuel_parts(
        prior_consequences=inp.get("prior_consequences") or "",
        recall_context=inp.get("recall_context") or "",
        causal_graph=inp.get("causal_graph") or "",
    )
    segs: list[dict] = []
    for name in ("story_ember", "story_recall", "story_causal"):
        text = (fuel.get(name) or "").strip()
        if text:
            segs.append({"name": name, "layer": "supplemental", "text": text})
        else:
            _record_story_soft_fail(f"empty_{name}")
    return segs


def load_chapter_story_inputs(st, chapter: int) -> dict:
    """写路径场面 IO：合同 / 痕迹 / 声口 / 三燃料。零写。"""
    out = {
        "contract": {},
        "evidence_must_show": [],
        "voice": {},
        "prior_consequences": "",
        "recall_context": "",
        "causal_graph": "",
    }
    if st is None or chapter is None:
        return out
    try:
        ch = st.get_chapter(int(chapter)) or {}
    except Exception:
        return out
    raw_nc = ch.get("narrative_contract")
    if isinstance(raw_nc, str) and raw_nc.strip():
        try:
            from scribe3.narrative_contract import validate_narrative_contract
            nc = validate_narrative_contract(raw_nc)
        except Exception:
            nc = {}
    elif isinstance(raw_nc, dict):
        nc = raw_nc
    else:
        nc = {}
    out["contract"] = nc
    try:
        from scribe3.story_constraint_prompt import load_evidence_must_show
        out["evidence_must_show"] = load_evidence_must_show(ch)
    except Exception:
        out["evidence_must_show"] = []
    voice = {}
    if isinstance(nc.get("bindings"), dict) and isinstance(nc["bindings"].get("scene_voice"), dict):
        voice = nc["bindings"]["scene_voice"]
    out["voice"] = voice
    if int(chapter) > 1:
        try:
            prev = st.get_chapter(int(chapter) - 1) or {}
            pnd = prev.get("narrative_drive") if isinstance(prev.get("narrative_drive"), dict) else {}
            hook = str(pnd.get("end_hook") or "").strip()
            if hook:
                out["prior_consequences"] = hook
        except Exception:
            pass
    out["recall_context"] = _hybrid_recall_for_write(st, int(chapter))
    out["causal_graph"] = _causal_chain_for_write(st, int(chapter))
    return out




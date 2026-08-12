"""Service helpers extracted from app_impl (architecture split Phase B).

Runtime: ``app_impl._rebind_services()`` rebinds each public function into
``app_impl`` globals (monkeypatch / router rebind).  Do not call these for
side-effectful paths without going through ``scribe3.app`` / ``app_impl``.
"""
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


# novel-first：写路径软失败计数 + 最近一次 budget_report（无 I/O · 可观测）
_WRITE_SOFT_FAIL_COUNTERS: dict[str, int] = {
    "epistemic_guard": 0,
    "empty_drama": 0,
    "empty_outline": 0,
    "continue_snapshot_skip": 0,
}
_LAST_WRITE_BUDGET_REPORT: dict[str, Any] = {}
_WRITE_OBS_LOCK = threading.Lock()


def record_write_soft_fail(kind: str) -> None:
    """递增 soft-fail 计数并打结构化日志（非成本 KPI）。"""
    key = str(kind or "unknown")
    with _WRITE_OBS_LOCK:
        _WRITE_SOFT_FAIL_COUNTERS[key] = int(_WRITE_SOFT_FAIL_COUNTERS.get(key, 0)) + 1
        count = _WRITE_SOFT_FAIL_COUNTERS[key]
    logging.getLogger("scribe3").info(
        "write_soft_fail kind=%s count=%s", key, count,
    )


def get_write_soft_fail_counters() -> dict[str, int]:
    with _WRITE_OBS_LOCK:
        return dict(_WRITE_SOFT_FAIL_COUNTERS)


def get_last_write_budget_report() -> dict[str, Any]:
    """最近一次 V1/V2 组装的 budget_report（可能为空 dict）。"""
    with _WRITE_OBS_LOCK:
        return dict(_LAST_WRITE_BUDGET_REPORT)


def _store_write_budget_report(report: dict[str, Any] | None) -> None:
    if not report:
        return
    with _WRITE_OBS_LOCK:
        _LAST_WRITE_BUDGET_REPORT.clear()
        _LAST_WRITE_BUDGET_REPORT.update(report)


# Note: function bodies resolve free names via rebound globals on app_impl.

# PR-EH-10: prompt blocks
from scribe3.api.services.write_assemble_blocks import (  # noqa: E402
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
            except Exception:
                pass
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


def _deduction_context_segments(st, seq: int) -> list[tuple[str, str, str]]:
    """把场景真相、每条限知投影与固定协议分开，供 Manifest 逐源追溯。

    stale 投影默认**不注入全文**（只标过期提示），避免草稿采信旧限知。
    """
    from scribe3.deduce_helpers import inject_deduction_items

    ch = st.get_chapter(seq) or {}
    truth = (ch.get("scene_truth") or "").strip()
    items = inject_deduction_items(ch)
    if not truth and not items:
        return []
    segments = [(
        "protocol:scribe3-deduction-context:v1:header",
        "deduction_protocol",
        "## 本章演绎(据此以作者视角写限知初稿)",
    )]
    if truth:
        segments.append((
            f"chapter:{seq}:scene-truth",
            "scene_truth",
            f"\n〔场景真相·全知〕{truth}",
        ))
    for ordinal, item in enumerate(items):
        identity = item.get("character_id") or "unknown"
        name = item.get("name") or identity
        if item.get("status") == "stale":
            based = item.get("based_on_truth_rev")
            cur = item.get("truth_revision")
            segments.append((
                f"chapter:{seq}:deduction:{ordinal:04d}:{identity}:stale",
                "deduction_stale",
                f"\n〔{name}·限知投影·过期〕基于真相 rev {based}，当前 rev {cur}；"
                f"请重演后再采信。正文勿将该角色旧限知当有效边界。",
            ))
            continue
        prose = (item.get("prose") or "").strip()
        if not prose:
            continue
        segments.append((
            f"chapter:{seq}:deduction:{ordinal:04d}:{identity}",
            "deduction",
            f"\n〔{name}·限知投影〕{prose}",
        ))
    segments.append((
        "protocol:scribe3-deduction-context:v1:footer",
        "deduction_protocol",
        "\n要求:以场景真相为事实骨架;焦点者**未过期**投影当 POV、他人投影约束其言行并埋反讽;"
        "过期投影仅提示勿采信;不写角色不知道的私密。",
    ))
    return segments


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
                except Exception:
                    pass
        return "\n\n" + block if block else ""
    except Exception:
        logging.getLogger("scribe3").debug("素材召回块失败(不阻断写作)", exc_info=True)
        return ""


def _assemble_write_instructions_v1(st, *, chapter, focalizer, phase, seed_words,
                                    short_mode, with_tools=False, work=None,
                                    envelope_trace=None, memory_trace_ctx=None,
                                    extra_instructions: str = "",
                                    request_text: str = ""):
    """统一写作编译路径：Envelope 与最终 system instructions 一次绑定。"""
    from scribe3.context_assembler import envelope_trace_manifest, render_envelope_text
    from scribe3.context_engine import CreativeContextEngine
    from scribe3.context_models import ContextRequest, ContextSource
    from scribe3.craft import build_craft_block
    import hashlib

    # 未显式传 work 时与当前 store 库名对齐(测试夹具 db=test;生产=一书一库)
    if work in (None, ""):
        work = getattr(st, "db_name", None) or "main"

    supplemental_sources: list[ContextSource] = []
    reference_craft_briefs = ()

    def _domain_input(source_id: str, source_kind: str, text: str) -> str:
        """登记 renderer 实际追加的动态领域字节；正文只进输入，Manifest 只存摘要。"""
        if not text:
            return ""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        supplemental_sources.append(ContextSource(
            source_id=source_id,
            source_kind=source_kind,
            work=str(work or "main"),
            content_digest=digest,
        ))
        return text

    # I1:身份用【纯身份块】而非 _editor_write_system——后者经 _editor_system 注入设定/角色/
    # 伏笔 + 章前简报,会与下方 envelope 的 canonical/global 重复(facts 2×/promises 3×)。
    # v1 让 envelope 独占 facts/promises/角色/北极星的数据注入,身份层只留身份+硬协议+文风。
    prefix = (_editor_identity_block() + _write_protocol_block()
              + _write_revision_block() + _anti_slop_floor_block())
    # WS-2：结构多样性短纪律（默认开 · fail-soft）
    try:
        from scribe3.structure_style import (
            structure_diversity_block,
            structure_diversity_inject_enabled,
        )
        if structure_diversity_inject_enabled():
            _sd = structure_diversity_block()
            if _sd:
                prefix += _domain_input(
                    f"work:{work or 'main'}:structure-diversity",
                    "structure_diversity",
                    "\n\n" + _sd,
                )
    except Exception:
        pass
    # 经验压力 E4:续写快照并入真实组装链(单源,非平行 builder)
    try:
        from scribe3.experience.continue_rite import (
            build_continue_snapshot, continue_block_text,
        )
        from scribe3.experience import exp_state as _exp_st
        if _exp_st.has_reread_ack(work or "main", chapter) or not _exp_st.get_require_reread(work or "main"):
            _snap = build_continue_snapshot(st, chapter, work=work or "main")
            _cblk = continue_block_text(_snap)
            if _cblk:
                prefix += _domain_input(
                    f"chapter:{chapter}:continue-snapshot", "continue_snapshot",
                    _cblk,
                )
            else:
                record_write_soft_fail("continue_snapshot_skip")
        else:
            record_write_soft_fail("continue_snapshot_skip")
    except Exception:
        record_write_soft_fail("continue_snapshot_skip")
    prefix += _domain_input(
        f"chapter:{chapter}:secret-guard", "secret_guard",
        _secret_guard_block(st, chapter),
    )
    prefix += _domain_input(
        f"chapter:{chapter}:request-position", "request_position",
        f"\n当前第 {chapter} 章。",
    )
    if with_tools:
        prefix += _domain_input(
            f"work:{work or 'main'}:tool-scope", "tool_scope",
            _s3_work_scope_block(work),
        )
        from scribe3.craft_skills import skills_index_block
        prefix += _domain_input(
            f"work:{work or 'main'}:craft-skills-index", "craft_skills_index",
            skills_index_block(),
        )   # P1 定案B:技法索引(渐进披露)
    if focalizer:
        try:
            from scribe3.epistemic_guard import writing_limited_banner
            focalizer_input = writing_limited_banner(focalizer)
        except Exception:
            focalizer_input = (f"作者指定本章跟随焦点者 {focalizer} 的限知视角:"
                               "贴该角色所知所感写,别写他不知道的私密。")
    else:
        try:
            from scribe3.epistemic_guard import writing_omniscient_author_banner
            focalizer_input = writing_omniscient_author_banner()
        except Exception:
            focalizer_input = "本章未指定限知焦点者 → 作者视角(可全知)。"
    prefix += _domain_input(
        f"chapter:{chapter}:focalizer", "focalizer",
        focalizer_input,
    )
    # parity 修补(2026-07-15):v1 身份层刻意不走 _editor_system(见上方 I1 注释,防
    # facts/promises 与 envelope 重复),但代价是设定圣经(codex:faction 28 字段/世界
    # 规则/术语/物件/母题)在 v1 完全缺席——CX-Task 6 后这是旗舰能力,不能因为切到 v1
    # 就消失(否则"开旗即回归")。逐字复用旧链同一函数、同一 for_generation=True 语义
    # (对照 _editor_system 内 app.py:3594 的调用形状;_editor_write_system 恒传
    # for_generation=True,唯一生成入口——v1 同样是生成路径,必须同传,漏传就是泄密)。
    # novel-first V2：codex 移到 drama/envelope 之后（注意力）；V1 保持 prefix 兼容。
    from scribe3.context_budget import (
        cap_codex_text,
        envelope_v2_enabled,
        get_codex_inject_cap,
        join_generation_segments,
    )
    _v2 = envelope_v2_enabled()
    codex_input = (
        "\n\n【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】\n"
        + (_codex_block(st, reveal=not focalizer, focalizer=focalizer,
                        chapter=chapter, for_generation=True,
                        request_text=request_text) or "(尚无设定)")
        + "\n"
    )
    if not _v2:
        prefix += _domain_input(
            f"work:{work or 'main'}:codex", "codex", codex_input,
        )
    else:
        codex_input = cap_codex_text(codex_input, get_codex_inject_cap())
    # 统一上下文段(替代旧 avoid/voice/arc/motif/frame/recap/tail/outline/material 散点拼装)
    # B∪C：memory_trace_ctx 真 session/revision 注入 snapshot，供 TurnBind 与检查器对齐。
    snap = _write_snapshot(st, chapter=chapter, focalizer=focalizer,
                           phase=phase, work=work, memory_trace_ctx=memory_trace_ctx)
    mode = "write" if (phase or "").strip().lower() in ("draft", "final") else "plan"
    # I1(Task 16-C 核心修复):写作路径必须给 assemble 一个【有意义 query】,否则
    #   store.memory_bm25/vector 对空串硬返 [](graph 种子亦空)→ episodic/working 三条经验
    #   通道全归零,只剩 structured/canonical(与 query 无关,retriever=None 降级即可得),
    #   捕获→memory_item→检索的经验回路在生产仍是"只写不读"。故 fabric 开(retriever 非 None)时
    #   用本章种子词/作者本轮请求/章纲作 query 靶向经验记忆;作者请求只当检索锚点，不
    #   作为正典或额外事实块。fabric 关(retriever=None)时 query 仍空——
    #   envelope 与接线前逐字不变(fabric 关时字节等价,连 focus 块"作者此刻问"都不出现)。
    #   剧透门不受影响:known_from 门在 store SQL/Python 侧恒生效,有意义 query 也挡不掉未来揭示。
    retriever = _get_write_retriever(st)
    retrieval_query = (_build_write_retrieval_query(
        st, chapter=chapter, seed_words=seed_words, request_text=request_text)
                       if retriever is not None else "")
    # Task 16 最后一厘米:检索发生(retriever 非 None = MEMORY_FABRIC 开)时收集本次完整
    # RetrievalResult,组装后落 memory_trace 给 ContextInspector 真数据。retriever=None
    # (MEMORY_FABRIC 关)→ 收集器 None → assemble 走协议 retrieve() → 与接线前【字节等价】。
    _retrieval_out = {} if retriever is not None else None

    def _render_final_input(envelope):
        nonlocal reference_craft_briefs
        # Manifest 必须 hash 真正交给 Hermes/Qwen 官方服务的全部字节。
        # 因此 envelope 后的工艺块、强制协议和演绎终检也在 renderer 内
        # 完成，编译返回后不再追加任何 instructions。
        # novel-first：收集段 → join_generation_segments（SSOT 物理序 + V2 L2）
        segs: list[dict] = []

        def _push(name: str, layer: str, text: str) -> str:
            if not text:
                return ""
            segs.append({"name": name, "layer": layer, "text": text})
            return text

        _push("prefix", "redline", prefix)
        # 叙事引擎：事件驱动引导块在戏剧 GCD 之前（冲突/事件主时钟）。
        # PR-4：戏剧合同置顶、先于 envelope 重记忆；冲突时裁记忆不裁戏剧（见 must-link cap）。
        _ed = _domain_input(
            f"chapter:{chapter}:event-drive", "event_drive",
            _event_drive_block(st, chapter, focalizer=focalizer or ""),
        )
        _push("event_drive", "redline", _ed)
        _dr_raw = _drama_block(st, chapter, focalizer=focalizer or "")
        if not (_dr_raw or "").strip():
            record_write_soft_fail("empty_drama")
            try:
                from scribe3.drama_beats import format_drama_vacuum_warn
                _vac = format_drama_vacuum_warn()
                if _vac:
                    _push(
                        "drama_vacuum",
                        "redline",
                        _domain_input(
                            f"chapter:{chapter}:drama-vacuum", "drama_vacuum",
                            _vac,
                        ),
                    )
            except Exception:
                pass
        _dr = _domain_input(
            f"chapter:{chapter}:drama-contract", "drama_contract",
            _dr_raw,
        )
        _push("drama_contract", "redline", _dr)
        env_text = render_envelope_text(envelope)
        if env_text:
            _push("envelope", "envelope", "\n\n" + env_text)
        # V2：codex 在 envelope 之后（注意力 · 防设定洪水盖住戏剧）
        if _v2 and codex_input:
            _cx = _domain_input(
                f"work:{work or 'main'}:codex", "codex", codex_input,
            )
            _push("codex", "supplemental", _cx)
        _sw = _domain_input(
            f"chapter:{chapter}:seed-words", "seed_words",
            _soak_block(seed_words),
        )
        _push("seed_words", "supplemental", _sw)
        # A7：作者粘贴圣经刷分 soft telemetry（不硬拒写 · 不 400）
        try:
            rt = (request_text or "").strip()
            if len(rt) >= 40:
                from scribe3.memory_must_link import detect_author_restated_canon
                anchors = []
                try:
                    # 轻量：用本章 synopsis/brief 片段作锚（有则）
                    ch_meta = st.get_chapter(int(chapter)) or {}
                    syn = str(ch_meta.get("synopsis") or "")
                    if syn:
                        anchors.append({"text": syn[:80]})
                    for bit in re.findall(r"[\u4e00-\u9fff]{2,8}", syn)[:8]:
                        anchors.append({"text": bit})
                except Exception:
                    anchors = []
                if anchors:
                    _rr = detect_author_restated_canon(rt, anchors, threshold=0.8)
                    if _rr.get("restated"):
                        _budget_report_holder.setdefault("author_restated_canon", _rr)
                        logging.getLogger("scribe3.write_assemble").info(
                            "author_restated_canon soft work=%s ch=%s ratio=%s",
                            work, chapter, _rr.get("ratio"),
                        )
        except Exception:
            pass
        craft = build_craft_block(st.list_craft_rules() or None, short_mode=short_mode)
        if craft:
            _cr = _domain_input(
                f"work:{work or 'main'}:craft", "craft", "\n\n" + craft,
            )
            _push("craft", "supplemental", _cr)
        # WS-1 C.2：phase_role 与 craft/anti_slop 去重
        _pr_raw = _phase_role_block(phase)
        try:
            from scribe3.injection_compact import dedup_phase_role
            _pr_raw = dedup_phase_role(
                _pr_raw,
                craft_text=craft or "",
                anti_slop_text=_anti_slop_floor_block() or "",
            )
        except Exception:
            pass
        _pr = _domain_input(
            f"chapter:{chapter}:phase-role", "phase_role",
            _pr_raw,
        )
        _push("phase_role", "supplemental", _pr)
        # WS-1 C.3：avoid 并入 anti_slop 时不推独立段
        _skip_avoid = False
        try:
            from scribe3.injection_compact import should_omit_avoid_domain
            _skip_avoid = should_omit_avoid_domain()
        except Exception:
            _skip_avoid = False
        if not _skip_avoid:
            _av = _domain_input(
                f"chapter:{chapter}:avoid", "avoid",
                _avoid_directive(st, chapter),
            )
            _push("avoid", "supplemental", _av)
        _rev = _domain_input(
            f"chapter:{chapter}:revelation-discipline", "revelation_discipline",
            _revelation_discipline_block(focalizer),
        )
        _push("revelation_discipline", "redline", _rev)
        _sinc = _focalizer_sincerity_block()
        _push("sincerity", "redline", _sinc)
        _pu = _domain_input(
            f"chapter:{chapter}:purpose", "purpose",
            _purpose_workflow_block(st, chapter, with_tools, work),
        )
        _push("purpose", "supplemental", _pu)
        # 大纲/节拍契约正文(mode=write,剥离 plan 协议尾段);domain fail-soft
        def _outline_write_domain():
            try:
                return _outline_block(
                    st, chapter, focalizer=focalizer or "", mode="write",
                )
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "写路径 outline 注入失败(fail-soft): %s", e)
                return ""

        _ol_raw = _outline_write_domain()
        if not (_ol_raw or "").strip():
            record_write_soft_fail("empty_outline")
        _ol = _domain_input(
            f"chapter:{chapter}:outline", "outline",
            _ol_raw,
        )
        _push("outline", "supplemental", _ol)
        # 当前卷 intro 摘要(flag 默开;空 intro/无卷 → 空串) · WS-1 C.1 compact
        _vol_intro = _volume_intro_block(st, chapter, focalizer=focalizer or "")
        try:
            from scribe3.injection_compact import compact_volume_intro
            _ch_meta = st.get_chapter(chapter) or {}
            _syn = str(_ch_meta.get("synopsis") or "")
            _vt, _vg = "", ""
            _vid_tmp = _ch_meta.get("volume")
            if _vid_tmp not in (None, ""):
                for _v in (st.list_volumes() or []):
                    if str(_v.get("id")) == str(_vid_tmp):
                        _vt = str(_v.get("title") or "")
                        _vg = str(_v.get("goal") or _v.get("intro") or "")
                        break
            _vol_intro = compact_volume_intro(
                _vol_intro,
                synopsis=_syn,
                outline_text=_ol_raw or "",
                volume_title=_vt,
                volume_goal=_vg,
            )
        except Exception:
            pass
        _vid = "none"
        if _vol_intro:
            try:
                _vid = str((st.get_chapter(chapter) or {}).get("volume") or "none")
            except Exception:
                _vid = "none"
        _vi = _domain_input(
            f"volume:{_vid}:intro", "volume_intro", _vol_intro,
        )
        _push("volume_intro", "supplemental", _vi)
        _bm = _domain_input(
            f"chapter:{chapter}:brief-must", "brief_must",
            _brief_must_sections_write_block(st, chapter, focalizer=focalizer or ""),
        )
        _push("brief_must", "supplemental", _bm)
        # WS-1 C.4：pressure 与 drama 结构化差集（drama 仅渲染串则整块保留）
        _pd_txt = _pressure_drive_write_block(st, chapter)
        try:
            from scribe3.injection_compact import pressure_diff_keys
            from scribe3.pressure_drive import load_pdc, render_pressure_drive_block
            _ch_p = st.get_chapter(int(chapter)) if chapter is not None else None
            _pdc = load_pdc(_ch_p) if _ch_p else None
            _drama_obj = None
            if isinstance(_ch_p, dict):
                raw_d = _ch_p.get("drama_contract") or _ch_p.get("drama")
                if isinstance(raw_d, dict):
                    _drama_obj = raw_d
            _emit = pressure_diff_keys(_pdc, _drama_obj)
            if _emit is not None and _pdc is not None:
                if not _emit:
                    _pd_txt = ""
                else:
                    slim = {k: _pdc.get(k) for k in _emit if k in _pdc}
                    # 保留最小结构键以免 render 全空
                    for _keep in ("fork", "progress", "role"):
                        if _keep in _pdc and _keep not in slim:
                            pass
                    _pd_txt = render_pressure_drive_block(slim) or ""
        except Exception:
            pass
        _pd = _domain_input(
            f"chapter:{chapter}:pressure-drive", "pressure_drive",
            _pd_txt,
        )
        _push("pressure_drive", "supplemental", _pd)
        _ap = _domain_input(
            f"work:{work or 'main'}:author-prefs", "author_prefs",
            _author_prefs_block_safe(),
        )
        _push("author_prefs", "supplemental", _ap)
        _va = _domain_input(
            f"chapter:{chapter}:voice-anchor", "voice_anchor",
            _voice_anchor_block(st, focalizer or ""),
        )
        _push("voice_anchor", "supplemental", _va)
        normalized_phase = (phase or "").strip().lower()
        if normalized_phase in ("draft", "final"):
            from scribe3.reference_craft import craft_briefs_for_write
            reference_craft_briefs = craft_briefs_for_write(st, str(work or "main"))
            for brief in reference_craft_briefs:
                _rf = _domain_input(
                    f"reference_fingerprint:{brief.fingerprint_id}", "reference_craft",
                    brief.text,
                )
                _push("reference_craft", "supplemental", _rf)
            # PR-5：Benchmark advisory 注入（旗默认关 · L2 可裁 · 不写 prose）
            try:
                from scribe3.benchmark_lib import (
                    build_benchmark_inject_segment,
                    benchmark_inject_enabled,
                )
                if benchmark_inject_enabled():
                    _bm_txt = build_benchmark_inject_segment(str(work or "main"))
                    if _bm_txt.strip():
                        _bm = _domain_input(
                            f"chapter:{chapter}:benchmark-advisory",
                            "benchmark_advisory",
                            "\n\n" + _bm_txt,
                        )
                        _push("benchmark_advisory", "supplemental", _bm)
            except Exception:
                pass
            for ordinal, (source_id, source_kind, text) in enumerate(
                _deduction_context_segments(st, chapter)
            ):
                _dd = _domain_input(
                    source_id, source_kind,
                    ("\n\n" if ordinal == 0 else "") + text,
                )
                _push("deduction_final", "redline", _dd)
            _mr = _domain_input(
                f"chapter:{chapter}:material-recall", "material_recall",
                _material_recall_block(st, chapter, phase=normalized_phase,
                                       focalizer=focalizer or "", llm=None,
                                       request_text=request_text),
            )
            _push("material_recall", "supplemental", _mr)
        _fr = _final_reminder()
        _push("final_reminder", "redline", _fr)
        if normalized_phase == "deduce":
            truth = ((st.get_chapter(chapter) or {}).get("scene_truth") or "").strip()
            scene_truth_input = (
                "\n\n## 本场「场景真相」(角色投影的唯一事实源)\n"
                + (truth or "(尚未填写场景真相；只能说明未能确认。)")
                + "\n\n【演绎终检合同】输出必须逐字可追溯到本场「场景真相」。"
                  "每个标题下只写真相中明确出现、且该角色可感知的内容；"
                  "不得补写环境细节、动作过程、人物关系、历史、心理原因或后续结果。"
                  "真相未写明时用“未能从场景真相确认。”留白，而不是推测。"
            )
            _st = _domain_input(
                f"chapter:{chapter}:scene-truth", "scene_truth", scene_truth_input,
            )
            _push("scene_truth_proj", "redline", _st)
        if extra_instructions:
            _rc = _domain_input(
                f"chapter:{chapter}:request-constraint", "request_constraint",
                "\n\n" + extra_instructions,
            )
            _push("request_constraint", "supplemental", _rc)

        # P2：软 lore 激活（仅 material/reference/codex 类；红线免疫）
        try:
            from scribe3.soft_activation import apply_soft_activation, soft_activation_enabled
            if soft_activation_enabled():
                _keys = []
                try:
                    _keys = [
                        w for w in re.findall(
                            r"[\u4e00-\u9fff]{2,8}|[A-Za-z]{3,16}",
                            str(retrieval_query or "")[:400],
                        )
                    ][:12]
                except Exception:
                    _keys = []
                segs, _act_rep = apply_soft_activation(segs, activation_keys=_keys)
                _budget_report_holder.setdefault("activation", _act_rep)
        except Exception:
            pass
        # 统一 join（V2：L2 有序裁剪；禁止 rendered[:hard] 尾截）
        joined, bud_rep = join_generation_segments(segs, v2=_v2)
        bud_rep = dict(bud_rep)
        if _budget_report_holder.get("activation"):
            bud_rep["soft_activation"] = _budget_report_holder["activation"]
        # P2 residual：写路径挂事件图一跳（共享 novel_first_surface，非平行实现）
        try:
            from scribe3.novel_first_surface import event_graph_from_store_chapter
            _eg = event_graph_from_store_chapter(st, int(chapter))
            bud_rep["event_graph"] = {
                "version": _eg.get("version"),
                "edge_count": (_eg.get("graph") or {}).get("edge_count"),
                "nodes": (_eg.get("graph") or {}).get("nodes"),
                "one_hop": _eg.get("one_hop"),
                "sample_pair": _eg.get("sample_pair"),
                "surface": _eg.get("surface"),
            }
        except Exception:
            pass
        # O33：故事线 polish 短段（旗关则 text 空；不挡 redline）
        try:
            from scribe3.storyline_inject_polish import (
                build_storyline_inject_segment,
                storyline_inject_enabled,
            )
            if storyline_inject_enabled():
                _seg = build_storyline_inject_segment(focus_seq=int(chapter))
                if (_seg.get("text") or "").strip():
                    joined = joined + str(_seg["text"])
                    bud_rep["storyline_inject"] = {
                        "applied": True,
                        "audit": _seg.get("audit"),
                    }
        except Exception:
            pass
        _budget_report_holder["report"] = bud_rep
        _store_write_budget_report(bud_rep)
        return joined, tuple(supplemental_sources)

    _budget_report_holder: dict = {}

    import uuid
    context_request = ContextRequest(
        request_id=uuid.uuid4().hex,
        task_kind="final" if (phase or "").strip().lower() == "final" else "draft",
        target_ref=f"chapter:{chapter}",
        navigation_snapshot_id=snap.navigation_id,
        work=snap.work,
        chapter=chapter,
        phase=snap.phase,
        actor_role="writer",
        pov_character=focalizer or None,
        required_slots=("focus", "global"),
        forbidden_source_kinds=generation_forbidden_source_kinds(),
        policy_version="generation.v1",
    )
    compiled = CreativeContextEngine(
        st, retriever=retriever, retrieval_out=_retrieval_out,
    ).compile(
        context_request, snap, retrieval_query, mode, _render_final_input,
    )
    envelope = compiled.envelope
    # M3 记账 + 指标接入:采样本次组装 envelope 的 token 估算(context_tokens_p95 由 0 变真实)。
    # 纯观测副作用，不改 instructions 字节；统一内核每次成功编译都会采样，
    # 与 MEMORY_FABRIC 是否启用无关（内存 deque、无秘密、字节无害）。
    try:
        from scribe3 import context_cache as _cc
        _cc.record_context_tokens(envelope.total_token_estimate)
    except Exception:
        pass
    # Caveat 1(Task 17 Step 5b):把 envelope 的【安全块清单】回填 envelope_trace,供
    # chat/write 落 chat_message.trace.context 审计"主编这轮看到了哪些上下文块"(Task 14
    # ContextInspector 数据源)。复用 envelope_trace_manifest —— 它本就"给 trace.context 用"
    # (计划 Step 5):每块只记 name/token/source id/被屏蔽 source id + omitted 原因,
    # 【绝不含】块正文与秘密 value(限知红线,test_trace_manifest_excludes_secret_values 锁死)。
    # 纯观测副作用:envelope_trace 缺省 None(仅 chat_write_post 传入)→ 其余调用方字节等价;
    # 摘要计算异常绝不影响写作主链路。
    if envelope_trace is not None:
        binding = {
            "request_id": compiled.request.request_id,
            "manifest_id": compiled.manifest.manifest_hash,
            "policy_version": compiled.manifest.policy_version,
            "actual_input_hash": compiled.manifest.actual_input_hash,
        }
        context_trace = envelope_trace_manifest(envelope)
        context_trace.update(binding)
        envelope_trace["context"] = context_trace
        envelope_trace.update(binding)
        # IA PR-6：可选注入去重报告（观测，不含正文）
        try:
            from scribe3.memory_must_link import (
                inject_dedup_enabled, must_link_already_pinned_from_items,
            )
            pin_items = []
            try:
                for blk in (getattr(envelope, "blocks", None) or []):
                    for it in (getattr(blk, "items", None) or []):
                        pin_items.append(it)
            except Exception:
                pin_items = []
            pinned = must_link_already_pinned_from_items(pin_items)
            envelope_trace["dedup_report"] = {
                "inject_dedup": inject_dedup_enabled(),
                "must_link_pinned": pinned,
                "brief_must_link_short_circuit": inject_dedup_enabled() and pinned,
                "pin_detect": "reason=must_link_priority|source_id_prefix",
            }
        except Exception:
            pass
        # novel-first：外露 budget_report + density_trace（非 tokens_saved KPI）
        try:
            _br = _budget_report_holder.get("report") or get_last_write_budget_report()
            if _br:
                envelope_trace["budget_report"] = _br
                envelope_trace["soft_fail_counters"] = get_write_soft_fail_counters()
                try:
                    from scribe3.injection_registry import density_trace_for_segments
                    _env_lens: dict[str, int] = {}
                    _prov_items = 0
                    try:
                        for _blk in (getattr(envelope, "blocks", None) or []):
                            _bn = str(getattr(_blk, "name", "") or "")
                            _bt = str(getattr(_blk, "text", "") or "")
                            _env_lens[_bn] = len(_bt)
                            if _bn == "provenance":
                                _prov_items = len(
                                    getattr(_blk, "sources", None) or []
                                ) or (1 if _bt else 0)
                        # G1(a) 硬字段：以实际渲染进 envelope 的 provenance 块为准
                        # （禁止用 flag 强制 0 掩盖泄漏；budget=0/forbidden 正常时此处即 0）
                        _prov_chars = int(_env_lens.get("provenance", 0) or 0)
                        try:
                            from scribe3.context_assembler import render_envelope_text
                            _ren = render_envelope_text(envelope) or ""
                            if "## 溯源清单" in _ren and _prov_chars == 0:
                                # 泄漏：标题出现在 joined 但块长未记 → 按命中段计
                                _i = _ren.find("## 溯源清单")
                                _prov_chars = max(_prov_chars, len(_ren[_i:_i + 200]))
                        except Exception:
                            pass
                    except Exception:
                        _prov_chars = 0
                        _prov_items = 0
                    envelope_trace["density_trace"] = density_trace_for_segments(
                        domain_lengths=_br.get("domain_lengths"),
                        order_indices=_br.get("order_indices"),
                        envelope_block_lengths=_env_lens,
                        provenance_trace_items=_prov_items,
                        provenance_in_prompt_chars=_prov_chars,
                    )
                    # R1：持久化 density 快照（跨请求 scorecard 可读；fail-soft）
                    try:
                        from scribe3.density_trace_store import upsert_density_trace
                        _dt_persist = dict(envelope_trace["density_trace"] or {})
                        _dt_persist["source"] = "write_assemble"
                        _up = upsert_density_trace(st, int(chapter), _dt_persist)
                        if _up.get("delta") is not None:
                            envelope_trace["density_delta"] = _up["delta"]
                        envelope_trace["density_persist_ok"] = bool(_up.get("ok"))
                    except Exception:
                        logging.getLogger("scribe3").debug(
                            "density_trace persist fail-soft", exc_info=True,
                        )
                except Exception:
                    pass
        except Exception:
            logging.getLogger("scribe3").debug(
                "budget_report envelope_trace attach fail-soft", exc_info=True,
            )
    else:
        # 无 envelope_trace 时仍写入模块级 last report（已在 render 内 _store）
        pass
    if reference_craft_briefs:
        from scribe3.quality.store import QualityStore
        QualityStore(st).record_reference_craft_use(
            work=str(work or "main"), chapter=int(chapter),
            request_id=compiled.request.request_id,
            manifest_id=compiled.manifest.manifest_hash,
            briefs=reference_craft_briefs,
        )
    # B∪C：前端带齐 session+revision 时，每次成功 compile 都落 TurnBind（与 fabric 无关）。
    # 另：fabric 开且有 RetrievalResult 时继续落 memory_trace（检索明细层）。
    # best-effort：落库失败只告警，绝不阻断写作主链路。
    _mtc = memory_trace_ctx or {}
    if _mtc.get("context_session_id") and _mtc.get("context_revision") is not None:
        _result = (_retrieval_out or {}).get("result") if _retrieval_out is not None else None
        _sel, _rej = [], []
        if _result is not None:
            try:
                from scribe3.store import build_memory_trace
                _tmp = build_memory_trace(
                    trace_id="tmp", work=str(work or ""), thread_id="",
                    context_session_id=str(_mtc.get("context_session_id")),
                    snapshot_revision=int(_mtc.get("context_revision")),
                    result=_result, store=st)
                _sel = list(_tmp.get("selected") or [])
                _rej = list(_tmp.get("rejected") or [])
            except Exception:
                logging.getLogger("scribe3").warning(
                    "turn selected 映射失败(忽略)", exc_info=True)
        _usage = {}
        try:
            _usage = (envelope_trace or {}).get("context", {}).get("usage_digest") or {}
            if not _usage:
                from scribe3.context_assembler import envelope_trace_manifest
                _usage = envelope_trace_manifest(envelope).get("usage_digest") or {}
        except Exception:
            _usage = {}
        _tk = "final" if (phase or "").strip().lower() == "final" else "draft"
        try:
            try:
                _scb = _save_context_turn_bind  # type: ignore[name-defined]
            except NameError:
                from scribe3.api.services.write_stream import _save_context_turn_bind as _scb
            _scb(
                st, snap=snap, envelope=envelope, work=work, ctx=_mtc,
                task_kind=_tk, path="write",
                manifest_id=compiled.manifest.manifest_hash,
                request_id=compiled.request.request_id,
                actual_input_hash=compiled.manifest.actual_input_hash,
                policy_version=compiled.manifest.policy_version,
                selected=_sel, rejected=_rej, query=retrieval_query,
                usage_digest=_usage)
        except Exception:
            logging.getLogger("scribe3").warning(
                "context_turn_bind 落库失败(忽略,不阻断写作)", exc_info=True)
        if _result is not None:
            try:
                try:
                    _smt = _save_write_memory_trace  # type: ignore[name-defined]
                except NameError:
                    from scribe3.api.services.write_stream import _save_write_memory_trace as _smt
                _smt(
                    st, snap=snap, envelope=envelope, result=_result,
                    query=retrieval_query, work=work, ctx=_mtc)
            except Exception:
                logging.getLogger("scribe3").warning(
                    "memory_trace 落库失败(忽略,不阻断写作)", exc_info=True)
    # D6：限知写路径出口守卫——帧外 secret 明文不得出站进模型
    rendered = compiled.rendered_input
    if focalizer:
        try:
            from scribe3.epistemic_guard import (
                EpistemicLeakError,
                guard_write_instructions,
            )
            rendered, _hits = guard_write_instructions(
                rendered, st, focalizer=focalizer, chapter=chapter, scrub=True,
            )
            if _hits:
                # 有命中但已 scrub：仍记 soft 计数（可观测，非成本 KPI）
                record_write_soft_fail("epistemic_guard")
        except EpistemicLeakError:
            # O17 fail-loud：向上抛，不吞
            record_write_soft_fail("epistemic_guard")
            raise
        except Exception:
            record_write_soft_fail("epistemic_guard")
            logging.getLogger("scribe3").warning(
                "epistemic guard failed (fail-soft keep instructions)", exc_info=True)
    return rendered


def check_generate_reread_gate(work: str, chapter: int) -> dict:
    """供 /chat/write 等生成入口:硬续写模式未 ack 则拒。"""
    from scribe3.experience import exp_state
    from scribe3.experience.continue_rite import reread_allowed
    return reread_allowed(
        require_reread=exp_state.get_require_reread(work),
        acked=exp_state.has_reread_ack(work, chapter),
        is_generate=True,
    )


def _assemble_write_instructions(st, *, chapter: int, focalizer: str, phase: str,
                                 seed_words: list, short_mode: bool,
                                 with_tools: bool = False,
                                 work: str | None = None,
                                 envelope_trace: dict | None = None,
                                 memory_trace_ctx: dict | None = None,
                                 extra_instructions: str = "",
                                 request_text: str = "") -> str:
    """chat_write 完整组装链单源；生产无条件走 Creative Context Engine。

    统一内核是唯一生产写作路由。编译失败直接上抛，不得回退旧散点链
    伪装成“没有上下文”。"""
    return _assemble_write_instructions_v1(
        st, chapter=chapter, focalizer=focalizer, phase=phase,
        seed_words=seed_words, short_mode=short_mode,
        with_tools=with_tools, work=work, envelope_trace=envelope_trace,
        memory_trace_ctx=memory_trace_ctx,
        extra_instructions=extra_instructions, request_text=request_text,
    )


def assemble_discussion_system(
    st,
    *,
    work: str | None = None,
    chapter: int | None = None,
    user_msg: str = "",
    memory_trace_ctx: dict | None = None,
    pulse_text: str = "",
    directive_text: str = "",
    with_tools_hint: str = "",
) -> str:
    """B∪C：讨论路径单编译（discussion.v1），禁止写作围栏协议。

    产出与写作同源的 Envelope+Manifest；有 session 绑定时落 TurnBind。
    不调用 _capture_turn_memory。for_generation 语义：讨论全知，不走生成秘密二次门。
    """
    import logging
    import uuid
    from scribe3.context_assembler import envelope_trace_manifest, render_envelope_text
    from scribe3.context_engine import CreativeContextEngine
    from scribe3.context_models import ContextRequest, ContextSource
    from scribe3.context_assembler import estimate_tokens

    if work in (None, ""):
        work = getattr(st, "db_name", None) or "main"
    try:
        from scribe3.api.services.write_stream import (
            _write_snapshot, _get_write_retriever, _save_context_turn_bind,
        )
    except Exception:
        from scribe3.api.services import write_stream as _ws
        _write_snapshot = _ws._write_snapshot
        _get_write_retriever = _ws._get_write_retriever
        _save_context_turn_bind = _ws._save_context_turn_bind

    snap = _write_snapshot(
        st, chapter=chapter, focalizer="", phase=None, work=work,
        memory_trace_ctx=memory_trace_ctx)
    retriever = _get_write_retriever(st)
    _retrieval_out = {} if retriever is not None else None
    query = (user_msg or "").strip()[:200]
    supplemental: list[ContextSource] = []

    def _render(envelope):
        # 讨论身份 + 全知 banner（不入 generation 围栏协议）
        parts = [
            "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
            "【模式·讨论全知】本轮是作者/主编讨论，不是限知正文生成；"
            "可讨论设定与私密伏线，但不得输出 ⟦PROPOSAL⟧ 写作围栏或把讨论稿当作书稿定稿。\n"
            "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;"
            "紧扣下方统一上下文中的世界观与北极星,不空泛;给建议时给 2-3 个选项与代价。\n"
        ]
        env_text = render_envelope_text(envelope)
        if env_text:
            parts.append(env_text)
        # pulse / directive 作为可审计补充段
        extra_bits = []
        if (pulse_text or "").strip():
            extra_bits.append(pulse_text.strip())
        if (directive_text or "").strip():
            extra_bits.append(directive_text.strip())
        if (with_tools_hint or "").strip():
            extra_bits.append(with_tools_hint.strip())
        for i, bit in enumerate(extra_bits):
            sid = f"discuss:extra:{i}"
            digest = __import__("hashlib").sha256(bit.encode("utf-8")).hexdigest()
            supplemental.append(ContextSource(
                source_id=sid,
                source_kind="procedural",
                work=str(work or "main"),
                reason="discussion_supplement",
                content_digest=digest,
            ))
            parts.append(bit)
        # 作者偏好
        try:
            pref = _author_prefs_block_safe()
            if pref:
                parts.append(pref)
        except Exception:
            pass
        return "\n\n".join(p for p in parts if p), tuple(supplemental)

    context_request = ContextRequest(
        request_id=uuid.uuid4().hex,
        task_kind="discussion",
        target_ref=f"chapter:{chapter}" if chapter is not None else f"work:{work}",
        navigation_snapshot_id=snap.navigation_id,
        work=snap.work,
        chapter=chapter,
        phase=None,
        actor_role="editor",
        pov_character=None,
        # focus 含用户本轮问句；空书 global 可能薄，不强制以免误杀讨论。
        required_slots=("focus",),
        forbidden_source_kinds=(),
        policy_version="discussion.v1",
    )
    compiled = CreativeContextEngine(
        st, retriever=retriever, retrieval_out=_retrieval_out,
    ).compile(
        context_request, snap, query, "discussion", _render,
    )
    rendered = compiled.rendered_input
    # 合同：讨论系统提示不得含写作围栏协议（防误套 generation.v1 围栏段）
    if "⟦PROPOSAL scope=" in rendered or "绝对禁止输出 ⟦PROPOSAL⟧" in rendered:
        raise RuntimeError("discussion compile leaked write proposal protocol")

    _mtc = memory_trace_ctx or {}
    if _mtc.get("context_session_id") and _mtc.get("context_revision") is not None:
        _sel, _rej = [], []
        _result = (_retrieval_out or {}).get("result") if _retrieval_out is not None else None
        if _result is not None:
            try:
                from scribe3.store import build_memory_trace
                _tmp = build_memory_trace(
                    trace_id="tmp-d", work=str(work or ""), thread_id="",
                    context_session_id=str(_mtc.get("context_session_id")),
                    snapshot_revision=int(_mtc.get("context_revision")),
                    result=_result, store=st)
                _sel = list(_tmp.get("selected") or [])
                _rej = list(_tmp.get("rejected") or [])
            except Exception:
                pass
        _usage = {}
        try:
            _usage = envelope_trace_manifest(compiled.envelope).get("usage_digest") or {}
        except Exception:
            pass
        try:
            _save_context_turn_bind(
                st, snap=snap, envelope=compiled.envelope, work=work, ctx=_mtc,
                task_kind="discussion", path="discuss",
                manifest_id=compiled.manifest.manifest_hash,
                request_id=compiled.request.request_id,
                actual_input_hash=compiled.manifest.actual_input_hash,
                policy_version=compiled.manifest.policy_version,
                selected=_sel, rejected=_rej, query=query,
                usage_digest=_usage)
        except Exception:
            logging.getLogger("scribe3").warning(
                "discussion turn_bind 落库失败(忽略)", exc_info=True)
        if _result is not None:
            try:
                from scribe3.api.services.write_stream import _save_write_memory_trace
                _save_write_memory_trace(
                    st, snap=snap, envelope=compiled.envelope, result=_result,
                    query=query, work=work, ctx=_mtc)
            except Exception:
                logging.getLogger("scribe3").warning(
                    "discussion memory_trace 落库失败(忽略)", exc_info=True)
    # GAP-9：讨论出口 soft 限知扫描（不阻断）
    try:
        from scribe3.epistemic_guard import guard_discuss_instructions
        rendered, _soft_hits = guard_discuss_instructions(
            rendered, st, chapter=int(chapter) if chapter is not None else None,
        )
        if _soft_hits:
            logging.getLogger("scribe3").info(
                "discussion soft secret hits=%s", len(_soft_hits),
            )
    except Exception:
        pass
    return rendered


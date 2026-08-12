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




# PR-EH-10b: context blocks live in write_assemble_context
from scribe3.api.services.write_assemble_context import (  # noqa: E402,F401
    _editor_write_system,
    _voice_anchor_block,
    _clip_chars,
    _volume_intro_inject_enabled,
    _outline_block,
    _volume_intro_block,
    _event_drive_block,
    _drama_block,
    _deduction_context_segments,
    _purpose_and_lessons_write_block,
    _pressure_drive_write_block,
    _brief_must_sections_write_block,
    _material_recall_block,
)

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


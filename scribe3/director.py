"""写作导演 · WorkflowSnapshot 合成（P0）。

纯函数为主：从 store + pilot 读状态，产出状态页/进度胶囊/聊天预填同源 JSON。
不写库、不替代 pilot step/approve。
"""
from __future__ import annotations

from typing import Any

from scribe3.pilot import NEXT, STATES, read_state, status as pilot_status

# 人话与 UI 提示（与 pilot 状态对齐）
PILOT_LABELS: dict[str, str] = {
    "idle": "待开写",
    "outline_proposed": "大纲待放行",
    "beats_ready": "节拍就绪",
    "deduced": "演绎就绪",
    "drafting": "草稿中",
    "checked": "体检过",
    "delivered": "待终选",
    "finalized": "已定稿",
}

PHASE_HINT: dict[str, str] = {
    "idle": "outline",
    "outline_proposed": "outline",
    "beats_ready": "beats",
    "deduced": "deduce",
    "drafting": "draft",
    "checked": "final",
    "delivered": "final",
    "finalized": "final",
}

ACTION_LABELS: dict[str, str] = {
    "propose_outline": "起草大纲",
    "expand_beats": "展开节拍",
    "deduce": "演绎场景",
    "draft_loop": "生成草稿",
    "full_check": "全书体检",
    "deliver": "交付过目",
    "finalize": "终选定稿",
}

# 状态 → next_step 模板
_NEXT_TEMPLATES: dict[str, dict[str, str]] = {
    "idle": {
        "id": "start_outline",
        "title": "请主编起草本章大纲",
        "why": "章尚未进入写作流水线，先有大纲再往下推。",
        "how_chat": "直接说：帮我写第{seq}章大纲，注意……",
        "prompt": "请为第{seq}章起草大纲（3–6 句）：目标、冲突、章末钩子。结合本书意图与前章余波。",
    },
    "outline_proposed": {
        "id": "approve_outline",
        "title": "确认或修改本章大纲",
        "why": "大纲是品味检查点，须你放行后才能推节拍。",
        "how_chat": "说「通过」或具体改法；放行也可在 Pilot 驾驶舱点确认。",
        "prompt": "第{seq}章大纲我看过了：通过，请继续推节拍。若需改：……",
    },
    "beats_ready": {
        "id": "confirm_beats",
        "title": "确认节拍或继续演绎",
        "why": "节拍已就绪，可微调后进演绎。",
        "how_chat": "说「节拍可以，继续演绎」或指出要改的一拍。",
        "prompt": "第{seq}章节拍可以，请继续演绎（场景真相/限知）。",
    },
    "deduced": {
        "id": "start_draft",
        "title": "开写草稿或补场景真相",
        "why": "演绎就绪后进入正文生产。",
        "how_chat": "说「开写草稿」或先补某角色反应。",
        "prompt": "第{seq}章演绎已就绪，请按节拍开写草稿。",
    },
    "drafting": {
        "id": "revise_draft",
        "title": "改稿、续写或求助",
        "why": "草稿生成中/已有稿，用聊天推进修订。",
        "how_chat": "指出卡住处或贴出要改的段落意图。",
        "prompt": "第{seq}章草稿：我卡在……请给最小可行下一步。",
    },
    "checked": {
        "id": "handle_check",
        "title": "处理体检结果或交付",
        "why": "体检已跑，需处理问题或确认交付。",
        "how_chat": "问「还有哪些 blocking」或「可以交付了」。",
        "prompt": "第{seq}章体检结果如何？有 blocking 请列清单；没有请交付过目。",
    },
    "delivered": {
        "id": "finalize_chapter",
        "title": "终选定稿（须你放行）",
        "why": "终选是宪法级动作，必须作者背书。",
        "how_chat": "确认后到 Pilot 点终选，或说明还要改哪里。",
        "prompt": "第{seq}章我准备定稿。若还有问题请指出；否则我将去驾驶舱确认终选。",
    },
    "finalized": {
        "id": "next_chapter",
        "title": "进入下一章或清理账本",
        "why": "本章已定稿。",
        "how_chat": "说「开下一章」或「先还超期伏笔」。",
        "prompt": "第{seq}章已定稿。请建议下一章焦点，或列出应优先处理的开放伏笔。",
    },
}

JOURNEY_STATIONS = (
    ("intent", "立项"),
    ("world", "世界底座"),
    ("structure", "结构"),
    ("serialize", "连载推进"),
    ("ledger", "账本健康"),
)


def _safe_intent(st) -> dict[str, Any]:
    try:
        if hasattr(st, "get_intent"):
            return dict(st.get_intent() or {})
    except Exception:
        pass
    return {}


def _chapters(st) -> list[dict[str, Any]]:
    try:
        if hasattr(st, "chapters_lite"):
            return list(st.chapters_lite() or [])
        if hasattr(st, "list_chapters"):
            return list(st.list_chapters() or [])
    except Exception:
        pass
    return []


def _char_count(st) -> int:
    """角色数。生产 Store 真源是 ``characters()``；测试桩常用 ``list_characters``。
    旧实现只查 list_characters → 生产永远 0 → 旅程永久卡在「世界底座」，
    Web 上像「没设定」即使用户已写过角色。"""
    try:
        if hasattr(st, "list_characters"):
            n = len(st.list_characters() or [])
            if n:
                return n
        if hasattr(st, "characters"):
            return len(st.characters() or [])
    except Exception:
        pass
    return 0


def _pick_seq(st, preferred: int | None) -> int | None:
    """优先 preferred；否则首个非 finalized；否则 max seq。"""
    chs = _chapters(st)
    if not chs:
        return int(preferred) if preferred is not None else None
    seqs = sorted(int(c["seq"]) for c in chs if c.get("seq") is not None)
    if preferred is not None and int(preferred) in seqs:
        return int(preferred)
    for seq in seqs:
        try:
            if read_state(st, seq)["state"] != "finalized":
                return seq
        except Exception:
            return seq
    return seqs[-1] if seqs else None


def _pipeline(pilot_state: str) -> list[dict[str, str]]:
    labels = {
        "idle": "开写",
        "outline_proposed": "大纲",
        "beats_ready": "节拍",
        "deduced": "演绎",
        "drafting": "草稿",
        "checked": "体检",
        "delivered": "交付",
        "finalized": "定稿",
    }
    try:
        cur_i = STATES.index(pilot_state) if pilot_state in STATES else 0
    except ValueError:
        cur_i = 0
    out = []
    for i, sid in enumerate(STATES):
        if i < cur_i:
            status = "done"
        elif i == cur_i:
            status = "current"
        else:
            status = "todo"
        out.append({"id": sid, "label": labels.get(sid, sid), "status": status})
    return out


def _next_step(seq: int, pilot_state: str, parked: str = "") -> dict[str, Any]:
    if parked:
        return {
            "id": "unpark",
            "title": "处理停靠原因",
            "why": parked[:200],
            "how_chat": "把停靠原因贴给主编，请给最小修复步骤。",
            "ui_target": {"kind": "chapter", "seq": seq, "phase": PHASE_HINT.get(pilot_state, "outline")},
        }
    tpl = _NEXT_TEMPLATES.get(pilot_state) or _NEXT_TEMPLATES["idle"]
    fmt = {"seq": seq}
    return {
        "id": tpl["id"],
        "title": tpl["title"].format(**fmt) if "{seq}" in tpl["title"] else tpl["title"],
        "why": tpl["why"],
        "how_chat": tpl["how_chat"].format(**fmt),
        "ui_target": {
            "kind": "chapter",
            "seq": seq,
            "phase": PHASE_HINT.get(pilot_state, "outline"),
        },
    }


def _suggested_prompt(seq: int, pilot_state: str, parked: str = "") -> str:
    if parked:
        return f"第{seq}章 pilot 停靠：{parked[:120]}。请给具体下一步。"
    tpl = _NEXT_TEMPLATES.get(pilot_state) or _NEXT_TEMPLATES["idle"]
    return tpl["prompt"].format(seq=seq)


def _journey(st, has_open_chapter: bool) -> dict[str, Any]:
    intent = _safe_intent(st)
    intent_ok = bool(
        (intent.get("reader_feeling") or intent.get("emotional_arc") or intent.get("red_lines") or "")
        and str(intent.get("reader_feeling") or intent.get("emotional_arc") or intent.get("red_lines") or "").strip()
    )
    world_ok = _char_count(st) >= 1
    struct_ok = len(_chapters(st)) >= 1

    # 线性启发式：第一个未完成站为 current
    flags = {
        "intent": intent_ok,
        "world": world_ok,
        "structure": struct_ok,
        "serialize": has_open_chapter or struct_ok,
        "ledger": False,  # P0 不主动抢 current
    }
    current = "intent"
    for sid, _ in JOURNEY_STATIONS:
        if sid == "ledger":
            continue
        if not flags.get(sid):
            current = sid
            break
        current = "serialize" if has_open_chapter or struct_ok else sid

    if intent_ok and world_ok and struct_ok:
        current = "serialize"

    stations = []
    seen_current = False
    for sid, label in JOURNEY_STATIONS:
        if sid == "ledger":
            status = "todo"
        elif sid == current:
            status = "current"
            seen_current = True
        elif not seen_current and flags.get(sid):
            status = "done"
        elif flags.get(sid) and sid != current:
            # 已满足且已过 current 逻辑
            status = "done" if JOURNEY_STATIONS.index((sid, label)) < [s[0] for s in JOURNEY_STATIONS].index(current) else "todo"
        else:
            status = "todo"
        # 修正：current 之前全 done
        stations.append({"id": sid, "label": label, "status": status})

    # 二次规范化：current 之前 done，之后 todo；current 标 current
    ids = [s[0] for s in JOURNEY_STATIONS]
    ci = ids.index(current) if current in ids else 0
    stations = []
    for i, (sid, label) in enumerate(JOURNEY_STATIONS):
        if sid == "ledger":
            stt = "todo"
        elif i < ci:
            stt = "done"
        elif i == ci:
            stt = "current"
        else:
            stt = "todo"
        stations.append({"id": sid, "label": label, "status": stt})

    return {"stations": stations, "current_station": current}


def build_workflow_snapshot(st, work: str = "main", seq: int | None = None) -> dict[str, Any]:
    """合成 WorkflowSnapshot（P0）。"""
    work = work or "main"
    picked = _pick_seq(st, seq)
    blockers: list[dict[str, str]] = []

    def _debt_block():
        d = {"total": 0, "high": 0}
        try:
            if hasattr(st, "count_canon_debt"):
                d = dict(st.count_canon_debt() or {})
            if hasattr(st, "list_canon_candidates"):
                from scribe3.canon_inbox import facets
                fac = facets(st.list_canon_candidates(status="pending"))
                d["noise_count"] = fac.get("noise_count", 0)
                d["suggested_priority_count"] = fac.get("suggested_priority_count", 0)
        except Exception:
            pass
        return d

    if picked is None:
        journey = _journey(st, has_open_chapter=False)
        debt0 = _debt_block()
        # 无章：引导建章/立项
        intent = _safe_intent(st)
        if not (intent.get("reader_feeling") or intent.get("red_lines")):
            next_step = {
                "id": "set_intent",
                "title": "先立北极星（读者感 / 红线）",
                "why": "没有意图锚点，大纲容易飘。",
                "how_chat": "告诉主编：这本书要让读者感到……红线是……",
                "ui_target": {"kind": "northstar"},
            }
            prompt = "帮我确立本书北极星：读者感、情绪弧、红线。先给 3 个选项我选。"
            ui = {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
                  "layout_mode": "collaboration"}
        else:
            next_step = {
                "id": "add_chapter",
                "title": "建立第一章",
                "why": "结构尚未有章。",
                "how_chat": "请主编添加第 1 章并起草大纲。",
                "ui_target": {"kind": "manuscript"},
            }
            prompt = "请添加第 1 章并起草大纲（目标、冲突、章末钩子）。"
            ui = {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
                  "layout_mode": "collaboration"}
        return {
            "work": work,
            "journey": journey,
            "chapter_lane": None,
            "current_focus": {"type": "work", "id": f"work:{work}", "label": work},
            "next_step": next_step,
            "blockers": blockers,
            "suggested_prompt": prompt,
            "ui_directive": ui,
            "canon_debt": debt0,
            "note": "P0 合成；无章时引导立项/建章",
        }

    pstat = pilot_status(st, picked)
    pstate = pstat.get("state") or "idle"
    parked = pstat.get("parked") or ""
    title = ""
    for c in _chapters(st):
        if int(c.get("seq") or -1) == picked:
            title = (c.get("title") or "")[:80]
            break

    if pstat.get("stalled"):
        blockers.append({"code": "pilot_stalled", "message": "本章自动步超时未推进，请检查或手动推进一步"})
    if parked:
        blockers.append({"code": "pilot_parked", "message": str(parked)[:200]})

    next_step = _next_step(picked, pstate, parked)
    phase = PHASE_HINT.get(pstate, "outline")
    nxt_act = pstat.get("next_action")
    chapter_lane = {
        "seq": picked,
        "title": title,
        "pilot_state": pstate,
        "pilot_state_label": PILOT_LABELS.get(pstate, pstate),
        "phase_hint": phase,
        "parked": parked,
        "stalled": bool(pstat.get("stalled")),
        "next_action": nxt_act,
        "next_action_label": ACTION_LABELS.get(nxt_act or "", nxt_act),
        "pipeline": _pipeline(pstate),
    }

    # 开放章？
    has_open = False
    for c in _chapters(st):
        try:
            if read_state(st, int(c["seq"]))["state"] != "finalized":
                has_open = True
                break
        except Exception:
            has_open = True
            break

    journey = _journey(st, has_open_chapter=has_open)
    ui_directive = {
        "entry": "manuscript",
        "phase": phase,
        "node": {"type": "chapter", "ref": picked, "id": f"ch:{picked}", "label": title or f"第{picked}章"},
        "right_tab": "chief",
        "layout_mode": "collaboration" if phase != "final" else "reading",
    }

    # 设定债（收件箱同源）；失败不拖垮旅程
    canon_debt = _debt_block()
    if int(canon_debt.get("high") or 0) > 0:
        blockers.append({
            "code": "canon_debt_high",
            "message": (
                f"有 {canon_debt['high']} 条高风险设定待确认；"
                "建议先到「设定收件箱」处理后再开写下一章。"
            ),
        })
    elif int(canon_debt.get("total") or 0) > 0:
        blockers.append({
            "code": "canon_debt",
            "message": (
                f"设定债 {canon_debt['total']} 条待确认"
                + (f"（噪声约 {canon_debt.get('noise_count', 0)}）" if canon_debt.get("noise_count") else "")
                + " · 可在设定收件箱批/拒。"
            ),
        })

    return {
        "work": work,
        "journey": journey,
        "chapter_lane": chapter_lane,
        "current_focus": {
            "type": "chapter",
            "id": f"chapter:{picked}",
            "label": title or f"第{picked}章",
        },
        "next_step": next_step,
        "blockers": blockers,
        "suggested_prompt": _suggested_prompt(picked, pstate, parked),
        "ui_directive": ui_directive,
        "canon_debt": canon_debt,
        "note": "P0 合成自 pilot+章列表+intent；非文学评分",
    }

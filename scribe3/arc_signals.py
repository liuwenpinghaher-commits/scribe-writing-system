"""角色弧光派生信号（纯函数，零 store 写）。

与设计文档 `设计文档/2026-08-09-角色弧光子系统完善改进方案.md` 对齐：
eligible / focus / miss_belief / 冷启动与节拍文案。pulse/brief/completeness 共 import。
"""
from __future__ import annotations

from typing import Any

# 与 pulse._ARC_JUMP_MAX 同值；本阶段不按书可配（KD14）
ARC_BELIEF_SLACK = 15

# 主角色档 importance（alias 归一后 + 历史中文/英文别名）
MAIN_CAST_IMPORTANCE = frozenset({
    "protagonist", "主角",
    "major", "主要", "main",
    "lead", "primary", "核心",
})

# 正向弧：Lie 信奉度应下降；负向弧：信奉度上升/恶化
_ARC_DOWN = frozenset({"positive", "disillusionment"})
_ARC_UP = frozenset({"fall", "corruption"})

# MCP / 历史 importance 别名（与 mcp._common._CHARACTER_IMPORTANCE_ALIASES 对齐意图）
_IMPORTANCE_ALIASES = {
    "protagonist": "protagonist",
    "主角": "protagonist",
    "major": "major",
    "主要": "major",
    "主要角色": "major",
    "重要配角": "major",
    "main": "major",
    "lead": "major",
    "primary": "major",
    "核心": "major",
    "minor": "minor",
    "配角": "minor",
    "background": "background",
    "龙套": "background",
    "extra": "extra",
}


def normalize_importance_for_arc(imp: str | None) -> str:
    """归一 importance 后再比 MAIN_CAST。"""
    s = (imp or "").strip()
    if not s:
        return ""
    low = s.lower()
    if s in _IMPORTANCE_ALIASES:
        return _IMPORTANCE_ALIASES[s]
    if low in _IMPORTANCE_ALIASES:
        return _IMPORTANCE_ALIASES[low]
    return low


def is_main_cast_importance(imp: str | None) -> bool:
    n = normalize_importance_for_arc(imp)
    if not n:
        return False
    if n in MAIN_CAST_IMPORTANCE:
        return True
    # 归一后的规范键
    return n in {"protagonist", "major", "main"}


def _char_importance(char: Any) -> str:
    traits = getattr(char, "traits", None)
    if isinstance(traits, dict):
        return str(traits.get("importance") or "")
    if isinstance(char, dict):
        t = char.get("traits") or {}
        if isinstance(t, dict) and t.get("importance"):
            return str(t.get("importance") or "")
        return str(char.get("importance") or "")
    return ""


def _char_id(char: Any) -> str:
    if isinstance(char, dict):
        return str(char.get("id") or char.get("character_id") or "")
    return str(getattr(char, "id", "") or "")


def _char_name(char: Any) -> str:
    if isinstance(char, dict):
        return str(char.get("name") or _char_id(char).split(":")[-1] or "")
    return str(getattr(char, "name", None) or _char_id(char).split(":")[-1] or "")


def is_arc_eligible(char: Any, anchors: dict | None) -> bool:
    """有 lie → 启用；无 lie 但主角色档 → 冷启动缺口；其余休眠。"""
    a = anchors or {}
    if (a.get("lie") or "").strip():
        return True
    return is_main_cast_importance(_char_importance(char))


def is_arc_tracking_off(intent_or_flag: Any) -> bool:
    """作品级静音：intent dict 的 arc_tracking、裸字符串 off、或 truthy flag。"""
    if intent_or_flag is None:
        return False
    if isinstance(intent_or_flag, bool):
        return intent_or_flag
    if isinstance(intent_or_flag, str):
        return intent_or_flag.strip().lower() in ("off", "false", "0", "no")
    if isinstance(intent_or_flag, dict):
        v = intent_or_flag.get("arc_tracking")
        if v is None:
            return False
        return str(v).strip().lower() in ("off", "false", "0", "no")
    return False


def partition_arc_chars(
    chars: list[Any],
    anchors_by_id: dict[str, dict],
) -> dict[str, list[dict]]:
    """拆成 with_lie / eligible_no_lie / dormant。每项 {id,name,char,anchors,importance}。"""
    with_lie: list[dict] = []
    eligible_no_lie: list[dict] = []
    dormant: list[dict] = []
    for c in chars or []:
        cid = _char_id(c)
        a = anchors_by_id.get(cid) or {}
        row = {
            "id": cid,
            "name": _char_name(c),
            "char": c,
            "anchors": a,
            "importance": _char_importance(c),
        }
        if (a.get("lie") or "").strip():
            with_lie.append(row)
        elif is_main_cast_importance(row["importance"]):
            eligible_no_lie.append(row)
        else:
            dormant.append(row)
    return {
        "with_lie": with_lie,
        "eligible_no_lie": eligible_no_lie,
        "dormant": dormant,
    }


def miss_belief(
    current: int | None,
    target: int | None,
    arc_type: str | None,
    slack: int = ARC_BELIEF_SLACK,
) -> bool:
    """True = 尚未达标（overdue_miss）。target/current 缺失时由调用方分流，本函数对 target None 永假。"""
    if target is None or current is None:
        return False
    at = (arc_type or "").strip().lower()
    if at in _ARC_DOWN:
        # 信奉度应下降：仍信得过猛 → miss
        return current > target + slack
    if at in _ARC_UP:
        # 应上升/恶化：还不够「陷」→ miss
        return current < target - slack
    # flat / 未知：绝对偏离
    return abs(current - target) > slack


def _beat_passed(
    belief: int | None,
    target: int | None,
    arc_type: str | None,
    slack: int,
) -> bool:
    """目标章已过时是否视为达标。无 target → 不算数值 miss，视为「无数值门槛」passed 以便推进。"""
    if target is None:
        return True
    if belief is None:
        return False
    return not miss_belief(belief, target, arc_type, slack=slack)


def arc_beat_focus(
    plan: list[dict] | None,
    *,
    belief: int | None,
    next_ch: int,
    arc_type: str | None = None,
    slack: int = ARC_BELIEF_SLACK,
) -> dict | None:
    """返回该角色唯一「当前关注拍」及 alignment，或 None（无 plan）。

    next_ch: 当前写作目标章（brief=即将写；pulse=审视 seq）。
    belief: 调用方按章号契约取 latest_lie_belief 后传入。
    """
    if not plan:
        return None
    ordered = sorted(
        [b for b in plan if isinstance(b, dict)],
        key=lambda b: int(b.get("target_chapter") or 0),
    )
    if not ordered:
        return None

    def _align_for(b: dict, status: str) -> dict:
        tid = b.get("id")
        return {
            "focus_beat_id": tid,
            "beat_id": tid,
            "beat_name": (b.get("beat_name") or "").replace("\n", " "),
            "target_chapter": int(b.get("target_chapter") or 0),
            "lie_belief_target": b.get("lie_belief_target"),
            "trigger_event": b.get("trigger_event") or "",
            "status": status,
            "alignment": status,
            "current_belief": belief,
            "target": b.get("lie_belief_target"),
            "next_ch": next_ch,
            "miss_slack": slack,
            "beat": b,
        }

    # 1) 最早未达标 past/due（target_chapter <= next_ch）
    for b in ordered:
        tc = int(b.get("target_chapter") or 0)
        if tc > next_ch:
            continue
        tgt = b.get("lie_belief_target")
        if tc < next_ch:
            if belief is None:
                if tgt is None:
                    # 已过且无数值目标 → info 级，仍作为 focus 提示补 target
                    return _align_for(b, "overdue_no_target")
                return _align_for(b, "overdue_unmeasured")
            if tgt is None:
                return _align_for(b, "overdue_no_target")
            if miss_belief(belief, int(tgt), arc_type, slack=slack):
                return _align_for(b, "overdue_miss")
            # passed → 继续找下一拍
            continue
        # tc == next_ch → due（不论是否已达标数值，本章应到达）
        return _align_for(b, "due")

    # 2) 全部 past 已 passed → 下一拍 approaching/due
    for b in ordered:
        tc = int(b.get("target_chapter") or 0)
        if tc > next_ch:
            gap = tc - next_ch
            if gap <= 2:
                return _align_for(b, "approaching")
            return _align_for(b, "approaching")

    # 3) 全 plan 已 passed
    return None


def format_cold_start_decision(name: str, *, tools: bool = True) -> str:
    n = (name or "角色").replace("\n", " ")
    if tools:
        return (
            f"冷启动·主角色「{n}」缺错误信念(Lie)锚：请 s3_set_char_anchors 写入 lie"
            f"（及 ghost/truth/want/need/arc_type），否则弧光指令与信奉度采样无法启用。"
        )
    return (
        f"冷启动·主角色「{n}」缺错误信念(Lie)锚：请补写 Lie/弧型内核，"
        f"否则弧光指令与信奉度采样无法启用。"
    )


def format_beat_decision(
    name: str,
    focus: dict,
    *,
    tools: bool = True,
) -> str:
    """节拍逾期三选一文案；tools=True 时点名 MCP（须 PR3 已合）。"""
    n = (name or "").replace("\n", " ")
    bn = (focus.get("beat_name") or "—").replace("\n", " ")
    tc = focus.get("target_chapter")
    cur = focus.get("current_belief")
    cur_s = "未测" if cur is None else str(cur)
    tgt = focus.get("target")
    tgt_s = "—" if tgt is None else str(tgt)
    st = focus.get("status") or focus.get("alignment") or ""
    head = (
        f"角色「{n}」关注拍「{bn}」目标第{tc}章已过，"
        f"当前信奉度 {cur_s}，目标 {tgt_s}"
    )
    if st == "overdue_unmeasured":
        head += "（尚无采样）"
    elif st == "overdue_miss":
        head += "（偏离目标）"
    if tools:
        return (
            f"{head}：① 补事件推动信念并落库（ingest 反哺，或 s3_add_char_state "
            f"change_type=belief + lie_belief）；"
            f"② 展期/重规划（s3_add_arc_beat 新目标章，或 s3_delete_arc_beat 后重建）；"
            f"③ 改写 Lie/弧型（s3_set_char_anchors）——简报持续携带直至决策。"
        )
    return (
        f"{head}：① 补事件并记录信奉度采样；② 展期/重规划里程碑；"
        f"③ 改写 Lie/弧型——简报持续携带直至决策。"
    )


def format_unmeasured_nudge(names: list[str]) -> str:
    listing = "、".join((n or "").replace("\n", " ") for n in names if n) or "角色"
    return f"已设 Lie 尚无信奉度采样：{listing}——写后 ingest 或 s3_add_char_state belief 补点"


def healthy_arc_message(n_samples: int) -> str:
    return f"弧光节奏平稳(已采样 {n_samples} 点,未见未见异常)"


def quiet_arc_message() -> str:
    return "未启用角色弧光——无主角色档/无 lie，可忽略"


def tracking_off_message() -> str:
    return "本书已关闭弧光追踪"


def count_belief_samples(beliefs_by_char: dict[str, int | None] | list[Any]) -> int:
    """统计有数值的 belief 采样点数（角色级最新值非空计 1，或列表长度）。"""
    if isinstance(beliefs_by_char, list):
        return len(beliefs_by_char)
    return sum(1 for v in (beliefs_by_char or {}).values() if v is not None)


def arc_directive_from_focus(
    name: str,
    anchors: dict,
    focus: dict | None,
    lie_belief: int | None,
    next_ch: int,
    plan: list[dict] | None = None,
) -> str:
    """三行弧光指令：所处节拍/下一拍/本章指令以 focus 为权威（KD18）。"""
    name = (name or "").replace("\n", " ")
    lie = (anchors.get("lie") or "—").replace("\n", " ")
    at = (anchors.get("arc_type") or "—").replace("\n", " ")
    cur_v = f"{lie_belief}" if lie_belief is not None else "未测"

    if focus is None:
        # 无 plan 或全 passed
        return (
            f"【角色弧光·{name}】弧型:{at} | 信念(Lie):「{lie}」\n"
            f"当前信奉度:{cur_v};所处节拍:开场常态 → 下一拍:终局\n"
            f"本章指令:朝终局缓移,位移须由本章事件背书。"
            f"禁止:一步顿悟、借台词明说信念、跳到终局姿态。"
        )

    st = focus.get("status") or focus.get("alignment") or ""
    bn = (focus.get("beat_name") or "—").replace("\n", " ")
    tc = focus.get("target_chapter")
    tgt = focus.get("target")
    tgt_s = f",信奉度趋 {tgt}" if tgt is not None else ""

    if st in ("overdue_miss", "overdue_unmeasured", "overdue_no_target"):
        cur_phase = bn
        nxt = f"{bn}(目标第{tc}章已过{tgt_s})——须先处理逾期"
        if st == "overdue_miss":
            chapter_cmd = (
                f"本章指令:关注拍「{bn}」已逾期且信奉度未达标，"
                f"须由事件背书补位移或展期里程碑，禁止假装已过拍。"
            )
        elif st == "overdue_unmeasured":
            chapter_cmd = (
                f"本章指令:关注拍「{bn}」已逾期且尚无信奉度采样，"
                f"须落库 belief 或展期，禁止空跳。"
            )
        else:
            chapter_cmd = (
                f"本章指令:关注拍「{bn}」已过但缺 lie_belief_target，"
                f"可补目标或忽略数值门槛。"
            )
    elif st == "due":
        cur_phase = "开场常态" if not plan else "推进中"
        # 若有更早 past passed，可显示上一拍；简化为「推进中」
        nxt = f"{bn}(目标第{tc}章{tgt_s})"
        chapter_cmd = (
            f"本章指令:本章应到达「{bn}」，位移须由本章事件背书。"
        )
    else:  # approaching
        cur_phase = "推进中"
        nxt = f"{bn}(目标第{tc}章{tgt_s})"
        chapter_cmd = (
            f"本章指令:朝下一拍「{bn}」缓移,位移须由本章事件背书。"
        )

    return (
        f"【角色弧光·{name}】弧型:{at} | 信念(Lie):「{lie}」\n"
        f"当前信奉度:{cur_v};所处节拍:{cur_phase} → 下一拍:{nxt}\n"
        f"{chapter_cmd}"
        f"禁止:一步顿悟、借台词明说信念、跳到终局姿态。"
    )

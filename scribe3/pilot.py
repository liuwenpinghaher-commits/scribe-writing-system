"""Chapter Pilot——章生命周期状态机(主编主动化 T6,方案 §三.决策层)。

作者=创意总监,主编=执行主编:状态机驱动 大纲→节拍→演绎→草稿(loop)→体检→交付→定稿,
每步执行完按授权矩阵决定「自动推进」还是「停靠等作者」。

设计要点:
- 纯函数核:状态表/授权判定/推进决策全部无副作用可单测;执行器(executor)由调用方
  注入(app 侧绑既有函数,测试侧 stub)——**禁止在此新写任何生成逻辑**(北极星宪法:
  regenerate 复用完整组装链,pilot 同理只做编排)。
- 宪法锚(CONSTITUTION_APPROVE)硬编码:终选定稿等四类永远 approve,book 级配置
  不可降档(authz_for 强制覆写)。
- 状态落 chapter.pilot_state(迁移 069)——崩溃后从库恢复;stalled 探测靠
  pilot_state_at 时间戳。
- 并发:与 save/dedup/loop 共用 _loop_inflight 互斥体系(app 端点侧登记)。
"""
from __future__ import annotations

import logging
import time

_log = logging.getLogger("scribe3.pilot")

# 状态序(线性主链;needs_human/failed 是停靠标记不是状态)
STATES = ("idle", "outline_proposed", "beats_ready", "deduced",
          "drafting", "checked", "delivered", "finalized")

# 每个状态的「下一步动作」:(action名, 目标状态)。finalized 无后继。
NEXT = {
    "idle": ("propose_outline", "outline_proposed"),
    "outline_proposed": ("expand_beats", "beats_ready"),
    "beats_ready": ("deduce", "deduced"),
    "deduced": ("draft_loop", "drafting"),
    "drafting": ("full_check", "checked"),
    "checked": ("deliver", "delivered"),
    "delivered": ("finalize", "finalized"),
}

# 宪法锚:这些动作任何配置/模式下都是 approve(永远等人)。
CONSTITUTION_APPROVE = frozenset({"finalize"})
# 授权默认(action → auto|propose|approve)
DEFAULT_AUTHZ = {
    "propose_outline": "propose",   # 大纲是品味起点,默认轻确认
    "expand_beats": "auto",
    "deduce": "auto",
    "draft_loop": "auto",
    "full_check": "auto",
    "deliver": "propose",           # 交付卡等作者过目(连写模式自动放行)
    "finalize": "approve",          # 宪法锚
}


def authz_for(overrides: dict | None) -> dict:
    """合成授权矩阵:book 级覆盖 + 宪法锚强制回写(试图把锚降档=静默纠正并告警)。"""
    a = dict(DEFAULT_AUTHZ)
    for k, v in (overrides or {}).items():
        if k in a and v in ("auto", "propose", "approve"):
            a[k] = v
    for k in CONSTITUTION_APPROVE:
        if a.get(k) != "approve":
            _log.warning("pilot authz 试图把宪法锚 %s 降为 %s——已强制回 approve", k, a.get(k))
            a[k] = "approve"
    return a


def read_state(st, seq: int) -> dict:
    # 直查窄字段(get_chapter 是显式字段列表,不含 pilot_*——勿绕回去)
    rows = st._query(
        "SELECT pilot_state, pilot_state_at, pilot_parked FROM type::record('chapter',$seq)",
        {"seq": seq})
    ch = rows[0] if rows else {}
    return {"state": ch.get("pilot_state") or "idle",
            "at": ch.get("pilot_state_at"),
            "parked": ch.get("pilot_parked") or ""}


def write_state(st, seq: int, state: str, parked: str = "") -> None:
    st._execute_write(
        "UPDATE type::record('chapter',$seq) SET pilot_state=$s, pilot_state_at=$t, pilot_parked=$p",
        {"seq": seq, "s": state, "t": int(time.time()), "p": parked})


def gate_of(action: str, authz: dict, mode: str) -> str:
    """本动作完成后的停靠语义:auto=继续;propose=停(连写 run 模式放行);approve=永远停。"""
    g = authz.get(action, "propose")
    if g == "approve" or action in CONSTITUTION_APPROVE:
        return "approve"
    if g == "propose" and mode == "run":
        return "auto"
    return g


def step(st, seq: int, executor: dict, *, mode: str = "manual",
         authz_overrides: dict | None = None, journal=None) -> dict:
    """推进一步:读状态 → 执行下一动作(注入的 executor)→ 写新状态 → 返回停靠决策。

    executor: {action_name: callable(st, seq) -> dict}——app 侧绑既有链;缺 action 视为配置错。
    返回 {"seq", "state", "action", "gate": auto|propose|approve|parked, "artifact", "reason"?}
    - gate=="auto":调用方可立即再 step(连写循环);
    - gate=="propose"/"approve":停靠等作者(收件箱呈现);
    - gate=="parked":执行失败/needs_human,如实停靠,reason 带因。
    """
    cur = read_state(st, seq)["state"]
    if cur == "finalized":
        return {"seq": seq, "state": cur, "action": None, "gate": "approve",
                "reason": "已定稿,无后继动作"}
    action, nxt = NEXT[cur]
    authz = authz_for(authz_overrides)
    if journal:
        try:
            journal.start_stage(f"pilot_ch{seq}_{action}")
        except Exception:
            pass
    try:
        fn = executor[action]
    except KeyError:
        raise RuntimeError(f"pilot executor 缺动作 {action}(配置错,非运行时容错项)")
    try:
        artifact = fn(st, seq)
    except Exception as e:
        _log.warning("pilot ch%s %s 执行失败(如实停靠): %s", seq, action, e)
        write_state(st, seq, cur, parked=f"{action} 失败:{str(e)[:120]}")
        return {"seq": seq, "state": cur, "action": action, "gate": "parked",
                "reason": f"{action} 失败:{str(e)[:120]}"}
    # 停靠协议(P1 审查 P0-1/P1-7):
    #   pilot_park —— executor 显式停靠(如体检 blocking);
    #   needs_human —— loop 三稿全拦;
    #   advisory —— loop 首稿带待批清单:宪法「advisory 不自动重写」的另一半是
    #   「不替作者放行」——正文未落库,清单进收件箱等批,绝不假交付空/旧稿。
    if isinstance(artifact, dict):
        park = None
        if artifact.get("pilot_park"):
            park = str(artifact["pilot_park"])[:160]
        elif artifact.get("verdict") == "needs_human":
            park = "needs_human:三稿全被确定性检测拦下,请人工裁决"
        elif artifact.get("verdict") == "advisory":
            _n = sum(len(r0.get("advisory") or r0.get("advisory_items") or [])
                     for r0 in (artifact.get("rounds") or []))
            park = f"advisory:草稿有 {_n or '若干'} 项待批建议(宪法:不替作者放行),请过目后 approve 继续"
        if park:
            write_state(st, seq, cur, parked=f"{action} → {park}")
            return {"seq": seq, "state": cur, "action": action, "gate": "parked",
                    "reason": park, "artifact": artifact}
    write_state(st, seq, nxt)
    if journal:
        try:
            journal.complete_stage(f"pilot_ch{seq}_{action}")
        except Exception:
            pass
    return {"seq": seq, "state": nxt, "action": action,
            "gate": gate_of(action, authz, mode), "artifact": artifact}


STALL_SECONDS = 30 * 60


def status(st, seq: int) -> dict:
    s = read_state(st, seq)
    stalled = bool(s["at"] and s["state"] not in ("idle", "finalized")
                   and (time.time() - s["at"]) > STALL_SECONDS and not s["parked"])
    nxt = NEXT.get(s["state"])
    return {**s, "seq": seq, "stalled": stalled,
            "next_action": nxt[0] if nxt else None}

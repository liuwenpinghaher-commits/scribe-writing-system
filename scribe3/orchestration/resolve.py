"""WorkPackage 解析 · 纯函数（无 LLM I/O，可单测驱动 shipped 路径）。"""
from __future__ import annotations

import re
import time
import uuid
from copy import deepcopy
from typing import Any

from scribe3.orchestration.catalog import CATALOG, get_domain

# 正文生成词：优先 prose 通道，避免「推进人物」误进世界写
_PROSE_RE = re.compile(
    r"(正文|草稿|段落|续写|改写|润色|扩写|缩写|写本章|写整章|写一章|完整正文|文风|镜头)"
)
_MUTATION_RE = re.compile(
    r"(新增|添加|登记|记录|补录|写入|落库|建立|创建|更新|修改|改成|删除|删卷|"
    r"归档|恢复|关闭|推进|兑现|回收|标记|更正|重排|排序|起草|埋|种)"
)


def _score_entry(text: str, entry: dict[str, Any]) -> int:
    """累加命中分：更长短语优先，避免「主角」单字抢走「埋一个承诺」。"""
    t = text or ""
    score = 0
    for kw in entry.get("match_force") or ():
        if kw and kw in t:
            score += 100
    for kw in entry.get("match_keywords") or ():
        if kw and kw in t:
            # 基础 10 + 长度加成（封顶 24），多关键词累加
            score += 10 + min(len(kw), 14)
    domain = entry.get("domain") or ""
    # 埋设动词 + 承诺/伏笔 → 明确偏向 plant（口语「埋一个承诺」）
    if domain == "promise.plant" and re.search(r"埋|种下|plant", t) and re.search(
        r"承诺|伏笔|promise", t
    ):
        score += 40
    # 兑现/回收/展期 → lifecycle
    if domain == "promise.lifecycle" and re.search(r"兑现|回收|展期|弃置|超期", t):
        score += 30
    return score


def match_domain(message: str, *, prior_domain: str | None = None) -> dict[str, Any]:
    """返回匹配分最高的 catalog 项（深拷贝）。"""
    text = (message or "").strip()
    best: dict[str, Any] | None = None
    best_score = -1
    default = None
    for entry in CATALOG:
        if entry.get("is_default"):
            default = entry
            continue
        sc = _score_entry(text, entry)
        # 同分时保留更具体域（后写的 promise 等可压过先出现的 codex.character）
        if sc > best_score or (
            sc == best_score
            and best is not None
            and sc > 0
            and (entry.get("domain") or "").count(".") >= (best.get("domain") or "").count(".")
            and len(entry.get("domain") or "") > len(best.get("domain") or "")
        ):
            best_score = sc
            best = entry
    # 正文词压过弱世界匹配（除非 force 已命中）
    if best and best.get("channel") == "world_write" and best_score < 100 and _PROSE_RE.search(text):
        prose = get_domain("prose.generate")
        if prose:
            return prose
    if best_score <= 0:
        if prior_domain:
            prior = get_domain(prior_domain)
            if prior and not prior.get("is_default"):
                return prior
        return deepcopy(default or CATALOG[-1])
    return deepcopy(best or default or CATALOG[-1])


def _extract_focus(message: str, domain: str, ctx: dict[str, Any] | None) -> dict[str, Any] | None:
    """从消息/上下文提取 focus（角色名、章号等）。"""
    ctx = ctx or {}
    # 章号
    m = re.search(r"第\s*(\d+)\s*章", message or "")
    seq = int(m.group(1)) if m else ctx.get("chapter")
    if domain.startswith("chapter.") or domain.startswith("structure.chapter") or domain.startswith("prose."):
        if seq is not None:
            return {"type": "chapter", "id": f"chapter:{int(seq)}", "ref": int(seq),
                    "label": f"第{int(seq)}章"}
    if domain.startswith("codex.character") or domain == "relation.character" or domain == "voice.manage":
        # 「角色沈砚」/「人物·甲」
        m2 = re.search(r"(?:角色|人物)[·:：\s]*([^\s，,。、]{1,12})", message or "")
        if m2:
            name = m2.group(1).strip()
            return {"type": "character", "id": f"role:{name}", "label": name}
        if ctx.get("focus_character"):
            fc = ctx["focus_character"]
            if isinstance(fc, dict):
                return fc
            return {"type": "character", "id": str(fc), "label": str(fc)}
    if domain.startswith("promise"):
        if ctx.get("promise_id"):
            return {"type": "promise", "id": str(ctx["promise_id"]), "label": "伏笔"}
        return {"type": "promise", "id": None, "label": "伏笔"}
    if domain == "intent.northstar":
        return {"type": "intent", "id": "intent", "label": "北极星"}
    return None


def build_ui_directive(
    entry: dict[str, Any],
    focus: dict[str, Any] | None,
    *,
    chapter: int | None = None,
) -> dict[str, Any]:
    ui = deepcopy(entry.get("ui") or {})
    node = ui.get("node")
    if isinstance(node, dict):
        node = dict(node)
        if focus:
            if focus.get("type") == "chapter" and focus.get("ref") is not None:
                node = {
                    "type": "chapter",
                    "id": f"ch:{focus['ref']}",
                    "ref": int(focus["ref"]),
                    "label": focus.get("label") or f"第{focus['ref']}章",
                }
            elif focus.get("type") == "character":
                node = {
                    "type": "character",
                    "id": focus.get("id") or "character",
                    "label": focus.get("label") or "",
                }
            elif focus.get("type") == "promise":
                node = {
                    "type": "promise",
                    "id": focus.get("id") or "promise",
                    "label": focus.get("label") or "伏笔",
                }
        elif chapter is not None and node.get("type") == "chapter":
            node = {
                "type": "chapter",
                "id": f"ch:{int(chapter)}",
                "ref": int(chapter),
                "label": f"第{int(chapter)}章",
            }
        ui["node"] = node
    phase = entry.get("phase_hint") or ui.get("phase")
    if phase:
        ui["phase"] = phase
    if chapter is not None and ui.get("phase") and not (ui.get("node") or {}).get("ref"):
        # 确保章域有 ref
        if ui.get("node") and ui["node"].get("type") == "chapter":
            ui["node"]["ref"] = int(chapter)
            ui["node"]["id"] = f"ch:{int(chapter)}"
    ui.setdefault("right_tab", "chief")
    return ui


def resolve_work_package(
    message: str,
    *,
    work: str = "main",
    chapter: int | None = None,
    phase: str | None = None,
    prior_package: dict[str, Any] | None = None,
    journey_next_domain: str | None = None,
    focus_hint: dict[str, Any] | None = None,
    action: str = "auto",  # auto|create|continue|switch
) -> dict[str, Any]:
    """解析/创建/继续 WorkPackage（shipped 核心）。

    返回结构无 total_score 等文学分字段。
    """
    text = (message or "").strip()
    prior = prior_package if isinstance(prior_package, dict) else None

    # journey 指定域优先（继续按钮）
    entry = None
    if journey_next_domain and action in ("auto", "create", "switch"):
        entry = get_domain(journey_next_domain)

    if entry is None and action == "continue" and prior:
        entry = get_domain(prior.get("domain") or "") or None

    if entry is None:
        prior_dom = (prior or {}).get("domain") if action != "switch" else None
        # 无新信号且 continue：沿用 prior
        if prior and action == "auto" and prior_dom and _score_entry(text, get_domain(prior_dom) or {}) <= 0:
            if not text or text in ("继续", "好", "嗯", "下一步"):
                entry = get_domain(prior_dom)
        if entry is None:
            entry = match_domain(text, prior_domain=prior_dom if action != "switch" else None)

    # phase 上下文增强
    if phase in ("outline", "beats", "deduce") and entry.get("domain") == "discuss.general":
        entry = get_domain(f"chapter.{phase}") or entry
    if phase in ("draft", "final") and entry.get("domain") == "discuss.general" and _PROSE_RE.search(text or ""):
        entry = get_domain("prose.generate") or entry

    focus = focus_hint or _extract_focus(text, entry["domain"], {"chapter": chapter})
    if focus is None and prior and prior.get("focus") and entry["domain"] == prior.get("domain"):
        focus = deepcopy(prior["focus"])

    ch = chapter
    if focus and focus.get("type") == "chapter" and focus.get("ref") is not None:
        ch = int(focus["ref"])

    ui = build_ui_directive(entry, focus, chapter=ch)
    write_tools = list(entry.get("write_tools") or ())
    read_tools = list(entry.get("read_tools") or ())
    required = entry.get("required_outcome") or "read_only_advice"
    channel = entry.get("channel") or "discuss"

    # 世界写通道：无写词且非 force 时，若 required 是 write 但消息纯讨论 → 仍保持 write_proposal
    # （空口策略在 evaluate_turn 处理）；通道标记 world_write 供前端走 Run
    use_world_write = channel == "world_write" and (
        bool(write_tools)
        and (
            _MUTATION_RE.search(text)
            or any(f in text for f in (entry.get("match_force") or ()))
            or required == "write_proposal"
        )
    )
    # prose 通道
    if channel == "prose_write":
        use_world_write = False

    pkg_id = None
    if prior and prior.get("domain") == entry["domain"] and action != "switch":
        pkg_id = prior.get("id")
    if not pkg_id:
        pkg_id = f"wp_{uuid.uuid4().hex[:12]}"

    pkg = {
        "id": pkg_id,
        "work": work or "main",
        "domain": entry["domain"],
        "label": entry.get("label") or entry["domain"],
        "status": "discussing",
        "focus": focus,
        "goal": entry.get("label") or entry["domain"],
        "tool_allowlist": read_tools + write_tools,
        "write_tools": write_tools,
        "read_tools": read_tools,
        "required_outcome": required,
        "ui_directive": ui,
        "channel": channel,
        "use_world_write_run": bool(use_world_write and write_tools),
        "phase_hint": entry.get("phase_hint") or ui.get("phase"),
        "chapter": ch,
        "updated_at": int(time.time()),
        "source": "resolve",
    }
    return pkg


def evaluate_turn(
    package: dict[str, Any],
    *,
    tools_called: list[str] | None = None,
    approved_writes: list[str] | None = None,
) -> dict[str, Any]:
    """回合结束策略：写必出则 incomplete/remedy，批准写才算 applied。

    绝不把空谈标成 written。
    """
    tools_called = list(tools_called or [])
    approved_writes = list(approved_writes or [])
    required = (package or {}).get("required_outcome") or "read_only_advice"
    write_tools = set((package or {}).get("write_tools") or ())
    called_writes = [t for t in tools_called if t in write_tools or t.startswith("s3_")]
    called_writes = [t for t in called_writes if t in write_tools] if write_tools else []

    out = {
        "package_id": (package or {}).get("id"),
        "domain": (package or {}).get("domain"),
        "required_outcome": required,
        "tools_called": tools_called,
        "write_tools_called": called_writes,
        "approved_writes": approved_writes,
        "status": "ok",
        "remedy": None,
        "fake_written": False,
    }

    if required == "write_proposal":
        if approved_writes:
            out["status"] = "applied"
            return out
        if called_writes:
            # 已调写工具但未批准 → 等待审批，不算成功写入
            out["status"] = "awaiting_approval"
            out["remedy"] = {
                "code": "approve_pending",
                "message": "写入提案已提交，请批准后才会落入设定/章结构库",
            }
            return out
        out["status"] = "incomplete"
        out["remedy"] = {
            "code": "empty_talk_no_write",
            "message": "本步需要写入提案，但未调用写工具；请点「生成写入提案」或明确要求 s3_* 写入并审批",
            "suggested_prompt": (
                f"请根据以上讨论，使用工具 "
                f"{', '.join(list(write_tools)[:4]) or '对应 s3_ 写工具'} "
                f"提交写入提案供我批准（不要只口头答应）。"
            ),
        }
        return out

    if required == "prose_proposal":
        out["status"] = "ok"  # 正文提案由流式 PROPOSAL 事件承载
        return out

    out["status"] = "ok"
    return out


def apply_ui_directive_events(directive: dict[str, Any] | None) -> list[dict[str, Any]]:
    """将 ui_directive 展开为前端可消费的事件描述（纯函数，供测试与前端共享契约）。

    前端 handler 按 type 派发 CustomEvent / setSel。
    """
    if not directive or not isinstance(directive, dict):
        return []
    events: list[dict[str, Any]] = []
    right = directive.get("right_tab") or "chief"
    events.append({"type": "s3-right-tab", "detail": right})

    node = directive.get("node")
    phase = directive.get("phase")
    entry = directive.get("entry")

    if entry:
        events.append({
            "type": "s3-open-capability",
            "detail": {"capability": entry if entry != "manuscript" else "manuscript", "focus": True},
        })

    if node and isinstance(node, dict):
        ntype = node.get("type")
        if ntype == "chapter" and node.get("ref") is not None:
            seq = int(node["ref"])
            events.append({
                "type": "selection",
                "detail": {
                    "mode": "node",
                    "node": {
                        "id": node.get("id") or f"ch:{seq}",
                        "type": "chapter",
                        "ref": seq,
                        "label": node.get("label") or f"{seq}",
                    },
                },
            })
            if phase:
                events.append({
                    "type": "s3-chapter-phase",
                    "detail": {"phase": phase, "seq": seq},
                })
        elif ntype == "character":
            events.append({
                "type": "selection",
                "detail": {
                    "mode": "node",
                    "node": {
                        "id": node.get("id") or "character",
                        "type": "character",
                        "ref": node.get("id"),
                        "label": node.get("label") or "",
                    },
                },
            })
            events.append({
                "type": "s3-open-capability",
                "detail": {"capability": "codex", "focus": True},
            })
        elif ntype == "promise":
            events.append({
                "type": "selection",
                "detail": {
                    "mode": "node",
                    "node": {
                        "id": node.get("id") or "promise:focus",
                        "type": "promise",
                        "ref": node.get("id"),
                        "label": node.get("label") or "伏笔",
                    },
                },
            })
        elif ntype in ("faction", "item", "term", "world_rule", "motif", "proposition", "volume"):
            events.append({
                "type": "selection",
                "detail": {
                    "mode": "node",
                    "node": {
                        "id": node.get("id") or ntype,
                        "type": ntype,
                        "label": node.get("label") or ntype,
                    },
                },
            })

    if directive.get("panel") == "northstar":
        events.append({
            "type": "s3-open-capability",
            "detail": {"capability": "manuscript", "focus": True},
        })

    return events

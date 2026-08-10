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
    r"归档|恢复|关闭|推进|兑现|回收|标记|更正|重排|排序|起草|规划|拟|写大纲|补大纲|填大纲|"
    r"埋|种)"
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
    # 负向：评分卡解读不得落到 intent 写；经验六格不得落到 beats 写
    if best and best.get("domain") == "intent.northstar":
        if re.search(r"评分卡|scorecard", text) and not re.search(
            r"作品意图|s3_set_intent|读者感受|红线|北极星意图", text
        ):
            aux = get_domain("aux.scorecard")
            if aux:
                return aux
    if best and best.get("domain") == "chapter.beats":
        if re.search(r"经验复盘|经验六格|问诊信|Scene.?Sequel", text) and not re.search(
            r"s3_patch_chapter_plan|写节拍|更新节拍", text
        ):
            aux = get_domain("aux.experience")
            if aux:
                return aux
    if best_score <= 0:
        if prior_domain:
            prior = get_domain(prior_domain)
            if prior and not prior.get("is_default"):
                return prior
        return deepcopy(default or CATALOG[-1])
    return deepcopy(best or default or CATALOG[-1])


def instruction_suffix_for_entry(
    entry: dict[str, Any] | None,
    *,
    chapter: int | None = None,
) -> str:
    """域纪律后缀（world_write 主路径；不依赖 run phase）。

    catalog ``instruction_duty`` 为真源；无则按 domain 回落短句。
    """
    e = entry if isinstance(entry, dict) else {}
    duty = str(e.get("instruction_duty") or "").strip()
    domain = str(e.get("domain") or "")
    ch = f"当前章:{int(chapter)}。" if chapter is not None else ""
    if duty:
        return f"{duty} {ch}".strip()
    # 回落：章脚手架三域
    fallbacks = {
        "chapter.outline": (
            "域纪律(章大纲):s3_patch_chapter_plan 写 synopsis；禁 s3_save_chapter 完成本任务。"
        ),
        "chapter.beats": (
            "域纪律(章节拍):s3_patch_chapter_plan 写 beats；禁 s3_save_chapter；≠经验六格。"
        ),
        "chapter.deduce": (
            "域纪律(章演绎):s3_patch_chapter_plan 写 scene_truth；禁 s3_save_chapter；勿 s3_add_fact。"
        ),
        "aux.scorecard": "域纪律(评分卡):只读；≠作品意图；禁止写评分卡 SSOT。",
        "aux.experience": "域纪律(经验复盘):≠pressure_drive/beats；六格为作者复盘。",
        "aux.brief": "域纪律(简报):只读派生；改大纲/伏笔走对应写工具。",
    }
    fb = fallbacks.get(domain, "")
    return f"{fb} {ch}".strip() if fb or ch else ""


# 角色名后常见接续（停用边界），避免「沈砚的恐惧写入…」整段当 id
_CHAR_NAME_STOP = (
    r"的|之|与|和|被|把|将|给|向|在|从|为|写入|设定|档案|恐惧|欲望|外貌|弧光|"
    r"表层|锚点|性格|背景|，|,|。|、|；|;|：|:|！|!|？|\?"
)


_PSEUDO_CHAR_NAMES = frozenset({
    "设定", "本身", "档案", "关系", "列表", "卡", "人设", "扮演", "体系",
    "主角", "配角", "角色", "人物", "character", "null", "None",
})


def _is_real_character_name(name: str | None) -> bool:
    n = (name or "").strip()
    if not n or n in _PSEUDO_CHAR_NAMES:
        return False
    if n.startswith("设定") or n.lower() in ("character", "null", "none"):
        return False
    return True


def _is_real_character_focus(focus: dict[str, Any] | None) -> bool:
    """有可加载的角色专名/id 才算真叶子；否则应落到「角色」分类，禁止幽灵选中。"""
    if not focus or focus.get("type") != "character":
        return False
    label = (focus.get("label") or "").strip()
    fid = str(focus.get("id") or focus.get("ref") or "").strip()
    if not _is_real_character_name(label) and not _is_real_character_name(
        fid.split(":", 1)[-1] if ":" in fid else fid
    ):
        return False
    if fid in ("character", "role:character", "role:", "null", "None", ""):
        return False
    return True


def _extract_character_name(message: str) -> str | None:
    """从「角色沈砚的恐惧…」「主角草案：顾声」抽出专名，而非吞到句尾/伪名。"""
    text = message or ""
    patterns = (
        r"主角草案[：:\s]*([一-龥]{2,4})",
        r"([一-龥]{2,4})（暂定名）",
        r"(?:名叫|名为|叫做|定名)[：:\s]*([一-龥]{2,4})",
        r"(?:角色|人物)[·:：\s]*([一-龥A-Za-z0-9]{1,16})",
        # 「主角顾声」；避免「主角草案」把「草案」当名
        r"主角(?!草案)[·:：\s]*([一-龥]{2,4})",
        r"配角[·:：\s]*([一-龥]{2,4})",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        raw = m.group(1)
        cut = re.match(rf"^(.+?)(?:{_CHAR_NAME_STOP}|$)", raw)
        name = (cut.group(1) if cut else raw).strip()
        if not name:
            continue
        if re.fullmatch(r"[一-龥]+", name):
            name = name[:4]
        else:
            name = name[:12]
        if _is_real_character_name(name):
            return name
    return None


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
        name = _extract_character_name(message or "")
        if name:
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
                if _is_real_character_focus(focus):
                    local = (focus.get("label") or "").strip() or str(focus.get("id") or "").split(":")[-1]
                    node = {
                        "type": "character",
                        "id": focus.get("id") or f"role:{local}",
                        "ref": local,
                        "label": local,
                    }
                else:
                    # 无专名：落到设定库「角色」分类，禁止幽灵 leaf → /characters/null
                    node = {
                        "type": "codex_category",
                        "id": "cat:character",
                        "ref": "character",
                        "label": "角色",
                    }
            elif focus.get("type") == "promise":
                node = {
                    "type": "promise",
                    "id": focus.get("id") or "promise",
                    "label": focus.get("label") or "伏笔",
                }
        elif node.get("type") == "character" and not _is_real_character_focus(
            {"type": "character", "id": node.get("id"), "label": node.get("label"), "ref": node.get("ref")}
        ):
            node = {
                "type": "codex_category",
                "id": "cat:character",
                "ref": "character",
                "label": "角色",
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
        pf = prior.get("focus")
        # 角色域：仅当消息仍点名该专名才继承，避免串到旧包/烟雾 focus → 幽灵叶
        if str(entry.get("domain") or "").startswith("codex.character") and isinstance(pf, dict):
            name = str(pf.get("label") or "").strip()
            if name and name in text:
                focus = deepcopy(pf)
        else:
            focus = deepcopy(pf)

    ch = chapter
    if focus and focus.get("type") == "chapter" and focus.get("ref") is not None:
        ch = int(focus["ref"])

    write_tools = list(entry.get("write_tools") or ())
    read_tools = list(entry.get("read_tools") or ())
    required = entry.get("required_outcome") or "read_only_advice"
    channel = entry.get("channel") or "discuss"

    # 世界写 Run：须显式突变词或 force 种子
    mutation = bool(_MUTATION_RE.search(text or ""))
    force_hit = any(f in (text or "") for f in (entry.get("match_force") or ()))
    use_world_write = (
        channel == "world_write"
        and bool(write_tools)
        and (mutation or force_hit)
    )
    if channel == "prose_write":
        use_world_write = False
    intent = "write" if use_world_write else "discuss"
    if required == "write_proposal" and not use_world_write and channel == "world_write":
        required = "read_only_advice"
    if channel == "prose_write":
        intent = "write"
        required = entry.get("required_outcome") or "prose_proposal"

    # 会话草稿：具名讨论产物（非正典）
    from scribe3.orchestration import drafts as draft_store
    from scribe3.orchestration.ui_target import (
        build_ui_target,
        object_type_for_entry,
        ui_target_to_directive,
    )

    ot_hint = object_type_for_entry(entry)
    touched_drafts: list[dict[str, Any]] = []
    if text and ot_hint in (
        "character", "faction", "item", "term", "world_rule", "promise", "motif", "proposition",
    ):
        try:
            touched_drafts = draft_store.upsert_from_message(
                work or "main", text, object_type_hint=ot_hint,
            )
        except Exception:
            touched_drafts = []
    draft = touched_drafts[0] if touched_drafts else None
    if draft is None and focus and focus.get("label"):
        draft = draft_store.find_by_label(
            work or "main", str(focus.get("label")), object_type=ot_hint,
        )

    # focus_policy：discuss 默认 soft；continue/journey/write hard
    if action in ("continue",) or journey_next_domain:
        focus_policy = "hard"
    elif intent == "write" or use_world_write:
        focus_policy = "hard"
    else:
        focus_policy = "soft"

    ui_target = build_ui_target(
        entry, focus=focus, chapter=ch, draft=draft, store_ids=None,
    )
    ui = ui_target_to_directive(ui_target)
    # 保留旧 build 的 phase 增强
    if not ui.get("phase"):
        legacy = build_ui_directive(entry, focus, chapter=ch)
        if legacy.get("phase"):
            ui["phase"] = legacy["phase"]
            ui_target["phase"] = legacy["phase"]

    pkg_id = None
    if prior and prior.get("domain") == entry["domain"] and action != "switch":
        pkg_id = prior.get("id")
    if not pkg_id:
        pkg_id = f"wp_{uuid.uuid4().hex[:12]}"

    entity_ids = [d["draft_id"] for d in touched_drafts if d.get("draft_id")]
    if draft and draft.get("draft_id") and draft["draft_id"] not in entity_ids:
        entity_ids.append(draft["draft_id"])

    suffix = instruction_suffix_for_entry(entry, chapter=ch)
    ctx_pack = list(entry.get("context_pack") or ())
    pkg = {
        "id": pkg_id,
        "work": work or "main",
        "domain": entry["domain"],
        "label": entry.get("label") or entry["domain"],
        "status": "discussing",
        "intent": intent,
        "focus": focus,
        "goal": entry.get("label") or entry["domain"],
        "tool_allowlist": read_tools + write_tools,
        "write_tools": write_tools,
        "read_tools": read_tools,
        "required_outcome": required,
        "ui_target": ui_target,
        "ui_directive": ui,
        "focus_policy": focus_policy,
        "entities": entity_ids,
        "channel": channel,
        "use_world_write_run": bool(use_world_write and write_tools),
        "phase_hint": entry.get("phase_hint") or ui.get("phase"),
        "chapter": ch,
        # H1：域纪律不依赖 run phase；前端 world_write 须拼进 instructions
        "instruction_suffix": suffix,
        # H1 PR-5：声明式 context_pack（不裁剪 assemble envelope）
        "context_pack": ctx_pack,
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
            "message": "本步需要写入提案，但未调用写工具；请点「根据讨论生成写入提案」或明确要求 s3_* 写入并审批",
            "suggested_prompt": (
                f"请根据以上讨论，使用工具 "
                f"{', '.join(list(write_tools)[:4]) or '对应 s3_ 写工具'} "
                f"提交写入提案供我批准（不要只口头答应）。"
            ),
            "action": "from_discussion",
        }
        return out

    if required == "prose_proposal":
        out["status"] = "ok"  # 正文提案由流式 PROPOSAL 事件承载
        return out

    out["status"] = "ok"
    return out


def apply_ui_directive_events(
    directive: dict[str, Any] | None,
    *,
    focus_policy: str | None = None,
    ui_target: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """将 ui_target（优先）或旧 ui_directive 展开为事件。

    soft 默认不抢 selection；hard 才发合法 selection。
    """
    from scribe3.orchestration.ui_target import apply_ui_target_events, build_ui_target
    from scribe3.orchestration.catalog import get_domain as _gd

    policy = focus_policy
    target = ui_target
    if isinstance(directive, dict):
        if policy is None:
            policy = directive.get("focus_policy")
        if target is None and directive.get("ui_target"):
            target = directive["ui_target"]
        if target is None and directive.get("ui_target_kind"):
            # 已是投影后的 directive，从 kind 重建最小 target
            kind = directive.get("ui_target_kind")
            target = {
                "kind": kind,
                "entry": directive.get("entry"),
                "phase": directive.get("phase"),
                "panel": directive.get("panel"),
                "right_tab": directive.get("right_tab") or "chief",
            }
            node = directive.get("node") or {}
            if kind == "category":
                target["category"] = node.get("ref") or "character"
            elif kind == "leaf":
                target["object_type"] = node.get("type")
                target["id"] = node.get("id")
                target["label"] = node.get("label")
                target["ref"] = node.get("ref")
            elif kind == "create":
                target["object_type"] = node.get("ref") or "character"
                target["label"] = node.get("label")
                target["draft_id"] = node.get("draft_id")
    if target is None and isinstance(directive, dict):
        # 旧路径：从 node 猜 target，强制可寻址
        node = directive.get("node")
        if node and isinstance(node, dict):
            ntype = node.get("type")
            if ntype == "codex_category":
                target = {
                    "kind": "category",
                    "entry": "codex",
                    "category": node.get("ref") or "character",
                    "right_tab": directive.get("right_tab") or "chief",
                    "panel": directive.get("panel"),
                }
            elif ntype == "chapter" and node.get("ref") is not None:
                target = {
                    "kind": "leaf",
                    "entry": "manuscript",
                    "object_type": "chapter",
                    "id": node.get("id"),
                    "ref": node.get("ref"),
                    "label": node.get("label"),
                    "phase": directive.get("phase"),
                    "right_tab": "chief",
                }
            else:
                # 半截 leaf → category/stage via entry catalog if possible
                dom = None
                if ntype in ("character", "faction", "item", "term", "world_rule"):
                    dom = f"codex.{ntype}"
                elif ntype == "promise":
                    dom = "promise.plant"
                elif ntype == "motif":
                    dom = "motif.manage"
                entry = _gd(dom) if dom else None
                if entry:
                    target = build_ui_target(entry, focus=None, chapter=None, draft=None)
                else:
                    target = {"kind": "stage", "entry": directive.get("entry") or "manuscript",
                              "right_tab": directive.get("right_tab") or "chief",
                              "panel": directive.get("panel")}
        else:
            target = {
                "kind": "stage",
                "entry": directive.get("entry") or "manuscript",
                "phase": directive.get("phase"),
                "panel": directive.get("panel"),
                "right_tab": directive.get("right_tab") or "chief",
            }
    if policy is None:
        policy = "soft"
    return apply_ui_target_events(target, focus_policy=policy)

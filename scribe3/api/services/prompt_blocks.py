"""Service helpers extracted from app_impl (architecture split).

Rebound into ``app_impl`` globals via ``_rebind_services()`` for monkeypatch.
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
from queue import Empty, Full, Queue
from typing import Any, Optional

def _codex_value_repr(field, value) -> str:
    """按 CodexField.type 把值转成注入 prompt 的紧凑文本表示。"""
    if field.type == "array<object>" and isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, dict):
                continue
            sub = [f"{sf.label}={item[sf.key]}" for sf in (field.item_schema or ())
                   if item.get(sf.key) not in (None, "", [], {})]
            if sub:
                items.append("/".join(sub))
        return "、".join(items)
    if field.type == "object" and isinstance(value, dict):
        sub = [f"{sf.label}={value[sf.key]}" for sf in (field.item_schema or ())
               if value.get(sf.key) not in (None, "", [], {})]
        return "/".join(sub)
    if field.type == "array<string>" and isinstance(value, list):
        return "、".join(str(v) for v in value)
    return str(value)


def _faction_relation_summary(st, name: str, chapter: int, *, for_generation: bool) -> str:
    """该势力的实体关系摘要:perception_a/b(双方各自认知)两档都注入。

    truth(主编独知的真相)是三档可见性的第三档:`for_generation=True`(限知续写/生成
    路径)永不注入——truth 不是给生成模型看的;`for_generation=False`(作者/主编对话)
    才注入,与 codex_schema.chief_only 字段(如 secret_agenda)同级——"仅主编可见"
    的字面意思就是主编在对话里看得见,只是不能流进读者最终看到的限知正文。
    2026-07-15 修订:此前 truth 无论哪种场合都不注入,是"太钝"的旧实现,把主编自己
    也挡在外面。"""
    entity_id = f"faction:{name}"
    try:
        rows = (st.entity_relations_at(chapter, entity_id) if chapter is not None
                else st.list_entity_relations(entity_id))
    except Exception:
        raise   # U-011 fail-loud: _faction_relation_summary 关系摘要
    segs = []
    for r in rows or []:
        a, b, rt = r.get("a"), r.get("b"), r.get("relation_type")
        seg = f"{a}↔{b}[{rt}]"
        pa, pb = r.get("perception_a"), r.get("perception_b")
        if pa:
            seg += f"({a}认知:{pa})"
        if pb:
            seg += f"({b}认知:{pb})"
        if not for_generation:
            truth = r.get("truth")
            if truth:
                seg += f"(真相[仅主编可见]:{truth})"
        segs.append(seg)
    return "；".join(segs)


def _pulse_digest(st, seq: int | None) -> str:
    """主编主动化 T3(时机C):讨论模式注入的脉搏速览段(≤400 字)。
    decision 级全文(主编该主动带出的话头)+ nudge 级只计数(防唠叨);
    写作模式已有完整简报,不注入此段(防双重施压)。fail-soft:挂了返回空段。"""
    if seq is None:
        return ""
    try:
        from scribe3.pulse import chapter_pulse
        p = chapter_pulse(st, int(seq))
        decisions, nudges = [], 0
        for d in p["dimensions"]:
            for it in d["items"]:
                if it["severity"] == "decision":
                    decisions.append(it["message"])
                elif it["severity"] == "nudge":
                    nudges += 1
        if not decisions and not nudges:
            return ""
        lines = [f"\n\n## 本章脉搏速览(第{seq}章,系统确定性信号——讨论时自然带出相关项,勿逐条播报)"]
        lines += [f"- 【需决策】{m}" for m in decisions[:4]]
        if nudges:
            lines.append(f"- 另有 {nudges} 项建议级提示(作者问到再展开)")
        out, total = [], 0
        for ln in lines:
            if total + len(ln) > 600:   # 按行裁剪,不截半句(审查 P2-10)
                break
            out.append(ln)
            total += len(ln)
        return "\n".join(out)
    except Exception as e:
        logging.getLogger("scribe3").warning("pulse digest 失败(忽略): %s", e)
        return ""


# fork 延续会话注入父近窗时的边界标记(模型可见;全新会话路径绝不出现)。
# 注意:函数体用字面量(见下方),因 app_impl rebind 会把 __code__ 绑到其它 globals,
# 模块级名在 rebind 后不可见;常量仍导出供测试断言同源文案。
PARENT_SESSION_EXCERPT_BOUNDARY = "【来自上一会话的摘录，非本会话消息】"
PARENT_SESSION_TURN_TAG = "【上一会话】"


DISCUSS_MAX_MSGS = 12
DISCUSS_MAX_CHARS_EACH = 600
DISCUSS_LAST_ASSISTANT_CHARS = 2400
DISCUSS_MAX_TOTAL_CHARS = 8000
DISCUSS_SUMMARY_CHARS = 1600


def _thread_history_for_prompt(st, thread_id: str | None, *, max_msgs: int = DISCUSS_MAX_MSGS,
                               max_chars_each: int = DISCUSS_MAX_CHARS_EACH,
                               last_assistant_chars: int = DISCUSS_LAST_ASSISTANT_CHARS,
                               max_total_chars: int = DISCUSS_MAX_TOTAL_CHARS) -> list[dict]:
    """U-009:主编速答的对话记忆——把本线程最近几轮 user/assistant 留痕变成 chat messages。

    根因:hermes_complete_stream 此前每轮只发 [system, 当前一句],模型从未见过自己
    上一轮说了什么(S-001 注释自认"单遍无续接")——作者选了主编自己给的"方向C",
    主编反问"方向C是什么"。U-005 已把讨论留痕进 editorial thread,这里让**同一份留痕**
    成为模型的上下文(单一事实源:界面显示的历史 = 模型看到的历史;前端零改动)。

    预算(业界 L1 近窗原文层;字符≈token 的中文近似,刻意不引 tokenizer):
    - 普通消息截头部 max_chars_each 字(线程里有《印迹》回填的整篇世界观全案,不截撑爆 prompt);
    - **最后一条 assistant 拿大预算 last_assistant_chars,且超长时头尾各留**(P1 修正:
      作者短回复"选C"的指代对象几乎总在上一条主编消息里,而"方向C:…"这类选项/结论
      惯常在消息**尾部**——砍尾留头恰好丢掉被指代的那段,失忆复发);
    - 总预算 max_total_chars,超了从最旧开始丢。
    **必须在落本轮 user 留痕之前调用**,否则当前这句会在 history 里出现第二遍。
    U-011:取历史失败直接抛(fail-loud),不再静默回 []——那等于失忆降级悄悄复发。
    P0b:L2 已补——线程 summary(增量压缩的更早轮次)作为首条 assistant 记忆块注入,
    近窗(L1)之外的早期讨论不再彻底失忆;summary 由 _maybe_summarize_thread 后台增量生成。"""
    if not thread_id:
        return []
    try:
        thread_row = st._get_editorial_thread(thread_id) or {}
        rows = st.list_thread_messages(thread_id, limit=max_msgs)
        kept = [(r.get("role"), (r.get("text") or "").strip()) for r in rows
                if r.get("role") in ("user", "assistant") and (r.get("text") or "").strip()]
        # 会话延续(作者定义纠正 2026-07-17):新建会话是为了**界面清洁/分类,不是失忆**。
        # 有 parent 的会话(新建默认=fork 延续)在本会话消息不足近窗时,用直接父会话的
        # 尾部原文补齐——主编无缝记得上一会话聊到哪(零 LLM、无损;fork 已拷父 summary 兜早期)。
        # 全新会话(无 parent,手动"不带历史"通道)不回溯;只回溯一层,父的父由父 summary 承载。
        # 父摘录必须带边界标记,避免模型把上一会话尾部当成「本会话已说」。
        parent_id = (thread_row.get("parent_thread_id") or "").strip()
        if parent_id and len(kept) < max_msgs:
            prows = st.list_thread_messages(parent_id, limit=max_msgs - len(kept))
            pkept = [(r.get("role"), (r.get("text") or "").strip()) for r in prows
                     if r.get("role") in ("user", "assistant") and (r.get("text") or "").strip()]
            if pkept:
                # 字面量:rebind 后不可依赖本模块 globals 中的常量名
                boundary = "【来自上一会话的摘录，非本会话消息】"
                turn_tag = "【上一会话】"
                labeled: list[tuple[str, str]] = []
                for i, (role, text) in enumerate(pkept):
                    if i == 0:
                        labeled.append((role, f"{boundary}\n{text}"))
                    else:
                        labeled.append((role, f"{turn_tag}{text}"))
                kept = labeled + kept
        last_asst = max((i for i, (role, _) in enumerate(kept) if role == "assistant"),
                        default=None)
        out = []
        for i, (role, text) in enumerate(kept):
            if i == last_asst and len(text) > last_assistant_chars:
                head = text[: last_assistant_chars * 2 // 3]
                tail = text[-(last_assistant_chars // 3):]
                text = head + "\n…(中段截断)…\n" + tail
            elif i != last_asst and len(text) > max_chars_each:
                text = text[:max_chars_each] + "…(后文截断)"
            out.append({"role": role, "content": text})
        while out and sum(len(m["content"]) for m in out) > max_total_chars:
            out.pop(0)   # 从最旧开始丢,近轮优先
        # P0b L2:早期摘要块置顶(不参与近窗预算裁剪——它本身就是预算的解法)
        summ = (thread_row.get("summary") or "").strip()
        if summ:
            out.insert(0, {"role": "assistant",
                           "content": "【主编讨论早期摘要(系统压缩,更早轮次的要点)】\n" + summ[:DISCUSS_SUMMARY_CHARS]})
        return out
    except Exception:
        # U-011(作者要 fail-loud):此前"取历史失败→本轮无记忆"是静默失忆(恰是 U-009 作者
        # 投诉的症状,由降级悄悄复发)。改抛→SSE error 帧→前端内联报错,作者当场看见。
        logging.getLogger("scribe3").error("载入主编讨论历史失败", exc_info=True)
        raise


def _fact_secret_keys(f) -> set[str]:
    """命题可被 reveal_secret_ids 命中的键：id / entity_id / entity:attr 及去前缀裸名。"""
    keys: set[str] = set()
    fid = str(getattr(f, "id", "") or "").strip()
    eid = str(getattr(f, "entity_id", "") or "").strip()
    attr = str(getattr(f, "attribute", "") or "").strip()
    for raw in (fid, eid, f"{eid}:{attr}" if eid and attr else ""):
        if not raw:
            continue
        keys.add(raw)
        bare = raw.split(":", 1)[-1].strip()
        if bare:
            keys.add(bare)
    return keys


def _load_reveal_secret_ids(st, chapter: int | None) -> list[str]:
    """读章字段 reveal_secret_ids。读失败不撤防（返回空=全部仍须藏）。"""
    if chapter is None or not hasattr(st, "get_chapter"):
        return []
    try:
        from scribe3.chapter_meta_codec import coerce_chapter_json_list
        ch = st.get_chapter(int(chapter)) or {}
        return coerce_chapter_json_list(ch.get("reveal_secret_ids"))
    except Exception:
        return []


def _secret_guard_block(st, chapter: int | None = None) -> str:
    """S-002:知情主角限知泄露修复。project_frame 只屏蔽【焦点者不知道】的帧外私密,
    但焦点者是知情主角时,他自己知道的核心悬念秘密(真名/前史/印记)在帧内、且 backstory
    里也写了 → 写他视角就把该留到揭示章的秘密提前泄露给读者(知情 POV 倒灌)。
    修复:对本书 secret 命题的破绽词(leak_markers),即便视角人物知情,也硬性约束本章
    藏匿、禁明写。默认所有 secret 都藏;揭示章用字段 ``reveal_secret_ids`` 覆盖词表。
    无 secret 命题 → 空串(默认行为字节不变,旧书/无私密书零变化)。

    U-011(2026-07-15,作者要 fail-loud):删掉了"facts_at 异常即返空串"——那是把反剧透
    护栏悄悄整体撤除(fail-open),稿子照写、无人知道核心悬念已失防。现在查询失败直接【抛】,
    崩到 SSE error 帧让作者看见,而不是静默拆防线。"""
    facts = st.facts_at(chapter or 99999)
    reveal_ids = set(_load_reveal_secret_ids(st, chapter))
    markers: list[str] = []
    revealed_labels: list[str] = []
    for f in facts:
        if not getattr(f, "secret", False):
            continue
        keys = _fact_secret_keys(f)
        if reveal_ids and (keys & reveal_ids):
            label = (
                str(getattr(f, "entity_id", "") or "").strip()
                or str(getattr(f, "id", "") or "").strip()
                or "未名秘密"
            )
            if label not in revealed_labels:
                revealed_labels.append(label)
            continue
        markers.extend(getattr(f, "leak_markers", None) or [])
    markers = list(dict.fromkeys(m for m in markers if m and str(m).strip()))
    parts: list[str] = []
    if revealed_labels:
        parts.append(
            "\n\n【核心悬念·本章揭示】已批准揭开："
            + "、".join(revealed_labels[:12])
            + "。这些破绽词允许进入正文；未列出的秘密仍须藏。"
        )
    if markers:
        banned = "、".join(markers[:40])
        parts.append(
            "\n\n【核心悬念·限知纪律(本章须藏·硬约束)】本书有读者尚不该知道的核心伏线。"
            "即便视角人物自己知情,本章也**绝不明写**这些秘密——只可用身体反应、回避、物件、"
            "欲言又止来暗示,把重量压住、留到揭示章引爆。**严禁在正文出现以下破绽词**(含其明显变体):"
            f"{banned}。剧情若逼近,以『藏着不说/一闪而过/避而不答』处理,绝不点破。"
        )
    # R9：无 secret 命题时也注入侧门/炉契操作禁令，避免 secret_guard 恒空
    parts.append(
        "\n\n【工艺密】侧门开法（铜签/锁眼/拨锁/门轴）仅知情者可写步骤；"
        "不得揭破炉契全文惩罚。破绽词含：铜签、锁眼、拨锁、门轴、填炉底。"
    )
    return "".join(parts)


def _strip_preamble(text: str) -> str:
    """剥离兜底 proposal 中模型的开场解说段(对话话术),只保留散文主体。
    策略:找首个双换行分隔符(\n\n)或⟦标志前的解说段,若首段含"思路/建议/处理"等关键词则丢弃首段。
    保守:若判断不确定则保留全文(宁多勿少)。"""
    stripped = text.strip()
    # 首选:按 \n\n 段落切分,若第一段含开场标志词则丢弃
    paras = stripped.split("\n\n", 1)
    if len(paras) == 2:
        first, rest = paras
        SIGNALS = ("我的处理思路", "处理思路", "思路：", "思路:", "建议：", "建议:", "我来", "我将", "我会")
        if any(sig in first for sig in SIGNALS) and len(rest.strip()) >= _FALLBACK_MIN_CHARS:
            return rest.strip()
    # 退路:若首行含明确标志词,尝试从第二行起
    lines = stripped.splitlines()
    if lines:
        SIGNALS = ("我的处理思路", "处理思路", "思路：", "思路:", "建议：", "建议:")
        if any(sig in lines[0] for sig in SIGNALS) and len(lines) > 1:
            return "\n".join(lines[1:]).strip()
    return stripped


def _avoid_directive(st, chapter: int, lookback: int = 8, top: int = 40) -> str:
    """前 lookback 章独特措辞 → '本章避免逐字复用'系统指令(服务端确定性防跨章复读)。

    根因:单遍长程生成的"复读病"——模型跨章逐字复用自己偏爱的措辞/动作句(实测 10 章共 106 处
    跨章逐字搬运,逐章 QC 全查不到)。把前文招式喂进【系统指令】,生成时就避开,而非事后删。

    lookback=8 覆盖到全书绝大多数前文(此前 =3 时第 7-10 章看不到前段招式→复读回升);
    刻意母题/专名(奈何谷/镇煞钉/大元炼真经…)经 motif_terms 白名单排除,不进 avoid——
    它们本应复现,逼模型回避反而伤质感(乱世铜炉正以母题手法见长)。
    """
    try:
        from scribe3.critique import distinctive_phrases
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        avoid, seen = [], set()
        for c in st.recent_proses(chapter, k=lookback):
            for ph in distinctive_phrases(c.get("prose", ""), n=8, top=40, allow=allow):
                if ph not in seen and not ph.startswith("#"):
                    seen.add(ph)
                    avoid.append(ph)
        if not avoid:
            return ""
        return ("\n\n【防跨章复读·硬约束】前文已用过下列 ≥8 字措辞/动作句,本章**严禁逐字复用**——"
                "同一个意思换感官/换喻体/换节奏另写(专有名词与刻意母题可保留,忌的是动作描写与句式的偷懒重打):\n"
                + "、".join(f"「{a}」" for a in avoid[:top]))
    except Exception:
        raise   # U-011: fail-loud,取块失败上抛(_avoid_directive 防复读)


def _arc_state_block(st, focalizer: str, chapter: int) -> str:
    """构建焦点者弧光状态块:将角色在当前章节的能力/关系/性格/阶段快照注入续写 prompt。"""
    if not focalizer:
        return ""
    snap = st.char_state_at(focalizer, chapter)
    if not snap:
        return ""
    parts = []
    abilities = snap.get("abilities") or {}
    if abilities:
        parts.append("能力:" + "、".join(f"{k}={v}" for k, v in abilities.items()))
    relations = snap.get("relations") or {}
    if relations:
        parts.append("关系:" + "、".join(f"{k}={v}" for k, v in relations.items()))
    personality = snap.get("personality") or ""
    if personality:
        parts.append("性格:" + str(personality))
    phases = snap.get("arc_phases") or []
    if phases:
        parts.append("当前阶段:" + str(phases[-1].get("phase", "")))
    if not parts:
        return ""
    return (f"\n\n## 本章焦点者弧光状态(写作须贴合)\n"
            f"{focalizer}:" + ";".join(parts))


def _motif_block(st, chapter: int | None = None) -> str:
    """构建母题注入块(兼容 bt_render / 旧测)。

    写作主路径真源: `_codex_block(..., for_generation=True)` 的 heat 调度块
    (与 assemble_chapter_brief 同源 motif_craft)。本函数:有 chapter 时走 schedule。
    """
    motifs = st.list_motifs() or []
    if not motifs:
        return ""
    if chapter is not None and hasattr(st, "motif_touch_map"):
        from scribe3.motif_craft import motif_schedule_directives, generation_motif_block
        d = motif_schedule_directives(motifs, st.motif_touch_map(), int(chapter))
        block = generation_motif_block(d)
        return ("\n\n" + block) if block else ""
    lines = ["## 贯穿母题(可主动编织)"]
    for m in motifs[:5]:
        name = m.get("name") or ""
        theme = m.get("theme") or ""
        echoes = m.get("echoes") or ""
        if not name:
            continue
        entry = name
        if theme:
            entry += f":{theme}"
        if echoes:
            entry += f"（回声:{echoes}）"
        lines.append(entry)
    if len(lines) <= 1:
        return ""
    return "\n\n" + "\n".join(lines)


def _frame_block(st, focalizer: str, chapter: int) -> str:
    """限知帧注入块:将 focalizer 截至本章确知的事实喂进 prompt(私密 value 屏蔽)。
    物理隔断:帧外的事情物理上进不了这段 prompt,生成时无从写他不知道的内容。"""
    if not focalizer:
        return ""
    try:
        from scribe3.knowledge import project_frame
        frame = project_frame(st, focalizer, chapter)
        masked = _facts(frame.facts, reveal_secret=False)   # secret value → None
        # 仅保留 value 不为 None 的条目(secret=True 且未解锁的被屏蔽掉)
        visible = [f for f in masked if f.get("value") is not None]
        if not visible:
            return ""
        lines = [
            f"- {f.get('entity') or ''}|{f.get('attribute', '')}|{f.get('value', '')}"
            for f in visible[:40]
        ]
        return (
            f"\n\n## 本章焦点者【此刻确知】的事实(限知硬边界)\n"
            f"以下是 {focalizer} 截至第 {chapter} 章所知的全部。"
            "**只能据这些写他的所见所想,严禁写他不知道的事**:\n"
            + "\n".join(lines)
        )
    except Exception:
        raise   # U-011: fail-loud(_frame_block 限知帧)


def _recap_block(st, chapter: int) -> str:
    """前情注入块:上一章结尾文字 + 关键事件摘要,让主编接着写时不失忆。"""
    if chapter <= 1:
        return ""
    try:
        parts = []
        prev = st.recent_proses(chapter, k=1)   # seq < chapter 最近1章
        if prev:
            tail = (prev[0].get("prose") or "")[-300:]
            if tail:
                parts.append("上一章结尾:\n" + tail)
        evs = st.events_at(chapter - 1) or []
        if evs:
            ev_summ = "；".join(
                str(e.type or e.motivated_by_goal or "")
                for e in evs[:6] if e
            )
            if ev_summ:
                parts.append("上一章关键事件:" + ev_summ)
        if not parts:
            return ""
        return "\n\n## 前情(接着往下写,别重复已发生的)\n" + "\n\n".join(parts)
    except Exception:
        raise   # U-011: fail-loud(_recap_block 前情)


def _revelation_discipline_block(focalizer: str | None) -> str:
    """限知揭示纪律注入块(M1-①):
    focalizer 为空/None → 返回空串(作者全知章不加);
    focalizer 非空 → 返回信息揭示节制纪律块,对抗配角批发真相病。"""
    if not focalizer:
        return ""
    return (
        f"\n\n## 限知揭示纪律(本章 {focalizer} 限知视角,务必遵守)\n"
        "- 焦点者的「未知」靠现象、误判、半懂、留白逐步透出:让他看见反常的「果」却猜不到「因」,先存疑,真相延后。\n"
        "- 在场的知情者**不得**整段向焦点者陈述背景、来历、数字、门派渊源、因果真相——那是「读设定卡」,不是叙事。"
        "配角要藏话、要欲言又止、要话只说三分。\n"
        "- 凡涉及焦点者本不知的隐情,宁露冰山一角(一个眼神/一件反常的物/一句没说完的话),不可借旁人之口一次说穿。\n"
        "- 数字、年份、人数等设定细节除非剧情必须且自然,否则不写进对话。\n"
        "- **被追问/逼问时绝不倒豆子**:知情者被焦点者(或读者)逼问真相时,连续的设定性陈述**不得超过2-3句**,"
        "之后必须以回避、岔开、反问、沉默、半句没说完、或让对方误判来收住;真相按「半句+留白」一点点漏,"
        "横跨数章慢慢拼,绝不在一场戏里整段独白讲完世界观/来历/机制/操作步骤。\n"
        "- **禁止「临死/摊牌前长篇身世独白」**:身世、动机、二十年前的因果要靠前文物象暗示分散打碎,"
        "高潮场只留动作与一两句点睛,不要插叙整段往事。\n"
        "- **禁止排比抒情回环**:不可用「想起A、想起B、想起C」「至少…至少…」这类同句式排比或同一串意象的回环来堆砌、复述情绪;"
        "情绪靠一个动作、一件物象点到即止。\n"
        "- 侧门开法（铜签/锁眼/拨锁/门轴）仅知情者可写操作步骤；非知情人只许看见记号与后果。\n"
        "- 不得揭破炉契全文惩罚（头一个名字填炉底）；只写人物此刻能感到的火与怕。\n"
        "- 断刀鞘现行真：霍三刀之物，沈拾灯暂扣，还到炉前。禁止改写成爹的遗物、郭家三刀或霍不知谁拾。"
    )


def _final_reminder_full() -> str:
    """完整 11 条尾注（仅 SCRIBE3_FINAL_REMINDER_CORE=0）。"""
    return (
        "\n\n（再次强调:① 动稿必须用 ⟦PROPOSAL scope=...⟧ 围栏包正文;"
        "② 文风贴乱世铜炉志怪笔记体——古白话、冷笔、世界密度,忌现代翻译腔与用力比喻;"
        "③ 情感不可直说——禁止用概念词直陈情绪(他感到害怕/她心里很疼/他不是个坏人/这一夜永远熬不到天亮);"
        "只写动作、生理反应、物象细节,让情绪自现(show, don't tell);"
        "④ **焦点者不自悟真相**:限知视角的焦点者绝不可'忽然明白/原来…/如今他懂了'地参透他本不知道的机关/真相,"
        "只能疑惧、误判、半懂、存疑——真相留给读者从现象里自己拼,别借主角之口替读者解题;"
        "⑤ **意象不即时翻译**:写了物象/声音/动作就让它自己说话,绝不紧跟一句解释它'象征/对应/意味着'什么"
        "(写了蛐蛐叫就别补'像在数阳寿');同一意象/动作(如某物自行微动)整章至多出现 2-3 次,每次换细节,杜绝节拍器式复读;"
        "⑥ **禁止诗化分行**:不可把单字/短句独立成行来抒情造气氛(如'等谁。/ 等什么。/ 还剩多少。'),"
        "用连贯的古白话长句白描,文体前后一致；"
        "⑦ **知情焦点者不交底**:若焦点者本就知情,其叙述/内心绝不可把自己的真身、目的、结局或秘局全貌交代给读者"
        "——这些一律留作伏笔,只用动作、欲言又止、缩回的手势暗示;**禁止'焦点者碰巧偷听到反派/知情者把底牌全亮'"
        "的廉价巧合**(偷听至多留半句不祥即被打断/走远,其余靠读者拼)。知情不等于全交底,藏比说更难也更对;"
        "⑧ **单一焦点者视角不漂移**:若本章限定了焦点者(某人的限知视角),则全章严格只写此人视角与内心,"
        "绝不中途切换到他人(包括另一POV主角)的视角/想法/独白(head-hopping);别人只能作为焦点者眼中所见的对象出现,"
        "其内心一概不可直接进入。一章一个脑袋,从头到尾;"
        "⑨ **禁拟声词/单字短句煞尾**:章节结尾绝不可停在孤立的拟声词(如'咔——''笃——')或单字短句上空响,"
        "同一拟声词整章至多 1-2 次、绝不连用三遍;恐怖/悬念的收口要把劲压在**人物的身体反应或一个实物动作**上落地"
        "(如他终于没点着那火折子、手抖得捏湿了纸),用实写比喻砸下,而非靠拟声悬停。"
        "⑩ **时间/称谓连续**:更次(一更→五更)须单调递增不可倒退(开篇四更则后文只能五更/天明,不可又回三更);"
        "引号务必成对开闭,人名/称谓前后一致;"
        "⑪ **知情者之间不互相交底(禁 as-you-know-Bob)**:当两个都知情的角色对话时,绝不可为喂读者而让他们"
        "互相把彼此早已心知的机关/图谋/真相逐条讲全(典型反派交底:'有了X再配上Y他就能Z');他们只说行话、黑话、"
        "半截话、威胁与试探(彼此心知故不必说全),解释性台词一律删去——话越省读者越急,真相留在场外让读者和不知情者一样够不着。"
        "——通篇紧贴《乱世铜炉》志怪笔记体:实得密、诡得克、半懂着往下沉。）"
    )


def _final_reminder_core() -> str:
    """短核尾注（默认）。文体句可用 SCRIBE3_PROSE_STYLE 按书覆盖。"""
    import os
    style = (os.environ.get("SCRIBE3_PROSE_STYLE") or "").strip()
    style_bit = style or "文体跟本书声口，勿串书、勿翻译腔"
    return (
        "\n\n（硬纪律·短核:① ⟦PROPOSAL⟧ 围栏;"
        f"② {style_bit};"
        "③ 情感不可直说(show, don't tell);"
        "④ 限知不自悟真相;⑤ 一章单一焦点者;"
        "⑥ 禁 as-you-know 与廉价偷听交底。）"
    )


def _final_reminder() -> str:
    """末尾强化提醒。默认短核;CORE=0 才用 11 条全文。"""
    import os
    raw = (os.environ.get("SCRIBE3_FINAL_REMINDER_CORE") or "1").strip().lower()
    if raw in ("0", "false", "no", "off", "full"):
        return _final_reminder_full()
    return _final_reminder_core()


def _verbatim_deduction_fallback(source: str, character_id: str) -> str:
    """把角色在场景真相中被明确提及的句子编排成可机械验真的五栏投影。

    这是自由生成两次未通过事实门时的安全兜底：不伪造角色限知，也不让失败稿
    留在编辑器里诱导误存。来源不足时明确留白，不能拿全知叙述补齐。
    """
    import re
    # 与 deduce_helpers / app_impl 同源；本模块被 pilot 直接 import，不可依赖 app_impl 全局
    from scribe3.deduce_helpers import DEDUCTION_HEADINGS
    from scribe3.deduce_helpers import _DEDUCTION_BLANK  # noqa: PLC2701

    name = (character_id or "").split(":", 1)[-1].strip()
    sentences = [s.strip() for s in re.findall(r"[^。！？]+[。！？]?", source or "") if s.strip()]
    def subject_tail(sentence: str) -> str:
        pos = sentence.find(name)
        return sentence[pos + len(name):pos + len(name) + 48] if pos >= 0 else ""

    # 仅接受角色自身紧随其名的感知/认知/行动，不能因句子在谈论该角色就把
    # 旁白或他者的认知搬进限知栏(如“黑盐纹认得……季棠”)。
    owned = [(idx, s) for idx, s in enumerate(sentences) if name and s.find(name) >= 0]
    if not owned:
        return ""
    def with_continuation(idx: int, sentence: str) -> str:
        # “季棠……。她……”是同一角色连续表述时，合并为一个仍可逐字定位的来源片段。
        if idx + 1 < len(sentences) and sentences[idx + 1].startswith("她"):
            return sentence + sentences[idx + 1]
        return sentence

    seen = next((s for _idx, s in owned if any(k in subject_tail(s) for k in ("看", "听", "照", "触"))), owned[0][1])
    known = next((with_continuation(idx, s) for idx, s in owned if "不知道" not in subject_tail(s)
                  and any(k in subject_tail(s) for k in ("知道", "看出", "认得", "明白"))), seen)
    action = next((s for _idx, s in owned if any(k in subject_tail(s) for k in ("用", "拿", "照", "说", "做"))), seen)
    sections = (seen, known, _DEDUCTION_BLANK, action, _DEDUCTION_BLANK)
    return "\n\n".join(f"### {heading}\n{content}" for heading, content in zip(DEDUCTION_HEADINGS, sections))


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


# Note: function bodies resolve free names via rebound globals on app_impl.
def _faction_prompt_block(st, row: dict, *, chapter: int, known_ids: set,
                          secret_ids: set, fact_index: dict, for_generation: bool) -> str:
    """单个势力的结构化注入块(CX-Task 6):按注册表 in_prompt 字段拼,secret/chief_only
    字段经三档可见性门控,附该势力的关系网摘要,超预算截断。

    U-003 三档可见性(2026-07-15):`for_generation` 是本函数的核心门控参数——
    True=限知续写/生成路径(读者最终会看到的正文),False=作者/主编对话(不流进正文,
    只是编辑讨论)。三档字段各自的门控规则:
    ① `chief_only`(如 secret_agenda,codex_chief_only_keys 结构性名单):
       for_generation=True → 永不注入,不看任何 knows 边/字段标志;
       for_generation=False → 直接注入(仅主编可见=主编对话看得见)。
    ② `secret_capable` 且 `{key}_secret=True`(如 origin/artifact_operation):
       for_generation=True → 保持既有**正证式** fail-closed(白名单,非黑名单):
       作者勾了 `{key}_secret` 就已经是"此字段是秘密"的权威声明,要证的只有一件事:
       **当前焦点者知道它**。证据 = 该字段桥接命题(codex_secret_bridge.sync_faction_secrets
       生成)的 fact id 出现在 known_ids(project_frame 在该章的知情投影)里。没有
       桥接命题(fid is None)、或 fid 不在 known_ids → 拿不出证据 → 不注入。
       for_generation=False → 直接注入(作者自己标记的秘密,作者/主编对话当然看得见,
       不必再向 knows 边求证——这是本次修订相对旧版最大的行为变化:旧版不分场合都走
       knows 边判据,导致主编在纯讨论里也看不到作者自己写的势力秘密)。
    ③ 其余字段:两档都注入,不受本函数门控影响。

    ⚠️ 2026-07-14 对抗审查修(仍然有效,别退回去):②的 fail-closed 判定只认 known_ids
    正证,不再用 `_secret_fact_ids` 反证"它是不是秘密"——那是黑名单式,`_secret_fact_ids`
    fail-soft 失败退空集会让黑名单式判据变成 fail-open(不看知不知情直接注入明文)。
    (secret_ids 参数保留在签名里供调用方兼容,判定不使用。)"""
    name = row.get("name") or ""
    field_defs = {f.key: f for f in codex_fields_for("faction")}
    secret_keys = set(codex_secret_capable_keys("faction"))
    chief_keys = set(codex_chief_only_keys("faction"))
    entity_id = f"faction:{name}"
    parts = []
    for key in codex_prompt_keys("faction"):
        if key == "name":
            continue
        value = row.get(key)
        if value in (None, "", [], {}):
            continue
        if key in chief_keys:
            if for_generation:
                continue   # ① 主编独知:生成/续写路径永不注入,即便字段有值
            # for_generation=False(作者/主编对话):直接注入,落到下面的拼接
        elif key in secret_keys and row.get(codex_secret_flag_key(key)):
            if for_generation:
                fid = fact_index.get((entity_id, key))
                if fid is None or fid not in known_ids:
                    continue   # 拿不出"焦点者知情"的正面证据 → 不注入(fail-closed)
            # for_generation=False(作者/主编对话):直接注入,作者自己的秘密他看得见
        f = field_defs.get(key)
        if f is None:
            continue
        rep = _codex_value_repr(f, value)
        if rep:
            parts.append(f"{f.label}:{rep}")
    rel = _faction_relation_summary(st, name, chapter, for_generation=for_generation)
    if rel:
        parts.append(f"关系:{rel}")
    body = "；".join(parts)
    text = f"{name}（{body}）" if body else name
    if len(text) > _FACTION_PROMPT_CHAR_CAP:
        text = text[:_FACTION_PROMPT_CHAR_CAP] + "…(略)"
    return text


def _codex_block(st, reveal: bool = True, focalizer: str = "", chapter: int | None = None,
                 for_generation: bool = False, request_text: str = "") -> str:
    """注入当前书的「设定圣经」(codex:角色前史/势力/物件/术语/世界规则/母题)。
    关键:经 codex 表(非命题)建的书,_editor_system 的 facts_at 注入为空 → 主编看不到设定;
    此块直接从当前 store 的 codex 表读,确保主编(讨论/写作)看到的是**这本书**的设定,
    不依赖 MCP(MCP 网关连固定库,会串到别的书)。

    reveal=False(限知模式,focalizer 非空):对 backstory_secret 角色隐去 backstory,
    防 POV 倒灌(F-3——限知章设定圣经明文注入私密前史);reveal=True(全知)保留。
    (这一路只管角色 backstory,与下面 for_generation 管的势力 secret_capable/chief_only
    字段是两套独立机制,互不影响——见 F-3 与 U-003 各自的历史沿革。)

    CX-Task 6 + U-003 三档可见性(2026-07-15):势力段改为注册表驱动
    (codex_schema.prompt_keys('faction')),不再只有 name+ideology[:18]。字段按
    `for_generation` 分两档門控(详见 `_faction_prompt_block` 的完整规则):
    - `for_generation=True`(限知续写/生成路径,读者最终会看到的正文——**唯一生成
      入口是 _editor_write_system**,它调用本函数时恒传 True):`secret_capable`
      字段只有在"能证明当前 focalizer 知情"时才注入(project_frame 投影 fail-closed);
      `chief_only` 字段(如 secret_agenda)永不注入,即便 focalizer 知情也不例外。
    - `for_generation=False`(默认;作者/主编对话,不流进正文):`secret_capable` 与
      `chief_only` 字段都直接注入——作者自己标记的秘密、连核心层都不知道的隐秘议程,
      作者/主编讨论创作时当然都看得见,这不是"泄露给读者",是"跟作者商量剧情"。
    **fail-closed 只在 for_generation=True 时生效**:focalizer 为空(拿不到焦点角色)
    时,`secret_capable` 字段一律不注入——即便 reveal=True(作者全知)也不例外
    (对齐既有测试红线,历史上 reveal 从不放行势力 secret 字段)。"""
    def _safe(fn):
        # U-011: 删静默降级(作者要 fail-loud)。此前 6 类设定(角色/势力/物件/术语/世界规则/
        # 母题)任一取数异常→返 []→主编看到"本书无此设定",与真没有无区别,把真 bug 悄悄躲过。
        # 现在直接抛→崩到 SSE error 帧、前端亮红,作者当场看见"设定读取失败"。名字保留兼容调用点。
        return fn() or []
    def _as_text(value, *, item_limit: int = 8, char_limit: int = 160) -> str:
        """把角色公开字段压成稳定、可读、预算受控的一行。"""
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            items = [str(item).strip() for item in value if str(item).strip()]
            text = "、".join(items[:item_limit])
        else:
            text = str(value).strip()
        return text[:char_limit] + ("…" if len(text) > char_limit else "")

    def _is_active_character(character) -> bool:
        """焦点者或作者本轮明确点名的人，才注入完整公开档案。

        未点名角色仍保留旧的轻量姓名/前史摘要，避免在多人长篇里把全部履历
        粗暴塞进上下文；但一旦作者点名，字段不得只停留在 UI 和数据库。
        """
        name = str(getattr(character, "name", "") or "").strip()
        cid = str(getattr(character, "id", "") or "").strip()
        traits = (getattr(character, "traits", None) or {})
        aliases = traits.get("aliases") or []
        needles = [name, cid, *[str(alias).strip() for alias in aliases]]
        if focalizer and any(focalizer == needle for needle in needles if needle):
            return True
        return bool(request_text and any(needle and needle in request_text for needle in needles))

    parts = []
    chars = _safe(st.characters)
    if chars:
        cl = []
        # 多角色请求也要受预算保护；按存储稳定顺序取前四位。
        detailed_ids = {
            str(getattr(c, "id", ""))
            for c in [c for c in chars if _is_active_character(c)][:4]
        }
        for c in chars[:14]:
            traits = (c.traits or {}) if hasattr(c, 'traits') else {}
            bs = traits.get('backstory') or ''
            if bs and not reveal and traits.get('backstory_secret'):
                bs = ''   # 限知模式:私密前史对帧外隐去(F-3)
            if str(getattr(c, "id", "")) not in detailed_ids:
                cl.append(f"- {c.name}:{bs[:48]}" if bs else f"- {c.name}")
                continue
            fields = [
                ("别名", _as_text(traits.get("aliases"))),
                ("外观习惯", _as_text(traits.get("appearance"))),
                ("性格细节", _as_text(traits.get("personality_detail"))),
                ("性格标签", _as_text(traits.get("personality_tags"))),
                ("表层目标", _as_text(traits.get("surface_goal"))),
                ("深层需要", _as_text(traits.get("deep_need"))),
                ("恐惧", _as_text(traits.get("fear"))),
                ("内在冲突", _as_text(traits.get("internal_conflict"))),
                ("能力", _as_text(traits.get("abilities"))),
                ("弱点", _as_text(traits.get("weaknesses"))),
                ("叙事重要性", _as_text(traits.get("importance"))),
                ("首次登场", _as_text(traits.get("first_appearance"))),
            ]
            profile = "；".join(f"{label}:{value}" for label, value in fields if value)
            if bs:
                profile = f"前史:{bs[:96]}" + (f"；{profile}" if profile else "")
            cl.append(f"- {c.name}" + (f"（{profile}）" if profile else ""))
        parts.append("〔角色〕\n" + "\n".join(cl))
    facs = _safe(st.list_factions) if hasattr(st, 'list_factions') else []
    if facs:
        eff_chapter = chapter if chapter is not None else 1
        known_ids = _faction_known_fact_ids(st, focalizer, eff_chapter)
        try:
            from scribe3.context_assembler import _secret_fact_ids
            secret_ids = _secret_fact_ids(st)
        except Exception:
            raise   # U-011 fail-loud: ⚠撤销批次1的fail-open:secret判据失败必须抛,不退空集
        fact_index = _faction_bridge_fact_index(st, eff_chapter)
        facs_blocks = [_faction_prompt_block(st, f, chapter=eff_chapter, known_ids=known_ids,
                                             secret_ids=secret_ids, fact_index=fact_index,
                                             for_generation=for_generation)
                      for f in facs[:10]]
        facs_blocks = [b for b in facs_blocks if b]
        if facs_blocks:
            parts.append("〔势力〕\n" + "\n".join(f"- {b}" for b in facs_blocks))
    items = _safe(st.list_items) if hasattr(st, 'list_items') else []
    if items:
        parts.append("〔物件〕" + "；".join(f"{i.get('name')}" for i in items[:14]))
    terms = _safe(st.list_terms) if hasattr(st, 'list_terms') else []
    if terms:
        parts.append("〔术语〕" + "；".join(f"{t.get('name')}:{(t.get('definition') or '')[:16]}" for t in terms[:14]))
    rules = _safe(st.list_world_rules) if hasattr(st, 'list_world_rules') else []
    if rules:
        parts.append("〔世界规则〕" + "；".join(f"{r.get('name')}（代价:{(r.get('cost') or '—')[:14]}）" for r in rules[:10]))
    motifs = _safe(st.list_motifs) if hasattr(st, 'list_motifs') else []
    if motifs:
        if for_generation:
            # 写作真源:motif_craft heat 调度(must_echo/avoid_overuse),与 brief 同源
            from scribe3.motif_craft import motif_schedule_directives, generation_motif_block
            next_ch = int(chapter) if chapter is not None else 1
            tmap = st.motif_touch_map() if hasattr(st, "motif_touch_map") else {}
            d = motif_schedule_directives(motifs, tmap, next_ch)
            block = generation_motif_block(d)
            if block:
                parts.append(block)
            else:
                names = [m.get("name") for m in motifs[:5] if m.get("name")]
                if names:
                    parts.append("〔母题·可主动编织〕" + "；".join(names))
        else:
            names = [m.get("name") for m in motifs[:10] if m.get("name")]
            if names:
                parts.append("〔母题〕" + "；".join(names))
    return "\n".join(parts)


def _editor_system(st, focalizer: str = "", chapter: int = None,
                   for_generation: bool = False) -> str:
    """主编对话的系统提示:注入本书北极星 + 角色 + 已确立设定。

    focalizer 非空(限知章):设定块只注入焦点者帧内可见事实,secret 明文屏蔽;
    focalizer 空(作者全知视角):M6 设定三态注入(opt-in)——本书未配 injection_mode 时
      等同旧 facts_at(99999)[:28] 全量(含私密标记,行为一字不变);一旦有 fact 显式配了
      injection_mode 则启用门控(None/always→恒注入,detected 挂真实实体→须本章草料提及,
      never→不注入,世界级命题→恒注入)+ 字符预算裁剪。

    for_generation(U-003 三档可见性,2026-07-15,默认 False=作者/主编对话):单纯
    透传给 `_codex_block`,门控势力 secret_capable/chief_only 字段是否注入——本函数
    自己不做判断。**`_editor_write_system`(唯一的生成/限知续写入口)调用本函数时
    恒传 True**;`chat_stream`/`chat_agentic_stream`(作者与主编对话,不流进正文)
    不传,吃默认值 False。新增任何调用点前,先想清楚它是不是"生成落进读者看到的
    正文"——是则必须显式传 True,不传默认值就是泄密(本仓库教训:每新开一个注入点
    都泄露过一次)。"""
    intent = st.get_intent()
    chars = st.characters()
    ctx_chars = "、".join(c.name for c in chars[:14]) or "(尚无角色)"

    if focalizer:
        # 限知模式:只注入焦点者帧内可见事实,secret value 物理屏蔽
        try:
            from scribe3.knowledge import project_frame
            ch = chapter if chapter is not None else 1
            frame = project_frame(st, focalizer, ch)
            masked = _facts(frame.facts, reveal_secret=False)
            visible = [d for d in masked if d.get("value") is not None]
            lines = [
                f"- {d.get('entity', '')} · {d.get('attribute', '')}:{d.get('value', '')}"
                for d in visible[:28]
            ]
        except Exception:
            raise   # U-011 fail-loud: _editor_system 限知帧可见设定
        ctx_set = "\n".join(lines) or "(焦点者帧内暂无可见设定)"
        set_label = f"【焦点者({focalizer})帧内可见设定(限知基座,帧外私密已屏蔽)】"
    else:
        # 作者全知视角:M6 设定三态注入(opt-in,migration 056)。
        # 真·向后兼容:本书从未配 injection_mode → assemble_injection 回 fallback=True,
        #   此处直接走旧 facts[:28] 全量,旧书行为一字不变(未点名实体/世界级命题/secret 均不丢)。
        # 一旦作者显式配了 ≥1 条 injection_mode → 启用门控:None/always/世界级 恒注入,
        #   detected 挂真实实体须本章草料(synopsis/beats/scene_truth)提及,never 不注入。
        def _line(f):
            return (f"- {f.entity_id} · {f.attribute}:{f.value}"
                    + ("(私密/伏线)" if f.secret else ""))

        def _is_faction_bridge_mirror(f) -> bool:
            """这条 Fact 是不是 codex_secret_bridge 造的势力 secret 字段镜像?

            薄委托(2026-07-15,parity 修补):判据本体已下沉到
            `codex_secret_bridge.is_faction_bridge_mirror`(单一真相源)——本函数只做
            Fact→(entity_id, attribute) 的取值适配,不再自己重复"entity_id 前缀 +
            secret_capable 字段名"这条逻辑。context_assembler.py 的 canonical 候选/store
            降级两条取数路径(Gap-B 修补)现在调用的是同一个领域函数,防止此处与那里各自
            实现、渐行渐远(2026-07-15 之前两处确实各写了一份)。
            (Fact 数据类没有 source 字段、facts_at 也没 SELECT 它,否则 source=='codex_bridge'
             会是更直白的判据;等哪天 Fact 带上 source,这里可以简化。)"""
            from scribe3.codex_secret_bridge import is_faction_bridge_mirror
            return is_faction_bridge_mirror(getattr(f, "entity_id", "") or "",
                                            getattr(f, "attribute", "") or "")

        # U-003(2026-07-15,端到端接线测试撞出的真实洞,不是假设性风险):
        # codex_secret_bridge.sync_faction_secrets 把 faction 表的 secret_capable/chief_only
        # 字段(origin/secret_agenda/...)镜像成一条 proposition(secret=True),目的只是给
        # project_frame/knowledge 限知链消费——它"该不该被看见"的权威判定已经由上面的
        # _codex_block/_faction_prompt_block 三档门控负责(带正确的中文字段标签,如"隐秘议程:…")。
        # 这条通用 Facts 全知转储此前对 for_generation 一无所知:只要 focalizer 为空(省略焦点者的
        # 全知视角续写章——一种正常写作模式,不是边角场景),同一份内容就会以裸格式
        # ("- faction:X · secret_agenda:明文(私密/伏线)")二次泄露,完全绕过三档门控。
        #
        # 在 **Fact 层**(渲染之前)滤掉这些镜像,而不是事后正则渲染出来的行:lines 有两个来源
        # (fallback 走 _line,门控态走 brief._fact_inject_line),字符串过滤要赌这两个格式
        # 永远保持一致——赌不起。不影响其余(非 codex 桥接的)真实故事秘密在全知视角的既有转储
        # 行为(那是长期支持的"省略焦点者=全知叙事"写法,不在 U-003 修复范围内)。
        def _keep_fact(f) -> bool:
            return not (for_generation and _is_faction_bridge_mirror(f))

        def _keep_item(i, by_id) -> bool:
            """门控态(assemble_injection 已渲染成 text)的同款判定。

            优先用结构判据(按 id 查回 Fact);查不回来时(理论上不该发生)降级到
            字符串判据兜底——两道判据都放行才注入。宁可多丢一行全知转储,不可漏一条。"""
            if not for_generation:
                return True
            f = by_id.get(i.get("id"))
            if f is not None:
                return not _is_faction_bridge_mirror(f)
            txt = i.get("text") or ""
            return not ("faction:" in txt
                        and any(f" · {k}:" in txt for k in codex_secret_capable_keys("faction")))

        try:
            from scribe3.brief import assemble_injection
            inj = assemble_injection(st, chapter)
            if inj["fallback"]:
                lines = [_line(f) for f in inj["facts"] if _keep_fact(f)][:28]
            else:
                by_id = {getattr(f, "id", None): f for f in (inj.get("facts") or [])}
                lines = [f"- {i['text']}" for i in inj["chosen"] if _keep_item(i, by_id)]
        except Exception:
            raise   # U-011 fail-loud: M6全知转储:assemble_injection崩不退裸转储
        ctx_set = "\n".join(lines) or "(尚无设定)"
        set_label = "【已确立设定(你全知,含私密伏线)】"

    # 开着的伏笔:预注入强提醒(易忘项;母题/事件等详情留主编按需调工具查)
    promises = st.open_promises() if hasattr(st, "open_promises") else []
    rem = ""
    if promises:
        items = "；".join(
            f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:30]}" for p in promises[:6])
        rem = f"\n【⚠ 开着的承诺线·勿忘(适时推进/回收,别让它凭空消失)】{items}"
    # 素材记忆能力提示(非空库时引导主编按需经 s3_material_recall 唤起参考素材;借鉴非事实)
    mat_hint = ""
    try:
        if st.list_materials():
            mat_hint = ("\n【素材记忆库】作者备有素材记忆(研究/风格/桥段等参考),讨论或构思时"
                        "可经 s3_material_recall(query) 按当前话题唤起相关素材借鉴(借鉴非照搬),"
                        "并向作者说明为什么参考。")
    except Exception:
        raise   # U-011 fail-loud: _editor_system 素材提示块
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        f"【北极星·作品意图】读者感受:{intent['reader_feeling'] or '—'};"
        f"情感弧:{intent['emotional_arc'] or '—'};绝不背叛的红线:{intent['red_lines'] or '—'}\n"
        f"【主要角色】{ctx_chars}\n{set_label}\n{ctx_set}\n\n"
        f"【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】\n{_codex_block(st, reveal=not focalizer, focalizer=focalizer, chapter=chapter, for_generation=for_generation) or '(尚无设定)'}\n\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣上面的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    ) + rem + mat_hint + _author_prefs_block_safe()


def _editor_identity_block() -> str:
    """主编身份 + 硬协议(纯身份,零数据注入)。I1:v1 上下文段由 envelope 独占,故 v1
    只取本块作身份,避免 _editor_system 的设定/角色/伏笔注入与 envelope 的 canonical/global
    重复(facts 出现 2 次、promises 最多 3 次的注意力稀释病灶,B-3 同型)。
    与 _editor_system 共享措辞但独立成函数:_editor_system 保持原样(旧路径字节一致),
    本块把"上面的世界观与北极星"改指"下方提供的"——v1 里数据段在身份之后由 envelope 给出。"""
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣下方提供的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    )


def _write_protocol_block() -> str:
    """写作硬协议(讨论 vs 动稿)+ 文风基准(纯静态,零数据)。原 _editor_write_system 内联串
    原样抽出,供旧 _editor_write_system 与 v1 共用——不改一字,保旧路径字节一致。"""
    return (
        "\n\n你是这部小说的主编,以**作者视角**帮作者写/改这本书的手稿——作者在写一本书,"
        "不是从某个角色的受限视角做渲染。\n\n"
        "## 核心判断:讨论 vs 动稿\n"
        "- 若作者只是讨论/提问/点评/分析/给意见 → **纯文字回复,绝对禁止输出 ⟦PROPOSAL⟧ 围栏**。\n"
        "- **仅当**作者明确使用「写/改/续写/帮我写/重写/把这段…/本章这样展开」等写作动词,\n"
        "  或作者提供了角色演绎草稿请求成文时 → 先简短说一句你的处理思路,"
        "然后把**书的本章正文**放进围栏:\n"
        "  (scope 取 chapter=整章 / selection=改选中段 / append=续写接在后面)\n"
        "  ⟦PROPOSAL scope=chapter⟧\n  （书的正文，作者笔调，纯散文，不要解说）\n  ⟦/PROPOSAL⟧\n"
        "- **多候选**:当作者对某段改写要求「2-3 个候选/几个版本/不同侧重」时,**连续输出 2-3 个独立的**\n"
        "  ⟦PROPOSAL scope=selection⟧…⟦/PROPOSAL⟧ 围栏,每个是对同一段的不同改法(如:一个收紧、"
        "一个加潜台词、一个换感官切入),围栏之间可不写解说。其余情况只出一个围栏。\n\n"
        "## 写作规则\n"
        "- 若作者给了某角色的「演绎草稿」(那角色这一场的限知体验)作为素材,把它**织进**书的叙事。\n"
        "- 尊重已确立设定/伏笔/北极星意图。默认作者视角(可全知);仅当作者明确指定本章跟某焦点者的"
        "限知走时,叙事才贴该视角、不写他不知道的私密。\n\n"
        "## 文风基准:贴《乱世铜炉》(志怪笔记体)——两条硬要求\n"
        "1. **古白话语体**:句子要带旧白话的筋骨与风物实词,少用现代抽象/翻译腔。多用'端的、岂料、怎禁得、"
        "却原来、一径、约莫'这类词;状物用具体名物(花脚毛驴、青骡子、喜糕、水酒)而非笼统形容。"
        "**禁**'像散了一地的骨头''张牙舞爪'这类用力过猛的现代文学比喻——冷笔、素描,信物自身说话。\n"
        "2. **世界密度(乱世铜炉的命门)**:每章须织入与主线无关、却让世界活起来的市井风物侧笔——"
        "婚丧社戏的张罗、乡邻帮衬、打更人讨水酒、行当忌讳、节庆吃食。别一上来直奔情节;让村镇先有烟火气,"
        "妖异方有依附。范例语感(仅供体感,勿照抄字句):\n"
        "  「" + _LUANSHI_EXEMPLAR + "」\n"
        "  ——注意它如何用一整段写婚宴的杀猪宰羊、姑嫂蒸糕、打更人讨酒,世界先活,事件才落地。"
    )


def _write_revision_block() -> str:
    """M8 修订纪律(恒注入)。原 _editor_write_system 内联串原样抽出,旧/ v1 共用。"""
    return (
        "\n\n## 修订纪律\n"
        "- 改稿默认 **span 级定向**:只重写被指出的最小片段,其余一字不动;"
        "除非作者明确要求整章重写。\n"
        "- 禁止开放式整章自评重写(critique 放在大纲/节拍层;正文层只做表达增强)——"
        "自评重写会同质化、越改越平。\n"
        "- 高潮章作者要多候选时,按已有多候选围栏规则出 2-3 个独立版本。")


def inject_floor_env_enabled() -> bool:
    """SCRIBE3_INJECT_FLOOR 默认开启;测试可关以对照组装差。"""
    v = os.environ.get("SCRIBE3_INJECT_FLOOR", "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def _anti_slop_floor_block() -> str:
    """内核3 最小生产集 · 反平庸/反 AI 腔硬约束(生成时注入,非仅事后检)。

    恒注入于写路径(受 SCRIBE3_INJECT_FLOOR 门控);不宣称保证文学上限。
    """
    if not inject_floor_env_enabled():
        return ""
    return (
        "\n\n## 生产下限·反平庸(强制)\n"
        "- **禁 AI 腔**:禁「不禁/竟然/心中一动/目光深邃/意味深长/仿佛在诉说」等空转修饰;"
        "禁排比三连堆砌与段末升华金句。\n"
        "- **身体先于标签**:情绪走微动作/物象/沉默,不直说「他感到…」。\n"
        "- **世界密度**:至少留一处与主线弱相关的市井/器物侧笔,忌情节直奔。\n"
        "- **信息冰山**:设定只露必要的 1/8;读者能推的不写明。\n"
        "- **伏笔诚实**:开着的承诺线须推进或回收,禁止无声蒸发。\n"
        "- 以上为下限纪律,好小说的文学上限仍由作者终裁。"
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


def _outline_block(st, chapter: int, focalizer: str = "") -> str:
    """B-3 根治:把本章五阶段的「大纲(synopsis)+ 节拍(beats)」注入写作 prompt。
    此前 synopsis/beats 从不注入 → 模型被指令"据大纲/节拍写"却从未收到内容。
    仿 _deduction_block:空(无 synopsis 且无 beats)→ 返回空串(默认行为不变)。
    Task8审查必修2:限知章(focalizer 非空)补一句限知免责——大纲是作者视角,
      帧外私密不得由焦点者知晓或道破(对齐 _deduction_block 的全知/限知分离)。
    方案B任务10:情节点字数预算契约(oh-story artifact-protocols.md 移植)——
      本函数是 chat_write(GET/POST)唯一共用的组装点,前端"大纲/节拍" tab 与
      "草稿" tab 都映射到同一 phase 经此函数注入(节拍无独立生成端点,由
      前端/主编对话驱动),故契约段落点选在此处而非另开端点:
      · 生成/调整节拍时的密度+预算标注规范(始终附带,覆盖节拍生成时刻);
      · 写草稿时"按预算分配笔墨"的执行要求(仅当已有节拍内容时附带)。
      确定性校验见 brief.validate_beat_budgets(后续可接进节拍保存端点)。
    自带前导 \\n\\n(与 _motif_block/_recap_block 同约定,caller 直接 += 即可)。"""
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
    parts.append(
        "情节点字数预算契约:生成/调整节拍时,每个情节点须标注「密度:密|疏」与"
        "「字数预算:N字」(密≥250字,慢镜头爽点400-600字,疏≈40字过场);"
        "全部情节点预算求和必须落在[章目标字数, ×1.1]区间;"
        "节拍列表末尾输出一行「预算合计:X字」。"
    )
    # 方案B任务11:章节定位六型 + 卷级张弛基线(oh-story outline-structure-theory.md:282-289 移植)——
    # 大纲/节拍标注补充"这一章在全书张弛节奏里的定位",供 brief.find_tension_monotony 卷级检测消费。
    parts.append(
        "章节定位标注:生成/调整大纲或节拍时,每章须标注「压力级:1-5」与"
        "「chapter_role:高压|推进|修炼|关系回收|低压|信息整理」;"
        "低压/关系回收章允许无显性爽点,但须保留追读拉力(未解悬念或未了结的关系张力仍须推进);"
        "均衡基线非硬配额,严肃志怪基调整体取克制档,但同一 chapter_role 不得连排超过 2-3 章。"
    )
    # 方案B任务13b:反转标注规范(oh-story reversal-toolkit.md 7类反转)——
    # 若本章含反转,节拍须显式标注 reversal_type/setup_clues/reveal_position_pct 三字段,
    # 供 critique.build_reversal_rubric_prompt 机检(铺垫是否≥3处/揭示是否<300字/
    # 有无凭空新信息/揭示位置是否落在50-85%最佳区间)。
    parts.append(
        "反转标注规范:若本章含反转,节拍须标注「reversal_type:七类之一(身份反转/"
        "动机反转/因果反转/立场反转/信息差反转/时间线反转/道德反转)」+「setup_clues」"
        "(≥3 处铺垫,须引用前文对应片段)+「reveal_position_pct」(建议落在 50-85 区间)。"
    )
    return "\n\n" + "\n".join(parts)


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


def _brief_must_sections_write_block(st, chapter: int, focalizer: str = "") -> str:
    """生产写路径:章前简报**操作必达段**(伏笔/开环/心跳/弧光/因果/stale)。

    单源 assemble_chapter_brief;刻意剔除 purpose/lessons(已由
    _purpose_and_lessons_write_block 内联)与 injection 回显(codex 块另注),
    避免双份圣经/双份目的合同。空操作段 → 空串。fail-soft:组装故障不阻断写作。"""
    try:
        from scribe3.brief import assemble_chapter_brief, render_brief
        brief = assemble_chapter_brief(st, int(chapter), focalizer=focalizer or "")
        sec = dict(brief.get("sections") or {})
        sec.pop("purpose", None)
        sec.pop("lessons", None)
        sec.pop("injection", None)
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
            return ""
        text = (render_brief(sec) or "").strip()
        if not text or text == "## 本章创作简报(章前组装,遵守但不复述)":
            return ""
        return "\n\n" + text
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "写路径 brief 必达段注入失败(fail-soft): %s", e)
        return ""


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
    except Exception:
        pass
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
        focalizer_input = (f"作者指定本章跟随焦点者 {focalizer} 的限知视角:"
                           "贴该角色所知所感写,别写他不知道的私密。")
    else:
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
    # 阶段2可把这块迁入 envelope 的专属 source(参与预算/溯源);现阶段用 instructions
    # 块保证与旧链字节级同语义,不额外造轮子。
    codex_input = (
        "\n\n【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】\n"
        + (_codex_block(st, reveal=not focalizer, focalizer=focalizer,
                        chapter=chapter, for_generation=True,
                        request_text=request_text) or "(尚无设定)")
        + "\n"
    )
    prefix += _domain_input(
        f"work:{work or 'main'}:codex", "codex", codex_input,
    )
    # 统一上下文段(替代旧 avoid/voice/arc/motif/frame/recap/tail/outline/material 散点拼装)
    snap = _write_snapshot(st, chapter=chapter, focalizer=focalizer,
                           phase=phase, work=work)
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
        rendered = prefix
        env_text = render_envelope_text(envelope)
        if env_text:
            rendered += "\n\n" + env_text
        rendered += _domain_input(
            f"chapter:{chapter}:seed-words", "seed_words",
            _soak_block(seed_words),
        )
        craft = build_craft_block(st.list_craft_rules() or None, short_mode=short_mode)
        if craft:
            rendered += _domain_input(
                f"work:{work or 'main'}:craft", "craft", "\n\n" + craft,
            )
        rendered += _domain_input(
            f"chapter:{chapter}:phase-role", "phase_role",
            _phase_role_block(phase),
        )
        rendered += _domain_input(
            f"chapter:{chapter}:avoid", "avoid",
            _avoid_directive(st, chapter),
        )
        rendered += _domain_input(
            f"chapter:{chapter}:revelation-discipline", "revelation_discipline",
            _revelation_discipline_block(focalizer),
        )
        rendered += _focalizer_sincerity_block()
        rendered += _domain_input(
            f"chapter:{chapter}:purpose", "purpose",
            _purpose_workflow_block(st, chapter, with_tools, work),
        )
        # 章前简报操作必达段(伏笔/开环/心跳/弧光/因果)——与 discussion 旧链
        # _editor_write_system 同源 assemble_chapter_brief,v1 此前漏挂。
        rendered += _domain_input(
            f"chapter:{chapter}:brief-must", "brief_must",
            _brief_must_sections_write_block(st, chapter, focalizer=focalizer or ""),
        )
        # 跨书作者偏好(USER.md)——讨论栈走 _editor_system;写栈此前只身份块,漏挂。
        rendered += _domain_input(
            f"work:{work or 'main'}:author-prefs", "author_prefs",
            _author_prefs_block_safe(),
        )
        # 焦点者声音锚 + 登场对白速记(helper 早有,生产写链未调用)。
        rendered += _domain_input(
            f"chapter:{chapter}:voice-anchor", "voice_anchor",
            _voice_anchor_block(st, focalizer or ""),
        )
        normalized_phase = (phase or "").strip().lower()
        if normalized_phase in ("draft", "final"):
            # 参考作品原文永不进入生成输入：这里只消费作者批准后的安全技法投影。
            # 每个指纹独立登记 supplemental source，供 Manifest 与使用账本追溯。
            from scribe3.reference_craft import approved_craft_briefs
            reference_craft_briefs = approved_craft_briefs(st, str(work or "main"))
            for brief in reference_craft_briefs:
                rendered += _domain_input(
                    f"reference_fingerprint:{brief.fingerprint_id}", "reference_craft",
                    brief.text,
                )
            for ordinal, (source_id, source_kind, text) in enumerate(
                _deduction_context_segments(st, chapter)
            ):
                rendered += _domain_input(
                    source_id, source_kind,
                    ("\n\n" if ordinal == 0 else "") + text,
                )
            # draft/final:门控素材参考(借鉴非事实);llm=None → 确定性强度排序,不阻塞网关。
            rendered += _domain_input(
                f"chapter:{chapter}:material-recall", "material_recall",
                _material_recall_block(st, chapter, phase=normalized_phase,
                                       focalizer=focalizer or "", llm=None,
                                       request_text=request_text),
            )
        rendered += _final_reminder()
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
            rendered += _domain_input(
                f"chapter:{chapter}:scene-truth", "scene_truth", scene_truth_input,
            )
        if extra_instructions:
            rendered += _domain_input(
                f"chapter:{chapter}:request-constraint", "request_constraint",
                "\n\n" + extra_instructions,
            )
        return rendered, tuple(supplemental_sources)

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
        forbidden_source_kinds=(),
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
    if reference_craft_briefs:
        from scribe3.quality.store import QualityStore
        QualityStore(st).record_reference_craft_use(
            work=str(work or "main"), chapter=int(chapter),
            request_id=compiled.request.request_id,
            manifest_id=compiled.manifest.manifest_hash,
            briefs=reference_craft_briefs,
        )
    # Task 16 最后一厘米:检索真发生(retriever 非 None)且前端带了会话绑定
    # (memory_trace_ctx 有 session_id + revision)时,落 memory_trace 给 ContextInspector。
    # 键用前端真实会话(前端 Inspector 查同一 session/revision,天然对齐);无绑定的调用方
    # (loop / 存量)→ 不落(诚实 404)。best-effort:落库失败只告警,绝不阻断写作主链路
    # (与 chat_message 同纪律);秘密屏蔽复用 _save_write_memory_trace 内 build/save 双重 mask。
    _mtc = memory_trace_ctx or {}
    if (_retrieval_out is not None and _mtc.get("context_session_id")
            and _mtc.get("context_revision") is not None):
        _result = _retrieval_out.get("result")
        if _result is not None:
            try:
                _save_write_memory_trace(
                    st, snap=snap, envelope=envelope, result=_result,
                    query=retrieval_query, work=work, ctx=_mtc)
            except Exception:
                logging.getLogger("scribe3").warning(
                    "memory_trace 落库失败(忽略,不阻断写作)", exc_info=True)
    return compiled.rendered_input


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


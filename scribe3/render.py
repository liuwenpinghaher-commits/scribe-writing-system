"""叙述层 · fabula ∩ 知识帧 → sjuzhet。

范式核心:build_render_prompt 只用 focalizer 知识帧里的事实拼 prompt。
帧外事实不进 prompt → POV 泄露结构性消失。

设计哲学(v2):
- 锚定+自由+后置校验,而非规则堆叠
- prompt 只保留:限知帧(结构保证) + 事件(情节骨架) + 风格锚(1段原文)
- 写作规则从 prompt 移除(soak 已处理角色声音,QC 后置处理质量问题)
- 让 LLM 把注意力花在创作上,不是合规上
"""
from __future__ import annotations

from typing import Callable

from scribe3.knowledge import project_frame
from scribe3.ontology import World

# 精简到极致:只保留结构性的限知+输出格式,不塞写作技巧规则
_CONSTRAINT = (
    "## 要求\n"
    "- 限知:只写视角角色此刻知道的事。\n"
    "- 直接输出正文,纯散文,不要解释或元叙述。"
)


def _facts_block(world: World, frame, foc_name: str) -> list[str]:
    """事实块:仅 focalizer 知识帧内的事实进入(限知核心)。"""
    lines = ["", f"## {foc_name} 此刻所知(这是你能用的全部事实,帧外之事他不知道):",
             "<facts>"]
    if frame.facts:
        for f in frame.facts:
            subj = world.entity(f.entity_id)
            nm = subj.name if subj else f.entity_id
            safe = f.value.replace("<", "‹").replace(">", "›")
            lines.append(f"- {nm}·{f.attribute}:{safe}")
    else:
        lines.append("-(空:此视角暂无已知事实)")
    lines.append("</facts>")
    return lines


def _events_block(world: World, story_at: int, frame, focalizer: str) -> list[str]:
    """事件块:列出本章事件及参与者,只展示 focalizer 可感知的参与者(限知门控 P33)。"""
    frame_entities = {f.entity_id for f in frame.facts} | {focalizer}
    lines = ["", "## 本章要发生的事件(按此渲染):"]
    for ev in world.events_at(story_at):
        visible = [v for v in ev.participants.values()
                   if v in frame_entities]
        if not visible:
            continue  # 焦点者不可感知的事件跳过
        parts = "、".join(
            (world.entity(v).name if world.entity(v) else v) for v in visible
        )
        where = world.entity(ev.location).name if ev.location and world.entity(ev.location) else (ev.location or "")
        lines.append(f"- [{ev.type}] {parts}" + (f" 于{where}" if where else ""))
    return lines


def _voice_block(foc_name: str, voice: dict | None) -> list[str]:
    """声音块:focalizer 的独白/叙述语气(不破限知)。"""
    if not voice:
        return []
    _VK = {"free": "自由独白", "pressure": "压力独白", "relation": "关系独白", "narration": "叙述语气"}
    vlines = [f"- {_VK[k]}:{voice[k]}" for k in ("free", "pressure", "relation", "narration") if voice.get(k)]
    if vlines:
        return ["", f"## 你({foc_name})的声音(保持一致,别串味)"] + vlines
    return []


def build_render_prompt(world: World, chapter: int, focalizer: str,
                        craft_block: str = "", soak_result: dict | None = None,
                        voice: dict | None = None,
                        story_at: int | None = None, frame_at: int | None = None,
                        style_anchor: str = "") -> str:
    """按 focalizer 的知识帧拼限知渲染 prompt。
    
    v2 设计:锚定+自由+后置校验
    - 限知帧(结构保证):focalizer 不知道的不进 prompt
    - 事件(情节骨架):本章要发生什么
    - 风格锚(1段原文):让模型自然模仿文风,而非背50条规则
    - soak(角色声音):浸泡产出的情感曲线/种子词
    - craft_block:默认不注入(v2移除规则堆叠),保留参数向后兼容
    """
    story_at = story_at if story_at is not None else chapter
    frame_at = frame_at if frame_at is not None else story_at
    frame = project_frame(world, focalizer, frame_at)
    foc = world.entity(focalizer)
    foc_name = foc.name if foc else focalizer

    lines = [f"# 第{chapter}章 · 限知视角:{foc_name}",
             f"以【{foc_name}】的视角写这一章。直接写正文。"]
    if story_at != chapter:
        lines.append(f"(这是闪回:渲染第{story_at}章发生的事)")

    # 风格锚:1段原文让模型自然模仿,替代50条写作规则
    if style_anchor:
        lines += ["", "## 风格参考(模仿这个文风,不要抄内容):", style_anchor]

    lines += _facts_block(world, frame, foc_name)
    lines += _events_block(world, story_at, frame, focalizer)
    lines += _voice_block(foc_name, voice)

    # soak:角色声音+情感曲线(soak已处理"进入角色",不需要在主prompt重复)
    if soak_result and (soak_result.get("seed_words") or soak_result.get("emotion_arc")):
        seeds = "、".join(soak_result.get("seed_words") or [])
        arc = soak_result.get("emotion_arc") or ""
        turn = soak_result.get("turn") or ""
        lines += ["", "## 本场情感(据此把握情绪,不要写进正文)"]
        if arc:
            lines.append(f"- 情感曲线:{arc}")
        if turn:
            lines.append(f"- 转折:{turn}")
        if seeds:
            lines.append(f"- 种子词:{seeds}")

    # craft_block:v2默认不注入(规则堆叠降低创作质量),保留参数兼容
    if craft_block:
        lines += ["", craft_block]

    lines += ["", _CONSTRAINT]
    return "\n".join(lines)


def render(world: World, chapter: int, focalizer: str,
           complete_fn: Callable[..., str] | None = None,
           max_tokens: int | None = None, timeout: float | None = None,
           soak: bool = True,
           story_at: int | None = None, frame_at: int | None = None,
           target_words: int = 0,
           style_anchor: str = "",
           use_craft: bool = False) -> str:
    """渲染一章一视角:浸泡→限知 prompt(含风格锚)→分段渲染→拼接。
    
    v2: 锚定+自由+后置校验
    - style_anchor: 1段原文做风格锚(替代50条写作规则)
    - use_craft: 是否注入craft_block(默认False,规则堆叠降低创作质量)
    - target_words=0: 单次渲染(向后兼容测试)
    - target_words>0: 分段续写至目标字数
    """
    story_at = story_at if story_at is not None else chapter
    frame_at = frame_at if frame_at is not None else story_at
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete

    # craft_block: v2默认不注入
    craft_block = ""
    if use_craft:
        from scribe3.craft import build_craft_block
        rules = world.list_craft_rules() if hasattr(world, "list_craft_rules") else None
        craft_block = build_craft_block(rules)

    soak_result = None
    if soak:
        from scribe3.soak import soak as run_soak
        try:
            soak_result = run_soak(world, frame_at, focalizer, complete_fn)
        except Exception as e:
            import logging
            logging.getLogger("scribe3.render").warning(
                "soak 失败,降级为无浸泡渲染(focalizer=%s @%s): %s", focalizer, frame_at, e)
            soak_result = None
    voice = world.latest_voice_samples(focalizer, frame_at) if hasattr(world, "latest_voice_samples") else None
    prompt = build_render_prompt(world, chapter, focalizer,
                                 craft_block=craft_block, soak_result=soak_result, voice=voice,
                                 story_at=story_at, frame_at=frame_at,
                                 style_anchor=style_anchor)
    kw: dict = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if timeout is not None:
        kw["timeout"] = timeout

    # 单次渲染
    first_pass = complete_fn(prompt, **kw)
    wc = len("".join(first_pass.split()))

    # 如果单次已达目标字数或未设置目标,直接返回
    if target_words <= 0 or wc >= target_words:
        return first_pass

    # 分段渲染:将第一次输出作为开头,继续续写直到达标
    import logging
    _log = logging.getLogger("scribe3.render")
    _log.info("单次渲染 %d 字 < 目标 %d 字,启动分段续写", wc, target_words)

    segments = [first_pass]
    max_segments = 5
    for seg_idx in range(max_segments):
        current_total = sum(len("".join(s.split())) for s in segments)
        if current_total >= target_words:
            break

        prev_text = "\n\n".join(segments)
        prev_tail = prev_text[-500:] if len(prev_text) > 500 else prev_text

        # 续写:简洁上下文,不堆规则——让LLM自由创作
        continue_prompt = (
            f"你正在写第{chapter}章。前文结尾:\n{prev_tail}\n\n"
            f"继续写,推进情节。不要重复前文。直接输出正文。"
        )
        next_seg = complete_fn(continue_prompt, **kw)
        if not next_seg or len(next_seg.strip()) < 50:
            _log.warning("续写第%d段返回过短(%d字),停止", seg_idx + 1, len(next_seg or ''))
            break
        segments.append(next_seg)
        seg_wc = len("".join(next_seg.split()))
        _log.info("续写第%d段: +%d字 (累计 %d/%d)",
                  seg_idx + 1, seg_wc, current_total + seg_wc, target_words)

    return "\n\n".join(segments)

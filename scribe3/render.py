"""叙述层 · fabula ∩ 知识帧 → sjuzhet。

build_render_prompt 是范式的工程落点:它【只】用 focalizer 知识帧里的事实拼 prompt。
focalizer 不知道的私密事实不在帧里 → 不进 prompt → 模型物理上写不出 → POV 泄露结构性消失。
render() 把这个限知 prompt 喂给注入的 complete_fn(默认走 Hermes)。渲染层只读,不回写世界。
"""
from __future__ import annotations

from typing import Callable

from scribe3.knowledge import project_frame
from scribe3.ontology import World

_CONSTRAINT = (
    "## 渲染纪律\n"
    "- 限知第三人称:只写视角角色【此刻知道】的事;他不知道的,一个字都不能出现。\n"
    "- show 不 tell;去 AI 腔(禁\"嘴角勾起/眼底闪过/命运的齿轮\");冷笔动作收尾,不喊升华口号。\n"
    "- 按给定事件渲染,不得偷塞别的情节(不双高潮、不偷跑后续章)。\n"
    "- 用了力量必付代价。\n"
    "## 输出格式(硬要求)\n"
    "- 直接输出小说正文本身,从故事的第一句开始写,到最后一句结束。\n"
    "- 不要任何元叙述/说明/汇报:禁止出现\"已完成/我写了/以…视角/文字已保存/本章\"之类的话,"
    "不要复述或解释上面的指令,不要写章节号或标题。整段回复就是纯散文。"
)


def _events_at(world: World, chapter: int):
    return world.events_at(chapter)   # World 与 SurrealStore 都提供此方法(鸭子兼容)


def build_render_prompt(world: World, chapter: int, focalizer: str,
                        craft_block: str = "", soak_result: dict | None = None) -> str:
    """按 focalizer 的知识帧拼限知渲染 prompt。帧外事实绝不出现。
    craft_block(引擎层+题材层)与 soak 种子词插在事件之后、渲染纪律之前。"""
    frame = project_frame(world, focalizer, chapter)
    foc = world.entity(focalizer)
    foc_name = foc.name if foc else focalizer

    lines = [f"# 把下面的事件写成小说正文(限知视角:{foc_name})",
             f"以【{foc_name}】的限知视角,把下列既定事件写成一段小说散文。直接写正文,别解释。",
             "",
             f"## {foc_name} 此刻所知(这是你能用的全部事实,帧外之事他不知道):"]
    if frame.facts:
        for f in frame.facts:
            subj = world.entity(f.entity_id)
            nm = subj.name if subj else f.entity_id
            lines.append(f"- {nm}·{f.attribute}:{f.value}")
    else:
        lines.append("-(空:此视角暂无已知事实)")

    lines += ["", "## 本章要发生的事件(按此渲染):"]
    for ev in _events_at(world, chapter):
        parts = "、".join(
            (world.entity(v).name if world.entity(v) else v)
            for v in ev.participants.values()
        )
        where = world.entity(ev.location).name if ev.location and world.entity(ev.location) else (ev.location or "")
        lines.append(f"- [{ev.type}] {parts}" + (f" 于{where}" if where else ""))

    if craft_block:
        lines += ["", craft_block]
    if soak_result and (soak_result.get("seed_words") or soak_result.get("emotion_arc")):
        seeds = "、".join(soak_result.get("seed_words") or [])
        arc = soak_result.get("emotion_arc") or ""
        turn = soak_result.get("turn") or ""
        lines += ["", "## 本场情感设计(浸泡产出,据此把握情绪曲线,不要写进正文)"]
        if arc:
            lines.append(f"- 情感曲线:{arc}")
        if turn:
            lines.append(f"- 转折时刻:{turn}")
        if seeds:
            lines.append(f"- 情绪种子词:{seeds}")

    lines += ["", _CONSTRAINT]
    return "\n".join(lines)


def render(world: World, chapter: int, focalizer: str,
           complete_fn: Callable[..., str] | None = None,
           max_tokens: int | None = None, timeout: float | None = None,
           soak: bool = True) -> str:
    """渲染一章一视角:浸泡→限知 prompt(含 craft)→complete_fn→sjuzhet。默认走 Hermes。"""
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    from scribe3.craft import build_craft_block
    rules = world.list_craft_rules() if hasattr(world, "list_craft_rules") else None
    craft_block = build_craft_block(rules)
    soak_result = None
    if soak:
        from scribe3.soak import soak as run_soak
        soak_result = run_soak(world, chapter, focalizer, complete_fn)
    prompt = build_render_prompt(world, chapter, focalizer,
                                 craft_block=craft_block, soak_result=soak_result)
    kw: dict = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if timeout is not None:
        kw["timeout"] = timeout
    return complete_fn(prompt, **kw)

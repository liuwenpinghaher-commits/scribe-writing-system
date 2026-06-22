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
    "- 用了力量必付代价。"
)


def _events_at(world: World, chapter: int):
    return [ev for ev in world.events.values() if ev.story_time == chapter]


def build_render_prompt(world: World, chapter: int, focalizer: str) -> str:
    """按 focalizer 的知识帧拼限知渲染 prompt。帧外事实绝不出现。"""
    frame = project_frame(world, focalizer, chapter)
    foc = world.entity(focalizer)
    foc_name = foc.name if foc else focalizer

    lines = [f"# 渲染本章(限知视角:{foc_name})",
             f"你是这本小说的渲染器。以【{foc_name}】的限知视角,把下列既定事件渲染成散文。",
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

    lines += ["", _CONSTRAINT]
    return "\n".join(lines)


def render(world: World, chapter: int, focalizer: str,
           complete_fn: Callable[..., str] | None = None,
           max_tokens: int | None = None, timeout: float | None = None) -> str:
    """渲染一章一视角:限知 prompt → complete_fn → sjuzhet。默认走 Hermes。"""
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    prompt = build_render_prompt(world, chapter, focalizer)
    kw: dict = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if timeout is not None:
        kw["timeout"] = timeout
    return complete_fn(prompt, **kw)

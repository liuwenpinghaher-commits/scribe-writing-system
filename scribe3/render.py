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


def _facts_block(world: World, frame, foc_name: str) -> list[str]:
    """事实块:仅 focalizer 知识帧内的事实进入(限知核心)。"""
    lines = ["", f"## {foc_name} 此刻所知(这是你能用的全部事实,帧外之事他不知道):"]
    if frame.facts:
        for f in frame.facts:
            subj = world.entity(f.entity_id)
            nm = subj.name if subj else f.entity_id
            lines.append(f"- {nm}·{f.attribute}:{f.value}")
    else:
        lines.append("-(空:此视角暂无已知事实)")
    return lines


def _events_block(world: World, story_at: int) -> list[str]:
    """事件块:列出本章要发生的事件及其参与者。"""
    lines = ["", "## 本章要发生的事件(按此渲染):"]
    for ev in world.events_at(story_at):
        parts = "、".join(
            (world.entity(v).name if world.entity(v) else v)
            for v in ev.participants.values()
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
                        story_at: int | None = None, frame_at: int | None = None) -> str:
    """按 focalizer 的知识帧拼限知渲染 prompt。帧外事实绝不出现。
    craft_block(引擎层+题材层)与 soak 种子词插在事件之后、渲染纪律之前。
    声音样本(focalizer 自己的,不破限知)同样插在事件之后、渲染纪律之前。
    story_at/frame_at 默认回退 chapter(线性);story_at 选事件故事时间、frame_at 选知识帧时间。
    沉浸式闪回 frame_at 默认=story_at(角色只知那时);回忆式显式传 frame_at=chapter。"""
    story_at = story_at if story_at is not None else chapter
    frame_at = frame_at if frame_at is not None else story_at
    frame = project_frame(world, focalizer, frame_at)
    foc = world.entity(focalizer)
    foc_name = foc.name if foc else focalizer

    lines = [f"# 把下面的事件写成小说正文(限知视角:{foc_name})",
             f"以【{foc_name}】的限知视角,把下列既定事件写成一段小说散文。直接写正文,别解释。"]
    if story_at != chapter:
        lines.append(f"## ⚠ 这是插叙/闪回:渲染第{story_at}章发生的事(非当前叙事时间,别当线性推进)")

    lines += _facts_block(world, frame, foc_name)
    lines += _events_block(world, story_at)
    lines += _voice_block(foc_name, voice)

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
           soak: bool = True,
           story_at: int | None = None, frame_at: int | None = None) -> str:
    """渲染一章一视角:浸泡→限知 prompt(含 craft)→complete_fn→sjuzhet。默认走 Hermes。
    story_at/frame_at 默认回退 chapter(线性);非线性时 soak/voice/知识帧都跟 frame_at(那时状态)。"""
    story_at = story_at if story_at is not None else chapter
    frame_at = frame_at if frame_at is not None else story_at
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    from scribe3.craft import build_craft_block
    rules = world.list_craft_rules() if hasattr(world, "list_craft_rules") else None
    craft_block = build_craft_block(rules)
    soak_result = None
    if soak:
        from scribe3.soak import soak as run_soak
        soak_result = run_soak(world, frame_at, focalizer, complete_fn)
    voice = world.latest_voice_samples(focalizer, frame_at) if hasattr(world, "latest_voice_samples") else None
    prompt = build_render_prompt(world, chapter, focalizer,
                                 craft_block=craft_block, soak_result=soak_result, voice=voice,
                                 story_at=story_at, frame_at=frame_at)
    kw: dict = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if timeout is not None:
        kw["timeout"] = timeout
    return complete_fn(prompt, **kw)

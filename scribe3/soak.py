"""浸泡前置 · 渲染前让模型以 focalizer 身份进入状态,产出情感曲线种子词。
意识流文本本身丢弃(只为进入角色),只解析 CoT 结构化产出带进正式渲染。
受限知约束:soak prompt 只用 focalizer 知识帧内的事实。"""
from __future__ import annotations

import json
import logging
import re

_log = logging.getLogger("scribe3.soak")

from scribe3.knowledge import project_frame


def build_soak_prompt(world, chapter: int, focalizer: str) -> str:
    foc = world.entity(focalizer)
    name = foc.name if foc else focalizer
    frame = project_frame(world, focalizer, chapter)
    facts = "、".join(f"{f.attribute}:{f.value}" for f in frame.facts[:8]) or "(此刻暂无已知)"
    return (
        f"你就是【{name}】。写前浸泡一次(产出只为进入状态,不进正文)。\n"
        f"你此刻只知道:{facts}——别人的私密心思你一概不知,不得提及。\n"
        "先在心里以你的身份过一遍这一场,然后只输出一行 JSON:\n"
        '{"emotion_arc":"本场情感 起点→终点(各3-5字)",'
        '"turn":"情感转折发生的具体时刻(一句话)",'
        '"seed_words":["本场情绪种子词3-5个"]}'
    )


def parse_soak(reply: str) -> dict:
    m = re.search(r"\{.*\}", reply or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            return {"emotion_arc": (d.get("emotion_arc") or "").strip(),
                    "turn": (d.get("turn") or "").strip(),
                    "seed_words": [str(x) for x in (d.get("seed_words") or [])][:5]}
        except Exception as e:
            _log.warning("parse_soak 失败,浸泡降级为空: %s | reply[:120]=%r", e, (reply or "")[:120])
    return {"emotion_arc": "", "turn": "", "seed_words": []}


def soak(world, chapter: int, focalizer: str, complete_fn) -> dict:
    """渲染前置:调一次模型拿情感曲线种子词。complete_fn(prompt)->str。

    ⚠ 休眠(P2-15,2026-07-04):本函数是 7 引擎之一(浸泡/craft.ENGINES)且有测试
    (test_soak/test_craft),但当前无生产调用方——app._soak_block 只消费"外部预先传入的
    seed_words",不自动触发 soak()(见 app.py:1794 注释),也无 /soak 端点。属"已建成待接线
    的能力",非死码;保留(勿删整模块),接线时补端点或写作前置调用。"""
    return parse_soak(complete_fn(build_soak_prompt(world, chapter, focalizer)))

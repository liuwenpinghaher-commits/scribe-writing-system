"""写作层移植 Phase3:生成管线 + 确定性记忆 rollup。

generate_continue:build_writing_context(确定性富注入)+ 续写 prompt + 可注入 LLM(complete_fn)。
complete_fn 在 Phase4 接 Hermes(主编/provider),单测注入 fake 即可。

rollup_global:章梗概**确定性拼接**(超长保留首章+最近若干章 verbatim),
不经 LLM 压缩 —— 这是对旧底座 rollup_global 漂移坑(把"孙辈"压成"独子"、凭空造人名)的根治。
"""
from __future__ import annotations

from .writing import build_writing_context


def build_chapter_prompt(ctx: str, seq: int, instruction: str = "",
                         prev: str = "", target: int = 850) -> str:
    """续写 prompt:吃 instruction(steer)+ prev(连贯)+ target(控长);前置 _writing_context。"""
    parts = [f"这是这本书第 {seq} 章。请往下写约 {target} 字正文,与上下文自然衔接,"
             "保持同一叙事声音、文白相间的笔法与各人物既定声音;"
             "只输出新写的正文本身,不要重复已写内容,不要任何解释或前后缀。"]
    if (instruction or "").strip():
        parts.append("\n【本节要写(务必照此推进情节,不要另起炉灶)】\n" + instruction.strip())
    if (prev or "").strip():
        parts.append("\n【本章已写正文(承接它继续,语气连贯,不要重写)】\n" + prev)
    body = "\n".join(parts)
    return (ctx + "\n\n" + body) if ctx else body


def generate_continue(d, work: str, seq: int, instruction: str, complete_fn,
                      target: int = 850, prev: str = "") -> str:
    """生成第 seq 章一节正文。complete_fn(prompt)->str 由调用方注入(Phase4=Hermes)。"""
    ctx = build_writing_context(d, work, seq)
    prompt = build_chapter_prompt(ctx, seq, instruction, prev, target)
    return complete_fn(prompt)


def rollup_global(d, work: str, cap: int = 1800) -> str:
    """把各章梗概**确定性拼接**成全书主线记忆并落库。超长则保首章(设定基底)+最近6章,
    全程 verbatim、不 LLM 压缩 —— 根治身份血缘漂移。身份铁律另靠角色档案 verbatim 注入。"""
    mems = d.list_chapter_memories(work)
    if not mems:
        return ""
    joined = "\n".join(f"第{m['seq']}章:{m['text']}" for m in mems)
    if len(joined) > cap:
        head = f"第{mems[0]['seq']}章:{mems[0]['text']}"
        tail = "\n".join(f"第{m['seq']}章:{m['text']}" for m in mems[-6:])
        joined = head + "\n…(中段略)…\n" + tail
    d.set_global_memory(work, joined)
    return joined

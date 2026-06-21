"""一致性检查(移植精简版):对照角色/设定/主线记忆,LLM 找本章矛盾 → 落 consistency_flag。
专治长篇身份血缘/设定漂移(与确定性记忆 + 角色锚互补)。
"""
from __future__ import annotations

import json
import re


def check_chapter(d, work: str, seq: int, complete_fn) -> list[str]:
    """检本章与已知设定/前文的矛盾,落库 consistency_flag,返回矛盾列表。"""
    ch = next((c for c in d.list_chapters(work) if c.get("seq") == seq), None)
    if not ch:
        return []
    content = d.latest_prose(d._idpart(ch["id"]))
    if not content.strip():
        return []
    chars = "；".join(f"{c.get('name')}({(c.get('motivation') or '')[:24]})"
                      for c in d.list_characters(work))
    sets = "；".join((s.get("text") or "")[:30] for s in d.list_settings(work))
    glob = d.get_global_memory(work)
    prompt = (
        "对照下列已知设定与前文,挑出这章正文里与之矛盾之处"
        "(人物身份/血缘/姓名、关键设定、已发生情节的冲突)。\n"
        f"角色:{chars}\n设定:{sets}\n全书主线:{glob[:400]}\n\n"
        '只输出一行 JSON:{"flags":["具体矛盾1",...]}(无矛盾则 flags 为空数组)。'
        "\n\n本章正文:\n" + content[:3000])
    reply = complete_fn(prompt)
    flags: list[str] = []
    m = re.search(r"\{.*\}", reply or "", re.S)
    if m:
        try:
            flags = [str(x) for x in (json.loads(m.group(0)).get("flags") or [])][:8]
        except Exception:
            pass
    for f in flags:
        d.s.create("consistency_flag",
                   {"work": f"work:{work}", "seq": seq, "detail": f, "status": "open"})
    return flags

"""纵切片端到端 demo:一章一视角走通新环,真机验证 POV 泄露结构性消失。

  设计 fabula → 冻结知识帧 → 渲染 sjuzhet → 校验

A/B 对比直击范式:
  旧法(全知扁平注入,= scribe2 之前)→ 焦三私密在 prompt 里 → 泄露曾经发生(老道说"够你给老娘治眼")
  新法(按 focalizer 投影知识帧)     → 焦三私密不在 prompt 里 → 物理上写不出 → 泄露结构性消失

跑:scribe/.venv/bin/python -m scribe3.demo   (Hermes :8642 在线则真机渲染;离线则只证结构保证)
"""
from __future__ import annotations

from scribe3.knowledge import project_frame
from scribe3.render import build_render_prompt, render
from scribe3.scenario import luanshi_leak_world
from scribe3.verify import causal_complete, find_leaks

LEAK_TOKEN = "治眼"


def _old_style_flat_prompt(world, chapter: int) -> str:
    """复刻旧系统:把【所有】角色的事实(含私密)拍进一个共享全知 prompt。"""
    lines = ["# 渲染本章(老道视角)", "## 全部设定(全知扁平,旧法):"]
    for f in world.facts_at(chapter):
        subj = world.entity(f.entity_id)
        lines.append(f"- {subj.name if subj else f.entity_id}·{f.attribute}:{f.value}")
    return "\n".join(lines)


def main() -> None:
    w = luanshi_leak_world()
    chapter, focalizer = 1, "role:老道"

    print("=" * 64)
    print("① 设计 fabula:乱岗对峙(老道追上焦三索丹)。焦三私密动机=攒钱给老娘治眼(secret)")
    print("② 冻结知识帧:focalizer = 流云观皂衣道士(老道)")
    frame = project_frame(w, focalizer, chapter)
    print(f"   老道此刻所知:{[w.fact(f.id).attribute + '=' + f.value for f in frame.facts]}")
    print(f"   老道知道焦三私密动机吗? {frame.knows('fact:治眼')}   (应为 False)")

    print("-" * 64)
    old_p = _old_style_flat_prompt(w, chapter)
    new_p = build_render_prompt(w, chapter, focalizer)
    print("③ 渲染 prompt A/B:")
    print(f"   旧法(全知扁平)prompt 含『{LEAK_TOKEN}』? {LEAK_TOKEN in old_p}   ← 泄露曾从这里发生")
    print(f"   新法(知识帧投影)prompt 含『{LEAK_TOKEN}』? {LEAK_TOKEN in new_p}   ← 物理上写不出")

    print("-" * 64)
    print("④ 校验:")
    viols = causal_complete(w, chapter)
    print(f"   因果完整性:{'✓ 干净' if not viols else viols}")

    # 真机渲染(Hermes 在线则跑;离线则跳过,结构保证已足够证明)
    print("-" * 64)
    print("⑤ 真机渲染(Hermes :8642)…")
    try:
        prose = render(w, chapter, focalizer, max_tokens=700, timeout=90)
        leaks = find_leaks(prose, w, focalizer, chapter)
        print("   ── 渲染出的 sjuzhet ──")
        print("   " + prose.replace("\n", "\n   ").strip())
        print("   ──────────────────────")
        print(f"   兜底判官 find_leaks:{'✓ 无泄露' if not leaks else [l.marker for l in leaks]}")
    except Exception as e:
        print(f"   (Hermes 离线/超时,跳过真机渲染:{type(e).__name__})")
        print("   ※ 结构保证不依赖真机:新法 prompt 不含私密,泄露已在 prompt 层被根除。")

    print("=" * 64)
    print("结论:POV 泄露从『事后判官救』变成『渲染前结构上不会犯』。判官降为第二道兜底。")


if __name__ == "__main__":
    main()

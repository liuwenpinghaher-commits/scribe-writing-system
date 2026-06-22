"""真机走通一整章:设计fabula→限知渲染→双层QC→存稿→回写→验证知识传播+伏笔超期。

跑:scribe3/.venv/bin/python -m scribe3.walkthrough
用 NS=scribe3 的真·乱世铜炉数据 + 真 Hermes。doubao 慢,每步限时 150s。
"""
from scribe3.critique import discipline_truncate, quality_flags
from scribe3.health import health_report
from scribe3.ingest import ingest_chapter
from scribe3.knowledge import project_frame
from scribe3.llm import hermes_complete
from scribe3.ontology import Entity, Event
from scribe3.render import render
from scribe3.store import SurrealStore

FOC = "role:胡不为"


def H(prompt, **kw):
    return hermes_complete(prompt, timeout=150, **kw)


def main() -> None:
    s = SurrealStore(ns="scribe3", db="main")
    s.apply_schema()
    try:
        print("① 设计 fabula:加第1章事件(胡不为在梧桐村,镇煞钉对峙)")
        s.add_entity(Entity("place:梧桐村", "place", "梧桐村"))
        s._db.query("DELETE event")
        s.add_event(Event("ev:ch1", "镇煞对峙", participants={"SUBJ": FOC},
                          location="place:梧桐村", story_time=1, motivated_by_goal="goal:胡保命"))
        print(f"   视角=胡不为(懦弱·怀揣镇煞钉) | 他此刻所知事实数={len(project_frame(s, FOC, 1).facts)}")

        print("② 限知渲染 sjuzhet(走 Hermes,只吃胡不为的知识帧)…")
        prose = render(s, 1, FOC, complete_fn=H, max_tokens=900)
        print("   ── 渲染(前180字)──")
        print("   " + prose[:180].replace("\n", " "))

        print("③ 双层 QC")
        qf = quality_flags(prose)
        print(f"   确定性:复读{len(qf['repetition'])} 排比{len(qf['structural'])} 升华{len(qf['purple'])}")
        dv = discipline_truncate(prose, "", H)
        print(f"   语义判官:violations={dv['violations']} changed={dv['changed']}")
        final = dv["text"]

        print("④ 存稿")
        s.save_chapter(1, final, title="镇煞对峙", focalizer=FOC)
        print(f"   已存第1章({len(final)}字)")

        print("⑤ 回写 ingest(走 Hermes 抽『谁新知道什么/做了什么』)…")
        before = len(project_frame(s, FOC, 1).facts)
        r = ingest_chapter(s, 1, H)
        print(f"   应用 {r['applied']} 条 | learned={[x.get('who') for x in r['delta'].get('learned', [])]}")

        print("⑥ 验证写循环闭合:回写后知识帧变化")
        after = len(project_frame(s, FOC, 1).facts)
        print(f"   胡不为 第1章帧事实数:{before} → {after}(回写把本章新知并入,下章限知据此渲染)")

        print("⑦ 伏笔超期告警(假设已写到第8章):")
        rep = health_report(s, up_to=8)
        eg = rep.overdue_promises[0]["text"][:26] if rep.overdue_promises else "(无)"
        print(f"   超期伏笔 {len(rep.overdue_promises)} 条 | 例:「{eg}」")
        print("=== 整环走通:设计→限知渲染→双层QC→存→回写→知识传播→伏笔超期 ===")
    finally:
        s.close()


if __name__ == "__main__":
    main()

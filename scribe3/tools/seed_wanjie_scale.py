#!/usr/bin/env python3
"""把《万界概率战争》的既有种子灌进一个本地库，作为 200 章规模化试验的底座。

为什么不走 humanrun 主编通道：那条路每条设定都要人审批，是**正典**写入的正确姿势；
这里灌的是**试验库**，目的是拿到一个 200 章规模的实物来看，不是给作者出书。
所以直连 store 公开 API（不碰 _query / _execute_write，遵守分层锁）。

用法：
    # 先起一个本地 Surreal（数据在 /tmp，不进 git）
    surreal start --bind 127.0.0.1:8123 --user root --pass root rocksdb:/tmp/wanjie-db/data

    scribe3/.venv/bin/python -m scribe3.tools.seed_wanjie_scale --db wanjie_scale
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))

from scribe3.ontology import Entity, Fact  # noqa: E402
from scribe3.store import SurrealStore  # noqa: E402

import humanrun_wanjie_seed as seed  # noqa: E402


def seed_intent(st) -> None:
    """北极星与红线。红线是硬约束，后面每一章的信息调度都不许违反。"""
    st.set_intent({
        "north_star": seed.NORTH_STAR,
        "reader_feeling": "读完要留下的是——保护和监禁原来是同一件事。"
                          "月球挡住宇宙噪音，同时把人钉死在一种现实里。",
        "emotional_arc": "从隐瞒体温，到被迫按回碎片，再到欠下一笔还不起的账。",
        "red_lines": "不美化把人当观测样本这件事\n"
                     "不让柳岸青看见场核坐标\n"
                     "不提前拆穿炉认主与帝的真名",
        "who_pays": "柳岸青",
        "axis_terms": "体温,倒计时,观测,场核",
        "clock_start": "华山成核当夜",
        "clock_end": "腕内倒计时归零 / 第三条路落地",
    })


def seed_characters(st) -> int:
    """幂等：rule/item/term/faction 的 store 方法本身是 upsert，这几张不是，得自己挡。"""
    for c in seed.CHARS:
        if st.entity(c["oid"]):
            continue
        traits = {k: c[k] for k in (
            "importance", "appearance", "personality_detail", "surface_goal",
            "deep_need", "internal_conflict", "fear", "abilities", "weaknesses",
            "backstory", "aliases", "gender", "first_appearance",
        ) if c.get(k) is not None}
        st.add_entity(Entity(c["oid"], "character", c["name"], traits=traits))
        anchors = {k: c[k] for k in ("ghost", "lie", "truth", "want", "need", "arc_type")
                   if c.get(k)}
        if anchors:
            try:
                st.set_char_anchors(c["oid"], anchors)
            except Exception as e:
                print(f"  ! 弧光锚 {c['name']}: {e}")
    return len(seed.CHARS)


def seed_relations(st) -> int:
    have = {(r.get("src"), r.get("dst"), r.get("relation"))
            for r in (st.relations_at(99999) or [])}
    for r in seed.RELATIONS:
        key = (r["src"].split(":")[-1], r["dst"].split(":")[-1], r["relation"])
        if key in have:
            continue
        st.add_character_relation(r["src"], r["dst"], r["relation"],
                                  since_chapter=r.get("since", 1), note=r.get("note"))
    return len(seed.RELATIONS)


def seed_rules(st) -> int:
    for r in seed.RULES:
        st.add_world_rule(
            r["name"], r["category"], source=r.get("source"),
            capabilities=r.get("capabilities"), cost=r.get("cost"),
            limitations=r.get("limitations"), exceptions=r.get("exceptions"),
            established_chapter=1)
    return len(seed.RULES)


def seed_facts(st) -> int:
    for fid, entity_id, attribute, value, vf in seed.FACTS:
        st.add_fact(Fact(id=fid, entity_id=entity_id, attribute=attribute,
                         value=value, valid_from=vf))
    return len(seed.FACTS)


def seed_factions(st) -> int:
    """种子里 goals 是字符串列表，schema 要的是 {phase,target,status}（codex_schema:124）。"""
    for f in seed.FACTIONS:
        payload = {k: v for k, v in f.items() if k != "name"}
        goals = payload.get("goals")
        if goals and isinstance(goals[0], str):
            payload["goals"] = [
                {"phase": f"卷一 · {i + 1}", "target": g, "status": "ongoing"}
                for i, g in enumerate(goals)]
        st.add_faction(f["name"], first_mention_chapter=1, **payload)
    return len(seed.FACTIONS)


def seed_items(st) -> int:
    for it in seed.ITEMS:
        st.add_item(it["name"], description=it.get("description"),
                    current_owner=it.get("current_owner"),
                    special_properties=it.get("special_properties"),
                    first_chapter=1)
    return len(seed.ITEMS)


def seed_terms(st) -> int:
    for name, cat, definition in seed.TERMS:
        st.add_term(name, category=cat, definition=definition, first_mention_chapter=1)
    return len(seed.TERMS)


def seed_motifs(st) -> int:
    have = {(m.get("name") or "") for m in (st.list_motifs() or [])}
    for m in seed.MOTIFS:
        if m["name"] in have:
            continue
        st.add_motif(m["name"], theme=m.get("theme", ""), echoes=m.get("echoes", ""),
                     unfolding=m.get("unfolding", ""), tier="book")
    return len(seed.MOTIFS)


def seed_promises(st) -> int:
    have = {(p.get("text") or "") for p in (st.list_promises() or [])}
    for p in seed.PROMISES:
        if p["text"] in have:
            continue
        st.plant_promise(p["text"], p["setup"], tier=p.get("tier", "chapter"),
                         resolution=p.get("resolution", ""))
    return len(seed.PROMISES)


def seed_volumes_chapters(st) -> tuple[int, int]:
    by_title = {v.get("title"): (v.get("id") or v.get("volume_id"))
                for v in (st.list_volumes() or [])}
    vol_ids = []
    for v in seed.VOLUMES:
        vid = by_title.get(v["title"])
        vol_ids.append(vid or st.add_volume(v["title"], sort_order=v["sort_order"],
                                            intro=v.get("intro")))
    for ch in seed.CHAPTERS:
        st.save_chapter(ch["seq"], "", title=ch["title"], focalizer=seed.FOCALIZER)
        fields = {"synopsis": ch["synopsis"]}
        vi = ch.get("vol")
        if vi is not None and vi < len(vol_ids):
            fields["volume"] = vol_ids[vi]
        st.update_chapter_meta(ch["seq"], fields)
    return len(vol_ids), len(seed.CHAPTERS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8123/rpc")
    ap.add_argument("--db", default="wanjie_scale")
    args = ap.parse_args()

    st = SurrealStore(url=args.url, ns="scribe3", db=args.db)
    st.apply_schema()
    print(f"连上 {args.url} db={args.db}\n")

    seed_intent(st)
    print("意图（北极星 / 红线 / 轴心词）已写")
    for label, fn in (("角色", seed_characters), ("角色关系", seed_relations),
                      ("世界规则", seed_rules), ("事实命题", seed_facts),
                      ("势力", seed_factions), ("物件", seed_items),
                      ("术语", seed_terms), ("母题", seed_motifs),
                      ("伏笔", seed_promises)):
        print(f"{label}: {fn(st)}")
    nv, nc = seed_volumes_chapters(st)
    print(f"卷: {nv}\n章壳: {nc}")

    print("\n" + "=" * 46)
    c = st.setting_completeness()
    print(f"完整度自评 {c['completeness_score']}  缺: {c['missing_dimensions'] or '无'}")
    print(f"角色 {c['total_chars']} / 规则 {c['total_rules']} / 势力 {c['total_factions']} / "
          f"地点 {c['total_places']} / 事实 {c['total_facts']} / 母题 {c['total_motifs']}")
    st.close()


if __name__ == "__main__":
    main()

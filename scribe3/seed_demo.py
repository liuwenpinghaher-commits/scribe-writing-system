"""Demo 种子：世界本体 + 可写第 1 章（五阶段可打开）。

跑::

  python -m scribe3.seed_demo
  python -m scribe3.seed_demo --db main --force-chapter

世界：焦三/老道乱岗泄露场景（additive；已存在 id 则 fail-soft）。
可写章：synopsis / beats / scene_truth / draft / prose / focalizer。
"""
from __future__ import annotations

import argparse
import logging
import sys

_log = logging.getLogger("scribe3.seed_demo")

CHAPTER_TITLE = "乱岗夜雨"
FOCALIZER = "role:焦三"

SYNOPSIS = (
    "暴雨乱岗，皂衣老道拦住焦三索要丹药。"
    "stakes:若今夜交不出丹，焦三走不出乱葬岗；"
    "若硬闯，怕把身后未了的事一齐赔进去。"
    "章末钩：雨幕里多一双不该有的脚印。"
)

BEATS = [
    {
        "goal": "焦三想借雨势尽快离开乱岗",
        "conflict": "老道拦路索丹，话里话外逼近",
        "text": "Goal：脱身。Conflict：老道拦住去路。雨大，火折子灭了。",
    },
    {
        "goal": "老道要焦三交出丹",
        "conflict": "焦三不认、不交，只能周旋",
        "text": "Goal：索丹。Conflict：焦三咬死不知。泥浆没过靴腰。",
    },
    {
        "goal": "双方试探底线",
        "conflict": "谁先动刀谁破局",
        "text": "僵持。远处坟头有动静。章末钩：第二双脚印。",
    },
]

SCENE_TRUTH = (
    "乱葬岗暴雨夜。流云观皂衣道士（老道）在坟堆间堵住焦三，索要一枚丹。"
    "焦三拒交、拒认。公开事实：雨大、地滑、无人见证。"
    "（限知：焦三私密动机不在此真相句中写给老道可知。）"
)

INVOLVED = ["role:焦三", "role:老道"]

DRAFT = (
    "【草稿】焦三脚下一滑，火折子灭了。老道蓑衣贴在肩上，问丹在哪。"
    "焦三说不知道。雨声大过说话声。"
)

PROSE = """乱葬岗的雨是从天缝里挤下来的，砸在焦三肩上，砸在无名坟头上，一样响。

火折子灭了。他蹲下去摸，指节碰到湿泥，泥里有人的靴尖。

「丹。」皂衣老道站在雨里，声音不大，「交出来。」

焦三抬头。雨顺着老道帽檐往下淌，淌进领口，老道也不躲。

「什么丹。」

「你袋里那枚。」老道往前半步，泥浆咕啾一声，「别装。」

焦三把空着手举起来给雨看。袖口湿透，没有鼓包。老道盯着他的袖口，又盯着他的眼。

远处坟堆之间，雨帘忽然被什么东西划开——像多了一双脚，踩在不该有脚印的地方。

焦三听见自己喉咙里发干。他说：「我没有。」

老道没接话。雨还在下。
"""

NARRATIVE_DRIVE = {
    "engine_type": "event",
    "dramatic_question": "焦三今夜能否带着丹活着离开乱岗？",
    "stakes": "交丹则空，不交则走不出岗",
    "end_hook": "雨里多出一双脚印",
}


def seed_world(store) -> dict:
    """灌泄露场景世界。已存在记录 fail-soft。"""
    from scribe3.scenario import luanshi_leak_world
    from scribe3.ontology import Fact, KnowledgeEdge

    out = {"world": False, "reader_fact": False}
    try:
        luanshi_leak_world(store)
        out["world"] = True
    except Exception as e:
        _log.warning("luanshi_leak_world soft: %s", e)
        out["world_error"] = str(e)[:160]
    try:
        store.add_fact(
            Fact("fact:追索", "role:老道", "身份", "流云观追索者", valid_from=1, secret=True)
        )
        store.add_knowledge(KnowledgeEdge("reader", "fact:追索", since_chapter=1))
        out["reader_fact"] = True
    except Exception as e:
        _log.warning("reader fact soft: %s", e)
        out["reader_error"] = str(e)[:160]
    return out


def _active_chapter_count(store) -> int:
    try:
        rows = store._query(
            "SELECT count() AS n FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL;"
        ) or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
    except Exception:
        pass
    return 0


def seed_writable_chapter(store, *, force: bool = False) -> dict:
    """确保至少一章可写：大纲/节拍/演绎/草稿/正文。"""
    out: dict = {"seq": None, "created": False, "updated": False}
    n = _active_chapter_count(store)
    seq = 1
    if n == 0:
        # 固定 seq=1，避免 max_chapter 幽灵号导致跳到 2
        store.save_chapter(1, "", title=CHAPTER_TITLE, focalizer=None)
        seq = 1
        out["created"] = True
    else:
        # 取最小 seq 作为演示章
        rows = store._query(
            "SELECT seq FROM chapter "
            "WHERE archived = NONE OR archived != true ORDER BY seq LIMIT 1;"
        ) or []
        if rows:
            seq = int(rows[0]["seq"])
        ch0 = store.get_chapter(seq)
        if ch0 and (ch0.get("prose") or "").strip() and not force:
            out["seq"] = seq
            out["skipped"] = "chapter_exists_use_force_chapter"
            out["title"] = ch0.get("title")
            return out

    out["seq"] = seq
    # 正文 + 视角（focalizer 走 save_chapter）
    store.save_chapter(seq, PROSE.strip(), title=CHAPTER_TITLE, focalizer=FOCALIZER)
    store.save_chapter_draft(seq, DRAFT)
    ok = store.update_chapter_meta(
        seq,
        {
            "title": CHAPTER_TITLE,
            "synopsis": SYNOPSIS,
            "beats": BEATS,
            "scene_truth": SCENE_TRUTH,
            "involved_characters": INVOLVED,
            "narrative_drive": NARRATIVE_DRIVE,
        },
    )
    out["updated"] = bool(ok)
    ch = store.get_chapter(seq) or {}
    out["verify"] = {
        "title": ch.get("title"),
        "focalizer": ch.get("focalizer"),
        "has_synopsis": bool((ch.get("synopsis") or "").strip()),
        "beats_n": len(ch.get("beats") or []) if isinstance(ch.get("beats"), list) else 0,
        "has_scene_truth": bool((ch.get("scene_truth") or "").strip()),
        "has_draft": bool((ch.get("draft") or "").strip()),
        "prose_len": len(ch.get("prose") or ""),
        "involved_n": len(ch.get("involved_characters") or [])
        if isinstance(ch.get("involved_characters"), list)
        else 0,
    }
    return out


def run(db: str = "main", *, force_chapter: bool = False, ns: str = "scribe3") -> dict:
    from scribe3.store import SurrealStore

    st = SurrealStore(ns=ns, db=db)
    try:
        st.apply_schema()
        world = seed_world(st)
        chapter = seed_writable_chapter(st, force=force_chapter)
        report = {"db": db, "ns": ns, "world": world, "chapter": chapter}
        ch_ok = bool(
            chapter.get("seq")
            and (
                chapter.get("skipped")
                or (
                    (chapter.get("verify") or {}).get("has_synopsis")
                    and (chapter.get("verify") or {}).get("prose_len", 0) > 50
                )
            )
        )
        report["ok"] = ch_ok
        return report
    finally:
        try:
            st.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed demo world + writable chapter")
    p.add_argument("--db", default="main")
    p.add_argument("--ns", default="scribe3")
    p.add_argument(
        "--force-chapter",
        action="store_true",
        help="已有章也覆写 synopsis/beats/draft/prose",
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(args.db, force_chapter=args.force_chapter, ns=args.ns)
    import json

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("ok"):
        print(
            f"✓ db={args.db} 世界+可写章就绪 seq={report.get('chapter', {}).get('seq')}。"
            "开写作台即可进第 1 章五阶段。"
        )
        return 0
    print("✗ 可写章种子未完整", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

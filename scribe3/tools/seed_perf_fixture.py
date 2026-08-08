#!/usr/bin/env python3
"""合成负载（可销毁）· Surreal 3.2.4 热路径 / 检索基线用。

用法（backend 容器或 PYTHONPATH 含 app）:
  python -m scribe3.tools.seed_perf_fixture              # 写入 works.perf_s32
  python -m scribe3.tools.seed_perf_fixture --destroy    # 删库
  python -m scribe3.tools.seed_perf_fixture --n-prop 20 --n-mem 10

默认规模偏小，避免 demo 上 embed 过久。
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

_log = logging.getLogger("scribe3.tools.seed_perf")

WORK = "perf_s32"


def _seed(n_char: int, n_prop: int, n_ch: int, n_mem: int) -> dict:
    from scribe3.memory_capture import MemoryCapture, turn_event
    from scribe3.ontology import Entity, Fact
    from scribe3.store import SurrealStore, create_work, list_works

    t0 = time.perf_counter()
    slugs = {w.get("slug") for w in (list_works() or []) if isinstance(w, dict)}
    if WORK not in slugs:
        create_work(title="S32 perf fixture (disposable)", slug=WORK)
    st = SurrealStore(db=WORK)
    st.apply_schema()

    # characters
    for i in range(n_char):
        name = f"测角{i:03d}"
        try:
            st.add_entity(Entity(
                id=f"role:{name}", kind="character", name=name,
                traits={"importance": "minor" if i else "protagonist"},
            ))
        except Exception as e:
            if "already" not in str(e).lower() and "exists" not in str(e).lower():
                _log.warning("char %s: %s", name, e)

    # propositions + embedding via add_fact
    for i in range(n_prop):
        fid = f"fact:perf_p{i:04d}"
        text = f"测角{i % max(n_char, 1):03d}在第{i % 10}章持有信物「玉佩{i}」，与血玉铜炉传说有关。"
        try:
            st.add_fact(Fact(
                id=fid,
                entity_id=f"role:测角{(i % max(n_char, 1)):03d}",
                attribute="prop",
                value=text,
                valid_from=max(1, i % 10),
            ))
        except Exception as e:
            _log.warning("fact %s: %s", fid, e)

    # chapters (prose short)
    for seq in range(1, n_ch + 1):
        prose = (
            f"第{seq}章。测角000走进乱岗，铜炉寒气逼人。"
            f"这一章发生了关于玉佩与密室的事，序号{seq}。"
        )
        try:
            st.save_chapter(seq, prose, title=f"perf-ch-{seq}", embed=False)
        except TypeError:
            try:
                st.save_chapter(seq, prose, title=f"perf-ch-{seq}")
            except Exception as e:
                _log.warning("chapter %s: %s", seq, e)
        except Exception as e:
            _log.warning("chapter %s: %s", seq, e)

    # memory_item via capture (experience, not canonical)
    cap = MemoryCapture(st)
    mem_ok = 0
    for i in range(n_mem):
        text = (
            f"写作备忘{i}: 下一场戏侧重密室机关与测角000的犹豫，"
            f"不要提前揭示铜炉来历。线索{i}。"
        )
        ev = turn_event(
            text,
            event_id=f"perf-turn-{i:04d}",
            work=WORK,
            thread_id="perf-thread",
            classification="episodic",
            known_from=1,
        )
        r = cap.capture_event(ev)
        if r.get("status") == "complete":
            mem_ok += 1

    def _count(table: str) -> int:
        rows = st._query(f"SELECT count() AS c FROM {table} GROUP ALL")
        if not rows:
            return 0
        return int(rows[0].get("c") or 0)

    stats = {
        "work": WORK,
        "characters": _count("character"),
        "propositions": _count("proposition"),
        "chapters": _count("chapter"),
        "memory_item": _count("memory_item"),
        "mem_capture_ok": mem_ok,
        "seconds": round(time.perf_counter() - t0, 2),
    }
    return stats


def _destroy() -> None:
    from scribe3.store.core_preamble import _reg_conn, list_works

    # remove registry row + database if API exists
    try:
        from scribe3.store import delete_work  # type: ignore
        delete_work(WORK)
        print({"destroyed": WORK, "via": "delete_work"})
        return
    except Exception:
        pass
    db = _reg_conn()
    try:
        db.query(f"REMOVE DATABASE IF EXISTS {WORK}")
    except Exception as e:
        print("REMOVE DATABASE:", e)
    try:
        db.query("DELETE type::record('work', $s)", {"s": WORK})
    except Exception:
        try:
            db.query(f"DELETE work:{WORK}")
        except Exception as e:
            print("DELETE work:", e)
    print({"destroyed": WORK, "via": "raw", "works": list_works()})


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Surreal 3.2 perf fixture seed")
    p.add_argument("--destroy", action="store_true")
    p.add_argument("--n-char", type=int, default=15)
    p.add_argument("--n-prop", type=int, default=25)
    p.add_argument("--n-ch", type=int, default=12)
    p.add_argument("--n-mem", type=int, default=12)
    args = p.parse_args(argv)
    if args.destroy:
        _destroy()
        return 0
    stats = _seed(args.n_char, args.n_prop, args.n_ch, args.n_mem)
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())

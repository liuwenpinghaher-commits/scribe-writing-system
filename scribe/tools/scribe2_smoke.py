"""新底座(SurrealDB + Hermes)端到端写作 smoke:
起内存 SurrealDB → 建书+圣经(北极星/角色含声音/设定)→ 经 Hermes 真实生成一章 → 存稿 + 建记忆。
证明写作层已真正落到 scribe2/SurrealDB,且生成走 Hermes(非直连 doubao)。

跑:cd scribe && .venv/bin/python tools/scribe2_smoke.py
"""
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from surrealdb import Surreal  # noqa: E402
from scribe2.store import Store  # noqa: E402
from scribe2.domain import Domain  # noqa: E402
from scribe2.generate import generate_continue, rollup_global  # noqa: E402
from scribe2.llm import hermes_complete  # noqa: E402

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _start_surreal():
    port = _free_port()
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"surreal 启动失败 {proc.returncode}")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close(); break
        except OSError:
            time.sleep(0.2)
    d = Surreal(f"ws://127.0.0.1:{port}/rpc")
    d.signin({"username": "root", "password": "root"})
    d.use("scribe", "smoke")
    return d, proc


def main():
    db, proc = _start_surreal()
    try:
        d = Domain(Store(db)); d.s.init_schema()
        print("SurrealDB 就绪,schema 已建")

        # 建书 + 圣经(真实落 SurrealDB)
        w = d.create_work("九原渡·新底座", genre="古典志怪")
        d.set_intent(w, reader_feeling="苍凉、克制,乱世里被小人物不肯泯灭的良心刺痛",
                     core_emotional_arc="少年由避世到以一身担一渡之业",
                     red_lines=["不用现代词与网络腔", "不直白说教", "悲剧不廉价不煽情"])
        d.add_character(w, "渡叔", motivation="守渡四十年替无名死者摆渡,想寻个接渡的人",
                        voice="极少话,开口带河上行话与谶语,平静得像河面")
        d.add_character(w, "阿砚", motivation="逃难少年,原裱画学徒,渐放不下渡口的死者",
                        voice="寡言,爱用裱画笔墨的比方看世界")
        d.add_setting(w, "九原渡", "浊河北岸的古渡,半塌河神庙、补丁层叠的旧渡船;九原者九泉也,渡的不只活人")
        d.add_setting(w, "三不渡", "渡叔的规矩:负心者、欠债者、自寻短见者不渡")
        print("圣经已落 SurrealDB:北极星 + 2 角色(带声音) + 2 设定")

        # 经 Hermes 真实生成第 1 章一节
        print("经 Hermes 生成中(:8642 → doubao)...")
        t0 = time.time()
        instr = ("写引子开篇:乱世末年,裱画学徒少年阿砚逃难七日,抵浊河北岸九原渡;"
                 "暮色里见半塌河神庙与补丁层叠的旧渡船,饥寒交迫躲进破庙避夜。文白相间,古典笔法。")
        prose = generate_continue(d, w, seq=1, instruction=instr,
                                  complete_fn=hermes_complete, target=700)
        dt = time.time() - t0
        cjk = sum(1 for ch in prose if "一" <= ch <= "鿿")
        print(f"\n=== 经 Hermes 生成 {dt:.0f}s,{cjk} 字 ===\n")
        print(prose)

        # 存稿 + 建记忆(真实落 SurrealDB)
        cid = d.add_chapter(w, seq=1, title="夜渡")
        d.save_prose(w, cid, prose)
        d.save_chapter_memory(w, 1, "第一章:裱画学徒阿砚逃难至九原渡,躲进半塌河神庙避夜。")
        rollup_global(d, w)
        snaps = d.list_snapshots(cid)
        print(f"\n=== 已落 SurrealDB:快照 {len(snaps)} 版,章记忆 {len(d.list_chapter_memories(w))} 条,"
              f"全局记忆 {len(d.get_global_memory(w))} 字 ===")
        print("✓ 新底座(SurrealDB + Hermes)端到端写作跑通")
    finally:
        try:
            db.close()
        except Exception:
            pass
        proc.terminate(); proc.wait(timeout=5)


if __name__ == "__main__":
    main()

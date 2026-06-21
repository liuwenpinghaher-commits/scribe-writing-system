"""新底座(SurrealDB + Hermes)多章驱动验证:写 3 章《九原渡》,全 QC 跑通——
生成(走Hermes)+ 自动章记忆(确定性rollup防漂移)+ critique 评分 + 一致性检查。
验证:跨章连贯(ch2/ch3 能引到 ch1)、全局记忆身份保真、QC 闭环。

跑:cd scribe && .venv/bin/python tools/scribe2_drive.py
"""
import os
import re
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
from scribe2.generate import generate_continue, ingest_chapter  # noqa: E402
from scribe2.critique import build_critique_prompt, parse_critique  # noqa: E402
from scribe2.consistency import check_chapter  # noqa: E402
from scribe2.llm import hermes_complete  # noqa: E402

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))

CHAPTERS = [
    {"seq": 1, "title": "夜渡", "beat": "引子开篇:乱世末年,裱画学徒少年阿砚逃难七日抵浊河北岸九原渡,"
     "暮色里见半塌河神庙与补丁层叠的旧渡船,饥寒躲进破庙避夜;夜里见独眼渡叔提灯,一船无声客夜渡,阿砚辨不清人鬼。"},
    {"seq": 2, "title": "三不渡", "beat": "天明流民来求渡,渡叔验客收渡钱;一负心男子求渡被渡叔一句'负心者不渡'拒了。"
     "渡叔授阿砚撑篙认水、收他为徒。承接第一章,阿砚仍是那个躲破庙的少年。"},
    {"seq": 3, "title": "接声", "beat": "无月夜,渡叔带阿砚夜渡,阿砚头一回清楚听见浊浪里枉死者的低语呼名,惊惧;"
     "渡叔道破'接声'之能。承接前两章渡口与三不渡的设定。"},
]


def _start_surreal():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen([SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
                             "--user", "root", "--pass", "root", "memory"], cwd="/tmp", env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError("surreal 启动失败")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close(); break
        except OSError:
            time.sleep(0.2)
    d = Surreal(f"ws://127.0.0.1:{port}/rpc")
    d.signin({"username": "root", "password": "root"}); d.use("scribe", "drive")
    return d, proc


def _cjk(s):
    return sum(1 for ch in s if "一" <= ch <= "鿿")


def main():
    db, proc = _start_surreal()
    try:
        d = Domain(Store(db)); d.s.init_schema()
        w = d.create_work("九原渡·新底座验证", genre="古典志怪")
        d.set_intent(w, reader_feeling="苍凉、克制,乱世里被小人物不肯泯灭的良心刺痛",
                     core_emotional_arc="少年由避世到以一身担一渡之业",
                     red_lines=["不用现代词与网络腔", "不直白说教", "悲剧不廉价不煽情"])
        d.add_character(w, "渡叔", "守渡四十年替无名死者摆渡,想寻个接渡的人",
                        "极少话,开口带河上行话与谶语,平静得像河面")
        d.add_character(w, "阿砚", "逃难少年,原裱画学徒,渐放不下渡口的死者",
                        "寡言,爱用裱画笔墨的比方看世界")
        d.add_setting(w, "九原渡", "浊河北岸古渡,半塌河神庙、补丁层叠旧渡船;九原者九泉,渡的不只活人")
        d.add_setting(w, "三不渡", "渡叔规矩:负心者、欠债者、自寻短见者不渡")
        print("圣经落 SurrealDB:北极星+2角色(带声音)+2设定\n")

        for ch in CHAPTERS:
            seq = ch["seq"]
            t0 = time.time()
            prose = generate_continue(d, w, seq, ch["beat"], hermes_complete, target=750)
            cid = d.add_chapter(w, seq, ch["title"])
            d.save_prose(w, cid, prose)
            ingest_chapter(d, w, seq, hermes_complete)            # 自动章记忆+确定性rollup
            rf = (d.get_intent(w) or {}).get("reader_feeling", "")
            crit = parse_critique(hermes_complete(build_critique_prompt(prose, rf)))
            flags = check_chapter(d, w, seq, hermes_complete)      # 一致性
            print(f"第{seq}章《{ch['title']}》 {_cjk(prose)}字 {time.time()-t0:.0f}s "
                  f"| critique={crit.get('overall')} 弱={crit.get('worst_dims')} | 矛盾flag={len(flags)}")

        # 跨章连贯验证:全局记忆应含三章梗概(确定性拼接、身份保真)
        glob = d.get_global_memory(w)
        print(f"\n全局记忆({len(glob)}字,确定性拼接无LLM压缩):\n{glob}\n")
        print(f"章记忆 {len(d.list_chapter_memories(w))} 条;一致性flag共 "
              f"{len(d.list_consistency_flags(w))} 条")
        # 抽看第3章开头(应承接前文渡口/渡叔)
        ch3 = next(c for c in d.list_chapters(w) if c.get("seq") == 3)
        print(f"\n=== 第3章开头(验证承接)===\n{d.latest_prose(d._idpart(ch3['id']))[:300]}")
        print("\n✓ 新底座(SurrealDB+Hermes)多章端到端 + 全 QC 跑通")
    finally:
        try:
            db.close()
        except Exception:
            pass
        proc.terminate(); proc.wait(timeout=5)


if __name__ == "__main__":
    main()

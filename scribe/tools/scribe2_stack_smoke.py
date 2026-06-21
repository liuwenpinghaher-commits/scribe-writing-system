"""全栈 smoke:起 SurrealDB + scribe2 uvicorn,验证前端契约端点的真实形状。
不需 Hermes(只验非 LLM 契约)。跑:cd scribe && .venv/bin/python tools/scribe2_stack_smoke.py
"""
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _free():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def main():
    sport, hport = _free(), _free()
    senv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    surreal = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{sport}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=senv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            socket.create_connection(("127.0.0.1", sport), timeout=0.2).close(); break
        except OSError:
            time.sleep(0.2)
    # 起 scribe2 uvicorn,连这个 surreal
    aenv = {**os.environ, "SURREAL_URL": f"ws://127.0.0.1:{sport}/rpc"}
    ulog = open("/tmp/uvi_smoke.log", "w")
    uvi = subprocess.Popen(
        [".venv/bin/python", "-m", "uvicorn", "scribe2.app:app", "--host", "127.0.0.1",
         "--port", str(hport)], cwd=str(ROOT), env=aenv,
        stdout=ulog, stderr=ulog)
    base = f"http://127.0.0.1:{hport}"
    H = {"X-Owner-Id": "u1"}
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except Exception:
                time.sleep(0.3)
        c = httpx.Client(base_url=base, headers=H, timeout=15)
        ok = []

        def check(name, cond):
            ok.append((name, bool(cond)))
            print(f"  {'✓' if cond else '✗'} {name}")

        w = c.post("/works", json={"title": "九原渡·全栈"}).json()["work_id"]
        check("createWork", w)
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉克制", "do_not_betray": ["不煽情", "不用现代词"]})
        it = c.get(f"/works/{w}/author-intent").json()
        check("intent.do_not_betray 是数组", isinstance(it.get("do_not_betray"), list) and "不煽情" in it["do_not_betray"])
        c.post(f"/works/{w}/characters", json={"name": "渡叔", "motivation": "守渡四十年", "voice": "极静带谶语"})
        chs = c.get(f"/works/{w}/characters").json()
        check("character 形状", chs and chs[0]["name"] == "渡叔" and "id" in chs[0])
        rp = c.post(f"/works/{w}/settings", json={"name": "九原渡", "type_": "place", "description": "浊河北岸古渡"})
        rg = c.get(f"/works/{w}/settings")
        print("    [debug] POST setting:", rp.status_code, rp.text[:150])
        print("    [debug] GET settings:", rg.status_code, rg.text[:200])
        st = rg.json() if isinstance(rg.json(), list) else []
        check("setting type/content", st and st[0].get("type") == "place" and st[0].get("content") == "浊河北岸古渡")
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "夜渡"})
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔立于船头,独眼望浊浪。", "lock": True})
        ch = c.get(f"/works/{w}/chapters/1").json()
        check("chapter snapshots + volume_id", "snapshots" in ch and len(ch["snapshots"]) == 1 and ch["snapshots"][0].get("is_human_locked") == 1)
        c.post(f"/works/{w}/chapters/1/segments/rebuild")
        segs = c.get(f"/works/{w}/chapters/1/segments").json()
        check("segments + 引用", segs and "渡叔" in segs[0]["text"])
        summ = c.get("/works").json()
        s = next(x for x in summ if x["id"] == w)
        check("works 汇总计数", s["chapter_count"] == 1 and s["word_count"] == 11)
        q = c.get(f"/works/{w}/quality").json()
        check("quality 嵌套形状", q.get("chapters") == 1 and "foreshadow" in q and "consistency" in q and "cost" in q)
        mem = c.get(f"/works/{w}/memory").json()
        check("memory 契约(global+chapters)", "global" in mem and "chapters" in mem)
        # 外围面板端点都返回(空也算通)
        for ep in ["insights", "option-sets", "threads", "materials", "imaginations",
                   "relations", "timeline", "agent-memory", "agent-skills", "foreshadows",
                   "consistency-flags", "volumes", "pending-writes"]:
            r = c.get(f"/works/{w}/{ep}")
            check(f"GET {ep}", r.status_code == 200 and isinstance(r.json(), list))
        check("cost 形状", "cost_usd" in c.get(f"/works/{w}/cost").json())
        t = c.get(f"/works/{w}/chapters/1/task").json()
        check("task 状态机", t.get("status") == "PLANNING" and "next" in t)

        passed = sum(1 for _, v in ok if v)
        print(f"\n全栈契约 smoke: {passed}/{len(ok)} 通过")
        if passed == len(ok):
            print("✓ 前端契约端点全部对齐 scribe2(真实 SurrealDB + uvicorn)")
    finally:
        uvi.terminate(); surreal.terminate()
        uvi.wait(timeout=5); surreal.wait(timeout=5)


if __name__ == "__main__":
    main()

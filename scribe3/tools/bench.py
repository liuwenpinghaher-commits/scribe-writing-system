#!/usr/bin/env python3
"""scribe3 性能基准:热路径查询耗时基线。

用法: scribe3/.venv/bin/python tools/bench.py [--scale N]
  --scale:测试数据规模(命题数,默认 500)
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time

# Add project root to path for scribe3 imports
_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def bench(scale: int = 500):
    """造 scale 条命题 + 相关字符和知识边 → 测量核心查询耗时。"""
    from scribe3.store import SurrealStore
    from scribe3.ontology import Entity, Fact, KnowledgeEdge, Event

    port = _free_port()
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"surreal 子进程启动失败,退出码 {proc.returncode}")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    st = SurrealStore(url=f"ws://127.0.0.1:{port}/rpc", ns="scribe3", db="test")
    st.apply_schema()

    try:
        # 造角色
        chars = [f"角色{i}" for i in range(10)]
        for c in chars:
            st.add_entity(Entity(f"role:{c}", "character", c))

        # 造命题(分布在不同章)
        print(f"造 {scale} 条命题...", flush=True)
        for i in range(scale):
            ch = (i % 50) + 1
            st.add_fact(Fact(f"fact:b{i}", f"role:角色{i % 10}", "获知",
                             f"命题内容编号{i}", valid_from=ch))

        # 造知识边
        for i in range(0, scale, 5):
            k = KnowledgeEdge(f"role:角色{i % 10}", f"fact:b{i}",
                              since_chapter=(i % 50) + 1, acquired_via="learned")
            st.add_knowledge(k)

        # 造事件
        for i in range(0, min(100, scale // 5)):
            ev = Event(f"ev:e{i}", "test", story_time=(i % 20) + 1,
                       participants={"SUBJ": f"role:角色{i % 10}"})
            st.add_event(ev)

        # 基准
        qv = [0.0] * 512  # 伪 query vector
        tests = [
            ("facts_at(5)", lambda: st.facts_at(5)),
            ("facts_at(25)", lambda: st.facts_at(25)),
            ("events_at(5)", lambda: st.events_at(5)),
            ("knowledge(@property)", lambda: st.knowledge),
            ("semantic_recall", lambda: st.semantic_recall("test", k=5)),
        ]
        for name, fn in tests:
            durations = []
            for _ in range(5):
                t0 = time.perf_counter()
                fn()
                durations.append((time.perf_counter() - t0) * 1000)
            durations.sort()
            print(f"{name:30s} p50={durations[2]:6.1f}ms  p95={durations[-1]:6.1f}ms")

    finally:
        st.close()
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    scale = 500
    args = sys.argv[1:]
    for a in args:
        if a.startswith("--scale="):
            scale = int(a.split("=", 1)[1])
        elif a.isdigit():
            scale = int(a)
    bench(scale)

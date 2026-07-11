"""scribe3 集成测试夹具:每个测试起一个临时内存 SurrealDB,返回已建 schema 的 SurrealStore。

注意:项目路径含中文「写作 3.0」会让 surreal v3 子进程读环境时 panic(SIGABRT)。
必须在纯 ASCII 的 cwd(/tmp)+ 净化环境下起服(沿用 scribe2 conftest 已验证的范式)。
"""
import os
import shutil
import socket
import subprocess
import time

import pytest

from scribe3.store import SurrealStore

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(autouse=True)
def _isolated_llm_ledger(tmp_path, monkeypatch):
    """H-10:LLM 日帽共享台账(SQLite)按测试隔离到 tmp,防测试笔数灌进生产台账
    误触真实日帽(与 store 夹具同理:测试绝不碰生产数据)。"""
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "llm_ledger.sqlite3"))


@pytest.fixture(autouse=True)
def _clear_context_caches():
    """Task 16-C:检索接线后 MemoryRetriever.retrieve() 走 module 级单例 RETRIEVAL_CACHE。
    每测试前清检索/全局卡缓存 + 重置指标直方图,防跨测试(不同临时 store 复用同 work/query)
    命中彼此陈旧结果或指标累加串扰(每个 store 夹具是独立临时 DB,缓存却是进程共享)。"""
    from scribe3 import context_cache as cc
    cc.RETRIEVAL_CACHE.clear()
    cc.GLOBAL_CARD_CACHE.clear()
    cc.reset_metrics_for_test()
    yield


@pytest.fixture()
def store():
    port = _free_port()
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
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
        yield st
    finally:
        st.close()
        proc.terminate()
        proc.wait(timeout=5)

"""S-1 连接韧性 TDD:SurrealDB 掉线后 store 自动重连,后端不再需要手工重启。

背景(2026-07-04 :8001 事件):SurrealDB 进程掉线 → store 的 WS 连接残留坏 socket,
除 /health 外全 500,必须重启后端。SDK 实测:`_send` 只在 socket is None 时懒建 TCP,
且 signin/use 是**连接级状态**——新 socket 没有认证态,所以任何掉线都是永久性失败。
修法:store 层捕获连接类异常 → 重建连接(Surreal+signin+use)→ 重试一次。

本机 WS(127.0.0.1)不存在"提交成功但响应丢失"的分区窗口:服务端死=写未提交,
故写路径重试一次可接受(且核心写多为 UPSERT 幂等)。
"""
import socket as _socket
import subprocess
import time

import pytest

from scribe3.store import SurrealStore
from scribe3.tests.conftest import SURREAL_BIN


def _start_surreal(port: int) -> subprocess.Popen:
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": __import__("os").path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"surreal 启动失败,退出码 {proc.returncode}")
        try:
            _socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    return proc


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_query_survives_socket_drop(store):
    """底层 socket 被掐(连接级故障)→ _query 透明重连,调用方无感。"""
    store.save_chapter(1, "第一章正文。", title="一")
    # 模拟掉线:直接关底层 ws socket(残留非 None 的坏 socket,复现事故形态)
    store._db.socket.close()
    ch = store.get_chapter(1)
    assert ch and ch["prose"] == "第一章正文。"


def test_write_survives_socket_drop(store):
    """写路径同样自动重连(save_chapter 走 _execute_write)。"""
    store.save_chapter(1, "v1。", title="一")
    store._db.socket.close()
    store.save_chapter(1, "v2,掉线后重写。", title="一")
    assert store.get_chapter(1)["prose"] == "v2,掉线后重写。"


def test_store_heals_after_server_restart():
    """整库进程重启(8001 事故等价):同端口拉起新 server 后,同一个 store
    实例读写自愈——不需要重启后端。(新 server 是空库,重连须重放 signin/use,
    验证点是'能查/能写'而非旧数据仍在。)"""
    port = _free_port()
    proc = _start_surreal(port)
    st = None
    try:
        st = SurrealStore(url=f"ws://127.0.0.1:{port}/rpc", ns="scribe3", db="test")
        st.apply_schema()
        st.save_chapter(1, "重启前。", title="一")
        proc.terminate()
        proc.wait(timeout=5)
        proc = _start_surreal(port)   # 同端口新进程(内存库,数据清零)
        # 第一类调用:读——应重连成功(空库查不到旧章,但不抛连接错)
        st.apply_schema()             # 新库重放 schema(掉线恢复的真实操作序列)
        assert st.get_chapter(1) is None
        # 第二类调用:写后读回
        st.save_chapter(2, "重启后新写。", title="二")
        assert st.get_chapter(2)["prose"] == "重启后新写。"
    finally:
        if st is not None:
            st.close()
        proc.terminate()
        proc.wait(timeout=5)


def test_non_connection_errors_do_not_retry(store, monkeypatch):
    """语法/校验类错误不属连接故障:原样抛,不得触发重连重试(防坏 SQL 双发)。

    打桩点是 query_raw:2026-07-14 起 `_raw_query` 改走它(逐条校验多语句结果,堵死
    "migration 后续语句失败被静默吞掉"的 P0;见 store._query_all_checked),不再经 SDK 裸 query。
    测试意图不变——变的只是被计数的那道接缝。"""
    calls = {"n": 0}
    original = store._db.query_raw

    def counting(surql, vars=None, **kw):
        calls["n"] += 1
        return original(surql, vars or {})

    monkeypatch.setattr(store._db, "query_raw", counting)
    with pytest.raises(Exception):
        store._query("SELECT FROM WHERE 语法错误")
    assert calls["n"] == 1, "非连接错误绝不能重试"

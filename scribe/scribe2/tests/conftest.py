import os
import shutil
import socket
import subprocess
import time

import pytest
from surrealdb import Surreal

# 解析 surreal 二进制(PATH 优先,否则用 ~/.surrealdb/surreal)
SURREAL_BIN = (
    os.environ.get("SURREAL_BIN")
    or shutil.which("surreal")
    or os.path.expanduser("~/.surrealdb/surreal")
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture()
def db():
    """每个测试起一个内存 SurrealDB,返回已登录的同步连接。"""
    port = _free_port()
    # 注意:项目路径含中文「写作 3.0」会让 surreal v3.1.5 在子进程里读环境时 panic(SIGABRT)。
    # 必须在纯 ASCII 的 cwd + 净化环境下起服。
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # 轮询端口就绪(server 起服约需 1–2s),最多等 8s
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"surreal 子进程启动失败,退出码 {proc.returncode}")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    d = Surreal(f"ws://127.0.0.1:{port}/rpc")
    try:
        d.signin({"username": "root", "password": "root"})
        d.use("scribe", "test")
        yield d
    finally:
        try:
            d.close()
        except Exception:
            pass
        proc.terminate()
        proc.wait(timeout=5)

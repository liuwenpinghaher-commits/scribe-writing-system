"""scribe3 集成测试夹具:每个测试起一个临时内存 SurrealDB,返回已建 schema 的 SurrealStore。

**仅支持 SurrealDB 3.x**（与 demo 3.2.4 对齐）。禁止 2.x 兼容回退。
Grok 运行机默认禁止起 Surreal 做验收——见用户 host-resource 规则；本夹具供
CI / 已装 Surreal 3 的开发机 / demo 侧使用。

注意:项目路径含中文会让 surreal 子进程读环境时 panic(SIGABRT)。
必须在纯 ASCII 的 cwd(/tmp)+ 净化环境下起服。
"""
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time

import pytest

# 设置中心隔离(必须先于任何 scribe3.* import):apply_restart_overrides 在
# import scribe3.app 时执行,若不先钉住台账路径,开发机生产
# ~/.scribe2-surreal/scribe3_settings.sqlite3 的值会灌进整个测试进程 env
# (实测:假库塞 SCRIBE3_API_TOKEN 后 import → 全部请求 401)。pytest 先加载
# conftest 再收集测试文件,故此处 setdefault 早于一切 import scribe3.app。
os.environ.setdefault("SCRIBE3_SETTINGS_DB",
                      os.path.join(tempfile.mkdtemp(prefix="scribe3-settings-test-"),
                                   "settings.sqlite3"))
# 3.x 为主；仅允许非致命迁移语法在极端版本漂移时 soft（默认仍应装 3.2.4）
os.environ.setdefault("SCRIBE3_SCHEMA_SOFT", "1")


from scribe3.store import SurrealStore

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _require_surreal_3(bin_path: str) -> None:
    """拒绝 SurrealDB 2.x：type::record 语义与 demo 3.2.4 不一致，禁止双轨。"""
    if not bin_path or not os.path.isfile(bin_path):
        raise RuntimeError(
            f"需要 SurrealDB 3.x 可执行文件（demo 对齐 3.2.4）。未找到: {bin_path!r}。"
            "请设置 SURREAL_BIN 指向 3.x，或在 CI/demo 机运行 store 集成测。"
        )
    try:
        out = subprocess.check_output(
            [bin_path, "version"], text=True, stderr=subprocess.STDOUT, timeout=10,
        )
    except Exception as e:
        raise RuntimeError(f"无法执行 {bin_path} version: {e}") from e
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out or "")
    if not m:
        raise RuntimeError(f"无法解析 Surreal 版本: {out!r}")
    major = int(m.group(1))
    if major < 3:
        raise RuntimeError(
            f"SurrealDB {m.group(0)} 不受支持（禁止 2.x 回退）。"
            f"请安装 3.x（demo 为 3.2.4）。当前二进制: {bin_path}\n输出: {out.strip()}"
        )


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
def _journey_precheck_off_by_default(monkeypatch):
    """生产默认开旅程门槛；存量写路径单测无北极星脚手架，默认关。
    需要测 409 的用例自行 monkeypatch.setenv('SCRIBE3_JOURNEY_PRECHECK','1')。"""
    monkeypatch.setenv("SCRIBE3_JOURNEY_PRECHECK", "0")


@pytest.fixture(autouse=True)
def _craft_gate_off_by_default(monkeypatch):
    """工艺门闩默认生产开启;单测/存量 API 用例无脚手架,默认关。
    需要测 409 门闩的用例自行 monkeypatch.setenv('SCRIBE3_CRAFT_GATE','1')。"""
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "0")


@pytest.fixture(autouse=True)
def _finalize_gate_off_by_default(monkeypatch):
    """定稿门闩默认生产开启;存量存稿用例无质控夹具,默认关。
    需要测 finalize 409/旁路的用例自行 monkeypatch.setenv('SCRIBE3_FINALIZE_GATE','1')。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "0")


@pytest.fixture(autouse=True)
def _codex_thicken_gate_off_by_default(request, monkeypatch):
    """设定加厚门默认生产开启;存量单测夹具使用简短占位文本,默认关。
    专门测加厚门的 test_codex_persist_gate / test_tonglu_round2 保持默认开启。"""
    node = getattr(request.node, "nodeid", "") or ""
    if "test_codex_persist_gate" in node or "test_tonglu_round2" in node:
        return
    monkeypatch.setenv("SCRIBE3_CODEX_THICKEN_GATE", "0")


@pytest.fixture(autouse=True)
def _emergency_rest_write_on_for_tests(monkeypatch):
    """生产默认关 REST 世界写;单测/存量 test_app 写路径需显式开。
    需要测 403 关闸的用例自行 monkeypatch.setenv('SCRIBE3_EMERGENCY_REST_WRITE','0')。"""
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "1")


@pytest.fixture(autouse=True)
def _context_snapshot_off_for_tests(monkeypatch):
    """生产默认开 context 快照绑定;存量 chat 单测未带三件套会 400。
    需要测强制绑定的用例(test_context_api)自行 monkeypatch 为 1。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "0")


@pytest.fixture(autouse=True)
def _fake_embed_512(request, monkeypatch):
    """测试默认假 embedding 前向(512 维),保留 embed() 缓存层。
    避免 CI 加载 fastembed/真模型或维度漂移炸 Surreal vector 索引。
    课例语义召回依赖真中文相似度,跳过假向量。"""
    node = getattr(request.node, "nodeid", "") or ""
    if "test_lesson.py" in node:
        return
    def _fake_compute(texts):
        out = []
        for t in texts or [""]:
            v = [0.0] * 512
            for ch in str(t):
                v[ord(ch) % 512] += 1.0
            out.append(v)
        return out
    try:
        monkeypatch.setattr("scribe3.embed._compute", _fake_compute)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _clear_context_caches():
    """Task 16-C:检索接线后 MemoryRetriever.retrieve() 走 module 级单例 RETRIEVAL_CACHE。
    每测试前清检索/全局卡缓存 + 重置指标直方图,防跨测试(不同临时 store 复用同 work/query)
    命中彼此陈旧结果或指标累加串扰(每个 store 夹具是独立临时 DB,缓存却是进程共享)。"""
    from scribe3 import context_cache as cc
    cc.RETRIEVAL_CACHE.clear()
    cc.GLOBAL_CARD_CACHE.clear()
    cc.reset_metrics_for_test()
    try:
        from scribe3.mcp import _common as mcp_common
        mcp_common._store = None
        mcp_common._stores.clear()
    except Exception:
        pass
    yield
    try:
        from scribe3.mcp import _common as mcp_common
        mcp_common._store = None
        mcp_common._stores.clear()
    except Exception:
        pass


def _boot_store():
    """起一个临时内存 SurrealDB 子进程 + 连上的 SurrealStore(schema 尚未应用)。"""
    _require_surreal_3(SURREAL_BIN)
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
    return st, proc


@pytest.fixture()
def store():
    st, proc = _boot_store()
    st.apply_schema()
    try:
        yield st
    finally:
        st.close()
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture()
def unmigrated_store():
    """schema **未应用**的裸 store——供 migration 层测试自己控制"应用到哪一版"。

    真实生产库是"跑到 082、从未见过 083"的状态;用 `store` 夹具(已应用全部 migration)
    再 CREATE 一行来冒充老行是**假老行**——CREATE 会自动填 DEFAULT,恰好绕开了
    "老行字段为 NONE"这个触发条件,测试会假绿。要复现真事故必须从未应用 083 的表开始。"""
    st, proc = _boot_store()
    try:
        yield st
    finally:
        st.close()
        proc.terminate()
        proc.wait(timeout=5)

# scribe3/tests/test_settings_gate.py
"""注册表完备性门禁(与 KNOWN_REST_WRITE_ROUTES 同范式):
代码里新增 SCRIBE3_*/HERMES_* 环境变量读取,必须登记 settings.REGISTRY,
否则本测试红——配置从此不再散落。"""
import re
from pathlib import Path

from scribe3.settings import REGISTRY

SRC = Path(__file__).resolve().parent.parent   # scribe3/
# 测试/工具/插件专用 env,不进设置中心(见 spec「明确不做」)
EXEMPT = {
    # 真实生效豁免:该 env 自身就是台账路径,登记进注册表会自举(台账存自己里面)。
    "SCRIBE3_SETTINGS_DB",
    # 防御性登记(现状下都不会被下面的扫描真正抓到,留着是显式声明"不进设置
    # 中心",防止将来代码挪位置/改扫描范围后被误判成漏登记):
    "SCRIBE3_API_BASE",        # 有 SCRIBE3_ 前缀会过滤通过,但只在
                                # scribe3/hermes_plugins/scribe3-memory/__init__.py(子目录)
                                # 里读取——SRC 只 glob scribe3/*.py 顶层,扫不到子目录
    "SURREAL_BIN",              # 无 SCRIBE3_/HERMES_ 前缀,天然被前缀过滤挡掉
    "API_SERVER_KEY",           # 无 SCRIBE3_/HERMES_ 前缀,天然被前缀过滤挡掉
}
_PAT = re.compile(r"os\.(?:environ\.get|getenv|environ\[)\(?\s*['\"]([A-Z][A-Z0-9_]+)['\"]")


def test_all_env_reads_registered():
    registered = {s.key for s in REGISTRY}
    offenders = []
    for py in SRC.glob("*.py"):
        for name in _PAT.findall(py.read_text(encoding="utf-8")):
            if not (name.startswith("SCRIBE3_") or name.startswith("HERMES_")):
                continue
            if name not in registered and name not in EXEMPT:
                offenders.append(f"{py.name}: {name}")
    assert not offenders, f"发现未登记设置注册表的 env 读取: {offenders}"

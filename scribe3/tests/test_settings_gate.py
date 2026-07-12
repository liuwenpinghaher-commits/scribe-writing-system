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
    "SCRIBE3_SETTINGS_DB",     # 设置台账自身路径(自举,不能存在自己里面)
    "SCRIBE3_API_BASE",        # hermes 插件回调(插件进程 env)
    "SURREAL_BIN",             # 测试专用
    "API_SERVER_KEY",          # Hermes 鉴权链(HermesAuth 多级回退,非本系统配置)
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

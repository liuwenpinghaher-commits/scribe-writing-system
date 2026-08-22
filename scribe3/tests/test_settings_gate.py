# scribe3/tests/test_settings_gate.py
"""注册表完备性门禁(与 KNOWN_REST_WRITE_ROUTES 同范式):
代码里新增 SCRIBE3_*/HERMES_* 环境变量读取,必须登记 settings.REGISTRY,
或写进 docs/ops/FLAG_EXEMPT.md。"""
import re
from pathlib import Path

from scribe3.settings import REGISTRY

SRC = Path(__file__).resolve().parent.parent   # scribe3/
ROOT = SRC.parent
EXEMPT_FILE = ROOT / "docs" / "ops" / "FLAG_EXEMPT.md"
_PAT = re.compile(r"os\.(?:environ\.get|getenv|environ\[)\(?\s*['\"]([A-Z][A-Z0-9_]+)['\"]")
_SKIP_PARTS = {"tests", "__pycache__", "web", "migrations"}


def _load_exempt() -> set[str]:
    keys = {
        "SURREAL_BIN",
        "API_SERVER_KEY",
    }
    if EXEMPT_FILE.is_file():
        for line in EXEMPT_FILE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            token = raw.split()[0]
            if token.startswith("SCRIBE3_") or token.startswith("HERMES_"):
                keys.add(token)
    return keys


def test_all_env_reads_registered():
    registered = {s.key for s in REGISTRY}
    exempt = _load_exempt()
    offenders = []
    for py in SRC.rglob("*.py"):
        if any(p in _SKIP_PARTS for p in py.parts):
            continue
        for name in _PAT.findall(py.read_text(encoding="utf-8")):
            if not (name.startswith("SCRIBE3_") or name.startswith("HERMES_")):
                continue
            if name not in registered and name not in exempt:
                offenders.append(f"{py.relative_to(SRC)}: {name}")
    assert not offenders, f"发现未登记设置注册表的 env 读取: {offenders}"


def test_exempt_file_exists():
    assert EXEMPT_FILE.is_file()
    assert "SCRIBE3_SETTINGS_DB" in _load_exempt()

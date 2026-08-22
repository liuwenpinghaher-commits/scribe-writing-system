"""统一召回中枢：入口唯一性 + 对话旗默认开。"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
_RECALL_MODULE = "recall_service"


def _find_hybrid_recall_callers():
    """扫描源码：所有 .hybrid_recall( 调用必须来自召回中枢、定义处或测试。"""
    hits = []
    for py in SRC.rglob("*.py"):
        if "tests" in py.parts or "__pycache__" in py.parts:
            continue
        if "tools" in py.parts and py.parent.name == "tools":
            continue
        text = py.read_text(encoding="utf-8")
        if ".hybrid_recall(" in text and _RECALL_MODULE not in py.name:
            if "write_assemble_context" in py.name:
                continue
            hits.append(str(py.relative_to(SRC)))
    return hits


def test_no_bypass_hybrid_recall():
    hits = _find_hybrid_recall_callers()
    allowed = {"store/recall.py", "mcp/tools.py", "mcp/tools_recall.py"}
    unexpected = [h for h in hits if h not in allowed]
    assert unexpected == [], f"发现绕过统一召回入口的调用：{unexpected}"


def test_recall_shadow_flag_default_on():
    from scribe3.feature_flags import get_flag
    assert get_flag("SCRIBE3_RECALL_DISCUSS") == "1"

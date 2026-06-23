"""引擎层 craft · 纯函数/纯常量,无 DB 无网络(同 test_critique 范式)。"""
from scribe3.craft import ENGINES, PALETTE, build_craft_block

_SCIFI = ("沈默", "姜婉", "陆远舟", "校准", "波形图", "数据面板", "探针", "数据日志", "酸菜鱼")


def test_engines_seven_present():
    assert set(ENGINES) == {"body", "temperature", "idle", "metaphor", "subtext", "sensory", "soak"}


def test_palette_fifteen_complete():
    assert len(PALETTE) == 15
    for name, e in PALETTE.items():
        assert e["body"], f"{name} 缺身体信号"
        assert e["inner"], f"{name} 缺内部感觉"


def test_no_scifi_residue():
    """craft wiki 是科幻《量子幽灵》提炼,迁移必须清洗(两版复盘发现 B)。"""
    blob = "".join(ENGINES.values()) + "".join(
        "".join(e["body"] + e["inner"]) for e in PALETTE.values())
    for w in _SCIFI:
        assert w not in blob, f"craft.py 残留科幻词:{w}"


def test_build_craft_block_has_engines():
    block = build_craft_block()
    assert "身体先行" in block and "温度曲线" in block and "潜台词" in block


def test_build_craft_block_appends_themed_rules():
    rules = [{"kind": "artifact_craft", "pattern": "法器四件套", "note": "专名+工艺+术数+义理"}]
    block = build_craft_block(rules)
    assert "本书题材规则" in block
    assert "法器四件套" in block and "专名+工艺+术数+义理" in block

"""引擎层 craft · 纯函数/纯常量,无 DB 无网络(同 test_critique 范式)。"""
from scribe3.craft import (
    ENGINES,
    PALETTE,
    PUBLIC_ENGINE_KEYS,
    build_craft_block,
    resolve_engine_key,
)

_SCIFI = ("沈默", "姜婉", "陆远舟", "校准", "波形图", "数据面板", "探针", "数据日志", "酸菜鱼")


def test_engines_eight_present():
    """8 个展示槽位必在；变体键(idle_pdc / metaphor_novel 等)为附加。"""
    assert set(PUBLIC_ENGINE_KEYS).issubset(set(ENGINES))
    assert set(PUBLIC_ENGINE_KEYS) == {
        "body", "temperature", "idle", "metaphor", "subtext", "sensory", "soak", "restraint",
    }
    for k in ("idle_pdc", "sensory_pdc", "metaphor_novel", "restraint_novel"):
        assert k in ENGINES


def test_build_craft_block_has_restraint():
    block = build_craft_block()
    assert "留白" in block and "该不写的不写" in block


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


# ── PR-5 · CRAFT_NOVEL 选择表 / 子串 ──────────────────────────────────────


def test_default_metaphor_keeps_quota_substring(monkeypatch):
    """flag 关：保留既有「每章 2-4 个」配额声口。"""
    monkeypatch.delenv("SCRIBE3_CRAFT_NOVEL", raising=False)
    monkeypatch.delenv("SCRIBE3_PDC", raising=False)
    block = build_craft_block()
    assert "2-4" in block
    assert "每章 2-4 个" in block
    assert "每章≥3" in block  # 默认闲笔
    assert "感官签名" in block  # 默认感官
    assert "anti_essay" not in block
    assert "小说优先" not in block


def test_craft_novel_metaphor_no_quota_prefers_action(monkeypatch):
    """CRAFT_NOVEL=1：无「2-4」；具体动作优先；禁比喻链。"""
    monkeypatch.setenv("SCRIBE3_CRAFT_NOVEL", "1")
    monkeypatch.delenv("SCRIBE3_PDC", raising=False)
    block = build_craft_block()
    assert "2-4" not in block
    assert "每章 2-4" not in block
    assert "具体动作" in block
    assert "比喻" in block and ("连环" in block or "比喻链" in block or "明喻" in block)
    assert "至多 1 个" in block or "认知必需" in block
    # 选择表：闲笔/感官走偏科；留白并 anti_essay
    assert "闲笔偏科" in block
    assert "感官峰值" in block
    assert "anti_essay" in block
    # 不得残留默认均铺配额声口
    assert "每章≥3" not in block


def test_craft_novel_and_pdc_no_double_inject(monkeypatch):
    """CRAFT_NOVEL + PDC 同开：每个槽位只注入一段，不并列默认+偏科。"""
    monkeypatch.setenv("SCRIBE3_CRAFT_NOVEL", "1")
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    block = build_craft_block()
    assert "2-4" not in block
    assert block.count("闲笔偏科") == 1
    assert block.count("感官峰值") == 1
    assert block.count("【闲笔】") == 1
    assert block.count("【感官锚定】") == 1
    assert block.count("【认知比喻】") == 1
    # 默认串不得与偏科串并排
    assert "每章≥3" not in block
    assert "感官签名" not in block
    assert "小说优先" in block  # metaphor_novel


def test_pdc_only_keeps_default_metaphor(monkeypatch):
    """仅 PDC：idle/sensory 偏科，metaphor 仍为默认配额串。"""
    monkeypatch.delenv("SCRIBE3_CRAFT_NOVEL", raising=False)
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    block = build_craft_block()
    assert "闲笔偏科" in block
    assert "感官峰值" in block
    assert "2-4" in block
    assert "小说优先" not in block
    assert "anti_essay" not in block


def test_resolve_engine_key_selection_table():
    assert resolve_engine_key("metaphor", novel=False, pdc=False) == "metaphor"
    assert resolve_engine_key("metaphor", novel=True, pdc=False) == "metaphor_novel"
    assert resolve_engine_key("metaphor", novel=True, pdc=True) == "metaphor_novel"
    assert resolve_engine_key("metaphor", novel=False, pdc=True) == "metaphor"
    assert resolve_engine_key("idle", novel=True, pdc=True) == "idle_pdc"
    assert resolve_engine_key("sensory", novel=False, pdc=True) == "sensory_pdc"
    assert resolve_engine_key("restraint", novel=True, pdc=False) == "restraint_novel"
    assert resolve_engine_key("body", novel=True, pdc=True) == "body"

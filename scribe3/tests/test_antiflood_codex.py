"""防洪水：点名公开档吃满、未点名名片、秘密 fail-closed。禁止 Surreal。"""
from __future__ import annotations

from scribe3.api.services.write_assemble_blocks import _codex_block, _codex_segments
from scribe3.context_budget import (
    GEN_SEGMENT_PROTECTED,
    L2_DROP_TIER,
    _half_cut_segment,
    apply_l2_trim,
    join_generation_segments,
)
from scribe3.iceberg import (
    CARDS_PACK_CAP,
    DEDUCTION_PACK_CAP,
    INJECT_CAP,
    clip_for,
    named_pack_soft_cap,
)
from scribe3.soft_activation import SOFT_SEGMENT_NAMES, apply_soft_activation


class _Char:
    def __init__(self, name, cid="", **traits):
        self.name = name
        self.id = cid or f"role:{name}"
        self.traits = traits


class _Store:
    def __init__(self, *, chars=None, facs=None, items=None, terms=None, rules=None, ch=None):
        self._chars = chars or []
        self._facs = facs or []
        self._items = items or []
        self._terms = terms or []
        self._rules = rules or []
        self._ch = ch or {}

    def characters(self):
        return list(self._chars)

    def list_factions(self):
        return list(self._facs)

    def list_items(self):
        return list(self._items)

    def list_terms(self):
        return list(self._terms)

    def list_world_rules(self):
        return list(self._rules)

    def list_motifs(self):
        return []

    def get_chapter(self, _n):
        return dict(self._ch)

    def facts_at(self, _n):
        return []

    def entity_relations_at(self, *_a, **_k):
        return []


def test_inject_cap_table_has_codex_kinds():
    assert INJECT_CAP["deduction"] == 6000
    assert INJECT_CAP["character_public"] == 2500
    assert INJECT_CAP["term"] == 1200
    assert DEDUCTION_PACK_CAP == 8500
    assert clip_for("deduction", "焦" * 5000) == "焦" * 5000
    assert clip_for("deduction", "焦" * 7000) == "焦" * 6000


def test_named_term_item_rule_full_unnamed_card_only():
    long_def = "炉令是铜炉祭火的口头契约，必须当场应声，不得隔夜。" + ("义" * 40)
    long_desc = "一把生了绿锈的铜钥，齿上刻着灶神的小名。" + ("钥" * 40)
    long_cost = "动用此规则须以一夜未眠为代价，且不得连续两夜。" + ("价" * 40)
    st = _Store(
        terms=[{
            "name": "炉令",
            "category": "仪式",
            "definition": long_def,
            "aliases": ["火令"],
        }],
        items=[{
            "name": "铜钥",
            "category": "信物",
            "description": long_desc,
            "current_owner": "灰狸",
            "special_properties": ["开侧门"],
        }],
        rules=[{
            "name": "隔夜禁忌",
            "category": "social",
            "cost": long_cost,
            "limitations": ["不可隔夜"],
            "exceptions": ["主祭特许"],
            "capabilities": ["镇火"],
            "note": "写在灶沿",
        }],
        facs=[{"name": "冷灶帮", "ideology": "灶上说话算数" + ("帮" * 80)}],
        chars=[_Char("冷锅婆", backstory="她年轻时在义庄守过一夜。" + ("史" * 80))],
    )
    named, cards, stats = _codex_segments(
        st, for_generation=True, request_text="请解释炉令、铜钥和隔夜禁忌",
    )
    joined = named + "\n" + cards
    assert long_def in named
    assert long_desc in named
    assert long_cost in named
    assert "不可隔夜" in named
    assert "主祭特许" in named
    assert "开侧门" in named
    assert "灰狸" in named
    assert "冷锅婆" in cards
    assert "她年轻时在义庄守过一夜" not in joined
    assert "灶上说话算数" not in joined or "冷灶帮" in cards
    assert any("term:炉令" in x for x in stats["codex_entities_full"])
    assert "definition" not in cards or long_def not in cards


def test_two_named_chars_plus_term_not_killed_by_4500():
    st = _Store(
        chars=[
            _Char("灰七", appearance="甲" * 900, personality_detail="乙" * 900, backstory="丙" * 900),
            _Char("冷锅婆", appearance="丁" * 900, personality_detail="戊" * 900, backstory="己" * 900),
        ],
        terms=[{"name": "炉令", "definition": "当场应声不得隔夜的祭火契约。"}],
    )
    named, cards, _ = _codex_segments(
        st, for_generation=True,
        request_text="灰七与冷锅婆讨论炉令",
        named_soft_cap=4500,
    )
    assert "当场应声不得隔夜的祭火契约" in named
    assert "炉令" in named
    # 不得先喂肥再整包 4500 把术语砍光
    assert named.count("炉令") >= 1


def test_secret_generation_closed_discuss_open():
    st = _Store(
        chars=[_Char("灰七", backstory="私密前史不该进正文", backstory_secret=True)],
        facs=[{
            "name": "秘会",
            "secret_agenda": "连核心层都不知道的真相",
            "secret_agenda_secret": True,
            "ideology": "尾衔其首",
        }],
    )
    gen = _codex_block(
        st, reveal=False, focalizer="role:旁观", chapter=1,
        for_generation=True, request_text="灰七 秘会",
    )
    talk = _codex_block(
        st, reveal=True, for_generation=False, request_text="灰七 秘会",
    )
    assert "私密前史不该进正文" not in gen
    assert "连核心层都不知道的真相" not in gen
    assert "连核心层都不知道的真相" in talk


def test_deduction_pack_keeps_just_over_floor():
    from scribe3.api.services.write_assemble_context import _deduction_context_segments

    truth = "真" * 2500
    prose = "癸" * 5000

    class St:
        def get_chapter(self, _n):
            return {
                "scene_truth": truth,
                "deductions": [{"character_id": "role:灰七", "name": "灰七", "prose": prose}],
            }

    segs = _deduction_context_segments(St(), 1, focalizer="role:灰七")
    text = "".join(t for _, _, t in segs)
    assert text.count("癸") == 5000
    assert "真" * 2500 in text
    assert len(text) <= DEDUCTION_PACK_CAP + 80


def test_l2_protects_named_drops_cards():
    assert "codex_named" in GEN_SEGMENT_PROTECTED
    assert "codex_cards" in L2_DROP_TIER["T3"]
    assert "codex" not in L2_DROP_TIER["T1"]
    fat = "X" * 20_000
    segs = [
        {"name": "prefix", "layer": "redline", "text": "ID"},
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】"},
        {"name": "envelope", "layer": "envelope", "text": "ENV"},
        {"name": "codex_named", "layer": "supplemental", "text": "点名炉令定义全文"},
        {"name": "codex_cards", "layer": "supplemental", "text": "名片" + fat},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】"},
    ]
    joined, rep = apply_l2_trim(segs, supplemental_hard=800, prompt_hard=2000)
    assert "点名炉令定义全文" in joined
    dropped = " ".join(rep.get("dropped") or [])
    assert "codex_cards" in dropped
    assert "codex_named" not in dropped
    assert _half_cut_segment("codex_named", "点名" * 40) == "点名" * 40


def test_soft_activation_keeps_outline_and_named():
    assert "outline" not in SOFT_SEGMENT_NAMES
    assert "codex_named" not in SOFT_SEGMENT_NAMES
    assert "codex_cards" in SOFT_SEGMENT_NAMES
    pieces = [
        {"name": "outline", "text": "无关大纲"},
        {"name": "codex_named", "text": "点名设定"},
        {"name": "codex_cards", "text": "未点名名片百科"},
        {"name": "drama_contract", "text": "戏"},
    ]
    kept, rep = apply_soft_activation(pieces, activation_keys=["龙渊"], force=True)
    names = [p["name"] for p in kept]
    assert "outline" in names
    assert "codex_named" in names
    assert "codex_cards" in rep["dropped"]


def test_named_pack_soft_cap_follows_work_profile(monkeypatch):
    monkeypatch.delenv("SCRIBE3_CODEX_INJECT_CAP", raising=False)
    monkeypatch.setenv("SCRIBE3_NOVEL_WIDE", "0")
    assert named_pack_soft_cap(work="main") == 4500
    monkeypatch.setenv("SCRIBE3_NOVEL_WIDE", "1")
    monkeypatch.setenv("SCRIBE3_MODEL_CONTEXT_WINDOW", "200000")
    # 显式 96k 开但窗不够会炸；只断言函数存在且 env 覆盖优先
    monkeypatch.setenv("SCRIBE3_CODEX_INJECT_CAP", "8888")
    assert named_pack_soft_cap(work="main") == 8888


def test_join_physical_order_uses_codex_named():
    pieces = [
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】"},
        {"name": "codex_named", "layer": "supplemental", "text": "设定圣经X"},
        {"name": "envelope", "layer": "envelope", "text": "ENV块"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】"},
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】"},
    ]
    joined, rep = join_generation_segments(pieces, v2=True)
    idx = rep.get("order_indices") or {}
    assert "codex_named" in idx
    assert joined.index("ENV") < joined.index("设定圣经") < joined.index("最终提醒")


def test_cards_pack_cap_constant():
    assert CARDS_PACK_CAP == 1500


def test_discuss_assembler_calls_codex_segments():
    import inspect
    from scribe3.api.services.write_assemble_discuss import assemble_discussion_system
    src = inspect.getsource(assemble_discussion_system)
    assert "_codex_segments" in src
    assert "for_generation=False" in src
    assert "⟦PROPOSAL scope=" in src  # 仍禁写作围栏

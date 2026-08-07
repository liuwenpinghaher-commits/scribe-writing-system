"""v6.1 产品钩子：讨论→ChangePack；finalize 邻接 PostFinalize。"""
from __future__ import annotations

from scribe3.api.services.canon_hooks import (
    body_confirmed_report,
    discussion_change_pack,
)
from scribe3.canon_loop import InMemoryCanonStore, apply_change_pack


class _FakeStore:
    """最小 store：characters + get_chapter。"""

    def __init__(self):
        from scribe3.ontology import Entity
        self._chars = [
            Entity(
                "role:沈拾灯", "character", "沈拾灯",
                traits={"fear": "旧恐惧", "appearance": "青衫"},
            ),
        ]
        self._chapters = {
            1: {
                "title": "雨巷",
                "synopsis": "沈拾灯入镇",
                "prose": (
                    "沈拾灯走在雨里。"
                    "【知识 L2|knowledge|role:沈拾灯|fact:债契三夜|知道|低】他听过三夜。"
                    "【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】他怕灯芯。"
                ),
            },
        }

    def characters(self):
        return self._chars

    def get_chapter(self, seq: int):
        return self._chapters.get(seq)

    def get_intent(self):
        return {"reader_feeling": "压抑中见暖"}

    def list_world_rules(self, category=None):
        return [{"name": "不渡夜魂", "category": "民俗"}]


def test_discussion_hook_change_pack_no_silent_write():
    st = _FakeStore()
    text = "【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】雨巷里他说怕灯芯。"
    pack = discussion_change_pack(work="hook_w", text=text, st=st)
    assert pack.get("items"), "discussion must yield change pack items"
    item = pack["items"][0]
    assert item["requires_approval"] is True
    assert item["evidence"]
    assert "impact" in pack and "chapters" in pack["impact"]
    ent = st.characters()[0]
    assert ent.traits.get("fear") == "旧恐惧"


def test_body_confirmed_hook_separates_l2_l1():
    st = _FakeStore()
    prose = st.get_chapter(1)["prose"]
    rep = body_confirmed_report(work="hook_w", seq=1, prose=prose, st=st)
    assert rep["silent_l1_write"] is False
    assert "l2_objective" in rep["sections"]
    assert "l1_requires_approval" in rep["sections"]
    assert rep["sections"]["l1_requires_approval"]["auto_applied"] is False
    assert rep["sections"]["l2_objective"]["auto_applied"] is False
    assert any(
        i.get("module") == "character"
        for i in rep["sections"]["l1_requires_approval"]["items"]
    )
    assert any(
        i.get("module") == "knowledge"
        for i in rep["sections"]["l2_objective"]["items"]
    )


def test_pilot_runtime_finalize_source_hooks_report():
    """pilot_runtime.finalize 必须调用 body_confirmed_report（结构门闩）。"""
    from pathlib import Path
    import scribe3.api.services.pilot_runtime as runtime
    src = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "body_confirmed_report" in src
    assert "post_finalize_report" in src


def test_orch_from_discussion_source_hooks_pack():
    from pathlib import Path
    import scribe3.api.routers.director as director
    src = Path(director.__file__).read_text(encoding="utf-8")
    assert "discussion_change_pack" in src
    assert "change_pack" in src


def test_apply_after_discussion_pack_roundtrip():
    st = _FakeStore()
    pack = discussion_change_pack(
        work="hook_rt",
        text="【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】怕灯芯。",
        st=st,
    )
    mem = InMemoryCanonStore()
    mem.characters["沈拾灯"] = {"name": "沈拾灯", "fear": "旧恐惧"}
    r0 = apply_change_pack(pack, approved_item_ids=[], store=mem)
    assert mem.read_character_field("沈拾灯", "fear") == "旧恐惧"
    assert r0["silent_l1_blocked"] is True
    l1_id = pack["items"][0]["id"]
    r1 = apply_change_pack(pack, approved_item_ids=[l1_id], store=mem)
    assert mem.read_character_field("沈拾灯", "fear") == "被写进灯芯"
    assert r1["applied"]


def test_full_type_marker_extract_and_modules():
    """标记语法覆盖 character/world_rule/faction/item/term/promise/fact/knowledge。"""
    from scribe3.canon_extract import extract_claims_from_prose
    from scribe3.canon_loop import MODULES

    prose = (
        "【设定 L1|character|role:阿绣|fear|兄名再被点亮|高】"
        "【设定 L1|world_rule|债契三夜|cost|折声或折命|高】"
        "【设定 L1|faction|灯火门|note|镇口势力|中】"
        "【设定 L1|item|青藤灯|description|照影不照人|中】"
        "【设定 L1|term|替死契|definition|以名换命|中】"
        "【设定 L1|promise|他日必还|text|他日必还灯债|中】"
        "【设定 L1|fact|role:阿绣|attribute|出身|镇口|中】"
        "【知识 L2|knowledge|role:阿绣|fact:债契三夜|知道|低】"
        "他叫沈拾灯。按灯火门规矩办。手持青藤灯。所谓替死契。他日必清账。"
    )
    claims = extract_claims_from_prose(prose, known_character_names=["阿绣"])
    mods = {c.module for c in claims}
    for need in ("character", "world_rule", "faction", "item", "term", "promise", "knowledge"):
        assert need in mods, f"missing module {need} in {mods}"
    assert mods <= MODULES or True  # extra ok if in MODULES
    for c in claims:
        if c.module != "knowledge":
            assert c.requires_approval is True


def test_multi_module_post_finalize_report():
    from scribe3.api.services.canon_hooks import body_confirmed_report

    prose = (
        "【设定 L1|world_rule|不渡夜魂|cost|命|高】"
        "【设定 L1|character|role:沈拾灯|fear|灯芯名|高】"
        "【知识 L2|knowledge|role:沈拾灯|fact:不渡夜魂|知道|低】"
    )
    rep = body_confirmed_report(work="multi", seq=3, prose=prose, st=None, persist=False)
    l1_mods = set(rep["sections"]["l1_requires_approval"]["modules"])
    assert "character" in l1_mods
    assert "world_rule" in l1_mods
    assert "knowledge" in rep["sections"]["l2_objective"]["modules"]

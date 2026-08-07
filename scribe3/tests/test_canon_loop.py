"""正典变更闭环：ChangePack / 定稿报告 / L1 批准 apply（纯模块 + 真实入口）。"""
from __future__ import annotations

import pytest

from scribe3.canon_loop import (
    CanonClaim,
    InMemoryCanonStore,
    apply_change_pack,
    build_post_finalize_report,
    pack_from_claims,
    pack_from_discussion_text,
    parse_marker_claims,
)


def test_parse_marker_claims_discussion_setting():
    text = (
        "我们商量把沈拾灯的恐惧钉死。"
        "【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】他怕灯芯上出现自己的名。"
        "另记知识："
        "【知识 L2|knowledge|role:沈拾灯|fact:债契三夜|知道|低】三夜之约他已听闻。"
    )
    claims = parse_marker_claims(text)
    assert len(claims) >= 2
    l1 = next(c for c in claims if c.layer == "L1")
    l2 = next(c for c in claims if c.layer == "L2")
    assert l1.module == "character"
    assert l1.target == "role:沈拾灯"
    assert l1.field == "fear"
    assert l1.after == "被写进灯芯"
    assert l1.risk == "high"
    assert l1.requires_approval is True
    assert "灯芯" in l1.evidence or "怕" in l1.evidence or l1.evidence
    assert l2.requires_approval is False
    assert l2.module == "knowledge"


def test_discussion_change_pack_no_silent_l1(monkeypatch):
    """准则 1：讨论 → ChangePack，不写 L1。"""
    store = InMemoryCanonStore()
    store.characters["沈拾灯"] = {"name": "沈拾灯", "fear": "旧恐惧"}
    snap = store.snapshot()
    text = "【设定 L1|character|role:沈拾灯|fear|被写进灯芯|高】证据：雨巷里他说怕灯芯。"
    pack = pack_from_discussion_text(
        text,
        work="test_work",
        source="discussion",
        canon_snapshot=snap,
        chapter_index={"沈拾灯": [1, 3], "role:沈拾灯": [1, 3]},
    )
    d = pack.to_dict()
    assert d["items"], "must list at least one item"
    item = d["items"][0]
    assert item["layer"] == "L1"
    assert item["target"]
    assert item["after"] == "被写进灯芯"
    assert item["evidence"]
    assert item["risk"] == "high"
    assert item["requires_approval"] is True
    assert item["before"] == "旧恐惧"
    # impact present (criterion 4)
    assert "chapters" in d["impact"]
    assert d["impact"]["chapters"] == [1, 3]
    assert isinstance(d["impact"]["inject_surfaces"], list)
    # no silent write
    assert store.read_character_field("沈拾灯", "fear") == "旧恐惧"


def test_post_finalize_separates_l2_and_l1():
    """准则 2：定稿报告分 L2 客观 vs L1 待批。"""
    prose = (
        "沈拾灯听懂了债契。"
        "【知识 L2|knowledge|role:沈拾灯|fact:债契三夜|知道|低】"
        "【设定 L1|character|role:沈拾灯|surface_goal|查清替死|中】他要把替字查清。"
    )
    report = build_post_finalize_report(seq=7, prose=prose, work="w")
    assert report["silent_l1_write"] is False
    sec = report["sections"]
    assert "l2_objective" in sec and "l1_requires_approval" in sec
    assert sec["l2_objective"]["auto_applied"] is False
    assert sec["l1_requires_approval"]["auto_applied"] is False
    assert "knowledge" in sec["l2_objective"]["modules"]
    assert "character" in sec["l1_requires_approval"]["modules"]
    assert len(sec["l1_requires_approval"]["items"]) >= 1
    # L1 not auto applied — still requires approval
    for it in sec["l1_requires_approval"]["items"]:
        assert it["requires_approval"] is True
        assert it["applied"] is False


def test_apply_rejects_unapproved_l1_and_persists_approved():
    """准则 3：未批 L1 拒绝；批准后写入。"""
    store = InMemoryCanonStore()
    store.characters["沈拾灯"] = {"name": "沈拾灯", "fear": "旧"}
    claims = [
        CanonClaim(
            layer="L1",
            op="patch",
            module="character",
            target="role:沈拾灯",
            field="fear",
            after="被写进灯芯",
            evidence="讨论共识",
            risk="high",
        ),
        CanonClaim(
            layer="L2",
            op="add",
            module="knowledge",
            target="role:沈拾灯",
            field="fact:债契三夜",
            after="知道",
            evidence="正文",
            risk="low",
        ),
    ]
    pack = pack_from_claims(claims, work="w", source="fixture", canon_snapshot=store.snapshot())
    l1_id = next(i.id for i in pack.items if i.layer == "L1")
    l2_id = next(i.id for i in pack.items if i.layer == "L2")

    # unapproved L1
    r0 = apply_change_pack(pack, approved_item_ids=[], apply_objective_l2=True, store=store)
    assert r0["silent_l1_blocked"] is True
    assert any(x["id"] == l1_id for x in r0["rejected"])
    assert store.read_character_field("沈拾灯", "fear") == "旧"
    # L2 objective may apply
    assert any(x.get("item_id") == l2_id for x in r0["applied"]) or any(
        k.get("proposition") == "fact:债契三夜" for k in store.knowledge
    )

    # approved L1
    r1 = apply_change_pack(pack, approved_item_ids=[l1_id], apply_objective_l2=True, store=store)
    assert any(x.get("item_id") == l1_id for x in r1["applied"])
    assert store.read_character_field("沈拾灯", "fear") == "被写进灯芯"


def test_impact_explicit_empty_when_no_index():
    pack = pack_from_claims(
        [CanonClaim(layer="L1", op="patch", module="character", target="role:新人",
                    field="appearance", after="青衫", evidence="e", risk="low")],
        chapter_index={},
    )
    assert pack.impact["chapters"] == []
    assert "inject_surfaces" in pack.impact


def test_l1_client_requires_approval_false_cannot_silent_write():
    """回归：客户端把 L1 标成 requires_approval=False 仍不得静默写。"""
    store = InMemoryCanonStore()
    store.characters["沈拾灯"] = {"name": "沈拾灯", "fear": "旧"}
    pack = pack_from_claims(
        [CanonClaim(
            layer="L1", op="patch", module="character", target="role:沈拾灯",
            field="fear", after="攻击写入", evidence="evil", risk="high",
            requires_approval=False,  # 客户端伪造
        )],
        work="atk",
        canon_snapshot=store.snapshot(),
    )
    # 再强制污染 pack 字段
    pack.items[0].requires_approval = False
    pack.items[0].approved = True
    r = apply_change_pack(pack, approved_item_ids=[], store=store)
    assert r["silent_l1_blocked"] is True
    assert any(x.get("reason") == "l1_requires_approval_not_granted" for x in r["rejected"])
    assert store.read_character_field("沈拾灯", "fear") == "旧"
    assert not any(a.get("item_id") == pack.items[0].id for a in r["applied"])


def test_l1_client_approved_true_without_ids_cannot_silent_write():
    """回归：仅 item.approved=True、approved_item_ids 为空 → 不写。"""
    store = InMemoryCanonStore()
    store.characters["阿绣"] = {"name": "阿绣", "fear": "旧恨"}
    pack = pack_from_claims(
        [CanonClaim(
            layer="L1", op="patch", module="character", target="role:阿绣",
            field="fear", after="伪造批准", evidence="e", risk="high",
        )],
        work="atk2",
        canon_snapshot=store.snapshot(),
    )
    pack.items[0].approved = True
    r = apply_change_pack(pack, approved_item_ids=None, store=store)
    assert store.read_character_field("阿绣", "fear") == "旧恨"
    assert r["silent_l1_blocked"] is True
    assert r["rejected"]


def test_http_apply_strips_client_approved_l1():
    """HTTP 入口同样不信 pack JSON 自批。"""
    from scribe3.api.routers.canon_loop import ApplyPackReq, apply_change_pack_ep

    evil_pack = {
        "id": "cp_evil",
        "work": "http_atk",
        "source": "attack",
        "items": [{
            "id": "ci_evil",
            "layer": "L1",
            "op": "patch",
            "module": "character",
            "target": "role:阿绣",
            "field": "fear",
            "after": "HTTP伪造",
            "evidence": "x",
            "risk": "high",
            "requires_approval": False,
            "approved": True,
            "applied": False,
        }],
        "impact": {"chapters": [], "inject_surfaces": []},
        "status": "proposed",
    }
    out = apply_change_pack_ep(ApplyPackReq(
        pack=evil_pack,
        approved_item_ids=[],
        work="http_atk",
        seed_snapshot={"characters": {"阿绣": {"fear": "稳"}}},
    ))
    assert out["silent_l1_blocked"] is True
    assert out["store_snapshot"]["characters"]["阿绣"]["fear"] == "稳"


def test_character_layer_l2_spoof_cannot_silent_write():
    """回归：character + layer=L2 + 空 approved_item_ids → store 不变且 reject。"""
    store = InMemoryCanonStore()
    store.characters["沈拾灯"] = {"name": "沈拾灯", "fear": "旧恐惧"}
    pack = pack_from_claims(
        [CanonClaim(
            layer="L2",  # 伪装
            op="patch",
            module="character",
            target="role:沈拾灯",
            field="fear",
            after="L2伪装写入",
            evidence="spoof",
            risk="low",
            requires_approval=False,
        )],
        work="spoof",
        canon_snapshot=store.snapshot(),
    )
    pack.items[0].layer = "L2"
    pack.items[0].requires_approval = False
    pack.items[0].approved = True
    r = apply_change_pack(pack, approved_item_ids=[], store=store)
    assert store.read_character_field("沈拾灯", "fear") == "旧恐惧"
    assert r["silent_l1_blocked"] is True
    assert any(x.get("reason") == "l1_requires_approval_not_granted" for x in r["rejected"])
    assert not r["applied"]


def test_world_rule_layer_l2_spoof_cannot_silent_write():
    store = InMemoryCanonStore()
    store.world_rules["不渡夜魂"] = "原规则"
    pack = pack_from_claims(
        [CanonClaim(
            layer="L2",
            op="patch",
            module="world_rule",
            target="不渡夜魂",
            field=None,
            after="被静默改掉",
            evidence="spoof",
            risk="high",
            requires_approval=False,
        )],
        work="spoof_rule",
        canon_snapshot=store.snapshot(),
    )
    r = apply_change_pack(pack, approved_item_ids=[], store=store)
    assert store.world_rules["不渡夜魂"] == "原规则"
    assert r["silent_l1_blocked"] is True
    assert r["rejected"]


def test_http_character_layer_l2_spoof_blocked():
    """HTTP：layer=L2 + module=character + empty approved_item_ids → fear 不变。"""
    from scribe3.api.routers.canon_loop import ApplyPackReq, apply_change_pack_ep

    pack = {
        "id": "cp_l2http",
        "work": "http_l2spoof",
        "source": "attack",
        "items": [{
            "id": "ci_l2http",
            "layer": "L2",
            "op": "patch",
            "module": "character",
            "target": "role:阿绣",
            "field": "fear",
            "after": "L2HTTP",
            "evidence": "x",
            "risk": "low",
            "requires_approval": False,
            "approved": True,
            "applied": False,
        }],
        "impact": {"chapters": [], "inject_surfaces": []},
        "status": "proposed",
    }
    out = apply_change_pack_ep(ApplyPackReq(
        pack=pack,
        approved_item_ids=[],
        work="http_l2spoof",
        seed_snapshot={"characters": {"阿绣": {"fear": "稳"}}},
    ))
    assert out["silent_l1_blocked"] is True
    assert out["store_snapshot"]["characters"]["阿绣"]["fear"] == "稳"
    assert any(r.get("id") == "ci_l2http" for r in out["rejected"])


def test_http_handlers_importable_and_pack_shape():
    """准则：服务入口可调用（与 router 同函数）。"""
    from scribe3.api.routers.canon_loop import (
        ChangePackFromTextReq,
        PostFinalizeReq,
        ApplyPackReq,
        change_pack_from_text,
        post_finalize_report_ep,
        apply_change_pack_ep,
    )

    pack = change_pack_from_text(ChangePackFromTextReq(
        text="【设定 L1|character|role:阿绣|fear|兄名再被点亮|高】她恨灯芯。",
        work="http_w",
        source="discussion",
        chapter_index={"阿绣": [2, 6]},
    ))
    assert pack["items"][0]["layer"] == "L1"
    assert pack["impact"]["chapters"] == [2, 6]

    rep = post_finalize_report_ep(PostFinalizeReq(
        seq=2,
        prose="【知识 L2|knowledge|role:阿绣|fact:灯芯名|知道|低】",
        work="http_w",
    ))
    assert rep["sections"]["l2_objective"]["items"]

    # apply without approval → reject L1
    pack2 = change_pack_from_text(ChangePackFromTextReq(
        text="【设定 L1|character|role:阿绣|fear|新恐惧|高】",
        work="http_w2",
        canon_snapshot={"characters": {"阿绣": {"fear": "旧"}}},
    ))
    out = apply_change_pack_ep(ApplyPackReq(
        pack=pack2,
        approved_item_ids=[],
        work="http_w2",
        seed_snapshot={"characters": {"阿绣": {"fear": "旧"}}},
    ))
    assert out["silent_l1_blocked"] is True
    assert out["store_snapshot"]["characters"]["阿绣"]["fear"] == "旧"

    l1 = pack2["items"][0]["id"]
    out2 = apply_change_pack_ep(ApplyPackReq(
        pack=pack2,
        approved_item_ids=[l1],
        work="http_w2",
        seed_snapshot={"characters": {"阿绣": {"fear": "旧"}}},
    ))
    assert out2["store_snapshot"]["characters"]["阿绣"]["fear"] == "新恐惧"

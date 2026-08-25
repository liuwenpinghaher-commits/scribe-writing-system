"""素材转正典：新开 MCP 审批，禁止改素材本身。"""
from __future__ import annotations

import asyncio

import scribe3.mcp as M


class _AcceptCtx:
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "accept"})()


class _DeclineCtx:
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "decline"})()


def test_promote_material_tool_is_write_gated():
    assert "s3_promote_material" in M.WRITE_GATED
    assert hasattr(M, "s3_promote_material")


def test_promote_material_writes_fact_without_patching_material(store):
    mid = store.add_material("密室白描", "寒气逼人", "snippet", summary="以物写情")
    before = dict(store.get_material(mid))
    M.set_store(store, work=store.db_name)

    out = asyncio.run(M.s3_promote_material(
        _AcceptCtx(),
        material_id=mid,
        target="fact",
        entity="role:沈砚",
        attribute="state",
        value="会密室白描",
        valid_from=1,
        work=store.db_name,
    ))
    assert out.get("status") == "written", out
    assert out.get("source_material_id") == mid
    fact_id = out.get("fact_id")
    assert fact_id
    fact = store.fact(fact_id)
    assert fact is not None
    assert fact.value == "会密室白描"
    assert (getattr(fact, "source", None) or "") == f"material:{mid}"
    after = store.get_material(mid)
    assert after["title"] == before["title"]
    assert after["body"] == before["body"]
    assert after.get("origin") == before.get("origin")


def test_promote_material_decline_does_not_write(store):
    mid = store.add_material("不转", "正文", "note")
    M.set_store(store, work=store.db_name)
    out = asyncio.run(M.s3_promote_material(
        _DeclineCtx(),
        material_id=mid,
        target="fact",
        entity="role:甲",
        attribute="state",
        value="不该落库",
        valid_from=1,
        work=store.db_name,
    ))
    assert out.get("status") == "declined"
    assert store.fact(out.get("fact_id") or "fact:missing") is None


def test_promote_material_missing_id_errors_before_approval():
    class _Boom:
        async def elicit(self, message, schema):
            raise AssertionError("缺素材不得进入审批")

    out = asyncio.run(M.s3_promote_material(
        _Boom(), material_id="", target="fact",
        entity="role:甲", attribute="state", value="x", valid_from=1, work="main"))
    assert out.get("status") == "error"

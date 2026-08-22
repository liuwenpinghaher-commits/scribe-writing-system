"""结构写工具 MCP 门控 TDD:卷/章 meta/章 plan/弧光锚。

每个工具:∈ WRITE_GATED、签名、decline 不写、accept 落库读回、
patch 目标不存在 → status=error(False 返回)。
"""
from __future__ import annotations

import asyncio
import inspect

import scribe3.mcp as M
from scribe3.ontology import Entity


class _AcceptCtx:
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "accept"})()


# ===== Task 3: volume =====

def test_volume_tools_in_write_gated():
    assert "s3_add_volume" in M.WRITE_GATED
    assert "s3_patch_volume" in M.WRITE_GATED
    assert M.requires_approval("s3_add_volume") is True
    assert M.requires_approval("s3_patch_volume") is True


def test_s3_add_volume_signatures():
    sig = inspect.signature(M.s3_add_volume)
    for p in ("title", "sort_order", "intro", "color", "work"):
        assert p in sig.parameters, f"s3_add_volume 缺参数 {p}"
    sig_p = inspect.signature(M.s3_patch_volume)
    for p in ("volume_id", "title", "sort_order", "intro", "color", "work"):
        assert p in sig_p.parameters, f"s3_patch_volume 缺参数 {p}"


def test_s3_add_volume_decline_blocks(store):
    M.set_store(store)
    before = store.list_volumes()
    out = M.commit_if_approved(
        "s3_add_volume", False,
        lambda: store.add_volume("卷一·不该出现", sort_order=1))
    assert out["status"] == "declined"
    assert store.list_volumes() == before


def test_s3_add_volume_accept_persists(store):
    M.set_store(store)
    out = M.commit_if_approved(
        "s3_add_volume", True,
        lambda: store.add_volume("卷一·潮生", sort_order=0, intro="入世"))
    assert out["status"] == "written"
    vols = store.list_volumes()
    assert any(v.get("title") == "卷一·潮生" for v in vols)


def test_s3_patch_volume_accept_and_missing(store):
    M.set_store(store)
    vid = store.add_volume("旧题", sort_order=0)

    def _patch_ok():
        ok = store.update_volume(vid, {"title": "新题", "intro": "改写"})
        return ok if ok else False

    out = M.commit_if_approved("s3_patch_volume", True, _patch_ok)
    assert out["status"] == "written"
    row = next(v for v in store.list_volumes() if v["id"] == vid)
    assert row["title"] == "新题"

    out2 = M.commit_if_approved(
        "s3_patch_volume", True,
        lambda: store.update_volume("no_such_vol", {"title": "x"}) or False)
    assert out2["status"] == "error"


# ===== Task 4: chapter meta =====

def test_chapter_tools_in_write_gated():
    assert "s3_add_chapter" in M.WRITE_GATED
    assert "s3_patch_chapter_meta" in M.WRITE_GATED
    assert "s3_refreeze_chapter" in M.WRITE_GATED
    assert M.requires_approval("s3_add_chapter") is True
    assert M.requires_approval("s3_patch_chapter_meta") is True
    assert M.requires_approval("s3_refreeze_chapter") is True


def test_s3_add_chapter_signatures():
    sig = inspect.signature(M.s3_add_chapter)
    for p in ("title", "volume_id", "work"):
        assert p in sig.parameters, f"s3_add_chapter 缺参数 {p}"
    sig_m = inspect.signature(M.s3_patch_chapter_meta)
    for p in ("seq", "title", "label", "volume_id", "clear_volume", "confidence", "work"):
        assert p in sig_m.parameters, f"s3_patch_chapter_meta 缺参数 {p}"
    sig_r = inspect.signature(M.s3_refreeze_chapter)
    for p in ("seq", "work"):
        assert p in sig_r.parameters, f"s3_refreeze_chapter 缺参数 {p}"


def test_s3_add_chapter_accept(store):
    M.set_store(store)
    vid = store.add_volume("卷一", sort_order=0)

    def _write():
        return store.create_chapter(title="开篇", volume_id=vid)

    out = M.commit_if_approved("s3_add_chapter", True, _write)
    assert out["status"] == "written"
    chs = store.list_chapters()
    assert any(c.get("title") == "开篇" for c in chs)


def test_s3_add_chapter_decline(store):
    M.set_store(store)
    n0 = len(store.list_chapters())
    out = M.commit_if_approved(
        "s3_add_chapter", False,
        lambda: store.create_chapter(title="幽灵章"))
    assert out["status"] == "declined"
    assert len(store.list_chapters()) == n0


def test_s3_patch_chapter_meta_missing_returns_error(store):
    M.set_store(store)
    out = M.commit_if_approved(
        "s3_patch_chapter_meta", True,
        lambda: store.update_chapter_meta(99999, {"title": "无"}) or False)
    assert out["status"] == "error"


def test_s3_patch_chapter_meta_title_and_label(store):
    M.set_store(store)
    store.save_chapter(1, "正文", title="旧")
    # label schema: NONE | draft|revise|done|idea|beat
    out = M.commit_if_approved(
        "s3_patch_chapter_meta", True,
        lambda: (store.update_chapter_meta(1, {"title": "新题", "label": "idea"}) or False))
    assert out["status"] == "written"
    ch = store.get_chapter(1)
    assert ch["title"] == "新题"
    assert ch.get("label") == "idea"


# ===== Task 5: chapter plan =====

def test_patch_chapter_plan_in_write_gated():
    assert "s3_patch_chapter_plan" not in M.WRITE_GATED


def test_s3_patch_chapter_meta_synopsis_signature():
    sig = inspect.signature(M.s3_patch_chapter_meta)
    assert "synopsis" in sig.parameters


def test_s3_generate_stage_focalizer_signature():
    sig = inspect.signature(M.s3_generate_stage)
    assert "focalizer" in sig.parameters


def test_s3_patch_chapter_meta_blank_synopsis_errors():
    out = asyncio.run(M.s3_patch_chapter_meta(_AcceptCtx(), 1, synopsis="   "))
    assert out.get("status") == "error"
    assert out.get("code") == "synopsis_blank"


def test_s3_patch_chapter_plan_signatures():
    sig = inspect.signature(M.s3_patch_chapter_plan)
    for p in ("seq", "synopsis", "beats", "scene_truth", "deductions",
              "involved_characters", "work"):
        assert p in sig.parameters, f"s3_patch_chapter_plan 缺参数 {p}"


def test_patch_chapter_plan_synopsis_beats(store):
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    beats = [{"text": "沈砚入城"}, {"text": "季棠试探"}]

    def _write():
        ok = store.update_chapter_meta(1, {
            "synopsis": "开篇立人物与潮信",
            "beats": beats,
            "scene_truth": "城门盘查在即",
            "involved_characters": ["沈砚"],
            "deductions": [{"character_id": "沈砚", "prose": "### 看到/听到\n城门"}],
        })
        return ok if ok else False

    out = M.commit_if_approved("s3_patch_chapter_plan", True, _write)
    assert out["status"] == "written"
    ch = store.get_chapter(1)
    assert "潮信" in (ch.get("synopsis") or "")
    assert isinstance(ch.get("beats"), list) and len(ch["beats"]) == 2
    assert "盘查" in (ch.get("scene_truth") or "")
    assert ch["involved_characters"] == ["role:沈砚"]
    assert ch["deductions"][0]["character_id"] == "role:沈砚"
    assert ch["deductions"][0].get("based_on_truth_rev") == ch.get("scene_truth_revision")


def test_patch_chapter_plan_decline(store):
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"synopsis": "原大纲"})
    out = M.commit_if_approved(
        "s3_patch_chapter_plan", False,
        lambda: store.update_chapter_meta(1, {"synopsis": "不该写入"}) or False)
    assert out["status"] == "declined"
    assert store.get_chapter(1).get("synopsis") == "原大纲"


def test_patch_chapter_plan_missing_returns_error(store):
    M.set_store(store)
    out = M.commit_if_approved(
        "s3_patch_chapter_plan", True,
        lambda: store.update_chapter_meta(88888, {"synopsis": "无"}) or False)
    assert out["status"] == "error"


def test_s3_patch_chapter_plan_normalizes_beats_and_rejects_malformed_involved(store):
    """真人 Run 常见的 beat 别名要归一;混入投影文本的角色字段必须在写前失败。"""
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))

    written = asyncio.run(M.s3_patch_chapter_plan(
        _AcceptCtx(), 1,
        beats=[{"beat": "沈砚推门"}, {"text": "老道回避"}],
        involved_characters=["沈砚"],
    ))
    assert written["status"] == "written"
    assert store.get_chapter(1)["beats"] == [
        {"text": "沈砚推门"}, {"text": "老道回避"},
    ]
    assert store.get_chapter(1)["involved_characters"] == ["role:沈砚"]

    before = store.get_chapter(1)
    invalid = asyncio.run(M.s3_patch_chapter_plan(
        _AcceptCtx(), 1,
        involved_characters=["role:'role:沈砚', 'deductions': '错误混入'"],
    ))
    assert invalid["status"] == "error"
    assert "involved_characters" in invalid["error"]
    assert store.get_chapter(1)["involved_characters"] == before["involved_characters"]


def test_s3_patch_chapter_plan_rejects_empty_or_incomplete_deductions_for_involved_roles(store):
    """演绎工具收到 deductions 时，不能接受把已涉及角色留成无投影的假成功。"""
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.add_entity(Entity("role:老道", "character", "老道"))

    empty = asyncio.run(M.s3_patch_chapter_plan(
        _AcceptCtx(), 1,
        involved_characters=["沈砚", "老道"],
        deductions=[],
    ))
    assert empty["status"] == "error"
    assert "deductions" in empty["error"]

    incomplete = asyncio.run(M.s3_patch_chapter_plan(
        _AcceptCtx(), 1,
        involved_characters=["沈砚", "老道"],
        deductions=[{"character_id": "沈砚", "prose": "### 看到/听到\\n老道沉默"}],
    ))
    assert incomplete["status"] == "error"
    assert "缺少" in incomplete["error"]


def test_s3_ingest_chapter_keeps_every_direct_provider_call_bounded(store, monkeypatch):
    """MCP 桥接上限是 300 秒；主抽取与空事件后的专用补抽都必须有更短的预算。"""
    M.set_store(store)
    store.save_chapter(1, "沈砚推门，老道沉默。", title="一")
    calls = []

    def complete(prompt, **kwargs):
        calls.append(kwargs)
        return '{"learned":[],"did":[],"voice_shift":[],"arc":[],"events":[]}'

    monkeypatch.setattr("scribe3.llm.hermes_complete", complete)
    result = M.s3_ingest_chapter(1)

    assert result["applied"] == 0
    # 空 events 会触发有界的专用事件补抽；本断言保护的是所有直连调用的
    # 时限契约，而不是把「只调用一次」这个已废弃的实现细节固化下来。
    assert calls
    assert all(call == {"timeout": 90.0, "max_tokens": 1600, "retries_override": 0}
               for call in calls)


# ===== Task 6: char anchors =====

def test_set_char_anchors_in_write_gated():
    assert "s3_set_char_anchors" in M.WRITE_GATED
    assert M.requires_approval("s3_set_char_anchors") is True


def test_s3_set_char_anchors_signatures():
    sig = inspect.signature(M.s3_set_char_anchors)
    for p in ("character_id", "want", "need", "lie", "ghost", "truth",
              "arc_type", "private_agenda", "work"):
        assert p in sig.parameters, f"s3_set_char_anchors 缺参数 {p}"


def test_set_char_anchors_accept_persists(store):
    from scribe3.ontology import Entity
    M.set_store(store)
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))

    def _write():
        store.set_char_anchors("role:沈砚", {
            "want": "查明潮信",
            "lie": "潮信只是气象",
            "arc_type": "disillusionment",
        })
        return {"character_id": "role:沈砚"}

    out = M.commit_if_approved("s3_set_char_anchors", True, _write)
    assert out["status"] == "written"
    a = store.char_anchors("role:沈砚")
    assert a.get("want") == "查明潮信"
    assert "气象" in (a.get("lie") or "")


def test_set_char_anchors_decline_blocks(store):
    from scribe3.ontology import Entity
    M.set_store(store)
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.set_char_anchors("role:沈砚", {"want": "原 want"})
    out = M.commit_if_approved(
        "s3_set_char_anchors", False,
        lambda: store.set_char_anchors("role:沈砚", {"want": "不该写入"}))
    assert out["status"] == "declined"
    assert store.char_anchors("role:沈砚").get("want") == "原 want"

"""结构写工具 MCP 门控 TDD:卷/章 meta/章 plan/弧光锚。

每个工具:∈ WRITE_GATED、签名、decline 不写、accept 落库读回、
patch 目标不存在 → status=error(False 返回)。
"""
from __future__ import annotations

import inspect

import scribe3.mcp as M


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
    assert M.requires_approval("s3_add_chapter") is True
    assert M.requires_approval("s3_patch_chapter_meta") is True


def test_s3_add_chapter_signatures():
    sig = inspect.signature(M.s3_add_chapter)
    for p in ("title", "volume_id", "work"):
        assert p in sig.parameters, f"s3_add_chapter 缺参数 {p}"
    sig_m = inspect.signature(M.s3_patch_chapter_meta)
    for p in ("seq", "title", "label", "volume_id", "clear_volume", "work"):
        assert p in sig_m.parameters, f"s3_patch_chapter_meta 缺参数 {p}"


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
    assert "s3_patch_chapter_plan" in M.WRITE_GATED
    assert M.requires_approval("s3_patch_chapter_plan") is True


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
            "deductions": [{"claim": "潮信与失踪有关"}],
        })
        return ok if ok else False

    out = M.commit_if_approved("s3_patch_chapter_plan", True, _write)
    assert out["status"] == "written"
    ch = store.get_chapter(1)
    assert "潮信" in (ch.get("synopsis") or "")
    assert isinstance(ch.get("beats"), list) and len(ch["beats"]) == 2
    assert "盘查" in (ch.get("scene_truth") or "")


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

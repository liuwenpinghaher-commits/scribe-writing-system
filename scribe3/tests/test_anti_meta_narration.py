"""PR-1 dual-lamp anti-meta — pure unit tests against shipped detector."""
from scribe3.anti_meta_narration import is_meta_span, scan_anti_meta
from scribe3.review.blocking import is_blocking_issue
from scribe3.reader_ready import anti_meta_issues_for_post, assert_reader_claim, build_reader_ready


# 齿边-style tail (positive acceptance-speak)
CH2_TAIL = """
信息差维持到章末：缺口露一线，用途不写明。伏笔触碰：齿边、铜匙、炉灰、温着、铜腥。
读者知道那是旧库钥匙；他知道；灰狸不知道——这道差，就是今夜的全部胜负。
伏笔仍 open：铜匙齿边缺口要回收——本章只 touch，不 close。
余烬主题在炉灰、温着、铜腥里轻轻回响。
"""

CLEAN = """晨光落在灰狸背上。覃灰七侧身，假铜片在掌心一转。
「给我看看。」灰狸伸手。冷锅婆嗓子像砂纸：「炉子还温着。」
灰七把真匙按进衣襟，齿边硌着皮肉。
"""


def test_ch2_tail_hits_claim_blocking():
    r = scan_anti_meta(CH2_TAIL)
    assert r["ok_for_claim"] is False
    ids = {h["id"] for h in r["hits"]}
    assert "M2" in ids  # 信息差维持 / 伏笔触碰
    assert "M1" in ids or "M6" in ids
    assert "M3" in ids
    assert any(h["severity"] == "claim_blocking" for h in r["hits"])


def test_clean_scene_ok_for_claim():
    r = scan_anti_meta(CLEAN)
    assert r["ok_for_claim"] is True
    assert r["claim_blocking_ids"] == []


def test_m8_chapter_boundary_is_claim_blocking():
    r = scan_anti_meta("上一章末他就数过，这一章里没有人开口。")
    assert r["ok_for_claim"] is False
    assert "M8" in r["claim_blocking_ids"]


def test_negative_open_dialogue_no_m1_claim():
    r = scan_anti_meta("「Open the door,」灰狸说。他推门进去。")
    assert r["ok_for_claim"] is True


def test_negative_reader_appendix_soft_only():
    r = scan_anti_meta("读者须知：本卷地图见附录。")
    # no 信息差/伏笔 co-occur → not claim_blocking alone
    blocking = [h for h in r["hits"] if h["severity"] == "claim_blocking"]
    assert blocking == []
    assert r["ok_for_claim"] is True


def test_negative_bu_zhidao_without_reader():
    r = scan_anti_meta("冷锅婆不知道炉里藏着什么。")
    assert r["ok_for_claim"] is True


def test_is_meta_span_intersects():
    r = scan_anti_meta("信息差维持到章末。他推门。")
    hits = r["hits"]
    assert hits
    h0 = hits[0]
    assert is_meta_span("信息差维持到章末。他推门。", h0["start"], h0["end"], hits)
    assert not is_meta_span("信息差维持到章末。他推门。", 50, 60, hits)


def test_anti_meta_never_is_blocking_issue():
    issues = anti_meta_issues_for_post(CH2_TAIL)
    assert issues
    for iss in issues:
        assert is_blocking_issue(iss) is False


def test_build_reader_ready_red_without_beats():
    rr = build_reader_ready(CLEAN, require_scene_cover=True, load_ack=False)
    assert rr["scene_cover"]["ok"] is None
    assert rr["machine_reader_ok"] is False
    assert rr["lamps"]["reader"]["phase"] == "red"


def test_build_reader_ready_yellow_with_beats_clean():
    beats = [
        {"text": "灰狸伸手"},
        {"text": "冷锅婆嗓子"},
        {"text": "齿边硌着"},
    ]
    rr = build_reader_ready(
        CLEAN, beats=beats, require_scene_cover=True, load_ack=False, work="w", seq=1
    )
    assert rr["anti_meta"]["ok_for_claim"] is True
    assert rr["scene_cover"]["ok"] is True
    assert rr["machine_reader_ok"] is True
    assert rr["lamps"]["reader"]["phase"] == "yellow"
    assert rr["claims"]["may_claim_readable"] is False  # no ack


def test_assert_reader_claim_refuses_meta():
    beats = [{"text": "齿边"}, {"text": "铜匙"}, {"text": "炉灰"}]
    out = assert_reader_claim(
        CH2_TAIL, beats=beats, require_ack=False, work="w", seq=1, st=None
    )
    # with beats only, no st — assert needs context if no beats... we passed beats
    assert out["allowed"] is False
    assert out["code"] == "reader_claim"


def test_assert_reader_claim_refuses_missing_ack():
    beats = [
        {"text": "灰狸伸手"},
        {"text": "冷锅婆嗓子"},
        {"text": "齿边硌着"},
    ]

    class FakeSt:
        def get_chapter(self, seq):
            return {"beats": beats}

        def get_reader_ack(self, work, seq):
            return None

    out = assert_reader_claim(
        CLEAN, st=FakeSt(), work="book", seq=2, require_ack=True
    )
    assert out["allowed"] is False
    assert out["code"] == "reader_ack_required"


def test_assert_reader_claim_ok_with_ack():
    from scribe3.review.fp import prose_fp

    beats = [
        {"text": "灰狸伸手"},
        {"text": "冷锅婆嗓子"},
        {"text": "齿边硌着"},
    ]
    fp = prose_fp(CLEAN)

    class FakeSt:
        def get_chapter(self, seq):
            return {"beats": beats}

        def get_reader_ack(self, work, seq):
            return {"prose_fp": fp, "work": work, "seq": seq}

    out = assert_reader_claim(
        CLEAN, st=FakeSt(), work="book", seq=2, require_ack=True
    )
    assert out["allowed"] is True
    assert out["code"] == "ok"
    assert out["reader_ready"]["lamps"]["reader"]["phase"] == "green"

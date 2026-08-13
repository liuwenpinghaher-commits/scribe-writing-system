"""Drive shipped parsers against book_79c0d45e evidence (no Surreal, no network)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evidence" / "v634-true-chat-20260814"
sys.path.insert(0, str(ROOT / "scripts"))
from v634_evidence_checklist import _parse_wordcount  # noqa: E402


def _claims_of(post: dict) -> dict:
    """Accept both live summary shape and full post-check payload."""
    if isinstance(post.get("claims"), dict):
        return post["claims"]
    rr = post.get("reader_ready") or {}
    if isinstance(rr.get("claims"), dict):
        return rr["claims"]
    return {}


def _scene_cover_of(post: dict) -> dict:
    if isinstance(post.get("scene_cover"), dict):
        return post["scene_cover"]
    rr = post.get("reader_ready") or {}
    if isinstance(rr.get("scene_cover"), dict):
        return rr["scene_cover"]
    return {}


def _ai_grade_of(post: dict) -> str:
    g = post.get("ai_grade")
    if isinstance(g, str):
        return g
    if isinstance(g, dict):
        return str(g.get("grade") or "")
    return ""


def test_parse_wordcount_on_real_rollup():
    text = (EV / "08-wordcount-rollup.md").read_text(encoding="utf-8")
    n = _parse_wordcount(text)
    assert n == 31614, n
    wc = json.loads((EV / "wordcount.json").read_text(encoding="utf-8"))
    assert wc["visible_finalized_1_5"] == n
    assert wc["slug"] == "book_79c0d45e"


def test_wcg_json_pass_true():
    wcg = json.loads((EV / "00-world-complete-gate.json").read_text(encoding="utf-8"))
    assert wcg["pass"] is True
    assert int(wcg.get("fail_count") or 0) == 0
    assert wcg.get("slug") == "book_79c0d45e"


def test_post_check_ch3_fields_block_readable_claim():
    post = json.loads(
        (EV / "13-capability-audit" / "post-check-ch3.json").read_text(encoding="utf-8")
    )
    claims = _claims_of(post)
    sc = _scene_cover_of(post)
    assert claims.get("may_claim_scaffold") is True
    assert claims.get("may_claim_readable") is False
    assert sc.get("ok") is False
    assert int(sc.get("valid") or 0) == 0
    assert int(sc.get("total") or 0) == 3
    assert _ai_grade_of(post) == "heavy"


if __name__ == "__main__":
    test_parse_wordcount_on_real_rollup()
    test_wcg_json_pass_true()
    test_post_check_ch3_fields_block_readable_claim()
    print("PASS test_v634_book79_analysis_parsers")

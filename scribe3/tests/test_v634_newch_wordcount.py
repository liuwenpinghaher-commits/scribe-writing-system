"""本轮新章 6–10：驱动已上线 visible_length / _parse_wordcount / WCG。

serialize 文件是 demo GET /chapter 的全文（非摘录）。字数由 shipped
`scribe3.prose_sanitize.visible_length` 对正文求和，禁止写死合计。
无 Surreal、无网络。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evidence" / "v634-newch-20260814"
sys.path.insert(0, str(ROOT / "scripts"))
from v634_evidence_checklist import _parse_wordcount  # noqa: E402
from scribe3.prose_sanitize import strip_pollution, visible_length


def _serialize_files() -> list[Path]:
    files = sorted((EV / "04-serialize").glob("ch*.md"))
    assert len(files) == 5, files
    return files


def test_visible_sum_from_shipped_sanitize_over_20k():
    per = []
    total = 0
    for p in _serialize_files():
        text = p.read_text(encoding="utf-8")
        assert "fallback" not in text
        clean = strip_pollution(text)
        assert "fallback" not in clean
        n = visible_length(text)
        assert n > 80, (p.name, n)
        per.append(n)
        total += n
    assert total >= 20000, (total, per)
    rollup = _parse_wordcount((EV / "08-wordcount-rollup.md").read_text(encoding="utf-8"))
    assert rollup == total, (rollup, total)
    wc = json.loads((EV / "wordcount.json").read_text(encoding="utf-8"))
    assert wc["visible_new"] == total
    assert wc["slug"] == "book_79c0d45e"
    assert wc["pass"] is True
    assert [c["visible"] for c in wc["chapters"]] == per


def test_wcg_still_pass_true():
    wcg = json.loads((EV / "00-world-complete-gate.json").read_text(encoding="utf-8"))
    assert wcg["pass"] is True
    assert int(wcg.get("fail_count") or 0) == 0
    assert wcg.get("slug") == "book_79c0d45e"


if __name__ == "__main__":
    test_visible_sum_from_shipped_sanitize_over_20k()
    test_wcg_still_pass_true()
    print("PASS test_v634_newch_wordcount")

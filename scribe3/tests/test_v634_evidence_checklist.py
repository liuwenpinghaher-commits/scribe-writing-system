"""Pure unit tests for scripts/v634_evidence_checklist.py (real entrypoints)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "v634_evidence_checklist.py"

# Import shipped module by path for direct function tests
sys.path.insert(0, str(ROOT / "scripts"))
from v634_evidence_checklist import (  # noqa: E402
    check_package,
    _parse_wordcount,
    _author_path_says_human,
)


def _write_matrix(dir_: Path, items: list[dict], **kw) -> None:
    body = {
        "version": "v6.3.4",
        "slug": "book_test",
        "wave": "all",
        "items": items,
        "should_rate": kw.get("should_rate", 0.0),
        "must_failed": kw.get("must_failed", []),
        "author_human": kw.get("author_human", False),
    }
    (dir_ / "02-feature-matrix.json").write_text(
        json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_parse_wordcount_and_human():
    assert _parse_wordcount("合计：20100 字") == 20100
    assert _parse_wordcount("total: 500") is None or _parse_wordcount("total: 500") == 500
    WC_ok = _parse_wordcount("可见字 **19500**")
    assert WC_ok is not None and 18000 <= WC_ok <= 24000
    assert _author_path_says_human("- 作者是否真人坐浏览器：是\n") is True
    assert _author_path_says_human("- 作者是否真人坐浏览器：否\n") is False
    # markdown bold (shipped evidence package style)
    assert _author_path_says_human("- 作者是否真人坐浏览器：**否**\n") is False
    assert _author_path_says_human("- 作者是否真人坐浏览器：**是**\n") is True
    assert _author_path_says_human("- 作者是否真人坐浏览器： **否** \n") is False


def test_empty_matrix_fails(tmp_path: Path):
    _write_matrix(tmp_path, [])
    errs = check_package(tmp_path)
    assert any("empty" in e.lower() or "missing" in e.lower() for e in errs)


def test_empty_status_fails(tmp_path: Path):
    _write_matrix(
        tmp_path,
        [{"id": "J1", "priority": "Must", "status": "", "evidence_path": [], "evidence_type": "API"}],
    )
    errs = check_package(tmp_path)
    assert any("empty status" in e for e in errs)


def test_pass_without_evidence_fails(tmp_path: Path):
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "PASS",
            "evidence_path": [],
            "evidence_type": "API",
        }],
    )
    errs = check_package(tmp_path)
    assert any("evidence_path" in e for e in errs)


def test_pass_with_missing_files_fails(tmp_path: Path):
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "PASS",
            "evidence_path": ["screenshots/nope.png"],
            "evidence_type": "UI",
        }],
    )
    errs = check_package(tmp_path)
    assert any("missing on disk" in e for e in errs)


def test_honest_fail_partial_ok(tmp_path: Path):
    (tmp_path / "00-author-path.md").write_text(
        "# 00-author-path\n- 作者是否真人坐浏览器：否\n", encoding="utf-8"
    )
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "FAIL",
            "evidence_path": [],
            "evidence_type": "API",
            "notes": "not run",
        }],
        author_human=False,
    )
    (tmp_path / "09-final-closure.md").write_text(
        "verdict: PARTIAL\n总 PASS：false\n", encoding="utf-8"
    )
    errs = check_package(tmp_path, expect_partial=True)
    assert errs == [], errs


def test_total_pass_requires_human_and_wcg(tmp_path: Path):
    (tmp_path / "00-author-path.md").write_text(
        "# 00-author-path\n- 作者是否真人坐浏览器：否\n", encoding="utf-8"
    )
    ev = tmp_path / "note.md"
    ev.write_text("ok", encoding="utf-8")
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "PASS",
            "evidence_path": ["note.md"],
            "evidence_type": "API",
        }],
        author_human=False,
    )
    (tmp_path / "08-wordcount-rollup.md").write_text("合计：20000\n", encoding="utf-8")
    (tmp_path / "00-world-complete-gate.json").write_text(
        json.dumps({"pass": True}), encoding="utf-8"
    )
    errs = check_package(tmp_path, expect_total_pass=True)
    assert any("author_human" in e for e in errs)


def test_wordcount_oor_fails_total(tmp_path: Path):
    (tmp_path / "00-author-path.md").write_text(
        "- 作者是否真人坐浏览器：是\n", encoding="utf-8"
    )
    ev = tmp_path / "e.md"
    ev.write_text("x", encoding="utf-8")
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "PASS",
            "evidence_path": ["e.md"],
            "evidence_type": "API",
        }],
        author_human=True,
    )
    (tmp_path / "08-wordcount-rollup.md").write_text("合计：100\n", encoding="utf-8")
    (tmp_path / "00-world-complete-gate.json").write_text(
        json.dumps({"pass": True}), encoding="utf-8"
    )
    errs = check_package(tmp_path, expect_total_pass=True)
    assert any("wordcount" in e for e in errs)


def test_cli_exit_codes(tmp_path: Path):
    _write_matrix(tmp_path, [])
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert r.returncode != 0
    assert "FAIL" in r.stdout


def test_na_only_for_must_if(tmp_path: Path):
    _write_matrix(
        tmp_path,
        [{
            "id": "J1",
            "priority": "Must",
            "status": "N/A",
            "evidence_path": ["x"],
            "evidence_type": "API",
        }],
    )
    errs = check_package(tmp_path)
    assert any("Must-if-triggered" in e for e in errs)

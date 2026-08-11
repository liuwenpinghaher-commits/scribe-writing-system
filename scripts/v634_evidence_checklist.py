#!/usr/bin/env python3
"""v6.3.4 evidence content checklist (PR-Script-0).

Validates package *content* (not re-implementing WCG logic):
- matrix schema / non-empty status
- Must rules (PASS|N/A only for total PASS; N/A only Must-if-triggered)
- evidence_path non-empty when status=PASS
- author_human vs 00-author-path 真人
- wordcount band [18000, 24000]
- WCG json pass===true for total PASS claims
- empty/fake matrices → non-zero exit

Does **not** write books or invent screenshots.

Usage:
  python3 scripts/v634_evidence_checklist.py --dir docs/evidence/v634-true-chat-...
  python3 scripts/v634_evidence_checklist.py --dir ... --expect-partial
  python3 scripts/v634_evidence_checklist.py --dir ... --expect-total-pass
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_STATUS = frozenset({"PASS", "FAIL", "SKIP", "N/A"})
MUST_PRIOS = frozenset({"Must", "Must-if-triggered"})
WC_MIN, WC_MAX = 18000, 24000


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_wordcount(text: str) -> int | None:
    """Extract total visible chars from rollup markdown if present."""
    # patterns: 合计: 20000 / total: 20000 / **20000** / 可见字 20000
    for pat in (
        r"合计[^\d]*(\d{4,6})",
        r"total[^\d]*(\d{4,6})",
        r"可见字[^\d]*(\d{4,6})",
        r"wordcount[^\d]*(\d{4,6})",
        r"\*\*(\d{4,6})\*\*",
    ):
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    # bare number on a line with 字
    for line in text.splitlines():
        if "字" in line or "char" in line.lower() or "total" in line.lower():
            nums = re.findall(r"\b(\d{4,6})\b", line)
            if nums:
                return int(nums[-1])
    return None


def _author_path_says_human(text: str) -> bool | None:
    """Parse 真人坐浏览器：是/否. None if unparsable."""
    m = re.search(r"真人坐浏览器[：:]\s*(是|否)", text)
    if not m:
        # template forms
        m = re.search(r"是否真人[^\n]*[：:]\s*(是|否)", text)
    if not m:
        return None
    return m.group(1) == "是"


def check_package(
    root: Path,
    *,
    expect_total_pass: bool = False,
    expect_partial: bool = False,
) -> list[str]:
    """Return list of error strings (empty = ok for mode)."""
    errors: list[str] = []
    root = Path(root)
    if not root.is_dir():
        return [f"not a directory: {root}"]

    matrix_path = root / "02-feature-matrix.json"
    if not matrix_path.is_file():
        errors.append("missing 02-feature-matrix.json")
        return errors

    try:
        matrix = _load_json(matrix_path)
    except Exception as e:
        return [f"matrix JSON invalid: {e}"]

    if not isinstance(matrix, dict):
        return ["matrix root must be object"]

    version = matrix.get("version")
    if version != "v6.3.4":
        errors.append(f"matrix.version must be 'v6.3.4', got {version!r}")

    items = matrix.get("items")
    if not isinstance(items, list) or not items:
        errors.append("matrix.items empty or missing (fake/empty matrix)")
        return errors

    author_human = bool(matrix.get("author_human"))
    must_failed: list[str] = []
    should_pass = should_fail = 0
    empty_status = 0

    for it in items:
        if not isinstance(it, dict):
            errors.append(f"item not object: {it!r}")
            continue
        iid = str(it.get("id") or "?")
        status = (it.get("status") or "").strip()
        pri = (it.get("priority") or "").strip()
        epaths = it.get("evidence_path") or []

        if not status:
            empty_status += 1
            errors.append(f"{iid}: empty status")
            continue
        if status not in VALID_STATUS:
            errors.append(f"{iid}: invalid status {status!r}")
            continue

        if status == "PASS":
            if not epaths or not any(str(p).strip() for p in epaths):
                errors.append(f"{iid}: PASS requires non-empty evidence_path")
            else:
                # at least one path exists relative to root (optional hard for API-only)
                missing = [p for p in epaths if not (root / str(p)).exists()]
                # soft: only warn as error if all missing (fake PASS)
                if len(missing) == len(list(epaths)):
                    errors.append(f"{iid}: PASS but all evidence_path missing on disk: {epaths}")

        if pri in MUST_PRIOS:
            if status == "FAIL":
                must_failed.append(iid)
            if status == "N/A" and pri != "Must-if-triggered":
                errors.append(f"{iid}: N/A only allowed for Must-if-triggered, got {pri}")
            if expect_total_pass and status not in ("PASS", "N/A"):
                errors.append(f"{iid}: total PASS requires Must status PASS|N/A, got {status}")

        if pri == "Should":
            if status == "PASS":
                should_pass += 1
            elif status == "FAIL":
                should_fail += 1
            # SKIP not in denominator

    if empty_status:
        errors.append(f"{empty_status} items with empty status (fake/unfilled matrix)")

    # should_rate consistency if present
    denom = should_pass + should_fail
    computed = (should_pass / denom) if denom else 0.0
    claimed = matrix.get("should_rate")
    if claimed is not None and denom:
        try:
            if abs(float(claimed) - computed) > 0.02:
                errors.append(
                    f"should_rate {claimed} != computed {computed:.3f} "
                    f"(PASS={should_pass} FAIL={should_fail})"
                )
        except (TypeError, ValueError):
            errors.append(f"should_rate not a number: {claimed!r}")

    # author_human vs author-path
    ap = root / "00-author-path.md"
    if ap.is_file():
        human_doc = _author_path_says_human(ap.read_text(encoding="utf-8"))
        if human_doc is True and not author_human:
            errors.append("00-author-path says 真人=是 but matrix.author_human is false")
        if human_doc is False and author_human:
            errors.append("00-author-path says 真人=否 but matrix.author_human is true")
        if author_human and human_doc is not True:
            # require explicit 是 when claiming human
            if human_doc is None:
                errors.append("author_human=true but 00-author-path lacks 真人坐浏览器：是")
    else:
        if expect_total_pass or author_human:
            errors.append("missing 00-author-path.md")

    if expect_total_pass and not author_human:
        errors.append("total PASS claim requires author_human=true")

    # wordcount
    wc_path = root / "08-wordcount-rollup.md"
    wc_val: int | None = None
    if wc_path.is_file():
        wc_val = _parse_wordcount(wc_path.read_text(encoding="utf-8"))
        if wc_val is not None and not (WC_MIN <= wc_val <= WC_MAX):
            errors.append(f"wordcount {wc_val} out of band [{WC_MIN},{WC_MAX}]")
        if expect_total_pass and wc_val is None:
            errors.append("total PASS requires parseable wordcount in 08-wordcount-rollup.md")
    elif expect_total_pass:
        errors.append("missing 08-wordcount-rollup.md")

    # WCG
    wcg_path = root / "00-world-complete-gate.json"
    wcg_pass = None
    if wcg_path.is_file():
        try:
            wcg = _load_json(wcg_path)
            wcg_pass = bool(wcg.get("pass") is True or wcg.get("pass") == True)
            if wcg.get("pass") is not True:
                wcg_pass = False
        except Exception as e:
            errors.append(f"WCG json invalid: {e}")
            wcg_pass = False
    if expect_total_pass:
        if not wcg_path.is_file():
            errors.append("missing 00-world-complete-gate.json")
        elif wcg_pass is not True:
            errors.append("total PASS requires WCG pass===true")

    if expect_total_pass and must_failed:
        errors.append(f"Must failed: {must_failed}")

    if expect_total_pass and denom and computed < 0.80:
        errors.append(f"ShouldRate {computed:.3f} < 0.80")

    # partial mode: disallow claiming green total via closure
    closure = root / "09-final-closure.md"
    if closure.is_file():
        ct = closure.read_text(encoding="utf-8")
        claims_total = bool(
            re.search(r"总\s*PASS\s*[：:=]\s*true|verdict\s*[：:=]\s*PASS\b|体验总\s*PASS", ct, re.I)
        )
        if claims_total and not author_human:
            errors.append("09-final-closure claims total PASS but author_human=false")
        if claims_total and expect_partial:
            errors.append("expect-partial but closure claims total PASS")
        if claims_total:
            # force total-pass style checks
            if not author_human:
                errors.append("closure total PASS without author_human")
            if wcg_pass is not True:
                errors.append("closure total PASS without WCG pass=true")

    # matrix must_failed field sync
    mf = matrix.get("must_failed")
    if isinstance(mf, list) and set(mf) != set(must_failed) and must_failed:
        # soft: only error if matrix claims empty but we found fails
        if not mf and must_failed and expect_total_pass:
            errors.append(f"must_failed field empty but Must FAIL: {must_failed}")

    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="v6.3.4 evidence content checklist")
    ap.add_argument("--dir", required=True, help="evidence package directory")
    ap.add_argument(
        "--expect-total-pass",
        action="store_true",
        help="require full total-PASS conditions",
    )
    ap.add_argument(
        "--expect-partial",
        action="store_true",
        help="allow incomplete journey; still reject empty status and fake PASS",
    )
    args = ap.parse_args(argv)

    if args.expect_total_pass and args.expect_partial:
        print("error: choose one of --expect-total-pass / --expect-partial", file=sys.stderr)
        return 2

    errs = check_package(
        Path(args.dir),
        expect_total_pass=args.expect_total_pass,
        expect_partial=args.expect_partial,
    )
    if errs:
        print("FAIL v634_evidence_checklist")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("OK v634_evidence_checklist")
    mode = "total-pass" if args.expect_total_pass else ("partial" if args.expect_partial else "schema")
    print(f"mode={mode} dir={args.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

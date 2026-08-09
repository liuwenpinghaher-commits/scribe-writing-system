#!/usr/bin/env python3
"""Offline close mutually exclusive open facts on a work (demo API).

用法：
  API_BASE=https://www.qing.blue python3 scripts/offline_close_dual_truth.py --work book_aa57f17e

仅扫描并报告；加 --apply 才写 supersede（通过 s3 或 save fact API 若可用）。
默认 dry-run：打印互斥对，不写库。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("API_BASE", "https://www.qing.blue")

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "v63_memory_journey", ROOT / "scripts" / "v63_memory_journey.py",
)
v63 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(v63)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--chapter", type=int, default=99999)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    v63.login()
    work = args.work
    # prefetch surface text for dual phrase scan
    code, pref = v63.curl(
        "POST", "/api/memory/prefetch",
        {"query": "状态 完整 缺口", "chapter": min(args.chapter, 20), "focalizer": ""},
        work=work, timeout=90,
    )
    text = json.dumps(pref, ensure_ascii=False) if isinstance(pref, dict) else str(pref)
    dual = "完整无缺" in text and "缺口" in text
    print(f"work={work} prefetch_http={code} dual_phrase={dual}")
    from scribe3.fact_surface import EXCLUSION_PAIRS, values_mutually_exclusive
    print("exclusion_pairs", len(EXCLUSION_PAIRS))
    print("sample", values_mutually_exclusive("完整无缺", "齿边有缺口"))
    if dual:
        print("WARN dual phrases still present on inject surface")
    else:
        print("OK no dual phrase co-presence on prefetch JSON")
    if args.apply:
        print("NOTE: apply path relies on server projection; no bulk write in dry tooling")
    print("DONE")


if __name__ == "__main__":
    main()

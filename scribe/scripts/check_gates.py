#!/usr/bin/env python3
"""C6-4 硬门检查(CI 用)—— 跑全部确定性单测,任一失败则退出码 1。

设计:这是"能跑且会拦"的门禁(工程11 H-03)。变差的代码/prompt 让单测失败 → CI 红。
LLM 主观质量门(eval/run_eval.py)需网络,单独运行;此处只保证确定性回归不破。
用法:python scripts/check_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = sorted((ROOT / "tests").glob("test_*.py"))


def main() -> int:
    py = sys.executable
    failed = []
    for t in TESTS:
        r = subprocess.run([py, str(t)], capture_output=True, text=True, cwd=str(ROOT))
        ok = r.returncode == 0
        print(f"{'PASS' if ok else 'FAIL'}  {t.name}")
        if not ok:
            failed.append(t.name)
            print(r.stdout[-500:], r.stderr[-500:])
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} 通过")
    if failed:
        print("硬门未过:", ", ".join(failed))
        return 1
    print("✅ 硬门通过(确定性回归全绿)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

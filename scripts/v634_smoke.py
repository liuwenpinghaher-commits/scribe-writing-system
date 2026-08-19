#!/usr/bin/env python3
"""部署/验收冒烟入口。默认 imports，不烧模型。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scribe3.tools.v634_smoke import main

if __name__ == "__main__":
    raise SystemExit(main())

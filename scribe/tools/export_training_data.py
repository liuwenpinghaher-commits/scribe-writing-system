#!/usr/bin/env python
"""导出作者的 LoRA 训练集(SFT JSONL)。无需 GPU,现在即可运行。

用法: python tools/export_training_data.py <owner_id> [out.jsonl]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database
from scribe_mcp.personalize import export_jsonl

if __name__ == "__main__":
    owner = sys.argv[1] if len(sys.argv) > 1 else "u1"
    out = sys.argv[2] if len(sys.argv) > 2 else f"data/{owner}-sft.jsonl"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    db = Database(str(Path(__file__).resolve().parent.parent / "scribe.db"))
    n = export_jsonl(db, owner, out)
    print(f"导出 {n} 条训练样本 → {out}")
    if n < 50:
        print("提示:样本偏少。作者认可(定稿/锁定)的章节越多,个性化效果越好。")

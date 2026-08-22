"""宇宙 §6 与闸同源：只读 md，不 import world_surface（PR-1 可独立绿）。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WANJIE = ROOT / "docs" / "worlds" / "wanjie-probability-war-v7.md"


def test_section6_off_wrist_cough_onto_observe():
    text = WANJIE.read_text(encoding="utf-8")
    # 只取 §6 到下一节
    start = text.find("## 6.")
    end = text.find("## 7.", start)
    sec = text[start:end] if start >= 0 else text
    assert "按腕" not in sec
    assert "母亲咳" not in sec
    assert "母亲的口气咳" not in sec
    assert any(w in sec for w in ("观测", "坍缩", "冗余", "指针态"))


if __name__ == "__main__":
    test_section6_off_wrist_cough_onto_observe()
    print("OK test_section6_off_wrist_cough_onto_observe")
    print("PASS test_world_claim_homology")

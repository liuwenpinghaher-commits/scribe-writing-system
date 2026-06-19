"""C2-2 LLM 深度一致性 自检:解析+类别过滤+落库(用桩 complete_fn)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.consistency import parse_deep_flags, run_deep_check, ERROR_CLASSES, build_deep_check_prompt  # noqa: E402


def test_parse_filters_classes():
    reply = '[{"error_class":"时序矛盾","severity":"major","detail":"第3章说是白天,本章却说同一时刻是深夜"},{"error_class":"瞎编的类","severity":"x","detail":"忽略"}]'
    flags = parse_deep_flags(reply)
    assert len(flags) == 1 and flags[0]["error_class"] == "时序矛盾"
    assert flags[0]["severity"] == "major"
    assert parse_deep_flags("没有矛盾 []") == []
    assert parse_deep_flags("模型乱说") == []


def test_run_deep_check_writes():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    cid = d.save_chapter(w, 4, "四")
    d.save_snapshot(w, cid, "沈砚突然复活了,尽管他第二章已确认死亡。", created_by="ai")
    fake = lambda p: '[{"error_class":"硬伤(死而复生等)","severity":"critical","detail":"沈砚第2章已死却复活"}]'  # noqa: E731
    ids = run_deep_check(d, fake, w, 4)
    assert len(ids) == 1
    flags = d.list_consistency_flags(w)
    assert any(f["error_class"] == "硬伤(死而复生等)" for f in flags)


def test_prompt_lists_classes():
    p = build_deep_check_prompt("正文", "前情", 5)
    assert "时序矛盾" in p and "人物OOC" in p and len(ERROR_CLASSES) == 19


def _run():
    for fn in [test_parse_filters_classes, test_run_deep_check_writes, test_prompt_lists_classes]:
        fn(); print(f"  ✓ {fn.__name__}")
    print("\n通过。")


if __name__ == "__main__":
    _run()

"""sqlite-vec KNN 机制自检(确定性合成向量,真实验证向量检索地基)。

不依赖任何嵌入模型:用已知几何的合成向量,断言最近邻顺序与跨书隔离正确。
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.vec import VecStore  # noqa: E402


def test_knn_order_and_isolation():
    conn = sqlite3.connect(":memory:")
    store = VecStore(conn, dim=3)
    # 单位轴向量:x/y/z
    store.add("seg-x", "bookA", [1.0, 0.0, 0.0], content="x 段")
    store.add("seg-y", "bookA", [0.0, 1.0, 0.0], content="y 段")
    store.add("seg-z", "bookA", [0.0, 0.0, 1.0], content="z 段")
    # 另一本书的向量(几乎等于 x),用来验证防串味
    store.add("seg-other", "bookB", [0.99, 0.01, 0.0], content="别的书")

    # 查询接近 x:最近应是 bookA 的 seg-x,且绝不返回 bookB 的 seg-other
    hits = store.knn("bookA", [0.9, 0.1, 0.0], k=3)
    ids = [h[0] for h in hits]
    assert ids[0] == "seg-x", f"最近邻应为 seg-x,实际 {ids}"
    assert "seg-other" not in ids, "串味!返回了另一本书的向量"
    # 距离单调:seg-x < seg-y 与 seg-z
    dist = {h[0]: h[1] for h in hits}
    assert dist["seg-x"] < dist["seg-y"]
    assert dist["seg-x"] < dist["seg-z"]

    # bookB 单独查,只能看到自己的
    hb = store.knn("bookB", [1.0, 0.0, 0.0], k=5)
    assert [h[0] for h in hb] == ["seg-other"]


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

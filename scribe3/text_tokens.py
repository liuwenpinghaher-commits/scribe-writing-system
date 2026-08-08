"""中文全文检索用分词（索引与查询须同一函数）。

背景：jieba 对「铜炉」单独切为整词，嵌在句中常切成「铜」「炉」，导致
BM25 查询「铜炉」打不中已索引句。此处在 jieba 结果上补充：
  · 词内单字与 bigram
  · 相邻单字 CJK 跨词 bigram（铜+炉 → 铜炉）
"""
from __future__ import annotations


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _all_cjk(s: str) -> bool:
    return bool(s) and all(_is_cjk(c) for c in s)


def tokenize_for_fts(text: str | None) -> str:
    """返回空格分隔 token 串，供 Surreal FULLTEXT blank analyzer 使用。"""
    import jieba

    raw = [
        w.strip()
        for w in jieba.cut(text or "")
        if w and w.strip()
    ]
    out: list[str] = []
    seen: set[str] = set()

    def add(tok: str) -> None:
        if not tok or tok in seen:
            return
        seen.add(tok)
        out.append(tok)

    for w in raw:
        add(w)
        if len(w) >= 2 and _all_cjk(w):
            for ch in w:
                add(ch)
            for i in range(len(w) - 1):
                add(w[i : i + 2])

    # 相邻单字跨词 bigram（解决「铜」「炉」 vs 查询「铜炉」）
    run: list[str] = []
    def flush_run() -> None:
        nonlocal run
        if len(run) >= 2:
            for i in range(len(run) - 1):
                add(run[i] + run[i + 1])
        run = []

    for w in raw:
        if len(w) == 1 and _is_cjk(w):
            run.append(w)
        else:
            flush_run()
    flush_run()

    return " ".join(out)

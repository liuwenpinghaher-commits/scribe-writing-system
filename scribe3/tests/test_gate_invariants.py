"""门控不变量:commit_if_approved 的 name 必须 ⊆ WRITE_GATED;关键写工具须入闸。

AST 解析 mcp.py 源码收集所有 commit_if_approved("s3_...", ...) 的第一个字符串参数,
与运行时 WRITE_GATED 交叉校验,防止「走了 commit 但未入闸」(假绿 fail-open)。
"""
from __future__ import annotations

import ast
from pathlib import Path

import scribe3.mcp as M


def _commit_names_from_mcp_source() -> set[str]:
    """从 mcp.py AST 收集 commit_if_approved 调用的第一个字符串实参。"""
    src = Path(M.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "commit_if_approved":
            pass
        elif isinstance(func, ast.Attribute) and func.attr == "commit_if_approved":
            pass
        else:
            continue
        if not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            names.add(arg0.value)
    return names


def test_commit_if_approved_names_subset_of_write_gated():
    names = _commit_names_from_mcp_source()
    assert names, "应至少收集到一个 commit_if_approved 调用"
    extra = names - M.WRITE_GATED
    assert not extra, (
        f"commit_if_approved name 不在 WRITE_GATED(假绿 fail-open): {sorted(extra)}"
    )


def test_s3_author_pref_add_is_write_gated():
    assert "s3_author_pref_add" in M.WRITE_GATED
    assert M.requires_approval("s3_author_pref_add") is True

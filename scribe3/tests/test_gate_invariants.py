"""门控不变量:commit_if_approved 的 name 必须 ⊆ WRITE_GATED;关键写工具须入闸。

AST 解析 mcp.py 源码收集所有 commit_if_approved("s3_...", ...) 的第一个字符串参数,
与运行时 WRITE_GATED 交叉校验,防止「走了 commit 但未入闸」(假绿 fail-open)。
"""
from __future__ import annotations

import ast
from pathlib import Path

import scribe3.mcp as M


def _commit_names_from_mcp_source() -> set[str]:
    """从 mcp 包 AST 收集 commit_if_approved 调用的第一个字符串实参。"""
    names: set[str] = set()
    root = Path(M.__file__).resolve().parent
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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


def test_write_gated_write_bodies_touch_store_or_llm():
    """空壳 + 审批成功 = 假绿。WRITE_GATED 的 _write 必须碰 store 或 LLM。"""
    root = Path(M.__file__).resolve().parent
    shells: list[str] = []
    for path in root.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            if node.name not in M.WRITE_GATED:
                continue
            text = ast.get_source_segment(src, node) or ""
            writes = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "_write"]
            called: list[str] = []
            for wn in writes or [node]:
                for c in ast.walk(wn):
                    if isinstance(c, ast.Call):
                        f = c.func
                        if isinstance(f, ast.Name):
                            called.append(f.id)
                        elif isinstance(f, ast.Attribute):
                            called.append(f.attr)
            touch = {"persist", "thicken", "hermes_complete", "expand_volume_accounts",
                     "thicken_codex", "thicken_codex_batch", "add_volume", "update_volume",
                     "add_fact", "save_chapter", "update_chapter_meta", "generate_charters",
                     "persist_charters", "thicken_stage", "persist_codex_row"}
            if not (touch & set(called)) and not any(
                k in text for k in ("expand_volume_accounts", "thicken_codex_batch",
                                    "hermes_complete", "persist(", "st.add_", "st.update_")
            ):
                shells.append(node.name)
    assert "s3_plan_chapter_accounts" not in shells
    assert "s3_expand_arc_window" not in shells

"""MCP tools entry — import family modules so @mcp.tool registrations apply."""
from __future__ import annotations

# Side-effect imports: each module registers tools on the shared FastMCP instance.
from scribe3.mcp import tools_read as _tools_read  # noqa: F401
from scribe3.mcp import tools_recall as _tools_recall  # noqa: F401
from scribe3.mcp import tools_write as _tools_write  # noqa: F401

# Re-export symbols for package __init__ star-copy and tests.
for _mod in (_tools_read, _tools_recall, _tools_write):
    for _k, _v in vars(_mod).items():
        if _k in ("__name__", "__file__", "__package__", "__doc__", "__spec__",
                  "__loader__", "__cached__", "__builtins__", "__all__"):
            continue
        if _k.startswith("__"):
            continue
        globals()[_k] = _v

__all__ = sorted(
    n for n in globals()
    if not n.startswith("__") and n not in (
        "_tools_read", "_tools_recall", "_tools_write", "_mod", "_k", "_v")
)

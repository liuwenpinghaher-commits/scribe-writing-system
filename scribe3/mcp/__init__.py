"""scribe3 MCP package (split from mcp.py). Stable re-exports."""
from __future__ import annotations

from scribe3.mcp import _common as _common
from scribe3.mcp import gating as _gating
from scribe3.mcp import tools as _tools
from scribe3.mcp import server as _server

for _mod in (_common, _gating, _tools, _server):
    for _k, _v in vars(_mod).items():
        if _k in ("__name__", "__file__", "__package__", "__doc__", "__spec__",
                  "__loader__", "__cached__", "__builtins__", "__all__"):
            continue
        if _k.startswith("__"):
            continue
        globals()[_k] = _v

__all__ = sorted(
    n for n in globals()
    if not n.startswith("__") and n not in ("_common", "_gating", "_tools", "_server", "_mod", "_k", "_v")
)

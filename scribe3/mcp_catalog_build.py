"""Build MCP capability catalog without FastMCP runtime.

Used by GET /mcp/catalog and unit tests. Scans tools*.py for def/async def s3_*.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MANUSCRIPT_SAVE = frozenset({"s3_save_chapter"})
INGEST = frozenset({"s3_ingest_chapter"})
UNGATED_WRITE_ALLOWLIST = frozenset()

NAME_RE = re.compile(
    r"^(?:async\s+)?def\s+(s3_[a-z0-9_]+)\s*\(",
    re.M,
)
DOC_RE = re.compile(
    r'\)\s*(?:->\s*[^:]+)?\s*:\s*(?:\n\s*)?"""(.*?)"""',
    re.S,
)


def parse_write_gated(common_py: Path | None = None) -> set[str]:
    if common_py is None:
        common_py = Path(__file__).resolve().parent / "mcp" / "_common.py"
    text = common_py.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"WRITE_GATED\s*=\s*\{([^}]+)\}", text, re.S)
    if not m:
        return set()
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def gate_for(name: str, write_gated: set[str]) -> str:
    if name in write_gated:
        return "world_write_gated"
    if name in MANUSCRIPT_SAVE:
        return "manuscript_save"
    if name in INGEST:
        return "ingest"
    if name in UNGATED_WRITE_ALLOWLIST:
        return "ungated_write"
    return "read"


def extract_tools_from_source(text: str, module: str, write_gated: set[str]) -> list[dict[str, Any]]:
    tools = []
    for m in NAME_RE.finditer(text):
        name = m.group(1)
        rest = text[m.start():]
        paren_i = rest.find("(")
        depth = 0
        end_sig = None
        for i, ch in enumerate(rest[paren_i:], start=paren_i):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end_sig = i
                    break
        doc = ""
        if end_sig is not None:
            after = rest[end_sig:]
            dm = DOC_RE.match(after)
            if dm:
                doc = dm.group(1).strip().split("\n")[0].strip()[:160]
        g = gate_for(name, write_gated)
        tools.append({
            "name": name,
            "write_gated": g == "world_write_gated",
            "gate": g,
            "group": (
                "write" if g == "world_write_gated"
                else "manuscript" if g == "manuscript_save"
                else "ingest" if g == "ingest"
                else "read"
            ),
            "doc": doc,
            "module": module,
        })
    return tools


def build_mcp_catalog(
    mcp_dir: Path | None = None,
    write_gated: set[str] | None = None,
) -> dict[str, Any]:
    if mcp_dir is None:
        mcp_dir = Path(__file__).resolve().parent / "mcp"
    if write_gated is None:
        write_gated = parse_write_gated(mcp_dir / "_common.py")

    seen: set[str] = set()
    tools: list[dict[str, Any]] = []
    for py in sorted(mcp_dir.glob("tools*.py")):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for t in extract_tools_from_source(text, py.name, write_gated):
            if t["name"] in seen:
                continue
            seen.add(t["name"])
            tools.append(t)

    for name in sorted(write_gated):
        if name not in seen:
            tools.append({
                "name": name,
                "write_gated": True,
                "gate": "world_write_gated",
                "group": "write",
                "doc": "",
                "module": "WRITE_GATED",
            })
            seen.add(name)

    counts: dict[str, int] = {}
    for t in tools:
        counts[t["gate"]] = counts.get(t["gate"], 0) + 1

    domains = _build_domains(write_gated)
    return {
        "tools": tools,
        "count": len(tools),
        "counts_by_gate": counts,
        "write_gated_total": len(write_gated),
        "domains": domains,
    }


def _build_domains(write_gated: set[str]) -> list[dict[str, Any]]:
    covered_write: set[str] = set()
    domains: list[dict[str, Any]] = []
    try:
        from scribe3.orchestration.catalog import CATALOG
        for d in CATALOG:
            rt = list(d.get("read_tools") or ())
            wt = list(d.get("write_tools") or ())
            covered_write.update(wt)
            domains.append({
                "domain": d.get("domain"),
                "label": d.get("label") or d.get("domain"),
                "read_tools": rt,
                "write_tools": wt,
                "read_count": len(rt),
                "write_gated_count": len(wt),
                "channel": d.get("channel"),
            })
    except Exception:
        pass

    missing = sorted(write_gated - covered_write)
    if missing:
        domains.append({
            "domain": "ungrouped.world_write",
            "label": "未分组·世界写（须审批）",
            "read_tools": [],
            "write_tools": missing,
            "read_count": 0,
            "write_gated_count": len(missing),
            "channel": "world_write",
        })
    domains.append({
        "domain": "prose.manuscript",
        "label": "存稿（手稿通道）",
        "read_tools": [],
        "write_tools": list(MANUSCRIPT_SAVE),
        "read_count": 0,
        "write_gated_count": 0,
        "channel": "manuscript",
        "gate_note": "manuscript_save",
    })
    domains.append({
        "domain": "prose.ingest",
        "label": "入库分析",
        "read_tools": [],
        "write_tools": list(INGEST),
        "read_count": 0,
        "write_gated_count": 0,
        "channel": "ingest",
        "gate_note": "ingest",
    })
    return domains

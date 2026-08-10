"""Shipped path: catalog_build scans async write tools + gate_for."""
from __future__ import annotations

from scribe3.mcp_catalog_build import (
    build_mcp_catalog,
    gate_for,
    parse_write_gated,
    NAME_RE,
    extract_tools_from_source,
)


def test_name_re_matches_async_def():
    sample = "async def s3_add_fact(entity: str) -> dict:\n    \"\"\"add fact.\"\"\"\n    pass\n"
    assert NAME_RE.search(sample).group(1) == "s3_add_fact"


def test_parse_write_gated_from_common():
    wg = parse_write_gated()
    assert "s3_add_character" in wg
    assert "s3_add_fact" in wg
    assert len(wg) >= 40


def test_gate_for_five_way():
    wg = {"s3_add_fact"}
    assert gate_for("s3_add_fact", wg) == "world_write_gated"
    assert gate_for("s3_save_chapter", wg) == "manuscript_save"
    assert gate_for("s3_ingest_chapter", wg) == "ingest"
    assert gate_for("s3_get_chapter", wg) == "read"


def test_build_catalog_write_gated_subset():
    cat = build_mcp_catalog()
    wg = parse_write_gated()
    names = {t["name"] for t in cat["tools"]}
    missing = wg - names
    assert not missing, f"WRITE_GATED missing from catalog: {sorted(missing)[:10]}"
    assert cat["counts_by_gate"].get("world_write_gated") == len(wg)
    assert cat["write_gated_total"] == len(wg)
    by = {t["name"]: t for t in cat["tools"]}
    if "s3_save_chapter" in by:
        assert by["s3_save_chapter"]["gate"] == "manuscript_save"
    if "s3_ingest_chapter" in by:
        assert by["s3_ingest_chapter"]["gate"] == "ingest"
    world = [t for t in cat["tools"] if t["gate"] == "world_write_gated" and t.get("doc")]
    assert len(world) >= 1, "expected at least one world_write with docstring"
    assert cat.get("domains")


def test_extract_async_with_multiline_sig_doc():
    src = (
        "async def s3_add_character(\n"
        "    name: str,\n"
        "    work: str | None = None,\n"
        ") -> dict:\n"
        '    """新建角色并待批落库。\n'
        "\n"
        "    longer body ignored.\n"
        '    """\n'
        "    pass\n"
    )
    tools = extract_tools_from_source(src, "tools_write.py", {"s3_add_character"})
    assert len(tools) == 1
    assert tools[0]["name"] == "s3_add_character"
    assert tools[0]["write_gated"] is True
    assert "新建角色" in tools[0]["doc"]

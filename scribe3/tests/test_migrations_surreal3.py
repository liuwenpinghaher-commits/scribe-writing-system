"""SurrealDB 3.x 迁移/代码护栏：禁止 2.x 专用旧写法回流。"""
from __future__ import annotations

from pathlib import Path

SCRIBE3 = Path(__file__).resolve().parents[1]
MIGRATIONS = SCRIBE3 / "migrations"

# 允许出现在「注释/字符串否定句」中的标记；扫描时仍禁止作为可执行写法。
_SKIP_DIR_NAMES = {
    "node_modules",
    ".venv",
    "web",
    "__pycache__",
    ".git",
}


def _iter_source_files():
    for p in list(SCRIBE3.rglob("*.py")) + list(SCRIBE3.rglob("*.surql")):
        if any(part in _SKIP_DIR_NAMES for part in p.parts):
            continue
        # 本护栏文件会提到旧写法名称
        if p.name == "test_migrations_surreal3.py":
            continue
        yield p


def test_017_no_async_retry_syntax():
    text = (MIGRATIONS / "017_async_events.surql").read_text(encoding="utf-8")
    assert "ASYNC RETRY" not in text
    assert "DEFINE EVENT" in text


def test_070_078_use_fulltext_analyzer():
    for name in ("070_material_memory.surql", "078_memory_fabric.surql"):
        text = (MIGRATIONS / name).read_text(encoding="utf-8")
        assert "SEARCH ANALYZER" not in text, name
        assert "FULLTEXT ANALYZER" in text, name


def test_075_no_count_index_legacy():
    text = (MIGRATIONS / "075_chapter_record_range_count.surql").read_text(encoding="utf-8")
    assert "ON chapter COUNT" not in text


def test_no_type_thing_in_scribe3_sources():
    """3.x 使用 type::record；禁止回流 type::thing（含 2.x 兼容回退）。"""
    bad = []
    for p in _iter_source_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "type::thing" in text:
            bad.append(str(p.relative_to(SCRIBE3)))
    assert not bad, f"still has type::thing: {bad[:20]}"


def test_migration_mark_uses_type_record_only():
    """_migration 标记禁止 2.x CREATE 回退 / type::thing。"""
    text = (SCRIBE3 / "store" / "connection.py").read_text(encoding="utf-8")
    assert "UPSERT type::record('_migration'" in text or 'UPSERT type::record("_migration"' in text
    # 可执行路径不得含 2.3 回退 CREATE
    assert "CREATE _migration:`" not in text
    assert "type::thing" not in text


def test_no_search_analyzer_in_scribe3_sources():
    """3.x 全文索引用 FULLTEXT ANALYZER。"""
    bad = []
    for p in _iter_source_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "SEARCH ANALYZER" in text:
            bad.append(str(p.relative_to(SCRIBE3)))
    assert not bad, f"still has SEARCH ANALYZER: {bad[:20]}"


def test_no_legacy_type_is_double_colon_in_surql():
    """3.x 函数为 type::is_string 等；禁止 type::is::string 旧式。"""
    bad = []
    for p in MIGRATIONS.glob("*.surql"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        # 可执行写法：type::is::
        if "type::is::" in text:
            # 允许纯注释句说明「已移除」时仍含字面量——若在非注释行则失败
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if "type::is::" not in stripped:
                    continue
                if stripped.startswith("--") or stripped.startswith("//"):
                    continue
                bad.append(f"{p.name}:{i}")
    assert not bad, f"legacy type::is:: in executable surql: {bad[:20]}"


def test_166_relates_is_material_relation():
    """素材联想边 relates 必须 SCHEMAFULL 锁成 material→material，禁止隐式表。"""
    text = (MIGRATIONS / "166_material_relates.surql").read_text(encoding="utf-8")
    assert "DEFINE TABLE OVERWRITE relates TYPE RELATION" in text
    assert "FROM material TO material" in text
    assert "SCHEMAFULL" in text
    assert "type::thing" not in text


def test_prod_compose_pins_surreal_3_2():
    """生产 compose 必须钉死 3.2.x，禁止 latest / 2.1。"""
    root = SCRIBE3.parents[0]
    compose = root / "deploy" / "prod" / "docker-compose.yml"
    assert compose.is_file(), compose
    text = compose.read_text(encoding="utf-8")
    assert "surrealdb/surrealdb:v3.2" in text
    assert "surrealdb/surrealdb:latest" not in text
    assert "surrealdb/surrealdb:v2." not in text
    assert "--query-timeout" in text
    assert "--transaction-timeout" in text

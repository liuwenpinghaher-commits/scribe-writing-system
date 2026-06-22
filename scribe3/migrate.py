"""scribe2(NS=scribe)→ scribe3(NS=scribe3)一次性数据迁移。

只迁世界观:character→character、setting→proposition(世界设定)。
诚实 parity:章节正文/伏笔/母题/事件 scribe3 尚无对应,不迁(见 README)。不动原库(只读 SELECT)。
跑:scribe3/.venv/bin/python -m scribe3.migrate <work_local_id>
"""
from __future__ import annotations

import sys

from surrealdb import Surreal

from scribe3.ontology import Entity, Fact


def _bs(r: dict) -> str:
    return " / ".join(x for x in [r.get("motivation"), r.get("voice"), r.get("text")] if x)


def project_characters(rows: list[dict]) -> list[Entity]:
    seen: set = set()
    out: list[Entity] = []
    for r in rows:
        name = r.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(Entity(f"role:{name}", "character", name, traits={"backstory": _bs(r)}))
    return out


def project_settings(rows: list[dict]) -> list[Fact]:
    seen: set = set()
    out: list[Fact] = []
    for r in rows:
        name = r.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        val = r.get("content") or r.get("text") or ""
        out.append(Fact(f"fact:{name}", "世界设定", name, val, valid_from=1))
    return out


def project_foreshadows(rows: list[dict]) -> list[dict]:
    seen: set = set()
    out: list[dict] = []
    for r in rows:
        text = r.get("promise") or r.get("summary") or r.get("text")
        if not text or text in seen:
            continue
        seen.add(text)
        ch = r.get("chapter")
        out.append({"text": text,
                    "setup_chapter": int(ch) if isinstance(ch, (int, float)) else 1,
                    "kind": r.get("ftype") or "promise"})
    return out


def migrate(work_local: str, dst_store, src: Surreal | None = None) -> dict:
    """读 scribe2 某 work 的 character/setting → 投影 → 写 scribe3 dst_store。"""
    close = False
    if src is None:
        src = Surreal("ws://127.0.0.1:8001/rpc")
        src.signin({"username": "root", "password": "root"})
        src.use("scribe", "main")
        close = True
    try:
        # scribe2 的 work 字段是字符串 'work:<local>'(非 record link)
        wstr = work_local if work_local.startswith("work:") else f"work:{work_local}"
        chars = src.query("SELECT name,motivation,voice,text FROM character WHERE work = $w", {"w": wstr})
        setts = src.query("SELECT name,stype,content,text FROM setting WHERE work = $w", {"w": wstr})
        fores = src.query("SELECT promise,summary,text,chapter,ftype FROM foreshadow WHERE work = $w", {"w": wstr})
        ents = project_characters(chars or [])
        facts = project_settings(setts or [])
        proms = project_foreshadows(fores or [])
        for e in ents:
            dst_store.add_entity(e)
        for f in facts:
            dst_store.add_fact(f)
            dst_store.grant_public(f.id, chapter=1)   # 设定=公开世界知识,人人皆知(渲染可用)
            if f.value:
                dst_store.semantic_index(f.id, f.value)
        for p in proms:
            dst_store.plant_promise(p["text"], p["setup_chapter"], kind=p["kind"])
        return {"characters": len(ents), "settings": len(facts), "promises": len(proms)}
    finally:
        if close:
            src.close()


def main() -> None:
    from scribe3.store import SurrealStore
    work = sys.argv[1] if len(sys.argv) > 1 else None
    if not work:
        print("用法:python -m scribe3.migrate <work_local_id>")
        return
    dst = SurrealStore(ns="scribe3", db="main")
    try:
        dst.apply_schema()
        print("迁移结果:", migrate(work, dst))
    finally:
        dst.close()


if __name__ == "__main__":
    main()

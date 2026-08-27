"""认知层 · 知识帧投影 + 看见即知道。

范式核心:**限知渲染 = 渲染前按 focalizer 投影出他的知识帧,只把帧喂生成。**
帧里没有的事,物理上进不了 prompt。判官只兜底,不是主防线。
"""
from __future__ import annotations

from dataclasses import dataclass

from scribe3.ontology import Event, Fact, KnowledgeEdge, World


@dataclass
class KnowledgeFrame:
    """某 knower 截至某章【知道】的事实集。renderer 只能看见这些。"""
    knower_id: str
    chapter: int
    facts: list[Fact]

    def knows(self, fact_id: str) -> bool:
        return any(f.id == fact_id for f in self.facts)


def project_frame(world: World, knower_id: str, chapter: int, edges=None) -> KnowledgeFrame:
    """投影 knower 在 chapter 的知识帧。
    knower='world' → 全知真相(一致性裁判);否则 = 有 KnowledgeEdge 的事实。
    edges: 可选预加载的知识边列表(避免 dramatic_irony 重复全扫,去 N+1)。

    S-5: SCRIBE3_DB_KNOWLEDGE_FRAME=1 且 store 支持时优先 ``fn::knowledge_frame``；
    失败回退 Python 边过滤。
    """
    if knower_id != "world":
        try:
            from scribe3.surreal_flags import db_knowledge_frame
            if db_knowledge_frame() and hasattr(world, "_query"):
                framed = _project_frame_db(world, knower_id, int(chapter))
                if framed is not None:
                    return framed
        except Exception:
            pass
    facts_now = world.facts_at(chapter)
    if knower_id == "world":
        return KnowledgeFrame("world", chapter, list(facts_now))
    if edges is None:
        edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    known_ids = {
        k.proposition_id for k in edges
        if k.knower_id == knower_id and k.polarity
        and k.since_chapter <= chapter
        and (k.until_chapter is None or k.until_chapter > chapter)
    }
    return KnowledgeFrame(knower_id, chapter,
                          [f for f in facts_now if f.id in known_ids])


def _normalize_frame_rows(rows) -> list | None:
    """把 fn::knowledge_frame 的返回归一成命题行列表。

    驱动对 `RETURN <array>` 的返回是**拍平的行列表**，不是 `[[row, row, ...]]`。
    这里原先直接 `rows[0]` 当整批用，于是**只剩第一条事实**——角色只有一条命题时
    看不出来（单测数据正是如此），一旦真书里某人知道十几件事，限知帧就残废了。
    两种形状都认，别再赌驱动的解包行为。
    """
    if not rows:
        return []
    if isinstance(rows, dict):
        return [rows] if "local" in rows else None
    if not isinstance(rows, list):
        return None
    if all(isinstance(r, dict) for r in rows):
        return rows
    head = rows[0]
    if isinstance(head, list):
        return [r for r in head if isinstance(r, dict)]
    if isinstance(head, dict):
        return [head]
    return None


def _project_frame_db(store, knower_id: str, chapter: int) -> KnowledgeFrame | None:
    """DB 侧投影；失败返回 None。"""
    from scribe3.ontology import Fact
    try:
        rows = store.knowledge_frame_fn(knower_id, int(chapter)) or []
    except Exception:
        return None
    raw = _normalize_frame_rows(rows)
    if raw is None:
        return None
    facts: list[Fact] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        local = r.get("local")
        if not local:
            continue
        facts.append(Fact(
            f"fact:{local}",
            r.get("entity_id") or "",
            r.get("attribute") or "",
            r.get("value"),
            int(r.get("valid_from") or 0),
            r.get("valid_to"),
            bool(r.get("secret", False)),
            r.get("leak_markers") or [],
        ))
    return KnowledgeFrame(knower_id, int(chapter), facts)


def _db_frame_ready(world) -> bool:
    """DB 侧限知帧可用时，两次 project_frame 都走 SQL，不必预载全表边。"""
    try:
        from scribe3.surreal_flags import db_knowledge_frame
        return bool(db_knowledge_frame()) and hasattr(world, "_query")
    except Exception:
        return False


def dramatic_irony(world, focalizer: str, chapter: int) -> list[Fact]:
    """戏剧反讽点 = KNOWS(reader,F) ∧ ¬KNOWS(focalizer,F)。
    返回读者已知、而视角角色尚不知的事实(可计算查询,非人脑事后判断)。

    走 DB 路径时不预载 `load_knowledge()`——那是一次全表边扫描，千万字规模实测 2.3 秒，
    而 project_frame 会优先用 SQL，预载的边根本用不上。内存 World 仍然预载一次，
    否则两次投影各扫一遍反而更慢。
    """
    edges = None
    if not _db_frame_ready(world):
        edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    reader = project_frame(world, "reader", chapter, edges=edges)
    foc_ids = {f.id for f in project_frame(world, focalizer, chapter, edges=edges).facts}
    return [f for f in reader.facts if f.id not in foc_ids]


def iter_participants(participants) -> list[tuple[str, str]]:
    """展开 participants 为 (role, oid) 列表。

    兼容三种形态:
    - dict[str, str]: 单槽单人(历史)
    - dict[str, str | list[str]]: 同槽多人(多 WITNESS)
    - list[tuple[str, str]]: 显式边列表
    """
    if not participants:
        return []
    out: list[tuple[str, str]] = []
    if isinstance(participants, list):
        for item in participants:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] and item[1]:
                out.append((str(item[0]), str(item[1])))
        return out
    if isinstance(participants, dict):
        for role, val in participants.items():
            if isinstance(val, (list, tuple, set)):
                for oid in val:
                    if oid:
                        out.append((str(role), str(oid)))
            elif val:
                out.append((str(role), str(val)))
    return out


def rebuild_participants_from_parts(parts) -> dict:
    """从 involves 边行重建 participants:同 role 多人时值为 list。"""
    out: dict = {}
    for p in parts or []:
        role = p.get("role") or "PART"
        clocal = p.get("clocal")
        if clocal is None:
            continue
        oid = f"role:{clocal}"
        if role not in out:
            out[role] = oid
            continue
        cur = out[role]
        if isinstance(cur, list):
            if oid not in cur:
                cur.append(oid)
        elif cur != oid:
            out[role] = [cur, oid]
    return out


def witnesses_of(event: Event) -> set[str]:
    """在场者 = 事件的全部参与者 oid(含同槽多 WITNESS)。"""
    return {oid for _, oid in iter_participants(event.participants)}


def see_event(world: World, event: Event,
              ingest_seq: int | None = None) -> list[KnowledgeEdge]:
    """看见即知道:在场目击者获知本事件每条 effect;不在场者不获知(无知是默认)。

    ingest_seq:由 store.add_event(ingest 路径)透传,供 purge_ingest 幂等清理;
    手动/MCP 不传 → 边的 ingest_seq=NONE,不受 purge 影响。
    """
    new_edges: list[KnowledgeEdge] = []
    for fid in event.effects:
        for w in witnesses_of(event):
            edge = KnowledgeEdge(w, fid, since_chapter=event.story_time, acquired_via="saw")
            # SurrealStore.add_knowledge 接受 ingest_seq;内存 World 不接受 → TypeError 回退
            if ingest_seq is not None:
                try:
                    world.add_knowledge(edge, ingest_seq=ingest_seq)
                except TypeError:
                    world.add_knowledge(edge)
            else:
                world.add_knowledge(edge)
            new_edges.append(edge)
    return new_edges

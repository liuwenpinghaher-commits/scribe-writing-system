"""Scribe 数据层(SQLite,纯 stdlib —— 可单测验证)。

设计依据:设计文档/00-总纲与数据模型.md §4 / §2.7(多本书隔离)。
安全(工程9):全部参数化查询,绝不字符串拼 SQL;写隔离与 human-lock 保护见 save_snapshot。
ponytail: id 用 uuid4(够用);若日后需时间排序再换 uuid7。向量检索在 vec.py(可选 sqlite-vec)。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


class Database:
    def __init__(self, path: str = "scribe.db"):
        # check_same_thread=False: MCP server 可能跨线程调用;写操作仍串行通过同一连接
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")  # 工程9: 崩溃续跑友好
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        self.conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """对已存在的旧库补列/补表(CREATE IF NOT EXISTS 不会给旧表加列)。每条容错。"""
        for sql in [
            "ALTER TABLE segments ADD COLUMN citation_refs TEXT",
            # C3-1 成本账本:每次 LLM 调用的 token 与估算成本
            "CREATE TABLE IF NOT EXISTS token_records ("
            "id TEXT PRIMARY KEY, work_id TEXT, role TEXT, model TEXT, "
            "prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd REAL, created_at TEXT)",
            # C3-3 章任务编排状态机
            "CREATE TABLE IF NOT EXISTS chapter_tasks ("
            "id TEXT PRIMARY KEY, work_id TEXT NOT NULL, seq INTEGER NOT NULL, "
            "status TEXT NOT NULL, detail TEXT, updated_at TEXT, UNIQUE(work_id, seq))",
            # B3 写工具审批队列
            "CREATE TABLE IF NOT EXISTS pending_writes ("
            "id TEXT PRIMARY KEY, work_id TEXT NOT NULL, tool_name TEXT NOT NULL, "
            "args_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "result_json TEXT, created_at TEXT NOT NULL, decided_at TEXT)",
        ]:
            try:
                self.conn.execute(sql); self.conn.commit()
            except sqlite3.OperationalError:
                pass  # 列已存在
        # 关系丰富化增列(新库 schema.sql 已含,旧库靠 ALTER 补;已存在则忽略)
        for col, ddl in [
            ("src_type", "ALTER TABLE entity_relations ADD COLUMN src_type TEXT"),
            ("dst_type", "ALTER TABLE entity_relations ADD COLUMN dst_type TEXT"),
            ("relation_category", "ALTER TABLE entity_relations ADD COLUMN relation_category TEXT"),
            ("weight", "ALTER TABLE entity_relations ADD COLUMN weight REAL DEFAULT 1.0"),
            ("directed", "ALTER TABLE entity_relations ADD COLUMN directed INTEGER DEFAULT 1"),
        ]:
            try:
                self.conn.execute(ddl)
            except Exception:
                pass  # 列已存在
        self.conn.commit()

    # ---- 作品 / 多本书(00 §2.7:owner 边界)----
    def create_work(self, owner_id: str, title: str, premise: str = "",
                    genre: str = "", structure_type: str = "") -> str:
        wid = _id()
        ts = _now()
        self.conn.execute(
            "INSERT INTO works(id,owner_id,title,premise,genre,structure_type,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (wid, owner_id, title, premise, genre, structure_type, ts, ts),
        )
        self.conn.commit()
        return wid

    def get_work(self, work_id: str) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM works WHERE id=? AND deleted_at IS NULL", (work_id,)
        ).fetchone()
        return dict(r) if r else None

    def list_all_works(self) -> list[dict]:
        """全部作品(跨 owner)—— 供后台主动引擎周期体检。"""
        rows = self.conn.execute(
            "SELECT * FROM works WHERE deleted_at IS NULL"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_works(self, owner_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM works WHERE owner_id=? AND deleted_at IS NULL ORDER BY updated_at DESC",
            (owner_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def work_summaries(self, owner_id: str) -> list[dict]:
        """作品库汇总(P0-6):每本书附 章数/字数/待看札记/待决方案 —— 一次查询消 N+1。"""
        out = []
        for w in self.list_works(owner_id):
            wid = w["id"]
            chap = self.conn.execute("SELECT COUNT(*) c, COALESCE(SUM(word_count),0) wc "
                                     "FROM chapters WHERE work_id=?", (wid,)).fetchone()
            ins = self.conn.execute("SELECT COUNT(*) c FROM proactive_insights "
                                    "WHERE work_id=? AND status='new'", (wid,)).fetchone()
            opt = self.conn.execute("SELECT COUNT(*) c FROM option_sets "
                                    "WHERE work_id=? AND chosen_option_id IS NULL", (wid,)).fetchone()
            out.append({**w, "chapter_count": chap["c"], "word_count": chap["wc"],
                        "new_insight_count": ins["c"], "pending_optionset_count": opt["c"]})
        return out

    # ---- 卷 Volume(P0-1:大纲树两级)----
    def create_volume(self, work_id: str, seq: int, title: str = "", arc_goal: str = "") -> str:
        existing = self.conn.execute(
            "SELECT id FROM volumes WHERE work_id=? AND seq=?", (work_id, seq)).fetchone()
        if existing:
            self.conn.execute("UPDATE volumes SET title=?, arc_goal=? WHERE id=?",
                              (title, arc_goal, existing["id"]))
            self.conn.commit()
            return existing["id"]
        vid = _id()
        self.conn.execute("INSERT INTO volumes(id,work_id,seq,title,arc_goal,status) "
                          "VALUES(?,?,?,?,?,'draft')", (vid, work_id, seq, title, arc_goal))
        self.conn.commit()
        return vid

    def list_volumes(self, work_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,seq,title,arc_goal,status FROM volumes WHERE work_id=? ORDER BY seq",
            (work_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- 北极星 ----
    def set_author_intent(self, work_id: str, reader_feeling: str = "",
                          core_emotional_arc: str = "", why_write: str = "",
                          central_promise: str = "", do_not_betray: list | None = None) -> str:
        iid = _id()
        self.conn.execute(
            "INSERT INTO author_intents(id,work_id,reader_feeling,core_emotional_arc,why_write,"
            "central_promise,do_not_betray,updated_at) VALUES(?,?,?,?,?,?,?,?)"
            " ON CONFLICT(work_id) DO UPDATE SET reader_feeling=excluded.reader_feeling,"
            " core_emotional_arc=excluded.core_emotional_arc, why_write=excluded.why_write,"
            " central_promise=excluded.central_promise, do_not_betray=excluded.do_not_betray,"
            " updated_at=excluded.updated_at",
            (iid, work_id, reader_feeling, core_emotional_arc, why_write, central_promise,
             json.dumps(do_not_betray or [], ensure_ascii=False), _now()),
        )
        self.conn.commit()
        return iid

    def get_author_intent(self, work_id: str) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM author_intents WHERE work_id=?", (work_id,)
        ).fetchone()
        return dict(r) if r else None

    # ---- 章节(upsert by work+seq)----
    def save_chapter(self, work_id: str, seq: int, title: str = "",
                     outline: dict | None = None, status: str = "draft",
                     volume_id: str | None = None) -> str:
        existing = self.conn.execute(
            "SELECT id FROM chapters WHERE work_id=? AND seq=?", (work_id, seq)
        ).fetchone()
        ol = json.dumps(outline or {}, ensure_ascii=False)
        if existing:
            if volume_id is not None:
                self.conn.execute("UPDATE chapters SET title=?, outline=?, status=?, volume_id=? WHERE id=?",
                                  (title, ol, status, volume_id, existing["id"]))
            else:
                self.conn.execute("UPDATE chapters SET title=?, outline=?, status=? WHERE id=?",
                                  (title, ol, status, existing["id"]))
            self.conn.commit()
            return existing["id"]
        cid = _id()
        self.conn.execute(
            "INSERT INTO chapters(id,work_id,volume_id,seq,title,outline,status) VALUES(?,?,?,?,?,?,?)",
            (cid, work_id, volume_id, seq, title, ol, status),
        )
        self.conn.commit()
        return cid

    def get_chapter(self, work_id: str, seq: int) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM chapters WHERE work_id=? AND seq=?", (work_id, seq)
        ).fetchone()
        return dict(r) if r else None

    def set_chapter_status(self, work_id: str, seq: int, status: str) -> None:
        """只改状态,不动 title/outline(P1-3 标记完成)。"""
        self.conn.execute("UPDATE chapters SET status=? WHERE work_id=? AND seq=?",
                          (status, work_id, seq))
        self.conn.commit()

    def chapters_citing(self, work_id: str, name: str) -> list[dict]:
        """引用过某设定/角色名的章节(按 seq 序),每章给首个出现段的片段。
        驱动『影响分析』(改设定→受影响章节)与『角色时间线』(出场轨迹)。"""
        rows = self.conn.execute(
            "SELECT c.seq AS seq, c.title AS title, s.seq AS sseq, s.text AS text, "
            "s.citation_refs AS refs FROM segments s JOIN chapters c ON s.chapter_id=c.id "
            "WHERE c.work_id=? AND s.citation_refs IS NOT NULL AND s.citation_refs!='[]' "
            "ORDER BY c.seq, s.seq",
            (work_id,),
        ).fetchall()
        out: list[dict] = []
        seen: set[int] = set()
        for r in rows:
            try:
                names = {c.get("name") for c in json.loads(r["refs"])}
            except Exception:
                names = set()
            if name in names and r["seq"] not in seen:
                seen.add(r["seq"])
                snip = (r["text"] or "")[:80]
                out.append({"seq": r["seq"], "title": r["title"], "snippet": snip})
        return out

    def move_chapter(self, work_id: str, seq: int, direction: int) -> bool:
        """与相邻章交换 seq(direction: -1 上移 / +1 下移)。内容随 chapter_id,不丢快照/引用。
        用临时偏移避免 (work_id,seq) 唯一约束冲突。到首/末则空操作返回 False。"""
        chs = self.conn.execute(
            "SELECT seq FROM chapters WHERE work_id=? ORDER BY seq", (work_id,)
        ).fetchall()
        seqs = [r["seq"] for r in chs]
        if seq not in seqs:
            return False
        i = seqs.index(seq)
        j = i + direction
        if j < 0 or j >= len(seqs):
            return False
        a, b = seqs[i], seqs[j]
        tmp = max(seqs) + 1000
        cur = self.conn
        cur.execute("UPDATE chapters SET seq=? WHERE work_id=? AND seq=?", (tmp, work_id, a))
        cur.execute("UPDATE chapters SET seq=? WHERE work_id=? AND seq=?", (a, work_id, b))
        cur.execute("UPDATE chapters SET seq=? WHERE work_id=? AND seq=?", (b, work_id, tmp))
        cur.commit()
        return True

    def list_chapters(self, work_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, seq, title, status, word_count, volume_id FROM chapters "
            "WHERE work_id=? ORDER BY seq",
            (work_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 设定项(自动注入/校验的真理源)----
    def upsert_setting(self, work_id: str, type_: str, name: str,
                       content: dict | None = None, first_chapter_seq: int | None = None) -> str:
        existing = self.conn.execute(
            "SELECT id FROM setting_items WHERE work_id=? AND type=? AND name=?",
            (work_id, type_, name),
        ).fetchone()
        payload = json.dumps(content or {}, ensure_ascii=False)
        if existing:
            self.conn.execute(
                "UPDATE setting_items SET content=?, first_chapter_seq=? WHERE id=?",
                (payload, first_chapter_seq, existing["id"]),
            )
            self.conn.commit()
            return existing["id"]
        sid = _id()
        self.conn.execute(
            "INSERT INTO setting_items(id,work_id,type,name,content,first_chapter_seq)"
            " VALUES(?,?,?,?,?,?)",
            (sid, work_id, type_, name, payload, first_chapter_seq),
        )
        self.conn.commit()
        return sid

    def list_settings(self, work_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM setting_items WHERE work_id=? ORDER BY type,name", (work_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 想象捕获(// 零摩擦)----
    def capture_imagination(self, work_id: str, raw_text: str, type_: str = "") -> str:
        iid = _id()
        self.conn.execute(
            "INSERT INTO imaginations(id,work_id,raw_text,type,status,created_at)"
            " VALUES(?,?,?,?,'captured',?)",
            (iid, work_id, raw_text, type_, _now()),
        )
        self.conn.commit()
        return iid

    def set_imagination_status(self, imagination_id: str, status: str) -> None:
        """C0-6 想象状态机推进:captured→structured→scheduled→used。"""
        self.conn.execute("UPDATE imaginations SET status=? WHERE id=?", (status, imagination_id))
        self.conn.commit()

    def list_imaginations(self, work_id: str, status: str | None = None) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM imaginations WHERE work_id=? AND status=? ORDER BY created_at",
                (work_id, status),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM imaginations WHERE work_id=? ORDER BY created_at", (work_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- 意见 ----
    def save_feedback(self, work_id: str, target_type: str, target_id: str,
                      nl_critique: str, parsed_directive: dict | None = None) -> str:
        fid = _id()
        self.conn.execute(
            "INSERT INTO feedback_notes(id,work_id,target_type,target_id,nl_critique,"
            "parsed_directive,created_at) VALUES(?,?,?,?,?,?,?)",
            (fid, work_id, target_type, target_id, nl_critique,
             json.dumps(parsed_directive or {}, ensure_ascii=False), _now()),
        )
        self.conn.commit()
        return fid

    # ---- 版本快照(写隔离 + human-lock 保护,工程9)----
    def save_snapshot(self, work_id: str, chapter_id: str, content: str,
                      created_by: str = "ai", parent_id: str | None = None,
                      branch_label: str = "ai-draft") -> str:
        # 工程9 / 工程4: AI 不得覆盖 human-locked 的章节内容(只能开新分支)
        if created_by == "ai":
            locked = self.conn.execute(
                "SELECT 1 FROM snapshots WHERE chapter_id=? AND is_human_locked=1 LIMIT 1",
                (chapter_id,),
            ).fetchone()
            if locked and branch_label == "human-final":
                raise PermissionError("AI 不能写入 human-final 分支(human-locked 受保护)")
        sid = _id()
        self.conn.execute(
            "INSERT INTO snapshots(id,chapter_id,work_id,content,created_by,parent_id,"
            "branch_label,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (sid, chapter_id, work_id, content, created_by, parent_id, branch_label, _now()),
        )
        self.conn.commit()
        return sid

    def lock_snapshot(self, snapshot_id: str) -> None:
        self.conn.execute("UPDATE snapshots SET is_human_locked=1 WHERE id=?", (snapshot_id,))
        self.conn.commit()

    def list_snapshots(self, chapter_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM snapshots WHERE chapter_id=? ORDER BY created_at", (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 段落 Segment + 引用(P0-2:正文按段存,回填引用了哪些设定/角色)----
    def save_segments(self, work_id: str, chapter_id: str, content: str,
                      created_by: str = "ai") -> int:
        """把整章正文按自然段切分入 segments,并规则化回填引用(段内出现的设定/角色名)。
        返回段数。引用 = 该段文本中出现的 设定项/角色 名(可机检,供前端"引用展开")。"""
        paras = [p.strip() for p in (content or "").split("\n") if p.strip()]
        names: list[tuple[str, str]] = []
        for s in self.list_settings(work_id):
            if s["name"]:
                names.append((s["name"], f"setting:{s['type']}"))
        for c in self.list_characters(work_id):
            if c["name"]:
                names.append((c["name"], "character"))
        self.conn.execute("DELETE FROM segments WHERE chapter_id=?", (chapter_id,))
        for i, p in enumerate(paras):
            cites = [{"name": n, "kind": k} for (n, k) in names if n in p]
            self.conn.execute(
                "INSERT INTO segments(id,chapter_id,work_id,seq,text,created_by,citation_refs) "
                "VALUES(?,?,?,?,?,?,?)",
                (_id(), chapter_id, work_id, i, p, created_by,
                 json.dumps(cites, ensure_ascii=False)),
            )
        self.conn.commit()
        return len(paras)

    def list_segments(self, chapter_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, seq, text, created_by, citation_refs FROM segments "
            "WHERE chapter_id=? ORDER BY seq", (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 多方案 OptionSet(协作回路:AI 出选项,人拍板)----
    def create_option_set(self, work_id: str, decision_point: str,
                          options: list[dict]) -> str:
        if not (2 <= len(options) <= 4):
            raise ValueError("OptionSet 需 2–4 个有差异的方案")
        oid = _id()
        self.conn.execute(
            "INSERT INTO option_sets(id,work_id,decision_point,options,created_at) "
            "VALUES(?,?,?,?,?)",
            (oid, work_id, json.dumps({"text": decision_point}, ensure_ascii=False),
             json.dumps(options, ensure_ascii=False), _now()),
        )
        self.conn.commit()
        return oid

    def list_open_option_sets(self, work_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM option_sets WHERE work_id=? AND chosen_option_id IS NULL "
            "ORDER BY created_at",
            (work_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_option_set(self, option_set_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM option_sets WHERE id=?", (option_set_id,)).fetchone()
        return dict(r) if r else None

    def choose_option(self, option_set_id: str, chosen_option_id: str,
                      rationale: str = "") -> dict:
        row = self.conn.execute(
            "SELECT * FROM option_sets WHERE id=?", (option_set_id,)
        ).fetchone()
        if not row:
            raise ValueError("OptionSet 不存在")
        if row["chosen_option_id"] is not None:
            raise ValueError("该 OptionSet 已选择,不可重复")
        opts = json.loads(row["options"])
        ids = {str(o.get("id", i)) for i, o in enumerate(opts)}
        if chosen_option_id not in ids:
            raise ValueError(f"chosen_option_id 不在选项中: {chosen_option_id}")
        self.conn.execute(
            "UPDATE option_sets SET chosen_option_id=?, choose_rationale=? WHERE id=?",
            (chosen_option_id, rationale, option_set_id),
        )
        self.conn.commit()
        return {"option_set_id": option_set_id, "chosen": chosen_option_id}

    # ---- 角色(设定圣经)----
    def upsert_character(self, work_id: str, name: str, traits: dict | None = None,
                         motivation: str = "", voice_profile: dict | None = None) -> str:
        existing = self.conn.execute(
            "SELECT id FROM characters WHERE work_id=? AND name=?", (work_id, name)
        ).fetchone()
        tr = json.dumps(traits or {}, ensure_ascii=False)
        vp = json.dumps(voice_profile or {}, ensure_ascii=False)
        if existing:
            self.conn.execute(
                "UPDATE characters SET traits=?, motivation=?, voice_profile=? WHERE id=?",
                (tr, motivation, vp, existing["id"]),
            )
            self.conn.commit()
            return existing["id"]
        cid = _id()
        self.conn.execute(
            "INSERT INTO characters(id,work_id,name,traits,motivation,voice_profile)"
            " VALUES(?,?,?,?,?,?)",
            (cid, work_id, name, tr, motivation, vp),
        )
        self.conn.commit()
        return cid

    def list_characters(self, work_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM characters WHERE work_id=? ORDER BY name", (work_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_character_by_name(self, work_id: str, name: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM characters WHERE work_id=? AND name=?",
                              (work_id, name)).fetchone()
        return dict(r) if r else None

    # ---- C2-1 三层记忆(memory_entries:chapter/volume/global 滚动摘要)----
    def upsert_memory(self, work_id: str, scope: str, summary_text: str,
                      source_chapter_range: str = "") -> str:
        """同 scope 覆盖更新(chapter 用 scope=f'chapter:{seq}')。"""
        row = self.conn.execute(
            "SELECT id FROM memory_entries WHERE work_id=? AND scope=?", (work_id, scope)).fetchone()
        if row:
            self.conn.execute("UPDATE memory_entries SET summary_text=?, source_chapter_range=?, "
                              "updated_at=? WHERE id=?",
                              (summary_text, source_chapter_range, _now(), row["id"]))
            self.conn.commit()
            return row["id"]
        mid = _id()
        self.conn.execute("INSERT INTO memory_entries(id,work_id,scope,summary_text,"
                          "source_chapter_range,updated_at) VALUES(?,?,?,?,?,?)",
                          (mid, work_id, scope, summary_text, source_chapter_range, _now()))
        self.conn.commit()
        return mid

    def get_memory(self, work_id: str, scope: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM memory_entries WHERE work_id=? AND scope=?",
                              (work_id, scope)).fetchone()
        return dict(r) if r else None

    def list_chapter_memories(self, work_id: str, upto_seq: int | None = None) -> list[dict]:
        """章级记忆(scope 形如 chapter:N),可只取 ≤upto_seq(C2-6 防剧透)。"""
        rows = self.conn.execute(
            "SELECT * FROM memory_entries WHERE work_id=? AND scope LIKE 'chapter:%'", (work_id,)
        ).fetchall()
        out = []
        for r in rows:
            try:
                seq = int(r["scope"].split(":", 1)[1])
            except Exception:
                continue
            if upto_seq is None or seq <= upto_seq:
                out.append({**dict(r), "seq": seq})
        return sorted(out, key=lambda x: x["seq"])

    # ---- C2-4 角色状态时间线 / 实体关系 / 时间线事件 ----
    def add_char_state(self, character_id: str, chapter_seq: int, state_desc: str,
                       change_type: str = "") -> str:
        sid = _id()
        self.conn.execute("INSERT INTO char_states(id,character_id,chapter_seq,state_desc,"
                          "change_type) VALUES(?,?,?,?,?)",
                          (sid, character_id, chapter_seq, state_desc, change_type))
        self.conn.commit()
        return sid

    def get_char_state_at(self, character_id: str, chapter_seq: int) -> dict | None:
        """C2-6 时点查询:该角色截至某章的最新状态(不泄露未来)。"""
        r = self.conn.execute(
            "SELECT * FROM char_states WHERE character_id=? AND chapter_seq<=? "
            "ORDER BY chapter_seq DESC LIMIT 1", (character_id, chapter_seq)).fetchone()
        return dict(r) if r else None

    def list_char_states(self, character_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM char_states WHERE character_id=? "
                                 "ORDER BY chapter_seq", (character_id,)).fetchall()
        return [dict(r) for r in rows]

    def add_relation(self, work_id: str, src: str, dst: str, relation: str,
                     valid_from: int | None = None, src_type: str | None = None,
                     dst_type: str | None = None, category: str | None = None,
                     weight: float = 1.0, directed: int = 1) -> str:
        existing = self.conn.execute(
            "SELECT id, weight FROM entity_relations WHERE work_id=? AND src_entity=? "
            "AND dst_entity=? AND relation=?", (work_id, src, dst, relation)).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE entity_relations SET weight=?, valid_from_chapter=COALESCE(valid_from_chapter, ?) "
                "WHERE id=?", ((existing["weight"] or 1.0) + 1.0, valid_from, existing["id"]))
            self.conn.commit()
            return existing["id"]
        rid = _id()
        self.conn.execute(
            "INSERT INTO entity_relations(id,work_id,src_entity,dst_entity,relation,"
            "valid_from_chapter,src_type,dst_type,relation_category,weight,directed) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (rid, work_id, src, dst, relation, valid_from, src_type, dst_type, category, weight, directed))
        self.conn.commit()
        return rid

    def list_relations(self, work_id: str, upto_seq: int | None = None) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM entity_relations WHERE work_id=?",
                                 (work_id,)).fetchall()
        out = [dict(r) for r in rows]
        if upto_seq is not None:
            out = [r for r in out if (r["valid_from_chapter"] or 0) <= upto_seq]
        return out

    def add_timeline_event(self, work_id: str, chapter_seq: int, description: str,
                           rel_order: int | None = None, entity_refs: list | None = None) -> str:
        import json as _j
        tid = _id()
        self.conn.execute("INSERT INTO timeline_events(id,work_id,chapter_seq,rel_order,"
                          "description,entity_refs) VALUES(?,?,?,?,?,?)",
                          (tid, work_id, chapter_seq, rel_order, description,
                           _j.dumps(entity_refs or [], ensure_ascii=False)))
        self.conn.commit()
        return tid

    def list_timeline(self, work_id: str, upto_seq: int | None = None) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM timeline_events WHERE work_id=? "
                                 "ORDER BY chapter_seq, rel_order", (work_id,)).fetchall()
        out = [dict(r) for r in rows]
        if upto_seq is not None:
            out = [r for r in out if (r["chapter_seq"] or 0) <= upto_seq]
        return out

    # ---- C4 素材库(materials + material_refs)----
    def add_material(self, owner_id: str, type_: str, title: str, content: str,
                     source: str = "", tags: list | None = None,
                     work_id: str | None = None, status: str = "raw") -> str:
        import json as _j
        mid = _id()
        self.conn.execute(
            "INSERT INTO materials(id,owner_id,work_id,type,title,content,source,tags,status,"
            "created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (mid, owner_id, work_id, type_, title,
             _j.dumps({"text": content}, ensure_ascii=False), source,
             _j.dumps(tags or [], ensure_ascii=False), status, _now()))
        self.conn.commit()
        return mid

    def update_material(self, material_id: str, *, tags: list | None = None,
                        status: str | None = None, title: str | None = None) -> None:
        import json as _j
        sets, params = [], []
        if tags is not None:
            sets.append("tags=?"); params.append(_j.dumps(tags, ensure_ascii=False))
        if status is not None:
            sets.append("status=?"); params.append(status)
        if title is not None:
            sets.append("title=?"); params.append(title)
        if not sets:
            return
        params.append(material_id)
        self.conn.execute(f"UPDATE materials SET {', '.join(sets)} WHERE id=?", params)
        self.conn.commit()

    def get_material(self, material_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        return dict(r) if r else None

    def list_materials(self, owner_id: str, work_id: str | None = None,
                       type_: str | None = None) -> list[dict]:
        """owner 级 + 可选本书级;防串味同 TasteModel(work_id NULL=跨作品)。"""
        q = "SELECT * FROM materials WHERE owner_id=?"
        params: list = [owner_id]
        if work_id:
            q += " AND (work_id IS NULL OR work_id=?)"; params.append(work_id)
        if type_:
            q += " AND type=?"; params.append(type_)
        q += " ORDER BY created_at DESC"
        return [dict(r) for r in self.conn.execute(q, params).fetchall()]

    def delete_material(self, material_id: str) -> None:
        self.conn.execute("DELETE FROM material_refs WHERE material_id=?", (material_id,))
        self.conn.execute("DELETE FROM materials WHERE id=?", (material_id,))
        self.conn.commit()

    def delete_work(self, work_id: str) -> None:
        """软删作品:置 deleted_at(所有 work 查询已过滤 deleted_at IS NULL,可恢复)。"""
        self.conn.execute("UPDATE works SET deleted_at=? WHERE id=?", (_now(), work_id))
        self.conn.commit()

    def add_material_ref(self, material_id: str, used_in: str, target_id: str = "",
                         ref_type: str = "ai_inject") -> str:
        rid = _id()
        self.conn.execute(
            "INSERT INTO material_refs(id,material_id,used_in,target_id,ref_type,created_at) "
            "VALUES(?,?,?,?,?,?)", (rid, material_id, used_in, target_id, ref_type, _now()))
        self.conn.commit()
        return rid

    def list_material_refs(self, material_id: str) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM material_refs WHERE material_id=? ORDER BY created_at",
            (material_id,)).fetchall()]

    # ---- C5-4 讨论线程(主编对话持久化,discussion_threads)----
    def create_thread(self, work_id: str, topic: str, trigger: str = "chat") -> str:
        import json as _j
        tid = _id()
        self.conn.execute(
            "INSERT INTO discussion_threads(id,work_id,trigger,topic,messages,status,created_at) "
            "VALUES(?,?,?,?,?,'open',?)", (tid, work_id, trigger, topic, _j.dumps([]), _now()))
        self.conn.commit()
        return tid

    def add_thread_message(self, thread_id: str, role: str, text: str,
                           concern_type: str = "", evidence_refs: list | None = None) -> None:
        import json as _j
        r = self.conn.execute("SELECT messages FROM discussion_threads WHERE id=?",
                              (thread_id,)).fetchone()
        if not r:
            return
        msgs = _j.loads(r["messages"] or "[]")
        msgs.append({"role": role, "text": text, "concern_type": concern_type,
                     "evidence_refs": evidence_refs or [], "at": _now()})
        self.conn.execute("UPDATE discussion_threads SET messages=? WHERE id=?",
                          (_j.dumps(msgs, ensure_ascii=False), thread_id))
        self.conn.commit()

    def list_threads(self, work_id: str, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM discussion_threads WHERE work_id=?"
        p: list = [work_id]
        if status:
            q += " AND status=?"; p.append(status)
        q += " ORDER BY created_at DESC"
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    def resolve_thread(self, thread_id: str, status: str = "resolved", resolution: str = "") -> None:
        import json as _j
        self.conn.execute("UPDATE discussion_threads SET status=?, resolution=? WHERE id=?",
                          (status, _j.dumps({"text": resolution}, ensure_ascii=False), thread_id))
        self.conn.commit()

    # ---- C-D 跨会话记忆(agent_memory,5 命名空间;<阈值不入)----
    def write_agent_memory(self, owner_id: str, namespace: str, key: str, value: dict,
                           confidence: float = 1.0, work_id: str | None = None,
                           min_confidence: float = 0.8) -> str | None:
        import json as _j
        if confidence < min_confidence:
            return None  # 低置信不入(设计要求)
        existing = self.conn.execute(
            "SELECT id FROM agent_memory WHERE owner_id=? AND namespace=? AND key=? "
            "AND (work_id IS ? OR work_id=?)",
            (owner_id, namespace, key, work_id, work_id)).fetchone()
        val = _j.dumps(value, ensure_ascii=False)
        if existing:
            self.conn.execute("UPDATE agent_memory SET value=?, confidence=?, updated_at=? WHERE id=?",
                              (val, confidence, _now(), existing["id"]))
            self.conn.commit()
            return existing["id"]
        mid = _id()
        self.conn.execute(
            "INSERT INTO agent_memory(id,owner_id,work_id,namespace,key,value,confidence,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (mid, owner_id, work_id, namespace, key, val, confidence, _now()))
        self.conn.commit()
        return mid

    def read_agent_memory(self, owner_id: str, namespace: str | None = None,
                          work_id: str | None = None) -> list[dict]:
        q = "SELECT * FROM agent_memory WHERE owner_id=? AND (work_id IS NULL OR work_id=?)"
        p: list = [owner_id, work_id]
        if namespace:
            q += " AND namespace=?"; p.append(namespace)
        q += " ORDER BY updated_at DESC"
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    # ---- C-D 自我优化技能(agent_skills,须人审批)----
    def propose_skill(self, owner_id: str, name: str, spec: dict, created_by: str = "editor") -> str:
        import json as _j
        sid = _id()
        self.conn.execute(
            "INSERT INTO agent_skills(id,owner_id,name,spec,status,created_by,approved_by_human,"
            "created_at) VALUES(?,?,?,?,'proposed',?,0,?)",
            (sid, owner_id, name, _j.dumps(spec, ensure_ascii=False), created_by, _now()))
        self.conn.commit()
        return sid

    def list_skills(self, owner_id: str, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM agent_skills WHERE owner_id=?"
        p: list = [owner_id]
        if status:
            q += " AND status=?"; p.append(status)
        return [dict(r) for r in self.conn.execute(q + " ORDER BY created_at DESC", p).fetchall()]

    def set_skill_status(self, skill_id: str, status: str, approved_by_human: bool = False) -> None:
        self.conn.execute("UPDATE agent_skills SET status=?, approved_by_human=? WHERE id=?",
                          (status, 1 if approved_by_human else 0, skill_id))
        self.conn.commit()

    # ---- 主编札记 ProactiveInsight(内核0 主动引擎)----
    def add_proactive_insight(self, work_id: str, kind: str, summary: str,
                              severity: str = "info", confidence: float = 0.8,
                              suggested_action: str = "", evidence_refs: dict | None = None) -> str:
        iid = _id()
        self.conn.execute(
            "INSERT INTO proactive_insights(id,work_id,kind,summary,evidence_refs,confidence,"
            "severity,suggested_action,status,created_at) VALUES(?,?,?,?,?,?,?,?,'new',?)",
            (iid, work_id, kind, summary, json.dumps(evidence_refs or {}, ensure_ascii=False),
             confidence, severity, suggested_action, _now()),
        )
        self.conn.commit()
        return iid

    def list_proactive_insights(self, work_id: str, status: str = "new") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM proactive_insights WHERE work_id=? AND status=? ORDER BY created_at DESC",
            (work_id, status),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_insight_status(self, insight_id: str, status: str) -> None:
        if status not in ("new", "acked", "acted", "dismissed"):
            raise ValueError("status 非法")
        self.conn.execute("UPDATE proactive_insights SET status=? WHERE id=?", (status, insight_id))
        self.conn.commit()

    def insight_exists(self, work_id: str, kind: str, ref_key: str) -> bool:
        """去重:同 work+kind 且 evidence_refs.key 已存在则不重复生成(防札记刷屏)。"""
        rows = self.conn.execute(
            "SELECT evidence_refs FROM proactive_insights WHERE work_id=? AND kind=? "
            "AND status IN('new','acked')",
            (work_id, kind),
        ).fetchall()
        for r in rows:
            try:
                if json.loads(r["evidence_refs"]).get("key") == ref_key:
                    return True
            except Exception:
                pass
        return False

    # ---- B3 写工具审批队列(pending_writes:主编写类工具挂起,作者批准才真写)----
    def enqueue_pending_write(self, work_id: str, tool_name: str, args: dict) -> str:
        pid = _id()
        self.conn.execute(
            "INSERT INTO pending_writes(id,work_id,tool_name,args_json,status,created_at) "
            "VALUES(?,?,?,?, 'pending', ?)",
            (pid, work_id, tool_name, json.dumps(args, ensure_ascii=False), _now()))
        self.conn.commit()
        return pid

    def _row_to_pending(self, r) -> dict:
        return {"id": r["id"], "work_id": r["work_id"], "tool_name": r["tool_name"],
                "args": json.loads(r["args_json"]), "status": r["status"],
                "result": json.loads(r["result_json"]) if r["result_json"] else None,
                "created_at": r["created_at"], "decided_at": r["decided_at"]}

    def list_pending_writes(self, work_id: str, status: str = "pending") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM pending_writes WHERE work_id=? AND status=? ORDER BY created_at",
            (work_id, status)).fetchall()
        return [self._row_to_pending(r) for r in rows]

    def get_pending_write(self, pid: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM pending_writes WHERE id=?", (pid,)).fetchone()
        return self._row_to_pending(r) if r else None

    def mark_pending_decided(self, pid: str, status: str, result: dict | None) -> None:
        if status not in ("approved", "rejected"):
            raise ValueError(f"非法决断状态: {status}(只能 approved/rejected)")
        self.conn.execute(
            "UPDATE pending_writes SET status=?, result_json=?, decided_at=? WHERE id=?",
            (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
             _now(), pid))
        self.conn.commit()

    # ---- 一致性标记(门槛1,后台校验产出)----
    def raise_consistency_flag(self, work_id: str, error_class: str, chapter_seq: int | None,
                               severity: str = "minor", detail: str = "",
                               evidence_refs: dict | None = None) -> str:
        fid = _id()
        self.conn.execute(
            "INSERT INTO consistency_flags(id,work_id,chapter_seq,error_class,severity,detail,"
            "evidence_refs,status,created_at) VALUES(?,?,?,?,?,?,?,'open',?)",
            (fid, work_id, chapter_seq, error_class, severity, detail,
             json.dumps(evidence_refs or {}, ensure_ascii=False), _now()),
        )
        self.conn.commit()
        return fid

    def list_consistency_flags(self, work_id: str, status: str = "open") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM consistency_flags WHERE work_id=? AND status=? ORDER BY created_at",
            (work_id, status),
        ).fetchall()
        return [dict(r) for r in rows]

    def resolve_consistency_flag(self, flag_id: str, status: str) -> None:
        """作者裁决:confirmed/dismissed/fixed(回流阈值见门槛1)。"""
        if status not in ("confirmed", "dismissed", "fixed"):
            raise ValueError("status 必须是 confirmed/dismissed/fixed")
        self.conn.execute("UPDATE consistency_flags SET status=? WHERE id=?", (status, flag_id))
        self.conn.commit()

    # ---- 质量快照(C6-2 质量时序)----
    def add_quality_snapshot(self, work_id: str, scope: str, chapter_seq: int | None,
                             metrics: dict) -> str:
        sid = _id()
        self.conn.execute(
            "INSERT INTO quality_snapshots(id,work_id,scope,chapter_seq,words,slop_density,"
            "consistency_score,foreshadow_payoff,vocab_richness,repetition_rate,cost_usd,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, work_id, scope, chapter_seq, metrics.get("words"), metrics.get("slop_density"),
             metrics.get("consistency_score"), metrics.get("foreshadow_payoff"),
             metrics.get("vocab_richness"), metrics.get("repetition_rate"),
             metrics.get("cost_usd"), _now()))
        self.conn.commit()
        return sid

    def list_quality_snapshots(self, work_id: str, scope: str | None = None) -> list[dict]:
        q = "SELECT * FROM quality_snapshots WHERE work_id=?"
        p: list = [work_id]
        if scope:
            q += " AND scope=?"; p.append(scope)
        q += " ORDER BY created_at ASC"
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    def clear_chapter_extractions(self, work_id: str, seq: int) -> None:
        """重跑前清理该章既有时间线/角色状态/关系,避免重复堆积(关系按 valid_from 清)。"""
        self.conn.execute("DELETE FROM timeline_events WHERE work_id=? AND chapter_seq=?", (work_id, seq))
        self.conn.execute(
            "DELETE FROM char_states WHERE chapter_seq=? AND character_id IN "
            "(SELECT id FROM characters WHERE work_id=?)", (seq, work_id))
        self.conn.execute("DELETE FROM entity_relations WHERE work_id=? AND valid_from_chapter=?", (work_id, seq))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

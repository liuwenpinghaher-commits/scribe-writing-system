"""SurrealStore mixin: structure."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class StructureMixin:

    def refresh_quality_caches(self) -> list[int]:
        """重算所有缺失或过期的质量缓存，返回实际刷新章节号。"""
        rows = self._query(
            "SELECT seq, qc_cache_revision FROM chapter:.. "
            "WHERE archived = NONE OR archived != true")
        refreshed: list[int] = []
        for row in rows:
            seq = row.get("seq")
            if seq is None or row.get("qc_cache_revision") == QUALITY_CACHE_REVISION:
                continue
            if self.refresh_chapter_cache(int(seq)):
                refreshed.append(int(seq))
        return sorted(refreshed)

    def graph(self, chapter: int | None = None, focus: str | None = None,
              limit: int = 300, hop: int = 1) -> dict:
        """知识图谱:角色/命题/势力/物件节点 + knows/关系/归属 边(Atlas 视图)。
        千万字基座(Phase0-BE1):不再无上限全图返回。

        - focus 给定 → 只返回该实体的 ego 子图:focus + hop 跳邻居 + 它们之间的边。
        - focus 为 None → 返回"按 secret(密)优先、再按 valid_from 倒序"排序的 top-limit
          命题节点 + 相关角色/势力/物件 + 这些节点间的边,**硬上限 limit**(节点总数 ≤ limit)。
        - chapter 时间门保留(截至该章;None=全书)。

        节点 id 约定:role:… / fact:… / faction:{name} / item:{name}。
        向后兼容:无新参数调用(graph()/graph(ch))仍返回 {nodes, edges},结构不变。
        """
        ch = chapter if chapter is not None else 9999
        chars = [{"id": e.id, "type": "character", "label": e.name} for e in self.characters()]
        char_ids = {c["id"] for c in chars}
        # 图谱节点标签：优先可读摘要。截断略放宽(36)以免半句难懂；私密仍不泄明文。
        # id 形如 fact:d2-4 / fact:k3-1 仅作内部键，前端抽屉用人话化，勿当标题裸奔。
        def _prop_label(f) -> str:
            if f.secret:
                return "🔒 私密"
            raw = (f.value or "").strip() or (getattr(f, "attribute", None) or "")
            raw = str(raw).replace("\n", " ")
            return (raw[:36] + ("…" if len(raw) > 36 else "")) if raw else ""

        props = [{"id": f.id, "type": "proposition",
                  "label": _prop_label(f),
                  "secret": f.secret, "_vf": f.valid_from} for f in self.facts_at(ch)]
        facs = []
        for f in (self.list_factions() or []):
            name = f.get("name")
            if not name:
                continue
            facs.append({"id": f"faction:{name}", "type": "faction", "label": name})
        items = []
        for it in (self.list_items() or []):
            name = it.get("name")
            if not name:
                continue
            items.append({
                "id": f"item:{name}", "type": "item", "label": name,
                "_owner": it.get("current_owner"),
            })
        # 全量边(限知门控后),供子图/全图共同筛选
        all_edges = []
        for k in self.knowledge:
            # 与 project_frame 同谓词: since<=ch 且 (until is None 或 until>ch)
            if k.knower_id == "reader" or k.since_chapter > ch:
                continue
            if k.until_chapter is not None and k.until_chapter <= ch:
                continue
            all_edges.append({"src": k.knower_id, "dst": k.proposition_id, "rel": "knows"})
        for r in self.relations_at(ch):
            all_edges.append({"src": f"role:{r['src']}", "dst": f"role:{r['dst']}", "rel": r["relation"]})
        # 通用实体关系(势力↔势力/角色等,两端已是 role:/faction: 本体 id)
        try:
            erels = self.entity_relations_at(ch) if hasattr(self, "entity_relations_at") else []
        except Exception:
            erels = []
        for r in erels or []:
            a, b = r.get("a"), r.get("b")
            if not a or not b:
                continue
            all_edges.append({"src": a, "dst": b, "rel": r.get("relation_type") or "related"})
        # 势力已知成员 → 角色
        for f in (self.list_factions() or []):
            fname = f.get("name")
            if not fname:
                continue
            fid = f"faction:{fname}"
            for m in (f.get("known_members") or []):
                if not m:
                    continue
                rid = m if str(m).startswith("role:") else f"role:{m}"
                if rid in char_ids:
                    all_edges.append({"src": fid, "dst": rid, "rel": "member"})
        # 物件持有者 → 角色
        for n in items:
            owner = n.pop("_owner", None)
            if not owner:
                continue
            rid = owner if str(owner).startswith("role:") else f"role:{owner}"
            if rid in char_ids:
                all_edges.append({"src": n["id"], "dst": rid, "rel": "held_by"})

        def _strip(nodes):
            for n in nodes:
                n.pop("_vf", None)
                n.pop("_owner", None)
            return nodes

        all_nodes = chars + facs + items + props

        if focus:
            # —— ego 子图:从 focus 起 BFS hop 跳 ——
            keep = {focus}
            frontier = {focus}
            for _ in range(max(1, hop)):
                nxt = set()
                for e in all_edges:
                    if e["src"] in frontier:
                        nxt.add(e["dst"])
                    if e["dst"] in frontier:
                        nxt.add(e["src"])
                new = nxt - keep
                keep |= new
                frontier = new
                if not frontier:
                    break
            nodes = [n for n in all_nodes if n["id"] in keep]
            # focus 孤立时仍返回焦点节点(若它在全量节点表中)
            if focus not in {n["id"] for n in nodes}:
                for n in all_nodes:
                    if n["id"] == focus:
                        nodes.append(n)
                        break
                if focus not in {n["id"] for n in nodes}:
                    # 未知 focus 仍回空邻域占位,便于 Atlas 显示焦点 id
                    nodes.append({"id": focus, "type": "unknown", "label": focus})
            edges = [e for e in all_edges if e["src"] in keep and e["dst"] in keep]
            return {"nodes": _strip(nodes), "edges": edges}

        # —— 无 focus:top-limit 重要度子集,硬上限 ——
        # 命题排序:secret 优先(密谋更值得看),再按 valid_from 倒序(近事在前)。
        props_sorted = sorted(
            props, key=lambda p: (0 if p.get("secret") else 1, -(p.get("_vf") or 0)))
        # 角色 → 势力/物件 → 命题,依次占预算(图骨架优先)。
        budget = max(0, limit)
        nodes = chars[:budget]
        remaining = budget - len(nodes)
        if remaining > 0:
            nodes += (facs + items)[:remaining]
            remaining = budget - len(nodes)
        if remaining > 0:
            nodes += props_sorted[:remaining]
        keep = {n["id"] for n in nodes}
        edges = [e for e in all_edges if e["src"] in keep and e["dst"] in keep]
        return {"nodes": _strip(nodes), "edges": edges}

    def outline(self) -> dict:
        """聚合大纲:卷 + 章(梗概/字数/QC/视角/卷/标签 + 场景切分)。
        千万字基座(Phase0-BE1):**绝不 SELECT prose**——场景数/详情、QC 计数全读章级缓存列
        (scene_count / scene_meta / qc_issues / qc_causal,均由 save_chapter 写入)。
        存量章用 backfill_scalability_caches 回填缓存;未回填章缓存为 NONE,降级为 0/空。
        章按 sort_order 升序排列(sort_order 为 NONE 时回退 seq)。
        SurrealDB 不支持 ORDER BY (expr ?? expr) 括号形式,改在 Python 侧排序。
        """
        vols = self.list_volumes()
        sql = (
            "SELECT seq, sort_order, title, synopsis, focalizer, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, label, "
            "qc_word_count AS word_count, qc_issues, qc_causal, qc_breakdown, qc_cache_revision, "
            "scene_count, scene_meta, beats, beats_meta, "
            "craft_compliance, craft_compliance_at "
            "FROM chapter:.. WHERE archived = NONE OR archived != true"
        )
        sql_flags = (
            "SELECT seq, sort_order, title, synopsis, focalizer, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, label, "
            "qc_word_count AS word_count, qc_issues, qc_causal, qc_breakdown, qc_cache_revision, "
            "scene_count, scene_meta, beats, beats_meta, "
            "craft_compliance, craft_compliance_at, "
            "outline_status, outline_rev, confidence, settled_note, "
            "(IF prose IS NONE OR prose = '' THEN false ELSE true END) AS has_prose "
            "FROM chapter:.. WHERE archived = NONE OR archived != true"
        )
        try:
            rows = self._query(sql_flags)
        except Exception:
            try:
                sql_flags_old = sql_flags.replace(
                    "outline_status, outline_rev, confidence, settled_note, ",
                    "",
                )
                rows = self._query(sql_flags_old)
            except Exception:
                rows = self._query(sql)
        for r in rows:
            if "has_prose" in r:
                r["has_prose"] = bool(r.get("has_prose"))
        # Python 侧排序:sort_order 为 None 时回退 seq
        rows.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else r["seq"]))
        import json
        from scribe3.chapter_hooks import resolve_chapter_hook
        chapters = []
        for r in rows:
            raw_meta = r.pop("scene_meta", None)
            try:
                meta = json.loads(raw_meta) if raw_meta else []
            except (ValueError, TypeError):
                meta = []
            raw_bd = r.pop("qc_breakdown", None)
            try:
                breakdown = json.loads(raw_bd) if raw_bd else {}
            except (ValueError, TypeError):
                breakdown = {}
            from scribe3.qc_product_keys import project_product_qc_breakdown
            breakdown = project_product_qc_breakdown(breakdown)
            sc = r.get("scene_count")
            if sc is None:
                sc = len(meta)
            raw_beats = r.pop("beats", None)
            try:
                beats = json.loads(raw_beats) if isinstance(raw_beats, str) else (raw_beats or [])
            except (ValueError, TypeError):
                beats = []
            if not isinstance(beats, list):
                beats = []
            raw_bm = r.pop("beats_meta", None)
            try:
                beats_meta = json.loads(raw_bm) if isinstance(raw_bm, str) else (raw_bm or {})
            except (ValueError, TypeError):
                beats_meta = {}
            if not isinstance(beats_meta, dict):
                beats_meta = {}
            hook = resolve_chapter_hook(
                {"synopsis": r.get("synopsis"), "beats": beats, "beats_meta": beats_meta},
                beats_meta=beats_meta, beats=beats, synopsis=r.get("synopsis") or "",
            )
            raw_cc = r.pop("craft_compliance", None)
            if isinstance(raw_cc, str):
                try:
                    raw_cc = json.loads(raw_cc)
                except (ValueError, TypeError):
                    raw_cc = None
            chapters.append({
                **r,
                "scene_count": sc,
                "qc_breakdown": breakdown,
                "scenes": [{"idx": i, "title": m.get("title", ""),
                            "char_count": m.get("char_count", 0)}
                           for i, m in enumerate(meta)],
                "hook_structured": bool(hook),
                "hook_preview": (hook or "")[:40],
                "craft_compliance": raw_cc if isinstance(raw_cc, dict) else None,
            })

        unassigned = [c["seq"] for c in chapters if not c.get("volume")]
        return {"volumes": vols, "chapters": chapters, "unassigned_chapters": unassigned}

    def project_tree(self) -> dict:
        """聚合左侧项目树:手稿支(卷→章→场景)+ 素材支(分类→条目)+ 横切视图清单。

        只读统一投影:复用 outline()/characters()/list_*() ,不新造存储。
        每个节点是 TreeNode {id, type, label, ref?, children?, badges?, meta?}。
        只搬「身份 + 角标」,不回正文/详情全字段(详情按 ref 懒加载)。
        """
        # —— 手稿支:复用 outline() ——
        out = self.outline()
        vols = out["volumes"]
        chapters = out["chapters"]
        # 卷 id → 该卷 TreeNode(保持 outline 的章顺序)
        vol_nodes: dict[str | None, dict] = {}

        def _wc_badge(n) -> dict:
            v = n or 0
            label = f"{v/1000:.1f}k" if v >= 1000 else str(v)
            return {"kind": "wc", "value": label}

        def _chapter_node(c: dict) -> dict:
            badges = [_wc_badge(c.get("word_count"))]
            if c.get("focalizer"):
                badges.append({"kind": "pov", "value": c["focalizer"]})
            if c.get("hook_structured"):
                badges.append({"kind": "hook", "value": "钩", "tone": "ok",
                               "title": c.get("hook_preview") or "钩子已结构化"})
            cc = c.get("craft_compliance") or {}
            if isinstance(cc, dict) and cc.get("ok") is False:
                badges.append({"kind": "compliance", "value": "合规", "tone": "danger",
                               "title": cc.get("detail") or "C-Det 未通过"})
            qc_n = c.get("qc_issues") or 0
            if qc_n:
                badges.append({"kind": "qc", "value": qc_n, "tone": "warn"})
            scenes = c.get("scenes") or []
            node = {
                "id": f"ch:{c['seq']}", "type": "chapter",
                "label": f"{c['seq']} {c.get('title') or ''}".strip(),
                "ref": c["seq"],
                "meta": {"focalizer": c.get("focalizer"), "label": c.get("label")},
                "badges": badges,
            }
            if len(scenes) > 1:
                node["children"] = [
                    {"id": f"ch:{c['seq']}#scene:{s['idx']}", "type": "scene",
                     "label": s.get("title") or f"场景 {s['idx']}",
                     "ref": {"seq": c["seq"], "idx": s["idx"]},
                     "badges": [_wc_badge(s.get("char_count"))]}
                    for s in scenes
                ]
            return node

        # 预建卷节点(按 outline 卷顺序),外加未分卷兜底组
        for v in vols:
            vol_nodes[v["id"]] = {
                "id": f"vol:{v['id']}", "type": "volume",
                "label": v.get("title") or "未命名卷", "ref": v["id"],
                "children": [], "badges": [],
            }
        for c in chapters:
            vid = c.get("volume")
            if vid not in vol_nodes:
                # 未分卷兜底组(vid=None)
                vol_nodes.setdefault(None, {
                    "id": "vol:null", "type": "volume", "label": "未分卷",
                    "ref": None, "children": [], "badges": [],
                })
            vol_nodes[vid if vid in vol_nodes else None]["children"].append(_chapter_node(c))
        # 卷角标:章数 + 卷总字数
        vol_order = [v["id"] for v in vols] + ([None] if None in vol_nodes else [])
        manuscript_children = []
        for vid in vol_order:
            node = vol_nodes.get(vid)
            if node is None:
                continue
            ch_count = len(node["children"])
            node["badges"] = [{"kind": "count", "value": ch_count}]
            manuscript_children.append(node)

        manuscript = {
            "id": "manuscript_root", "type": "manuscript_root", "label": "手稿",
            "children": manuscript_children,
        }

        # —— 素材支:各分类 → 条目 ——
        def _cat(cat_type: str, label: str, items: list[dict],
                 leaf_type: str, name_key: str = "name",
                 ref_key: str = "name", meta_fn=None, badge_fn=None) -> dict:
            children = []
            for it in items:
                leaf = {
                    "id": f"{leaf_type}:{it.get(ref_key)}", "type": leaf_type,
                    "label": str(it.get(name_key) or it.get(ref_key) or "—"),
                    "ref": it.get(ref_key),
                }
                if meta_fn:
                    leaf["meta"] = meta_fn(it)
                if badge_fn:
                    b = badge_fn(it)
                    if b:
                        leaf["badges"] = b
                children.append(leaf)
            return {
                "id": f"cat:{cat_type}", "type": "codex_category", "label": label,
                "ref": cat_type, "badges": [{"kind": "count", "value": len(children)}],
                "children": children,
            }

        chars = self.characters()
        char_items = []
        for c in chars:
            traits = c.traits if isinstance(getattr(c, "traits", None), dict) else {}
            char_items.append({
                "name": c.name, "id": c.id, "local": c.id.split(":", 1)[-1],
                "importance": traits.get("importance"),
                "secret": bool(traits.get("backstory_secret")),
                "_ready_row": {"name": c.name, **traits},
            })

        def _char_meta(c):
            return {"importance": c.get("importance"), "id": c.get("id")}

        def _ready_badges(kind, row):
            from scribe3.iceberg import codex_ready_badge
            return [codex_ready_badge(kind, row)]

        def _char_badge(c):
            badges = []
            if c.get("secret"):
                badges.append({"kind": "secret", "tone": "faint"})
            badges.extend(_ready_badges("character", c.get("_ready_row") or c))
            return badges

        # 世界真相(引擎 ref=proposition):开区间投影 + classify_bucket 滤噪
        # 见 truth_surface · PR-UX1/UX1b / KD-17；SCRIBE3_TRUTH_UI=legacy_tree 跳过滤
        import os
        from scribe3.truth_surface import (
            WORLD_TRUTH_HINT,
            WORLD_TRUTH_LABEL,
            format_fact_as_codex_title,
            row_source,
            tree_hide_must,
        )
        truth_ui = (os.environ.get("SCRIBE3_TRUTH_UI") or "entity_first").strip().lower()
        show_engine = truth_ui in ("legacy_tree", "show_engine")
        prop_items = []
        try:
            for r in self.list_open_propositions():
                eid = str(r.get("entity_id") or "")
                attr = str(r.get("attribute") or "")
                local = str(r.get("id") or "")
                src = row_source(r)
                if tree_hide_must(attr, src, show_engine=show_engine):
                    continue
                secret = bool(r.get("secret"))
                val = None if secret else r.get("value")
                prop_items.append({
                    "id": local,
                    "text": format_fact_as_codex_title(
                        eid, attr, None if val is None else str(val), secret=secret),
                    "entity_id": eid,
                    "attribute": attr,
                    "secret": secret,
                })
        except Exception:
            prop_items = []

        def _prop_badge(p):
            return [{"kind": "secret", "tone": "faint"}] if p.get("secret") else None

        prop_cat = _cat(
            "proposition", WORLD_TRUTH_LABEL, prop_items, "proposition",
            name_key="text", ref_key="id", badge_fn=_prop_badge)
        # 分类级副文案：全库账本提示（叶子 meta 可忽略）
        prop_cat["meta"] = {"hint": WORLD_TRUTH_HINT, "advanced": True}

        codex_children = [
            _cat("character", "角色", char_items, "character", ref_key="local",
                 meta_fn=_char_meta, badge_fn=_char_badge),
            _cat("faction", "势力", self.list_factions(), "faction",
                 badge_fn=lambda r: _ready_badges("faction", r)),
            _cat("item", "物件", self.list_items(), "item",
                 badge_fn=lambda r: _ready_badges("item", r)),
            _cat("term", "术语", self.list_terms(), "term",
                 badge_fn=lambda r: _ready_badges("term", r)),
            _cat("world_rule", "世界规则", self.list_world_rules(), "world_rule",
                 badge_fn=lambda r: _ready_badges("world_rule", r)),
            _cat("promise", "伏笔", self.list_promises(), "promise",
                 name_key="text", ref_key="id"),
            _cat("motif", "母题", self.list_motifs(), "motif", ref_key="id",
                 badge_fn=lambda r: _ready_badges("motif", r)),
            prop_cat,
        ]
        codex = {
            "id": "codex_root", "type": "codex_root", "label": "设定库",
            "children": codex_children,
        }

        # —— 素材库支(非正典材料,与设定库正典严格分开):kind 分类 → 素材条目 ——
        all_materials = self.list_materials()
        mat_kind_labels = [("research", "研究"), ("reference", "参考"),
                           ("snippet", "片段"), ("inspiration", "灵感"), ("note", "笔记"),
                           ("emotion_module", "情绪卡")]
        mat_children = []
        for k, label in mat_kind_labels:
            items = [m for m in all_materials if m.get("kind") == k]
            leaves = [{"id": f"material:{m['id']}", "type": "material",
                       "label": str(m.get("title") or "—"), "ref": m["id"],
                       "meta": {"kind": k}}
                      for m in items]
            mat_children.append({
                "id": f"matcat:{k}", "type": "material_category", "label": label,
                "ref": k, "badges": [{"kind": "count", "value": len(leaves)}],
                "children": leaves,
            })
        materials = {
            "id": "material_root", "type": "material_root", "label": "素材库",
            "children": mat_children,
        }

        # —— 横切视图(静态清单)——
        views = [
            {"id": "view:overview", "type": "view", "label": "概览"},
            {"id": "view:atlas", "type": "view", "label": "图谱"},
            {"id": "view:timeline", "type": "view", "label": "时间线"},
            {"id": "view:insight", "type": "view", "label": "仪表盘"},
            {"id": "view:progress", "type": "view", "label": "进度"},
        ]

        return {"manuscript": manuscript, "codex": codex,
                "materials": materials, "views": views}

    def _structure_mode_on(self) -> bool:
        try:
            intent = self.get_intent() or {}
        except Exception:
            intent = {}
        return bool(intent.get("structure_mode"))

    def list_arc_units(self, volume_id: str) -> list[dict]:
        if not self._structure_mode_on():
            return []
        vid = str(volume_id or "").strip()
        if not vid:
            return []
        try:
            return self._query(
                "SELECT seq, title, goal, events, chapter_from, chapter_to, status, "
                "meta::id(volume_id) AS volume_id FROM arc_unit "
                "WHERE volume_id = type::record('volume', $vid) ORDER BY seq",
                {"vid": vid},
            ) or []
        except Exception:
            return []

    def add_arc_unit(self, volume_id: str, seq: int, title: str, **fields) -> dict:
        if not self._structure_mode_on():
            raise ValueError("structure_mode_off")
        vid = str(volume_id or "").strip()
        content = {
            "volume_id": f"volume:{vid}",
            "seq": int(seq),
            "title": str(title or "").strip() or f"单元{seq}",
            "goal": fields.get("goal") or "",
            "events": fields.get("events") or [],
            "chapter_from": fields.get("chapter_from"),
            "chapter_to": fields.get("chapter_to"),
            "status": str(fields.get("status") or "draft"),
        }
        self._execute_write(
            "CREATE arc_unit SET volume_id=type::record('volume',$vid), seq=$seq, "
            "title=$title, goal=$goal, events=$events, chapter_from=$cf, "
            "chapter_to=$ct, status=$st",
            {
                "vid": vid, "seq": content["seq"], "title": content["title"],
                "goal": content["goal"], "events": content["events"],
                "cf": content["chapter_from"], "ct": content["chapter_to"],
                "st": content["status"],
            },
        )
        return content

    def settle_arc_event(self, volume_id: str, unit_seq: int, event_id: str, done_seq: int) -> dict:
        if not self._structure_mode_on():
            raise ValueError("structure_mode_off")
        rows = self.list_arc_units(volume_id)
        unit = next((u for u in rows if int(u.get("seq") or 0) == int(unit_seq)), None)
        if not unit:
            return {"ok": False, "code": "unit_missing"}
        events = list(unit.get("events") or [])
        found = False
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if str(ev.get("id") or "") == str(event_id):
                ev["done_seq"] = int(done_seq)
                found = True
        if not found:
            return {"ok": False, "code": "event_missing"}
        self._execute_write(
            "UPDATE arc_unit SET events=$ev WHERE volume_id=type::record('volume',$vid) AND seq=$seq",
            {"vid": volume_id, "seq": int(unit_seq), "ev": events},
        )
        return {"ok": True, "events": events}

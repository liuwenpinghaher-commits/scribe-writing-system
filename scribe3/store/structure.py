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
        """知识图谱:角色/命题节点 + knows/关系 边(Atlas 视图)。
        千万字基座(Phase0-BE1):不再无上限全图返回。

        - focus 给定 → 只返回该实体的 ego 子图:focus + hop 跳邻居 + 它们之间的边。
        - focus 为 None → 返回"按 secret(密)优先、再按 valid_from 倒序"排序的 top-limit
          命题节点 + 相关角色 + 这些节点间的边,**硬上限 limit**(节点总数 ≤ limit)。
        - chapter 时间门保留(截至该章;None=全书)。

        向后兼容:无新参数调用(graph()/graph(ch))仍返回 {nodes, edges},结构不变。
        """
        ch = chapter if chapter is not None else 9999
        chars = [{"id": e.id, "type": "character", "label": e.name} for e in self.characters()]
        props = [{"id": f.id, "type": "proposition",
                  "label": ("🔒 私密" if f.secret else (f.value or "")[:18]),
                  "secret": f.secret, "_vf": f.valid_from} for f in self.facts_at(ch)]
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

        def _strip(nodes):
            for n in nodes:
                n.pop("_vf", None)
            return nodes

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
            nodes = [n for n in (chars + props) if n["id"] in keep]
            edges = [e for e in all_edges if e["src"] in keep and e["dst"] in keep]
            return {"nodes": _strip(nodes), "edges": edges}

        # —— 无 focus:top-limit 重要度子集,硬上限 ——
        # 命题排序:secret 优先(密谋更值得看),再按 valid_from 倒序(近事在前)。
        props_sorted = sorted(
            props, key=lambda p: (0 if p.get("secret") else 1, -(p.get("_vf") or 0)))
        # 角色先占额(图骨架),命题填满到 limit。
        budget = max(0, limit)
        nodes = chars[:budget]
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
        rows = self._query(
            "SELECT seq, sort_order, title, synopsis, focalizer, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, label, "
            "qc_word_count AS word_count, qc_issues, qc_causal, qc_breakdown, qc_cache_revision, "
            "scene_count, scene_meta "
            "FROM chapter:.. WHERE archived = NONE OR archived != true")
        # Python 侧排序:sort_order 为 None 时回退 seq
        rows.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else r["seq"]))
        import json
        chapters = []
        for r in rows:
            raw_meta = r.pop("scene_meta", None)
            try:
                meta = json.loads(raw_meta) if raw_meta else []
            except (ValueError, TypeError):
                meta = []
            # qc_breakdown 缓存为 JSON 串;解析失败/缺失降级为零拆分(字段恒在,向后兼容)。
            raw_bd = r.pop("qc_breakdown", None)
            try:
                breakdown = json.loads(raw_bd) if raw_bd else {}
            except (ValueError, TypeError):
                breakdown = {}
            breakdown = {k: breakdown.get(k, 0) for k in
                         ("repetition", "structural", "purple", "ai_tics", "oversaturation")}
            # scene_count 缓存优先;缺失(存量未回填)回退 scene_meta 长度,再不济 0。
            sc = r.get("scene_count")
            if sc is None:
                sc = len(meta)
            chapters.append({
                **r,
                "scene_count": sc,
                "qc_breakdown": breakdown,
                "scenes": [{"idx": i, "title": m.get("title", ""),
                            "char_count": m.get("char_count", 0)}
                           for i, m in enumerate(meta)],
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
        char_items = [{"name": c.name, "id": c.id, "local": c.id.split(":", 1)[-1],
                       "importance": c.traits.get("importance"),
                       "secret": bool(c.traits.get("backstory_secret"))}
                      for c in chars]

        def _char_meta(c):
            return {"importance": c.get("importance"), "id": c.get("id")}

        def _char_badge(c):
            return [{"kind": "secret", "tone": "faint"}] if c.get("secret") else None

        codex_children = [
            _cat("character", "角色", char_items, "character", ref_key="local",
                 meta_fn=_char_meta, badge_fn=_char_badge),
            _cat("faction", "势力", self.list_factions(), "faction"),
            _cat("item", "物件", self.list_items(), "item"),
            _cat("term", "术语", self.list_terms(), "term"),
            _cat("world_rule", "世界规则", self.list_world_rules(), "world_rule"),
            _cat("promise", "伏笔", self.list_promises(), "promise",
                 name_key="text", ref_key="id"),
            _cat("motif", "母题", self.list_motifs(), "motif", ref_key="id"),
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

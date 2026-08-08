"""SurrealStore mixin: motifs (split from store/misc.py)."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


class MotifsMixin:
    @staticmethod
    def _norm_motif_id(motif_id) -> str:
        """母题 id 归一:去空白、剥 motif: 前缀、字符串化(兼容 RecordID/混存形态)。"""
        s = str(motif_id or "").strip()
        if s.startswith("motif:"):
            s = s.split(":", 1)[1]
        return s

    def _motif_row_normalize(self, m: dict) -> dict:
        """补 echo_terms / phase / tier 默认,便于下游 heat 与 UI。"""
        from scribe3.motif_craft import (
            parse_echo_terms, format_echoes, normalize_phase, normalize_tier)
        row = dict(m or {})
        mid = self._norm_motif_id(row.get("id"))
        if mid:
            row["id"] = mid
        terms = parse_echo_terms(row.get("echoes"), row.get("echo_terms"))
        row["echo_terms"] = terms
        if terms and not (row.get("echoes") or "").strip():
            row["echoes"] = format_echoes(terms)
        row["phase"] = normalize_phase(row.get("phase"))
        row["tier"] = normalize_tier(row.get("tier"))
        if row.get("scope") is None:
            row["scope"] = None
        return row

    def add_motif(self, name: str, theme: str = "", echoes: str = "",
                  unfolding: str = "", echo_terms: list | None = None,
                  phase: str = "seed", tier: str = "book",
                  scope: str | None = None) -> None:
        from scribe3.motif_craft import (
            parse_echo_terms, format_echoes, normalize_phase, normalize_tier)
        terms = parse_echo_terms(echoes, echo_terms)
        echoes_s = (echoes or "").strip() or format_echoes(terms)
        self._execute_write(
            "CREATE motif SET name=$n, theme=$t, echoes=$e, unfolding=$u, "
            "echo_terms=$et, phase=$ph, tier=$tr, scope=$sc",
            {"n": name, "t": theme or "", "e": echoes_s, "u": unfolding or "",
             "et": terms, "ph": normalize_phase(phase),
             "tr": normalize_tier(tier), "sc": scope})

    def list_motifs(self) -> list[dict]:
        """列母题;附 hit_count 与结构化字段(供 heat/本卷/过度重复过滤)。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, name, theme, echoes, unfolding, "
            "echo_terms, phase, tier, scope FROM motif") or []
        if not rows:
            return []
        counts: dict[str, int] = {}
        try:
            for r in self._query(
                    "SELECT motif_id, count() AS c FROM motif_instance GROUP BY motif_id") or []:
                mid = self._norm_motif_id(r.get("motif_id"))
                if mid:
                    counts[mid] = int(r.get("c") or 0)
        except Exception:
            counts = {}
        out = []
        for m in rows:
            row = self._motif_row_normalize(m)
            row["hit_count"] = counts.get(self._norm_motif_id(row.get("id")), 0)
            out.append(row)
        return out

    def motif_touch_map(self) -> dict[str, list[int]]:
        """motif_id -> 触及章号列表(升序去重),供 heat 调度。"""
        rows = self._query(
            "SELECT motif_id, chapter FROM motif_instance") or []
        by: dict[str, set[int]] = {}
        for r in rows:
            mid = self._norm_motif_id(r.get("motif_id"))
            ch = r.get("chapter")
            if not mid or ch is None:
                continue
            by.setdefault(mid, set()).add(int(ch))
        return {k: sorted(v) for k, v in by.items()}

    def add_motif_instance(self, motif_id: str, chapter: int,
                           evidence: str = "", ingest_seq: int | None = None) -> bool:
        """落本章母题触及。返回是否写入。

        卫生:证据过短 skip;同章同母题已有记录则幂等更新 evidence(不叠 junk 行)。
        """
        from scribe3.motif_craft import evidence_acceptable
        mid = self._norm_motif_id(motif_id)
        if not mid:
            return False
        ev = (evidence or "").strip()
        if not evidence_acceptable(ev):
            return False
        existing = self._query(
            "SELECT meta::id(id) AS id, evidence FROM motif_instance "
            "WHERE motif_id=$m AND chapter=$c LIMIT 1",
            {"m": mid, "c": int(chapter)}) or []
        if existing:
            # 幂等:已有则必要时补长证据,不新建
            old = (existing[0].get("evidence") or "").strip()
            if len(ev) > len(old):
                self._execute_write(
                    "UPDATE type::thing('motif_instance',$i) SET evidence=$e",
                    {"i": existing[0]["id"], "e": ev})
            return False  # 未新增行
        self._execute_write(
            "CREATE motif_instance SET motif_id=$m, chapter=$c, evidence=$e, ingest_seq=$i",
            {"m": mid, "c": int(chapter), "e": ev,
             "i": ingest_seq if ingest_seq is not None else int(chapter)})
        return True

    def list_motif_instances(self, chapter: int) -> list[dict]:
        """本章触及的母题:[{motif_id, name, evidence}](name 由 motif 表 join)。"""
        rows = self._query(
            "SELECT motif_id, evidence FROM motif_instance WHERE chapter = $c",
            {"c": chapter}) or []
        names = {self._norm_motif_id(m.get("id")): (m.get("name") or "")
                 for m in self.list_motifs()}
        out = []
        for r in rows:
            mid = self._norm_motif_id(r.get("motif_id"))
            out.append({
                "motif_id": mid,
                "name": names.get(mid, ""),
                "evidence": r.get("evidence") or "",
            })
        return out

    def list_motif_timeline(self, motif_id: str) -> list[dict]:
        """单母题跨章触及史,按 chapter 升序:[{chapter, evidence, motif_id, name}]。"""
        mid = self._norm_motif_id(motif_id)
        if not mid:
            return []
        rows = self._query(
            "SELECT motif_id, chapter, evidence FROM motif_instance "
            "WHERE motif_id=$m OR motif_id=$mp ORDER BY chapter ASC",
            {"m": mid, "mp": f"motif:{mid}"}) or []
        name = ""
        got = self.get_motif(mid) if hasattr(self, "get_motif") else None
        if got:
            name = got.get("name") or ""
        else:
            for m in self.list_motifs():
                if self._norm_motif_id(m.get("id")) == mid:
                    name = m.get("name") or ""
                    break
        return [{
            "motif_id": mid,
            "name": name,
            "chapter": int(r.get("chapter") or 0),
            "evidence": r.get("evidence") or "",
        } for r in rows]

    def motif_schedule(self, next_chapter: int) -> dict:
        """相对 next_chapter 的 heat 调度(must_echo / avoid_overuse / rows)。"""
        from scribe3.motif_craft import schedule_motifs
        motifs = self.list_motifs()
        tmap = self.motif_touch_map()
        return schedule_motifs(motifs, tmap, int(next_chapter))

    def update_motif(self, motif_id: str, fields: dict) -> None:
        self._update_by("motif", self._norm_motif_id(motif_id), fields)

    def delete_motif(self, motif_id: str) -> None:
        """硬删母题并级联清 motif_instance(防孤儿触及记录导致 UI 名空/计数脏)。"""
        mid = self._norm_motif_id(motif_id)
        if not mid:
            return
        # 兼容历史可能写入的裸 id / motif:id 两种 motif_id 形态
        self._execute_write(
            "DELETE motif_instance WHERE motif_id=$m OR motif_id=$mp",
            {"m": mid, "mp": f"motif:{mid}"})
        self._delete_by("motif", mid)


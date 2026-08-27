"""SurrealStore mixin: intent."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class IntentMixin:

    # 命运轴四字段 migration 144 就建了，但读写白名单一直没接——写进去静默丢弃、
    # 也读不出来，等于死字段。168 的 book_charter 一并补上。
    _FATE_FIELDS = ("who_pays", "axis_terms", "clock_start", "clock_end")

    def get_intent(self) -> dict:
        try:
            rows = self._query(
                "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
                "total_word_goal, daily_word_goal, arc_tracking, imagery, north_star, "
                "structure_mode, structure_budget, who_pays, axis_terms, clock_start, "
                "clock_end, book_charter FROM intent:main")
        except Exception:
            rows = self._get_intent_legacy()
        r = rows[0] if rows else {}
        result = {"reader_feeling": r.get("reader_feeling", ""),
                  "emotional_arc": r.get("emotional_arc", ""),
                  "red_lines": r.get("red_lines", "")}
        for k in self._FATE_FIELDS:
            if r.get(k) is not None and str(r.get(k)).strip():
                result[k] = str(r[k]).strip()
        if r.get("book_charter"):
            result["book_charter"] = r["book_charter"]
        return self._merge_intent_tail(result, r)

    def _get_intent_legacy(self) -> list:
        """旧库缺 168/154/149/148 的字段时逐级回退，别让读挂掉。"""
        try:
            return self._query(
                "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
                "total_word_goal, daily_word_goal, arc_tracking, imagery, north_star, "
                "structure_mode, structure_budget FROM intent:main")
        except Exception:
            pass
        try:
            return self._query(
                "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
                "total_word_goal, daily_word_goal, arc_tracking, imagery, north_star FROM intent:main")
        except Exception:
            pass
        try:
            return self._query(
                "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
                "total_word_goal, daily_word_goal, arc_tracking, imagery FROM intent:main")
        except Exception:
            return self._query(
                "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
                "total_word_goal, daily_word_goal, arc_tracking FROM intent:main")

    @staticmethod
    def _merge_intent_tail(result: dict, r: dict) -> dict:
        if r.get("imagery") is not None and str(r.get("imagery")).strip():
            result["imagery"] = str(r["imagery"]).strip()
        if r.get("north_star") is not None and str(r.get("north_star")).strip():
            result["north_star"] = str(r["north_star"]).strip()
        if r.get("overdue_threshold") is not None:
            result["overdue_threshold"] = r["overdue_threshold"]
        if r.get("total_word_goal") is not None:
            result["total_word_goal"] = r["total_word_goal"]
        if r.get("daily_word_goal") is not None:
            result["daily_word_goal"] = r["daily_word_goal"]
        # 弧光追踪：on|off；未设则不写键（调用方默认 on）
        if r.get("arc_tracking") is not None and str(r.get("arc_tracking")).strip():
            result["arc_tracking"] = str(r["arc_tracking"]).strip().lower()
        if r.get("structure_mode") is not None:
            result["structure_mode"] = bool(r.get("structure_mode"))
        if r.get("structure_budget") is not None and str(r.get("structure_budget")).strip():
            result["structure_budget"] = r.get("structure_budget")
        return result

    def set_intent(self, fields: dict) -> None:
        # P2-12:MERGE(非 CONTENT 整替)——只写调用方真正传入的字段,未传字段保留库中旧值。
        # 此前 CONTENT 会把未传的 reader_feeling/emotional_arc/red_lines/阈值抹掉
        # (GET 失败后局部保存会毁未传目标)。intent 为 SCHEMAFULL,首建时缺省字段由 schema DEFAULT 补齐。
        content: dict = {}
        for k in ("reader_feeling", "emotional_arc", "red_lines", "imagery", "north_star",
                  *self._FATE_FIELDS):
            if k in fields:
                content[k] = fields[k]
        if "book_charter" in fields and fields.get("book_charter") is not None:
            bc = fields["book_charter"]
            if isinstance(bc, str):
                import json
                bc = json.loads(bc) if bc.strip() else {}
            content["book_charter"] = bc
        if fields.get("overdue_threshold") is not None:
            content["overdue_threshold"] = fields["overdue_threshold"]
        if fields.get("total_word_goal") is not None:
            content["total_word_goal"] = int(fields["total_word_goal"])
        if fields.get("daily_word_goal") is not None:
            content["daily_word_goal"] = int(fields["daily_word_goal"])
        if "arc_tracking" in fields and fields.get("arc_tracking") is not None:
            at = str(fields.get("arc_tracking") or "").strip().lower()
            if at not in ("on", "off"):
                raise ValueError("arc_tracking 须为 on|off")
            content["arc_tracking"] = at
        if "structure_mode" in fields and fields.get("structure_mode") is not None:
            raw = fields.get("structure_mode")
            if isinstance(raw, str):
                content["structure_mode"] = raw.strip().lower() in ("1", "true", "yes", "on")
            else:
                content["structure_mode"] = bool(raw)
        if "structure_budget" in fields and fields.get("structure_budget") is not None:
            import json
            sb = fields.get("structure_budget")
            content["structure_budget"] = sb if isinstance(sb, str) else json.dumps(sb, ensure_ascii=False)
        if not content:
            return
        self._execute_write("UPSERT intent:main MERGE $c", {"c": content})

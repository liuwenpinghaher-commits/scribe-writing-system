"""SurrealStore mixin: intent."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class IntentMixin:

    def get_intent(self) -> dict:
        rows = self._query(
            "SELECT reader_feeling, emotional_arc, red_lines, overdue_threshold, "
            "total_word_goal, daily_word_goal, arc_tracking FROM intent:main")
        r = rows[0] if rows else {}
        result = {"reader_feeling": r.get("reader_feeling", ""),
                  "emotional_arc": r.get("emotional_arc", ""),
                  "red_lines": r.get("red_lines", "")}
        if r.get("overdue_threshold") is not None:
            result["overdue_threshold"] = r["overdue_threshold"]
        if r.get("total_word_goal") is not None:
            result["total_word_goal"] = r["total_word_goal"]
        if r.get("daily_word_goal") is not None:
            result["daily_word_goal"] = r["daily_word_goal"]
        # 弧光追踪：on|off；未设则不写键（调用方默认 on）
        if r.get("arc_tracking") is not None and str(r.get("arc_tracking")).strip():
            result["arc_tracking"] = str(r["arc_tracking"]).strip().lower()
        return result

    def set_intent(self, fields: dict) -> None:
        # P2-12:MERGE(非 CONTENT 整替)——只写调用方真正传入的字段,未传字段保留库中旧值。
        # 此前 CONTENT 会把未传的 reader_feeling/emotional_arc/red_lines/阈值抹掉
        # (GET 失败后局部保存会毁未传目标)。intent 为 SCHEMAFULL,首建时缺省字段由 schema DEFAULT 补齐。
        content: dict = {}
        for k in ("reader_feeling", "emotional_arc", "red_lines"):
            if k in fields:
                content[k] = fields[k]
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
        if not content:
            return
        self._execute_write("UPSERT intent:main MERGE $c", {"c": content})

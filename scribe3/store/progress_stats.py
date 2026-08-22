"""SurrealStore mixin: progress_stats (split from store/misc.py)."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


class ProgressStatsMixin:
    def purple_patterns(self) -> list[str]:
        """本书升华正则(喂 critique.find_purple_prose 的 extra_patterns)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "purple_regex"]

    def allow_patterns(self) -> list[str]:
        """方案B任务14:本书题材豁免正则(前置 skip 判定——减法,与 purple_patterns/
        extra_patterns 的加法标记彻底分离)。实际消费方:critique.find_purple_prose
        (经 quality_flags/quality_issues 透传)与 critique.find_emotion_telling
        (app.py /post-check 直接传入)——不是"各检测器"都吃这个白名单,新增消费方
        时请在此处补记,避免文档与接线脱节(收尾清理批 B14 审查发现)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_pattern"]

    def allow_words(self) -> list[str]:
        """方案B任务14:本书题材豁免词(喂 critique.find_ai_tics 的 allow_words 白名单)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_word"]

    def latest_draft_version(self, seq: int) -> dict | None:
        """该章最新 draft 版(prose+stats),供刷新恢复。无 draft 版返回 None。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, prose, label, summary, stats, created_at "
            "FROM chapter_version WHERE seq=$seq AND stage='draft' "
            "ORDER BY created_at DESC LIMIT 1",
            {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        r["stage"] = "draft"
        r.setdefault("summary", "")
        return r

    def total_word_count(self) -> int:
        """全书可见字数合计(qc_word_count 存稿缓存求和,不拉正文)。"""
        rows = self._query(
            "SELECT math::sum(qc_word_count) AS w FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        return int((rows[0].get("w") if rows else 0) or 0)

    def stats(self) -> dict:
        """本书章数 + 字数(读 QC 缓存,不回传全表正文)。"""
        count_rows = self._query(
            "SELECT count() AS chapter_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        word_rows = self._query(
            "SELECT math::sum(qc_word_count) AS word_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        chapter_count = (count_rows[0].get("chapter_count") if count_rows else 0) or 0
        word_count = (word_rows[0].get("word_count") if word_rows else 0) or 0
        return {"chapter_count": chapter_count, "word_count": word_count}

    def progress(self, today: str | None = None, window: str | None = None,
                 timezone: str | None = None) -> dict:
        """日字数序列 + 累计曲线 + 目标完成度 + 趋势窗口 + 最高产星期几。
        读 daily_progress + intent,纯聚合。
        window: '30' | '90' | 'all'(默认 'all')
        timezone: 用户时区，用来算「今天」（DSH-03）。
        """
        import time as _time
        from datetime import date as _date, timedelta as _td
        if not today and timezone:
            try:
                from datetime import datetime
                from zoneinfo import ZoneInfo
                today = datetime.now(ZoneInfo(str(timezone))).strftime("%Y-%m-%d")
            except Exception:
                today = None
        today = today or _time.strftime("%Y-%m-%d")
        # `date` 是 SurrealDB 保留字,ORDER BY 须用别名;字典序即日期升序
        rows = self._query(
            "SELECT date AS dp_date, words_written, words_total FROM daily_progress ORDER BY dp_date")
        intent = self.get_intent()
        total_goal = intent.get("total_word_goal")       # None → 前端回退 100000
        daily_goal = intent.get("daily_word_goal")       # None → 不显每日目标
        total_words = self.stats().get("word_count", 0)
        # 把 dp_date 别名统一为 date 键(供 _compute_streaks 纯函数和输出共用)
        all_normalized = [{"date": r["dp_date"], "words_written": r["words_written"],
                           "words_total": r["words_total"]} for r in rows]

        # streak / heatmap 始终用全量数据,不受 window 裁剪影响
        cur_streak, longest_streak = _compute_streaks(all_normalized, today, daily_goal)
        today_words = next((r["words_written"] for r in all_normalized if r["date"] == today), 0)

        # window 裁剪:仅影响 daily 序列(用于图表);heatmap / streak 用全量
        win = str(window).strip() if window else "all"
        if win in ("30", "90"):
            n_days = int(win)
            cutoff = (_date.fromisoformat(today) - _td(days=n_days - 1)).isoformat()
            windowed = [r for r in all_normalized if r["date"] >= cutoff]
        else:
            windowed = all_normalized  # 'all' 或其他值均视为全程

        # weekday_histogram:基于全量数据聚合,返回 7 个槽(周一=0…周日=6)
        # 每槽:{weekday, label, total_words, avg_words, count}
        from collections import defaultdict
        _wd_total: dict[int, int] = defaultdict(int)
        _wd_count: dict[int, int] = defaultdict(int)
        for r in all_normalized:
            try:
                d = _date.fromisoformat(r["date"])
                ww = d.weekday()  # 0=周一,6=周日
                words = r.get("words_written") or 0
                if words > 0:   # 只统计有写字的天
                    _wd_total[ww] += words
                    _wd_count[ww] += 1
            except ValueError:
                pass
        _WD_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_histogram = []
        for ww in range(7):
            tot = _wd_total.get(ww, 0)
            cnt = _wd_count.get(ww, 0)
            weekday_histogram.append({
                "weekday": ww,
                "label": _WD_LABELS[ww],
                "total_words": tot,
                "avg_words": round(tot / cnt) if cnt > 0 else 0,
                "count": cnt,
            })
        # 最高产星期几:按 avg_words 降序,取第一个有数据的
        best_wd = max(weekday_histogram, key=lambda x: x["avg_words"], default=None)
        best_weekday = best_wd["label"] if best_wd and best_wd["avg_words"] > 0 else None

        # 理想线(ideal):若设了 total_word_goal,按匀速插值
        # 起点=第一条记录日期,终点=总目标字数,每天均摊
        ideal_daily_rate = None
        if total_goal and total_goal > 0 and windowed:
            first_date = _date.fromisoformat(windowed[0]["date"])
            today_date = _date.fromisoformat(today)
            total_days_elapsed = max(1, (today_date - first_date).days + 1)
            ideal_daily_rate = round(total_goal / total_days_elapsed)   # 匀速字数/天
        # 在 daily 序列里附加 ideal_cumulative(匀速理想累计)
        daily_with_ideal = []
        for i, r in enumerate(windowed):
            row_date = _date.fromisoformat(r["date"])
            row = {"date": r["date"], "words": r["words_written"], "cumulative": r["words_total"]}
            if total_goal and windowed:
                first_d = _date.fromisoformat(windowed[0]["date"])
                days_from_start = (row_date - first_d).days + 1
                row["ideal_cumulative"] = min(total_goal, round(total_goal * days_from_start
                                              / max(1, (_date.fromisoformat(today) - first_d).days + 1)))
            daily_with_ideal.append(row)

        return {
            "today": today,
            "window": win,
            "total_words": total_words,
            "total_word_goal": total_goal,
            "daily_word_goal": daily_goal,
            "today_words": today_words,
            "daily": daily_with_ideal,
            "current_streak": cur_streak,
            "longest_streak": longest_streak,
            "heatmap": [{"date": r["date"], "words": r["words_written"]} for r in all_normalized],
            "weekday_histogram": weekday_histogram,
            "best_weekday": best_weekday,
            "ideal_daily_rate": ideal_daily_rate,
        }


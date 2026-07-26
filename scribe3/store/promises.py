"""SurrealStore mixin: promises."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


def _bare_record_id(rid) -> str:
    """Surreal RecordID / 'promise:xxx' → 裸 id 字符串。"""
    s = str(rid)
    return s.split(":")[-1] if ":" in s else s


class PromisesMixin:

    def add_promise_touch(self, promise_id: str, chapter: int,
                          evidence: str = "", ingest_seq: int | None = None) -> None:
        self._execute_write(
            "CREATE promise_touch SET promise_id=$p, chapter=$c, evidence=$e"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"p": promise_id, "c": chapter, "e": evidence or None,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})

    def list_promise_touches(self, promise_id: str) -> list[dict]:
        return self._query(
            "SELECT promise_id, chapter, evidence, ingest_seq FROM promise_touch "
            "WHERE promise_id=$p ORDER BY chapter ASC", {"p": promise_id})

    def update_promise(self, pid: str, fields: dict) -> bool:
        """更新伏笔字段;返回 True 若存在,False 若不存在。

        setup_chapter 或 tier 变更且调用方未显式给 payoff_min/payoff_max 时,
        按(新)tier 重算兑现窗口,防脏窗口落库(edit_prom 端点自动跟随)。"""
        rows = self._query("SELECT id, tier, setup_chapter FROM type::record('promise',$pid) "
                           "LIMIT 1", {"pid": pid})
        if not rows:
            return False
        fields = dict(fields)
        new_setup = fields.get("setup_chapter")
        new_tier = fields.get("tier")
        # tier 校验在窗口分支之外:非法 tier 即使显式给了窗口也不得落库
        if new_tier is not None and new_tier not in _TIER_WINDOW:
            raise ValueError(f"非法伏笔层级 tier='{new_tier}'(合法: {sorted(_TIER_WINDOW)})")
        window_given = (fields.get("payoff_min") is not None
                        or fields.get("payoff_max") is not None)
        clear_pmax = False
        if (new_setup is not None or new_tier is not None) and not window_given:
            tier = new_tier or rows[0].get("tier") or "chapter"
            if tier not in _TIER_WINDOW:
                raise ValueError(f"非法伏笔层级 tier='{tier}'(合法: {sorted(_TIER_WINDOW)})")
            setup = new_setup if new_setup is not None else rows[0].get("setup_chapter")
            if setup is not None:
                lo, hi = _TIER_WINDOW[tier]
                fields["payoff_min"] = setup + lo
                if hi is None:
                    clear_pmax = True  # _update_by 过滤 None 值,book 层需显式清 payoff_max
                else:
                    fields["payoff_max"] = setup + hi
        self._update_by("promise", pid, fields)
        if clear_pmax:
            self._execute_write(
                "UPDATE type::record('promise',$pid) SET payoff_max=NONE", {"pid": pid})
        return True

    def delete_promise(self, promise_id: str) -> bool:
        """删除伏笔;返回 True 若存在并删除,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": promise_id})
        if not rows:
            return False
        self._delete_by("promise", promise_id)
        return True

    def plant_promise(self, text: str, setup_chapter: int, kind: str = "promise",
                      tier: str = "chapter", resolution: str = "") -> dict:
        """种下伏笔。返回 {id, text, setup_chapter, tier, kind, payoff_min, payoff_max, status}。

        resolution(方案B任务21):悬念存档答案;book/arc 长期悬念强制校验在 REST/MCP 层,
        store 层只负责落库,不做 tier 相关必填校验(向后兼容)。"""
        if tier not in _TIER_WINDOW:
            raise ValueError(f"非法伏笔层级 tier='{tier}'(合法: {sorted(_TIER_WINDOW)})")
        lo, hi = _TIER_WINDOW[tier]
        pmin = setup_chapter + lo
        pmax = None if hi is None else setup_chapter + hi
        # 用 _query 拿 CREATE 返回的 record id(与 add_volume 同范式)
        created = self._query(
            "CREATE promise SET text=$t, setup_chapter=$s, payoff_chapter=NONE, status='open', "
            "kind=$k, tier=$tier, payoff_min=$pmin, payoff_max=$pmax, "
            "resolution=$resolution",
            {"t": text, "s": setup_chapter, "k": kind,
             "tier": tier, "pmin": pmin, "pmax": pmax,
             "resolution": resolution or None})
        row = created[0] if created else {}
        rid = row.get("id")
        if rid is None:
            # 极少数驱动不回 id:按 text+setup 回查最近一条
            rows = self._query(
                "SELECT meta::id(id) AS id FROM promise "
                "WHERE text=$t AND setup_chapter=$s ORDER BY setup_chapter",
                {"t": text, "s": setup_chapter}) or []
            if not rows:
                raise RuntimeError("plant_promise: CREATE 未返回 id 且回查失败")
            pid = rows[-1]["id"]
        else:
            pid = _bare_record_id(rid)
        return {
            "id": pid,
            "text": text,
            "setup_chapter": setup_chapter,
            "tier": tier,
            "kind": kind,
            "status": "open",
            "payoff_min": pmin,
            "payoff_max": pmax,
            "resolution": resolution or None,
        }

    def _normalize_promise_row(self, r: dict) -> dict:
        """list/get 共用:clues/tier/窗口兼容补全。"""
        if r.get("clues") is None:
            r["clues"] = []
        # 兼容旧行(未跑 052 迁移前创建):tier 回退 chapter,窗口按 setup 补算。
        # book 层 payoff_max 合法为 None,不补;setup_chapter 为 None 时不补。
        if r.get("tier") is None:
            r["tier"] = "chapter"
        if r.get("status") is None:
            r["status"] = "open"
        if r["tier"] == "chapter" and r.get("setup_chapter") is not None:
            lo, hi = _TIER_WINDOW["chapter"]
            if r.get("payoff_min") is None:
                r["payoff_min"] = r["setup_chapter"] + lo
            if r.get("payoff_max") is None:
                r["payoff_max"] = r["setup_chapter"] + hi
        return r

    def get_promise(self, promise_id: str) -> dict | None:
        """单条伏笔 O(1) 读(type::record),禁止全表扫描。"""
        pid = (promise_id or "").strip()
        if not pid:
            return None
        rows = self._query(
            "SELECT meta::id(id) AS id, text, setup_chapter, payoff_chapter, "
            "status, kind, clues, tier, payoff_min, payoff_max, resolution "
            "FROM type::record('promise',$pid) LIMIT 1",
            {"pid": pid}) or []
        if not rows:
            return None
        return self._normalize_promise_row(rows[0])

    def list_promises(self) -> list[dict]:
        rows = self._query("SELECT meta::id(id) AS id, text, setup_chapter, payoff_chapter, "
                           "status, kind, clues, tier, payoff_min, payoff_max, resolution "
                           "FROM promise ORDER BY setup_chapter")
        # 兼容旧库(未跑 045 迁移时 clues 字段为 None):安全回退为 []
        return [self._normalize_promise_row(r) for r in (rows or [])]

    def open_promises(self) -> list[dict]:
        """有效 open:status=open(不含 closed/abandoned)。"""
        return [p for p in self.list_promises() if p.get("status") == "open"]

    def effective_open_promises(self) -> list[dict]:
        """GATE-A / 开环账:open 且非障眼法(red_herring 仍 open 但不计有效欠账)。"""
        return [p for p in self.open_promises() if p.get("kind") != "red_herring"]

    def promises_with_lifecycle(self, max_chapter: int | None = None) -> list[dict]:
        """list_promises + 派生 refresh_count/last_refresh_at(自 promise_touch)+ window 计算态。"""
        if max_chapter is None:
            max_chapter = self.max_chapter()
        touches = self._query(
            "SELECT promise_id, chapter FROM promise_touch ORDER BY chapter ASC")
        by_pid: dict[str, list[int]] = {}
        for t in touches or []:
            # 审查 P1-3:回看旧章视角(max_chapter=seq)时丢弃未来章 touch——
            # 否则 refresh_count 吃到 seq 之后的刷新,把旧章视角误升 decision。
            if (t.get("chapter") or 0) > max_chapter:
                continue
            by_pid.setdefault(t["promise_id"], []).append(t["chapter"])
        out = []
        for p in self.list_promises():
            chs = by_pid.get(p["id"], [])
            p = dict(p, refresh_count=len(chs), last_refresh_at=(chs[-1] if chs else None))
            p["window"] = promise_window_state(p, max_chapter)
            out.append(p)
        return out

    def advance_promise(self, promise_id: str, payoff_chapter: int) -> None:
        """回收伏笔:标 closed + payoff_chapter。payoff≥setup 校验(Python 侧先行,拒绝脏数据)。"""
        rows = self._query(
            "SELECT setup_chapter, status FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        if rows[0].get("status") == "abandoned":
            raise ValueError(f"promise '{promise_id}' 已弃置,不能再兑现;请先恢复为 open")
        setup = rows[0].get("setup_chapter")
        if setup is not None and payoff_chapter < setup:
            raise ValueError(
                f"payoff_chapter({payoff_chapter}) < setup_chapter({setup}):回收不能早于埋设,拒绝写入。"
            )
        self._execute_write("UPDATE type::record('promise',$pid) SET status='closed', "
                            "payoff_chapter=$p", {"pid": promise_id, "p": payoff_chapter})

    def abandon_promise(self, promise_id: str) -> bool:
        """弃置伏笔:status=abandoned(账本结案,≠ red_herring,≠ closed 兑现)。
        返回 True 若存在,False 若不存在。"""
        rows = self._query("SELECT id, status FROM type::record('promise',$pid) LIMIT 1",
                           {"pid": promise_id})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET status='abandoned'",
            {"pid": promise_id})
        return True

    def mark_promise_herring(self, promise_id: str) -> bool:
        """将伏笔标记为 red_herring(障眼法)。返回 True 若存在,False 若不存在。
        不改 status:障眼法仍可 open 供参考,但不参与 overdue/A6 有效 open。"""
        rows = self._query("SELECT id FROM type::record('promise',$pid) LIMIT 1", {"pid": promise_id})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET kind='red_herring'", {"pid": promise_id})
        return True

    def add_promise_clue(self, promise_id: str, note: str, chapter: int) -> None:
        """追加一条草蛇灰线线索到 promise.clues[]{chapter, note}。

        统一推进账:线索同时写入 promise_touch(evidence=note),使 refresh_count /
        brief tension promise_progress 与台账同源(clue ≡ soft touch)。
        """
        rows = self._query(
            "SELECT clues FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        existing = rows[0].get("clues") or []
        new_clue = {"chapter": chapter, "note": note}
        updated = existing + [new_clue]
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET clues=$clues",
            {"pid": promise_id, "clues": updated})
        # 同源 refresh 信号
        self.add_promise_touch(promise_id, chapter, evidence=note or "")

    def remove_promise_clue(self, promise_id: str, idx: int) -> None:
        """按下标删除 promise.clues 中的一条线索(0-based)。
        不回溯删 touch(历史触及保留;避免误伤同章其它 touch)。"""
        rows = self._query(
            "SELECT clues FROM type::record('promise',$pid)", {"pid": promise_id})
        if not rows:
            raise ValueError(f"promise '{promise_id}' 不存在")
        existing = rows[0].get("clues") or []
        if idx < 0 or idx >= len(existing):
            raise IndexError(f"clue 下标 {idx} 超出范围(共 {len(existing)} 条)")
        updated = [c for i, c in enumerate(existing) if i != idx]
        self._execute_write(
            "UPDATE type::record('promise',$pid) SET clues=$clues",
            {"pid": promise_id, "clues": updated})

    def promise_timeline(self, promise_id: str) -> dict | None:
        """单条伏笔时间线投影:setup + touches/clues + close/abandon,按章排序。

        返回 None 若不存在;否则:
          {promise: {...}, events: [{kind, chapter, evidence?, source?}...]}
        kind ∈ plant | touch | clue | closed | abandoned
        """
        p = self.get_promise(promise_id)
        if not p:
            return None
        events: list[dict] = []
        setup = p.get("setup_chapter")
        if setup is not None:
            events.append({
                "kind": "plant",
                "chapter": setup,
                "evidence": p.get("text") or "",
                "source": "promise",
            })
        # clues
        for c in sorted(p.get("clues") or [], key=lambda x: x.get("chapter") or 0):
            events.append({
                "kind": "clue",
                "chapter": c.get("chapter"),
                "evidence": c.get("note") or "",
                "source": "clue",
            })
        # touches(含 clue 同步写入的 soft touch;UI 可并存展示)
        for t in self.list_promise_touches(promise_id) or []:
            events.append({
                "kind": "touch",
                "chapter": t.get("chapter"),
                "evidence": t.get("evidence") or "",
                "source": "ingest" if t.get("ingest_seq") is not None else "manual",
                "ingest_seq": t.get("ingest_seq"),
            })
        status = p.get("status")
        if status == "closed" and p.get("payoff_chapter") is not None:
            events.append({
                "kind": "closed",
                "chapter": p.get("payoff_chapter"),
                "evidence": "兑现回收",
                "source": "advance",
            })
        elif status == "abandoned":
            # 弃置无专用章字段:挂在 max(setup, last event) 或 setup
            chs = [e.get("chapter") for e in events if e.get("chapter") is not None]
            ach = max(chs) if chs else (setup or 0)
            events.append({
                "kind": "abandoned",
                "chapter": ach,
                "evidence": "弃置结案",
                "source": "abandon",
            })
        # 稳定排序:章升序,同章 plant < clue < touch < closed/abandoned
        order = {"plant": 0, "clue": 1, "touch": 2, "closed": 3, "abandoned": 4}
        events.sort(key=lambda e: (e.get("chapter") or 0, order.get(e.get("kind") or "", 9)))
        return {"promise": p, "events": events}

    def promise_ledger(self, slack: int) -> dict:
        """伏笔台账(单源)。四栏 + 每条 setup/payoff/overdue/跨度 + open/close bracket 审计。

        纯聚合,不改库。overdue 复用 _overdue_flag(与 /promises、/quality 同一份判定),
        阈值 slack 由调用方传入(intent.overdue_threshold ?? OVERDUE_SLACK,单源在端点解析)。

        返回:
          {threshold, max_chapter, open[], closed[], red_herring[], abandoned[],
           audit:{balanced, overdue_count, payoff_without_setup[], closed_without_setup[], never_paid}}
        """
        mc = self.max_chapter()
        proms = self.list_promises()
        open_col: list[dict] = []
        closed_col: list[dict] = []
        herring_col: list[dict] = []
        abandoned_col: list[dict] = []
        payoff_without_setup: list[dict] = []
        closed_without_setup: list[dict] = []

        for p in proms:
            setup = p.get("setup_chapter")
            payoff = p.get("payoff_chapter")
            # clues 按 chapter 排序(草蛇灰线中途线索)
            clues_sorted = sorted(p.get("clues") or [], key=lambda c: c.get("chapter", 0))
            row = {
                "id": p.get("id"),
                "text": p.get("text", ""),
                "kind": p.get("kind"),
                "status": p.get("status"),
                "setup_chapter": setup,
                "payoff_chapter": payoff,
                "tier": p.get("tier"),
                "payoff_min": p.get("payoff_min"),
                "payoff_max": p.get("payoff_max"),
                # abandoned/closed 永不 overdue
                "overdue": _overdue_flag(p, mc, slack),
                "clues": clues_sorted,
            }
            # audit: 闭无开(deus ex machina 的可检形态)
            if payoff is not None:
                if setup is None or setup <= 0:
                    closed_without_setup.append(
                        {"id": p.get("id"), "text": p.get("text", ""),
                         "setup_chapter": setup, "payoff_chapter": payoff})
                elif payoff < setup:
                    payoff_without_setup.append(
                        {"id": p.get("id"), "text": p.get("text", ""),
                         "setup_chapter": setup, "payoff_chapter": payoff})

            # 分类优先序:abandoned → red_herring → closed → open
            if p.get("status") == "abandoned":
                row["chapters_open"] = (mc - setup) if setup is not None else None
                abandoned_col.append(row)
            elif p.get("kind") == "red_herring":
                row["chapters_open"] = (mc - setup) if setup is not None else None
                herring_col.append(row)
            elif p.get("status") == "closed":
                row["span"] = (payoff - setup) if (payoff is not None and setup is not None) else None
                closed_col.append(row)
            else:
                # open(及未知 status 回退)
                row["chapters_open"] = (mc - setup) if setup is not None else None
                open_col.append(row)

        # open 按紧迫度(chapters_open)降序;closed 按 payoff 升序
        open_col.sort(key=lambda r: -(r.get("chapters_open") or 0))
        closed_col.sort(key=lambda r: (r.get("payoff_chapter") or 0))

        overdue_count = sum(1 for r in open_col if r["overdue"])
        never_paid = len(open_col)  # 契诃夫枪"埋了未响":open 非 red_herring/abandoned
        balanced = (overdue_count == 0
                    and not payoff_without_setup
                    and not closed_without_setup)
        return {
            "threshold": slack,
            "max_chapter": mc,
            "open": open_col,
            "closed": closed_col,
            "red_herring": herring_col,
            "abandoned": abandoned_col,
            "audit": {
                "balanced": balanced,
                "overdue_count": overdue_count,
                "payoff_without_setup": payoff_without_setup,
                "closed_without_setup": closed_without_setup,
                "never_paid": never_paid,
            },
        }

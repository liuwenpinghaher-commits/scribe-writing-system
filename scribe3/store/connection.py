"""SurrealStore mixin: connection."""
from __future__ import annotations

import os
import threading
import time

from scribe3.store.core_preamble import *  # noqa: F403

class ConnectionMixin:

    """SurrealDB 后端的 World。默认连 NS=scribe3 / DB=main(与 scribe2 的 NS=scribe 隔离)。"""

    # Surreal WS SDK 非线程安全：changefeed 后台线程与请求线程共用 store 时必须串行化。
    _ws_lock: threading.RLock

    # Surreal 3.x: bare ``<string> f`` InternalError when f is NONE.
    @staticmethod
    def _sstr(field: str, alias: str | None = None) -> str:
        a = alias or field
        return f"(IF {field} IS NONE THEN NONE ELSE <string>{field} END) AS {a}"

    _CHAT_MESSAGE_FIELDS = (
        "meta::id(id) AS id, work, chapter, stage, role, text, turn, trace, "
        "thread_id, context_session_id, context_revision, context_hash, focus, "
        "response_id, "
        "(IF ts IS NONE THEN NONE ELSE <string>ts END) AS ts")

    _EDITORIAL_THREAD_FIELDS = (
        "thread_id, work, actor_id, parent_thread_id, title, status, "
        "hermes_conversation_id, previous_response_id, summary, "
        "summarized_upto_ts, summary_error, "
        "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at, "
        "(IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS updated_at")

    _AUTOTITLE_DEFAULTS = ("主编讨论", "新会话")

    _MATERIAL_COLS = ("meta::id(id) AS id, title, body, kind, tags, source, "
                      "ref_tags, summary, origin, tokens, about_entities, pinned, archived, "
                      "recall_count, last_recalled_at, created_at, updated_at")

    _CONTEXT_SNAPSHOT_FIELDS = (
        "session_id, work, revision, previous_revision, navigation_id, thread_id, "
        "entry, directory_path, focus, detail_route, chapter, phase, focalizer, "
        "reason, context_hash, "
        "(IF captured_at IS NONE THEN NONE ELSE <string>captured_at END) AS captured_at")

    _MEMORY_TRACE_COLS = (
        "trace_id, work, thread_id, context_session_id, snapshot_revision, "
        "snapshot_hash, envelope_hash, query, channels, selected, rejected, "
        "block_tokens, latency_ms, response_id, run_id, "
        "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at")

    _MEMORY_COLS = ("meta::id(id) AS id, work, scope_type, scope_id, kind, text, summary, "
                    "condition, source_type, source_id, source_revision, status, "
                    "confidence, importance, pinned, valid_from, valid_to, known_from, "
                    "known_to, recall_count, provenance, linked_ids, "
                    "(IF observed_at IS NONE THEN NONE ELSE <string>observed_at END) AS observed_at")

    _PENDING_CLAIM_FIELDS = (
        "meta::id(id) AS id, work, thread_id, text, entity, attribute, value, "
        "source_type, source_id, status, "
        "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at")

    _MEMORY_EVENT_FIELDS = (
        "meta::id(id) AS id, event_id, work, thread_id, event_type, payload, status, "
        "attempts, error, "
        "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at, "
        "(IF processed_at IS NONE THEN NONE ELSE <string>processed_at END) AS processed_at")

    _WORKING_SUMMARY_FIELDS = (
        "work, thread_id, through_turn, goals, open_tasks, decisions, assumptions, "
        "summary, "
        "(IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS updated_at")

    def __init__(self, url: str | None = None, ns: str = "scribe3", db: str = "main",
                 user: str | None = None, password: str | None = None):
        self.url = url or os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
        self.db_name = db   # 本库名(=work);chat_message.work 等冗余字段由此自动填(台账 D-002)
        self._ns = ns
        self._user = user or os.environ.get("SCRIBE3_SURREAL_USER", "root")
        self._password = password or os.environ.get("SCRIBE3_SURREAL_PASS", "root")
        self._ws_lock = threading.RLock()
        self._connect()

    def _connect(self) -> None:
        with self._ws_lock:
            self._db = Surreal(self.url)
            self._db.signin({"username": self._user, "password": self._password})
            self._db.use(self._ns, self.db_name)

    def _reconnect(self) -> None:
        with self._ws_lock:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = Surreal(self.url)
            self._db.signin({"username": self._user, "password": self._password})
            self._db.use(self._ns, self.db_name)

    def _query_all_checked(self, surql: str, vars: dict):
        """执行 surql 并**逐条**校验全部语句结果,任一语句 ERR 即抛。

        P0(2026-07-14 实证):surrealdb-py 的 `query()` 对多语句脚本只检查/返回
        `result[0]`——后续语句报错会被**静默吞掉**。migration 是"整个文件一次 query"
        的多语句调用,于是只要第 1 条 DEFINE 成功,后面任何一条(含数据迁移 UPDATE)
        失败都不会抛异常,`apply_schema` 照样把该 migration 标记为已应用 → schema/数据
        半成功而无人知晓,且永久不再重放。083 就是这样静默失败的(数据迁移 UPDATE 因老行
        bool 字段为 NONE 而 coercion 报错,但 query() 一声不吭)。

        故此处改走 `query_raw` 并遍历全部语句状态。返回值与 SDK `query()` 保持一致
        (`result[0]['result']`),不改变任何既有调用方的语义。"""
        resp = self._db.query_raw(surql, vars)
        self._db.check_response_for_error(resp, "query")
        self._db.check_response_for_result(resp, "query")
        stmts = resp["result"]
        for stmt in stmts:
            self._db._check_query_result(stmt)   # 任一 ERR → parse_query_error 抛出
        return stmts[0]["result"] if stmts else None

    def _raw_query(self, surql: str, vars: dict | None = None):
        """S-1 连接韧性单点(2026-07-04 :8001 事故根治):连接类异常 → 重建连接
        (signin/use 是 WS 连接级状态,SDK 懒重连不会重放)→ 重试一次。
        本机 WS 不存在"已提交但响应丢失"的分区窗口(服务端死=写未提交),
        且核心写多为 UPSERT 幂等,故写路径重试一次可接受。
        语法/校验等非连接错误原样抛,绝不重试。

        多语句脚本的逐条校验见 `_query_all_checked`(不能用 SDK 裸 query——它只看第一条)。"""
        with self._ws_lock:
            try:
                return self._query_all_checked(surql, vars or {})
            except _CONN_ERRORS as e:
                logging.getLogger("scribe3.store").warning(
                    "SurrealDB 连接故障,重连后重试一次(%s): %s",
                    type(e).__name__, str(e)[:120])
                # 已持锁：内联重连避免 _reconnect 再抢锁死锁
                try:
                    self._db.close()
                except Exception:
                    pass
                self._db = Surreal(self.url)
                self._db.signin({"username": self._user, "password": self._password})
                self._db.use(self._ns, self.db_name)
                return self._query_all_checked(surql, vars or {})

    def close(self) -> None:
        try:
            self._db.close()
        except Exception as e:
            logging.getLogger("scribe3.store").warning("store.close 失败: %s", e)

    _SCHEMA_INITIALIZATION_ATTEMPTS = 5

    @staticmethod
    def _is_retryable_schema_conflict(exc: Exception) -> bool:
        message = str(exc).lower()
        return "transaction conflict" in message and "retry" in message

    def apply_schema(self, migrations_dir: str | None = None) -> None:
        """幂等初始化 schema，并处理 API/MCP 首次打开同一作品时的短暂写冲突。"""
        for attempt in range(self._SCHEMA_INITIALIZATION_ATTEMPTS):
            try:
                self._apply_schema_once(migrations_dir)
                return
            except Exception as exc:
                if (not self._is_retryable_schema_conflict(exc)
                        or attempt + 1 >= self._SCHEMA_INITIALIZATION_ATTEMPTS):
                    raise
                delay = 0.05 * (attempt + 1)
                logging.getLogger("scribe3").warning(
                    "作品 %s schema 初始化遇到可重试事务冲突，第 %s/%s 次重试",
                    self.db_name, attempt + 1, self._SCHEMA_INITIALIZATION_ATTEMPTS,
                )
                time.sleep(delay)

    def _apply_schema_once(self, migrations_dir: str | None = None) -> None:
        d = Path(migrations_dir) if migrations_dir else (Path(__file__).resolve().parent.parent / "migrations")
        self._raw_query("DEFINE TABLE IF NOT EXISTS _migration SCHEMALESS; "
                        "DEFINE FIELD IF NOT EXISTS applied_at ON _migration TYPE datetime;")
        try:
            rows = self._query("SELECT meta::id(id) AS id FROM _migration")
            applied = {f"_migration:{r['id']}" for r in (rows or []) if r and r.get("id")}
        except Exception:
            applied = set()
        # P1-7:迁移全用 IF NOT EXISTS / OVERWRITE(幂等重放本就无害,不会报错),
        # 故运行中的任何异常都是真失败(连接抖动/语法错)——绝不能标记已应用,
        # 否则该迁移被永久跳过、schema 静默漂移。失败者不写 _migration 记录、聚合后向上抛,
        # 保证下次启动可重试;成功者照常标记。
        failures: list[tuple[str, str]] = []
        for f in sorted(d.glob("*.surql")):
            key = f"_migration:{f.stem}"
            if key in applied:
                continue
            try:
                self._raw_query(f.read_text(encoding="utf-8"))
            except Exception as e:
                logging.getLogger("scribe3").warning(
                    "迁移 %s 失败,不标记已应用(下次可重试): %s", f.stem, str(e)[:120])
                failures.append((f.stem, str(e)[:120]))
                continue  # 真失败:跳过 CREATE _migration 记录
            # API 与 Hermes MCP 是独立进程，首次打开同一 work 时可能同时读到
            # 尚未应用。迁移正文已要求幂等，记录写入也必须幂等，不能由第二个
            # initializer 的唯一键冲突把整个 MCP 读取路径打断。
            # 唯一支持：SurrealDB 3.x（demo 3.2.4）。迁移标记只用 type::record。
            self._raw_query(
                "UPSERT type::record('_migration', $name) SET applied_at = time::now()",
                {"name": f.stem},
            )
        if failures:
            # SCRIBE3_SCHEMA_SOFT=1: continue after non-fatal migration parse/version skew
            # (local/CI host Surreal minor mismatch). Default remains strict for production.
            soft = (os.environ.get("SCRIBE3_SCHEMA_SOFT") or "").strip().lower() in {
                "1", "true", "yes", "on",
            }
            msg = (
                "apply_schema 迁移失败清单(未标记已应用): "
                + "; ".join(f"{n}: {e}" for n, e in failures)
            )
            if soft:
                logging.getLogger("scribe3").warning("SCRIBE3_SCHEMA_SOFT: %s", msg)
            else:
                raise RuntimeError(msg)
        # Task 6:回填存量对话史进默认主编线程(幂等且代价小——只 UPDATE thread_id IS NONE)。
        # fail-soft:失败只告警不阻断启动(线程回填非启动关键路径;下次启动可再试)。
        try:
            self.backfill_thread_ids()
        except Exception:
            logging.getLogger("scribe3").warning(
                "backfill_thread_ids 失败(不阻断启动,下次可重试)", exc_info=True)

    def _execute_write(self, surql: str, vars: dict) -> None:
        """改世界状态的唯一落库点。所有 add_* 经此(开发标准不变量1)。"""
        self._raw_query(surql, vars)

    # ── O28 / A4: concurrency_lock.LockStore 协议（与 TableInflightLock 同 rid）──
    @staticmethod
    def _inflight_rid(kind: str, target: str) -> str:
        """统一 rid：target 为 work:seq 时 → {work}_{seq}_{kind}（与 inflight_lock 一致）。"""
        k = str(kind or "run").strip() or "run"
        t = str(target or "").strip()
        if ":" in t:
            work, _, rest = t.partition(":")
            try:
                seq = int(str(rest).strip())
                return f"{work}_{seq}_{k}".replace(":", "_")
            except Exception:
                pass
        return f"{k}_{t}".replace(":", "_").replace("/", "_")[:200]

    def try_create_inflight(self, kind: str, target: str, worker: str, ttl_sec: int) -> bool:
        """跨进程锁：CREATE ONLY inflight 行；冲突/已存在 → False。"""
        rid = self._inflight_rid(kind, target)
        try:
            self._execute_write(
                "CREATE type::record('inflight', $rid) CONTENT {"
                " work: $work, seq: $seq, op: $op, worker: $worker, ttl_seconds: $ttl"
                "};",
                {
                    "rid": rid,
                    "work": str(target).split(":", 1)[0] if ":" in str(target) else str(target),
                    "seq": (
                        int(str(target).split(":", 1)[1])
                        if ":" in str(target) and str(target).split(":", 1)[1].isdigit()
                        else 0
                    ),
                    "op": str(kind or "run"),
                    "worker": str(worker or ""),
                    "ttl": int(ttl_sec or 60),
                },
            )
            return True
        except Exception as e:
            msg = str(e).lower()
            if "unique" in msg or "already" in msg or "exists" in msg or "conflict" in msg:
                return False
            logging.getLogger("scribe3.store").debug("try_create_inflight: %s", e)
            return False

    def delete_inflight(self, kind: str, target: str) -> None:
        rid = self._inflight_rid(kind, target)
        try:
            self._execute_write(
                "DELETE type::record('inflight', $rid);",
                {"rid": rid},
            )
        except Exception as e:
            logging.getLogger("scribe3.store").debug("delete_inflight: %s", e)

    @contextmanager
    def transaction(self):
        """关键多步写的事务边界。收集块内写,退出时拼为单条多语句提交。
        SurrealDB Python SDK 不支持跨 query() 调用事务,需拼成单条 surql。"""
        old = self._execute_write
        stmts: list[tuple[str, dict]] = []

        def _collect(surql: str, vars: dict) -> None:
            stmts.append((surql, vars))

        self._execute_write = _collect
        try:
            yield
            if stmts:
                self._commit_transaction(stmts, old)
        except Exception:
            try:
                old("CANCEL TRANSACTION", {})
            except Exception:
                pass
            raise
        finally:
            self._execute_write = old

    def _commit_transaction(self, stmts: list[tuple[str, dict]], old):
        """将收集的语句拼成单条多语句 surql 并提交。"""
        import re as _re
        parts = []
        all_vars: dict = {}
        for i, (s, v) in enumerate(stmts):
            s_num = _re.sub(r'\$([a-zA-Z_]\w*)', rf'$\1___{i}', s)
            for key, val in v.items():
                all_vars[f"{key}___{i}"] = val
            parts.append(s_num)
        surql = "BEGIN TRANSACTION; " + "; ".join(parts) + "; COMMIT TRANSACTION;"
        old(surql, all_vars)

    def _query(self, surql: str, vars: dict | None = None) -> list[dict]:
        res = self._raw_query(surql, vars or {})
        # surrealdb-py 2.0:SELECT 直接返回 rows 列表;兼容包一层 {"result":...} 的旧形态
        if isinstance(res, list):
            if res and isinstance(res[0], dict) and "result" in res[0] and "status" in res[0]:
                return res[-1].get("result") or []
            return res
        if isinstance(res, dict) and "result" in res:
            return res["result"] or []
        return res or []

    def _record_daily_progress(self, seq: int, today: str | None = None) -> None:
        """把本次 save_chapter 的净增字数累加进今日 daily_progress 行。
        注意:此方法本身不做 fail-soft 包裹(调用者 save_chapter 负责捕获)。
        delta = 落库后全书总字数 - 上次记账的 words_total(最近一行)。
        record id 格式 daily_progress:<YYYY-MM-DD>,字典序即日期序;
        `date` 是 SurrealDB 保留字,ORDER BY 用 id 替代。
        """
        import time as _time
        today = today or _time.strftime("%Y-%m-%d")
        new_total = self.stats().get("word_count", 0)
        # `date` 是 SurrealDB 保留字,ORDER BY 须用别名;字典序即日期降序
        rows = self._query(
            "SELECT date AS dp_date, words_total FROM daily_progress ORDER BY dp_date DESC LIMIT 1")
        # 用最近一行(任意日)的 words_total 作 prev,delta = 全书净增
        prev_total = rows[0]["words_total"] if rows else 0
        delta = max(0, new_total - prev_total)  # 缩写日记 0,不倒扣;words_total 快照仍如实更新
        # save_count / chapters_touched:疑似死(P2-15)——写入(下方)但无生产读取方
        #   (progress()/_streak 只读 words_written/words_total),仅 test_store 断言写入。
        #   保留写侧供未来 /progress UI("今日存 N 次/触 M 章");疑似死待确认。
        # Surreal: `[] + [$seq]` can InternalError ("Cannot perform addition with
        # '[]' and '[1]'"); use array::concat / array::append instead of `+`.
        self._execute_write(
            "UPSERT type::record('daily_progress', $d) SET "
            "date=$d, "
            "words_written = (IF words_written THEN words_written + $delta ELSE $delta END), "
            "words_total=$total, "
            "save_count = (IF save_count THEN save_count + 1 ELSE 1 END), "
            "chapters_touched = array::distinct("
            "  array::concat("
            "    (IF chapters_touched IS NONE THEN [] ELSE chapters_touched END),"
            "    [$seq]"
            "  )"
            "), "
            "updated_at=time::now()",
            {"d": today, "delta": delta, "total": new_total, "seq": seq})

    def _upsert_style_profile(self, seq: int, profile: dict) -> None:
        import json
        self._execute_write(
            "UPSERT type::record('style_profile',$s) SET seq=$s, profile=$p, "
            "computed_at=time::now()",
            {"s": seq, "p": json.dumps(profile, ensure_ascii=False)})

    def _update_by(self, table: str, local: str, fields: dict) -> None:
        if table not in _TABLES:
            raise ValueError(f"unknown table: {table}")
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            return
        allowed = _FIELDS_BY_TABLE.get(table, set())
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"disallowed fields for {table}: {bad}")
        sets = ", ".join(f"{k}=${k}" for k in fields)
        self._execute_write(f"UPDATE type::record('{table}',$_l) SET {sets}", {"_l": local, **fields})

    def _delete_by(self, table: str, local: str) -> None:
        self._execute_write(f"DELETE type::record('{table}',$_l)", {"_l": local})

    def _cleanup_record_refs(self, oid: str) -> None:
        table, local = _split(oid)
        rid = RecordID(table, local)
        if oid.startswith("role:"):
            self._execute_write("DELETE knows WHERE in=$rid", {"rid": rid})
            self._execute_write("DELETE involves WHERE out=$rid", {"rid": rid})
        elif oid.startswith("fact:"):
            self._execute_write("DELETE knows WHERE out=$rid", {"rid": rid})
            self._execute_write("DELETE reader_knows WHERE proposition=$rid", {"rid": rid})
            self._execute_write("DELETE causes WHERE out=$rid", {"rid": rid})

    def _compute_scorecard(self, seq: int, prose: str, focalizer: str | None,
                           precomputed_flags: dict | None = None) -> dict:
        """章级北极星 scorecard 三分栏(北极星任务3,蓝图 §3-③ 前半)。纯计算不写库。

        constraints(硬,全确定性):leaks(全知章 None=N/A,绝不写 0 假绿)/
          degeneration_blocking / qc_causal(-1 哨兵=无事件数据)/ promise_overdue。
        advisory_scores(软参考,只提示不门禁):ai_grade / qc_breakdown。
        fulfillment(正向达成):任务6 目的合同接入前占位 not_available。
        每个检测器独立 fail-soft:挂了记 degraded 如实上报(不假绿),绝不拖垮存稿。
        不合成总分(宪法条款)。
        """
        constraints: dict = {}
        advisory: dict = {}
        degraded: list[str] = []
        try:
            if focalizer:
                from scribe3.verify import find_leaks_for_chapter
                constraints["leaks"] = len(find_leaks_for_chapter(prose, self, focalizer, seq))
            else:
                constraints["leaks"] = None   # 全知章泄密不可判:N/A ≠ 0
        except Exception:
            degraded.append("leaks")
            constraints["leaks"] = None
        try:
            from scribe3.critique import find_degeneration
            degs = find_degeneration(prose)
            constraints["degeneration_blocking"] = sum(
                1 for d in degs if d.get("severity") == "blocking")
            constraints["degeneration_total"] = len(degs)
        except Exception:
            degraded.append("degeneration")
            constraints["degeneration_blocking"] = None
            constraints["degeneration_total"] = None
        try:
            from scribe3.verify import causal_complete
            constraints["qc_causal"] = (-1 if not self.events_at(seq)
                                        else len(causal_complete(self, seq)))
        except Exception:
            degraded.append("qc_causal")
            constraints["qc_causal"] = None
        try:
            rows = self.promises_with_lifecycle(max_chapter=seq)
            constraints["promise_overdue"] = sum(
                1 for p in rows if (p.get("window") or {}).get("state") == "overdue")
        except Exception:
            degraded.append("promise_overdue")
            constraints["promise_overdue"] = None
        try:
            from scribe3.critique import aggregate_ai_grade, quality_flags
            qf = precomputed_flags if precomputed_flags is not None else quality_flags(prose)
            g = aggregate_ai_grade(qf, prose)
            advisory["ai_grade"] = {"grade": g.get("grade"), "gates_hit": g.get("gates_hit")}
            from scribe3.qc_product_keys import product_qc_breakdown_from_flags
            advisory["qc_breakdown"] = product_qc_breakdown_from_flags(qf)
        except Exception:
            degraded.append("ai_grade")
            advisory["ai_grade"] = None
            advisory["qc_breakdown"] = None
        # 北极星任务6:目的合同接入后 fulfillment 出真数据(登记了 deltas 的章);
        # 未登记章保持 not_available 占位。carried 链≥2 → alert(连续未达成告警,蓝图 §3-④)。
        _ful_read_failed = False
        try:
            rows = self._query("SELECT deltas FROM type::record('chapter',$s)", {"s": seq})
            from scribe3.purpose import parse_deltas
            ds = parse_deltas(rows[0].get("deltas") if rows else None)
        except Exception:
            degraded.append("fulfillment")
            _ful_read_failed = True   # P1门审查 P2-10:读取失败≠未登记,note 不得误导
            ds = []
        if ds:
            counts = {s: sum(1 for d in ds if d.get("status") == s)
                      for s in ("planned", "achieved", "carried", "waived")}
            chain = max(((seq - d["carried_from"]) for d in ds
                         if d.get("status") == "carried" and d.get("carried_from") is not None),
                        default=1 if counts["carried"] else 0)
            fulfillment = {"status": "active", "total": len(ds), **counts,
                           "carried_chain_max": chain, "alert": chain >= 2}
        elif _ful_read_failed:
            fulfillment = {"status": "unavailable", "deltas": [],
                           "note": "目的数据读取失败(degraded),非未登记——修好后重存本章刷新"}
        else:
            fulfillment = {"status": "not_available", "deltas": [],
                           "note": "本章未登记目的合同(空 delta 章照常可写)"}
        # PDC 压力 advisory（永不进 constraints；machine≠文学 9.5）
        try:
            from scribe3.pressure_drive import load_pdc
            from scribe3.pressure_metrics import measure_pressure
            ch = None
            try:
                ch = self.get_chapter(int(seq))
            except Exception:
                ch = None
            contract = load_pdc(ch) if ch else None
            beats_text = ""
            if ch and isinstance(ch.get("beats"), list):
                beats_text = " ".join(
                    str(b.get("text") or "") for b in ch["beats"] if isinstance(b, dict)
                )
            try:
                cp = int((contract or {}).get("chapter_pressure") or 0)
            except (TypeError, ValueError):
                cp = 0
            pr = measure_pressure(
                prose or "",
                contract,
                synopsis=str((ch or {}).get("synopsis") or ""),
                beats_text=beats_text,
                chapter_pressure=cp,
            )
            advisory["pressure"] = {
                "contract_present": pr.get("contract_present"),
                "finding_count": len(pr.get("findings") or []),
                "metrics_tiers": {
                    k: (v or {}).get("tier")
                    for k, v in (pr.get("metrics") or {}).items()
                },
                "literary_claim_ban": pr.get("literary_claim_ban"),
            }
        except Exception:
            degraded.append("pressure")
            advisory["pressure"] = None
        return {"seq": seq, "constraints": constraints, "advisory_scores": advisory,
                "fulfillment": fulfillment, "degraded": degraded}

    def _upsert_scorecard(self, sc: dict) -> None:
        import json
        self._execute_write(
            "UPSERT type::record('chapter_scorecard',$seq) SET seq=$seq, constraints=$c, "
            "advisory=$a, fulfillment=$f, degraded=$d, computed_at=time::now()",
            {"seq": sc["seq"],
             "c": json.dumps(sc["constraints"], ensure_ascii=False),
             "a": json.dumps(sc["advisory_scores"], ensure_ascii=False),
             "f": json.dumps(sc["fulfillment"], ensure_ascii=False),
             "d": json.dumps(sc["degraded"], ensure_ascii=False)})

    def _safe_count(self, surql: str, vars: dict) -> int:
        # U-011(作者要 fail-loud):删"查询失败返0"。它供删除影响预览 9 项计数复用——
        # 查询炸了返0=作者看到"0引用,可安全删除"→误删有引用的角色/事实/素材。现在
        # 查询失败直接【抛】→删除流程拿到错误(500→前端红字),不是假0。名字保留兼容调用点。
        rows = self._query(surql, vars)
        return int((rows[0].get("n") if rows else 0) or 0)

    def _context_tx(self, surql: str, vars: dict) -> None:
        """执行多语句 CAS 事务并逐语句核对状态。

        为什么不走 _raw_query:surrealdb-py 的 query() 只检查【第一条】语句的
        status(2026-07-10 实测),事务里的 THROW / 唯一索引冲突全被静默吞掉——
        而 CAS 的失配/冲突信号正是靠这些错误传递,必须 query_raw 自查全部语句。
        连接类异常沿用 _raw_query 的"重连重试一次"策略:advance 场景下若首次
        已提交、响应丢失,重试的事务会先撞 stale THROW(IF 判定在 CREATE 之前)
        ——由上层"stale → 先按 navigation 读回 → 读不回才是真 stale"机制转为
        幂等读回;create 场景重试非幂等,见 create_context_session 说明。"""
        with self._ws_lock:
            try:
                resp = self._db.query_raw(surql, vars)
            except _CONN_ERRORS as e:
                logging.getLogger("scribe3.store").warning(
                    "SurrealDB 连接故障,重连后重试一次(%s): %s",
                    type(e).__name__, str(e)[:120])
                try:
                    self._db.close()
                except Exception:
                    pass
                self._db = Surreal(self.url)
                self._db.signin({"username": self._user, "password": self._password})
                self._db.use(self._ns, self.db_name)
                resp = self._db.query_raw(surql, vars)
        if resp.get("error"):
            raise RuntimeError(f"context 事务 RPC 错误: {resp['error']}")
        errs = [str(st.get("result")) for st in (resp.get("result") or [])
                if isinstance(st, dict) and st.get("status") == "ERR"]
        if errs:
            # 过滤连带失败的样板消息("was not executed due to"/"Cannot COMMIT"),
            # 留下第一现场(THROW 文本 / 索引冲突),供上层按消息分流
            real = [m for m in errs
                    if "not executed due to" not in m and "Cannot COMMIT" not in m]
            raise RuntimeError("; ".join(real or errs))

    @staticmethod
    def _classify_context_tx_error(msg: str) -> str:
        """把 CAS 事务错误文案分流为语义类别(单独成函数以便文本注入单测)。

        类别:stale(自家 THROW 的 revision 失配)/ session_missing / session_ended
        / unique_conflict(快照唯一索引)/ commit_conflict(SurrealDB 提交层
        读写冲突,乐观事务固有,语义同 CAS 失配请重试)/ unknown(原样上抛)。"""
        if "stale_revision:" in msg:
            return "stale"
        if "context_session_missing" in msg:
            return "session_missing"
        if "context_session_ended" in msg:
            return "session_ended"
        if "already contains" in msg or "context_snapshot_navigation" in msg \
                or "context_snapshot_session_revision" in msg:
            return "unique_conflict"
        if "read or write conflict" in msg or "write conflict" in msg \
                or "transaction can be retried" in msg:
            return "commit_conflict"
        return "unknown"

    def _warn_context_replay_mismatch(self, replay: dict, it: NavigationIntent) -> None:
        """M-1:同 navigation_id 视为重放,新 payload 被忽略(以先落库者为准)。
        payload 不一致说明前端错误复用了 navigation_id——留 warning 便于排查,
        但仍按幂等重放返回,不打断用户。"""
        focus_id = (replay.get("focus") or {}).get("id")
        if replay.get("detail_route") != it.detail_route or focus_id != it.focus.id:
            logging.getLogger("scribe3.store").warning(
                "advance_context: navigation_id=%s 重放 payload 与已落库快照不一致"
                "(route %s→%s / focus %s→%s),忽略新 payload 按重放返回",
                it.navigation_id, replay.get("detail_route"), it.detail_route,
                focus_id, it.focus.id)

    def _find_context_snapshot_by_navigation(
            self, session_id: str, navigation_id: str) -> dict | None:
        """按 (session_id, navigation_id) 读回快照——幂等重放的读路径,
        预查与唯一键冲突兜底都走这里。"""
        rows = self._query(
            f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
            "WHERE session_id=$sid AND navigation_id=$nav LIMIT 1",
            {"sid": session_id, "nav": navigation_id})
        return rows[0] if rows else None

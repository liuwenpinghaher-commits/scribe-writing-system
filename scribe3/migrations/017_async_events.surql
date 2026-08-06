-- scribe3 · 017_async_events.surql · 异步事件(E枢纽 §3.3 + 分析报告优化#4)
-- ASYNC: 事件在触发事务外异步执行;RETRY: 失败自动重试。
-- 红线:事件只做纯 DB 副作用,绝不写 knows 边(否则破限知单点)。
--
-- ⚠ 疑似死(P2-15,2026-07-04):下方两触发器写入的 meta:manuscript 与 promise_audit 记录
--   全仓均无读取方(app/store/mcp 皆不查)——纯 write-only 幽灵记录。因 ASYNC 非阻塞、无害,
--   且移除 DEFINE EVENT 需专门 down-migration(超出本次"仅注释"范围),保留待确认。

-- ON chapter:存稿后回写 manuscript 进度。
-- SurrealDB 2.1.x: 异步事件子句不支持(Parse error)；用同步 THEN 保持副作用。
DEFINE EVENT OVERWRITE ev_chapter_saved ON TABLE chapter
    WHEN $event = "CREATE" OR $event = "UPDATE"
    THEN {
        UPSERT meta:manuscript SET
            last_saved_seq = $after.seq,
            last_saved_at  = time::now()
    };

-- ON promise:伏笔闭合后写审计
DEFINE EVENT OVERWRITE ev_promise_closed ON TABLE promise
    WHEN $event = "UPDATE" AND $before.status = 'open' AND $after.status = 'closed'
    THEN {
        CREATE promise_audit SET
            promise   = $after.id,
            setup     = $after.setup_chapter,
            payoff    = $after.payoff_chapter,
            closed_at = time::now()
    };

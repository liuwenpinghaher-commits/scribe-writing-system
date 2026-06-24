-- scribe3 · 017_async_events.surql · 异步事件(E枢纽 §3.3 + 分析报告优化#4)
-- ASYNC: 事件在触发事务外异步执行;RETRY: 失败自动重试。
-- 红线:事件只做纯 DB 副作用,绝不写 knows 边(否则破限知单点)。

-- ON chapter:存稿后回写 manuscript 进度(ASYNC 不阻塞存稿事务)
DEFINE EVENT OVERWRITE ev_chapter_saved ON TABLE chapter
    WHEN $event = "CREATE" OR $event = "UPDATE"
    ASYNC RETRY 3
    THEN {
        UPSERT meta:manuscript SET
            last_saved_seq = $after.seq,
            last_saved_at  = time::now()
    };

-- ON promise:伏笔闭合后写审计(ASYNC RETRY 3,失败自动重试)
DEFINE EVENT OVERWRITE ev_promise_closed ON TABLE promise
    WHEN $event = "UPDATE" AND $before.status = 'open' AND $after.status = 'closed'
    ASYNC RETRY 3
    THEN {
        CREATE promise_audit SET
            promise   = $after.id,
            setup     = $after.setup_chapter,
            payoff    = $after.payoff_chapter,
            closed_at = time::now()
    };

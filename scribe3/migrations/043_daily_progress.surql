-- scribe3 · 043_daily_progress.surql · 每日码字账(进度统计/趋势的真源)
-- 一书一 DB,不含 work 字段(与 chapter/chapter_version 同例,每书独立 db 隔离)。
-- date 为自然日字符串 'YYYY-MM-DD'(本机时区,与 app.py time.strftime 口径一致)。
-- record id = daily_progress:<date>,天然唯一,UPSERT 即累加。

DEFINE TABLE IF NOT EXISTS daily_progress SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS date             ON daily_progress TYPE string;
DEFINE FIELD IF NOT EXISTS words_written    ON daily_progress TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS words_total      ON daily_progress TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS chapters_touched ON daily_progress TYPE array DEFAULT [];
DEFINE FIELD IF NOT EXISTS save_count       ON daily_progress TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS updated_at       ON daily_progress TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS daily_progress_date ON daily_progress FIELDS date UNIQUE;

-- intent 表加整稿/每日字数目标字段(per-work 单例)
-- NONE → 前端回退默认值;有值则替换硬编码 100000
DEFINE FIELD IF NOT EXISTS total_word_goal ON intent TYPE option<int>;
DEFINE FIELD IF NOT EXISTS daily_word_goal ON intent TYPE option<int>;

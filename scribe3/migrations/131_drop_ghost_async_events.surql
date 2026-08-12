-- 131: 移除 017 幽灵 DEFINE EVENT（P1-6）
-- meta:manuscript / promise_audit 全仓无 Python 读取方；写入为无效副作用。
-- 删除事件定义本身；历史行保留（可选日后手工清理）。

REMOVE EVENT IF EXISTS ev_chapter_saved ON TABLE chapter;
REMOVE EVENT IF EXISTS ev_promise_closed ON TABLE promise;

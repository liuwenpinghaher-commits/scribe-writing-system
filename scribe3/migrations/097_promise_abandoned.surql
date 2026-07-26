-- scribe3 · 097_promise_abandoned.surql · 伏笔 status 增加 abandoned(弃置)
-- 一等关闭态:不进 open 催收/A6 有效 open/overdue;ledger 独立一栏。
-- 与 red_herring(kind) 区分:障眼法是叙事手法,弃置是账本结案。

DEFINE FIELD OVERWRITE status ON promise TYPE string
  ASSERT $value IN ['open', 'closed', 'abandoned'] DEFAULT 'open';

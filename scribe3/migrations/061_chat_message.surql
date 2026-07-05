-- scribe3 · 061_chat_message.surql · 主编对话落库(北极星方案任务1,蓝图 §4-② 沉淀环第1级)
-- 对话是目的推导链与纠偏信号的原材料:POST /chat/write 每轮追加 user/assistant 两条。
-- work 冗余存库名(per-work db 隔离下由 store 自动填,台账 D-002);ts 由 DB 侧 time::now()。
DEFINE TABLE IF NOT EXISTS chat_message SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS work ON chat_message TYPE string;
DEFINE FIELD IF NOT EXISTS chapter ON chat_message TYPE int;
DEFINE FIELD IF NOT EXISTS stage ON chat_message TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS role ON chat_message TYPE string ASSERT $value IN ['user', 'assistant'];
DEFINE FIELD IF NOT EXISTS text ON chat_message TYPE string;
DEFINE FIELD IF NOT EXISTS ts ON chat_message TYPE datetime;
DEFINE INDEX IF NOT EXISTS chat_message_chapter_idx ON chat_message FIELDS chapter;

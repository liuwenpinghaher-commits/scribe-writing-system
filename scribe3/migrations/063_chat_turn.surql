-- scribe3 · 063_chat_turn.surql · chat_message 补 turn 字段(P0门对抗审查 P2-6)
-- 同章并发会话时 user/assistant 交错无法配对,复盘蒸馏(任务8)原料会被污染;
-- POST /chat/write 每轮生成 turn id,串起本轮 user+assistant 两条。option:旧行无值兼容。
DEFINE FIELD IF NOT EXISTS turn ON chat_message TYPE option<string>;

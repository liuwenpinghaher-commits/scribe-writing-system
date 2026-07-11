-- scribe3 · 073_chat_message_trace.surql · Hermes Responses 工具链与 usage 留痕

DEFINE FIELD IF NOT EXISTS trace ON chat_message TYPE object DEFAULT {};
DEFINE FIELD IF NOT EXISTS trace.* ON chat_message TYPE any;

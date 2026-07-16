-- scribe3 · 086_thread_summary.surql · P0b:线程增量摘要游标 + 失败可见字段
-- summarized_upto_ts:摘要已覆盖到的消息 ts(ISO 字符串,与 chat_message.ts 的 <string> 投影同序可比);
-- summary_error:最近一次摘要生成失败原因(前端摘要卡红字——失败不许只躺后端日志,零降级可见性)。
DEFINE FIELD IF NOT EXISTS summarized_upto_ts ON editorial_thread TYPE option<string>;
DEFINE FIELD IF NOT EXISTS summary_error ON editorial_thread TYPE option<string>;

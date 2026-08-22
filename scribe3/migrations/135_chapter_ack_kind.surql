-- narrative-mainline：reader/story ack 分 kind；record id = {work}_{seq}_{kind}
-- 旧行 local={work}_{seq} 视为 kind=reader（读端 fallback）
DEFINE FIELD IF NOT EXISTS kind ON chapter_reader_ack TYPE option<string>;

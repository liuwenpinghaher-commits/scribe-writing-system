-- scribe3 · narrative_drive：章级冲突/事件驱动合同 JSON 串（schema/inciting/opposition/…）
-- chapter SCHEMAFULL：新字段须显式 DEFINE，否则静默丢弃/报错（同 114/117）。
-- 存 option<string> JSON，绕嵌套 object 校验；读端 json.loads（镜像 beats_meta/pressure_drive）。
-- 设计：docs/plans/2026-08-10-narrative-event-engine.md rev.2.3（引导优先、少硬拦）
DEFINE FIELD IF NOT EXISTS narrative_drive ON chapter TYPE option<string>;

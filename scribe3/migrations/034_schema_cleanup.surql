-- scribe3 · 034_schema_cleanup.surql · schema 清债(只删确认无写无读、无数据、且会造成混淆的)
-- 依据《数据字段生命周期审计》逐字段核验 + 重新 grep 确认。其余死字段(harmless 占位/写侧赋空/被 tool 写)保留。
-- 命名漂移双写(event etype/event_type 等)有意不动:working code,收口高风险换低收益。

-- 1) word_stats 预聚合视图(023):全仓零引用,stats() 绕过它直查 chapter;纯遗留 DDL。
REMOVE TABLE IF EXISTS word_stats;

-- 2) character.traits / motivation(027):option<object> 孤儿列,代码零写零读、main 库零数据,
--    且与内存 Entity.traits(ontology.py:22)同名撞车——极易误导后人以为深描落库于此。
--    实际深描走 031 扁平字段(surface_goal/deep_need/...)。删除消除 footgun。
REMOVE FIELD IF EXISTS traits ON character;
REMOVE FIELD IF EXISTS motivation ON character;

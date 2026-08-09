-- scribe3 · 115_intent_arc_tracking.surql · 作品级弧光追踪开关（PR8）
-- on|off；缺省/未设 = on（应用层 is_arc_tracking_off 处理）
DEFINE FIELD IF NOT EXISTS arc_tracking ON intent TYPE option<string>;

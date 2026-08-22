-- 长篇结构 opt-in。默认关。option 无 DEFAULT，老行 NONE = 关。

DEFINE FIELD IF NOT EXISTS structure_mode ON intent TYPE option<bool>;
DEFINE FIELD IF NOT EXISTS structure_budget ON intent TYPE option<string>;

-- scribe3 · 056_injection_mode.surql · 设定条目三态注入:always/detected/never + 优先级
DEFINE FIELD IF NOT EXISTS injection_mode ON proposition TYPE option<string>;
DEFINE FIELD IF NOT EXISTS priority ON proposition TYPE option<int>;

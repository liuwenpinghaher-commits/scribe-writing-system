-- scribe3 · 052_promise_lifecycle.surql · 伏笔生命周期:层级 + 兑现窗口 + 关闭方式
DEFINE FIELD IF NOT EXISTS tier ON promise TYPE option<string>;
DEFINE FIELD IF NOT EXISTS payoff_min ON promise TYPE option<int>;
DEFINE FIELD IF NOT EXISTS payoff_max ON promise TYPE option<int>;
DEFINE FIELD IF NOT EXISTS resolution ON promise TYPE option<string>;

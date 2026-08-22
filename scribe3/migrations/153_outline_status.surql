-- 章纲状态：缺字段 = 旧书，不拦。option 无 DEFAULT。

DEFINE FIELD IF NOT EXISTS outline_status ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS outline_rev ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS confidence ON chapter TYPE option<string>;

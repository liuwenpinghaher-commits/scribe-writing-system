-- scribe3 · 098_motif_craft.surql · 母题工艺:结构化回声 / 生命周期 / 卷级绑定
-- 遗留 echoes 字符串保留;echo_terms 为可选数组,读写侧双向兼容。
-- phase: seed|echo|turn|payoff|rest
-- tier: book|volume|arc|chapter(本卷主母题用 tier=volume 或 scope 非空)

DEFINE FIELD IF NOT EXISTS echo_terms ON motif TYPE option<array> DEFAULT [];
DEFINE FIELD IF NOT EXISTS phase ON motif TYPE string DEFAULT 'seed';
DEFINE FIELD IF NOT EXISTS tier ON motif TYPE string DEFAULT 'book';
DEFINE FIELD IF NOT EXISTS scope ON motif TYPE option<string>;

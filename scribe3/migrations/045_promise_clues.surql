-- scribe3 · 045_promise_clues.surql · 草蛇灰线中途线索台账
-- 给 promise 加内嵌 clues 数组:每条 {chapter:int, note:string}。
-- 对应 Weiland 的 light foreshadowing / 草蛇灰线"中途微提醒"工艺。
-- 内嵌而非独立表:线索强属某条 promise、量小、读 promise 时一次取回。
-- 幂等:IF NOT EXISTS 保证重跑安全。

DEFINE FIELD IF NOT EXISTS clues     ON promise TYPE option<array> DEFAULT [];
DEFINE FIELD IF NOT EXISTS clues[*]  ON promise TYPE object;
DEFINE FIELD IF NOT EXISTS clues[*].chapter ON promise TYPE int;
DEFINE FIELD IF NOT EXISTS clues[*].note    ON promise TYPE string;

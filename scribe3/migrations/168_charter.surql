-- scribe3 · 168_charter.surql · 纲层契约（书级总纲 + 卷级契约）
--
-- 为什么要这个：北极星、卷纲、章纲此前每一层都是自由文本，层与层之间没有可核对的接口。
-- 模型生成下一层时没有「必须比上一层多出什么」的约束，只能在既有元素上加细节。
-- 《万界概率战争》实测：第 14 章起每章新增实体恒为 0，15 章只多出 7 个实体，
-- 「开-3」一个词占 33% 的命题——不是模型不行，是没人告诉它这一卷该长出什么。
--
-- 契约要求每卷声明三件事，三件都能机器核：
--   introduces —— 这一卷引入哪些新实体（核：卷末实际新增实体 ⊇ 声明）
--   pays       —— 收哪几条旧线（核：卷内 promise 实际 advance 过）
--   knowledge_end —— 卷末主角必须知道 / 仍不能知道什么
--                    （核：用 fn::knowledge_frame 查卷末限知帧，这条最硬）
--
-- knowledge_end 是关键：它把纲层和限知帧接上，下一卷的章级生成才有新起点，
-- 而不是从同一处再来一遍。
--
-- FLEXIBLE 必须跟在 TYPE 之后（语序见 083 的注释），否则解析器拒绝。

DEFINE FIELD IF NOT EXISTS charter ON volume TYPE option<object> FLEXIBLE;

-- 书级总纲：全书分几卷、每卷职责、书级线怎么分布。放 intent 单例，不新建表。
DEFINE FIELD IF NOT EXISTS book_charter ON intent TYPE option<object> FLEXIBLE;

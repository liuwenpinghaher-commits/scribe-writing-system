-- scribe3 · 083_faction_expand.surql · 势力表扩字段(codex_schema.py 注册表驱动,阶段1)
-- 背景:private_operation 原是塞进「遗产运作/对外操纵/加速手段/起源/关系」等一切秘密的
-- 超级垃圾桶,现按 scribe3/codex_schema.py 的权威注册表(FACTION_FIELDS)拆成 ~19 个独立
-- 新字段,便于分维度检索/限知门控/一致性校验。全文件幂等可重放。
--
-- 类型映射(与 codex_schema.CodexField.type 对齐):
--   text/textarea -> option<string>；int -> option<int>；bool -> bool DEFAULT false；
--   array<string> -> array<string> DEFAULT []；
--   object(如 structure) -> option<object> FLEXIBLE；
--   array<object>(如 key_figures)-> option<array> + OVERWRITE 其 `.*` 子字段为
--   `TYPE object FLEXIBLE`。
--
-- ⚠️ 实测 SurrealDB 3.2.0 踩过的坑(全部在临时库用「真老行」验证过,不是推理):
--   ① SCHEMAFULL 表下,裸 option<array>/option<array<object>>(不管加不加 FLEXIBLE)仍会
--      逐路径校验数组元素子字段——写 key_figures[0].generation 直报「no such field exists」。
--      真正放开任意子键的写法是显式覆写该数组的隐式子字段:
--      `DEFINE FIELD OVERWRITE <field>.* ON faction TYPE object FLEXIBLE;`
--      (`DEFINE FIELD <field> ... TYPE option<array>` 会自动生成一条限制性的隐式 `.*` 定义,
--       故必须 OVERWRITE 而非 IF NOT EXISTS,否则是空操作。)
--   ② `FLEXIBLE` 必须跟在 `TYPE` 之后;`FLEXIBLE TYPE ...` 语序被解析器拒绝。
--   ③ 【P0·老行地雷】SurrealDB 的 `DEFAULT` **只在 CREATE 时生效,不回填已存在的老行**。
--      若把新 `_secret` 直接定义成非 optional 的 `bool DEFAULT false`,则跑过 001~082、
--      从未见过本迁移的老行(如《印迹》既有势力)这些字段实为 NONE;而 SurrealDB 在写入时
--      校验【整条记录】(不只被写的字段),于是:
--        · 本迁移末尾的数据迁移 UPDATE 当场 coercion 报错(Expected `bool` but found `NONE`),
--          拷贝根本不会发生;
--        · 此后对该老行的【任何】写操作(含 store.add_faction 的 MERGE)永久 500,
--          真实势力再也编辑不了。
--      修法(下方"老行兼容"段):先把 6 个 `_secret` 一律 OVERWRITE 成 `option<bool>`(允许
--      NONE,写入不再报错)→ 用 `?? false` 把老行的 NONE 回填成 false → 再 OVERWRITE 收紧回
--      `bool DEFAULT false`。三步都幂等,重放无害。注意必须**连 035 建的
--      private_operation_secret 一起放宽**:它同样是 `bool DEFAULT false`,若 035 之前建的
--      老行该字段为 NONE,回填 UPDATE 自己就会被它绊倒。

-- ===== 拆解 private_operation 垃圾桶:三个独立 secret 字段(值字段)=====
DEFINE FIELD IF NOT EXISTS artifact_operation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS external_manipulation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS acceleration_methods ON faction TYPE option<string>;

-- ===== 第一梯队 =====
DEFINE FIELD IF NOT EXISTS origin ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS internal_factions ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE internal_factions.* ON faction TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS structure ON faction TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS key_figures ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE key_figures.* ON faction TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS artifacts ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE artifacts.* ON faction TYPE object FLEXIBLE;

-- ===== 第二梯队 =====
DEFINE FIELD IF NOT EXISTS scale ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS recruitment ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS symbols ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS motto ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS goals ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE goals.* ON faction TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS world_rule_affinity ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE world_rule_affinity.* ON faction TYPE object FLEXIBLE;

-- ===== 第三梯队 =====
-- 注:aliases 也是"非 optional + DEFAULT"的新字段,同样踩 ③ 号老行地雷(DEFAULT 不回填老行
-- → 老行为 NONE → 整条记录写入时 coercion 报错)。它的定义与回填并入下方"老行兼容"段统一处理。
DEFINE FIELD IF NOT EXISTS timeline ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE timeline.* ON faction TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS headquarters ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS communication ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS rituals ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS secret_agenda ON faction TYPE option<string>;

-- ===== deprecated 值字段(private_operation 已由 027 定义;IF NOT EXISTS 幂等跳过,
--       仅为与 codex_schema.all_storage_keys 保持文档级对照)=====
DEFINE FIELD IF NOT EXISTS private_operation ON faction TYPE option<string>;

-- ===== 老行兼容:非 optional 字段的 NONE 回填(见文件头 ③ 的 P0 说明)=====
-- 覆盖范围 = 本迁移新增的全部"非 optional + DEFAULT"字段(5 个 `_secret` + aliases)
-- + 035 已建的 private_operation_secret(它同为 `bool DEFAULT false`;若 035 之前建的老行该
--   字段为 NONE,第 2 步的回填 UPDATE 自己就会被它绊倒,故必须一并放宽)。
--
-- 第 1 步:一律放宽为 option<...>(OVERWRITE 而非 IF NOT EXISTS——既要能新建,也要能把已按
--          非 optional 建过的字段就地放宽,否则老行的 NONE 根本无法回填)。
DEFINE FIELD OVERWRITE private_operation_secret     ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE artifact_operation_secret    ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE external_manipulation_secret ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE acceleration_methods_secret  ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE origin_secret                ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE secret_agenda_secret         ON faction TYPE option<bool>;
DEFINE FIELD OVERWRITE aliases                      ON faction TYPE option<array<string>>;

-- 第 2 步:把老行的 NONE 回填成各自的默认值(`??` 只在 NONE 时取默认,已有值不动 → 幂等)。
--          顺带把 027 建的 status / known_members 也兜一遍:它们同为非 optional + DEFAULT,
--          理论上 add_faction 每次都会显式赋值,但若存在任何绕过该路径写入的老行(NONE),
--          整条记录就永久不可写——这里一并回填,代价为零。
UPDATE faction SET
    private_operation_secret     = private_operation_secret     ?? false,
    artifact_operation_secret    = artifact_operation_secret    ?? false,
    external_manipulation_secret = external_manipulation_secret ?? false,
    acceleration_methods_secret  = acceleration_methods_secret  ?? false,
    origin_secret                = origin_secret                ?? false,
    secret_agenda_secret         = secret_agenda_secret         ?? false,
    aliases                      = aliases                      ?? [],
    known_members                = known_members                ?? [],
    status                       = status                       ?? 'active';

-- 第 3 步:收紧回非 optional + DEFAULT(此时全表已无 NONE,收紧安全;新建行由 DEFAULT 兜底)。
DEFINE FIELD OVERWRITE private_operation_secret     ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE artifact_operation_secret    ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE external_manipulation_secret ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE acceleration_methods_secret  ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE origin_secret                ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE secret_agenda_secret         ON faction TYPE bool DEFAULT false;
DEFINE FIELD OVERWRITE aliases                      ON faction TYPE array<string> DEFAULT [];

-- ===== 数据迁移:老行的 private_operation 垃圾桶 → artifact_operation =====
-- 幂等:只在 artifact_operation 尚为空时拷贝(不覆盖作者后续手动分流的内容);不自动拆分到
-- external_manipulation/acceleration_methods——机器不猜作者意图,拆分留给作者/主编手动分流
-- (codex_schema.py 中 private_operation 的 desc 已注明)。
UPDATE faction SET artifact_operation = private_operation
    WHERE private_operation != NONE AND private_operation != ''
      AND (artifact_operation = NONE OR artifact_operation = '');

-- 伴生 secret 旗标同步迁移:private_operation_secret=true 时,artifact_operation_secret
-- 尚为 false 才拷贝(幂等;不会覆盖作者后续对 artifact_operation_secret 的手动改动)。
UPDATE faction SET artifact_operation_secret = true
    WHERE private_operation_secret = true AND artifact_operation_secret = false;

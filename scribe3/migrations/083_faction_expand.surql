-- scribe3 · 083_faction_expand.surql · 势力表扩字段(codex_schema.py 注册表驱动,阶段1)
-- 背景:private_operation 原是塞进「遗产运作/对外操纵/加速手段/起源/关系」等一切秘密的
-- 超级垃圾桶,现按 scribe3/codex_schema.py 的权威注册表(FACTION_FIELDS)拆成 ~19 个独立
-- 新字段,便于分维度检索/限知门控/一致性校验。所有 DEFINE 均 IF NOT EXISTS(或对必须强制
-- 覆写的 `.*` 子字段用 OVERWRITE,见下),幂等可重放;不改动 027_setting_completeness.surql /
-- 035_entity_secret.surql 已定义的 8 个老字段与 private_operation_secret 旗标。
--
-- 类型映射(与 codex_schema.CodexField.type 对齐):
--   text/textarea -> option<string>；int -> option<int>；bool -> bool DEFAULT false；
--   array<string> -> array<string> DEFAULT []；
--   object(如 structure) -> option<object> FLEXIBLE；
--   array<object>(如 key_figures/artifacts/...)-> option<array> + 显式 OVERWRITE 其
--   `<field>.*` 子字段为 `TYPE object FLEXIBLE`。
--
-- 实测 SurrealDB 3.2.0 踩过的三个坑(均已在本文件用真实语法验证通过,而非道听途说):
--   ① SCHEMAFULL 表下,裸 option<array>/option<array<object>>(不加任何 FLEXIBLE 标注)
--      仍会逐路径校验数组元素的子字段——写 key_figures[0].generation 直接报
--      「no such field exists for table」;单纯给 option<array<object>> 挂 FLEXIBLE 同样
--      不生效(FLEXIBLE 修饰的是外层容器类型本身,不会传导进数组元素的隐式 `.*` 子模式)。
--   ② `FLEXIBLE TYPE ...` 语序会被解析器拒绝,必须写成 `TYPE ... FLEXIBLE`(FLEXIBLE 须跟在
--      TYPE 子句之后)。
--   ③ 真正让"数组里任意结构的 object"可写入/回读的写法,是显式定义该数组的隐式子字段
--      `<field>.*` 为 `TYPE object FLEXIBLE`——而 `DEFINE FIELD <field> ON tb TYPE
--      option<array>` 一旦执行,SurrealDB 会自动为 `<field>.*` 生成一条限制性的隐式定义,
--      导致后续 `DEFINE FIELD IF NOT EXISTS <field>.* ...` 是空操作(隐式定义已"存在"),
--      必须用 `DEFINE FIELD OVERWRITE <field>.* ON tb TYPE object FLEXIBLE;` 强制覆写掉
--      它,才能真正放开任意子键。OVERWRITE 每次重放都以同一定义覆盖,天然幂等,不会有害。

-- ===== 拆解 private_operation 垃圾桶:三个独立 secret 字段 =====
DEFINE FIELD IF NOT EXISTS artifact_operation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS artifact_operation_secret ON faction TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS external_manipulation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS external_manipulation_secret ON faction TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS acceleration_methods ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS acceleration_methods_secret ON faction TYPE bool DEFAULT false;

-- ===== 第一梯队 =====
DEFINE FIELD IF NOT EXISTS origin ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS origin_secret ON faction TYPE bool DEFAULT false;
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
DEFINE FIELD IF NOT EXISTS aliases ON faction TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS timeline ON faction TYPE option<array>;
DEFINE FIELD OVERWRITE timeline.* ON faction TYPE object FLEXIBLE;
DEFINE FIELD IF NOT EXISTS headquarters ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS communication ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS rituals ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS secret_agenda ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS secret_agenda_secret ON faction TYPE bool DEFAULT false;

-- ===== deprecated 伴生旗标(private_operation 已由 027 定义,private_operation_secret 已由
--      035 定义;此处 IF NOT EXISTS 幂等跳过,仅为与 codex_schema.all_storage_keys 保持文档级
--      对照,不改动其既有类型/默认值)=====
DEFINE FIELD IF NOT EXISTS private_operation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS private_operation_secret ON faction TYPE bool DEFAULT false;

-- ===== 数据迁移:老行的 private_operation 垃圾桶 → artifact_operation =====
-- 幂等:只在 artifact_operation 尚为空时拷贝(不重复覆盖);不自动拆分到
-- external_manipulation/acceleration_methods——机器不猜作者意图,拆分留给作者/主编手动分流
-- (codex_schema.py 中 private_operation 的 desc 已注明)。
UPDATE faction SET artifact_operation = private_operation
    WHERE private_operation != NONE AND private_operation != ''
      AND (artifact_operation = NONE OR artifact_operation = '');

-- 伴生 secret 旗标同步迁移:private_operation_secret=true 时,artifact_operation_secret
-- 尚为 false 才拷贝(幂等;不会覆盖作者后续对 artifact_operation_secret 的手动改动)。
UPDATE faction SET artifact_operation_secret = true
    WHERE private_operation_secret = true AND artifact_operation_secret = false;

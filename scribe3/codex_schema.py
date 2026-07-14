# scribe3/codex_schema.py
"""设定字段注册表:声明式 schema,驱动 migration/store/REST/MCP/前端(仿 settings.py REGISTRY)。

背景:faction 原来只有 9 个字段,`private_operation` 成了塞进烛照遗产/天龙座关系/加速
手段三块内容的超级垃圾桶——按维度检索、限知门控、一致性校验对长文本全是盲区。本注册表
把字段定义权威源收拢到代码里(决策 4):加字段 = 这里加一行 + 一条 migration,前端零改动
(拉 `schema_for()` 自动渲染表单)。

- `in_prompt`:该字段是否注入写作/对话 prompt(默认 True;secret 字段经限知门控后才注入,
  门控逻辑不在本文件,见 codex_secret_bridge.py / context_assembler.py)。
- `secret_capable`:该字段可被作者标记限知,伴生一个 bool 旗标键,统一由
  `secret_flag_key(key)` 派生为 `f"{key}_secret"`——不手写,避免"新增 secret 字段忘了同步
  掩码哨兵"的陷阱(旧代码 POST /factions 只 pop 了 private_operation 一个字段)。
- `deprecated`:字段仍可读旧数据,但不再进 prompt、不再进新建表单;仅 faction.private_operation
  当前处于此状态(拆分为 artifact_operation/external_manipulation/acceleration_methods,
  数据已一次性迁移,拆分靠作者/主编手动分流,机器不猜)。

阶段 1 只覆盖 faction;阶段 2 再把 character/item/term/world_rule 迁入同一模板(KINDS 加键)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexField:
    key: str
    label: str
    type: str   # 'text' | 'textarea' | 'int' | 'enum' | 'bool' | 'array<string>' | 'array<object>' | 'object'
    secret_capable: bool = False
    in_prompt: bool = True
    desc: str = ""
    enum: tuple[str, ...] | None = None
    item_schema: tuple["CodexField", ...] | None = None
    deprecated: bool = False
    # U-003 三档可见性(2026-07-15,推翻"in_prompt=False 关掉 secret_agenda"的上一版):
    # chief_only=True 表示"仅主编可见"——比 secret_capable 更强一档,连势力核心层
    # 都不知道,没有任何角色该知道,故不走 knows 边判据。它仍 in_prompt=True(要进
    # 作者与主编对话的 prompt——"仅主编可见"字面意思就是主编看得见),但生成/限知
    # 续写路径(app._codex_block 等的 for_generation=True)必须把它当**永不注入**处理,
    # 与 entity_relation.truth 同级。见 app.py `_faction_prompt_block` 的三档门控。
    chief_only: bool = False


def secret_flag_key(key: str) -> str:
    """secret_capable 字段的伴生 bool 旗标键——唯一派生点,禁止在别处手写 f"{key}_secret"。"""
    return f"{key}_secret"


FACTION_FIELDS: tuple[CodexField, ...] = (
    # ── 现有(保留)──
    CodexField("name", "势力名", "text",
               desc="势力/组织的正式名称,设定库、命题桥与实体关系表都据此互相引用,是本行的主键。"),
    CodexField("status", "状态", "enum",
               enum=("active", "dissolved", "dormant", "reformed"),
               desc="势力当前的存续状态(枚举值与 migration 027 的 ASSERT 同源,不得随意改动)。"),
    CodexField("ideology", "意识形态", "textarea",
               desc="该势力对外宣称、对内信奉的理念、主张与价值取向。"),
    CodexField("leader", "领袖", "text",
               desc="势力当前公开的领袖或最高负责人姓名。"),
    CodexField("known_members", "已知成员", "array<string>",
               desc="已在设定中登记、读者/在场角色可能已经知晓的成员名单。"),
    CodexField("public_face", "公开面目", "textarea",
               desc="势力对外展示的形象、口号或公开身份,不必然与其真实运作一致。"),
    CodexField("first_mention_chapter", "首次出场章", "int",
               desc="该势力在正文中首次被提及或登场的章节号。"),

    # ── 拆解 private_operation 垃圾桶 → 三个独立 secret 字段 ──
    CodexField("artifact_operation", "遗产运作", "textarea", secret_capable=True,
               desc="势力围绕其核心信物/遗产的具体运作方式,通常不为外人知晓。"),
    CodexField("external_manipulation", "对外操纵", "textarea", secret_capable=True,
               desc="势力对外部人物、局势或其他势力施展的暗中操纵手段。"),
    CodexField("acceleration_methods", "加速手段", "textarea", secret_capable=True,
               desc="势力用以加速自身目标达成(夺权、扩张等)的具体方法。"),

    # ── 第一梯队(新增)──
    CodexField("origin", "起源", "textarea", secret_capable=True,
               desc="势力真实的成立缘起与历史渊源,可能与其对外宣称的说法不同。"),
    CodexField("internal_factions", "内部派系", "array<object>",
               item_schema=(
                   CodexField("name", "派系名", "text", desc="内部派系/分支的名称。"),
                   CodexField("claim", "主张", "text", desc="该派系的核心诉求或主张。"),
                   CodexField("representative", "代表人物", "text", desc="该派系的代表性人物。"),
                   CodexField("power_share", "权力占比", "text", desc="该派系在势力内部的权力占比或影响力描述。"),
               ),
               desc="势力内部再分裂出的子派系,及其各自主张、代表人物与权力占比。"),
    CodexField("structure", "组织结构", "object",
               item_schema=(
                   CodexField("type", "结构类型", "enum",
                              enum=("金字塔", "扁平", "蜂窝", "双头"),
                              desc="势力的组织形态类型。"),
                   CodexField("core_size", "核心圈人数", "int", desc="决策核心圈层的人数上限或实际人数。"),
                   CodexField("decision_mechanism", "决策机制", "text", desc="势力如何做出关键决策(如一言堂/投票/共识)。"),
                   CodexField("succession", "继承机制", "text", desc="领袖或核心人物更替/继承的规则。"),
               ),
               desc="势力的组织形态、核心决策层规模、决策机制与继承规则。"),
    CodexField("key_figures", "关键人物", "array<object>",
               item_schema=(
                   CodexField("name", "姓名", "text", desc="关键人物姓名。"),
                   CodexField("generation", "代际", "int", desc="该人物所属的传承代际序号。"),
                   CodexField("fragment_decay_rate", "碎片衰减速率", "text",
                              desc="该人物持有的信物/能力碎片的衰减速率描述。"),
                   CodexField("status", "状态", "enum",
                              enum=("active", "dissipated", "dead"),
                              desc="该人物当前的存续状态。"),
                   CodexField("known_abilities", "已知能力", "text", desc="该人物已在设定中登记的已知能力。"),
               ),
               desc="势力核心传承链上的关键人物列表,含代际、状态与已知能力。"),
    CodexField("artifacts", "信物", "array<object>",
               item_schema=(
                   CodexField("artifact_name", "信物名", "text", desc="信物/圣器的名称。"),
                   CodexField("artifact_type", "信物类型", "text", desc="信物的类别或性质。"),
                   CodexField("current_power_level", "当前效力等级", "text", desc="信物当前的力量/效力等级描述。"),
                   CodexField("decay_rate", "衰减速率", "text", desc="信物力量随时间/使用衰减的速率描述。"),
                   CodexField("last_transfer_chapter", "最近传承章", "int", desc="信物最近一次易主/传承发生的章节号。"),
               ),
               desc="势力持有或曾持有的核心信物清单,含效力、衰减与传承记录。"),

    # ── 第二梯队 ──
    CodexField("scale", "规模", "text", desc="势力的势力范围/规模量级(如地区级、跨国级)。"),
    CodexField("recruitment", "招募方式", "textarea", desc="势力吸纳新成员的渠道与筛选标准。"),
    CodexField("symbols", "象征符号", "text", desc="势力标志性的符号、图腾或视觉标识。"),
    CodexField("motto", "格言", "text", desc="势力对外或对内奉行的格言、口号。"),
    CodexField("goals", "阶段目标", "array<object>",
               item_schema=(
                   CodexField("phase", "阶段", "text", desc="目标所属的阶段名称或序号。"),
                   CodexField("target", "目标内容", "text", desc="该阶段要达成的具体目标。"),
                   CodexField("status", "状态", "enum",
                              enum=("planned", "ongoing", "done", "failed"),
                              desc="该阶段目标当前的完成状态。"),
               ),
               desc="势力按阶段划分的行动目标及完成状态,供追踪势力的长线布局。"),
    CodexField("world_rule_affinity", "世界规则关联", "array<object>",
               item_schema=(
                   CodexField("rule_name", "规则名", "text", desc="关联的世界规则名称。"),
                   CodexField("affinity_type", "关联类型", "text", desc="势力与该规则的关联性质(如依附/对抗/利用)。"),
                   CodexField("note", "备注", "text", desc="关于该关联的补充说明。"),
               ),
               desc="势力与世界规则体系之间的关联,标注关联类型与补充说明。"),

    # ── 第三梯队 ──
    CodexField("aliases", "别名", "array<string>", desc="势力在不同语境/阵营口中的别称或代号。"),
    CodexField("timeline", "势力大事记", "array<object>",
               item_schema=(
                   CodexField("chapter", "章节", "int", desc="事件发生的章节号。"),
                   CodexField("event", "事件", "text", desc="该章节发生的与势力相关的关键事件。"),
               ),
               desc="按章节排列的势力关键事件时间线。"),
    CodexField("headquarters", "总部/据点", "text", desc="势力的主要活动据点或总部所在地。"),
    CodexField("communication", "联络方式", "textarea", desc="势力内部成员之间的联络/传讯方式。"),
    CodexField("rituals", "仪式", "textarea", desc="势力特有的仪式、入会礼或惯例活动。"),
    # chief_only=True(2026-07-15 修订,推翻上一版 in_prompt=False 的做法):"仅主编可见"
    # 是比"限知"更强的一档——限知字段还能靠 knows 边授予某个角色,而它连势力核心层都
    # 不知道,**没有任何角色该知道**,故不走 knows 边判据。上一版用 in_prompt=False 把它
    # 整个关出 prompt_keys,结果连"仅主编"的"主编"都看不见它了——过钝:secret_agenda
    # 的定义恰恰是"仅主编可见",不是"谁都看不见"。现改为 in_prompt=True(恢复默认)+
    # chief_only=True:作者/主编对话(for_generation=False)正常注入;生成/限知续写路径
    # (for_generation=True)永不注入,与 entity_relation.truth 同级——由 app.py
    # `_faction_prompt_block` 按 chief_only_keys() 结构性拦截,不依赖 knows 边、不依赖
    # 任何字段级判定,防一条误建的边或黑名单反查捅穿。
    CodexField("secret_agenda", "隐秘议程", "textarea", secret_capable=True, chief_only=True,
               desc="连势力核心层都不知道的真相,仅主编可见(永不进写作/续写生成 prompt,"
                    "但会出现在作者与主编的对话中)。"),

    # ── deprecated:旧垃圾桶字段,保留读取兼容,不再进 prompt / 新建表单 ──
    CodexField("private_operation", "私下运作(已废弃)", "textarea", secret_capable=True,
               in_prompt=False, deprecated=True,
               desc="已拆分为 artifact_operation/external_manipulation/acceleration_methods,"
                    "内容已迁至前者,请手动分流后清空。"),
)


KINDS: dict[str, tuple[CodexField, ...]] = {
    "faction": FACTION_FIELDS,
    # 阶段 2:character / item / term / world_rule 迁入后在此加键。
}


#: 通用实体关系表(entity_relation,CX-Task 5)relation_type 的合法词表——单一权威源:
#: migration 085 的 DB 侧 ASSERT、store.add_entity_relation 的 ValueError、app.py
#: POST /entity-relations 的 422 校验都从这里取值,不在三处分别手写(同一教训见
#: FACTION_FIELDS 里 status 字段 "枚举值与 migration 027 的 ASSERT 同源" 的注释——
#: SurrealDB migration 是静态 .surql 文本,没法 import Python 常量,DB 侧 ASSERT 必然是
#: 一份手写镜像,但 Python 侧的 store/app 两处校验必须共享这同一个元组,不允许各自抄一份)。
ENTITY_RELATION_TYPES: tuple[str, ...] = (
    "臣服", "敌对", "渗透", "无视", "共生", "结盟", "利用", "未知",
)


def fields_for(kind: str) -> tuple[CodexField, ...]:
    """按实体类型取字段元组;未登记的 kind 抛 KeyError(不 fail-soft——这是配置错误)。"""
    return KINDS[kind]


def _field_to_dict(f: CodexField) -> dict:
    return {
        "key": f.key,
        "label": f.label,
        "type": f.type,
        "secret_capable": f.secret_capable,
        "in_prompt": f.in_prompt,
        "desc": f.desc,
        "enum": list(f.enum) if f.enum else None,
        "item_schema": [_field_to_dict(c) for c in f.item_schema] if f.item_schema else None,
        "deprecated": f.deprecated,
        "chief_only": f.chief_only,   # U-003:前端据此可显示"仅主编可见"徽标
    }


def schema_for(kind: str) -> list[dict]:
    """JSON 可序列化的字段元数据列表,供 `GET /codex-schema/{kind}` 下发给前端渲染表单。"""
    return [_field_to_dict(f) for f in fields_for(kind)]


def secret_capable_keys(kind: str) -> tuple[str, ...]:
    """该实体类型下所有可标记限知的字段 key(供 REST/MCP 掩码通用循环使用)。"""
    return tuple(f.key for f in fields_for(kind) if f.secret_capable)


def chief_only_keys(kind: str) -> tuple[str, ...]:
    """该实体类型下"仅主编可见"的字段 key(U-003 三档可见性)。

    这些字段 in_prompt=True(会出现在作者/主编对话的 prompt 里),但生成/限知续写
    路径必须结构性排除——不看 knows 边、不看任何字段级标志,只看 for_generation。
    供 app.py `_faction_prompt_block` 按名单拦截,供前端渲染"仅主编可见"徽标。"""
    return tuple(f.key for f in fields_for(kind) if f.chief_only)


def prompt_keys(kind: str) -> tuple[str, ...]:
    """会被注入写作/对话 prompt 的字段 key(in_prompt=True 且非 deprecated)。"""
    return tuple(f.key for f in fields_for(kind) if f.in_prompt and not f.deprecated)


def all_storage_keys(kind: str) -> tuple[str, ...]:
    """该实体类型的全部存储列 key,含每个 secret_capable 字段的伴生 `_secret` 旗标键。
    供 store 白名单过滤 / migration 字段清单生成使用。"""
    keys: list[str] = []
    for f in fields_for(kind):
        keys.append(f.key)
        if f.secret_capable:
            keys.append(secret_flag_key(f.key))
    return tuple(keys)

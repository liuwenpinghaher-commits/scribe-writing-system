# scribe3/codex_secret_bridge.py
"""设定字段 secret → 真限知命题桥(CX-Task 4)。

背景(spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §2):
codex_schema.py 的 `{key}_secret` 目前只是【界面掩码】(`app._mask_field`/`_SECRET_MASK`)——
它只影响 GET/POST 时字符串是否显示为 "🔒 私密",完全不经过既有限知体系:
`project_frame`(knowledge.py,角色知情投影)、`_secret_fact_ids`(context_assembler.py,
prompt 门控权威判定)、`_secret_guard_block`(app.py,泄露检测硬约束)、
`_secret_proposition_values`(store.py,证据链 trace 脱敏)全部只认 `proposition.secret`,
与 faction 表自己的 `{key}_secret` 毫无关系。于是"标了 secret 的字段"从未真正被这条限知链
保护/消费过——更糟的是 faction 原本根本不进 prompt(`_codex_block` 只取 name+ideology 前
18 字),所以主编写作时一个字都用不上,"私密不泄露"只是因为主编压根看不见,不是因为门控。

本模块把"字段级 secret"真正同步成一条 `proposition(secret=True)`,从而被上述整条既有
限知链自动消费——这是作者要的"origin 部分对角色可见、'不可名状之处'仅主编知道":字段
整体可见性由 `{key}_secret` 控,更细的"谁知道"由该 proposition 挂 `knows` 边表达(既有
机制,本模块不涉及)。

## 实现决策(先核实、后落笔,均见任务报告)

- **不复用 `store.add_fact`/`ontology.Fact`**:那条路径会同步调 `semantic_index`(需要
  加载本地 embedding 模型,见 `embed.py`)并触发 `_emit_cache_invalidation`。核实结论:
  本任务要求的三个消费方——`_secret_fact_ids`(本文件下方)、`project_frame`
  (`store.facts_at()`)、`_secret_guard_block`(`store.facts_at()`)——全部是直接查库,
  不经 `context_cache`,也不依赖 embedding 是否存在;跳过这两步不影响限知门控本身是否
  生效,只是桥接命题当前不可被语义召回(可接受的范围裁剪,不在本任务 8 条断言内)。
  故直接走 `store._execute_write`/`store._query`——这本身就是仓内既有惯例
  (app.py/ingest.py/pilot.py/pulse.py 等模块都直接调用 store 这两个方法,并非本文件自创)。
- **幂等键 = (entity_id, attribute, source),不是自造的确定性 record id**:任务原话
  "幂等:同 (entity_id, attribute, source='codex_bridge') 唯一"——按内容查询而非按 id
  猜测,天然避免"势力名/字段名拼接出的 record id 恰好撞车"的边角风险。
- **`source` 字段核实结论**:`proposition` 表(migration 001)原生没有 `source` 列;
  该表历史上一直以"逐条 `DEFINE FIELD IF NOT EXISTS` 追加一列"的方式扩展
  (003/012/014/026/056/071 依次加了 embedding/ingest_seq/entity_link/injection_mode/
  priority/archived)。照此惯例新增 migration 084(`option<string>`,无 DEFAULT,老行
  天然为 NONE,零迁移成本、不触发 083 号迁移踩过的"DEFAULT 不回填老行"地雷)。
  `entity_id` 惯例核实:既有命题一律 `"{table_prefix}:{local_name}"` 形式
  (如 `role:焦三`、`place:乱岗`),本模块对 faction 使用 `f"faction:{name}"`,与任务要求
  及 spec §3 的 `entity_relation.a/b` 引用格式(`"faction:衔尾蛇秘会"`)一致。
- **不生成 `leak_markers`**:spec 描述提到"leak_markers = 从内容提取的破绽词",但全仓
  没有任何"从自由文本提取破绽词"的现成工具函数可复用(唯一相关写点是
  `app.py` `/facts` POST,直接透传调用方显式提供的 `leak_markers`,并非自动提取);
  且本任务的 8 条验收断言未要求 leak_markers。自造一个提取式启发算法风险是产出噪声词
  污染 `_secret_guard_block` 的禁写词表,伤害正常写作——故本任务只做结构化字段的
  secret→proposition 同步,leak_markers 留空(schema DEFAULT `[]`),破绽词提取留待作者/
  主编在设定库里手动补(与既有 `scenario.py` 手写 leak_markers 的方式一致),或后续任务。
- **不触发 `_emit_cache_invalidation`**:该函数是 store.py 内部私有函数,目前从未被
  其它模块引用(仅 store.py 内部 3 处自用),没有跨模块调用先例;且如上所述,本任务要求
  的三个消费方都不经 context_cache,故跳过它不影响限知门控生效。
"""
from __future__ import annotations

import logging

from scribe3.codex_schema import secret_capable_keys, secret_flag_key

_log = logging.getLogger("scribe3.codex_secret_bridge")

#: 桥接命题的 source 标记,供与作者/主编手写命题区分、按 source 过滤(一致性校验等)。
SOURCE = "codex_bridge"

#: 命题 value 的字符上限(截断,非摘要——摘要需要额外一次 LLM 调用,与"落库先保住设定"
#: 的既有原则冲突;字段全文的权威源始终是 faction 表本身,命题只服务"可见性判定 + 给主编
#: 一个可读片段",截断即可满足)。见任务报告的说明。
_VALUE_MAX = 500


def _summarize(value: object) -> str:
    """把字段值规整成可入命题的短文本:非字符串转字符串,超上限截断并加省略号。"""
    text = value if isinstance(value, str) else str(value)
    text = text.strip()
    if len(text) > _VALUE_MAX:
        text = text[:_VALUE_MAX] + "…"
    return text


def _has_value(value: object) -> bool:
    """当前 faction 全部 secret_capable 字段均为 textarea(字符串)类型
    (artifact_operation/external_manipulation/acceleration_methods/origin/secret_agenda);
    此判据按此现状写。若未来新增非字符串的 secret_capable 字段(如数值/数组),需回来
    重新审视这里(尤其 `0`/`False` 是否该视为"有值"要看具体字段语义,不能一概而论)。"""
    return value not in (None, "", [], {})


def _find_bridge_local(store, entity_id: str, attribute: str) -> str | None:
    """按幂等键 (entity_id, attribute, source) 查已存在的桥接命题,返回其 record id 的
    本地部分(无则 None)。LIMIT 1 是防御性写法——本模块自身的 create/update 分支保证
    该键至多一行,不依赖这里的 LIMIT 掩盖潜在重复(测试②③用不带 LIMIT 的裸查询验证)。"""
    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute=$attr AND source=$src LIMIT 1",
        {"eid": entity_id, "attr": attribute, "src": SOURCE})
    return rows[0]["local"] if rows else None


def sync_faction_secrets(store, name: str, row: dict) -> dict:
    """把一条 faction 行里"标了 `{key}_secret=True` 且有值"的字段同步成桥接 proposition;
    否则(无值,或未标/取消标 secret)删除对应的既有桥接命题——幂等,可任意次重放。

    Args:
        store: SurrealStore 实例(需支持 `_query`/`_execute_write`,与仓内既有跨模块用法
            一致,见本文件头部说明)。
        name: 势力名(`faction.name`,用于拼 `entity_id = f"faction:{name}"`)。
        row: 该势力当前的**完整**落库行(如 `store.get_faction(name)` 的回读结果)——
            必须是完整行而非本次请求的增量 `sent` dict,否则"这次没提交但之前已标
            secret 的字段"会被误判为"无值"而被错误删除桥接命题。

    Returns:
        {"created": int, "updated": int, "deleted": int} 本次同步实际发生的桥接命题
        增/改/删计数,供调用方(app.py POST /factions)记日志用。

    异常:本函数不吞异常——DB 层错误原样上抛,由调用方决定 fail-soft 策略(app.py 落库
    后调用本函数,失败只 warning、不阻断已经成功的 faction 写入,见 app.py 调用处注释)。
    """
    entity_id = f"faction:{name}"
    counts = {"created": 0, "updated": 0, "deleted": 0}
    for key in secret_capable_keys("faction"):
        flagged = bool(row.get(secret_flag_key(key)))
        has_value = _has_value(row.get(key))
        existing_local = _find_bridge_local(store, entity_id, key)

        if flagged and has_value:
            text = _summarize(row.get(key))
            if existing_local:
                # 策略 B：镜像 UPSERT value，无演变史；保持 source=codex_bridge
                store._execute_write(
                    "UPDATE type::record('proposition', $local) SET value=$val, secret=true, source=$src",
                    {"local": existing_local, "val": text, "src": SOURCE})
                counts["updated"] += 1
                # best-effort 语义索引 + 缓存失效（与 add_fact 对齐）
                try:
                    store.semantic_index(f"fact:{existing_local}", text)
                except Exception as e:
                    logging.getLogger("scribe3.codex_secret_bridge").warning(
                        "bridge_side_effect_failed op=semantic_index entity=%s attr=%s err=%s",
                        entity_id, key, type(e).__name__,
                    )
                try:
                    from scribe3.store.core_preamble import _emit_cache_invalidation
                    _emit_cache_invalidation(
                        "proposition", getattr(store, "db_name", None), store=store)
                except Exception as e:
                    logging.getLogger("scribe3.codex_secret_bridge").warning(
                        "bridge_side_effect_failed op=cache_invalidate entity=%s attr=%s err=%s",
                        entity_id, key, type(e).__name__,
                    )
            else:
                store._execute_write(
                    "CREATE proposition SET entity_id=$eid, attribute=$attr, value=$val, "
                    "valid_from=1, secret=true, source=$src",
                    {"eid": entity_id, "attr": key, "val": text, "src": SOURCE})
                counts["created"] += 1
                try:
                    # CREATE 后查 local 可能已有 existing 路径；用 attribute 再找一次
                    loc = _find_bridge_local(store, entity_id, key) or existing_local
                    if loc:
                        store.semantic_index(f"fact:{loc}", text)
                except Exception as e:
                    logging.getLogger("scribe3.codex_secret_bridge").warning(
                        "bridge_side_effect_failed op=semantic_index entity=%s attr=%s err=%s",
                        entity_id, key, type(e).__name__,
                    )
                try:
                    from scribe3.store.core_preamble import _emit_cache_invalidation
                    _emit_cache_invalidation(
                        "proposition", getattr(store, "db_name", None), store=store)
                except Exception as e:
                    logging.getLogger("scribe3.codex_secret_bridge").warning(
                        "bridge_side_effect_failed op=cache_invalidate entity=%s attr=%s err=%s",
                        entity_id, key, type(e).__name__,
                    )
        elif existing_local:
            store._execute_write(
                "DELETE type::record('proposition', $local)", {"local": existing_local})
            counts["deleted"] += 1
    return counts


def is_faction_bridge_mirror(entity_id: str, attribute: str) -> bool:
    """此 (entity_id, attribute) 是否本模块 `sync_faction_secrets` 造的势力 secret 字段镜像?

    判据与 `sync_faction_secrets` **创建**它们时用的谓词同源(entity_id 是
    `f"faction:{名}"` 前缀形态 + attribute ∈ `secret_capable_keys('faction')`),是结构性
    的、精确的——不看渲染出来的字符串长什么样,也不依赖 `proposition.secret`/`source`
    等字段是否可靠(那些信号可能因 store 抖动/查询失败而退化,见
    test_codex_prompt_adversarial.py 的 P0 对抗用例)。

    领域归属单一真相源:本模块创建这些镜像,判据必须与创建谓词同源,故放在这里而非
    app.py/context_assembler.py 各自实现——供 app.py `_editor_system` 的 M6 全知转储过滤、
    context_assembler.py canonical 候选/store 降级两条取数路径共用,防三处判据各自
    实现、渐行渐远(2026-07-15 之前 app.py 独立内嵌过一份同款逻辑,即本次改为委托的
    由来)。本函数不 import app/context_assembler,无循环依赖。"""
    return bool(entity_id) and str(entity_id).startswith("faction:") \
        and attribute in secret_capable_keys("faction")

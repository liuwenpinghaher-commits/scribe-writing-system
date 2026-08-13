# 写路径上下文单元审计 · drama_vacuum

| 项 | 值 |
|----|----|
| 单元 | `drama_vacuum` |
| 库存 | [INVENTORY.md](./INVENTORY.md) B 注入段 · L0 / head / redline / **NEVER** |
| 审计日 | 2026-08-13 |
| 代码锚 | `scribe3/drama_beats.py` · `scribe3/api/services/write_assemble_v1.py` · `injection_registry.py` · `context_budget.py` |
| 口径 | 只读；未改代码、未跑全量测、未起本机 Surreal |

---

## 单元是什么

无 GCD（目标/阻力/转折/代价/钩子）时的 **L0 红线替代段**：不造假合同，改注入固定「戏剧真空警告」。与 `drama_contract` **互斥**（合同空才推真空）。旗 `SCRIBE3_DRAMA_VACUUM_WARN` 默认开（`settings.py` / `feature_flags.py`）。

设计分工：`DRAMA_GATE`（`expand_beats` 高压 park，代码默认关）拦在写前；真空是 **写时仍无合同** 的注意力护栏，见 `drama_beats.py:649` 注释「与 NQ DRAMA_GATE park 分工」。

现网文案（全文静态、约百字）：

```650:654:scribe3/drama_beats.py
DRAMA_VACUUM_WARN_TEXT = (
    "\n\n【戏剧真空警告·作者执行】本章节拍尚无目标/阻力/转折/代价/钩子。"
    "禁止公园巡礼与无目标巷志；落笔前先补 GCD，或明确本章仅过渡并压短游历。"
    "禁：匀速地点句；无外力阻力的散步；章末假升华。\n"
)
```

---

## 流程完善性

**真主路径已接。** `_assemble_write_instructions_v1` → `_render_final_input`：先 `_drama_block`；空则 `empty_drama` + `_push("drama_vacuum")`；随后仍 `_push("drama_contract", …)`，但 `_dr_raw` 空时 `_domain_input` / `_push` 都丢空串，join 侧也不会留空段。

```271:294:scribe3/api/services/write_assemble_v1.py
        _dr_raw = _drama_block(st, chapter, focalizer=focalizer or "")
        if not (_dr_raw or "").strip():
            _record_write_soft_fail("empty_drama")
            try:
                from scribe3.drama_beats import format_drama_vacuum_warn
                _vac = format_drama_vacuum_warn()
                if _vac:
                    _push(
                        "drama_vacuum",
                        "redline",
                        _domain_input(
                            f"chapter:{chapter}:drama-vacuum", "drama_vacuum",
                            _vac,
                        ),
                    )
            except Exception as _sf_e:
                ...
        _dr = _domain_input(
            f"chapter:{chapter}:drama-contract", "drama_contract",
            _dr_raw,
        )
        _push("drama_contract", "redline", _dr)
```

物理序 SSOT：`generation_physical_order_names` 在 `drama_contract` 后、`outline` 前挂名（`context_budget.py:786-798`）；默认 `SCRIBE3_OUTLINE_AFTER_DRAMA=1` 时 `outline` 紧随真空。注册表 `SEGMENT_REGISTRY` 同序（`injection_registry.py:52-54`）。旗关真空时该槽位空，outline 仍跟在合同后——序不断。

**断点 / 漏网：**

1. **触发过宽「有钩即有戏」。** `_drama_block` 用 `resolve_chapter_hook(ch)`（`write_assemble_context.py:308-324`），`beats_have_drama_gcd` 对 `goal|conflict|turn|cost|hook` **任一非空** 或章钩非空即 True（`drama_beats.py:682-695`）。大纲/synopsis 里一枚 `hook`、或 `beats_meta.chapter_hook` 残留，就会打出「只有钩 + MRU 三行」的合同，**真空永不进模型**。公园巡礼章往往「有钩无目标」，正是真空该拦的形状。
2. **判定 ≠ 戏剧门。** `validate_drama_beats` / `extract_drama_gaps` 的缺口不参与真空；弱字段（一字 cost）也算「有 GCD」。
3. **旁路未接。** `brief.assemble_chapter_brief` 无 GCD 只落空 `drama_contract`（`brief.py:833-857`），作者在简报看不到真空。`assemble_discussion_system` 不推本段。讨论/简报改节拍时无对称警告。
4. **旗关静默。** `format_drama_vacuum_warn()` 空串时仍计 `empty_drama`，prompt 无护栏。`DRAMA_GATE` 默认关，写前 park 与写时真空可同时不在。
5. **层表漏名。** `GENERATION_SEGMENT_LAYERS` 无 `drama_vacuum`（`context_budget.py:424-454`）。现网 `_push(..., "redline")` 且名在 `L0_NEVER_CUT`，裁剪仍免疫；缺 layer 的平行调用会落到默认 `supplemental`（再被 NEVER 名保住）。`physical_order_markers()` 也不含本段（`:619-628`），`order_indices` 看不见真空槽。

读章失败 fail-soft 成空合同 → 会推真空（`write_assemble_context.py:302-305`），方向对。

---

## 生成质量

**有效处：** 短、位置在 envelope 之前（高注意力 head），三条禁令对准公园病（匀速地点句 / 无阻力散步 / 章末假升华），与 `format_drama_block` 的 MRU 禁令同族，不造假 GCD。

**伤文处：**

- 工程词进生成面：「GCD」「作者执行」「巷志」不是角色可感知物，模型可能复述标题或把禁令当旁白。
- 全文罐头，不列本章缺哪一栏；与 `format_drama_gate_park_reason` 的缺口 JSON 不共用。
- 「或明确本章仅过渡」无产品字段承接，过渡章与忘填戏被同一锤砸。
- 计入 `DRAMA_CORE_NAMES`（`injection_registry.py:84-86`）：真空越响，`drama_core_share` 越高——**缺戏被记成戏核**，与主指标 `signal_density_for_drama` 相反。`signal_density_proxy` 反而不含本段（`context_budget.py:883-886`），两套密度口径打架。

有真合同时本段不出现，不与 `drama_contract` 双份稀释。

---

## 爆炸半径

| 面 | 行为 |
|----|------|
| 体积 | 固定 ~100 汉字；相对 48k `NOVEL_PROMPT_HARD` 可忽略 |
| 裁剪 | `L0_NEVER_CUT`（`context_budget.py:164-174`）；assemble 标 `redline`；`enforce_total_prompt_budget` 跳过 redline/L0 |
| 软激活 | `REDLINE_SEGMENT_NAMES` 含本段（`soft_activation.py:29-33`），激活键缺失也不得丢 |
| 密度分子 | `DRAMA_CORE_NAMES` 六名之一；真空当戏核 |
| 失败 | 格式化异常 `soft_fail('write_assemble_soft_2')`，不挡写 |
| 旗 | `SCRIBE3_DRAMA_VACUUM_WARN=0` 可整段消失 |
| 数据 | 只读章 beats/钩；不写库、不改稿 |

半径小、优先级极高：不会挤爆预算，但 **永不让位**，且会污染戏核份额。无秘密/限知正文，泄漏面接近零。

---

## 业务完善性

意图正确：无戏时禁止巡礼，而不是注入空合同骗过注意力。与 GATE 的「写前 park / 写时警告」分层也清楚。

产品缺口：

- 作者在 UI/简报看不到「本章真空」；只在生成 instructions 里警告模型。
- 无「本章仅过渡」声明位，过渡章无法合法豁免禁令。
- GATE 默认关 + 钩子即可熄真空 → 连载「大纲切句 + 章末钩」路径（`BEATS_SYNOPSIS_FALLBACK` 默认开）最容易 **合法无戏且无真空**。
- 讨论路径改拍不对称，作者问「这章怎么写」时主编看不到同一红线。

对「忘填 GCD 且连钩子都没有」的章，业务闭环成立。对「有钩无目标」的主病型，业务未咬合。

---

## 五维评分（1–5）

| 维 | 分 | 一句话 |
|----|----|--------|
| **P_flow** | 3 | 真主路径互斥注入 + 物理序登记完整；触发被钩子/单字段短路，brief/discuss 未接。 |

| P_flow | 3 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 3 |
| **Q_craft** | 3 | 禁巡礼短句有用；罐头 + GCD 工程词，过渡与忘填不分。 |
| **R_safety** | 4 | L0/redline/软激活免疫，体积小、无泄密；旗关或钩子熄火后护栏消失。 |
| **B_product** | 3 | 写前 GATE 默认关时本段是唯一写时网；UI/过渡声明/弱 GCD 未产品化。 |
| **Observability** | 3 | `empty_drama` 计数 + density 能见长度；戏核口径虚高；无 assemble 接线测、`order_indices` 无本槽。 |

---

## 恰好一个最优改造

**诚实真空：触发改「无 goal∧conflict」（单钩不算戏），文案改缺口短句且禁工程词，并从 `DRAMA_CORE_NAMES` 剔除。**

只改这一包，不动 GATE、不扩 brief/discuss（那些是下一厘米）。

1. **触发**（`drama_beats.beats_have_drama_gcd` 的写路径专用谓词，或真空专用 `should_inject_drama_vacuum`）：仅当本章无实质 `goal` **且** 无实质 `conflict`（`_field` 达现网 `MIN_FIELD`）时注入；`chapter_hook` / 单字 `cost` **不得**熄火。`format_drama_block` 仍可对「仅钩」出薄合同——那是合同段的事；真空负责「没有戏核」而不是「字节全空」。
2. **文案**：`format_drama_vacuum_warn(gaps)` 复用 `extract_drama_gaps` 已有 `missing_*`，输出不超过 120 字：「本章缺目标/阻力；禁无外力地点句与章末假升华。过渡章请先标明过场并压短。」删除「GCD」「作者执行」「巷志」。
3. **度量**：`DRAMA_CORE_NAMES` 去掉 `drama_vacuum`。真空是缺戏警报，不得抬升 `drama_core_share`。`budget_report` 加布尔 `drama_vacuum_injected`（可从 `domain_lengths` 派生），与 `empty_drama` 对齐。
4. **锁测（纯函数，无 Surreal）**：仅钩 → 真空仍注入；有 goal+conflict → 不注入；`density_trace` 在仅真空时 `drama_core_share` 不含该段长度。

回滚：旗关 + 恢复旧静态串即可。爆炸半径仍是同一百字段。

---

## 关键 path:line

- 注入：`scribe3/api/services/write_assemble_v1.py:271-294`
- 文案/旗：`scribe3/drama_beats.py:649-667`
- 有戏判定（钩子即可）：`scribe3/drama_beats.py:682-695`
- 章钩 SSOT：`scribe3/chapter_hooks.py:30-73`
- 合同源（空→真空）：`scribe3/api/services/write_assemble_context.py:290-328`
- 注册 / 戏核：`scribe3/injection_registry.py:52-54`、`:84-86`
- NEVER / 物理序：`scribe3/context_budget.py:164-174`、`:786-798`
- 层表漏名 / 序标记漏槽：`scribe3/context_budget.py:424-454`、`:619-628`
- soft-fail 计数：`scribe3/api/services/write_assemble.py:22-40`
- 单测仅锁字符串与旗，不锁 assemble：`scribe3/tests/test_novel_first_injection.py:400-411`

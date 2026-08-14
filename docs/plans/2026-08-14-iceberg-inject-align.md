# 冰山对齐：库里写厚的，提示词必须用上

> **已并入** [`2026-08-14-iceberg-complete.md`](./2026-08-14-iceberg-complete.md)。本文只作考古；冲突以完整方案为准。

| 项 | 值 |
|----|----|
| **日期** | 2026-08-14 |
| **产品** | 铜炉 / tonglu · `scribe3/` |
| **状态** | Draft（方案；待落地） |
| **不改** | 宣称公式、`GATE_SAVE_MODE`、GATE-B 80 字「有没有字」口径、final **限知尖**原则 |
| **验证** | 只冒烟已部署 demo；禁止 Grok 机 `npm ci` / 本机 Surreal |

---

## 0. 一句话

**写厚是给「下一阶段生成」用的；尖端裁切只属于「读者正文」。**  
现网把 final 的裁法套在 thicken / 排演上，再叠一层 `_ctx_bits[:200]`，等于刚过 persist 闸的材料当场扔掉。

---

## 1. 对账（现网）

### 1.1 库地板（`iceberg.py`）

| 字段 | 地板 | 落哪 |
|------|------|------|
| synopsis | 500 | `chapter.synopsis` |
| beat each / sum | 500 / 2000 | `chapter.beats[].text` |
| deductions | 5000 | `chapter.deductions[].prose` |
| draft | 10000 | `chapter.draft` |
| prose 水面 | 5000 | `chapter.prose`（steer，不进宣称） |

### 1.2 提示词实际裁切

| 消费点 | 代码 | 现网帽 | 刚过地板时用上多少 | 判定 |
|--------|------|--------|-------------------|------|
| 独立生成用户消息 | `stage_generate._ctx_bits` | 大纲 1500；**每拍 200**；真相 1200 | 拍 **200/500=40%** | **白写** |
| assemble 大纲栏 | `_outline_block` `_OUTLINE_INJECT_BUDGET` | 800 | 500 全进 | 刚过闸够用 |
| assemble 节拍 | `_outline_block` `beat_cap=700` | 每拍 700，**空格拼接** | 500 全进，但挤成一行 | 结构损 |
| assemble 大纲 `mode=plan` | 同函数尾段 | **密≥250 / 疏≈40 / 慢镜头 400–600** | 与 500 场面纸对打 | **方法论打架** |
| 焦点演绎 | `FOCAL_DEDUCTION_PROSE_CAP=1800` | 1800 | 若单人写了 2500，砍 700 | 只该用于 **final** |
| 非焦点演绎 | `_nonfocal_boundary_line` | 可见 80 + 已做 60 | 一篇 ≥800 剩一行 | 只该用于 **final** |
| 演绎整包 | `_apply_deduction_pack_cap` + `DEFAULT_CODEX_INJECT_CAP=4500` | 先扔非焦点 → 砍真相 → 焦点对半 | 5000 可能砍到 4500 以下 | draft/final 同帽 |
| 排演尖 | `draft_tip(cap=2400)` | **头 2400 字** | 10000 的前 24%，后 3 拍常没了 | **白写后半** |
| 排演段注册 | `GENERATION_SEGMENT_LAYERS` / 物理序 | **`draft_tip` 未登记** | 当无名 supplemental，L2 可整段丢 | **可能 0%** |
| L2 半裁 outline | `_half_cut_segment` **保拍砍纲** | 超窗先丢 500 字大纲 | 刚写厚的大纲优先被砍 | 与「先砍 polish」口头纪律不符 |
| L2 保护集 | `GEN_SEGMENT_PROTECTED` | outline / brief_must / voice_anchor | 无 draft_tip、无「整段节拍」 | 排演尖无保护 |
| 软长度 | `DEFAULT_SOFT_LEN_FLOOR=2400` | 已有 2400 字可 skip 加长 | 与水面 5000 对不齐 | 口径混 |
| 戏剧 steer | `format_default_drama_steer` | 「目标仍约 4800–5500」 | 与 5000 接近但第三套数字 | 噪声 |
| 独立生成 output | `STAGE_MAX_TOKENS` | 4096/8192/16384 | 输出紧，不是输入裁切 | 次要 |
| GATE-B | 80 / 3 条 | 「有没有字」 | **不是注入帽** | 勿并进本表 |

`_deduction_context_segments` **只在** `phase∈{draft,final}` 注入。outline/beats/deduce 生成吃不到库里的 5000——对。  
问题是：**draft 排演也走 1800+4500 尖端裁**，而这正是 5000 该被用上的时候。

### 1.3 两条路、两套帽

```text
thicken / generate-stage / pilot
  用户消息 = StageSpec + _ctx_bits（拍 200）     ← 下一阶段主燃料被削
  instructions = 全套 assemble（拍 700 + 演绎尖） ← 和用户消息对不齐

SPA /chat/write
  用户消息 = 种子话术
  instructions = 同上 assemble
```

同一章材料被裁两次、数字还不同。

---

## 2. 原则（最优，不是再加第三套字数质量）

**按「谁在读」分两档，禁止一套帽打天下。**

| purpose | 谁在读 | 上一层怎么给 | 理由 |
|---------|--------|--------------|------|
| **`thicken`** | 正在生成 **下一阶段** | **吃满**刚过闸的上一层（`cn ≤ floor×1.2` 不裁） | 写厚就是为了这一步 |
| **`rehearse`** | 正在生成 **排演 draft** | 大纲+节拍吃满；**演绎吃满**（可按人分段，整包帽 ≥ 地板） | 排演 = 走认知地图 |
| **`surface`** | 正在写 **读者正文 final** | 只给尖：大纲/每拍刚过闸则全给；演绎焦点角+他人边界；排演**按拍抽骨架** | 限知不被 5000 全知灌爆 |

字数仍只表示覆盖，不进 `may_claim_*`。

**刚过闸必须 100% 进提示词。**  
`inject_cap` 只砍「写超了很多」的尾巴，不砍地板本身：

```text
if cn_len(text) <= floor * 1.2:  原文全给
else:                            裁到 inject_cap，且 inject_cap >= floor
```

---

## 3. InjectSpec（唯一数字表）

落 `scribe3/iceberg.py`（或 `stage_generate.py` 再 export），**禁止** `_ctx_bits` / `_outline_block` / `draft_tip` / deduction 各写一套。

| 字段 | floor | thicken 帽 | rehearse 帽 | surface 帽 |
|------|-------|------------|-------------|------------|
| synopsis | 500 | **全文**（上限 2500，仅防万字粘贴） | 全文 / 2500 | `max(800, floor)`；≤600 不裁 |
| beat each | 500 | **全文** / 1200 | 全文 / 1200 | `max(700, floor)`；≤600 不裁 |
| beat join | — | **换行编号**，禁止空格拼接 | 同左 | 同左 |
| scene_truth | （无 5000 地板） | 全文 / 2500 | 全文 / 2500 | 全文 / 1200 |
| deduction 焦点 | 计入 5000 | 不注入（本阶段在写它） | **全文** / 4000 | 1800 五层 |
| deduction 他人 | 计入 5000 | 不注入 | **全文** / 2000 | 边界一行（80+60） |
| deduction 整包 | 5000 | — | **≥6000**（先于 DEFAULT_CODEX 4500） | 4500 尖端包 |
| draft | 10000 | — | 不回灌自己 | **按拍抽骨架** 合计 ≤2400，**每拍都要露头** |
| 旧 plan 250/40 | — | **删出发路径** | 删 | 删 |

`DEFAULT_SOFT_LEN_FLOOR`：改名或注释钉死「已有稿 skip 加长」≠ 水面 5000；**不要**再让 2400 出现在作者可见 steer 里。水面只留 `BASE_LENGTH_STEER` 一套。

---

## 4. 各阶段读什么（改完后）

```text
① outline thicken
   吃：设定/协议/作者意图 + 旧大纲全文（若薄要加厚）
   不吃：演绎、排演、正文

② beats thicken
   吃：大纲全文（≥500 全给）
   不吃：每拍 200 字残片；不吃 250/40 预算圣经

③ deduce thicken
   吃：大纲全文 + 每拍场面纸全文
   不吃：自己的 5000（还没写完）

④ draft rehearse
   吃：大纲全文 + 每拍全文 + 每人五层全文（整包 ≥5000）
   不吃：final 那套 1800/一行/4500

⑤ final surface
   吃：大纲尖（刚过闸则全给）+ 每拍尖（刚过闸则全给）
        + 焦点 ≤1800 + 他人边界 + 按拍排演骨架（3+ 拍都在）
   不吃：万字排演原文、非焦点「没察觉的」
```

L2：`outline` 在 `cn(synopsis)≤800` 时 **禁止保拍砍纲**（没有可砍的肥肉）。  
`draft_tip` 登记进物理序（outline 后、deduction 前），列入 `GEN_SEGMENT_PROTECTED`。先砍 `material_recall` / `reference_craft` / `storyline_polish`。

---

## 5. 现网改动清单

| 文件 | 改什么 |
|------|--------|
| `iceberg.py` | `INJECT` 表 + `clip_for(purpose, field, text)` + `passthrough_if_near_floor` |
| `stage_generate._ctx_bits` | 改走 `clip_for("thicken", …)`；拍不再 `[:200]` |
| `write_assemble_context._outline_block` | 按 phase→purpose；换行编号；**删 plan 密≥250/疏≈40** |
| `_deduction_context_segments` | `purpose=rehearse\|surface`；draft 不走 1800+4500 |
| `_apply_deduction_pack_cap` | rehearse 帽 ≥6000 |
| `draft_tip` | 按拍抽骨架（进场/事件/出场各 ≤N），禁止 `raw[:2400]` |
| `write_assemble_v1` | draft vs final 传 purpose；`draft_tip` 只 surface |
| `context_budget.py` | 登记 `draft_tip`；保护；短大纲不砍纲 |
| `execution_contract.py` | 作者可见文案去掉 2400 软地板口吻 |
| 单测 | 500 字大纲 thicken 用户消息含全文；3×500 拍 draft 提示词三段都在；final 非焦点无「没察觉的」；draft_tip 登记且 L2 不先丢 |

---

## 6. Key Decisions

1. **thicken / rehearse / surface 三 purpose，一套 InjectSpec。** 不准再出现第三处 `[:200]`。  
2. **刚过闸 = 100% 可见。** 帽只砍超写。  
3. **5000 演绎的消费者是排演，不是 final。** final 继续限知尖——这不是浪费，是冰山。浪费的是 draft 也只给 1800。  
4. **10000 排演进 final 必须按拍抽，不能截前 2400。**  
5. **不把 250/40 预算契约再注入写路径。** 旧 `validate_beat_budgets` 可留作可选机读，不进 prompt。

---

## 7. 明确不做

- 不把 5000 演绎整包灌进 **final**（限知灌爆）。  
- 不把 10000 排演原文灌进 final（定稿变复读）。  
- 不改 GATE-B 80、不重开宣称。  
- 不为注入再起 Surreal 表。  
- 不在 Grok 机跑全量测。

---

## 8. PR Plan

| PR | 标题 | 内容 |
|----|------|------|
| I1 | InjectSpec + `_ctx_bits` / outline 换行 | 刚过闸不裁；删 250/40；拍不再 200 |
| I2 | deduction purpose 分档 | draft 吃满；final 仍尖 |
| I3 | draft_tip 按拍抽 + L2 登记保护 | 3 拍都在；短大纲不砍纲 |
| I4 | demo 一章对账冒烟 | 日志/body：thicken 含全文；final 无 5000 整包 |

先落地 I1，白写立刻停。

---

## 9. 验收

1. 库里 synopsis=520 → beats 生成用户消息含这 520，不是 200 字残片。  
2. 3 拍各 500 → deduce / draft 提示词三段全文都在，且换行，不空格粘成一团。  
3. 演绎合计 5200 → **draft** 提示词合计 ≥5000；**final** 焦点 ≤1800、他人无「没察觉的」。  
4. 排演 10000、4 拍 → final `draft_tip` 4 个拍头都在，不是只前 2400。  
5. L2 超窗：先丢 material/polish；520 字大纲不被「保拍砍纲」删掉。  

做不到 1–2，就还是「写了没用上」。

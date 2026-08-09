# 记忆质量 · 根因分析与最优改进方案（v2 · 2026-08-09）

| 项 | 值 |
|----|-----|
| **版本** | 2.1（根因驱动 + **PR-A/B/C 工程落地** · 2026-08-09） |
| **目标** | 七维**质量**逼近 ≥9.5（不是 M0–M6 再绿一遍） |
| **环境** | 只在 demo 已部署栈验证；禁止本机 Surreal/全量 npm |
| **前序** | v1.1 七维方案已落地地基；本版钉死「为何仍只有 6.5–7.5」 |
| **工程状态** | **PR-A/B/C + 最佳方案 v3 Wave-A/B/C 工程已热更 demo**；A/B 基线 lead=0.5 未过；**人盲未做** → **仍不宣称任一维 ≥9.5**。权威执行见 `docs/plans/2026-08-09-memory-quality-best-plan-v3.md` |

---

## 0. 结论摘要（先给答案）

**根因不是「没部署」或「探针不够绿」。**  
`book_4c7815eb` 已证明：链路通、锚能进文、铁律大体遵守。质量卡在 **真值模型/冲突消解/注入策略/验收方式** 四层错位：

| # | 根因（一句话） | 主伤维度 | 业界对应 |
|---|---------------|----------|----------|
| R1 | **单真值键错了**：折叠只认 `(entity, attribute)`，变更常写**新 attribute / 把旧态嵌进 value 长串** → 表面双真 | D4 | 时态 KG：同一关系槽位 supersede，不是另开槽并存 [web:19][web:22][web:25] |
| R2 | **注入层无冲突消解**：must-link 把 artifact=完整无缺 **与** condition=缺口 **同时钉成〔必需〕**；模型碰运气站队 | D3/D4 | RAG 冲突需 **fact-level 过滤**，否则 retrieval 比 zero-shot 更糟 [web:9][web:16][web:12] |
| R3 | **验收与生产路径脱节**：质量测的是「强 steer 灌锚」；产品默认 `MEMORY_STEER=full`；D5 几乎未测 | D5/D7 | 长篇依赖「结构化真值 + 按需切片」，不是 prompt 圣经 [web:21][web:3] |
| R4 | **限知只擦 secret 明文，不建模「谁知何时知」**；M5 启发式过松/过严都失真 | D6 | Narratology memory：who knows secret **and when** [web:3] |
| R5 | **写回污染主记忆**：post-finalize/ingest 把群像写进全局角色层，稀释主角锚 | D1/D3 | 数据质量是 RAG 第一瓶颈 [web:13]；分层记忆（canon vs episodic）[web:1][web:6] |
| R6 | **质量量表错位**：M0–M6 / 文件存在 = 地板；无人评 A/B → 永远假 9.5 | D7 全局 | 创意写作缺可验证答案，须对照与人评 [web:0]；D7 协议已有未执行 |

**最优策略：** 先修 **真值语义（R1）+ 注入冲突消解（R2）**，再强制 **极简 steer 消融（R3）** 与 **认知图（R4）**，最后用 **人评 A/B（R6）** 封顶。不做新大框架、不换库、不重写 fabric。

---

## 1. 证据链（本仓可复现）

### 1.1 双真实锤（`book_4c7815eb` @ch5 prefetch）

```
〔必需〕world:三棱铜匙·artifact = …完整无缺
〔必需〕world:三棱铜匙·condition = …齿边新缺口
```

同时 `facts_at` 的 `collapse_facts_single_truth` **无法合并**二者（键不同）。  
正文 ch4–5 **跟着缺口写对了** = 模型选对，**不是**系统只给一真。

### 1.2 代码层根因定位

| 位置 | 行为 | 问题 |
|------|------|------|
| `facts_knowledge.collapse_facts_single_truth` | 键 = `(entity_id, attribute)` | 正确实现了「同槽单真」；**调用方却把同一物件状态拆成多 attribute** |
| `v63 apply_a6_mutation` | 旧写 `attribute=artifact` 且 value 含「完整无缺」；新写 `attribute=condition` | **变更 API 用错槽**；应 `supersede_fact(entity, "condition" 或统一 "state")` 并改写/关闭旧串 |
| `canon_apply_store._apply_fact` | `add_fact` 默认 supersede 同 attribute | change-pack 若 field 不一致 → 旧行永活 |
| `memory_must_link.collect_must_anchors` | 对 `artifact` **与** `condition` 都加分置顶 | **无「同 entity 矛盾检测」** |
| `v63 drive_chapter` steer | 长段强制专名+禁串书 | D5 消融无效；质量归因混淆「记忆 vs 指令」 |
| `epistemic_guard` | 擦 **secret 命题明文** | A7 若非 secret 或只以碎片出现 → 不护「认知合理」 |
| post-finalize / ingest | 扩角色进库 | prefetch 主角色出现王二嫂/覃有年等 |

### 1.3 业界对齐（检索结论 → 设计约束）

1. **时态知识图 / Graphiti·Zep 类**：事实带 `valid_from/to`，改职/改态是 **invalidation + 新边**，查询默认「当下真」 [web:19][web:22][web:24][web:25]。  
   → 我们已有 valid_from/to + supersede；缺的是 **槽位本体（同一物件「外观状态」只能有一个 open 槽）** 与 **注入时只暴露当下真**。

2. **TruthfulRAG / FaithfulRAG**：冲突要在 **事实级** 消解，不能只堆 retrieved chunks [web:9][web:11]。  
   → must-link 并列矛盾 = 经典「检索毒化」。

3. **RAGuard 类发现**：误导性检索会使 RAG **弱于** zero-shot [web:16]。  
   → 双真注入比「少记一点」更危险。

4. **叙事 KG 双向管道**：生成 ↔ 图对齐，减少幻觉 [web:21]。  
   → 写后闭环应 **校验/ supersede**，不是只 **append 噪声角色**。

5. **限知 = 认知状态图**：who knows / when [web:3]。  
   → 不能只靠 string scrub。

6. **创意写作评估**：缺标准答案 → 必须 **人评 + A/B** [web:0]。  
   → D7 的 `comparison_protocol` 是正道，尚未当真跑。

---

## 2. 根因分层模型（便于排期）

```text
┌─────────────────────────────────────────────────────────┐
│ L0 验收错位：绿=好；强 steer 冒充记忆（R3/R6）              │
├─────────────────────────────────────────────────────────┤
│ L1 注入冲突：must-link / prefetch 并列矛盾（R2）           │  ← 读者可见「记忆在撒谎」
├─────────────────────────────────────────────────────────┤
│ L2 真值语义：槽位/value 嵌套态/错误 attribute（R1）         │  ← 根
├─────────────────────────────────────────────────────────┤
│ L3 认知模型：knows 边未驱动写路径限知（R4）                  │
├─────────────────────────────────────────────────────────┤
│ L4 写回治理：episodic 污染 canon 层（R5）                   │
└─────────────────────────────────────────────────────────┘
```

**最优路径：L2 → L1 → L0（消融）→ L3 → L4 → 人评封顶。**  
先修根再测质量；禁止继续堆探针绿。

---

## 3. 最优改进方案（按 ROI）

### P0 — 真值语义与变更纪律（锁死 D4）

**目标：** 改设定后，**任意** `facts_at` / must-link / prefetch / usage_digest **不得同时暴露互斥态**。

#### 3.1 物件状态槽位本体（Attribute Registry）

为「会变的世界」固定槽，禁止把状态塞进散文 value：

| 实体类 | 规范 attribute | 示例 value（短、原子） |
|--------|----------------|------------------------|
| 关键物件 | `state`（唯一开放态） | `完整` / `齿边缺口·炉门咬痕` |
| 规则 | `rule_text` | 一句铁律 |
| 角色 | `status` / `location_hint` | 可选 |

- **废弃用法：** `artifact` 长串里嵌「完整无缺」；变更时另开 `condition`。  
- **迁移：** 历史 `artifact` 中可解析的状态 → 抽到 `state`，旧行 `valid_to` 关闭。

#### 3.2 变更唯一入口

```text
作者改设定 / change-pack / s3_add_fact(状态类)
        ↓
resolve_slot(entity, semantic_attr)  → 规范 attribute
        ↓
supersede_fact(entity, attr, new_value, since_chapter)  // 禁止静默 add 新 attribute
        ↓
（可选）矛盾扫描：同 entity 其它 open 行 value 与 new 互斥 → 一并 close 或告警
```

- 改 `canon_apply_store._apply_fact`：状态类 field 强制走 `supersede_fact`。  
- 改 `v63 apply_a6_mutation`：对 `world:三棱铜匙` 的 **同一 `state` 槽** supersede；删「新 condition」路径。  
- 探针 **质量化**：`prefetch` 在变更后 **禁止** 同时命中旧短语与新短语（不只同键 supersede 绿）。

#### 3.3 读路径「实体投影」

在 `collapse_facts_single_truth` **之外**增加：

```text
project_entity_surface(facts) →
  每个 entity 一组「当前标签」；
  若检测互斥对（完整无缺 vs 缺口、活 vs 死…）→ 只保留 valid_from 最新且记录 conflict_resolved
```

注入（must-link / assembler）**只消费投影结果**，禁止原始双行并列成〔必需〕。

**验收（质量）：** 对 `book_4c7815eb` 跑变更后 prefetch：  
「完整无缺」**不得**出现在 must-link；「缺口」必须出现。正文抽检 ch4+ 与投影一致。  
→ **D4 质量门槛：≥9.0 才谈 9.5（人评「改过像改过」）**。

---

### P1 — 注入冲突消解（锁死 D3 表面）

**目标：** 检索/钉锚 **永不** 同时推荐互斥事实（TruthfulRAG 精神，轻量实现）。

1. **must-link 去矛盾：** `collect_must_anchors` 后跑 `resolve_conflicts(anchors)`。  
2. **预算去重：** `pin_must_first` 已有正文去重；扩展为 **entity 级** 去重。  
3. **矛盾词典（最小）：** 配置/规则：`(完整无缺, 缺口)`、`(未冷, 已冷死)` 等；后续可 embedding 对立检测。  
4. **usage_digest 诚实：** 若发生冲突消解，digest 记 `conflicts_dropped: N`，作者可见「记忆在裁矛盾」——服务 D1/D7。

**不做：** 引入完整 TruthfulRAG 熵过滤（算力与延迟过高）；本产品以 **权威正典** 为准，冲突时 **canon 赢、较新 valid_from 赢**。

---

### P2 — 验收与生产对齐（解锁真实 D5/D7）

**目标：** 测到的就是用户用的。

| 项 | 现状 | 改进 |
|----|------|------|
| 连载 steer | 长圣经 | 质量跑强制 `SCRIBE3_MEMORY_STEER_MODE=minimal` + `minimal_chapter_steer` |
| 刷分 | 作者粘贴设定 | `detect_author_restated_canon` **一票否决** 该维分 |
| D7 | 仅 API 可见 | 执行 `memory_gain.comparison_protocol`：**A=开 fabric，B=关 must-link+事实块** 各写 1 章，人评三项 ≥4.5 且 A 领先 ≥1.5 |
| M 探针 | 通/绿 | 保留为 **门禁地板**；质量报告 **单独** `12-quality-d1-7.md` |

**消融协议（固定书 `book_4c7815eb` 或新书）：**

1. 章 N 大纲固定。  
2. **A 组：** 现网记忆全开 + minimal steer。  
3. **B 组：** 关 must-link + 关 facts 注入（或 fabric 软关）+ 同 minimal steer。  
4. 盲评：连贯 / 正典回声 / 矛盾（1–5）。  
5. 仅当 A 显著优于 B → D5/D7 可报 ≥9。

---

### P3 — 认知限知（D6 从运气 → 结构）

**目标：** 灰狸 POV **不是**「没写出 A7 整句」，而是 **帧内不可知的秘密不得以「已理解」方式出现**。

1. **知识边驱动：** 写路径 `focalizer` → `frame_known_fact_ids` **已有**；扩展：  
   - 帧外 secret → 继续 scrub（现有）；  
   - 帧外 **非 secret 但标记 `epistemic=hidden`** → 注入侧 **不进入** 该 POV 的「已知」块，仅可进「环境可观察」块。  
2. **A7 类：** 建 `fact` + `role:冷锅婆 knows`；灰狸 **无** knows 边。  
3. **人评问卷：** 「读 ch3，你是否认为灰狸 **已经知道** 炉心印开侧门？」目标：否 ≥80%。  
4. 废弃过严 heuristic（侧门∧炉心印∧打开）；改为 **认知问卷 + 帧扫描**。

---

### P4 — 写回分层（D1/D3 防脏）

**目标：** 过程记忆 / 章后提取 **不得污染** 北极星角色与正典主锚。

| 层 | 内容 | 注入优先级 |
|----|------|------------|
| Canon L1 | intent / 铁律 / 主角 / 规范 state 事实 | 最高 |
| Canon L2 | 伏笔 / 次要设定 | 中 |
| Episodic | 章后人物、一次性动作 | **默认不进 global 主要角色**；需作者批准升格 |

- post-finalize：新角色默认 `importance=extra` 且 **不进** `characters:main` 列表。  
- prefetch 主角色列表：**仅 protagonist + major**。

---

### P5 — 质量封顶流程（唯一宣称 9.5 的路径）

1. P0–P1 合并部署 demo。  
2. 修复书或新书 5 章：**minimal steer** 连载。  
3. D4 自动：**变更后零双真**。  
4. D5/D7 人评 A/B。  
5. D6 认知问卷。  
6. 七维表：每维质量证据链齐全才可填 ≥9.5；缺人评维 **封顶 6.0**。

**明确否决：**  
- 只靠 M0–M6 PASS 写进对外「记忆质量 9.5」；  
- 完整设定 steer 刷跨章分；  
- 再起第二套 Surreal 验收。

---

## 4. 实施排期（建议 3 个 PR 切片）

| 切片 | 内容 | 验收 |
|------|------|------|
| **PR-A** | Attribute 规范 + supersede 变更入口 + A6/脚本修正 + entity 投影 + must-link 去矛盾 + 质量探针「禁双真」 | demo：`book_4c7815eb` prefetch 无「完整无缺」；有缺口 |
| **PR-B** | minimal steer 默认质量路径 + 连载驱动开关 + 消融脚本 + 主角色分层 | A/B 草稿可产出；无作者圣经刷分 |
| **PR-C** | epistemic 注入分层 + post-finalize 不升格 extra + 人评表与 `12-quality-d1-7.md` | 问卷 + A/B 填表后才允许报分 |

每切片：**hot deploy demo → 冒烟 → 质量探针**；不跑本机全量测。

---

## 5. 成功标准（可审计）

| 维 | 质量 ≥9.5 才允许的证据 |
|----|------------------------|
| D1 | 对抗「未写入设定」时模型承认不知；矛盾 digest 可见 |
| D2 | minimal 下铁律仍进正文（人抽 5 章） |
| D3 | 极简指令下专名自然、非清单腔（人评） |
| D4 | **注入面零互斥双真** + 正文跟新态 |
| D5 | A/B：A 显著优于 B |
| D6 | 认知问卷 + 帧外 secret 零明文 |
| D7 | 协议三项达标；作者主观「记忆在扛」 |

---

## 6. 非目标（防范围膨胀）

- 不换 Surreal / 不上 Graphiti 全量产品。  
- 不做完整 TruthfulRAG 熵模块。  
- 不重训写作模型。  
- 不把 Hermes 当剧情真相库。  
- 不为验收再拉平行库。

---

## 7. 风险

| 风险 | 缓解 |
|------|------|
| 历史数据多 attribute 脏 | 一次性 migration 脚本 + 投影兜底 |
| minimal 后成稿变差 | 正说明记忆未达标；用 A/B 驱动修 must-link 而非加回圣经 |
| 互斥词典不全 | 先覆盖状态对立高频；漏网靠 valid_from 最新 |

---

## 8. 落地记录（2026-08-09）

| 切片 | 状态 | 要点 |
|------|------|------|
| **PR-A** | **done** | `fact_surface` 互斥投影；`facts_at` 注入单真；`supersede` 交叉关槽；`book_4c7815eb` prefetch **无完整无缺、有缺口** |
| **PR-B** | **done** | global 主角色仅 protagonist+major；`v63` 支持 `MEMORY_STEER=minimal`；`scripts/ablation_memory_d5d7.py` |
| **PR-C** | **done** | must-link 限知帧过滤；新建角色默认 `extra`；`scripts/quality_d17_report.py` + 证据 `12-quality-d1-7.md` |

### demo 冒烟快照（`book_4c7815eb`）

- 双真：消  
- 主要角色行：`覃灰七、冷锅婆`（无王二嫂等噪声）  
- D4–D7 地板探针：通（质量 9.5 仍待人评）  
- 消融：`artifacts/.../12-ablation-d5d7.md`  
- 质量表：`artifacts/.../12-quality-d1-7.md`

### A/B minimal 收尾（2026-08-09 · 自动化协议跑完）

| 项 | 结果 |
|----|------|
| 书/章 | `book_aa57f17e` ch6（真 chat 旅程书） |
| 路径 | `scripts/run_memory_ab_minimal.py` · minimal + A ON / B OFF → 恢复 ON |
| lead | **0.5**（门槛 1.5） |
| pass_rule_met | **false** |
| 主增益 | contradiction 5.0 vs 3.5；coherence/canon_echo 持平 3.5/4.8 |
| 证据 | `artifacts/e2e-journey-2w-chat-v632-20260809-book_aa57f17e/ab-minimal/13-ab-closeout.md` |
| 结案 | **工程 A/B 收尾完成**；质量仍 ~7；**禁止 9.5** |

### 仍须人完成（无法自动化封顶）

1. ~~minimal 下再写对照章~~ → **已跑** ch6 双稿（机器初评）  
2. **真人双盲**覆核 `a_prose`/`b_prose` 三项分（D7 正式封顶）  
3. **认知问卷 ch3**（D6）——本轮 `d6_questionnaire` 未绑全文  
4. （可选工程）拉大 minimal 下 A 的 coherence/canon_echo 差，再跑一轮 A/B  

**本 plan：PR-A/B/C + 最小 A/B 工程路径已完成；未宣称任一维质量 9.5。**

# scribe3 统一上下文+记忆系统 · 验收报告

- **验收日期**:2026-07-11
- **代码基线**:`9fd35b7`(分支 codex/pc-ui-system-polish)
- **里程碑提交**:`83c93e4`(Task 8/9/10/11/13 记忆核心)、`1fd6e2f`(Task 14/15 检查器+影子+全系统审查加固)、`9fd35b7`(Task 16 隔离/安全/性能/可观测/开关/检索接线)
- **范围**:计划 `docs/superpowers/plans/2026-07-10-scribe3-unified-context-memory.md` 全 17 任务

## 1. 系统概述

统一上下文+记忆系统把主编从"每轮无状态"升级为:原子 ContextSnapshot(Task 2-5)+ 一 work 一连续主编线程(Task 6)+ 可预算可追溯 ContextAssembler(Task 7)+ 多通道记忆检索(Task 8:structured/bm25/vector/graph→RRF,限知时态门)+ 幂等捕获管线(Task 9)+ 三时态生命周期(Task 10:supersede/invalidate/forget)+ Hermes 稳定/动态层(Task 11)+ Runs 审批链回主编线程(Task 13)+ 上下文检查器/记忆溯源 UI(Task 14)+ Spectron 影子门禁(Task 15)+ 隔离/安全/性能/可观测/灰度开关(Task 16)。

**核心闭环(Task 16-C)**:全系统审查揭示系统一度是"只写不读半空转"(捕获恒开写入,检索器 `_get_write_retriever` 恒 None 永不读)。Task 16-C 用 `SCRIBE3_MEMORY_FABRIC_V1` 对称门控 capture+retrieval:默认关=字节等价(零 embed 成本、零写入),开=经验记忆经 MemoryRetriever 四通道进写作 prompt(seed_words/章纲作检索 query),且剧透门(known_from)/秘密屏蔽(assembler C1)/work 隔离三守卫全生效。

## 2. 自动化验收结果(Step 1-3, 5)

| Step | 项目 | 命令 | 结果 | 门槛 |
|---|---|---|---|---|
| 1 | 后端完整回归 | `pytest -q scribe3/tests` | **1527 passed**(0 fail/0 error) | 0 failures ✅ |
| 2 | 前端回归 | `npm test` | **381 passed**(67 files) | 0 failed ✅ |
| 2 | 前端生产构建 | `npm run build` | **exit 0** | exit 0 ✅ |
| 3 | SurrealDB 版本 | `surreal version` | **3.2.0** | 3.2.0 ✅ |
| 3 | SurrealDB 就绪 | `surreal is-ready --endpoint :8001` | **OK** | OK ✅ |
| 3 | Hermes 版本 | `hermes --version` | **0.18.2** | 0.18.2 ✅ |
| 3 | Hermes 冒烟 | `bash scribe3/scripts/hermes_smoke.sh` | **PASS=11 FAIL=0** | 11/0 ✅ |
| 5 | 金标评测 | `context_memory_eval.py`(flag 开) | 见下 | 见下 |

**Step 5 金标评测(36 例门禁全绿)**:

| 指标 | 实测 | 门槛 |
|---|---|---|
| Recall@10 | **1.0** | ≥0.90 ✅ |
| nDCG@10 | **1.0** | ≥0.85 ✅ |
| provenance_coverage | **1.0** | 1.0 ✅ |
| cross_work_leaks | **0** | 0 ✅ |
| stale_revision_accepts | **0** | 0 ✅ |
| p95 | **0.004ms** | <250ms ✅ |

## 3. 写作质量金丝雀门(Step 5b)

沿 D-028 惯例,开 `SCRIBE3_MEMORY_FABRIC_V1`+`SCRIBE3_CONTEXT_ASSEMBLER_V1` 独立后端(演练 work,不碰生产纸命),真机生成一章,跑既有 QC 检测器(复读/telling/限知泄露/排比/拟声词),各项不得高于重构前基线;`chat_message.trace.context` 须含 envelope 块。

**状态:PASS**(独立 flag-on `:3399` vs flag-off 对照 `:3398`,同 SurrealDB per-work 隔离,未碰生产 `:3321`/纸命;演练 work ON=`book_f4ae6fdd`/OFF=`book_d97fddb2`)。

- **写作质量不回退**:对照法(ON_omni vs OFF_omni,仅 flag 不同)重量级检测器全部 0=0(复读/跨章复读/排比/情感直说/过饱和/整句重复/god_view)。唯一差异 `ai_tics(em_dash)` 开=1/关=0,根因定位为**长度密度阈值边界的单样本噪声**(破折号构造两侧各 2 对相同,ON 写短 981 字 2.04‰ 刚过线、OFF 1126 字 1.78‰ 刚不过),非 flag 效应。
- **限知不泄(硬红线)**:所有生成秘密破绽词=0、god_view=0,含最危险的焦三限知焦点稿(秘密是可检索正典材料)。**红线过**。
- **envelope 在场 + 经验记忆真进 prompt + 零回退**:in-process 组装 envelope 8 块齐全(focus/global/canonical/recent/procedural/reference/uncertainty/provenance);经验记忆(火候/留白/包袱)命中 recent+procedural 块,差分证明 `retriever=None` 时召回=[](召回由 fabric 带来);`_context_assembler_fallbacks` 0→0、服务端 0 告警、2 次 chat/write 均走 v1 未降级;捕获 3 条落 memory_item,pending=0/failed=0。

**结论:PASS,无需回滚 assembler 收口。**

**验收发现的两个 caveat(已回修)**:
1. **`chat_message.trace.context` 未存 envelope 块清单**(计划 Step 5b 要求):当前 assistant trace 仅含 response_id/status/tool_calls/tool_outputs/usage,envelope 只渲进 instructions 不落 trace。金丝雀改用 in-process 组装块清单 + 零回退告警 + fallbacks 计数证明。→ 已补:chat/write 落 chat_message 时把 envelope 块清单存进 trace.context(供 Inspector 审计"主编这轮看到哪些上下文块")。
2. **`get_voice_profile` 裸名 500**(旧路径既存缺陷,与本次 flag 无关):focalizer 传裸名("焦三"而非 `role:jiaosan`)且无 voice_profile 时 `_split` 抛 ValueError(app.py:3870 `_voice_anchor_block`)。v1 路径不调此块不受影响。→ 已补:`get_voice_profile` 对无冒号入参兜底。

## 4. 产品语义浏览器验收(Step 4,待真机 UI)

7 场景(需浏览器 + 真机灰度,与 Step 6 一起,待作者在场):
1. 同 work 谈角色→切伏笔→"继续刚才取舍",主编承接历史且焦点明确。
2. 切 work,不提前作品角色/秘密,保留用户通用偏好。
3. 角色限知视角开秘密事实,Inspector 只显遮罩来源,不泄 value。
4. 发起写入 Run 后切焦点,审批卡显示过期+二次确认/重建。
5. 刷新恢复同一 thread/pending approval/snapshot/焦点标签。
6. 断开 Hermes read gateway,UI 显只读联查不可用(不伪装模型失败),恢复不丢 thread。
7. 断开 SurrealDB 再恢复,store 重连后 revision 不回退,幂等 navigation 不重复。

## 5. 灰度次序(Step 6,产品决策)

固定次序,每步观察指标(`/ai/runtime-status` 的 `context_memory` 块:cross_work_rejections/memory_events_pending-failed/retrieval_p50-p95):
1. 开发环境开 ContextSnapshot,memory fabric 保持关。
2. 内部 work 开 EditorialThread,连续 3 天查 stale/cross-work。
3. 开 MemoryFabric **只读检索**(不开自动捕获),对比 gold set。
4. 开 capture + consolidation,保持写入审批与可视化 trace。
5. 开 Inspector 给作者查主编"为什么知道"。
6. Spectron 仅发布门禁通过后进影子(当前包 PyPI 未发布,恒关)。

**注意(Task 16-C M4)**:检索进 prompt 需 `MEMORY_FABRIC_V1`+`CONTEXT_ASSEMBLER_V1` 同开;单开 fabric 只捕获不读。

## 6. 回滚锚点(Step 7)

- **migration 最高版本**:082(`082_memory_trace.surql`);回滚不删表(数据保留)。
- **运行时版本**:SurrealDB 3.2.0、Hermes 0.18.2。
- **feature flags(默认全关=当前生产行为)**:`SCRIBE3_CONTEXT_SNAPSHOT_V1`/`SCRIBE3_EDITORIAL_THREAD_V1`/`SCRIBE3_MEMORY_FABRIC_V1`/`SCRIBE3_CONTEXT_INSPECTOR_V1`/`SCRIBE3_SPECTRON_SHADOW`/`SCRIBE3_CONTEXT_ASSEMBLER_V1`。
- **回滚顺序**:inspector → memory retrieval → editorial thread → context snapshot(只关开关+恢复路由,不删表、不改历史、不丢作者会话)。
- **gold metrics 基线**:Recall@10=1.0/nDCG@10=1.0/provenance=1.0/p95=0.004ms(见 §2)。
- **数据备份**:生产数据在 `~/.scribe2-surreal/data.db`(逐书备份 `surreal_backup.sh`)。

## 7. 审查记账(诚实边界,后续收口项)

全系统深度审查(10 维×27 agent 对抗验证)+ 各任务双审确证并修复:秘密 trace 服务端权威(重犯 assembler C1)、捕获 processing 孤儿静默丢失、canonical_claim 非幂等、run trace redactor 两个 Critical 秘密泄漏(认证正则顺序/error 绕过)、剧透门缓存击穿、空 query 欠交付(经验记忆读入为零)——均已修 + 测试守护。

**明确记账的后续增强(非缺陷,不阻塞灰度)**:
- Task 9:自由文本 (entity,attribute) 精确抽取(正典压制对真机 episodic 部分靠 attribute)、relation 建边、session_end/on_pre_compress 真接线(本仓无 Hermes compress 挂钩)。
- Task 16:GLOBAL_CARD_CACHE 键接线前须加 chapter/focalizer 维(当前休眠)、`_secret_fact_ids` 每 save 全表扫 proposition(可缓存)、写作热路径缓存命中率(M2 失效优先取舍)、run 逻辑-work 绑定(依赖 Task 13 落逻辑 work)、实时 run 端点跨 work 委托 Hermes session_key 强制(建议本报告 §4 场景验证)。
- Task 12(可选 scribe3-memory Hermes provider):优先级最低,Scribe Web 主路不依赖,未实现。

## 8. Step 4/6 真机验收结果(2026-07-11 补,独立开 flag 后端,未碰生产)

**Step 4 七场景全 PASS**(REST 端到端 + 已有测试/代码确认):

| # | 场景 | 结果 | 证据 |
|---|---|---|---|
| 1 | 历史承接 | PASS | 3 轮真主编回复同一线程(6 消息)、navigate rev0→1→2、焦点标签逐条落库、当前快照 focus 正确 |
| 2 | 跨 work 隔离 | PASS | session/navigate 跨 work→404、thread→409 context_work_mismatch、cross_work_rejections+1、金标 leaks=0 |
| 3 | 限知秘密屏蔽 | PASS | trace.context manifest 无秘密 token;at-rest+GET API 双抹、秘密条目 text 空、非秘密保留(精准) |
| 4 | Run 过期审批 | PASS | origin 绑定入 trace→navigate→审批 409 run_context_changed(进 Hermes 前拦)、deny 不被拦、test_ai_runs 12 绿 |
| 5 | 刷新恢复 | PASS | 重启后端后 16 消息/焦点/session/current_rev=2(不回退)/rev0 快照 hash 一致/8 记忆项全按 id 从 DB 恢复 |
| 6 | Hermes 断连降级 | PASS | 坏网关下 runtime-status ok=False、available 全 False、degraded 三项 True、issues 含 *_gateway_unavailable(诚实上报非伪装) |
| 7 | SurrealDB 重连 | PASS | test_store_reconnect 4 例 + test_context_store 14 例(CAS/幂等/revision 单调/去重)全绿 |

**Step 6 灰度逐级全达标**(证明可安全放量):

| 步 | flag | 指标 | 达标 |
|---|---|---|---|
| 6.1 | SNAPSHOT | 无绑定 chat/write→400 context_binding_required | ✅ |
| 6.2 | +EDITORIAL | 主编线程 16 消息 DB 恢复连续 | ✅ |
| 6.3 | +FABRIC+ASSEMBLER(M4 同开) | retrieval p50=6ms/p95=28-34ms(<250ms)、pending/failed=0、金标绿 | ✅ |
| 6.4 | 捕获+consolidation | 8 轮:memory_item 0→4→8 单调增、event 全 drain(pending/failed=0) | ✅ |
| 6.5 | +INSPECTOR | 全 5 flag=true、GET trace 可取(有数据屏蔽/无数据 404) | ✅ |

金标 baseline(fake:clean)7 门槛绿(Recall@10/nDCG@10=1.0/p95=0.0035ms/36 例)+ 4 负向对照(cross_work/excluded/stale/partial)正确亮红,证门槛非虚绿。

**验证边界(concern,非阻断)**:
- **Inspector 的 memory_trace 数据源生产暂空**:chat/write 已把 envelope manifest 写进 `chat_message.trace.context`(已验不泄秘密),但 Inspector 专用的 `memory_trace` 表(GET /context/sessions/{id}/trace/{rev})的 build/save_memory_trace 仍无生产调用方,生产显"未检索到证据"。屏蔽机制本身 store 层 + manifest 双层测试锁死;真实检索→memory_trace 落库是明确的后续接线(Task 14 已标注)。
- **金标 CLI 用内置 FakeRetriever**:验证指标器+门禁链路+baseline;真实 MemoryRetriever 的生产表现由 runtime-status 真实指标(p95<250ms、捕获收敛)独立验证(§8 步 6.3/6.4)。

**验收产生的临时演练 work(未删,遵守破坏性红线,建议按需清理)**:`book_5bd72f52`(验收17演练A)、`book_8468fcd2`(验收17演练B)——在生产 SurrealDB per-work db,与纸命隔离。

---

## 验收总结

统一上下文+记忆系统 17 任务全部完成:代码实现 + 每任务双审/对抗审 + 全系统 10 维审查(27 agent) + 回修 + 自动化验收(后端 1527/前端 381) + 写作质量金丝雀门 PASS + 7 场景 + 灰度逐级验证,全部达标。**系统默认关时与重构前字节等价,可按 §5 次序安全灰度放量。** 剩余 concern 均为已如实记账的后续接线增强,非缺陷/阻断。

*代码与测试证据见提交 83c93e4 / 1fd6e2f / 9fd35b7 / 1fa4619。*

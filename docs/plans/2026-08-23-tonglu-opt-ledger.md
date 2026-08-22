# 铜炉最优化改造编号台账（2026-08-23）

与 Spec 编号一一对应。status = `done` 或 `decision: …`。

| ID | 标题 | 优先级 | 阶段 | status | 备注 |
|----|------|--------|------|--------|------|
| SYS-01 | Admin危险操作缺二次确认 | P0 | 0 | done | AdminConsole ConfirmDialog |
| SYS-02 | settings/admin板块零toast反馈 | P0 | 0 | done | SettingField/Admin showToast |
| SYS-03 | story-moves propose/review无审计日志 | P1 | 5 | done | story_moves_propose append_audit |
| SYS-04 | PUT /gateway/files无结构化审计 | P1 | 5 | done | gateway write_file append_audit |
| SYS-05 | 无主动告警机制 | P1 | 5 | done | scribe3/alerts.py webhook |
| SYS-06 | FastEmbed嵌入服务未探活 | P1 | 5 | done | GET /health embedding |
| SYS-07 | /settings/audit无admin门禁 | P2 | 5 | decision: 按产品决策保留已认证用户可读审计（规格原文：或按产品决策保留） | decision: 按产品决策保留已认证用户可读审计（规格原文：或按产品决策保留） |
| SYS-08 | 技法/招式列表空态无兜底文案 | P2 | 5 | done | SystemHub 空态文案 |
| SYS-09 | Gateway restart后无轮询探活 | P2 | 1 | done | retryUntilOnline 3×2s |
| SYS-10 | secret输入缺autocomplete="off" | P2 | 5 | done | autoComplete=off |
| SYS-11 | 幽灵配置SCRIBE3\_DESIGN\_BOOK | P3 | 5 | decision: 标记 deferred，旗已在 REGISTRY，章设计校验另走 DESIGN_BOOK | decision: 标记 deferred，旗已在 REGISTRY，章设计校验另走 DESIGN_BOOK |
| SYS-12 | 幽灵配置SCRIBE3\_STORYLINE\_UI | P3 | 5 | decision: 标记 deferred，前端 Gantt 未做入口 | decision: 标记 deferred，前端 Gantt 未做入口 |
| SYS-13 | SCRIBE3\_DEFAULT\_WORK裸environ绕过 | P3 | 5 | decision: 记录在案，app_impl 裸 environ 本轮不改启动路径 | decision: 记录在案，app_impl 裸 environ 本轮不改启动路径 |
| SYS-14 | MCP catalog gate字段为展示型非运行时门控 | P3 | 5 | decision: gate 字段为能力说明书非运行时门控（规格原文） | decision: gate 字段为能力说明书非运行时门控（规格原文） |
| DSH-01 | totalGoal=0时前端除零 | P0 | 0 | done | safeWordGoal/wordGoalPct |
| DSH-02 | InsightView不监听s3-live事件 | P1 | 1 | done | InsightView s3-live |
| DSH-03 | 连胜计算用服务器时区非用户时区 | P1 | 5 | done | progress(timezone=) |
| DSH-04 | /quality端点无TTL缓存但每次全查SurrealDB | P1 | 5 | done | /quality 5s TTL（按 work+max_chapter） |
| DSH-05 | PromiseLedger加载失败时静默消失 | P2 | 5 | done | PromiseLedger ErrorState |
| DSH-06 | 伏笔setup章被删后UI仍显示可点击 | P2 | 5 | decision: P2 跳章前校验留给前端章号存在性，台账已记 | decision: P2 跳章前校验留给前端章号存在性，台账已记 |
| DSH-07 | 200+章/100+伏笔时无分页无虚拟列表 | P2 | 5 | decision: P2 大规模虚拟列表远期 | decision: P2 大规模虚拟列表远期 |
| DSH-08 | set\_intent无乐观锁并发写同字段丢失 | P2 | 5 | decision: 规格写配额字段可接受无 CAS | decision: 规格写配额字段可接受无 CAS |
| DSH-09 | 跨视图切换时数据刷新依赖组件卸载/重挂载 | P2 | 5 | done | s3-live 递增 key 不依赖卸载 |
| CDX-01 | store patch白名单硬编码，新增schema字段被静默丢弃 | P0 | 0 | done | filter_patch_fields |
| CDX-02 | codex\_digest字段名错误（item用了不存在的字段） | P0 | 0 | done | kind_field_groups 真实 schema |
| CDX-03 | codex\_generate prompt不读schema字段列表 | P0 | 0 | done | spec_ask 注入 schema 键 |
| CDX-04 | Apply后不触发sync\_entity\_digests | P1 | 1 | done | after_canon_apply digest |
| CDX-05 | Apply后不触发codex\_secret\_bridge同步 | P1 | 1 | done | after_canon_apply secret bridge |
| CDX-06 | Apply后非fact实体不触发语义索引 | P1 | 1 | done | after_canon_apply semantic_index |
| CDX-07 | Reject不学习，下次抽取反复提同样噪声 | P1 | 5 | done | persist_pack 预取 rejected 去重 |
| CDX-08 | faction/item/term/world\_rule删除无级联清理 | P1 | 1 | done | _cleanup_record_refs 扩 faction/item/term |
| CDX-09 | faction删除不走lifecycle | P1 | 1 | done | delete_faction 走 cleanup |
| CDX-10 | MCP s3\_delete\_codex不走lifecycle | P1 | 5 | done | s3_delete_codex 走 delete_* 含 cleanup |
| CDX-11 | character secret bridge默认关闭 | P1 | 1 | done | SECRET_BRIDGE_ROLES 默认开 |
| CDX-12 | codex\_health与iceberg evaluate\_codex\_ready标准不一致 | P2 | 5 | decision: P2 两套完备性标准语义差记录在案 | decision: P2 两套完备性标准语义差记录在案 |
| CDX-13 | canon\_extract LLM prompt不含schema字段列表 | P2 | 5 | done | canon_extract prompt 注入 schema 字段列表 |
| CDX-14 | SurrealDB SCHEMAFULL表需手写migration | P2 | 5 | decision: 规格写高/P2，自动 SCHEMAFULL migration 生成器本轮明确推迟 | decision: 规格写高/P2，自动 SCHEMAFULL migration 生成器本轮明确推迟 |
| CDX-15 | motif/promise仅MCP可达，前端无REST路由 | P2 | 5 | decision: motif/promise 仅 AI 操作，按规格可文档化 | decision: motif/promise 仅 AI 操作，按规格可文档化 |
| CDX-16 | world\_rule无REST PATCH端点 | P2 | 5 | done | PATCH /world-rules/{name} |
| CDX-17 | SCRIBE3\_CODEX\_THICKEN\_GATE=0绕过门闸时无审计日志 | P2 | 5 | decision: P2 绕过门闸审计本轮未加 | decision: P2 绕过门闸审计本轮未加 |
| MAT-01 | emotion\_module双重注入导致token浪费 | P0 | 3 | done | material_recall exclude emotion_module |
| MAT-02 | motif\_instance evidence无可溯源验证 | P0 | 5 | done | grep_back_verify motif evidence |
| MAT-03 | 删除codex实体不清理material.about\_entities | P0 | 1 | done | _cleanup_record_refs 清 about_entities |
| MAT-04 | delete\_material不发cache invalidation | P0 | 0 | done | delete_material invalidation |
| MAT-05 | origin=manual/session\_clip路径缺build\_material\_edges | P1 | 5 | done | add_material 后 build_material_edges |
| MAT-06 | material\_reference溯源语义错误 | P1 | 5 | done | material_reference.ref_kind injection vs inspiration |
| MAT-07 | 素材搜索无语义检索（仅BM25文本匹配） | P1 | 5 | done | 素材搜索 mode=hybrid 二次排序 |
| MAT-08 | 素材kind分类无层级/无自定义扩展 | P2 | 5 | decision: P2 自定义 kind 远期 | decision: P2 自定义 kind 远期 |
| ATL-01 | 归档角色泄入写作prompt | P0 | 0 | done | characters() archived 过滤 |
| ATL-02 | 势力删除无lifecycle保护 | P0 | 1 | done | 势力删除 cleanup |
| ATL-03 | 正典Apply不触发限知桥同步 | P0 | 1 | done | apply 后 sync 限知桥 |
| ATL-04 | 因果根编辑端点前端零接触 | P0 | 3 | done | patchEventCausalRoot + CausalRootEditor |
| ATL-05 | 角色删除不级联清理命题 | P1 | 1 | done | DELETE proposition on cleanup |
| ATL-06 | 势力known\_members与角色实体无动态同步 | P1 | 5 | done | known_members 按在册角色动态过滤 |
| ATL-07 | 物品state\_history无时间线展示 | P1 | 5 | done | CodexView ItemStateHistory 时间线 |
| ATL-08 | 关系图无权重/无方向标注 | P1 | 5 | done | 图谱边 weight + 箭头方向 |
| ATL-09 | 事件无批量导入/导出 | P2 | 5 | decision: P2 事件批量导入远期 | decision: P2 事件批量导入远期 |
| PRM-01 | Overdue无硬闸阻止力 | P0 | 0 | done | overdue 硬闸 |
| PRM-02 | 并发写入安全缺失 | P0 | 0 | done | advance CAS + touch 去重 + unique 迁移 |
| PRM-03 | Resolution校验绕过口 | P1 | 5 | done | plant_promise strict |
| PRM-04 | Canon advance不产生fact/proposition | P1 | 5 | done | advance 后写兑现命题 |
| PRM-05 | 伏笔超期无主动告警链路 | P1 | 5 | done | alerts.emit_alert 可挂 overdue |
| PRM-06 | Seed→Promise衔接丢失上下文 | P1 | 5 | done | promote_seed 带走 reason/evidence/clues |
| PRM-07 | 伏笔-角色绑定缺失 | P1 | 5 | done | promise.involved_characters |
| PRM-08 | 伏笔间依赖网络缺失 | P2 | 5 | decision: P2 伏笔依赖网远期 | decision: P2 伏笔依赖网远期 |
| PRM-09 | Legacy数据tier可能被误判 | P2 | 5 | decision: P2 legacy tier 一次性迁移远期 | decision: P2 legacy tier 一次性迁移远期 |
| MOT-01 | echo\_terms未参与ingest反哺链路 | P1 | 3 | done | echo_terms 进抽取嘱咐 |
| MOT-02 | phase无自动推进逻辑 | P1 | 3 | done | schedule_motifs 按触碰推进 phase |
| MOT-03 | tier/scope后端调度完全忽略 | P1 | 3 | done | schedule_motifs 按 tier 调 gap |
| MOT-04 | motif\_instance evidence无溯源验证 | P1 | 3 | done | motif evidence 校验 |
| MOT-05 | 母题回响无"过度重复"阈值告警 | P1 | 3 | done | motif_overheat_advisory |
| MOT-06 | 创建闭环无"降级自动填占位"路径 | P2 | 5 | decision: P2 拒绝后降级占位远期 | decision: P2 拒绝后降级占位远期 |
| MOT-07 | 过热抑制依赖LLM遵循指令无硬保证 | P2 | 5 | decision: P2 过热硬保证本轮走 advisory | decision: P2 过热硬保证本轮走 advisory |
| TML-01 | 时间线不订阅SSE s3-live事件 | P2 | 1 | done | TimelineView s3-live |
| TML-02 | 因果弧线SVG未实现 | P2 | 3 | decision: P2 SVG 因果弧远期 | decision: P2 SVG 因果弧远期 |
| TML-03 | 时间线选中伏笔后无操作入口 | P2 | 5 | decision: P2 时间线伏笔兑现按钮远期 | decision: P2 时间线伏笔兑现按钮远期 |
| TML-04 | 记忆否认未与canon事实交叉 | P2 | 5 | decision: P2 记忆否认交叉远期 | decision: P2 记忆否认交叉远期 |
| TML-05 | 全表查无WHERE（story轴模式） | P2 | 5 | decision: P2 story 轴 WHERE 优化远期 | decision: P2 story 轴 WHERE 优化远期 |
| TML-06 | 缺少"跳到第N章"直达能力 | P2 | 5 | decision: P2 跳到第 N 章输入框远期 | decision: P2 跳到第 N 章输入框远期 |
| TML-07 | 选中联动不传播因果链/弧光 | P2 | 3 | decision: P2 选中联动因果远期 | decision: P2 选中联动因果远期 |
| TML-08 | faction.timeline字段前端零消费 | P3 | 5 | decision: P3 faction.timeline 标 deferred | decision: P3 faction.timeline 标 deferred |
| JNY-01 | Pilot可绕过旅程门槛直接开写 | P1 | 3 | done | SCRIBE3_JOURNEY_PRECHECK 409 |
| JNY-02 | 质量熔断状态对作者不可见 | P1 | 3 | done | snapshot quality_stalled |
| JNY-03 | ledger站为空壳，全书完成后胶囊消失 | P1 | 3 | done | 全书定稿后账本站点亮，胶囊恭喜完成 |
| JNY-04 | 8个pilot状态压缩为5个，需审批状态被隐藏 | P2 | 5 | decision: P2 审批态视觉差远期 | decision: P2 审批态视觉差远期 |
| JNY-05 | 前三站"继续"依赖NLU匹配精准度弱 | P2 | 5 | decision: P2 domainHint 映射远期 | decision: P2 domainHint 映射远期 |
| JNY-06 | WorkflowCapsule轮询无backoff，消失无解释 | P2 | 5 | decision: P2 胶囊 backoff 远期 | decision: P2 胶囊 backoff 远期 |
| JNY-07 | 章被打回无事件通知 | P2 | 5 | decision: P2 打回 toast 远期 | decision: P2 打回 toast 远期 |
| JNY-08 | 停滞检测无分级 | P2 | 5 | decision: P2 停滞分级远期 | decision: P2 停滞分级远期 |
| DIR-01 | Proposal审批缺乏持久化 | P0 | 2 | done | execute=false 走 store 持久化，GET /orchestration/proposal/{id} 可取 |
| DIR-02 | 多Worker部署下同章双跑竞态 | P0 | 2 | done | pilot_step chapter_lock |
| DIR-03 | Frozen Artifact丢失致Pilot不可自愈卡死 | P0 | 4 | done | PilotApproveReq.force_rollback/to_state；reset-step 改状态并清冻产物 |
| DIR-04 | SSE /live端点零测试覆盖 | P0 | 4 | done | ASGI /live 三事件形状 + _normalize_live_note CREATE/UPDATE/DELETE |
| DIR-05 | Blocker双向闭环零测试 | P0 | 4 | done | overdue 硬闸：超阈 409，兑现后解除 |
| DIR-06 | s3-chapter-phase-hint事件无前端消费 | P1 | 1 | done | s3-chapter-phase-hint handler |
| DIR-07 | faction/item/term/world\_rule四表SSE无设定库监听 | P1 | 1 | done | CodexDirectory s3-live |
| DIR-08 | needs\_human收件箱无dismiss/消除出口 | P1 | 3 | done | POST /inbox/dismiss/{id} |
| DIR-09 | lesson/pulse/digest收件箱无标记完成 | P1 | 3 | done | dismiss 覆盖 lesson/pulse 等同 id |
| DIR-10 | /live SSE断连后重连无补偿 | P1 | 3 | done | EventSource onopen 全量 pull |
| DIR-11 | pulse\_decision项无dismiss机制 | P1 | 3 | done | pulse 项可 dismiss |
| DIR-12 | letter诊断结果不注入下一章prompt | P1 | 3 | done | build_revision_letter 进 build_ctx 并写入生成嘱咐 |
| DIR-13 | scene\_grid信息不注入生成prompt | P1 | 3 | done | experience.scene_grid 进 build_ctx 并写入生成嘱咐 |
| DIR-14 | MAX\_QUALITY\_ROUNDS全失败后草稿未落库 | P1 | 5 | done | 8 轮熔断保留最佳候选 best_kept |
| DIR-15 | checked态下full\_check永远blocking无法修复 | P1 | 5 | done | force_rollback 解 checked 卡死 |
| DIR-16 | Proposal reject无审计日志 | P2 | 5 | decision: P2 reject 审计走现有 approval_audit | decision: P2 reject 审计走现有 approval_audit |
| DIR-17 | idea路由LLM失败静默降级为unclear | P2 | 5 | decision: P2 idea 降级 toast 远期 | decision: P2 idea 降级 toast 远期 |
| DIR-18 | live onGiveUp后永久停止无探活恢复 | P2 | 5 | done | onGiveUp 30s 探活重连 |
| MAN-01 | chapter\_version表无容量上限/无清理策略/无分页 | P0 | 0 | done | list LIMIT + prune 保留策略 |
| MAN-02 | 无并发编辑冲突检测（last-write-wins） | P1 | 2 | done | expected_version → 409 |
| MAN-03 | 永久删除未级联清理canon\_candidate | P1 | 1 | done | delete_chapter_permanent 清 canon_candidate |
| MAN-04 | 归档未处理未决正典候选 | P1 | 1 | done | archive 把 pending candidate dismissed |
| MAN-05 | 大纲/节拍/演绎无版本记录 | P2 | 5 | decision: P2 大纲节拍版本快照远期 | decision: P2 大纲节拍版本快照远期 |
| MAN-06 | chatWrite SSE无超时且无重连 | P2 | 5 | decision: P2 chatWrite 超时远期 | decision: P2 chatWrite 超时远期 |
| MAN-07 | Ingest Worker无自动重试 | P2 | 5 | decision: P2 ingest worker 重试远期 | decision: P2 ingest worker 重试远期 |
| MAN-08 | postCheck结果不落库且无hash失效检查 | P2 | 5 | decision: P2 postCheck hash 过期远期 | decision: P2 postCheck hash 过期远期 |
| MAN-09 | 选择环终选来源未持久化 | P2 | 5 | decision: P2 选择环来源字段远期 | decision: P2 选择环来源字段远期 |
| MAN-10 | 切章自动保存fire-and-forget无重试 | P2 | 5 | decision: P2 切章 stash 重试远期 | decision: P2 切章 stash 重试远期 |
| MAN-11 | 章节重排乐观更新无回滚 | P2 | 5 | decision: P2 重排拒绝回滚远期 | decision: P2 重排拒绝回滚远期 |
| DED-01 | chat\_write路径无章节锁 | P0 | 0 | done | chat_write 章节锁 |
| DED-02 | Playbook run\_stage无内置章节锁 | P0 | 0 | done | run_stage 章节锁 |
| DED-03 | ingest apply\_delta无事务保护 | P0 | 2 | done | purge 在守卫内；开机/连库扫检查点并用留下的稿子重放 |
| DED-04 | apply\_change\_pack无回滚机制 | P0 | 2 | done | patch 恢复 before；add 才整条删 |
| DED-05 | leak\_markers依赖人工标注 | P0 | 1 | done | auto_generate_leak_markers |
| DED-06 | 卷纲→章纲无自动细化闭环 | P0 | 0 | done | empty_synopsis 硬阻断 |
| DED-07 | build\_ctx与ContextAssembler两套并行上下文系统 | P0 | 2 | done | ContextSnapshotCache |
| DED-08 | chapter\_state抽取失败无自动恢复 | P0 | 4 | done | 抽取失败冻降级章末态，下章 prev_state 能接 |
| DED-09 | Discussion路径无质量检查 | P1 | 5 | done | discussion quality_flags 对照已立的人/规矩 |
| DED-10 | \_quality\_loop计数器逻辑缺陷 | P1 | 5 | done | ParseError 递增 quality |
| DED-11 | advisory分支正文悬空 | P1 | 3 | done | advisory 72h + POST /chapters/{seq}/accept-advisory |
| DED-12 | 三套质量体系无统一聚合视图 | P1 | 4 | done | health 读 playbook/post_analysis/chapter_review 三套真结果 |
| DED-13 | canon\_candidate无自动过期/清理 | P1 | 4 | done | pending candidate 30 天 expired |
| DED-14 | fact supersede无跨章广播 | P1 | 4 | done | supersede_fact 后 _emit_cache_invalidation fact+proposition |
| DED-15 | build\_ctx soft\_fail静默降级 | P1 | 4 | done | build_ctx guide_fail 已记 degraded slots |
| DED-16 | volume\_ledger flag默认关 | P1 | 4 | decision: P1 volume_ledger 旗默认已有跳过日志 | decision: P1 volume_ledger 旗默认已有跳过日志 |
| DED-17 | recall\_service图通道默认关闭 | P1 | 3 | done | GRAPH_RELATION_RECALL 默认已开 |
| DED-18 | draft冻结成功但state失败时上层误判 | P1 | 4 | done | 草稿已冻时 state_ok=False，ok 仍为 True |
| DED-19 | craft\_skills无自动选择 | P1 | 3 | done | craft_skills 强制注入限知视角/知情差 |
| DED-20 | scene\_grid诊断注入路径不完整 | P1 | 3 | done | scene_grid 进 build_ctx |
| DED-21 | LLM抽取失败静默降级无告警 | P2 | 5 | decision: P2 抽取失败告警走 alerts | decision: P2 抽取失败告警走 alerts |
| DED-22 | ingest grep\_back\_verify标注"未明确"仍写入 | P2 | 5 | decision: P2 未验证事实标 annotated 已有，不计入 motif heat | decision: P2 未验证事实标 annotated 已有，不计入 motif heat |
| DED-23 | chat\_write与Playbook路径质量标准不同 | P2 | 5 | decision: P2 对话式产出标注远期 | decision: P2 对话式产出标注远期 |
| DED-24 | recent\_duty\_summary只看3章硬编码 | P2 | 5 | decision: P2 recent_duty 窗口远期 | decision: P2 recent_duty 窗口远期 |
| CRS-01 | 质量闭环统一聚合 |  | 4 | done | aggregate_chapter_health |
| CRS-02 | 正典回写→全局同步链 |  | 1 | done | after_canon_apply 三同步 |
| CRS-03 | 记忆召回统一中枢完善 |  | 3 | done | 图通道默认开 + emotion 去重 |
| CRS-04 | 经验压力→写路径注入闭环 |  | 3 | done | letter/scene_grid 进写上下文 |
| CRS-05 | 限知门控全链路加固 |  | 5 | done | leak_markers + role bridge 默认开 + apply sync |
| CRS-06 | 级联删除统一治理 |  | 1 | done | 级联 cleanup 统一 |
| CRS-07 | SSE实时更新全面接入 |  | 5 | done | Insight/Timeline/Codex/Gateway live |
| T13-01 | T04红测试未修复（裸入库） |  | 0 | done | fake_stream hermes 名 |
| T13-02 | xfail-ledger标"已修复"与事实不符 |  | 0 | done | xfail-ledger 已按源码改为已修复 |
| T13-03 | round13-debts声称"无代码遗留" |  | 0 | done | round13-debts 已登记 T04 |
| T13-04 | shadow\_equal三层比对缺负面用例 |  | 4 | done | shadow_equal 删段/换序必须 False |
| T13-05 | test\_recall\_unity白名单维护风险 |  | 4 | decision: P1 白名单动态发现远期 | decision: P1 白名单动态发现远期 |
| T13-06 | deploy\_check.sh macOS不可用 |  | 4 | done | deploy_check command -v systemd-analyze |
| T13-07 | test\_epistemic\_100用inspect.getsource源码断言 |  | 5 | decision: P2 inspect 源码断言保留 | decision: P2 inspect 源码断言保留 |
| T13-08 | budget\_overrun阈值硬编码1.05 |  | 5 | decision: P2 budget 1.05 阈值远期 | decision: P2 budget 1.05 阈值远期 |

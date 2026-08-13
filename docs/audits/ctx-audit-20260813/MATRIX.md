# ctx-audit MATRIX · 全库存
> W1 分数沿用 `W1-SCORES.md` / 卷宗机读表；W2–W4 新卷宗。现网硬顶 48k。

| 波 | 单元 | P | Q | R | B | O | 最优改造（一句） |
|----|------|---|---|---|---|---|------------------|
| W1 | deduction_final | 4 | 3 | 2 | 4 | 2 | 焦点优先压缩 + 整包硬帽 + 单段 push |
| W1 | drama_contract | 4 | 2 | 3 | 3 | 4 | 400 字先砍 MRU 套话、保代价/冲突 |
| W1 | drama_vacuum | 3 | 3 | 4 | 3 | 3 | 触发改「无 goal∧conflict」+ 可操作短句 |
| W1 | event_drive | 3 | 3 | 4 | 3 | 3 | assemble 单点判定 + empty_event_drive 可观测 |
| W1 | final_reminder | 5 | 2 | 4 | 2 | 4 | 默认 CORE 短核，文体按书覆盖 |
| W1 | focalizer | 4 | 3 | 4 | 3 | 2 | 独立 `_push("focalizer")` |
| W1 | narrative_contract | 2 | 4 | 4 | 2 | 3 | store 按 narrative_drive 同构打通读写 |
| W1 | outline | 4 | 3 | 4 | 3 | 4 | 半裁改为保拍砍纲 |
| W1 | scene_truth_proj | 4 | 4 | 4 | 3 | 3 | budget_report 标明真相源路径 |
| W1 | secret_guard | 4 | 3 | 5 | 3 | 2 | 独立 `_push("secret_guard")` + 揭示字段覆盖 |
| W2 | canonical | 4 | 4 | 5 | 4 | 4 | codex 与 canonical 做结构化差集（已在 codex 的角色/规则勿再以 fact 行复读）。 |
| W2 | focus | 4 | 3 | 4 | 3 | 3 | 保持指针不去重失败；budget_report 增加 focus_has_outline_pointer 布尔。 |
| W2 | global | 4 | 4 | 4 | 3 | 3 | 渲染标签改为「作品意图」对齐产品文案；strip 红线时留「红线已按实验剥离」一行以免像没配置。 |
| W2 | procedural | 4 | 3 | 3 | 3 | 3 | assemble 对 craft 段与 procedural 做 compact 去重（已有 phase_role 去重可仿）。 |
| W2 | provenance | 5 | 2 | 5 | 2 | 5 | 维持 0 额度；检查器读 envelope.omitted / trace 而非 prompt。 |
| W2 | recent | 3 | 3 | 3 | 3 | 3 | fabric 开时保证 _build_write_retrieval_query 非空（v1 已有）；观测 recent_item_count。 |
| W2 | reference | 4 | 4 | 4 | 3 | 3 | 保持免责门；材料空时 omitted 记 no_materials 以便检查器。 |
| W2 | uncertainty | 4 | 3 | 4 | 3 | 3 | 保留 superseded 行优先于低信心闲聊（allocate 时先留 reason=superseded）。 |
| W3 | brief_must | 3 | 3 | 3 | 3 | 3 | must 节只保留 outline/contract 没有的键。 |
| W3 | codex | 4 | 3 | 4 | 3 | 3 | 与 canonical 差集后再 cap；观测 codex_chars。 |
| W3 | event_drive_hook | 4 | 3 | 4 | 3 | 3 | contract 对象只判一次并传入 helper（与 W1 event_drive 同一改造）。 |
| W3 | pressure_drive | 3 | 3 | 3 | 3 | 3 | 差集失败记 soft_fail 并仍尝试差集空键；禁止再渲染与 drama 相同的 goal 句。 |
| W3 | story_causal | 5 | 5 | 5 | 5 | 5 | 已接线：`collect_story_fuel_segments` supplemental；查询失败 `empty_story_causal`。 |
| W3 | story_ember | 5 | 5 | 5 | 5 | 5 | 已接线：`prior_consequences` → `_push("story_ember","supplemental")`；不进 L0_NEVER_CUT。 |
| W3 | story_recall | 5 | 5 | 5 | 5 | 5 | 已接线：hybrid_recall 掩码后注入；T1_fuel 先裁 recall。 |
| W4 | anti_slop | 4 | 2 | 4 | 2 | 2 | 三处 slop 收成一处短核。 |
| W4 | author_prefs | 3 | 3 | 3 | 3 | 3 | 与 procedural 偏好去重。 |
| W4 | avoid | 4 | 3 | 4 | 3 | 3 | 默认 omit 独立段（已有旗）。 |
| W4 | continue_snapshot | 3 | 3 | 3 | 3 | 3 | 独立 push；skip 原因进 report。 |
| W4 | craft | 4 | 3 | 3 | 3 | 3 | 与 procedural compact 去重。 |
| W4 | craft_skills_index | 4 | 3 | 3 | 3 | 2 | 保持索引；独立 push。 |
| W4 | discourse_soft | 4 | 3 | 3 | 3 | 3 | 与 CORE 尾注差集。 |
| W4 | envelope | 4 | 4 | 4 | 3 | 4 | budget_report 必带 envelope_block_lengths 八键（registry density 已支持入参）。 |
| W4 | identity | 4 | 3 | 4 | 3 | 2 | 独立 push 名 identity 以便 NEVER 真按名裁。 |
| W4 | material_recall | 3 | 3 | 3 | 3 | 3 | 与 reference 块去重标题。 |
| W4 | phase_role | 4 | 3 | 4 | 3 | 3 | 保持去重；空 phase 不 push。 |
| W4 | prefix | 3 | 3 | 3 | 3 | 2 | 拆出已在 NEVER 的旁路为独立 _push（与 W1 secret_guard/focalizer 同一方向），prefix 只留身份+协议+anti_slop。 |
| W4 | purpose | 3 | 3 | 3 | 3 | 3 | 若 global 已有意图则 purpose 只留「本章目的」差集。 |
| W4 | reference_craft | 3 | 3 | 3 | 3 | 3 | 合并一次 push + 条数帽 2。 |
| W4 | request_constraint | 4 | 4 | 4 | 4 | 3 | 空 extra 不 push（已然）。 |
| W4 | request_position | 5 | 2 | 5 | 3 | 2 | 可留在 prefix 一行；不必独立段。本卷宗改造=维持一行。 |
| W4 | revelation_discipline | 4 | 3 | 4 | 3 | 3 | 与 CORE 尾注差集，只保留尾注没有的一句。 |
| W4 | revision | 4 | 3 | 4 | 3 | 2 | 非修订请求不注入。 |
| W4 | seed_words | 4 | 3 | 4 | 3 | 3 | 空 soak 不 push。 |
| W4 | sincerity | 4 | 2 | 4 | 2 | 3 | 并入 anti_slop 或删独立段，只留一条。 |
| W4 | story_move | 4 | 4 | 4 | 4 | 4 | 保持零字节默认；观测 plan_missing 原因。 |
| W4 | storyline_polish | 3 | 3 | 3 | 3 | 3 | 空 meta 不 push；观测 skip 原因。 |
| W4 | structure_diversity | 4 | 3 | 3 | 3 | 3 | 保持短纪律；独立 _push 名以便 density。 |
| W4 | tool_scope | 4 | 3 | 4 | 3 | 2 | 独立 push 当 with_tools。 |
| W4 | voice_anchor | 4 | 4 | 4 | 3 | 3 | 无 profile 时一行「未登记声口」而非空。 |
| W4 | volume_intro | 4 | 3 | 4 | 3 | 3 | 保持 compact；空不 push。 |
| W4 | write_protocol | 4 | 3 | 4 | 3 | 2 | 与 CORE 尾注差集。 |

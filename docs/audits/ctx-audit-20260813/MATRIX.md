# ctx-audit MATRIX · 全库存
> W1 分数沿用 `W1-SCORES.md` / 卷宗机读表；W2–W4 新卷宗。代码常量硬顶 48k；**demo 已 env 全站升 96k**（空白名单）。禁止为刷分再加大常量。

| 波 | 单元 | P | Q | R | B | O | 最优改造（一句） |
|----|------|---|---|---|---|---|------------------|
| W1 | deduction_final | 5 | 5 | 5 | 5 | 5 | 已落地：焦点优先压缩 + 整包硬帽 + 单段 push |
| W1 | drama_contract | 5 | 5 | 5 | 5 | 5 | 已落地：拍级走法保冲突/代价，去掉 MRU |
| W1 | drama_vacuum | 5 | 5 | 5 | 5 | 5 | 已落地：仅无 goal∧conflict；短句；剔出戏核 |
| W1 | event_drive | 5 | 5 | 5 | 5 | 5 | 已落地：单点判定 + 短标题「本章冲突时钟」 |
| W1 | final_reminder | 5 | 5 | 5 | 5 | 5 | 已落地：默认短核；PROSE_STYLE 可覆盖 |
| W1 | focalizer | 5 | 5 | 5 | 5 | 5 | 已落地：独立 `_push` + 全知横幅点明 secret_guard |
| W1 | narrative_contract | 5 | 5 | 5 | 5 | 5 | 已落地：store 同构读写 + 场面头 push + injected/skip 可查 |
| W1 | outline | 5 | 5 | 5 | 5 | 5 | 已落地：半裁保拍 + 无预算不喊字数预算 |
| W1 | scene_truth_proj | 5 | 5 | 5 | 5 | 5 | 已落地：scene_truth_source=proj\|deduction_final\|none |
| W1 | secret_guard | 5 | 5 | 5 | 5 | 5 | 已落地：独立 `_push` + `reveal_secret_ids` 覆盖 |
| W2 | canonical | 5 | 5 | 5 | 5 | 5 | 已落地：canonical 相对 codex 整行差集 |
| W2 | focus | 5 | 5 | 5 | 5 | 5 | 已落地：outline 指针 + focus_has_outline_pointer |
| W2 | global | 5 | 5 | 5 | 5 | 5 | 已落地：作品意图标签 + strip 明示行 |
| W2 | procedural | 5 | 5 | 5 | 5 | 5 | 已落地：相对 craft compact 去重；omitted+budget_report 可查 |
| W2 | provenance | 5 | 2 | 5 | 2 | 5 | 维持 0 额度；检查器读 envelope.omitted / trace 而非 prompt。 |
| W2 | recent | 5 | 5 | 5 | 5 | 5 | 已落地：fabric 空 query 兜底 + recent_item_count |
| W2 | reference | 5 | 5 | 5 | 5 | 5 | 已落地：空素材 omitted.no_materials |
| W2 | uncertainty | 5 | 5 | 5 | 5 | 5 | 已落地：superseded 优先于待确认闲聊 |
| W3 | brief_must | 5 | 5 | 5 | 5 | 5 | 已落地：must 条相对大纲/场面合同差集 |
| W3 | codex | 5 | 5 | 5 | 5 | 5 | 已落地：与 envelope 差集后再 cap；codex_chars |
| W3 | event_drive_hook | 5 | 5 | 5 | 5 | 5 | 已落地：与 event_drive 同一谓词；续势钩 supplemental |
| W3 | pressure_drive | 5 | 5 | 5 | 5 | 5 | 已落地：空键仍差集 + 禁复述 drama goal |
| W3 | story_causal | 5 | 5 | 5 | 5 | 5 | 已接线：`collect_story_fuel_segments` supplemental；查询失败 `empty_story_causal`。 |
| W3 | story_ember | 5 | 5 | 5 | 5 | 5 | 已接线：`prior_consequences` → `_push("story_ember","supplemental")`；不进 L0_NEVER_CUT。 |
| W3 | story_recall | 5 | 5 | 5 | 5 | 5 | 已接线：hybrid_recall 掩码后注入；T1_fuel 先裁 recall。 |
| W4 | anti_slop | 5 | 5 | 5 | 5 | 5 | 已落地：与 sincerity 收成 prefix 短核 |
| W4 | author_prefs | 5 | 5 | 5 | 5 | 5 | 已落地：与 envelope 整行去重；空则 empty_author_prefs |
| W4 | avoid | 5 | 5 | 5 | 5 | 5 | 已落地：默认 omit 独立段；skip_reason 可查 |
| W4 | continue_snapshot | 5 | 5 | 5 | 5 | 5 | 已独立 _push；空则 continue_snapshot_skip |
| W4 | craft | 5 | 5 | 5 | 5 | 5 | 已落地：与 envelope procedural 整行去重 |
| W4 | craft_skills_index | 5 | 5 | 5 | 5 | 5 | 已独立 _push（仅 with_tools） |
| W4 | discourse_soft | 5 | 5 | 5 | 5 | 5 | 已落地：与 final_reminder CORE 整行差集 |
| W4 | envelope | 5 | 5 | 5 | 5 | 5 | 已落地：budget_report 八键 envelope_block_lengths |
| W4 | identity | 5 | 5 | 5 | 5 | 5 | 已落地：独立 `_push("identity")` |
| W4 | material_recall | 5 | 5 | 5 | 5 | 5 | 已落地：与 envelope reference 去重标题 |
| W4 | phase_role | 5 | 5 | 5 | 5 | 5 | 已落地：去重 + 空不 push；skip 可查 |
| W4 | prefix | 5 | 5 | 5 | 5 | 5 | 已落地：`prefix` = anti_slop 短核 + 当前第 N 章；`identity` / `write_protocol` 已独立 `_push` |
| W4 | purpose | 5 | 5 | 5 | 5 | 5 | 已落地：global 有作品意图（兼容旧「北极星」差集）则只留本章目的 |
| W4 | reference_craft | 5 | 5 | 5 | 5 | 5 | 已落地：最多 2 条、单次 push |
| W4 | request_constraint | 5 | 5 | 5 | 5 | 5 | 已落地：空 extra 不 push；skip 可查 |
| W4 | request_position | 5 | 2 | 5 | 3 | 2 | 可留在 prefix 一行；不必独立段。本卷宗改造=维持一行。 |
| W4 | revelation_discipline | 5 | 5 | 5 | 5 | 5 | 已落地：相对 CORE 只留一句差集 |
| W4 | revision | 5 | 5 | 5 | 5 | 5 | 已落地：非修订请求不注入；skip_reason 可查 |
| W4 | seed_words | 5 | 5 | 5 | 5 | 5 | 已落地：空 soak 不 push；skip 可查 |
| W4 | sincerity | 5 | 5 | 5 | 5 | 5 | 已并入 anti_slop 短核，不再独立段 |
| W4 | story_move | 4 | 4 | 4 | 4 | 4 | 保持零字节默认；观测 plan_missing 原因。 |
| W4 | storyline_polish | 5 | 5 | 5 | 5 | 5 | 已落地：空 meta 不 push，skip_reason 可查 |
| W4 | structure_diversity | 5 | 5 | 5 | 5 | 5 | 已独立 _push，不再吞进 prefix |
| W4 | tool_scope | 5 | 5 | 5 | 5 | 5 | 已独立 _push（仅 with_tools） |
| W4 | voice_anchor | 5 | 5 | 5 | 5 | 5 | 已落地：无 profile 写「未登记声口」 |
| W4 | volume_intro | 5 | 5 | 5 | 5 | 5 | 已落地：compact + 空不 push |
| W4 | write_protocol | 5 | 5 | 5 | 5 | 5 | 已落地：独立段 + 与 CORE 整行差集 |

const MUTATION_WORDS = /(新增|添加|登记|记录|补录|写入|落库|建立|创建|更新|修改|改成|删除|删卷|归档|恢复|关闭|推进|兑现|回收|标记|更正|重排|排序)/
const WORLD_OBJECT_WORDS = /(设定|事实|命题|伏笔|承诺|母题|角色|人物|势力|物件|物品|术语|世界规则|关系|弧光|里程碑|声线|声音|章节|分卷|卷纲|卷|北极星|意图|红线|读者感受|情感弧|外貌|外观|档案)/
// 「推进人物关系」「写本章正文」是正常的写作要求，不是授权主编改写世界状态。
// 先排除散文生成，避免词面上的“推进 + 人物”误路由到需要审批的 Hermes Run。
// 但「写入/登记 北极星/设定」必须保留走 Run，即使句中出现「场景」等词——先判写工具意图。
const PROSE_GENERATION_WORDS = /(正文|草稿|段落|续写|改写|润色|扩写|缩写|写本章|写整章|写一章|完整正文|文风|镜头)/
// 生产 chief-seed / MCP 工具名 / 强制世界写话术 — 一律走 Hermes Run(可待批),禁止掉进无工具 stream
const WORLD_WRITE_FORCE = /(s3_[a-z_]+|北极星意图|写入落库|登记\/更新本书北极星|更正角色|更新角色|提交写入提案|供我批准|需我审批|写入提案)/

/**
 * @deprecated 发送主路径请用 orchestrateBeforeSend（/orchestration/resolve）。
 * 本函数仅作后端不可达时的弱回退 + 单测兼容，不再是唯一分流真理。
 */
export function shouldUseHermesRun(text) {
  const value = String(text || '').trim()
  if (!value || value.startsWith('#想法')) return false
  if (WORLD_WRITE_FORCE.test(value)) return true
  if (PROSE_GENERATION_WORDS.test(value)) return false
  return MUTATION_WORDS.test(value) && WORLD_OBJECT_WORDS.test(value)
}

/** 强制种子话术仍须命中写通道（回归护栏） */
export function isWorldWriteForceSeed(text) {
  return WORLD_WRITE_FORCE.test(String(text || '').trim())
}

export function hermesRunInstructions({ chapter, phase, focalizer } = {}) {
  const parts = [
    '这是 scribe3 会改世界状态的主编任务。',
    '必须先用只读 s3_ 工具核实当前书内事实;需要写入时使用 scribe3_write 工具,等待作者审批。',
    '书级北极星用 s3_get_intent 核实后 s3_set_intent 写入;角色字段更正用 s3_patch_character。',
    '结构运维:建卷 s3_add_volume、建章 s3_add_chapter、重排 s3_reorder_chapters、删卷 s3_delete_volume、章脚手架 s3_patch_chapter_plan。',
    '母题(开书强制):设定圣经阶段必须用 s3_add_motif(name, theme, echoes, unfolding) 立至少 3 条母题；禁止零母题开写。写作注入与正文反哺只匹配已立母题，不会从正文自动新建。',
    '素材是作者直管的非正典参考记忆，只读召回和引用，不得写入或删改。',
    '作者点名工具时必须调用该工具并等待审批,禁止只口头答应不调用。',
    '不要把剧情事实写入 Hermes memory 或 skill;剧情事实只能进 scribe3 SurrealDB。',
  ]
  if (chapter != null) parts.push(`当前章:${chapter}`)
  if (phase) parts.push(`当前阶段:${phase}`)
  if (focalizer) parts.push(`当前视角:${focalizer}`)
  return parts.join('\n')
}

/**
 * world_write Run 指令单源：base + resolve.instruction_suffix。
 * 即使 phase 被清空，后缀仍须注入（H1 KD-CM-13）。
 */
export function assembleWorldWriteInstructions({
  chapter,
  focalizer = '',
  instructionSuffix = '',
  phase = '',
} = {}) {
  // world_write 故意不传业务 phase（与 ChiefDock 一致）；后缀承载域纪律
  const base = hermesRunInstructions({
    chapter,
    phase: '',
    focalizer,
  })
  const suf = String(instructionSuffix || '').trim()
  if (!suf) return base
  return `${base}\n\n## 本域纪律\n${suf}`
}

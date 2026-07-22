const MUTATION_WORDS = /(新增|添加|登记|记录|补录|写入|落库|建立|创建|更新|修改|改成|删除|归档|恢复|关闭|推进|兑现|回收|标记|更正)/
const WORLD_OBJECT_WORDS = /(设定|事实|命题|伏笔|承诺|母题|角色|人物|势力|物件|物品|术语|世界规则|素材|关系|弧光|里程碑|声线|声音|章节|分卷|卷纲|北极星|意图|红线|读者感受|情感弧|外貌|外观|档案)/
// 「推进人物关系」「写本章正文」是正常的写作要求，不是授权主编改写世界状态。
// 先排除散文生成，避免词面上的“推进 + 人物”误路由到需要审批的 Hermes Run。
// 但「写入/登记 北极星/设定」必须保留走 Run，即使句中出现「场景」等词——先判写工具意图。
const PROSE_GENERATION_WORDS = /(正文|草稿|段落|续写|改写|润色|扩写|缩写|写本章|写整章|写一章|完整正文|文风|镜头)/
const WORLD_WRITE_FORCE = /(s3_set_intent|s3_patch_character|北极星意图|写入落库|登记\/更新本书北极星|更正角色|更新角色)/

export function shouldUseHermesRun(text) {
  const value = String(text || '').trim()
  if (!value || value.startsWith('#想法')) return false
  if (WORLD_WRITE_FORCE.test(value)) return true
  if (PROSE_GENERATION_WORDS.test(value)) return false
  return MUTATION_WORDS.test(value) && WORLD_OBJECT_WORDS.test(value)
}

export function hermesRunInstructions({ chapter, phase, focalizer } = {}) {
  const parts = [
    '这是 scribe3 会改世界状态的主编任务。',
    '必须先用只读 s3_ 工具核实当前书内事实;需要写入时使用 scribe3_write 工具,等待作者审批。',
    '书级北极星用 s3_get_intent 核实后 s3_set_intent 写入;角色字段更正用 s3_patch_character。',
    '不要把剧情事实写入 Hermes memory 或 skill;剧情事实只能进 scribe3 SurrealDB。',
  ]
  if (chapter != null) parts.push(`当前章:${chapter}`)
  if (phase) parts.push(`当前阶段:${phase}`)
  if (focalizer) parts.push(`当前视角:${focalizer}`)
  return parts.join('\n')
}

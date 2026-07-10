const MUTATION_WORDS = /(新增|添加|登记|记录|补录|写入|落库|建立|创建|更新|修改|改成|删除|归档|恢复|关闭|推进|兑现|回收|标记)/
const WORLD_OBJECT_WORDS = /(设定|事实|命题|伏笔|承诺|母题|角色|人物|势力|物件|物品|术语|世界规则|素材|关系|弧光|里程碑|声线|声音|章节|分卷|卷纲)/

export function shouldUseHermesRun(text) {
  const value = String(text || '').trim()
  if (!value || value.startsWith('#想法')) return false
  return MUTATION_WORDS.test(value) && WORLD_OBJECT_WORDS.test(value)
}

export function hermesRunInstructions({ chapter, phase, focalizer } = {}) {
  const parts = [
    '这是 scribe3 会改世界状态的主编任务。',
    '必须先用只读 s3_ 工具核实当前书内事实;需要写入时使用 scribe3_write 工具,等待作者审批。',
    '不要把剧情事实写入 Hermes memory 或 skill;剧情事实只能进 scribe3 SurrealDB。',
  ]
  if (chapter != null) parts.push(`当前章:${chapter}`)
  if (phase) parts.push(`当前阶段:${phase}`)
  if (focalizer) parts.push(`当前视角:${focalizer}`)
  return parts.join('\n')
}

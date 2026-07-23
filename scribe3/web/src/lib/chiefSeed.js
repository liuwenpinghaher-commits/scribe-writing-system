/**
 * 主编种子 + 右栏聚焦（统一作者「让主编写入」合同）。
 * 与 WriteLayout / studioDocks 一致：sessionStorage + s3-chief-seed + s3-right-tab。
 * 种子文案须命中 shouldUseHermesRun(WORLD_WRITE_FORCE / 工具名),禁止掉进无工具讨论流。
 */

export function focusChiefWithSeed(text) {
  const payload = String(text ?? '')
  try { sessionStorage.setItem('s3.chief.seed', payload) } catch { /* */ }
  try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: payload })) } catch { /* */ }
  try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
  return payload
}

/** 设定库档案补全/更正（Codex 主路径） */
export function seedChiefCodexWrite(type, row = {}, hint = '') {
  const name = row.name || row.text || row.id || type
  const lines = type === 'chars'
    ? [
      `请更新/更正角色「${name}」的档案并写入落库(需我审批):`,
      '可补全或修正:外貌/性格/前史/目标/恐惧/首次出场等。',
      '必须先用只读工具核实,再用 s3_patch_character(或对应写工具)写入。',
      '未获批准不得声称已落库。',
    ]
    : [
      `请根据本书上下文补全/更正设定「${name}」(类型:${type})并提交写入提案供我批准。`,
      '先只读核实当前库内事实,再调用对应 s3_ 写工具;未获批准不得声称已落库。',
    ]
  if (hint) lines.push(String(hint))
  return focusChiefWithSeed(lines.join('\n'))
}

/**
 * 新建设定(法典入口)。禁止表单直写 REST;走 MCP 待批。
 * @param {string} catType character|faction|item|term|world_rule|promise|motif|proposition
 * @param {object} [fields] 用户已填草稿字段
 */
export function seedChiefCodexCreate(catType, fields = {}) {
  const toolByCat = {
    character: 's3_add_character',
    faction: 's3_add_faction',
    item: 's3_add_item',
    term: 's3_add_term',
    world_rule: 's3_add_world_rule',
    promise: 's3_plant_promise',
    motif: 's3_add_motif',
    proposition: 's3_add_fact',
  }
  const tool = toolByCat[catType] || 's3_add_character'
  const label = fields.name || fields.text || fields.entity || catType
  const payload = JSON.stringify(fields || {}, null, 0)
  const lines = [
    `请新建设定「${label}」(类型:${catType})并写入落库(需我审批)。`,
    `使用工具 ${tool} 提交写入提案;字段草稿:${payload}`,
    '先只读核实是否已有同名实体,再写入;未获批准不得声称已落库。',
  ]
  return focusChiefWithSeed(lines.join('\n'))
}

/**
 * 通用叙事元数据种子（大纲/节拍/演绎/卷纲/章信息/意图/伏笔决策等）。
 * @param {string} scope 简短域标签
 * @param {string} target 对象描述（如「第 3 章大纲」）
 * @param {string} [hint] 具体意图
 */
export function seedChiefNarrativeWrite(scope, target, hint = '') {
  const lines = [
    `请更新/更正「${target}」(${scope})并提交写入提案供我批准。`,
    '先用只读工具核实当前库内内容,再调用对应 s3_ 写工具;未获批准不得声称已落库。',
  ]
  if (hint) lines.push(String(hint))
  return focusChiefWithSeed(lines.join('\n'))
}

/** 章节重排 → s3_reorder_chapters */
export function seedChiefReorderChapters(volumeId, order) {
  const seqs = Array.isArray(order) ? order : []
  const vol = volumeId || '未分卷'
  return focusChiefWithSeed([
    `请重排章节顺序并写入落库(需我审批)。`,
    `使用工具 s3_reorder_chapters: volume_id=${volumeId ? JSON.stringify(volumeId) : 'null'}, order=${JSON.stringify(seqs)}。`,
    `目标卷:${vol};新序章号:${seqs.join(',') || '(空)'}。`,
    '未获批准不得声称已落库。',
  ].join('\n'))
}

/** 删卷 → s3_delete_volume(章保留) */
export function seedChiefDeleteVolume(volumeId, title = '') {
  return focusChiefWithSeed([
    `请删除分卷「${title || volumeId}」并写入落库(需我审批)。`,
    `使用工具 s3_delete_volume(volume_id=${JSON.stringify(volumeId)});该卷下章仅清卷归属,不删正文。`,
    '未获批准不得声称已落库。',
  ].join('\n'))
}

/** 新建素材 → s3_add_material（保留 source 出处字段） */
export function seedChiefAddMaterial({
  title = '', body = '', kind = 'note', tags = [], ref_tags = [], source = '',
} = {}) {
  const src = String(source || '').trim()
  return focusChiefWithSeed([
    `请新建素材「${title || '未命名'}」并写入落库(需我审批)。`,
    `使用工具 s3_add_material(title, body, kind=${JSON.stringify(kind)}`
      + (src ? `, source=${JSON.stringify(src)}` : '')
      + ');借鉴非正典事实。',
    `正文草稿:${(body || '').slice(0, 500)}`,
    tags?.length ? `tags:${tags.join(',')}` : '',
    ref_tags?.length ? `ref_tags:${ref_tags.join(',')}` : '',
    src ? `source:${src}` : '',
    '未获批准不得声称已落库。',
  ].filter(Boolean).join('\n'))
}

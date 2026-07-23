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

/** DetailView type → 具名 MCP patch 工具 */
const CODEX_PATCH_TOOL = {
  chars: 's3_patch_character',
  factions: 's3_patch_faction',
  items: 's3_patch_item',
  terms: 's3_patch_term',
  rules: 's3_patch_world_rule',
  promises: 's3_patch_promise',
  motifs: 's3_patch_motif',
  facts: 's3_supersede_fact',
}

/** 设定库档案补全/更正（Codex 主路径）——种子必须点名真实写工具 */
export function seedChiefCodexWrite(type, row = {}, hint = '') {
  const name = row.name || row.text || row.id || type
  const tool = CODEX_PATCH_TOOL[type] || 's3_patch_character'
  const idHint = row.id || row.name || name
  const lines = type === 'chars'
    ? [
      `请更新/更正角色「${name}」的档案并写入落库(需我审批):`,
      '可补全或修正:外貌/性格/前史/目标/恐惧/首次出场等。',
      `必须先用只读工具核实,再用 ${tool}(character_id=…) 写入。`,
      '未获批准不得声称已落库。',
    ]
    : [
      `请根据本书上下文补全/更正设定「${name}」(类型:${type})并提交写入提案供我批准。`,
      `先只读核实当前库内事实,再调用 ${tool}(目标 id/name=${JSON.stringify(String(idHint))}) 写入。`,
      '未获批准不得声称已落库。',
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
 * 归档/删除设定对象 → s3_delete_codex
 * @param {string} objectType role|fact|faction|item|term|world_rule|promise|motif
 * @param {string} objectId 裸 id 或 name
 * @param {{ label?: string, archive?: boolean }} [opts]
 */
export function seedChiefDeleteCodex(objectType, objectId, { label = '', archive = true } = {}) {
  const ot = String(objectType || '').trim()
  const oid = String(objectId || '').trim()
  const mode = archive ? '归档' : '删除'
  return focusChiefWithSeed([
    `请${mode}设定 ${ot}:${label || oid} 并写入落库(需我审批)。`,
    `使用工具 s3_delete_codex(object_type=${JSON.stringify(ot)}, object_id=${JSON.stringify(oid)}, archive=${archive ? 'true' : 'false'})。`,
    '未获批准不得声称已落库。',
  ].join('\n'))
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

/** 新建素材 → s3_add_material（summary/ref_tags/pinned/source 与导入字段对齐） */
export function seedChiefAddMaterial({
  title = '', body = '', kind = 'note', tags = [], ref_tags = [], source = '',
  summary = '', pinned = false,
} = {}) {
  const src = String(source || '').trim()
  const sum = String(summary || '').trim()
  return focusChiefWithSeed([
    `请新建素材「${title || '未命名'}」并写入落库(需我审批)。`,
    `使用工具 s3_add_material(title, body, kind=${JSON.stringify(kind)}`
      + (src ? `, source=${JSON.stringify(src)}` : '')
      + (sum ? `, summary=${JSON.stringify(sum)}` : '')
      + (pinned ? ', pinned=true' : '')
      + (tags?.length ? `, tags=${JSON.stringify(tags)}` : '')
      + (ref_tags?.length ? `, ref_tags=${JSON.stringify(ref_tags)}` : '')
      + ');借鉴非正典事实。',
    `正文草稿:${(body || '').slice(0, 500)}`,
    sum ? `summary:${sum}` : '',
    tags?.length ? `tags:${tags.join(',')}` : '',
    ref_tags?.length ? `ref_tags:${ref_tags.join(',')}` : '',
    src ? `source:${src}` : '',
    '未获批准不得声称已落库。',
  ].filter(Boolean).join('\n'))
}

/** 更新素材 → s3_patch_material（禁 REST 直写） */
export function seedChiefPatchMaterial(materialId, {
  title = '', body = '', kind = 'note', tags = [], ref_tags = [], source = '',
  summary = '', pinned = undefined, archived = undefined,
} = {}) {
  const mid = String(materialId || '').trim()
  const src = String(source || '').trim()
  const sum = String(summary || '').trim()
  return focusChiefWithSeed([
    `请更新素材 id=${mid}「${title || '未命名'}」并写入落库(需我审批)。`,
    `使用工具 s3_patch_material(material_id=${JSON.stringify(mid)}, title, body, kind=${JSON.stringify(kind)}`
      + (src ? `, source=${JSON.stringify(src)}` : ', source=""')
      + (sum ? `, summary=${JSON.stringify(sum)}` : ', summary=""')
      + (tags?.length ? `, tags=${JSON.stringify(tags)}` : '')
      + (ref_tags?.length ? `, ref_tags=${JSON.stringify(ref_tags)}` : '')
      + (pinned === true ? ', pinned=true' : pinned === false ? ', pinned=false' : '')
      + (archived === true ? ', archived=true' : archived === false ? ', archived=false' : '')
      + ')。',
    `正文草稿:${(body || '').slice(0, 800)}`,
    '未获批准不得声称已落库。',
  ].filter(Boolean).join('\n'))
}


/** 归档/删除素材 → s3_delete_material */
export function seedChiefDeleteMaterial(materialId, { title = '', archive = true } = {}) {
  const mid = String(materialId || '').trim()
  const mode = archive ? '归档' : '删除'
  return focusChiefWithSeed([
    `请${mode}素材 id=${mid}「${title || mid}」并写入落库(需我审批)。`,
    `使用工具 s3_delete_material(material_id=${JSON.stringify(mid)}, archive=${archive ? 'true' : 'false'})。`,
    '未获批准不得声称已落库。',
  ].join('\n'))
}

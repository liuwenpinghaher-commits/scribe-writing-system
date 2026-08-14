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

const REGISTRY_CODEX_KIND = {
  chars: 'character',
  factions: 'faction',
  items: 'item',
  terms: 'term',
  rules: 'world_rule',
}

function registryFields(row = {}) {
  return Object.fromEntries(Object.entries(row).filter(([key, value]) => (
    value != null && !['id', 'kind', 'archived'].includes(key)
  )))
}

/** 设定库档案补全/更正（Codex 主路径）——种子必须点名真实写工具 */
export function seedChiefCodexWrite(type, row = {}, hint = '') {
  const name = row.name || row.text || row.id || type
  const tool = CODEX_PATCH_TOOL[type] || 's3_patch_character'
  const idHint = row.id || row.name || name
  const registryKind = REGISTRY_CODEX_KIND[type]
  const fields = registryFields(row)
  const lines = registryKind
    ? [
      `请根据本书上下文补全/更正设定「${name}」(类型:${registryKind})并提交写入提案供我批准。`,
      `先用只读工具核实现状，再调用 s3_patch_codex(kind=${JSON.stringify(registryKind)}, name=${JSON.stringify(String(name))}, fields=${JSON.stringify(fields)})。`,
      '该工具支持该类型的全部注册字段；未获批准不得声称已落库。',
    ]
    : type === 'chars'
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
  if (catType === 'proposition') {
    const entity = fields.entity || 'role:…'
    const attr = fields.attribute || 'state'
    const value = fields.value || '…'
    const ch = fields.valid_from ?? 1
    const secret = fields.secret ? 'true' : 'false'
    const lines = [
      `请登记世界真相（时态状态，勿与场景 deduce 混淆）并写入落库(需我审批)。`,
      `请自第 ${ch} 章起，将「${entity}」的「${attr}」确立为：${value}。secret=${secret}。`,
      `使用工具 ${tool}（或已有同槽时用 s3_supersede_fact 演变）；勿使用 edit_fact 原地抹历史。`,
      `字段草稿:${payload}`,
      '先只读核实是否已有同 entity+attribute 开区间,再写入;未获批准不得声称已落库。',
    ]
    return focusChiefWithSeed(lines.join('\n'))
  }
  const lines = [
    `请新建设定「${label}」(类型:${catType})并写入落库(需我审批)。`,
    `使用工具 ${tool} 提交写入提案;字段草稿:${payload}`,
    '先只读核实是否已有同名实体,再写入;未获批准不得声称已落库。',
  ]
  return focusChiefWithSeed(lines.join('\n'))
}

/** PR-6：演变种子模板（实体卡 / 命题详情共用） */
export function seedChiefTruthSupersede({
  entityId,
  entityLabel,
  attribute = '状态',
  valueHint = '（请填写新状态）',
  sinceChapter = '当前章',
  secret = false,
} = {}) {
  const name = entityLabel || String(entityId || '').split(':').pop() || '该实体'
  const lines = [
    `请自第 ${sinceChapter} 章起，将「${name}」的状态「${attribute}」演变为：${valueHint}。`,
    `使用 s3_supersede_fact（entity_id=${JSON.stringify(String(entityId || ''))}）；secret=${secret ? 'true' : 'false'}。`,
    '勿使用 edit_fact 原地抹历史；未获批准不得声称已落库。',
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

/** 脚手架任务禁止用正文 save 完成（软合同 · 与 H1 设计一致） */
export const SCAFFOLD_FORBID_SAVE =
  '禁止用 s3_save_chapter 或「保存正文」完成本章大纲/节拍/演绎/章信息脚手架；请用下列 patch 工具提交写入提案。'

/**
 * scope → 具名写工具合同（点名工具 = RunToolContract / match_force 素材）。
 * @returns {{ tool: string, field?: string, gateHint?: string }|null}
 */
export function scaffoldToolContract(scope) {
  const s = String(scope || '').toLowerCase()
  if (s === 'outline' || s === 'synopsis' || s === '章大纲') {
    return {
      tool: 's3_patch_chapter_plan',
      field: 'synopsis',
      gateHint: '必须用 LLM 写因果大纲 ≥500 字（日子/必须发生/因→果/不能说/章末未决）。禁止口号。也可用 s3_generate_stage(stage=outline)。',
    }
  }
  if (s === 'beats' || s === '节拍') {
    return {
      tool: 's3_patch_chapter_plan',
      field: 'beats',
      gateHint: '必须用 LLM 写场面纸：每拍 ≥500、合计 ≥2000。禁止大纲切句。也可用 s3_generate_stage(stage=beats)。',
    }
  }
  if (s === 'deduce' || s === 'scene_truth' || s === '演绎') {
    return {
      tool: 's3_patch_chapter_plan',
      field: 'scene_truth',
      gateHint: '必须用 LLM 写场景真相+五层投影合计 ≥5000。禁止摘录占位。也可用 s3_generate_stage(stage=deduce)。',
    }
  }
  if (s === 'draft' || s === '排演' || s === '草稿') {
    return {
      tool: 's3_save_chapter_draft',
      field: 'draft',
      gateHint: '排演 ≥10000 字，只落 chapter.draft，禁止写入 prose。也可用 s3_generate_stage(stage=draft)。',
    }
  }
  if (s === 'chapter-meta' || s === 'chapter_meta' || s === '章信息') {
    return { tool: 's3_patch_chapter_meta', field: null, gateHint: '仅 title/label/volume/focalizer 等身份字段。' }
  }
  if (s === 'volume' || s === '卷' || s === '卷纲') {
    return { tool: 's3_patch_volume', field: 'intro', gateHint: '卷纲≠章大纲 synopsis；空 intro 则不注入 volume_intro。' }
  }
  if (s === 'story_move' || s === '招式' || s === '这一圈') {
    return {
      tool: 's3_patch_chapter_plan',
      field: 'story_move_plan',
      gateHint: '这一圈是绕法，不是完成灯。先 s3_move_retrieve。',
    }
  }
  if (s === 'scene' || s === '场面' || s === 'narrative_contract') {
    return {
      tool: 's3_patch_chapter_plan',
      field: 'narrative_contract',
      gateHint: '场面合同走审批。不要把建议四格原样当合同。',
    }
  }
  return null
}

/**
 * 通用叙事元数据种子（大纲/节拍/演绎/卷纲/章信息/意图/伏笔决策等）。
 * 已知脚手架 scope 时**必须点名**对应 s3_ 写工具（H1 KD-CM-6）。
 * @param {string} scope 简短域标签
 * @param {string} target 对象描述（如「第 3 章大纲」）
 * @param {string} [hint] 具体意图
 */
export function seedChiefNarrativeWrite(scope, target, hint = '') {
  const contract = scaffoldToolContract(scope)
  const lines = [
    `请更新/更正「${target}」(${scope})并提交写入提案供我批准。`,
  ]
  if (contract) {
    const fieldPart = contract.field ? ` field=${contract.field}` : ''
    const alreadyNamesTool = String(hint || '').includes(contract.tool)
    if (!alreadyNamesTool) {
      lines.push(
        `使用工具 ${contract.tool}${fieldPart} 提交写入提案；先用 s3_get_chapter / 只读工具核实现状。`,
      )
    }
    if (contract.gateHint) lines.push(contract.gateHint)
    if (contract.tool === 's3_patch_chapter_plan' || contract.tool === 's3_patch_chapter_meta') {
      lines.push(SCAFFOLD_FORBID_SAVE)
    }
  } else {
    lines.push('先用只读工具核实当前库内内容,再调用对应 s3_ 写工具;未获批准不得声称已落库。')
  }
  if (hint) lines.push(String(hint))
  if (contract && !lines.some((l) => l.includes('未获批准'))) {
    lines.push('未获批准不得声称已落库。')
  }
  return focusChiefWithSeed(lines.join('\n'))
}

/**
 * 章大纲 synopsis 主编种子（与 OutlineTab / ChapterCard scope='outline' 同源）。
 */
export function seedChapterOutline(seq, synopsis = '', extraHint = '') {
  const n = Number(seq) || seq
  const body = extraHint
    || `请更新第 ${n} 章大纲(synopsis)。当前内容:\n${synopsis || '（空）'}`
  return seedChiefNarrativeWrite(
    'outline',
    `第 ${n} 章大纲`,
    [
      `使用工具 s3_patch_chapter_plan(seq=${n}, field=synopsis) 提交写入提案；或先 s3_generate_stage(stage=outline) 让 LLM 写厚再批。`,
      SCAFFOLD_FORBID_SAVE,
      '大纲必须 LLM 生成 ≥500 字（日子/必须发生/因→果/不能说/章末未决），禁止口号。',
      body,
    ].join('\n'),
  )
}

/**
 * 章节拍 beats 主编种子（与 BeatsTab scope='beats' 同源）。
 */
export function seedChapterBeats(seq, beats = [], extraHint = '') {
  const n = Number(seq) || seq
  const list = Array.isArray(beats) ? beats : []
  const serialized = list.map((b, i) => {
    if (typeof b === 'string') return `${i + 1}. ${b}`
    return `${i + 1}. ${b?.text || ''}${b?.done ? ' [已完成]' : ''}`
  }).join('\n')
  const body = extraHint
    || `请更新第 ${n} 章节拍列表(beats)。当前 ${list.length} 条:\n${serialized || '（空）'}`
  return seedChiefNarrativeWrite(
    'beats',
    `第 ${n} 章节拍`,
    [
      `使用工具 s3_patch_chapter_plan(seq=${n}, field=beats) 提交写入提案；或先 s3_generate_stage(stage=beats) 让 LLM 写厚再批。`,
      SCAFFOLD_FORBID_SAVE,
      '每拍场面纸 ≥500 字、合计 ≥2000，必须 LLM 生成，禁止大纲切句充数。',
      body,
    ].join('\n'),
  )
}

/**
 * 章演绎 scene_truth / 限知 主编种子。
 */
export function seedChapterScene(seq, extraHint = '') {
  const n = Number(seq) || seq
  return seedChiefNarrativeWrite(
    'scene',
    `第 ${n} 章场面合同`,
    [
      `1. 先 s3_suggest_scene_contract(seq=${n}) 拿 briefing + candidates（persist=false，不是已落库合同）。`,
      '2. 先用人话讲这场戏：发生哪一下、谁拦、留下什么。材料不够就问作者，不要凑字。',
      '3. 再落四义+≤3痕迹，每条能指回 briefing.source。',
      '4. 自检咬合（check_scene_lock 的人话版）；与上章 turn 撞车则改。',
      `5. s3_patch_chapter_plan(seq=${n}, narrative_contract={desire,obstacle,turn,cost,bindings:{evidence_must_show:[…]}}) 提交我批准。`,
      '未获批准不得声称已落库。若场面合同已变，旧提案会被拒，须按最新场面重拟。',
      '不要先齐大纲/节拍。不要说 GATE、可开写、材料够了。不要把建议四格原样当合同。',
      extraHint || '',
    ].filter(Boolean).join('\n'),
  )
}

export function seedChapterDeduce(seq, sceneTruth = '', extraHint = '') {
  const n = Number(seq) || seq
  const body = extraHint
    || `请填写/完善第 ${n} 章 scene_truth（场景真相）。当前:\n${sceneTruth || '（空）'}`
  return seedChiefNarrativeWrite(
    'deduce',
    `第 ${n} 章演绎/场景真相`,
    [
      `使用工具 s3_patch_chapter_plan(seq=${n}, field=scene_truth) 提交写入提案；演绎字段也可同工具；或先 s3_generate_stage(stage=deduce)。`,
      SCAFFOLD_FORBID_SAVE,
      '限知投影合计 ≥5000 字，必须 LLM 生成。勿用 s3_add_fact 当场景真相。禁止摘录占位。',
      body,
    ].join('\n'),
  )
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

export function seedChiefMovePlan(seq, benyi = '') {
  const n = Number(seq) || seq
  return seedChiefNarrativeWrite(
    'story_move',
    `第 ${n} 章招式计划`,
    [
      `域纪律(章招式):先 s3_move_retrieve(benyi=${benyi || '（先问作者：本意是什么）'}) 取一张已批招式（默认真三角；勿用 pending）。`,
      `使用工具 s3_patch_chapter_plan(seq=${n}, story_move_plan=) 提交本意+招式+构造拍。`,
      SCAFFOLD_FORBID_SAVE,
      '这是这一圈怎么绕，不是完成宣称。',
    ].join('\n'),
  )
}

export function seedChiefHookType(seq, hookType = '') {
  const n = Number(seq) || seq
  return seedChiefNarrativeWrite(
    'chapter-hook',
    `第 ${n} 章钩类型`,
    `请把第 ${n} 章 beats_meta.chapter_hook_type 设为 ${hookType || '悬念/危机/反转/情绪/信息之一'}，并用 s3_patch_chapter_meta 或 plan 写入。只多一句类型，不要倾倒钩子百科。`,
  )
}

/** 删卷 → s3_delete_volume(章保留) */
export function seedChiefDeleteVolume(volumeId, title = '') {
  return focusChiefWithSeed([
    `请删除分卷「${title || volumeId}」并写入落库(需我审批)。`,
    `使用工具 s3_delete_volume(volume_id=${JSON.stringify(volumeId)});该卷下章仅清卷归属,不删正文。`,
    '未获批准不得声称已落库。',
  ].join('\n'))
}

/**
 * 设定卡就绪灯。优先吃后端 evaluate_codex_ready 挂在 row.codex_ready 的结果。
 * 无后端字段时用同数字本地近似（详情离线/旧响应）。
 */

const TERM_PARTS = ['是什么', '不是什么', '本书用法', '边界']

const FIELD_FLOOR = {
  character: {
    personality_detail: 200, surface_goal: 80, deep_need: 80,
    fear: 80, internal_conflict: 80,
  },
  faction: { ideology: 200, public_face: 80 },
  item: { description: 400 },
  term: { definition: 1200 },
  world_rule: { cost: 80 },
  motif: { theme: 40, unfolding: 80 },
  voice: { style_summary: 80 },
}

const PACK_FLOOR = {
  character: 1200, faction: 1200, item: 1200, term: 1200, world_rule: 1200,
}

const LABELS = { stub: '空壳', thin: '偏薄', ready: '已齐' }

export function detailTypeToKind(detailType) {
  return ({
    chars: 'character',
    factions: 'faction',
    items: 'item',
    terms: 'term',
    rules: 'world_rule',
    motifs: 'motif',
  })[detailType] || detailType
}

function cn(value) {
  if (value == null) return 0
  if (Array.isArray(value)) return value.filter((x) => String(x || '').trim()).join('').replace(/\s/g, '').length
  return String(value).replace(/\s/g, '').length
}

export function evaluateCodexReady(kind, row = {}) {
  if (row?.codex_ready && row.codex_ready.status) {
    return {
      ok: !!row.codex_ready.ok,
      status: row.codex_ready.status,
      pack_cn: row.codex_ready.pack_cn || 0,
    }
  }
  const k = String(kind || '').toLowerCase()
  const floors = FIELD_FLOOR[k] || {}
  const keys = Object.keys(floors)
  let pack = 0
  let hasAny = false
  for (const key of keys) {
    const got = cn(row[key])
    pack += got
    if (got > 0) hasAny = true
  }
  if (k === 'term' && String(row.definition || '').trim()) hasAny = true
  if (!hasAny) return { ok: false, status: 'stub', pack_cn: pack }
  // 无后端 codex_ready 时不宣称已齐：缺 abilities/goals 等也会被本地近似漏判。
  return { ok: false, status: 'thin', pack_cn: pack }
}

export function lampOf(kind, row = {}) {
  const ev = evaluateCodexReady(kind, row)
  return { status: ev.status, label: LABELS[ev.status] || ev.status, pack_cn: ev.pack_cn }
}

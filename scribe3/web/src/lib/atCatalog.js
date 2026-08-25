/**
 * 全书 @ 引用目录（章节/视图/设定/事件/命题/素材）。
 * 与会话剪藏（sessionClip）分开：剪藏写素材库，本文件只组装 compose token。
 */

/**
 * 检测输入框光标前是否正在打 @查询（用于素材 @ 选择器）。
 * @param {string} text
 * @param {number} caret
 * @returns {{ atIndex: number, query: string, caret: number } | null}
 */
export function detectAtQuery(text, caret) {
  const s = String(text ?? '')
  const c = Math.max(0, Math.min(Number(caret) || 0, s.length))
  const before = s.slice(0, c)
  const at = before.lastIndexOf('@')
  if (at < 0) return null
  // @ 前须为行首/空白，避免邮箱等
  if (at > 0 && !/[\s\n]/.test(before[at - 1])) return null
  const query = before.slice(at + 1)
  // 查询段不含空白/换行；含则已结束 @token
  if (/[\s\n]/.test(query)) return null
  return { atIndex: at, query, caret: c }
}

/** 设定库叶子类型（project-tree codex） */
export const CODEX_AT_TYPES = Object.freeze([
  'character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif',
])

/** @ 条目 domain → 中文标签 */
export const AT_DOMAIN_LABEL = Object.freeze({
  chapter: '章节',
  view: '视图',
  codex: '设定',
  event: '事件',
  fact: '命题',
  material: '素材',
})

/**
 * 素材 → 统一 @ 条目
 * @returns {Array<{ key: string, domain: string, type: string, title: string, refToken: string, kind?: string, subtitle?: string, hay: string }>}
 */
export function materialsToAtItems(rows) {
  const list = Array.isArray(rows) ? rows : []
  const out = []
  for (const m of list) {
    if (!m) continue
    const id = m.id ?? m.material_id
    if (id == null || id === '') continue
    const title = String(m.title || id)
    const kind = String(m.kind || 'note')
    const source = String(m.source || '')
    const body = String(m.body || '')
    const refToken = `material:${id}`
    out.push({
      key: refToken,
      domain: 'material',
      type: 'material',
      title,
      refToken,
      kind,
      subtitle: source || kind,
      hay: `${title}\n${kind}\n${body}\n${source}\n素材`.toLowerCase(),
    })
  }
  return out
}

/**
 * 从 project-tree 的 codex 根递归收集设定叶子。
 * @param {object|null} codexRoot
 */
export function codexTreeToAtItems(codexRoot) {
  const out = []
  const leaf = new Set(CODEX_AT_TYPES)
  const walk = (node) => {
    if (!node || typeof node !== 'object') return
    if (leaf.has(node.type)) {
      const title = String(node.label || node.ref || node.id || '')
      if (!title && node.ref == null && node.id == null) return
      const refToken = String(node.id || `${node.type}:${node.ref}`)
      const type = String(node.type)
      out.push({
        key: refToken,
        domain: 'codex',
        type,
        title: title || refToken,
        refToken,
        subtitle: type,
        hay: `${title}\n${type}\n${refToken}\n设定`.toLowerCase(),
      })
    }
    for (const c of node.children || []) walk(c)
  }
  walk(codexRoot)
  return out
}

/**
 * 手稿树 → 章 / 卷
 * @param {object|null} manuscriptRoot
 */
export function manuscriptTreeToAtItems(manuscriptRoot) {
  const out = []
  const walk = (node) => {
    if (!node || typeof node !== 'object') return
    if (node.type === 'chapter') {
      const seq = node.ref != null ? node.ref : (String(node.id || '').replace(/^ch:/, '') || null)
      const title = String(node.label || (seq != null ? `第${seq}章` : node.id || ''))
      const refToken = String(node.id || (seq != null ? `ch:${seq}` : title))
      out.push({
        key: refToken,
        domain: 'chapter',
        type: 'chapter',
        title,
        refToken,
        subtitle: seq != null ? `第${seq}章` : '章节',
        seq: seq != null ? Number(seq) : undefined,
        hay: `${title}\n章节\nchapter\n${refToken}\n${seq ?? ''}`.toLowerCase(),
      })
    } else if (node.type === 'volume') {
      const title = String(node.label || node.ref || node.id || '分卷')
      const refToken = String(node.id || `vol:${node.ref ?? title}`)
      out.push({
        key: refToken,
        domain: 'chapter',
        type: 'volume',
        title,
        refToken,
        subtitle: '分卷',
        hay: `${title}\n分卷\nvolume\n${refToken}`.toLowerCase(),
      })
    }
    for (const c of node.children || []) walk(c)
  }
  walk(manuscriptRoot)
  return out
}

/**
 * 横切视图 → @ 条目
 * @param {Array|object|null} views project-tree.views 或含 children 的节点
 */
export function viewsToAtItems(views) {
  const list = Array.isArray(views)
    ? views
    : (views?.children || [])
  const out = []
  for (const v of list) {
    if (!v) continue
    const key = String(v.id || v.viewKey || v.ref || '')
    if (!key) continue
    const viewKey = String(v.viewKey || key.replace(/^view:/, '') || key)
    const title = String(v.label || viewKey)
    const refToken = key.startsWith('view:') ? key : `view:${viewKey}`
    out.push({
      key: refToken,
      domain: 'view',
      type: 'view',
      title,
      refToken,
      subtitle: '视图',
      hay: `${title}\n视图\nview\n${viewKey}\n${refToken}`.toLowerCase(),
    })
  }
  return out
}

/**
 * 时间线 items → 事件/弧光/关系/伏笔触点
 * @param {Array|object|null} timeline payload.items 或整包
 */
export function timelineToAtItems(timeline) {
  const items = Array.isArray(timeline)
    ? timeline
    : (Array.isArray(timeline?.items) ? timeline.items : [])
  const out = []
  for (const ev of items) {
    if (!ev) continue
    const id = ev.id || ev.event_id
    if (id == null || id === '') continue
    const kind = String(ev.kind || ev.type || 'event')
    const ch = ev.chapter != null ? ev.chapter : ev.story_chapter
    const label = String(ev.label || ev.goal || ev.text || id)
    const refToken = String(id).includes(':') ? String(id) : `ev:${id}`
    const title = label.length > 48 ? `${label.slice(0, 47)}…` : label
    out.push({
      key: `event:${refToken}`,
      domain: 'event',
      type: kind === 'event' ? 'event' : kind,
      title,
      refToken,
      subtitle: ch != null ? `第${ch}章·${kind}` : kind,
      hay: `${title}\n${kind}\n事件\n${refToken}\n${ch ?? ''}\n${label}`.toLowerCase(),
    })
  }
  return out
}

/**
 * 命题/事实（facts_at 结果）
 * @param {Array|null} facts
 */
export function factsToAtItems(facts) {
  const list = Array.isArray(facts) ? facts : []
  const out = []
  for (const f of list) {
    if (!f) continue
    const id = f.id || f.local || f.fact_id
    if (id == null || id === '') continue
    const entity = f.entity || f.subject || ''
    const attr = f.attribute || f.attr || ''
    const value = f.value != null ? String(f.value) : ''
    const title = [entity, attr, value].filter(Boolean).join(' · ')
      || String(f.text || f.label || id)
    const refToken = String(id).includes(':') ? String(id) : `fact:${id}`
    const short = title.length > 48 ? `${title.slice(0, 47)}…` : title
    out.push({
      key: refToken,
      domain: 'fact',
      type: 'fact',
      title: short,
      refToken,
      subtitle: '命题',
      hay: `${title}\n命题\nfact\n${entity}\n${attr}\n${value}\n${refToken}`.toLowerCase(),
    })
  }
  return out
}

/**
 * /entities 补充（与 codex 树去重）
 * @param {Array|null} entities
 */
export function entitiesToAtItems(entities) {
  const list = Array.isArray(entities) ? entities : []
  const out = []
  for (const e of list) {
    if (!e) continue
    const id = e.id
    const name = e.name || e.label
    if (id == null && !name) continue
    const kind = String(e.kind || 'character')
    const refToken = String(id || `${kind}:${name}`)
    const title = String(name || id)
    out.push({
      key: refToken,
      domain: 'codex',
      type: kind,
      title,
      refToken,
      subtitle: kind,
      hay: `${title}\n${kind}\n设定\n${refToken}\n${(e.aliases || []).join(' ')}`.toLowerCase(),
    })
  }
  return out
}

/**
 * 合并全书可 @ 对象目录。
 * 顺序：章节 → 视图 → 设定 → 事件 → 命题 → 素材（正典优先于剪藏）。
 */
export function buildAtCatalog({
  materials,
  codexRoot,
  manuscriptRoot,
  views,
  timeline,
  facts,
  entities,
} = {}) {
  const batches = [
    manuscriptTreeToAtItems(manuscriptRoot),
    viewsToAtItems(views),
    codexTreeToAtItems(codexRoot),
    entitiesToAtItems(entities),
    timelineToAtItems(timeline),
    factsToAtItems(facts),
    materialsToAtItems(materials),
  ]
  const seen = new Set()
  const merged = []
  for (const batch of batches) {
    for (const it of batch) {
      if (!it?.key || seen.has(it.key)) continue
      seen.add(it.key)
      merged.push(it)
    }
  }
  return merged
}

/**
 * 统一 @ 目录过滤。
 * @param {Array<object>} items buildAtCatalog 结果或兼容旧 material 行
 * @param {string} query
 * @param {number} [limit]
 */
export function filterAtCatalog(items, query = '', limit = 50) {
  const list = Array.isArray(items) ? items : []
  const q = String(query || '').trim().toLowerCase()
  const scored = []
  for (const raw of list) {
    if (!raw) continue
    // 兼容未 normalize 的素材行
    const it = raw.domain
      ? raw
      : materialsToAtItems([raw])[0]
    if (!it) continue
    const hay = it.hay || `${it.title}\n${it.type}\n${it.refToken}`.toLowerCase()
    if (q && !hay.includes(q)) continue
    scored.push(it)
    if (scored.length >= limit) break
  }
  return scored
}

/** @deprecated 用 filterAtCatalog；保留兼容旧测试 */
export function filterMaterialsForAt(rows, query = '', limit = 40) {
  return filterAtCatalog(materialsToAtItems(rows), query, limit)
}

/**
 * 生成写入 compose 的 @ 引用 token（章节/视图/设定/事件/命题/素材）。
 */
export function formatAtMentionToken(item) {
  if (!item) return ''
  const title = String(item.title || item.label || item.refToken || '')
    .replace(/[】\n]/g, ' ').trim()
  const domain = item.domain
    || (String(item.refToken || '').startsWith('material:') ? 'material' : 'codex')
  const type = item.type || domain
  const ref = item.refToken
    || (domain === 'material' && (item.id ?? item.material_id) != null
      ? `material:${item.id ?? item.material_id}`
      : `${type}:${item.id || title}`)
  if (!ref) return ''
  const label = AT_DOMAIN_LABEL[domain] || '引用'
  if (domain === 'material') {
    const kind = item.kind || 'note'
    return `【@${label} ref=${ref} title=「${title}」 kind=${kind}】`
  }
  return `【@${label} type=${type} ref=${ref} title=「${title}」】`
}

/**
 * 把 @query 替换为稳定引用 token（素材或设定）。
 * @returns {{ text: string, caret: number, token: string } | null}
 */
export function insertAtMention(text, caret, item) {
  const det = detectAtQuery(text, caret)
  if (!det) return null
  // 兼容旧：传入裸 material 行
  const norm = item?.domain
    ? item
    : (item && (item.id != null || item.material_id != null)
      ? materialsToAtItems([item])[0]
      : null)
  if (!norm) return null
  const token = formatAtMentionToken(norm)
  if (!token) return null
  const s = String(text ?? '')
  const next = s.slice(0, det.atIndex) + token + s.slice(det.caret)
  const nextCaret = det.atIndex + token.length
  return { text: next, caret: nextCaret, token }
}

/** @deprecated 用 insertAtMention */
export function insertMaterialAtMention(text, caret, material) {
  return insertAtMention(text, caret, material)
}

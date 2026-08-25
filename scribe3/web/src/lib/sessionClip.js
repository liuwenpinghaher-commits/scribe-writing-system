/**
 * 会话/选区摘录 → 素材 + 引入会话 / 讨论。
 *
 * 作者点「存」= 私人剪藏，走 POST /author/session-clips（世界写闸外），
 * 不经主编 MCP 审批、不走被闸死的 POST /materials。
 * 收件箱仍是决策队列，与摘录无关。
 */
import { focusChiefWithSeed } from './chiefSeed.js'
import { focusTalk } from './focusTalk.js'
import { api } from '../api.js'

/** 允许的会话摘录 kind（素材，非决策 inbox） */
export const SESSION_CLIP_KINDS = Object.freeze(['snippet', 'note'])

/** 收件箱 decision kinds —— 摘录路径严禁产出 */
export const INBOX_DECISION_KINDS = Object.freeze([
  'needs_human',
  'promotable_lesson',
  'pilot_parked',
  'pilot_outline',
  'pilot_delivered',
  'pulse_decision',
  'idea_pending',
])

const MAX_BODY = 4000
const MAX_TITLE = 48
const MAX_CITE = 800

function shortTitle(text) {
  const t = String(text || '').replace(/\s+/g, ' ').trim()
  if (!t) return '会话摘录'
  return t.length <= MAX_TITLE ? t : `${t.slice(0, MAX_TITLE - 1)}…`
}

function truncateBody(text) {
  const t = String(text || '').trim()
  if (t.length <= MAX_BODY) return t
  return `${t.slice(0, MAX_BODY)}…`
}

function truncateCite(text, max = MAX_CITE) {
  const t = String(text || '').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

/**
 * 构造会话摘录草稿（纯对象，不写库、不进 inbox）。
 * @returns {{ title: string, body: string, kind: 'snippet'|'note', source: string,
 *   scope_label?: string, chapter_seq?: number, origin_label?: string } | null}
 */
export function buildSessionClipDraft(p = {}) {
  const body = truncateBody(p.text)
  if (!body) return null
  let kind = String(p.kind || 'snippet')
  if (!SESSION_CLIP_KINDS.includes(kind)) kind = 'snippet'
  if (INBOX_DECISION_KINDS.includes(kind)) kind = 'snippet'

  const scope = String(p.scopeLabel || '').trim()
  const origin = String(p.originLabel || '选区摘录').trim() || '选区摘录'
  const ch = p.chapterSeq != null && Number.isFinite(Number(p.chapterSeq))
    ? ` · 第${Number(p.chapterSeq)}章`
    : ''
  const scopePart = scope ? ` · ${scope}` : ''
  const source = `会话摘录 · ${origin}${ch}${scopePart}`

  return {
    title: shortTitle(body),
    body,
    kind,
    source,
    scope_label: scope || undefined,
    chapter_seq: p.chapterSeq != null && Number.isFinite(Number(p.chapterSeq))
      ? Number(p.chapterSeq) : undefined,
    origin_label: origin,
  }
}

/**
 * 作者「存」：POST /author/session-clips 立即落库（闸外，无需主编审批）。
 * @param {(body: object) => Promise<{id?: string, ok?: boolean, title?: string, kind?: string, source?: string}>} [addClip]
 */
export async function saveSessionClipAsMaterial(p = {}, addClip = api.addSessionClip.bind(api)) {
  const draft = buildSessionClipDraft(p)
  if (!draft) return null
  const res = await addClip({
    title: draft.title,
    body: draft.body,
    kind: draft.kind,
    source: draft.source,
    scope_label: draft.scope_label,
    chapter_seq: draft.chapter_seq,
    origin_label: draft.origin_label,
  })
  const id = res?.id != null ? String(res.id) : ''
  if (!id) throw new Error(res?.detail || '素材保存失败: 未返回 id')
  return {
    id,
    title: res.title || draft.title,
    body: draft.body,
    kind: res.kind || draft.kind,
    source: res.source || draft.source,
  }
}

/**
 * 「引入会话」：选区带标记塞进主编 compose。
 */
export function citeSelectionPayload(p = {}) {
  const text = truncateCite(p.text)
  if (!text) return null
  const scope = String(p.scopeLabel || '选区').trim() || '选区'
  const prefix = `【引入会话 · ${scope}】\n`
  const seedText = `${prefix}「${text}」\n`
  return { prefix, seedText }
}

export function seedCiteSelection(p = {}) {
  const c = citeSelectionPayload(p)
  if (!c) return false
  return focusChiefWithSeed(c.seedText)
}

export function discussMaterialPayload(material = {}) {
  const id = material.id ?? material.material_id
  if (id == null || id === '') return null
  const title = String(material.title || material.label || id)
  const focus = {
    type: 'material',
    id: String(id),
    label: title,
    payload: {
      kind: material.kind || 'note',
      source: material.source || '',
      material_id: String(id),
    },
    origin: 'panel',
  }
  const talk = focusTalk(focus)
  const prefix = talk?.prefix || `【当前聚焦:素材「${title}」(id=${id})】\n`
  const seedText = `${prefix}素材 id=${id}。请围绕这条素材讨论：如何用进当前故事？转正典必须 s3_promote_material(material_id=${id})，禁止改素材本身。`
  return { focus, prefix, seedText }
}

export function seedDiscussMaterial(material) {
  const p = discussMaterialPayload(material)
  if (!p) return false
  return focusChiefWithSeed(p.seedText)
}

export function citeMaterialPayload(material = {}, userNote = '') {
  const id = material.id ?? material.material_id
  if (id == null || id === '') return null
  const title = String(material.title || material.label || id)
  const kind = material.kind || 'note'
  const ref = `material:${id}`
  const prefix = `【引用素材 ref=${ref} title=「${title}」 kind=${kind}】\n`
  const note = String(userNote || '').trim()
  const seedText = note
    ? `${prefix}${note}`
    : `${prefix}请结合这条素材继续讨论/改写；引用身份以 ref 为准，勿丢 material id。`
  return { ref, prefix, seedText }
}

export function seedCiteMaterial(material, userNote = '') {
  const p = citeMaterialPayload(material, userNote)
  if (!p) return false
  return focusChiefWithSeed(p.seedText)
}

export {
  AT_DOMAIN_LABEL,
  CODEX_AT_TYPES,
  buildAtCatalog,
  codexTreeToAtItems,
  detectAtQuery,
  entitiesToAtItems,
  factsToAtItems,
  filterAtCatalog,
  filterMaterialsForAt,
  formatAtMentionToken,
  insertAtMention,
  insertMaterialAtMention,
  manuscriptTreeToAtItems,
  materialsToAtItems,
  timelineToAtItems,
  viewsToAtItems,
} from './atCatalog.js'

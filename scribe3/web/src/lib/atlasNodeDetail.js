/**
 * 图谱节点抽屉纯函数（PR-A）。
 * 邻居/度数/子图知情差/hop-boost — 无 React/Sigma。
 */
import { REL_LABEL } from './relColors.js'

export const SECRET_PLACEHOLDER = '私密命题'
export const SECRET_LOCK_LABEL = '🔒 私密'

/** 边关系展示：补全 REL_LABEL 缺项 */
export const EDGE_LABEL = {
  ...REL_LABEL,
  knows: '知道',
  member: '成员',
  held_by: '持有',
}

export function edgeLabel(rel) {
  if (!rel) return ''
  return EDGE_LABEL[rel] || REL_LABEL[rel] || String(rel)
}

/** 打开设定用类型；禁止 faction/item 落到 proposition */
export function atlasNavType(n) {
  if (n?.type === 'character') return 'character'
  if (n?.type === 'faction') return 'faction'
  if (n?.type === 'item') return 'item'
  if (n?.type === 'proposition') return 'proposition'
  const id = String(n?.id || '')
  if (id.startsWith('role:')) return 'character'
  if (id.startsWith('faction:')) return 'faction'
  if (id.startsWith('item:')) return 'item'
  return 'proposition'
}

export function displayNodeLabel(node) {
  if (!node) return ''
  if (node.secret) return SECRET_PLACEHOLDER
  const lab = (node.label || '').trim()
  if (lab) return lab
  return humanizeFactId(node.id) || node.id || ''
}

/**
 * 命题 id 人话化，避免 UI 直接甩 fact:d2-4。
 * 约定（ingest）：fact:d{章}-{序}=行动抽取；fact:k{章}-{序}=获知抽取；其它 fact: 未命名。
 */
export function humanizeFactId(id) {
  const s = String(id || '')
  if (!s.startsWith('fact:')) return ''
  const rest = s.slice(5)
  let m = /^d(\d+)-(\d+)$/.exec(rest)
  if (m) return `第${m[1]}章·行动摘要 #${m[2]}`
  m = /^k(\d+)-(\d+)$/.exec(rest)
  if (m) return `第${m[1]}章·获知摘要 #${m[2]}`
  return '未命名事实'
}

/** 抽屉列表主文案：有摘要用摘要；无则人话 id；永不把 fact: 当主标题裸奔 */
export function propositionListLabel(row) {
  if (!row) return ''
  if (row.secret) return SECRET_PLACEHOLDER
  const lab = (row.label || row.peerLabel || '').trim()
  if (lab && !lab.startsWith('fact:')) return lab
  const id = row.id || row.peerId || lab
  return humanizeFactId(id) || id || '未命名事实'
}

function nodeById(nodes, id) {
  if (!id) return null
  const list = nodes || []
  return list.find((n) => n.id === id) || null
}

/**
 * @returns {{
 *   relDegree: number,
 *   knowsDegree: number,
 *   degree: number,
 *   relEdges: object[],
 *   knowsOut: object[],
 *   knowsIn: object[],
 *   sharedWithFocus: object[],
 * }}
 */
export function neighborsOf(nodeId, edges, nodes, focusId) {
  const nodeMap = new Map((nodes || []).map((n) => [n.id, n]))
  const me = nodeMap.get(nodeId)
  const isProp = me?.type === 'proposition' || String(nodeId).startsWith('fact:')

  let relDegree = 0
  let knowsDegree = 0
  const relEdges = []
  const knowsOut = []
  const knowsIn = []
  const sharedWithFocus = []

  for (const e of edges || []) {
    if (!e || (e.src !== nodeId && e.dst !== nodeId)) continue
    const rel = e.rel || ''
    const peerId = e.src === nodeId ? e.dst : e.src
    const peer = nodeMap.get(peerId)
    const direction = e.src === nodeId ? 'out' : 'in'
    const peerSecret = !!(peer?.secret)
    const peerLabel = peerSecret
      ? SECRET_PLACEHOLDER
      : (() => {
          const raw = (peer?.label || '').trim()
          if (raw && !raw.startsWith('fact:')) return raw
          // 无摘要 / 摘要即 id 时：角色名保留 id 后缀；命题用 humanize
          if (peer?.type === 'proposition' || String(peerId).startsWith('fact:')) {
            return humanizeFactId(peerId) || '未命名事实'
          }
          return raw || peerId
        })()

    if (rel === 'knows') {
      const row = {
        peerId,
        peerLabel,
        peerType: peer?.type || (String(peerId).startsWith('role:') ? 'character' : 'proposition'),
        secret: peerSecret,
        direction,
        propId: direction === 'out' ? peerId : nodeId,
      }
      if (isProp) {
        // 命题：知情人为入边 src
        if (direction === 'in') {
          knowsDegree += 1
          knowsIn.push(row)
        }
      } else if (direction === 'out') {
        knowsDegree += 1
        knowsOut.push(row)
      }
    } else {
      relDegree += 1
      relEdges.push({
        peerId,
        peerLabel,
        peerType: peer?.type || 'character',
        rel,
        relLabel: edgeLabel(rel),
        direction,
        secret: peerSecret,
      })
    }

    if (focusId && peerId === focusId) {
      sharedWithFocus.push({
        rel,
        relLabel: rel === 'knows' ? edgeLabel('knows') : edgeLabel(rel),
        direction,
      })
    }
  }

  // 命题 knows：只统计入边
  if (isProp) {
    knowsDegree = knowsIn.length
  }

  return {
    relDegree,
    knowsDegree,
    degree: relDegree + knowsDegree,
    relEdges,
    knowsOut,
    knowsIn,
    sharedWithFocus,
  }
}

/** K(role) = 从角色出发 knows 且目标仍在 nodes 的命题 id 集合 */
export function knowsSet(roleId, edges, nodeIds) {
  const ids = nodeIds instanceof Set ? nodeIds : new Set(nodeIds || [])
  const out = new Set()
  for (const e of edges || []) {
    if (e.rel !== 'knows' || e.src !== roleId) continue
    if (ids.has(e.dst)) out.add(e.dst)
  }
  return out
}

/**
 * 子图知情差 + hop-boost 谓词（KD-20）。
 * peerKnowsUnobservable === (hop < 2 && nodeId !== focusId)
 */
export function knowledgeDiffSubgraph(nodeId, focusId, edges, nodes, opts = {}) {
  const hop = opts.hop != null ? Number(opts.hop) : 1
  const nodeIds = new Set((nodes || []).map((n) => n.id))
  const peerKnowsUnobservable = hop < 2 && !!nodeId && !!focusId && nodeId !== focusId
  const showHopBoost = peerKnowsUnobservable

  if (!nodeId || !focusId || nodeId === focusId) {
    const k = knowsSet(nodeId || focusId, edges, nodeIds)
    const onlySelf = []
    const list = [...k].slice(0, 5).map((id) => {
      const n = nodeById(nodes, id)
      return {
        id,
        label: n?.secret ? SECRET_PLACEHOLDER : (n?.label || id),
        secret: !!n?.secret,
      }
    })
    return {
      onlySelf,
      onlyFocus: [],
      bothCount: k.size,
      selfKnowsCount: k.size,
      scope: 'subgraph',
      hop,
      peerKnowsUnobservable: false,
      showHopBoost: false,
      isSelfFocus: true,
      focusKnownPreview: list,
      truncated: k.size > 5,
    }
  }

  const kSelf = knowsSet(nodeId, edges, nodeIds)
  const kFocus = knowsSet(focusId, edges, nodeIds)
  const onlySelfIds = [...kSelf].filter((id) => !kFocus.has(id))
  const onlyFocusIds = [...kFocus].filter((id) => !kSelf.has(id))
  const bothCount = [...kSelf].filter((id) => kFocus.has(id)).length

  const toRows = (ids, cap = 4) => ids.slice(0, cap).map((id) => {
    const n = nodeById(nodes, id)
    return {
      id,
      label: n?.secret ? SECRET_PLACEHOLDER : (n?.label || id),
      secret: !!n?.secret,
    }
  })

  // secret: never leak plaintext sample
  const sanitize = (rows) => rows.map((r) => (
    r.secret ? { ...r, label: SECRET_PLACEHOLDER } : r
  ))

  return {
    onlySelf: sanitize(toRows(onlySelfIds)),
    onlyFocus: sanitize(toRows(onlyFocusIds)),
    bothCount,
    selfKnowsCount: kSelf.size,
    focusKnowsCount: kFocus.size,
    scope: 'subgraph',
    hop,
    peerKnowsUnobservable,
    showHopBoost,
    isSelfFocus: false,
    truncated: onlySelfIds.length > 4 || onlyFocusIds.length > 4,
  }
}

/** 弧光一行展示文案（只读） */
export function formatArcLine(alignment, anchors) {
  const a = anchors || {}
  const al = alignment || {}
  if (!(a.lie || '').trim() && !al.status) {
    return { kind: 'cold', text: '冷启动：尚未填写错误信念(Lie)' }
  }
  const status = al.status || ''
  const beat = al.beat_name || ''
  const cur = al.current_belief
  const tgt = al.target
  const parts = []
  if (status) parts.push(status)
  if (beat) parts.push(`「${beat}」`)
  if (cur != null) parts.push(`信奉度 ${cur}`)
  if (tgt != null) parts.push(`→ ${tgt}`)
  if (parts.length) return { kind: 'ok', text: parts.join(' · ') }
  if ((a.lie || '').trim()) return { kind: 'ok', text: `Lie：「${String(a.lie).slice(0, 24)}」` }
  return { kind: 'empty', text: '暂无弧光采样' }
}

/** 首个可用于 expand 的角色 id */
export function resolveExpandCharacterId(node, edges, nodes) {
  if (!node) return null
  if (node.type === 'character' || String(node.id).startsWith('role:')) return node.id
  const nb = neighborsOf(node.id, edges, nodes, null)
  if (node.type === 'proposition' || String(node.id).startsWith('fact:')) {
    const knower = (nb.knowsIn || []).find((r) => !r.secret && (r.peerType === 'character' || String(r.peerId).startsWith('role:')))
    return knower?.peerId || null
  }
  if (node.type === 'faction') {
    const m = (nb.relEdges || []).find((r) => r.rel === 'member')
    return m?.peerId || null
  }
  if (node.type === 'item') {
    const h = (nb.relEdges || []).find((r) => r.rel === 'held_by')
    return h?.peerId || null
  }
  return null
}

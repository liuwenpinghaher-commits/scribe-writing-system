import { describe, it, expect } from 'vitest'
import {
  EDGE_LABEL,
  edgeLabel,
  atlasNavType,
  neighborsOf,
  knowledgeDiffSubgraph,
  knowsSet,
  formatArcLine,
  resolveExpandCharacterId,
  SECRET_PLACEHOLDER,
  displayNodeLabel,
} from './atlasNodeDetail.js'

const A = 'role:甲'
const B = 'role:乙'
const P1 = 'fact:共知'
const P2 = 'fact:乙独知'
const PSEC = 'fact:secret'

describe('atlasNavType', () => {
  it('maps faction/item correctly (not proposition)', () => {
    expect(atlasNavType({ type: 'faction', id: 'faction:x' })).toBe('faction')
    expect(atlasNavType({ type: 'item', id: 'item:y' })).toBe('item')
    expect(atlasNavType({ type: 'character', id: A })).toBe('character')
    expect(atlasNavType({ id: 'faction:only' })).toBe('faction')
  })
})

describe('edgeLabel / EDGE_LABEL', () => {
  it('labels knows/member/held_by', () => {
    expect(edgeLabel('knows')).toBe('知道')
    expect(edgeLabel('member')).toBe('成员')
    expect(edgeLabel('held_by')).toBe('持有')
    expect(EDGE_LABEL.knows).toBe('知道')
  })
})

describe('neighborsOf', () => {
  const nodes = [
    { id: A, type: 'character', label: '甲' },
    { id: B, type: 'character', label: '乙' },
    { id: P1, type: 'proposition', label: '共知题' },
    { id: 'faction:门', type: 'faction', label: '门' },
  ]
  const edges = [
    { src: A, dst: B, rel: 'ally' },
    { src: A, dst: P1, rel: 'knows' },
    { src: B, dst: P1, rel: 'knows' },
    { src: A, dst: 'faction:门', rel: 'member' },
  ]

  it('counts degree and lists rel/knows', () => {
    const n = neighborsOf(A, edges, nodes, B)
    expect(n.relDegree).toBe(2) // ally + member
    expect(n.knowsDegree).toBe(1)
    expect(n.degree).toBe(3)
    expect(n.sharedWithFocus.some((s) => s.rel === 'ally')).toBe(true)
    expect(n.knowsOut.some((k) => k.peerId === P1)).toBe(true)
  })

  it('proposition knowsIn lists knowers', () => {
    const n = neighborsOf(P1, edges, nodes, null)
    expect(n.knowsIn.length).toBe(2)
  })
})

describe('knowledgeDiffSubgraph hop honesty', () => {
  // A—ally—B; A/B know P1; only B knows P2 (2-hop from A as focus)
  const nodesHop1 = [
    { id: A, type: 'character', label: '甲' },
    { id: B, type: 'character', label: '乙' },
    { id: P1, type: 'proposition', label: '共知题' },
  ]
  const edgesHop1 = [
    { src: A, dst: B, rel: 'ally' },
    { src: A, dst: P1, rel: 'knows' },
    { src: B, dst: P1, rel: 'knows' },
    // B→P2 not in hop1 subgraph nodes — so onlySelf empty but boost still true
  ]

  it('hop=1 non-focus: showHopBoost true even when shared knows (共知仍 boost)', () => {
    const d = knowledgeDiffSubgraph(B, A, edgesHop1, nodesHop1, { hop: 1 })
    expect(d.peerKnowsUnobservable).toBe(true)
    expect(d.showHopBoost).toBe(true)
    expect(d.isSelfFocus).toBe(false)
    // onlySelf may be empty at hop1
    expect(Array.isArray(d.onlySelf)).toBe(true)
  })

  it('hop=2: P2 in onlySelf and boost false', () => {
    const nodes = [
      ...nodesHop1,
      { id: P2, type: 'proposition', label: '乙独知题' },
    ]
    const edges = [
      ...edgesHop1,
      { src: B, dst: P2, rel: 'knows' },
    ]
    const d = knowledgeDiffSubgraph(B, A, edges, nodes, { hop: 2 })
    expect(d.showHopBoost).toBe(false)
    expect(d.peerKnowsUnobservable).toBe(false)
    expect(d.onlySelf.some((r) => r.id === P2)).toBe(true)
    expect(d.onlyFocus.length).toBe(0)
  })

  it('self===focus: no boost, preview known', () => {
    const d = knowledgeDiffSubgraph(A, A, edgesHop1, nodesHop1, { hop: 1 })
    expect(d.showHopBoost).toBe(false)
    expect(d.isSelfFocus).toBe(true)
    expect(d.selfKnowsCount).toBe(1)
  })

  it('secret never leaks plaintext in labels', () => {
    const nodes = [
      { id: A, type: 'character', label: '甲' },
      { id: B, type: 'character', label: '乙' },
      { id: PSEC, type: 'proposition', label: '不该出现的明文机密', secret: true },
    ]
    const edges = [
      { src: B, dst: PSEC, rel: 'knows' },
    ]
    const d = knowledgeDiffSubgraph(B, A, edges, nodes, { hop: 2 })
    const blob = JSON.stringify(d)
    expect(blob).not.toContain('不该出现的明文机密')
    expect(d.onlySelf.every((r) => r.label === SECRET_PLACEHOLDER || !r.secret)).toBe(true)
    expect(displayNodeLabel({ secret: true, label: 'x' })).toBe(SECRET_PLACEHOLDER)
  })
})

describe('formatArcLine / expand', () => {
  it('cold start when no lie', () => {
    const r = formatArcLine({}, {})
    expect(r.kind).toBe('cold')
  })

  it('alignment line', () => {
    const r = formatArcLine(
      { status: 'overdue_miss', beat_name: '中点', current_belief: 80, target: 40 },
      { lie: 'X' },
    )
    expect(r.text).toContain('中点')
    expect(r.text).toContain('80')
  })

  it('resolveExpandCharacterId', () => {
    const nodes = [
      { id: A, type: 'character', label: '甲' },
      { id: P1, type: 'proposition', label: '题' },
    ]
    const edges = [{ src: A, dst: P1, rel: 'knows' }]
    expect(resolveExpandCharacterId({ id: A, type: 'character' }, edges, nodes)).toBe(A)
    expect(resolveExpandCharacterId({ id: P1, type: 'proposition' }, edges, nodes)).toBe(A)
  })
})

describe('knowsSet', () => {
  it('only outgoing knows into node set', () => {
    const s = knowsSet(A, [
      { src: A, dst: P1, rel: 'knows' },
      { src: A, dst: 'fact:out', rel: 'knows' },
      { src: B, dst: P1, rel: 'knows' },
    ], new Set([P1]))
    expect([...s]).toEqual([P1])
  })
})

describe('humanizeFactId / propositionListLabel', () => {
  it('decodes ingest fact ids', async () => {
    const { humanizeFactId, propositionListLabel } = await import('./atlasNodeDetail.js')
    expect(humanizeFactId('fact:d2-4')).toBe('第2章·行动摘要 #4')
    expect(humanizeFactId('fact:k5-1')).toBe('第5章·获知摘要 #1')
    expect(propositionListLabel({ peerId: 'fact:d2-4', label: '' })).toBe('第2章·行动摘要 #4')
    expect(propositionListLabel({ peerId: 'fact:d2-4', label: '埋灰' })).toBe('埋灰')
  })
})

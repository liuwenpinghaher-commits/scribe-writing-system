import { describe, expect, it } from 'vitest'
import { targetNodeToSelection } from '../targetNavigation.js'

describe('targetNodeToSelection', () => {
  it('keeps weak chapter targets in the review entry even when they include a chapter target_node', () => {
    const next = targetNodeToSelection({
      type: 'weak_chapter',
      id: 'issue:weak:3',
      chapter: 3,
      title: '第3章 · 弱章诊断',
      reason: '该章有 20 个 QC 问题。',
      target_node: { id: 'ch:3', type: 'chapter', ref: 3, label: '第3章' },
    })

    expect(next).toMatchObject({
      entry: 'review',
      node: {
        id: 'issue:weak:3',
        type: 'review_issue',
        label: '第3章 · 弱章诊断',
        payload: {
          chapter: 3,
          target_node: { id: 'ch:3', type: 'chapter', ref: 3, label: '第3章' },
        },
      },
    })
  })

  it('maps graph facts and character relations back to codex detail targets', () => {
    expect(targetNodeToSelection({ type: 'fact', id: 'fact:真相', label: '井底有骨' })).toMatchObject({
      entry: 'codex',
      node: { id: 'proposition:真相', type: 'proposition', ref: '真相', label: '井底有骨' },
    })

    expect(targetNodeToSelection({ type: 'relation', id: 'rel:甲乙', label: '师徒' })).toMatchObject({
      entry: 'codex',
      node: { id: 'cat:character_relation', type: 'codex_category', ref: 'character_relation', label: '角色关系' },
    })
  })

  it('maps timeline events and chapters back to manuscript targets', () => {
    expect(targetNodeToSelection({ type: 'event', id: 'ev:夜审', chapter: 5, label: '夜审' })).toMatchObject({
      entry: 'manuscript',
      node: { id: 'ch:5', type: 'chapter', ref: 5, label: '夜审' },
    })

    expect(targetNodeToSelection({ type: 'chapter', id: 'ch:7', ref: 7, label: '第七章' })).toMatchObject({
      entry: 'manuscript',
      node: { id: 'ch:7', type: 'chapter', ref: 7, label: '第七章' },
    })
  })

  it('maps material, promise and motif targets to their capability entries', () => {
    expect(targetNodeToSelection({ type: 'material', id: 'material:m1', label: '铜炉资料', meta: { kind: 'research' } })).toMatchObject({
      entry: 'materials',
      node: { id: 'material:m1', type: 'material', ref: 'm1', label: '铜炉资料', meta: { kind: 'research' } },
    })

    expect(targetNodeToSelection({ type: 'promise', id: 'promise:p1', label: '铜炉要回收', chapter: 4 })).toMatchObject({
      entry: 'promise',
      node: { id: 'promise:p1', type: 'promise_view', ref: 'open', label: '铜炉要回收', meta: { seq: 4 } },
    })

    expect(targetNodeToSelection({ type: 'motif', id: 'motif:m1', label: '借命回环', chapter: 6 })).toMatchObject({
      entry: 'motif',
      node: { id: 'motif:m1', type: 'motif_view', ref: 'book', label: '借命回环', meta: { seq: 6 } },
    })
  })
})

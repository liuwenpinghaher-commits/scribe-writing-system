import { describe, expect, it } from 'vitest'
import { targetNodeToSelection } from '../targetNavigation.js'

describe('targetNodeToSelection', () => {
  it('maps weak chapter targets to quality review with the chapter seq', () => {
    const next = targetNodeToSelection({
      type: 'weak_chapter',
      id: 'issue:weak:3',
      chapter: 3,
      title: '第3章 · 弱章诊断',
      reason: '该章有 20 个 QC 问题。',
      target_node: { id: 'ch:3', type: 'chapter', ref: 3, label: '第3章' },
    })

    expect(next).toMatchObject({
      entry: 'references',
      node: {
        id: 'quality:3',
        type: 'quality_review',
        ref: { seq: 3 },
        label: '第3章 · 弱章诊断',
      },
    })
  })

  it('maps 设定库分类到 codex 入口', () => {
    expect(targetNodeToSelection({
      type: 'codex_category',
      id: 'cat:character',
      ref: 'character',
      label: '角色',
    })).toMatchObject({
      entry: 'codex',
      node: { id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色' },
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

    // 具体母题叶 → 设定详情(CodexDetail),不是能力分组台账
    expect(targetNodeToSelection({ type: 'motif', id: 'motif:m1', label: '借命回环', chapter: 6 })).toMatchObject({
      entry: 'codex',
      node: { id: 'motif:m1', type: 'motif', ref: 'm1', label: '借命回环', meta: { seq: 6 } },
    })
    // 能力分组键 → MotifDetailPane
    expect(targetNodeToSelection({ type: 'motif_view', id: 'motif:book', ref: 'book', label: '全书母题' })).toMatchObject({
      entry: 'motif',
      node: { type: 'motif_view', ref: 'book' },
    })
  })

  it('maps view/atlas open-in-graph targets with atlasFocus (not codex entry)', () => {
    expect(targetNodeToSelection({
      type: 'view',
      id: 'view:atlas',
      viewKey: 'atlas',
      focus: 'role:小翠',
      meta: { focus: 'role:小翠' },
    })).toMatchObject({
      viewKey: 'atlas',
      atlasFocus: 'role:小翠',
      node: { type: 'view', id: 'view:atlas', viewKey: 'atlas' },
    })
    expect(targetNodeToSelection({ type: 'atlas', focus: 'faction:秘会' })).toMatchObject({
      viewKey: 'atlas',
      atlasFocus: 'faction:秘会',
    })
  })
})

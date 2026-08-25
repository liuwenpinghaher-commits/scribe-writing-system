import { describe, expect, it } from 'vitest'
import { selectionFromSnapshot } from './contextSelection.js'

describe('selectionFromSnapshot', () => {
  it('projects a chapter including its phase', () => {
    expect(selectionFromSnapshot({ detail_route: 'chapter:7', chapter: 7, phase: 'deduce', focus: { type: 'chapter', id: 'chapter:7', label: '第七章' } }, null)).toEqual({
      mode: 'node',
      node: { id: 'ch:7', type: 'chapter', ref: 7, label: '第七章', phase: 'deduce' },
    })
  })

  it('keeps a richer local selection when routes match', () => {
    const local = { mode: 'node', node: { id: 'material:abc', type: 'material', ref: 'material:abc', label: '原始标题', meta: { kind: 'note' } } }
    expect(selectionFromSnapshot({ detail_route: 'material:abc', focus: { type: 'material', id: 'material:abc', label: '标题' } }, local)).toBe(local)
  })

  // I-1:codex/material 节点的 ref 必须是【去前缀本地 id】,与 targetNodeToSelection 同形。
  // 若投影自造全限定 id 当 ref,CodexDetail/PropositionDetail/MaterialDetail 匹配落空、栏3 空白。
  it('projects a character with a local (prefix-stripped) ref', () => {
    const sel = selectionFromSnapshot({ detail_route: 'character:甲', focus: { type: 'character', id: 'character:甲', label: '甲' } }, null)
    expect(sel).toEqual({ mode: 'node', node: { id: 'character:甲', type: 'character', ref: '甲', label: '甲' } })
    expect(sel.node.ref).toBe('甲')   // 不是 'character:甲'
  })

  it('projects a proposition/fact with a local ref (PropositionDetail 拼 fact:${ref})', () => {
    const sel = selectionFromSnapshot({ detail_route: 'proposition:p1', focus: { type: 'fact', id: 'proposition:p1', label: '命题一' } }, null)
    expect(sel).toEqual({ mode: 'node', node: { id: 'proposition:p1', type: 'proposition', ref: 'p1', label: '命题一' } })
    expect(sel.node.ref).toBe('p1')   // 不是 'proposition:p1' / 'fact:proposition:p1'
  })

  it('projects a material with a local ref (MaterialDetail 按 row.id === ref)', () => {
    const sel = selectionFromSnapshot({ detail_route: 'material:m9', focus: { type: 'material', id: 'material:m9', label: '笔记' } }, null)
    expect(sel.mode).toBe('node')
    expect(sel.node.type).toBe('material')
    expect(sel.node.id).toBe('material:m9')
    expect(sel.node.ref).toBe('m9')   // 不是 'material:m9'
  })

  it('projects a promise as promise_view (→ PromiseDetailPane) with a local ref', () => {
    const sel = selectionFromSnapshot({ detail_route: 'promise:P1', focus: { type: 'promise', id: 'promise:P1', label: '伏笔一' } }, null)
    expect(sel.mode).toBe('node')
    expect(sel.node.type).toBe('promise_view')   // 不落到 CODEX_LEAF/CodexDetail
    expect(sel.node.ref).toBe('P1')
  })

  it('projects a concrete motif to codex leaf (→ CodexDetail), not capability group', () => {
    const sel = selectionFromSnapshot({ detail_route: 'motif:M1', focus: { type: 'motif', id: 'motif:M1', label: '母题一' } }, null)
    expect(sel.mode).toBe('node')
    expect(sel.node.type).toBe('motif')
    expect(sel.node.ref).toBe('M1')
  })

  it('projects quality_review to the quality workbench, not a fake view', () => {
    const sel = selectionFromSnapshot({
      entry: 'references',
      detail_route: 'quality:3',
      chapter: 3,
      focus: { type: 'quality_review', id: 'quality:3', label: '质量审阅' },
    }, null)
    expect(sel).toEqual({
      mode: 'node',
      node: {
        id: 'quality:3',
        type: 'quality_review',
        ref: { seq: 3 },
        meta: { seq: 3 },
        label: '质量审阅',
      },
    })
  })

  it('remaps a mistaken view:quality:N snapshot back to quality_review', () => {
    const sel = selectionFromSnapshot({
      entry: 'references',
      detail_route: 'quality:3',
      focus: { type: 'view', id: 'quality:3', label: '质量审阅' },
    }, { mode: 'node', node: null })
    expect(sel.node).toMatchObject({ id: 'quality:3', type: 'quality_review', ref: { seq: 3 } })
    expect(sel.mode).toBe('node')
  })

  it('projects a review_issue carrying payload/target_node (→ ReviewIssueDetail)', () => {
    const sel = selectionFromSnapshot({ detail_route: 'issue:weak:5', focus: { type: 'review_issue', id: 'issue:weak:5', label: '第5章诊断' } }, null)
    expect(sel.mode).toBe('node')
    expect(sel.node.type).toBe('review_issue')
    expect(sel.node.id).toBe('issue:weak:5')
    expect(sel.node).toHaveProperty('payload')
    expect(sel.node).toHaveProperty('target_node')
  })

  // I-3:章节判据必须以 focus.type 为准。带 ambient chapter 的角色 focus 不得被误投成章节。
  it('does not mistake a character focus for a chapter even when chapter is set', () => {
    const sel = selectionFromSnapshot({ detail_route: 'character:甲', chapter: 7, focus: { type: 'character', id: 'character:甲', label: '甲' } }, null)
    expect(sel.node.type).toBe('character')   // 不是 'chapter'
    expect(sel.node.ref).toBe('甲')
  })

  it('entry-only focus clears foreign domain detail but keeps sticky chapter', () => {
    const foreign = {
      mode: 'node',
      node: { id: 'promise:overdue', type: 'promise_view', capability: 'promise', label: '超期未收' },
    }
    const cleared = selectionFromSnapshot({
      entry: 'materials',
      detail_route: 'entry:materials',
      focus: { type: 'entry', id: 'entry:materials', label: '素材库' },
    }, foreign)
    expect(cleared).toEqual({ mode: 'node', node: null })

    const chapter = { mode: 'node', node: { id: 'ch:4', type: 'chapter', ref: 4, label: '4' } }
    const kept = selectionFromSnapshot({
      entry: 'search',
      detail_route: 'entry:search',
      focus: { type: 'entry', id: 'entry:search', label: '搜索' },
    }, chapter)
    expect(kept).toBe(chapter)
  })
})

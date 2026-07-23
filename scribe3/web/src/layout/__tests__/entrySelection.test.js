import { describe, expect, it } from 'vitest'
import {
  defaultLandingNode,
  emptyDetailCopy,
  nodeCompatibleWithEntry,
  planEntryChange,
  resolveEntrySelection,
} from '../entrySelection'

describe('entrySelection · 入口与栏3 域兼容', () => {
  it('写作粘性节点跨入口保留', () => {
    const ch = { id: 'ch:4', type: 'chapter', ref: 4, label: '4' }
    expect(nodeCompatibleWithEntry(ch, 'materials')).toBe(true)
    expect(nodeCompatibleWithEntry(ch, 'promise')).toBe(true)
    expect(resolveEntrySelection('materials', ch, {}).action).toBe('keep')
  })

  it('伏笔详情与素材库入口不兼容,落到 material_root', () => {
    const promiseView = {
      id: 'promise:overdue',
      type: 'promise_view',
      capability: 'promise',
      label: '超期未收',
      ref: { view: 'overdue', seq: 3 },
    }
    expect(nodeCompatibleWithEntry(promiseView, 'materials')).toBe(false)
    const decision = resolveEntrySelection('materials', promiseView, {
      materials: { id: 'material_root', type: 'material_root', label: '素材库' },
    })
    expect(decision).toEqual({
      action: 'land',
      node: expect.objectContaining({ type: 'material_root', id: 'material_root', label: '素材库' }),
    })
  })

  it('素材叶切到伏笔入口时清空栏3', () => {
    const mat = { id: 'material:1', type: 'material', ref: 1, label: 'A' }
    expect(nodeCompatibleWithEntry(mat, 'promise')).toBe(false)
    expect(resolveEntrySelection('promise', mat, {}).action).toBe('clear')
  })

  it('同域节点 keep', () => {
    const mat = { id: 'material:1', type: 'material', ref: 1, label: 'A' }
    expect(resolveEntrySelection('materials', mat, {}).action).toBe('keep')
    const group = {
      id: 'promise:open',
      type: 'capability_group',
      capability: 'promise',
      label: '待回收',
    }
    expect(resolveEntrySelection('promise', group, {}).action).toBe('keep')
  })

  it('defaultLandingNode 内容三根与参考作品', () => {
    expect(defaultLandingNode('materials', null).type).toBe('material_root')
    expect(defaultLandingNode('codex', null).type).toBe('codex_root')
    expect(defaultLandingNode('manuscript', null).type).toBe('manuscript_root')
    expect(defaultLandingNode('references', null).type).toBe('references')
    expect(defaultLandingNode('promise', null)).toBeNull()
  })

  it('planEntryChange 伏笔→素材落地 nodePatch', () => {
    const promiseView = {
      id: 'promise:overdue', type: 'promise_view', capability: 'promise', label: '超期未收',
    }
    const plan = planEntryChange('materials', promiseView, { materials: { id: 'material_root', label: '素材库' } }, '素材库')
    expect(plan.select).toEqual(expect.objectContaining({ type: 'material_root' }))
    expect(plan.patch.entry).toBe('materials')
    expect(plan.patch.detail_route).toMatch(/material/)
  })

  it('emptyDetailCopy 按域给文案', () => {
    expect(emptyDetailCopy('materials').hint).toMatch(/素材/)
    expect(emptyDetailCopy('search').hint).toMatch(/搜索/)
  })
})

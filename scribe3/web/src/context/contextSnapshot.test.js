import { describe, it, expect } from 'vitest'
import {
  reduceSnapshot, semanticIntent, bootstrapSnapshot,
  focusForNode, detailRouteForNode, entryPatch, nodePatch,
} from './contextSnapshot'

// 一份"服务端形状"的快照样本(与 context_models.ContextSnapshot 字段对齐)
function snap(over = {}) {
  return {
    session_id: 'ctx:1',
    work: 'demo',
    revision: 3,
    entry: 'manuscript',
    directory_path: ['manuscript'],
    focus: { type: 'entry', id: 'entry:manuscript', label: '' },
    detail_route: 'entry:manuscript',
    chapter: null,
    phase: null,
    focalizer: null,
    previous_revision: 2,
    navigation_id: 'nav-prev',
    context_hash: 'h3',
    ...over,
  }
}

function intent(over = {}) {
  return {
    navigation_id: 'nav-1',
    expected_revision: 3,
    entry: 'codex',
    directory_path: ['codex'],
    focus: { type: 'entry', id: 'entry:codex', label: '设定库' },
    detail_route: 'entry:codex',
    reason: 'entry',
    ...over,
  }
}

describe('reduceSnapshot(纯 reducer)', () => {
  it('current 缺失时抛 context_snapshot_missing', () => {
    expect(() => reduceSnapshot(null, intent())).toThrow('context_snapshot_missing')
  })

  it('expected_revision 失配时抛 stale_context', () => {
    expect(() => reduceSnapshot(snap({ revision: 5 }), intent({ expected_revision: 3 })))
      .toThrow('stale_context')
  })

  it('CAS 命中时整体推进:revision+1、previous_revision 记录、语义字段全量替换', () => {
    const current = snap()
    const next = reduceSnapshot(current, intent({
      chapter: 7, phase: 'draft', focalizer: '小翠',
    }))
    expect(next.revision).toBe(4)
    expect(next.previous_revision).toBe(3)
    expect(next.entry).toBe('codex')
    expect(next.directory_path).toEqual(['codex'])
    expect(next.focus).toEqual({ type: 'entry', id: 'entry:codex', label: '设定库' })
    expect(next.detail_route).toBe('entry:codex')
    expect(next.chapter).toBe(7)
    expect(next.phase).toBe('draft')
    expect(next.focalizer).toBe('小翠')
    expect(next.navigation_id).toBe('nav-1')
    // 会话身份字段随 ...current 保留
    expect(next.session_id).toBe('ctx:1')
    expect(next.work).toBe('demo')
    // 乐观快照 hash 失效是 reducer 的责任(hash 是服务端快照的身份指纹,本地推进即失真)
    expect(next.context_hash).toBeNull()
  })

  it('intent 未带 chapter/phase/focalizer 时归 null(完整语义状态,不残留旧值)', () => {
    const next = reduceSnapshot(snap({ chapter: 7, phase: 'draft', focalizer: '小翠' }), intent())
    expect(next.chapter).toBeNull()
    expect(next.phase).toBeNull()
    expect(next.focalizer).toBeNull()
  })

  it('不原地修改 current,数组/对象为拷贝', () => {
    const current = snap()
    const it2 = intent()
    const next = reduceSnapshot(current, it2)
    expect(current.revision).toBe(3)
    expect(current.entry).toBe('manuscript')
    expect(next.directory_path).not.toBe(it2.directory_path)
    expect(next.focus).not.toBe(it2.focus)
  })
})

describe('semanticIntent(意图构造)', () => {
  it('自动带 navigation_id(唯一)与 expected_revision(当前 revision)', () => {
    const a = semanticIntent(snap(), { focus: { type: 'chapter', id: 'chapter:7' }, detail_route: 'chapter:7', reason: 'item' })
    const b = semanticIntent(snap(), { focus: { type: 'chapter', id: 'chapter:7' }, detail_route: 'chapter:7', reason: 'item' })
    expect(typeof a.navigation_id).toBe('string')
    expect(a.navigation_id.length).toBeGreaterThan(0)
    expect(a.navigation_id).not.toBe(b.navigation_id)
    expect(a.expected_revision).toBe(3)
  })

  it('entry/directory_path 未给时回退快照当前值;chapter/phase/focalizer 未给时归 null', () => {
    const it2 = semanticIntent(snap({ chapter: 9 }), {
      focus: { type: 'character', id: 'character:甲' }, detail_route: 'character:甲', reason: 'item',
    })
    expect(it2.entry).toBe('manuscript')
    expect(it2.directory_path).toEqual(['manuscript'])
    expect(it2.chapter).toBeNull()
    expect(it2.phase).toBeNull()
    expect(it2.focalizer).toBeNull()
    expect(it2.reason).toBe('item')
  })
})

describe('focus/route 投影辅助', () => {
  it('入口 patch:完整 NavigationIntent 语义(entry/path/focus/route/reason)', () => {
    expect(entryPatch('codex', '设定库')).toEqual({
      entry: 'codex',
      directory_path: ['codex'],
      focus: { type: 'entry', id: 'entry:codex', label: '设定库' },
      detail_route: 'entry:codex',
      reason: 'entry',
    })
  })

  it('章节点 patch:chapter/phase 上快照,route=chapter:seq', () => {
    const node = { id: 'ch:7', type: 'chapter', ref: 7, label: '7 长夜', phase: 'draft' }
    expect(nodePatch(node, 'manuscript')).toEqual({
      entry: 'manuscript',
      directory_path: ['manuscript', 'ch:7'],
      focus: { type: 'chapter', id: 'chapter:7', label: '7 长夜' },
      detail_route: 'chapter:7',
      chapter: 7,
      phase: 'draft',
      reason: 'item',
    })
  })

  it('focus 类型映射:proposition→fact,后端白名单外的类型兜底 view', () => {
    expect(focusForNode({ id: 'proposition:p1', type: 'proposition', ref: 'p1' }).type).toBe('fact')
    expect(focusForNode({ id: 'character:甲', type: 'character', ref: '甲' }).type).toBe('character')
    expect(focusForNode({ id: 'cat:character', type: 'codex_category', ref: 'character' }).type).toBe('view')
    expect(focusForNode({ id: 'quality:3', type: 'quality_review', ref: { seq: 3 }, label: '质量审阅' })).toEqual({
      type: 'quality_review', id: 'quality:3', label: '质量审阅',
    })
    expect(focusForNode({ id: 'material:1', type: 'material', ref: 1 }).type).toBe('material')
    expect(focusForNode(null)).toEqual({ type: 'view', id: 'view:empty', label: '' })
  })

  it('弱章质量审阅 patch:焦点是 quality_review，不是 view', () => {
    const node = { id: 'quality:3', type: 'quality_review', ref: { seq: 3 }, meta: { seq: 3 }, label: '质量审阅' }
    expect(nodePatch(node, 'references')).toEqual({
      entry: 'references',
      directory_path: ['references', 'quality:3'],
      focus: { type: 'quality_review', id: 'quality:3', label: '质量审阅' },
      detail_route: 'quality:3',
      chapter: 3,
      phase: null,
      reason: 'item',
    })
  })

  it('detail_route:章走 chapter:seq,其余用节点 id', () => {
    expect(detailRouteForNode({ id: 'ch:7', type: 'chapter', ref: 7 })).toBe('chapter:7')
    expect(detailRouteForNode({ id: 'character:甲', type: 'character' })).toBe('character:甲')
    expect(detailRouteForNode(null)).toBe('empty')
  })
})

describe('bootstrapSnapshot(降级基座)', () => {
  it('revision=0、无会话身份、entry 留空(消费端回退本地投影)', () => {
    const s = bootstrapSnapshot('demo')
    expect(s.revision).toBe(0)
    expect(s.session_id).toBeNull()
    expect(s.entry).toBeNull()
    expect(s.navigation_id).toBeNull()
    expect(s.context_hash).toBeNull()
    expect(s.work).toBe('demo')
  })
})

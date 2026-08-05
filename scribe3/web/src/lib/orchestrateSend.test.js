/**
 * 编排发送路径结构契约（无 vitest 时可用 node 跑不了 jsx；此处供已有 vitest 环境）。
 * 主门禁在 pytest test_orchestration；本文件断言模块导出与弱回退语义。
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { shouldUseHermesRun, isWorldWriteForceSeed } from './hermesRunIntent.js'
import { applyUiEvents, uiDirectiveToEvents, focusFromSelectionDetail } from './uiDirective.js'

afterEach(() => { vi.restoreAllMocks() })

describe('hermesRunIntent demoted to weak feature', () => {
  it('force seed still hits world-write path', () => {
    expect(isWorldWriteForceSeed('请 s3_patch_character 更新角色')).toBe(true)
    expect(shouldUseHermesRun('提交写入提案供我批准')).toBe(true)
  })
  it('plain chat does not force run', () => {
    expect(shouldUseHermesRun('这个角色设定我喜欢')).toBe(false)
  })
})

describe('uiDirectiveToEvents three domains', () => {
  it('character codex directive', () => {
    const evs = uiDirectiveToEvents({
      entry: 'codex',
      right_tab: 'chief',
      node: { type: 'character', id: 'role:沈砚', label: '沈砚' },
    })
    expect(evs.some((e) => e.type === 'selection' && e.detail.node.type === 'character')).toBe(true)
    expect(evs.some((e) => e.type === 's3-open-capability')).toBe(true)
  })
  it('outline chapter phase', () => {
    const evs = uiDirectiveToEvents({
      entry: 'manuscript',
      phase: 'outline',
      right_tab: 'chief',
      node: { type: 'chapter', ref: 4, id: 'ch:4' },
    })
    expect(evs.some((e) => e.type === 's3-chapter-phase' && e.detail.phase === 'outline' && e.detail.seq === 4)).toBe(true)
  })
  it('promise node + panel', () => {
    const evs = uiDirectiveToEvents({
      entry: 'manuscript',
      node: { type: 'promise', id: 'p1', label: '铜炉' },
      right_tab: 'chief',
      panel: 'promise',
    })
    expect(evs.some((e) => e.type === 'selection' && e.detail.node.type === 'promise')).toBe(true)
    expect(evs.some((e) => e.type === 's3-ui-directive' && e.detail.panel === 'promise')).toBe(true)
    expect(evs.some((e) => e.type === 's3-open-capability' && e.detail.capability === 'promise')).toBe(true)
  })
})

describe('applyUiEvents selection never silent-drop', () => {
  it('without onSel dispatches s3-selection and setFocus', () => {
    const setFocus = vi.fn()
    const selSpy = vi.fn()
    window.addEventListener('s3-selection', selSpy)
    applyUiEvents([
      {
        type: 'selection',
        detail: { mode: 'node', node: { id: 'role:沈砚', type: 'character', label: '沈砚' } },
      },
    ], { setFocus })
    window.removeEventListener('s3-selection', selSpy)
    expect(selSpy).toHaveBeenCalled()
    expect(setFocus).toHaveBeenCalledWith(expect.objectContaining({
      type: 'character', id: 'role:沈砚', label: '沈砚', origin: 'orchestration',
    }))
  })
  it('with onSel calls onSel', () => {
    const onSel = vi.fn()
    applyUiEvents([
      { type: 'selection', detail: { mode: 'node', node: { type: 'promise', id: 'p1' } } },
    ], { onSel })
    expect(onSel).toHaveBeenCalledWith(expect.objectContaining({ mode: 'node' }))
  })
  it('focusFromSelectionDetail maps node', () => {
    expect(focusFromSelectionDetail({
      mode: 'node', node: { type: 'chapter', id: 'ch:3', ref: 3, label: '第3章' },
    })).toMatchObject({ type: 'chapter', id: 'ch:3', origin: 'orchestration' })
  })
})

import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  handleSelAction,
  openChiefForEmptyField,
  openChiefForSelection,
  selDiscussPrompt,
  selEditPrompt,
  truncateQuote,
} from './selAction.js'

vi.mock('./chiefSeed.js', () => ({
  focusChiefWithSeed: vi.fn((t) => t),
}))

import { focusChiefWithSeed } from './chiefSeed.js'

describe('selAction', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('truncateQuote 超长截断', () => {
    expect(truncateQuote('短')).toBe('短')
    expect(truncateQuote('x'.repeat(900)).endsWith('…')).toBe(true)
    expect(truncateQuote('x'.repeat(900)).length).toBe(801)
  })

  it('discuss/edit 话术含 scope 与引用', () => {
    expect(selDiscussPrompt('素材', '城墙')).toMatch(/素材/)
    expect(selDiscussPrompt('素材', '城墙')).toMatch(/城墙/)
    expect(selDiscussPrompt('素材', '城墙')).toMatch(/聊聊/)
    expect(selEditPrompt('草稿', '晨雾')).toMatch(/改一下/)
    expect(selEditPrompt('草稿', '晨雾')).toMatch(/晨雾/)
  })

  it('openChiefForSelection 空文本不发', () => {
    expect(openChiefForSelection({ text: '  ' })).toBe(false)
    expect(focusChiefWithSeed).not.toHaveBeenCalled()
  })

  it('openChiefForSelection discuss/edit 调 focusChiefWithSeed', () => {
    expect(openChiefForSelection({ intent: 'discuss', text: '甲', scopeLabel: '设定' })).toBe(true)
    expect(focusChiefWithSeed).toHaveBeenCalledWith(expect.stringMatching(/设定[\s\S]*甲/))
    focusChiefWithSeed.mockClear()
    openChiefForSelection({ intent: 'edit', text: '乙', scopeLabel: '素材' })
    expect(focusChiefWithSeed).toHaveBeenCalledWith(expect.stringMatching(/改一下[\s\S]*乙/))
  })

  it('handleSelAction 优先自定义 onEdit/onDiscuss', () => {
    const onEdit = vi.fn()
    const onDiscuss = vi.fn()
    handleSelAction({ text: 't', intent: 'edit' }, { onEdit, onDiscuss })
    expect(onEdit).toHaveBeenCalledWith('t')
    expect(focusChiefWithSeed).not.toHaveBeenCalled()
    handleSelAction({ text: 'u', intent: 'discuss' }, { onEdit, onDiscuss })
    expect(onDiscuss).toHaveBeenCalledWith('u')
  })

  it('openChiefForEmptyField 空字段指定实体+字段进主编', () => {
    expect(openChiefForEmptyField({ entityLabel: '甲', fieldLabel: '外貌', fieldKey: 'appearance' })).toBe(true)
    expect(focusChiefWithSeed).toHaveBeenCalledWith(expect.stringMatching(/甲[\s\S]*外貌[\s\S]*appearance/))
    expect(focusChiefWithSeed).toHaveBeenCalledWith(expect.stringMatching(/当前为空/))
  })
})

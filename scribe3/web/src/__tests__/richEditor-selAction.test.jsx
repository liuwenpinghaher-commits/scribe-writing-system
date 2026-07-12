import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { RichEditor } from '../editor/RichEditor.jsx'

// jsdom 的 Range 未实现 getBoundingClientRect/getClientRects,BubbleMenu 底层 floating-ui
// 定位时会抛错(不影响我们要断言的"按钮存不存在/点击回调"语义)。补零值 polyfill 让真实
// 文本选区能触发 BubbleMenu 显示(选中→有焦点+非空选区→插件把气泡元素挂进 DOM)。
beforeAll(() => {
  const zeroRect = () => ({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0, toJSON() { return this } })
  Range.prototype.getBoundingClientRect = zeroRect
  Range.prototype.getClientRects = () => ({ length: 0, item: () => null, [Symbol.iterator]: function* () {} })
})

// 用真实浏览器 Selection API 在 contenteditable 里选中全部文本,派发 selectionchange 让
// ProseMirror 读取选区、更新 editor.state.selection,进而让 BubbleMenuPlugin 显示气泡。
async function selectAllText(container) {
  const editable = container.querySelector('[contenteditable="true"]')
  editable.focus()
  await waitFor(() => expect(editable.querySelector('p')).toBeTruthy())
  const p = editable.querySelector('p')
  const textNode = p.firstChild
  const range = document.createRange()
  range.setStart(textNode, 0)
  range.setEnd(textNode, textNode.length)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
  document.dispatchEvent(new Event('selectionchange'))
  return editable
}

describe('RichEditor 气泡选区动作(聊这段/改这段)', () => {
  it('不传 onSelAction:选中文本后气泡内无「改这段」「聊这段」(与现状逐字一致)', async () => {
    const { container } = render(<RichEditor value="选中的这段文字" onChange={() => {}} />)
    await selectAllText(container)
    // 先确认气泡确实弹出了(排版钮可见),排除"选区没生效导致误判"
    await waitFor(() => expect(screen.queryByTitle('加粗')).toBeTruthy())
    expect(screen.queryByTitle('让主编改这段')).toBeNull()
    expect(screen.queryByTitle('就这段和主编讨论(不改稿)')).toBeNull()
  })

  it('minimal 模式:即使传 onSelAction 气泡也不出现(现状不变)', () => {
    const onSelAction = vi.fn()
    render(<RichEditor value="选中的这段文字" onChange={() => {}} minimal onSelAction={onSelAction} />)
    expect(screen.queryByTitle('让主编改这段')).toBeNull()
    expect(screen.queryByTitle('就这段和主编讨论(不改稿)')).toBeNull()
    expect(screen.queryByTitle('加粗')).toBeNull()
  })

  it('传 onSelAction 且选区非空:两钮出现;点「聊这段」→ onSelAction({text, intent:"discuss"})', async () => {
    const onSelAction = vi.fn()
    const { container } = render(<RichEditor value="选中的这段文字" onChange={() => {}} onSelAction={onSelAction} />)
    await selectAllText(container)

    const discussBtn = await screen.findByTitle('就这段和主编讨论(不改稿)')
    const editBtn = screen.getByTitle('让主编改这段')
    expect(discussBtn).toBeTruthy()
    expect(editBtn).toBeTruthy()

    discussBtn.click()
    expect(onSelAction).toHaveBeenCalledTimes(1)
    expect(onSelAction).toHaveBeenCalledWith({ text: '选中的这段文字', intent: 'discuss' })
  })

  it('点「改这段」→ onSelAction({text, intent:"edit"})', async () => {
    const onSelAction = vi.fn()
    const { container } = render(<RichEditor value="选中的这段文字" onChange={() => {}} onSelAction={onSelAction} />)
    await selectAllText(container)

    const editBtn = await screen.findByTitle('让主编改这段')
    editBtn.click()
    expect(onSelAction).toHaveBeenCalledTimes(1)
    expect(onSelAction).toHaveBeenCalledWith({ text: '选中的这段文字', intent: 'edit' })
  })
})

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, act, waitFor } from '@testing-library/react'
import { SelectionQuoteActions } from './SelectionQuoteActions.jsx'

const openChief = vi.hoisted(() => vi.fn())
const saveClip = vi.hoisted(() => vi.fn(async () => ({ id: 'm1', title: '摘录' })))
const citeSel = vi.hoisted(() => vi.fn(() => 'seed'))
const toast = vi.hoisted(() => vi.fn())

vi.mock('../lib/selAction.js', () => ({
  openChiefForSelection: (...a) => openChief(...a),
}))
vi.mock('../lib/sessionClip.js', () => ({
  saveSessionClipAsMaterial: (...a) => saveClip(...a),
  seedCiteSelection: (...a) => citeSel(...a),
}))
vi.mock('./Toast.jsx', () => ({
  showToast: (...a) => toast(...a),
}))

function selectTextIn(el, text) {
  const range = document.createRange()
  const node = el.childNodes[0]
  range.setStart(node, 0)
  range.setEnd(node, text.length)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
}

async function selectAndShowBar(text) {
  render(
    <SelectionQuoteActions scopeLabel="会话" chapterSeq={3} originLabel="主编会话">
      <p>{text}</p>
    </SelectionQuoteActions>,
  )
  const p = screen.getByText(text)
  selectTextIn(p, text)
  await act(async () => {
    fireEvent.mouseUp(document)
    await new Promise((r) => requestAnimationFrame(r))
  })
  return screen.findByTestId('selection-quote-bar')
}

describe('SelectionQuoteActions', () => {
  beforeEach(() => {
    openChief.mockClear()
    saveClip.mockClear()
    citeSel.mockClear()
    toast.mockClear()
  })
  afterEach(() => {
    window.getSelection()?.removeAllRanges()
  })

  it('划选后浮窗为 存 / 引入会话 / 聊', async () => {
    await selectAndShowBar('这段大纲可以划选讨论')
    expect(screen.getByTestId('selection-save-material').textContent).toMatch(/存/)
    expect(screen.getByTestId('selection-cite-session').textContent).toMatch(/引入会话/)
    expect(screen.getByTestId('selection-discuss').textContent).toMatch(/聊/)
  })

  it('聊：送主编讨论', async () => {
    await selectAndShowBar('这段大纲可以划选讨论')
    fireEvent.click(screen.getByTestId('selection-discuss'))
    expect(openChief).toHaveBeenCalledWith(expect.objectContaining({
      intent: 'discuss',
      text: '这段大纲可以划选讨论',
      scopeLabel: '会话',
    }))
  })

  it('引入会话：seed 选区进 compose', async () => {
    await selectAndShowBar('值得以后用的句子')
    fireEvent.click(screen.getByTestId('selection-cite-session'))
    expect(citeSel).toHaveBeenCalledWith(expect.objectContaining({
      text: '值得以后用的句子',
      scopeLabel: '会话',
    }))
    expect(toast).toHaveBeenCalled()
  })

  it('存：直写素材库(saveSessionClipAsMaterial)，不走主编审批种子', async () => {
    await selectAndShowBar('值得以后用的句子')
    fireEvent.click(screen.getByTestId('selection-save-material'))
    await waitFor(() => {
      expect(saveClip).toHaveBeenCalledWith(expect.objectContaining({
        text: '值得以后用的句子',
        kind: 'snippet',
        scopeLabel: '会话',
        chapterSeq: 3,
        originLabel: '主编会话',
      }))
    })
    expect(openChief).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/已存入素材库/), expect.anything())
    })
  })

  it('disabled 时不出现工具条', async () => {
    render(
      <SelectionQuoteActions scopeLabel="空" disabled>
        <p>不可划选动作</p>
      </SelectionQuoteActions>,
    )
    const p = screen.getByText('不可划选动作')
    selectTextIn(p, '不可划选动作')
    await act(async () => {
      fireEvent.mouseUp(document)
      await new Promise((r) => requestAnimationFrame(r))
    })
    expect(screen.queryByTestId('selection-quote-bar')).toBeNull()
  })
})

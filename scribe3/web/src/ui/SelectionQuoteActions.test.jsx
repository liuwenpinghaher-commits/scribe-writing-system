import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, act } from '@testing-library/react'
import { SelectionQuoteActions } from './SelectionQuoteActions.jsx'

const openChief = vi.hoisted(() => vi.fn())
vi.mock('../lib/selAction.js', () => ({
  openChiefForSelection: (...a) => openChief(...a),
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

describe('SelectionQuoteActions', () => {
  beforeEach(() => {
    openChief.mockClear()
  })
  afterEach(() => {
    window.getSelection()?.removeAllRanges()
  })

  it('划选宿主内文本后出现聊/改按钮并送主编', async () => {
    render(
      <SelectionQuoteActions scopeLabel="大纲">
        <p>这段大纲可以划选讨论</p>
      </SelectionQuoteActions>,
    )
    const host = screen.getByTestId('selection-quote-host')
    const p = host.querySelector('p')
    selectTextIn(p, '这段大纲可以划选讨论')
    await act(async () => {
      fireEvent.mouseUp(document)
      await new Promise((r) => requestAnimationFrame(r))
    })
    expect(await screen.findByTestId('selection-quote-bar')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /聊这段/ }))
    expect(openChief).toHaveBeenCalledWith(expect.objectContaining({
      intent: 'discuss',
      text: '这段大纲可以划选讨论',
      scopeLabel: '大纲',
    }))
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

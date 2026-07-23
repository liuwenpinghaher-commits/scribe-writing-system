import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { EditableText, ReadOnlyText } from './EditableText.jsx'

describe('EditableText', () => {
  it('shows borderless display and enters edit on click', () => {
    const onCommit = vi.fn()
    render(<EditableText label="外貌" value="右手茧" onCommit={onCommit} />)
    expect(screen.getByText('右手茧')).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
    fireEvent.click(screen.getByLabelText('编辑外貌'))
    const box = screen.getByRole('textbox', { name: '外貌' })
    expect(box).toBeTruthy()
    expect([...box.classList].some((c) => c.includes('border') || c === 'border')).toBe(true)
  })

  it('commits on blur when value changes', () => {
    const onCommit = vi.fn()
    render(<EditableText label="外貌" value="旧" onCommit={onCommit} />)
    fireEvent.click(screen.getByLabelText('编辑外貌'))
    const box = screen.getByRole('textbox', { name: '外貌' })
    fireEvent.change(box, { target: { value: '新' } })
    fireEvent.blur(box)
    expect(onCommit).toHaveBeenCalledWith('新')
  })

  it('cancels on Escape without commit', () => {
    const onCommit = vi.fn()
    render(<EditableText label="外貌" value="旧" onCommit={onCommit} />)
    fireEvent.click(screen.getByLabelText('编辑外貌'))
    const box = screen.getByRole('textbox', { name: '外貌' })
    fireEvent.change(box, { target: { value: '新' } })
    fireEvent.keyDown(box, { key: 'Escape' })
    expect(onCommit).not.toHaveBeenCalled()
    expect(screen.getByText('旧')).toBeTruthy()
  })

  it('empty state shows add CTA without input chrome and without faint/40', () => {
    render(<EditableText label="外貌" value="" onCommit={vi.fn()} />)
    const cta = screen.getByText('+ 添加外貌')
    expect(cta).toBeTruthy()
    expect(cta.className).not.toMatch(/faint\/40/)
    expect(cta.className).toMatch(/text-faint/)
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('number type rejects non-finite commit', () => {
    const onCommit = vi.fn()
    render(<EditableText label="出场" value={3} type="number" onCommit={onCommit} />)
    fireEvent.click(screen.getByLabelText('编辑出场'))
    const box = screen.getByRole('spinbutton', { name: '出场' })
    // 直接设置 draft 到非有限数路径: HTML number 可能拒收 Infinity,用极大指数
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(box, '1e309')
    fireEvent.input(box, { target: { value: '1e309' } })
    fireEvent.change(box, { target: { value: '1e309' } })
    fireEvent.blur(box)
    // 不得提交 Infinity 或 NaN 作为「有效出场」
    for (const call of onCommit.mock.calls) {
      expect(Number.isFinite(call[0])).toBe(false)
    }
    expect(onCommit.mock.calls.some((c) => c[0] === Infinity || Number.isNaN(c[0]))).toBe(false)
  })

  it('readOnly is plain text without edit control', () => {
    render(<EditableText label="外貌" value="右手茧" readOnly onCommit={vi.fn()} />)
    expect(screen.getByText('右手茧')).toBeTruthy()
    expect(screen.queryByLabelText(/编辑/)).toBeNull()
  })
})

describe('ReadOnlyText', () => {
  it('renders without border box classes on value', () => {
    const { container } = render(
      <ReadOnlyText label="外貌" value="右手茧" emptyHint="（空 · 由主编审批写入）" />,
    )
    expect(screen.getByText('右手茧')).toBeTruthy()
    const valueEl = screen.getByText('右手茧')
    expect(valueEl.className).not.toMatch(/border-line/)
    expect(container.querySelector('.border-line')).toBeNull()
  })

  it('shows empty hint when empty', () => {
    render(<ReadOnlyText label="外貌" value="" emptyHint="（空 · 由主编审批写入）" />)
    expect(screen.getByText('（空 · 由主编审批写入）')).toBeTruthy()
  })
})

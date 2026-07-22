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

  it('empty state shows add CTA without input chrome', () => {
    render(<EditableText label="外貌" value="" onCommit={vi.fn()} />)
    expect(screen.getByText('+ 添加外貌')).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
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

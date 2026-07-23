import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Btn } from '../ui.jsx'
import { Field } from './Field.jsx'
import { Tabs } from './Tabs.jsx'
import { AsyncState } from './AsyncState.jsx'

const accessibleDescription = (element) => (element.getAttribute('aria-describedby') || '')
  .split(/\s+/)
  .filter(Boolean)
  .map((id) => document.getElementById(id)?.textContent)
  .filter(Boolean)
  .join(' ')

describe('PC UI primitives', () => {
  it('associates field label, description and error', () => {
    render(<Field label="标题" description="用于目录显示" error="不能为空" required><input /></Field>)
    const input = screen.getByRole('textbox', { name: /标题/ })
    expect(input.required).toBe(true)
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(accessibleDescription(input)).toBe('用于目录显示 不能为空')
  })

  it('moves focus and selection with arrow keys', () => {
    const onChange = vi.fn()
    render(<Tabs ariaLabel="章节阶段" value="outline" onValueChange={onChange}
      items={[{ value: 'outline', label: '大纲' }, { value: 'beats', label: '节拍' }]} />)
    const outline = screen.getByRole('tab', { name: '大纲' })
    const beats = screen.getByRole('tab', { name: '节拍' })
    outline.focus()
    fireEvent.keyDown(outline, { key: 'ArrowRight' })
    expect(onChange).toHaveBeenCalledWith('beats')
    expect(document.activeElement).toBe(beats)
  })

  it('uses status and alert semantics', () => {
    const { rerender } = render(<AsyncState state="loading" title="加载目录" />)
    expect(screen.getByRole('status')).not.toBeNull()
    rerender(<AsyncState state="error" title="目录加载失败" onRetry={() => {}} />)
    expect(screen.getByRole('alert')).not.toBeNull()
    expect(screen.getByRole('button', { name: '重试' })).not.toBeNull()
  })

  it('renders ready content without a status wrapper', () => {
    render(<AsyncState state="ready" title="已加载"><div>目录内容</div></AsyncState>)
    expect(screen.getByText('目录内容')).not.toBeNull()
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('keeps icon buttons accessible at PC sizes', () => {
    render(<>
      <Btn icon size="xs" aria-label="收起目录" />
      <Btn icon size="sm" aria-label="展开目录" />
      <Btn icon size="md" aria-label="打开主编" />
    </>)
    const xs = screen.getByRole('button', { name: '收起目录' })
    const sm = screen.getByRole('button', { name: '展开目录' })
    const md = screen.getByRole('button', { name: '打开主编' })
    expect([...xs.classList]).toEqual(expect.arrayContaining(['h-8', 'w-8']))
    expect([...sm.classList]).toEqual(expect.arrayContaining(['h-8', 'w-8']))
    expect([...md.classList]).toEqual(expect.arrayContaining(['h-9', 'w-9']))
  })

  it('Input defaults to ghost and supports bordered', async () => {
    const { Input } = await import('../ui.jsx')
    const { rerender } = render(<Input aria-label="g" />)
    const g = screen.getByLabelText('g')
    expect([...g.classList]).toEqual(expect.arrayContaining(['border-transparent']))
    rerender(<Input aria-label="b" variant="bordered" />)
    const b = screen.getByLabelText('b')
    expect([...b.classList].some((c) => c.startsWith('border-line'))).toBe(true)
  })

  it('Btn/Input use compact rounded-md and never wrap label text', async () => {
    const { Input } = await import('../ui.jsx')
    render(
      <>
        <Btn>导入</Btn>
        <Input aria-label="title" />
      </>,
    )
    const btn = screen.getByRole('button', { name: '导入' })
    expect(btn.className).toMatch(/rounded-md/)
    expect(btn.className).toMatch(/whitespace-nowrap/)
    expect(btn.className).not.toMatch(/rounded-xl/)
    expect(screen.getByLabelText('title').className).toMatch(/rounded-md/)
  })
})


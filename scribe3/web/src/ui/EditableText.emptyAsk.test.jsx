import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ReadOnlyText } from './EditableText.jsx'

const openEmpty = vi.hoisted(() => vi.fn())
vi.mock('../lib/selAction.js', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    openChiefForEmptyField: (...a) => openEmpty(...a),
  }
})

describe('ReadOnlyText 空字段聊聊', () => {
  beforeEach(() => openEmpty.mockClear())

  it('空值显示聊聊怎么写并带上条目/字段', () => {
    render(
      <ReadOnlyText
        label="外貌"
        value=""
        emptyHint="（空 · 由主编审批写入）"
        entityLabel="柳怀玉"
        fieldKey="appearance"
      />,
    )
    expect(screen.getByText('（空 · 由主编审批写入）')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '聊聊怎么写' }))
    expect(openEmpty).toHaveBeenCalledWith({
      entityLabel: '柳怀玉',
      fieldLabel: '外貌',
      fieldKey: 'appearance',
    })
  })

  it('有内容时不显示空字段按钮', () => {
    render(<ReadOnlyText label="外貌" value="青衫" entityLabel="甲" />)
    expect(screen.queryByRole('button', { name: '聊聊怎么写' })).toBeNull()
    expect(screen.getByText('青衫')).toBeTruthy()
  })
})

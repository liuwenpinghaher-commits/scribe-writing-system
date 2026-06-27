import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { InputDialog } from './Dialog.jsx'

describe('InputDialog', () => {
  it('确认回传输入值', () => {
    const onConfirm = vi.fn(); const onClose = vi.fn()
    render(<InputDialog open title="起名" defaultValue="" onConfirm={onConfirm} onClose={onClose} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '重写结尾前' } })
    fireEvent.click(screen.getByText('确认'))
    expect(onConfirm).toHaveBeenCalledWith('重写结尾前')
  })
  it('Esc 关闭', () => {
    const onClose = vi.fn()
    render(<InputDialog open title="x" onConfirm={() => {}} onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})

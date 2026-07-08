import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { WriteChat } from '../WriteChat'
import { api } from '../api'

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo_work'),
  addIdea: vi.fn(),
  chatWrite: vi.fn((_msg, opts) => {
    opts.onDone?.()
    return { abort: vi.fn() }
  }),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('WriteChat phase', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('demo_work')
  })

  it('正文阶段传入 phase=final 时把 final phase 发给写作接口', async () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '继续写正文' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(api.chatWrite).toHaveBeenCalled())
    expect(api.chatWrite.mock.calls[0][0]).toBe('继续写正文')
    expect(api.chatWrite.mock.calls[0][1]).toMatchObject({
      chapter: 4,
      focalizer: '崔判',
      phase: 'final',
    })
  })

  it('正文主编对话使用统一的单面板输入区', () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    expect(screen.getByTestId('chief-write-chat')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-messages').className).toContain('bg-canvas')
    const composer = screen.getByTestId('chief-chat-composer')
    const textarea = screen.getByPlaceholderText(/提思路/)
    expect(composer.getAttribute('data-chief-composer')).toBe('true')
    expect(composer.className).toContain('chief-composer-panel')
    expect(composer.className).toContain('rounded-xl')
    expect(composer.className).not.toContain('space-y-2')
    expect(textarea.className).toContain('border-0')
    expect(textarea.className).toContain('shadow-none')
    expect(textarea.className).toContain('focus:shadow-none')
    expect(textarea.className).toContain('focus:ring-0')
    expect(textarea.className).toContain('min-h-[36px]')
    expect(textarea.className).not.toContain('min-h-[72px]')
  })

  it('正文主编底部工具栏展示附件、语音和大发送按钮', () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const toolbar = screen.getByTestId('chief-chat-toolbar')
    expect(screen.getByRole('button', { name: '添加附件' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '语音输入' })).toBeTruthy()
    const send = screen.getByRole('button', { name: '发送' })
    expect(send.textContent).toContain('发送')
    expect(send.className).toContain('min-w-')
    expect(toolbar.textContent).not.toContain('Enter 发送')
  })
})

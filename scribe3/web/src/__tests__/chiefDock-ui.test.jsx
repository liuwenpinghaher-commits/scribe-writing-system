import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { useEffect } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChiefDock } from '../ChiefDock'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo_work'),
  chapterPulse: vi.fn(() => Promise.resolve({ dimensions: [] })),
  addIdea: vi.fn(),
  chatWrite: vi.fn(),
  chatStream: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const here = dirname(fileURLToPath(import.meta.url))

function PhaseSetter({ phase }) {
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase) }, [phase, setChapterPhase])
  return null
}

function Harness({ phase = 'outline' }) {
  return (
    <ChiefSlotProvider>
      <PhaseSetter phase={phase} />
      <ChiefDock
        chapterSel
        lastSeq={7}
        sel={{ mode: 'node', node: { id: 'ch:7', type: 'chapter', ref: 7, label: '7 铜炉认主' } }}
      />
    </ChiefSlotProvider>
  )
}

describe('ChiefDock UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('demo_work')
  })

  it('非正文阶段主编对话框使用统一上下文壳', async () => {
    render(<Harness phase="outline" />)

    const shell = await screen.findByTestId('chief-chat-shell')
    expect(shell.className).toContain('bg-surface')
    expect(screen.getByTestId('chief-chat-title').textContent).toBe('主编上下文')
    expect(screen.getByTestId('chief-ctx').textContent).toBe('第 7 章 · 大纲')
    expect(screen.getByTestId('chief-chat-messages')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-composer')).toBeTruthy()
  })

  it('非正文阶段主编输入区使用单一输入面板, textarea 不再画独立大框', async () => {
    render(<Harness phase="outline" />)

    await screen.findByTestId('chief-chat-shell')
    const composer = screen.getByTestId('chief-chat-composer')
    const textarea = screen.getByPlaceholderText(/就当前内容问主编/)

    expect(composer.getAttribute('data-chief-composer')).toBe('true')
    expect(composer.className).toContain('chief-composer-panel')
    expect(composer.className).toContain('rounded-xl')
    expect(composer.className).not.toContain('space-y-2')
    expect(textarea.className).toContain('w-full')
    expect(textarea.className).toContain('border-0')
    expect(textarea.className).toContain('shadow-none')
    expect(textarea.className).toContain('focus:shadow-none')
    expect(textarea.className).toContain('focus:ring-0')
    expect(textarea.className).toContain('min-h-[36px]')
    expect(textarea.className).not.toContain('min-h-[72px]')
    expect(textarea.className).not.toContain('flex-1')
  })

  it('主编输入器局部覆盖全局 textarea focus 光晕', () => {
    const css = readFileSync(resolve(here, '../index.css'), 'utf8')

    expect(css).toContain('[data-chief-composer="true"] textarea:focus')
    expect(css).toContain('box-shadow: none')
  })

  it('非正文阶段主编底部工具栏展示附件、语音和大发送按钮', async () => {
    render(<Harness phase="outline" />)

    await screen.findByTestId('chief-chat-shell')
    const toolbar = screen.getByTestId('chief-chat-toolbar')

    expect(screen.getByRole('button', { name: '添加附件' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '语音输入' })).toBeTruthy()
    const send = screen.getByRole('button', { name: '发送' })
    expect(send.textContent).toContain('发送')
    expect(send.className).toContain('min-w-')
    expect(toolbar.textContent).not.toContain('Enter 发送')
  })
})

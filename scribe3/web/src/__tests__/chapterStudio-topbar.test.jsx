import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../WriteLayout', async () => {
  const React = await import('react')
  return {
    WriteLayout: () => <div data-testid="write-layout" />,
    RestoreContext: React.createContext(0),
  }
})
vi.mock('../DeduceStage', () => ({ DeduceStage: () => <div data-testid="deduce-stage" /> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))

// Task 7:顶栏插槽链已删,章阶段页签由 ChapterStudio 内的 ObjectFrame 承载(role="tab")。
function Harness({ initialPhase }) {
  return (
    <ChiefSlotProvider>
      <ChapterStudio work="demo" seq={3} initialPhase={initialPhase} />
    </ChiefSlotProvider>
  )
}

describe('ChapterStudio 章对象外框与五阶段页签', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({ title: '三', synopsis: '', beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [] })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('章页签恰为五个语义阶段,辅助资料不再占阶段位', async () => {
    render(<Harness initialPhase="outline" />)

    const tabs = await screen.findAllByRole('tab')
    expect(tabs.map((tab) => tab.textContent)).toEqual(['大纲', '节拍', '演绎', '草稿', '正文'])
    expect(screen.queryByRole('tab', { name: '简报' })).toBeNull()
    expect(screen.queryByRole('tab', { name: '关联' })).toBeNull()
    expect(screen.queryByRole('tab', { name: '北极星' })).toBeNull()
    expect(screen.queryByRole('tab', { name: '限知帧' })).toBeNull()
  })

  it('旧持久化 deduce 阶段就地渲染演绎工作台,不再改道正文', async () => {
    localStorage.setItem('s3.chapter.phase', 'deduce')

    render(<Harness />)

    expect(await screen.findByTestId('deduce-stage')).toBeTruthy()
    expect(screen.queryByTestId('write-layout')).toBeNull()
    expect(screen.getByRole('tab', { name: '演绎' }).getAttribute('aria-selected')).toBe('true')
  })

  it('大纲到草稿阶段在栏3共享统一章工作台骨架', async () => {
    render(<Harness initialPhase="outline" />)

    const shell = await screen.findByTestId('chapter-workbench-shell')
    expect(shell.getAttribute('data-phase')).toBe('outline')
    expect(within(shell).getByTestId('chapter-stage-heading').textContent).toBe('大纲')
    expect(within(shell).getByTestId('chapter-stage-meta')).toBeTruthy()
    // 第三栏内容流:不套 elevated 装饰卡,只保留工作台 testid 与阶段切换
    expect(shell.className).not.toContain('panel-elevated')

    fireEvent.click(screen.getByRole('tab', { name: '节拍' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('beats'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('节拍')

    fireEvent.click(screen.getByRole('tab', { name: '草稿' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('draft'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('草稿')
  })

  it('草稿窄栏中标题与操作分层，操作区可在本栏换行', async () => {
    render(<Harness initialPhase="draft" />)

    const title = await screen.findByTestId('chapter-stage-title')
    const actions = screen.getByTestId('chapter-stage-actions')

    // 详情栏与主编栏会并排。草稿的五个动作不能挤压标题/说明到逐字竖排，
    // 因此标题和动作必须是垂直的两个布局区，动作行自身占满可用宽度并换行。
    expect(title.className).toContain('flex-col')
    expect(actions.className).toContain('w-full')
    expect(actions.className).toContain('flex-wrap')
  })

  it('正文阶段在布局导致工作台重挂时不被初始大纲指令覆盖', async () => {
    const first = render(<Harness initialPhase="outline" />)

    fireEvent.click(await screen.findByRole('tab', { name: '正文' }))
    expect(await screen.findByTestId('write-layout')).toBeTruthy()

    // 正文会令四栏切到阅读布局，真实页面会因此重挂 DetailPane/ChapterStudio。
    // 重挂后仍必须停在正文；否则作者每次点正文都会被旧 selection.phase 拉回大纲。
    first.unmount()
    render(<Harness initialPhase="outline" />)

    expect(await screen.findByTestId('write-layout')).toBeTruthy()
    expect(screen.getByRole('tab', { name: '正文' }).getAttribute('aria-selected')).toBe('true')
  })
})

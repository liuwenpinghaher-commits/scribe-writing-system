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
  fetchCapabilities: vi.fn(),
  chapterPlay: vi.fn(),
  chapterContract: vi.fn(),
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
    apiMock.fetchCapabilities.mockRejectedValue(new Error('no caps'))
    apiMock.chapterPlay.mockRejectedValue(Object.assign(new Error('HTTP 404'), { status: 404, body: { detail: { code: 'play_missing' } } }))
    apiMock.chapterContract.mockRejectedValue(Object.assign(new Error('HTTP 404'), { status: 404, body: { detail: { code: 'contract_missing' } } }))
  })

  it('旗 on 时页签为章设计/演绎/草稿/正文', async () => {
    apiMock.fetchCapabilities.mockResolvedValue({ flags: { chapter_design: true } })
    render(<Harness initialPhase="outline" />)
    await waitFor(() => {
      const tabs = screen.getAllByRole('tab')
      expect(tabs.map((tab) => tab.textContent)).toEqual(['章设计', '演绎', '草稿', '正文'])
    })
    expect(await screen.findByTestId('chapter-workbench-shell')).toHaveAttribute('data-phase', 'design')
  })

  it('章设计页能看见节拍块和跳转', async () => {
    apiMock.fetchCapabilities.mockResolvedValue({ flags: { chapter_design: true } })
    apiMock.chapter.mockResolvedValue({
      title: '华山成核',
      synopsis: '',
      chapter_spine: { goal: '沈拾灯按场核成核', choice: '交指针态 vs 观测大遮蔽' },
      beats: [
        { id: 'b1', goal: '按场核', conflict: '挡', turn: '变', cost: '付', text: '拍1' },
        { id: 'b2', goal: '交指针态', choice: '交指针态 vs 观测大遮蔽', text: '拍2' },
        { id: 'b3', goal: '观测金縢', text: '拍3' },
      ],
      prose: '',
    })
    render(<Harness initialPhase="design" />)
    expect(await screen.findByTestId('design-beats-section')).toBeTruthy()
    expect(screen.getByTestId('design-jump-beats').textContent).toMatch(/节拍/)
    expect(screen.getByTestId('beat-card-0')).toBeTruthy()
    expect(screen.getByText('拍1')).toBeTruthy()
    expect(screen.getByText('按场核')).toBeTruthy()
  })

  it('章设计页读这场戏，不把空的旧格子当内容', async () => {
    apiMock.fetchCapabilities.mockResolvedValue({ flags: { chapter_design: true } })
    apiMock.chapter.mockResolvedValue({ title: '华山成核', chapter_spine: {}, beats: [], prose: '' })
    apiMock.chapterPlay.mockResolvedValue({
      text: '柳岸青把碎片按了进去。沈烛记下货已验过。',
    })
    apiMock.chapterContract.mockResolvedValue({
      fields: {
        goal: { text: '把碎片按回裂口' },
        choice: { text: '按则废左手，不按裂口压向兰因' },
        decision: { text: '按了进去' },
        cost: { text: '左手不受他管' },
        hook: { text: '裂口没合' },
      },
      beats: [{ n: 1, goal: { text: '沈烛验货' }, turn: { text: '碎片咬进右腕' } }],
    })
    render(<Harness initialPhase="design" />)
    expect(await screen.findByTestId('design-play-text')).toHaveTextContent('柳岸青把碎片按了进去')
    expect(screen.getByTestId('design-contract-nails')).toHaveTextContent('把碎片按回裂口')
    expect(screen.getByTestId('beat-card-0')).toHaveTextContent('沈烛验货')
    expect(screen.queryByText('（还没有这场戏 · 让主编先写设计）')).toBeNull()
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
    expect(shell.className).toContain('h-full')
    expect(screen.queryByTestId('phase-duty-line')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: '节拍' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('beats'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('节拍')

    fireEvent.click(screen.getByRole('tab', { name: '草稿' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('draft'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('草稿')
  })

  it('场面纸默认收成一行，不占草稿正文高度', async () => {
    render(<Harness initialPhase="draft" />)
    const paper = await screen.findByTestId('scene-paper-expand')
    expect(paper.tagName).toBe('DETAILS')
    expect(paper.open).toBe(false)
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

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChapterMetaPane } from './ChapterMetaPane'

vi.mock('./api', () => ({
  api: {
    chapter: vi.fn(),
    listVolumes: vi.fn(),
    patchChapter: vi.fn(),
    chapterBrief: vi.fn(),
    executionSoftStatus: vi.fn(),
  },
}))
vi.mock('./ui/Toast.jsx', () => ({ useToast: () => vi.fn() }))

const { api } = await import('./api')

describe('ChapterMetaPane', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    api.chapter.mockResolvedValue({
      title: '第1章',
      label: '',
      volume: null,
      synopsis: '',
      beats: [],
      scene_truth: '',
      involved_characters: [],
      deductions: [],
      narrative_drive: {},
    })
    api.listVolumes.mockResolvedValue([{ id: 'vol:one', title: '第一卷·退潮之名' }])
    api.chapterBrief.mockRejectedValue(new Error('no brief'))
    api.executionSoftStatus.mockResolvedValue({
      seq: 1,
      severity: 'advisory',
      has_prose: false,
      drive_summary: { present: false, inciting: '', opposition: '', end_hook: '' },
      stakes: { present: false, high_pressure: false, warning: '' },
      soft_fulfill: null,
      drift: { drift: false, advisory: '', reason: 'no_prose' },
    })
  })

  it('章节信息只读,让主编写入不调用 patchChapter', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(<ChapterMetaPane seq={1} work="book-test" onClose={vi.fn()} />)

    expect(await screen.findByTestId('chapter-meta-pane')).toBeTruthy()
    expect(screen.getByText(/第1章/)).toBeTruthy()
    expect(screen.getByTestId('chapter-contract-checklist')).toBeTruthy()
    fireEvent.click(screen.getByTestId('chapter-meta-ask-chief'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(tabs).toContain('chief')
    expect(api.patchChapter).not.toHaveBeenCalled()
  })

  it('空 synopsis 显示不建议开写与 CTA，跳转只走 onNavigatePhase', async () => {
    const onNavigatePhase = vi.fn()
    const onClose = vi.fn()
    render(
      <ChapterMetaPane
        seq={1}
        work="book-test"
        onClose={onClose}
        onNavigatePhase={onNavigatePhase}
      />,
    )
    expect(await screen.findByTestId('contract-attention')).toBeTruthy()
    fireEvent.click(screen.getByTestId('contract-go-outline'))
    expect(onNavigatePhase).toHaveBeenCalledWith('outline')
    expect(api.patchChapter).not.toHaveBeenCalled()
  })

  it('有 synopsis/beats/truth 时展示摘要', async () => {
    api.chapter.mockResolvedValue({
      title: '潮声',
      label: 'draft',
      volume: 'vol:one',
      synopsis: '柳怀玉赴义庄验尸，发现铜钱异样。',
      beats: [{ text: '抵达' }, { text: '验尸' }, { text: '铜钱' }],
      scene_truth: '义庄后室有人先到，换走了证物。',
      involved_characters: [],
      deductions: [],
      narrative_drive: {
        inciting_force: { summary: '铜钱失踪' },
        opposition: { who_or_what: '义庄管事', wants: '掩盖' },
        end_hook: '门外脚步',
      },
    })
    api.executionSoftStatus.mockResolvedValue({
      seq: 2,
      severity: 'advisory',
      has_prose: true,
      drive_summary: {
        present: true,
        inciting: '铜钱失踪',
        opposition: '义庄管事 要 掩盖',
        end_hook: '门外脚步',
      },
      stakes: { present: false, high_pressure: false, warning: '' },
      soft_fulfill: {
        ok_soft: false,
        gaps: ['dialogue_low'],
        quotes: 1,
        prose_cn: 1200,
        severity: 'advisory',
      },
      drift: { drift: false, advisory: '', reason: '' },
    })
    render(<ChapterMetaPane seq={2} work="book-test" onClose={vi.fn()} />)
    expect(await screen.findByText(/柳怀玉赴义庄验尸/)).toBeTruthy()
    expect(screen.getByText(/抵达/)).toBeTruthy()
    expect(screen.getByText(/义庄后室/)).toBeTruthy()
    expect(screen.queryByTestId('contract-attention')).toBeNull()
    expect(await screen.findByTestId('chapter-event-drive')).toBeTruthy()
    expect(screen.getByText(/铜钱失踪/)).toBeTruthy()
    expect(screen.getByTestId('chapter-execution-soft')).toBeTruthy()
    expect(screen.getByTestId('contract-stakes-row')).toBeTruthy()
  })

  it('空章也挂载事件驱动与执行对照区块', async () => {
    render(<ChapterMetaPane seq={1} work="book-test" onClose={vi.fn()} />)
    expect(await screen.findByTestId('chapter-event-drive')).toBeTruthy()
    expect(screen.getByTestId('chapter-execution-soft')).toBeTruthy()
    expect(screen.getByTestId('contract-stakes-row')).toBeTruthy()
  })
})

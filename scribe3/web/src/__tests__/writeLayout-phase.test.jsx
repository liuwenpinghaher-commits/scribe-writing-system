import { forwardRef, useImperativeHandle } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WriteLayout } from '../WriteLayout'

const apiMock = vi.hoisted(() => ({
  setWork: vi.fn(),
  chapters: vi.fn(),
  progress: vi.fn(),
  entities: vi.fn(),
  motifs: vi.fn(),
  chapter: vi.fn(),
  causal: vi.fn(),
  qc: vi.fn(),
  checkProse: vi.fn(),
  saveChapter: vi.fn(),
  postCheck: vi.fn(),
  checkpoint: vi.fn(),
  ingest: vi.fn(),
  listUnverified: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

vi.mock('../WriteChat', () => ({
  WriteChat: (props) => (
    <div data-testid="captured-write-chat">
      phase={props.phase};chapter={props.chapter};focalizer={props.focalizer}
    </div>
  ),
}))

vi.mock('../shell', () => ({ Shell: ({ center }) => <div data-testid="shell">{center}</div> }))
vi.mock('../NorthStarBar', () => ({ NorthStarBar: () => <div data-testid="north-star-bar" /> }))
vi.mock('../PulseBar', () => ({ PulseBar: () => <div data-testid="pulse-bar" /> }))
vi.mock('../ChapterMemoryRefs', () => ({ ChapterMemoryRefs: () => <div data-testid="chapter-memory-refs" /> }))
// (M4:WriteLayout 已删 VersionPanel/FramePanel 死 import,对应死 mock 一并移除)
vi.mock('../ui/Toast.jsx', () => ({
  useToast: () => vi.fn(),
  dismissToast: vi.fn(),
  showToast: vi.fn(),
}))
vi.mock('../editor/ProseEditor', () => ({
  ProseEditor: forwardRef(function MockProseEditor(props, ref) {
    useImperativeHandle(ref, () => ({
      focusIssue: vi.fn(),
      focusScene: vi.fn(),
    }))
    return <textarea aria-label="正文编辑器" readOnly value={props.value || ''} />
  }),
}))

describe('WriteLayout final phase', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    apiMock.chapters.mockResolvedValue([{ seq: 4 }])
    apiMock.progress.mockResolvedValue({ today_words: 0 })
    apiMock.entities.mockResolvedValue([{ id: 'role:崔判', kind: 'character', name: '崔判' }])
    apiMock.motifs.mockResolvedValue([])
    apiMock.chapter.mockResolvedValue({
      title: '四',
      prose: '',
      focalizer: 'role:崔判',
      beats: [],
      deductions: [],
      involved_characters: [],
    })
    apiMock.causal.mockResolvedValue({ no_event_data: true, violations: [] })
    apiMock.qc.mockResolvedValue({ repetition: 0, structural: 0, purple: 0 })
  })

  it('正文写作布局把 WriteChat 固定为 final phase', async () => {
    render(<WriteLayout work="demo" seq={4} />)

    const captured = await screen.findByTestId('captured-write-chat')
    await waitFor(() => expect(captured.textContent).toContain('phase=final'))
    expect(captured.textContent).toContain('chapter=4')
    const island = screen.getByTestId('prose-island')
    expect(island.className).toContain('max-w-[56rem]')
    expect(island.className).toContain('py-4')
    expect(screen.getByTestId('write-meta-row')).toBeTruthy()
    expect(screen.getByTestId('pulse-bar')).toBeTruthy()
    expect(screen.getByTestId('write-meta-row').querySelector('[data-testid="pulse-bar"]')).toBeNull()
  })

  // Task 7:全 DOM 单套章导航归 ChapterStudio(ObjectFrame actions),
  // WriteLayout 不再自带第二套上一章/下一章。
  it('WriteLayout 单独渲染时没有章导航按钮', async () => {
    render(<WriteLayout work="demo" seq={4} />)

    await screen.findByTestId('captured-write-chat')
    expect(screen.queryByRole('button', { name: '上一章' })).toBeNull()
    expect(screen.queryByRole('button', { name: '下一章' })).toBeNull()
  })
})

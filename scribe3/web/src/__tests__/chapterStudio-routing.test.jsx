import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  archiveChapter: vi.fn(),
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
vi.mock('../DeduceStage', () => ({ DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎:{seq}</div> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))

function renderStudio({ seq = 3, ...props } = {}) {
  return render(
    <ChiefSlotProvider>
      <ChapterStudio work="demo" seq={seq} initialPhase="outline" {...props} />
    </ChiefSlotProvider>,
  )
}

describe('ChapterStudio 章工作台归位', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({ title: '三', synopsis: '', beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [] })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.archiveChapter.mockResolvedValue({ status: 'archived', seq: 3 })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('简报/关联/北极星不再是章内页签,章页签只剩五阶段', async () => {
    renderStudio()

    const tabs = await screen.findAllByRole('tab')
    expect(tabs.map((tab) => tab.textContent)).toEqual(['大纲', '节拍', '演绎', '草稿', '正文'])
    expect(screen.queryByRole('tab', { name: '简报' })).toBeNull()
    expect(screen.queryByRole('tab', { name: '关联' })).toBeNull()
    expect(screen.queryByRole('tab', { name: '北极星' })).toBeNull()
  })

  it('点「演绎」页签就地渲染 DeduceStage,不再派发 s3-open-capability', async () => {
    const events = []
    const onCap = (e) => events.push(e.detail)
    window.addEventListener('s3-open-capability', onCap)
    renderStudio()

    fireEvent.click(await screen.findByRole('tab', { name: '演绎' }))
    expect((await screen.findByTestId('deduce-stage')).textContent).toBe('演绎:3')

    window.removeEventListener('s3-open-capability', onCap)
    expect(events).toEqual([])
  })

  it('章导航只此一套:上一章步进回调,末章禁用下一章', async () => {
    const onSeqChange = vi.fn()
    renderStudio({ seq: 4, onSeqChange })

    const prevButtons = await screen.findAllByRole('button', { name: '上一章' })
    expect(prevButtons).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: '下一章' })).toHaveLength(1)

    fireEvent.click(prevButtons[0])
    expect(onSeqChange).toHaveBeenCalledWith(3)

    // maxSeq=4(api.chapters 全量):已在末章 → 下一章禁用,不再翻出空章;title 如实说明
    await waitFor(() => expect(screen.getByRole('button', { name: '下一章' }).hasAttribute('disabled')).toBe(true))
    expect(screen.getByRole('button', { name: '下一章' }).getAttribute('title')).toBe('已是最后一章')
  })

  // I2 正向路径(防假绿):未到末章时下一章必须可点且步进;
  // I1 回归:maxSeq 未加载(null)首帧不得闪禁、不得谎报「已是最后一章」。
  it('未到末章:下一章首帧不闪禁,加载后可点并步进', async () => {
    const onSeqChange = vi.fn()
    renderStudio({ seq: 2, onSeqChange })

    const next = screen.getByRole('button', { name: '下一章' })
    expect(next.hasAttribute('disabled')).toBe(false)
    expect(next.getAttribute('title')).toBe('下一章')

    // 等 meta/chapters 都落定(同批 mock 微任务,骨架出现即 effects 已 flush)
    await screen.findByTestId('chapter-workbench-shell')
    await waitFor(() => expect(apiMock.chapters).toHaveBeenCalled())

    // maxSeq=4 > seq=2:仍可点;禁用态下 React 不触发 onClick,故回调即"已加载且未禁用"的实证
    fireEvent.click(screen.getByRole('button', { name: '下一章' }))
    expect(onSeqChange).toHaveBeenCalledWith(3)
  })

  it('章工作台经「更多」菜单归档章节,确认后调用归档并通知外层刷新', async () => {
    const onArchived = vi.fn()
    renderStudio({ onArchived })

    fireEvent.click(await screen.findByRole('button', { name: '更多' }))
    fireEvent.click(screen.getByRole('button', { name: '归档章节' }))
    fireEvent.click(screen.getByRole('button', { name: '归档' }))

    expect(apiMock.archiveChapter).toHaveBeenCalledWith(3, '')
    await waitFor(() => expect(onArchived).toHaveBeenCalledWith(3))
  })
})

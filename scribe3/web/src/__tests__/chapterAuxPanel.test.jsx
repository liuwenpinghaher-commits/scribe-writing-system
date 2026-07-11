import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChapterAuxPanel } from '../ChapterAuxPanel'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../BriefPanel', () => ({ BriefPanel: ({ seq }) => <div data-testid="brief-panel">简报:{seq}</div> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: ({ seq }) => <div data-testid="northstar-panel">北极星:{seq}</div> }))
// mock FramePanel 复刻真身分派逻辑的关键面:空 focalizer → 全知空态文案(FramePanel.jsx:724),
// 便于断言「C1:限知章不得落全知空态」;同时回显收到的 props 供断言。
vi.mock('../FramePanel', () => ({
  FramePanel: ({ focalizer, chapter, focalizerOptions = [] }) => (
    <div data-testid="frame-panel">
      {focalizer ? `限知:${focalizer}` : '作者全知视角——暂无限知约束'}:{chapter}:{focalizerOptions.length}
    </div>
  ),
}))

describe('ChapterAuxPanel 章节辅助(右栏)', () => {
  beforeEach(() => {
    apiMock.chapter.mockResolvedValue({ title: '三', focalizer: 'role:小翠' })
    apiMock.entities.mockResolvedValue([
      { id: 'role:小翠', kind: 'character', name: '小翠' },
      { id: 'role:崔判', kind: 'character', name: '崔判' },
      { id: 'loc:炉坊', kind: 'location', name: '炉坊' },
    ])
  })

  // C1:限知章的关联页必须拿到章 focalizer(自拉 api.chapter)与角色候选(entities 过滤 character),
  // 不得因 RightDock 不传 meta 而渲成「作者全知视角」空态。
  it('限知章的关联页拿到章 focalizer 与角色候选,不落全知空态', async () => {
    render(<ChapterAuxPanel seq={3} />)

    fireEvent.click(screen.getByRole('tab', { name: '关联' }))

    await waitFor(() => expect(screen.getByTestId('frame-panel').textContent).toBe('限知:role:小翠:3:2'))
    expect(screen.queryByText(/作者全知视角/)).toBeNull()
    expect(apiMock.chapter).toHaveBeenCalledWith(3)
  })

  it('三页可切换:简报 → 关联 → 北极星,brief/northstar 正常渲染', async () => {
    render(<ChapterAuxPanel seq={3} />)

    expect((await screen.findByTestId('brief-panel')).textContent).toBe('简报:3')

    fireEvent.click(screen.getByRole('tab', { name: '关联' }))
    expect(await screen.findByTestId('frame-panel')).toBeTruthy()
    expect(screen.queryByTestId('brief-panel')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: '北极星' }))
    expect((await screen.findByTestId('northstar-panel')).textContent).toBe('北极星:3')
    expect(screen.queryByTestId('frame-panel')).toBeNull()
  })

  // fail-soft:章 meta / 实体拉取失败 → 关联页降级为全知空态(空 focalizer),面板不崩。
  it('章 meta 拉取失败时降级为全知空态,不崩面板', async () => {
    apiMock.chapter.mockRejectedValue(new Error('boom'))
    apiMock.entities.mockRejectedValue(new Error('boom'))
    render(<ChapterAuxPanel seq={3} />)

    fireEvent.click(screen.getByRole('tab', { name: '关联' }))

    await waitFor(() => expect(screen.getByTestId('frame-panel').textContent).toContain('作者全知视角'))
    expect(screen.getByTestId('frame-panel').textContent).toContain(':3:0')
  })
})

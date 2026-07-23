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
  FramePanel: ({ focalizer, chapter, focalizerOptions = [], onSelectNode }) => (
    <div data-testid="frame-panel">
      {focalizer ? `限知:${focalizer}` : '作者全知视角——暂无限知约束'}:{chapter}:{focalizerOptions.length}
      <button
        type="button"
        data-testid="frame-mock-jump"
        onClick={() => onSelectNode?.({ id: 'character:甲', type: 'character', ref: '甲', label: '甲' })}
      >
        mock-jump
      </button>
    </div>
  ),
}))

describe('ChapterAuxPanel 章节辅助(章工作台栏3 内容区视图)', () => {
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

    await waitFor(() => expect(screen.getByTestId('frame-panel').textContent).toMatch(/^限知:role:小翠:3:2/))
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

  // initialTab(非受控):以指定 tab 起始,内部三 tab 仍可自切。
  it('initialTab=frame 时初始即关联页,且仍可切回简报', async () => {
    render(<ChapterAuxPanel seq={3} initialTab="frame" />)

    expect(await screen.findByTestId('frame-panel')).toBeTruthy()
    expect(screen.getByRole('tab', { name: '关联' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.queryByTestId('brief-panel')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: '简报' }))
    expect(await screen.findByTestId('brief-panel')).toBeTruthy()
  })

  // 防御:非法 initialTab 归一到 brief,不渲空内容
  it('非法 initialTab 归一到简报', async () => {
    render(<ChapterAuxPanel seq={3} initialTab="bogus" />)
    expect(await screen.findByTestId('brief-panel')).toBeTruthy()
  })

  // 受控模式(ChapterStudio 栏3 内容区接线):tab prop 是唯一事实源。
  // 2026-07-12 UX 修正:受控时【不渲染】内部 tab 行——头部三入口是唯一切换器,
  // 面板内再画一排同名 tab 是重复信息且白占一行(作者实拍反馈)。
  it('受控模式:不渲染内部 tab 行(头部入口是唯一切换器),内容随 tab prop 切换', async () => {
    const { rerender } = render(<ChapterAuxPanel seq={3} tab="frame" onTabChange={() => {}} />)

    expect(await screen.findByTestId('frame-panel')).toBeTruthy()
    expect(screen.queryByRole('tablist', { name: '章节辅助' })).toBeNull()   // 无重复 tab 行

    rerender(<ChapterAuxPanel seq={3} tab="brief" onTabChange={() => {}} />)
    expect(await screen.findByTestId('brief-panel')).toBeTruthy()
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

  it('透传 onSelectNode 到 FramePanel,关联跳转可回调', async () => {
    const onSelectNode = vi.fn()
    render(<ChapterAuxPanel seq={3} tab="frame" onTabChange={() => {}} onSelectNode={onSelectNode} />)
    expect(await screen.findByTestId('frame-panel')).toBeTruthy()
    fireEvent.click(screen.getByTestId('frame-mock-jump'))
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({ type: 'character', ref: '甲' }))
  })
})

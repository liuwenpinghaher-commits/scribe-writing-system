import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'

// 章节辅助(2026-07-12 修正):三入口(简报/关联/北极星)在章工作台头部,点击在
// 【栏3 内容区】切换渲染 ChapterAuxPanel——与点大纲/正文页签同级的内容切换。
// 不再是铺满栏2+3+4 的全宽 portal 层:那会挤掉栏4 主编,用户没法边看辅助资料边讨论。
// ChapterAuxPanel 用真身(受控 tab 接线是本测职责),其三个子面板打桩。
const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  archiveChapter: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../WriteLayout', () => ({ WriteLayout: () => <div data-testid="write-layout" /> }))
vi.mock('../DeduceStage', () => ({ DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎:{seq}</div> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))
vi.mock('../BriefPanel', () => ({ BriefPanel: ({ seq }) => <div data-testid="brief-panel">简报:{seq}</div> }))
vi.mock('../FramePanel', () => ({ FramePanel: ({ chapter }) => <div data-testid="frame-panel">关联:{chapter}</div> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: ({ seq }) => <div data-testid="northstar-panel">北极星:{seq}</div> }))

function renderStudio({ seq = 3, ...props } = {}) {
  return render(
    <ChiefSlotProvider>
      <div style={{ display: 'flex' }}>
        <div style={{ flex: 1 }}>
          <ChapterStudio work="demo" seq={seq} initialPhase="outline" {...props} />
        </div>
        {/* 栏4 哨兵:辅助视图只是栏3 内容切换,兄弟 DOM(主编栏位)必须原封不动 */}
        <aside data-testid="right-dock-sentinel">主编对话</aside>
      </div>
    </ChiefSlotProvider>,
  )
}

const phaseTabLabels = ['大纲', '节拍', '演绎', '草稿', '正文']
const phaseTabs = () => screen.getAllByRole('tab').filter((t) => phaseTabLabels.includes(t.textContent))

describe('ChapterStudio 章节辅助:头部入口 + 栏3 内容区切换', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({ title: '三', synopsis: '', beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [] })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('选中章后头部渲染三入口(简报/关联/北极星),且不混进阶段页签', async () => {
    renderStudio()
    const group = await screen.findByRole('group', { name: '章节辅助' })
    expect(within(group).getByRole('button', { name: /简报/ })).toBeTruthy()
    expect(within(group).getByRole('button', { name: /关联/ })).toBeTruthy()
    expect(within(group).getByRole('button', { name: /北极星/ })).toBeTruthy()
    // 阶段页签仍只有五阶段(入口是按钮不是 tab)
    expect(phaseTabs().map((tab) => tab.textContent)).toEqual(phaseTabLabels)
  })

  it('点「关联」→ 栏3 内容区切到 FramePanel,替代阶段内容;栏4 哨兵 DOM 不受影响', async () => {
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')
    const sentinelBefore = screen.getByTestId('right-dock-sentinel')

    fireEvent.click(screen.getByRole('button', { name: /关联/ }))

    const view = await screen.findByTestId('chapter-aux-view')
    // 内容区切换,不是 portal:视图在章工作台 section(ObjectFrame)内部
    expect(view.closest('section')).not.toBeNull()
    expect(view.parentElement).not.toBe(document.body)
    // 初始 tab=关联,内容挂 FramePanel
    expect(within(view).getByRole('tab', { name: '关联' }).getAttribute('aria-selected')).toBe('true')
    expect(await within(view).findByTestId('frame-panel')).toBeTruthy()
    expect(within(view).queryByTestId('brief-panel')).toBeNull()
    // 阶段内容被替换(同级切换语义)
    expect(screen.queryByTestId('chapter-workbench-shell')).toBeNull()
    // 栏4 哨兵纹丝不动:同一节点引用仍在文档里(主编可边看边聊)
    expect(screen.getByTestId('right-dock-sentinel')).toBe(sentinelBefore)
    expect(document.body.contains(sentinelBefore)).toBe(true)
  })

  it('激活态互斥:辅助入口 aria-pressed,阶段页签整体去激活但键盘仍可达', async () => {
    renderStudio()
    fireEvent.click(await screen.findByRole('button', { name: /关联/ }))
    await screen.findByTestId('chapter-aux-view')

    const group = screen.getByRole('group', { name: '章节辅助' })
    expect(within(group).getByRole('button', { name: /关联/ }).getAttribute('aria-pressed')).toBe('true')
    expect(within(group).getByRole('button', { name: /简报/ }).getAttribute('aria-pressed')).toBe('false')
    // 阶段页签无一"假激活"
    const tabs = phaseTabs()
    expect(tabs.every((t) => t.getAttribute('aria-selected') === 'false')).toBe(true)
    // roving tabindex 兜底:无选中时第一个阶段页签仍可 Tab 进入
    expect(tabs[0].getAttribute('tabindex')).toBe('0')
  })

  it('点阶段页签 → 关辅助视图回到原阶段内容,阶段激活态恢复', async () => {
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')
    fireEvent.click(screen.getByRole('button', { name: /北极星/ }))
    await screen.findByTestId('chapter-aux-view')

    fireEvent.click(screen.getByRole('tab', { name: '大纲' }))

    expect(screen.queryByTestId('chapter-aux-view')).toBeNull()
    expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('outline')
    expect(screen.getByRole('tab', { name: '大纲' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('button', { name: /北极星/ }).getAttribute('aria-pressed')).toBe('false')
  })

  it('再点当前高亮入口 = toggle 关闭,同样回到原阶段', async () => {
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')
    const brief = screen.getByRole('button', { name: /简报/ })

    fireEvent.click(brief)
    await screen.findByTestId('chapter-aux-view')
    expect(brief.getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(brief)
    await waitFor(() => expect(screen.queryByTestId('chapter-aux-view')).toBeNull())
    expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('outline')
  })

  it('视图内三 tab 互切(受控),头部入口高亮同步跟随', async () => {
    renderStudio()
    fireEvent.click(await screen.findByRole('button', { name: /关联/ }))
    const view = await screen.findByTestId('chapter-aux-view')

    fireEvent.click(within(view).getByRole('tab', { name: '简报' }))

    expect(await within(view).findByTestId('brief-panel')).toBeTruthy()
    expect(within(view).queryByTestId('frame-panel')).toBeNull()
    // 受控回写:头部高亮跟着内部互切走,当前位置永远可见且一致
    const group = screen.getByRole('group', { name: '章节辅助' })
    expect(within(group).getByRole('button', { name: /简报/ }).getAttribute('aria-pressed')).toBe('true')
    expect(within(group).getByRole('button', { name: /关联/ }).getAttribute('aria-pressed')).toBe('false')
  })

  it('未选中章(seq 为空)不出现三入口', async () => {
    renderStudio({ seq: null })
    await waitFor(() => expect(apiMock.chapters).toHaveBeenCalled())
    expect(screen.queryByRole('group', { name: '章节辅助' })).toBeNull()
    expect(screen.queryByRole('button', { name: /北极星/ })).toBeNull()
  })
})

describe('ChapterStudio 紧凑头部(三行压两行 + 章号去重)', () => {
  beforeEach(() => {
    localStorage.clear()
    // title 置空:标题走 fallback「第 3 章」,正是章导航文字重复的实证场景
    apiMock.chapter.mockResolvedValue({ title: '', synopsis: '', beats: [], focalizer: '', prose: '', deductions: [], involved_characters: [] })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('面包屑与标题合一行(手稿 › 第 3 章),不再单独占一行', async () => {
    renderStudio()
    const row = await screen.findByTestId('object-frame-titlerow-compact')
    expect(within(row).getByText('手稿')).toBeTruthy()
    expect(within(row).getByRole('heading', { name: '第 3 章' })).toBeTruthy()
  })

  it('章导航中间只显位置计数 N / 总数,「第 3 章」全文只出现在标题一处', async () => {
    renderStudio()
    await screen.findByRole('heading', { name: '第 3 章' })
    // 章导航中间是「3 / 4」(总数来自 api.chapters),不再复读「第 3 章」
    expect(await screen.findByText('3 / 4')).toBeTruthy()
    expect(screen.getAllByText('第 3 章')).toHaveLength(1)
  })
})

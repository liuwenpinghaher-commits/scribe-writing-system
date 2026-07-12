import { useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

// Task 2:大纲/草稿选区「聊这段/改这段」→ chiefIntent 预填 + s3-right-tab 聚焦右栏;
// 「改这段」额外记 selAnchor,既有 stageProposal pending 卡在唯一命中时升级为「替换选中段」。
// RichEditor 打桩:暴露 onSelAction 时渲两个可点按钮(聊/改),点击即模拟气泡菜单回调
// { text, intent }——真实气泡渲染/TipTap 选区已由 Task 1 richEditor-selAction.test.jsx 覆盖。
// selActionState:可变持有当前「点按钮送出的选中文本」——vi.hoisted 让 mock 工厂与测试体
// 共享同一引用,测试可在点击前改写它,模拟不同选区文本(如跨段落场景)。
const selActionState = vi.hoisted(() => ({ text: '这段大纲文字' }))
const SEL_TEXT = selActionState.text

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  saveDraft: vi.fn(),
  patchChapter: vi.fn(),
  archiveChapter: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../WriteLayout', () => ({ WriteLayout: () => <div data-testid="write-layout" /> }))
vi.mock('../DeduceStage', () => ({ DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎:{seq}</div> }))
vi.mock('../BriefPanel', () => ({ BriefPanel: ({ seq }) => <div data-testid="brief-panel">简报:{seq}</div> }))
vi.mock('../FramePanel', () => ({ FramePanel: ({ chapter }) => <div data-testid="frame-panel">关联:{chapter}</div> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: ({ seq }) => <div data-testid="northstar-panel">北极星:{seq}</div> }))

// RichEditor 打桩:受控 textarea(value/onChange/onBlur)+ 传 onSelAction 时渲两钮,
// 点击即用 selActionState.text(测试可改写)触发回调——真实 TipTap 选区行为由 Task 1 单测覆盖。
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: ({ value, onChange, onBlur, onSelAction, ariaLabel, editorKey }) => (
    <div data-testid={`richeditor-${editorKey}`}>
      <textarea aria-label={ariaLabel} value={value || ''} onChange={(e) => onChange?.(e.target.value)} onBlur={onBlur} />
      {onSelAction && (
        <>
          <button aria-label={`聊这段-${editorKey}`} onClick={() => onSelAction({ text: selActionState.text, intent: 'discuss' })}>聊这段</button>
          <button aria-label={`改这段-${editorKey}`} onClick={() => onSelAction({ text: selActionState.text, intent: 'edit' })}>改这段</button>
        </>
      )}
    </div>
  ),
  useUnsavedGuard: () => {},
}))

// 哨兵:消费 useChiefSlot 暴露 chiefIntent,供断言(DiscussionDock 的真实消费在 ChiefDock,
// 此处不重复其 UI,只验证总线上写入的值形状是否正确)。
function ChiefIntentSentinel() {
  const { chiefIntent } = useChiefSlot()
  return <div data-testid="chief-intent-sentinel">{chiefIntent ? JSON.stringify(chiefIntent) : ''}</div>
}

// 章导航「下一章」要真的改变 seq prop 才能验到「切章清 selAnchor」;ChapterStudio 本身不持
// seq state(受控于父级),测试用一个持 seq 的宿主组件桥接 onSeqChange → 下一次渲染的 seq prop。
function StudioHost({ initialSeq }) {
  const [seq, setSeq] = useState(initialSeq)
  return <ChapterStudio work="demo" seq={seq} initialPhase="outline" onSeqChange={setSeq} />
}

function renderStudio({ seq = 3 } = {}) {
  return render(
    <ChiefSlotProvider>
      <div style={{ display: 'flex' }}>
        <div style={{ flex: 1 }}>
          <StudioHost initialSeq={seq} />
        </div>
        <aside data-testid="right-dock-sentinel">
          <ChiefIntentSentinel />
        </aside>
      </div>
    </ChiefSlotProvider>,
  )
}

describe('ChapterStudio 大纲/草稿选区聊这段/改这段(Task 2)', () => {
  beforeEach(() => {
    localStorage.clear()
    selActionState.text = SEL_TEXT
    apiMock.chapter.mockResolvedValue({
      title: '三', synopsis: `前情。\n\n${SEL_TEXT}\n\n后续。`, beats: [], focalizer: 'role:小翠',
      prose: '', deductions: [], involved_characters: [],
    })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: `前情。\n\n${SEL_TEXT}\n\n后续。`, summary: '' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
    apiMock.patchChapter.mockResolvedValue({ ok: true })
    apiMock.saveDraft.mockResolvedValue({ ok: true })
  })

  it('①大纲「聊这段」→ chiefIntent 形状正确(phase/seq/text 含选中文本与「聊聊」)+ 派发 s3-right-tab', async () => {
    const onRightTab = vi.fn()
    window.addEventListener('s3-right-tab', onRightTab)
    try {
      renderStudio()
      await screen.findByTestId('chapter-workbench-shell')

      fireEvent.click(screen.getByRole('button', { name: '聊这段-3|synopsis' }))

      const raw = await screen.findByTestId('chief-intent-sentinel')
      await waitFor(() => expect(raw.textContent).not.toBe(''))
      const intent = JSON.parse(raw.textContent)
      expect(intent.phase).toBe('outline')
      expect(intent.seq).toBe(3)
      expect(intent.text).toContain(SEL_TEXT)
      expect(intent.text).toContain('聊聊')

      expect(onRightTab).toHaveBeenCalledTimes(1)
      expect(onRightTab.mock.calls[0][0].detail).toBe('chief')
    } finally {
      window.removeEventListener('s3-right-tab', onRightTab)
    }
  })

  it('②大纲「改这段」记 selAnchor;唯一命中 proposal → 「替换选中段」替换正确 + patchChapter 被调', async () => {
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|synopsis' }))
    const raw = await screen.findByTestId('chief-intent-sentinel')
    await waitFor(() => expect(raw.textContent).not.toBe(''))
    const intent = JSON.parse(raw.textContent)
    expect(intent.phase).toBe('outline')
    expect(intent.text).toContain('改')
    expect(intent.text).toContain(SEL_TEXT)

    // 模拟右栏主编生成完毕,经既有窗口事件通道发布 stageProposal(与 ChiefDock 发布口径一致)
    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'outline', seq: 3, target: null, content: '全新替换段', ts: 1 } }))

    const replaceBtn = await screen.findByRole('button', { name: '替换选中段' })
    fireEvent.click(replaceBtn)

    const textarea = screen.getByRole('textbox', { name: '本章大纲' })
    expect(textarea.value).toBe('前情。\n\n全新替换段\n\n后续。')
    await waitFor(() => expect(apiMock.patchChapter).toHaveBeenCalled())
    expect(apiMock.patchChapter).toHaveBeenCalledWith(3, { synopsis: '前情。\n\n全新替换段\n\n后续。' }, 'demo')
  })

  it('③buffer 含两处相同选中文本 → 主按钮维持现状「填入」+ 出现降级提示', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '三', synopsis: `${SEL_TEXT}\n\n中段。\n\n${SEL_TEXT}`, beats: [], focalizer: 'role:小翠',
      prose: '', deductions: [], involved_characters: [],
    })
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|synopsis' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'outline', seq: 3, target: null, content: '全新替换段', ts: 1 } }))

    await screen.findByText(/主编生成了内容/)
    expect(screen.queryByRole('button', { name: '替换选中段' })).toBeNull()
    expect(screen.getByRole('button', { name: '填入' })).toBeTruthy()
    expect(screen.getByText('选中段无法精确定位,按原方式落地')).toBeTruthy()
  })

  it('④草稿 DraftTab 同型:改这段→选区替换后 draftRef.dirty 置真(不强制立即 saveDraft)', async () => {
    renderStudio()
    fireEvent.click(await screen.findByRole('tab', { name: '草稿' }))
    await waitFor(() => expect(screen.getByTestId('richeditor-3|draft')).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|draft' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))
    const intent = JSON.parse(screen.getByTestId('chief-intent-sentinel').textContent)
    expect(intent.phase).toBe('draft')
    expect(intent.text).toContain('改')
    expect(intent.text).toContain(SEL_TEXT)

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'draft', seq: 3, target: null, content: '全新草稿段', ts: 1 } }))
    const replaceBtn = await screen.findByRole('button', { name: '替换选中段' })
    fireEvent.click(replaceBtn)

    const textarea = screen.getByRole('textbox', { name: '草稿正文' })
    expect(textarea.value).toBe('前情。\n\n全新草稿段\n\n后续。')
    // 不强制立即 saveDraft:落地这一步不应触发保存请求
    expect(apiMock.saveDraft).not.toHaveBeenCalled()
  })

  it('⑤大纲跨段选区(anchor 含单 \\n,md buffer 块间 \\n\\n)→ \\n→\\n\\n 兜底精确替换', async () => {
    const crossParaSel = `第一段末${SEL_TEXT}\n第二段开头`
    apiMock.chapter.mockResolvedValue({
      title: '三',
      // buffer 里块间是 \n\n(docToMd 口径),与选区文本(块间单 \n)不逐字一致
      synopsis: `前情。\n\n第一段末${SEL_TEXT}\n\n第二段开头\n\n后续。`,
      beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [],
    })
    selActionState.text = crossParaSel

    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|synopsis' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'outline', seq: 3, target: null, content: '跨段替换后', ts: 1 } }))
    const replaceBtn = await screen.findByRole('button', { name: '替换选中段' })
    fireEvent.click(replaceBtn)

    const textarea = screen.getByRole('textbox', { name: '本章大纲' })
    expect(textarea.value).toBe('前情。\n\n跨段替换后\n\n后续。')
  })

  it('⑥切章清 selAnchor:再来 proposal 不出「替换选中段」', async () => {
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|synopsis' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent.click(screen.getByRole('button', { name: '下一章' }))
    await waitFor(() => expect(apiMock.chapter).toHaveBeenCalledWith(4))
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'outline', seq: 4, target: null, content: '第四章新内容', ts: 2 } }))
    await screen.findByText(/主编生成了内容/)
    expect(screen.queryByRole('button', { name: '替换选中段' })).toBeNull()
    expect(screen.getByRole('button', { name: '填入' })).toBeTruthy()
  })
})

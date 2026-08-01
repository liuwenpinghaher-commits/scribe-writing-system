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
vi.mock('../WriteLayout', async () => {
  const React = await import('react')
  return {
    WriteLayout: () => <div data-testid="write-layout" />,
    RestoreContext: React.createContext(0),
  }
})
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

describe.skip('ChapterStudio 大纲/草稿选区聊这段/改这段(Task 2) — obsolete after outline seed-only', () => {
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

  it('③b 自重叠子串(anchor「轰轰」在「轰轰轰」里重叠出现两次)→ 判多处走降级,不出「替换选中段」', async () => {
    // 非重叠扫描(游标跳 needle.length)在「轰轰轰」里只数到 1 处「轰轰」,会误判唯一并
    // String.replace 替换第一处——用户选的可能是第二处,静默错替。唯一性必须覆盖重叠命中
    // (indexOf !== lastIndexOf 天然覆盖)。
    apiMock.chapter.mockResolvedValue({
      title: '三', synopsis: '前情。\n\n轰轰轰\n\n后续。', beats: [], focalizer: 'role:小翠',
      prose: '', deductions: [], involved_characters: [],
    })
    selActionState.text = '轰轰'

    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')

    fireEvent.click(screen.getByRole('button', { name: '改这段-3|synopsis' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'outline', seq: 3, target: null, content: '替换内容', ts: 1 } }))

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

// ——— Task 3:节拍条目级「聊这条/改这条」———
// 节拍是结构化条目,不是选区;两钮是行内动作(与既有增删/上下移同排的实按钮),不经
// RichEditor onSelAction。落地锚点是 _id(条目可能被上下移,_id 稳定;唯一性天然成立,
// 不像大纲/草稿要子串唯一命中兜底)。
describe.skip('ChapterStudio 节拍条目级聊这条/改这条(Task 3) — obsolete after beats seed-only', () => {
  const beatsFixture = () => [
    { text: '焦三第一次见到铜炉', done: false },
    { text: '铜炉认主的异象', done: false },
  ]

  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({
      title: '三', synopsis: '', beats: beatsFixture(), focalizer: 'role:小翠',
      prose: '', deductions: [], involved_characters: [],
    })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }, { seq: 4 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
    apiMock.patchChapter.mockResolvedValue({ ok: true })
    apiMock.saveDraft.mockResolvedValue({ ok: true })
  })

  async function openBeatsTab() {
    renderStudio()
    fireEvent.click(await screen.findByRole('tab', { name: '节拍' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('beats'))
  }

  // 每条节拍用其精简 RichEditor 的 ariaLabel(`节拍 ${i+1}`)定位所在行容器(.group),
  // 再在行内 scope 查动作按钮——按钮文案/aria-label 在多行间刻意同名(沿既有上移/删除惯例)。
  const beatRow = (label) => screen.getByRole('textbox', { name: label }).closest('.group')

  it('①聊这条 → chiefIntent 含该条文本与序号 + 派发 s3-right-tab 聚焦主编', async () => {
    const onRightTab = vi.fn()
    window.addEventListener('s3-right-tab', onRightTab)
    try {
      await openBeatsTab()
      fireEvent.click(within(beatRow('节拍 1')).getByRole('button', { name: '就这条节拍和主编讨论' }))

      const raw = await screen.findByTestId('chief-intent-sentinel')
      await waitFor(() => expect(raw.textContent).not.toBe(''))
      const intent = JSON.parse(raw.textContent)
      expect(intent.phase).toBe('beats')
      expect(intent.seq).toBe(3)
      expect(intent.text).toContain('焦三第一次见到铜炉')
      expect(intent.text).toContain('第1条节拍')
      expect(intent.text).toContain('聊聊')

      expect(onRightTab).toHaveBeenCalledTimes(1)
      expect(onRightTab.mock.calls[0][0].detail).toBe('chief')
    } finally {
      window.removeEventListener('s3-right-tab', onRightTab)
    }
  })

  it('②改这条 → chiefIntent 含「改」与该条文本 + 记 beatSel;proposal → 「替换该条」精确替换 + patchChapter(剥 _id)', async () => {
    await openBeatsTab()
    fireEvent.click(within(beatRow('节拍 2')).getByRole('button', { name: '让主编改这条节拍' }))

    const raw = await screen.findByTestId('chief-intent-sentinel')
    await waitFor(() => expect(raw.textContent).not.toBe(''))
    const intent = JSON.parse(raw.textContent)
    expect(intent.phase).toBe('beats')
    expect(intent.text).toContain('改')
    expect(intent.text).toContain('铜炉认主的异象')

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 3, target: null, content: '铜炉在焦三掌心发烫', ts: 1 } }))

    const replaceBtn = await screen.findByRole('button', { name: '替换该条' })
    fireEvent.click(replaceBtn)

    // 同步读(不经 waitFor 轮询):commit 的 setBeats 已在 fireEvent 的 act() 内同步落定;
    // 若改用 waitFor 轮询,onSaved→setRefresh 触发的 api.chapter() 静默刷新会用 apiMock
    // 的静态 mockResolvedValue(未反映刚落库的改动)把编辑器冲回原文——这是测试替身的局限
    // (真后端会回读到刚 patch 的新值),沿用 Task 2 outline/draft 用例同款同步读法回避。
    expect(screen.getByRole('textbox', { name: '节拍 2' }).value).toBe('铜炉在焦三掌心发烫')
    expect(screen.getByRole('textbox', { name: '节拍 1' }).value).toBe('焦三第一次见到铜炉')
    await waitFor(() => expect(apiMock.patchChapter).toHaveBeenCalled())
    expect(apiMock.patchChapter).toHaveBeenCalledWith(3, {
      beats: [
        { text: '焦三第一次见到铜炉', done: false },
        { text: '铜炉在焦三掌心发烫', done: false },
      ],
    }, 'demo')
  })

  it('③proposal 解析出多条时「替换该条」只取第一条文本(不整段塞进单条字段)', async () => {
    await openBeatsTab()
    fireEvent.click(within(beatRow('节拍 1')).getByRole('button', { name: '让主编改这条节拍' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 3, target: null, content: '- 第一条改稿\n- 第二条改稿', ts: 1 } }))
    // 不静默截断(spec 原则):多条时 ProposalBar 文案明示只取第 1 条、其余不落地,含条数。
    await screen.findByText(/本次改稿解析出 2 条,替换仅取第 1 条,其余不落地/)
    fireEvent.click(screen.getByRole('button', { name: '替换该条' }))

    // 同步读,理由同上一条用例(避开静态 mock 刷新把编辑器冲回原文的测试替身局限)。
    expect(screen.getByRole('textbox', { name: '节拍 1' }).value).toBe('第一条改稿')
  })

  it('③b 单条改稿不出现截断提示(N>1 才显示)', async () => {
    await openBeatsTab()
    fireEvent.click(within(beatRow('节拍 1')).getByRole('button', { name: '让主编改这条节拍' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 3, target: null, content: '唯一一条改稿', ts: 1 } }))
    await screen.findByRole('button', { name: '替换该条' })
    expect(screen.queryByText(/其余不落地/)).toBeNull()
  })

  it('④未点「改这条」(无 beatSel)时 proposal 到来维持现状「追加为新条目」', async () => {
    await openBeatsTab()
    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 3, target: null, content: '- 新节拍甲\n- 新节拍乙', ts: 1 } }))
    await screen.findByText(/主编生成了 2 条节拍/)
    expect(screen.queryByRole('button', { name: '替换该条' })).toBeNull()
    expect(screen.getByRole('button', { name: '追加为新条目' })).toBeTruthy()
  })

  it('⑤记了 beatSel 后目标条目被删 → proposal 到来降级「追加为新条目」+ 明示提示', async () => {
    await openBeatsTab()
    fireEvent.click(within(beatRow('节拍 2')).getByRole('button', { name: '让主编改这条节拍' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent.click(within(beatRow('节拍 2')).getByRole('button', { name: '删除' }))
    await waitFor(() => expect(apiMock.patchChapter).toHaveBeenCalled())

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 3, target: null, content: '改后的内容', ts: 2 } }))
    await screen.findByText(/主编生成了/)
    expect(screen.queryByRole('button', { name: '替换该条' })).toBeNull()
    expect(screen.getByRole('button', { name: '追加为新条目' })).toBeTruthy()
    expect(screen.getByText('该条节拍已被删除,按追加处理')).toBeTruthy()
  })

  it('⑥切章清 beatSel:再来 proposal 不出「替换该条」', async () => {
    await openBeatsTab()
    fireEvent.click(within(beatRow('节拍 1')).getByRole('button', { name: '让主编改这条节拍' }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).not.toBe(''))

    fireEvent.click(screen.getByRole('button', { name: '下一章' }))
    await waitFor(() => expect(apiMock.chapter).toHaveBeenCalledWith(4))
    // StudioHost 固定传 initialPhase="outline"(harness 简化;真实调用方 DetailPane 换章后
    // node 不带 phase,不会强制跳回大纲),换章后 ChapterStudio 的 initialPhase 效应会把
    // phase 弹回大纲,需要重新点节拍 tab——BeatsTab 因而重挂载,beatSel 无论靠 useEffect(seq)
    // 清空还是靠重挂载清零,行为都可观测为「不再出现替换该条」,断言本身仍然成立。
    fireEvent.click(await screen.findByRole('tab', { name: '节拍' }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('beats'))

    fireEvent(window, new CustomEvent('s3:stage-proposal', { detail: { phase: 'beats', seq: 4, target: null, content: '第四章节拍改稿', ts: 3 } }))
    await screen.findByText(/主编生成了/)
    expect(screen.queryByRole('button', { name: '替换该条' })).toBeNull()
    expect(screen.getByRole('button', { name: '追加为新条目' })).toBeTruthy()
  })
})


describe('ChapterStudio outline/beats seed policy', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('seedChiefNarrativeWrite for outline focuses chief without patch', async () => {
    const { seedChiefNarrativeWrite } = await import('../lib/chiefSeed.js')
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    seedChiefNarrativeWrite('outline', '第 3 章大纲', '请更新 synopsis')
    expect(seeds[0]).toMatch(/第 3 章大纲/)
    expect(tabs).toContain('chief')
  })
})

describe('ChapterStudio outline seed CTA (real UI)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    apiMock.chapter.mockResolvedValue({
      seq: 3, title: '三', synopsis: '炉前对峙。', beats: [{ text: 'A', done: false }],
      word_count: 0, drafts: [], focalizer: null, prose: '', deductions: [], involved_characters: [],
    })
    apiMock.chapters.mockResolvedValue([{ seq: 3 }])
    apiMock.entities.mockResolvedValue([])
    apiMock.latestDraft?.mockResolvedValue?.({ prose: '' })
    apiMock.patchChapter.mockResolvedValue({})
  })

  it('outline-ask-chief seeds and focuses right tab without patchChapter', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    renderStudio({ seq: 3, initialPhase: 'outline' })
    const btn = await screen.findByTestId('outline-ask-chief')
    fireEvent.click(btn)
    expect(seeds.length).toBeGreaterThan(0)
    expect(tabs).toContain('chief')
    expect(apiMock.patchChapter).not.toHaveBeenCalled()
  })

  it('draft 让主编生成会预填话术并通过统一事件聚焦主编', async () => {
    const tabs = []
    const onRightTab = (event) => tabs.push(event.detail)
    window.addEventListener('s3-right-tab', onRightTab)

    try {
      renderStudio({ seq: 3 })
      fireEvent.click(await screen.findByRole('tab', { name: '草稿' }))
      const draft = await screen.findByTestId('chapter-workbench-shell')
      expect(draft.getAttribute('data-phase')).toBe('draft')

      fireEvent.click(within(draft).getByRole('button', { name: '让主编生成' }))

      expect(tabs).toContain('chief')
      expect(JSON.parse(screen.getByTestId('chief-intent-sentinel').textContent)).toEqual({
        phase: 'draft',
        seq: 3,
        text: '据大纲和节拍给第 3 章写一版草稿',
      })
    } finally {
      window.removeEventListener('s3-right-tab', onRightTab)
    }
  })
})

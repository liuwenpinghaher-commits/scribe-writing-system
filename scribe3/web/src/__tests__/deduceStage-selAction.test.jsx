import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DeduceStage } from '../DeduceStage'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

// Task 4:演绎条目级「聊这条/改这条」——当前演绎目标(truth 或角色)的编辑区工具条两钮,
// 话术经 setChiefIntent 预填右栏 + 派发 s3-right-tab 聚焦;phase='deduce'(与 ChapterStudio
// setChapterPhase('deduce')/ChiefDock DiscussionDock 消费口径一致,核实见 Step 1)。
// 落地(替换当前目标 prose)复用既有 fillPending——零新逻辑,本测试不重复覆盖。

// 演绎当前选中目标(truth/character_id)由 deduceContext 的 DeduceProvider 持有,固定初值
// 'truth' 且不接受外部初值,故本文件直接打桩该 hook 以覆盖角色目标场景。
const deduceSelState = vi.hoisted(() => ({ selected: 'truth', setSelected: vi.fn() }))
vi.mock('../deduceContext', () => ({
  useDeduceSel: () => ({ selected: deduceSelState.selected, setSelected: deduceSelState.setSelected }),
}))

const apiMock = vi.hoisted(() => ({
  patchChapter: vi.fn(() => Promise.resolve({})),
  chapter: vi.fn(() => Promise.resolve({ deductions: [] })),
  chatWrite: vi.fn(),
  validateDeduction: vi.fn(() => Promise.resolve({ ok: false, issues: [{ reason: '无来源' }] })),
  groundedDeductionFallback: vi.fn(() => Promise.resolve({ candidate: '### 看到/听到\n未能从场景真相确认。' })),
}))
vi.mock('../api', () => ({ api: apiMock }))

vi.mock('../context/ContextSnapshotContext', () => ({
  useContextSnapshot: () => ({ snapshot: {
    session_id: 'ctx-deduce', revision: 7, context_hash: 'a'.repeat(64),
  } }),
}))

// RichEditor 打桩为受控 textarea,暴露 value 供断言当前 prose 是否已载入(与 chapterStudio-selAction
// 同款打桩风格),不测真实 TipTap 行为(已由 Task 1 单测覆盖)。
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: ({ value, onChange, onBlur, ariaLabel }) => (
    <textarea aria-label={ariaLabel} value={value || ''} onChange={(e) => onChange?.(e.target.value)} onBlur={onBlur} />
  ),
  useUnsavedGuard: vi.fn(),
}))

vi.mock('../ui/Toast.jsx', () => ({
  useToast: () => vi.fn(),
}))

function ChiefIntentSentinel() {
  const { chiefIntent } = useChiefSlot()
  return <div data-testid="chief-intent-sentinel">{chiefIntent ? JSON.stringify(chiefIntent) : ''}</div>
}

function renderDeduce(props) {
  return render(
    <ChiefSlotProvider>
      <DeduceStage seq={3} work="demo" {...props} />
      <ChiefIntentSentinel />
    </ChiefSlotProvider>,
  )
}

describe('DeduceStage 条目级聊这条/改这条(Task 4)', () => {
  beforeEach(() => {
    localStorage.clear()
    deduceSelState.selected = 'truth'
    deduceSelState.setSelected.mockClear()
    vi.clearAllMocks()
  })

  it('①truth 目标工具条渲染「聊这条」「改这条」两钮', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '真相文本' } })
    expect(await screen.findByRole('button', { name: '就这条演绎和主编讨论' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '让主编改这条演绎' })).toBeTruthy()
  })

  it('②truth「聊这条」→ chiefIntent { phase:"deduce", seq, text 含「场景真相」与「聊聊」与当前 prose } + 派发 s3-right-tab', async () => {
    const onRightTab = vi.fn()
    window.addEventListener('s3-right-tab', onRightTab)
    try {
      renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '真相正文内容' } })
      await waitFor(() => expect(screen.getByRole('textbox', { name: '场景真相' }).value).toBe('真相正文内容'))

      fireEvent.click(screen.getByRole('button', { name: '就这条演绎和主编讨论' }))

      const raw = await screen.findByTestId('chief-intent-sentinel')
      await waitFor(() => expect(raw.textContent).not.toBe(''))
      const intent = JSON.parse(raw.textContent)
      expect(intent.phase).toBe('deduce')
      expect(intent.seq).toBe(3)
      expect(intent.text).toContain('场景真相')
      expect(intent.text).toContain('真相正文内容')
      expect(intent.text).toContain('聊聊')

      expect(onRightTab).toHaveBeenCalledTimes(1)
      expect(onRightTab.mock.calls[0][0].detail).toBe('chief')
    } finally {
      window.removeEventListener('s3-right-tab', onRightTab)
    }
  })

  it('③truth「改这条」→ chiefIntent 话术含「改」与目标名与当前 prose', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '真相正文内容' } })
    await waitFor(() => expect(screen.getByRole('textbox', { name: '场景真相' }).value).toBe('真相正文内容'))

    fireEvent.click(screen.getByRole('button', { name: '让主编改这条演绎' }))

    const raw = await screen.findByTestId('chief-intent-sentinel')
    await waitFor(() => expect(raw.textContent).not.toBe(''))
    const intent = JSON.parse(raw.textContent)
    expect(intent.phase).toBe('deduce')
    expect(intent.text).toContain('改')
    expect(intent.text).toContain('场景真相')
    expect(intent.text).toContain('真相正文内容')
  })

  it('④角色目标(非 truth)→ chiefIntent 含角色名而非「场景真相」', async () => {
    deduceSelState.selected = 'c1'
    renderDeduce({
      meta: {
        chars: [{ id: 'c1', name: '焦三' }],
        deductions: [{ character_id: 'c1', character_name: '焦三', prose: '焦三的限知内容' }],
      },
    })
    await waitFor(() => expect(screen.getByRole('textbox', { name: '限知投影' }).value).toBe('焦三的限知内容'))

    fireEvent.click(screen.getByRole('button', { name: '就这条演绎和主编讨论' }))

    const raw = await screen.findByTestId('chief-intent-sentinel')
    await waitFor(() => expect(raw.textContent).not.toBe(''))
    const intent = JSON.parse(raw.textContent)
    expect(intent.text).toContain('焦三')
    expect(intent.text).not.toContain('场景真相')
    expect(intent.text).toContain('焦三的限知内容')
  })

  it('⑤prose 超过 400 字 → 话术引用截断到 400 字 + 省略号,不把全文塞进 chiefIntent', async () => {
    const longProse = '甲'.repeat(450)
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: longProse } })
    await waitFor(() => expect(screen.getByRole('textbox', { name: '场景真相' }).value).toBe(longProse))

    fireEvent.click(screen.getByRole('button', { name: '就这条演绎和主编讨论' }))

    const raw = await screen.findByTestId('chief-intent-sentinel')
    await waitFor(() => expect(raw.textContent).not.toBe(''))
    const intent = JSON.parse(raw.textContent)
    expect(intent.text).toContain('甲'.repeat(400) + '…')
    expect(intent.text).not.toContain(longProse)
  })

  it('⑥当前目标内容为空 → 两钮 disabled 且点击不写 chiefIntent(避免发出空引号话术)', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '' } })
    const chatBtn = await screen.findByRole('button', { name: '就这条演绎和主编讨论' })
    const editBtn = screen.getByRole('button', { name: '让主编改这条演绎' })
    expect(chatBtn.disabled).toBe(true)
    expect(editBtn.disabled).toBe(true)

    fireEvent.click(chatBtn)
    fireEvent.click(editBtn)
    expect(screen.getByTestId('chief-intent-sentinel').textContent).toBe('')
  })

  it('⑥b 纯空白内容(只有空格/换行)同样视为空 → 两钮 disabled', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '  \n\n  ' } })
    await waitFor(() => expect(screen.getByRole('textbox', { name: '场景真相' }).value).toBe('  \n\n  '))
    expect(screen.getByRole('button', { name: '就这条演绎和主编讨论' }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: '让主编改这条演绎' }).disabled).toBe(true)
  })

  it('⑦生成演绎时携带当前上下文快照，避免开启快照门后被后端静默拒绝', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '已有真相' } })
    await waitFor(() => expect(screen.getByRole('textbox', { name: '场景真相' }).value).toBe('已有真相'))

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    expect(apiMock.chatWrite).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
      chapter: 3,
      phase: 'deduce',
      context: { context_session_id: 'ctx-deduce', context_revision: 7, context_hash: 'a'.repeat(64) },
    }))
  })

  it('⑧四栏工作台可把角色显式加入本章再切换到该角色投射，且不覆盖已有涉及角色', async () => {
    apiMock.chapter.mockResolvedValue({ involved_characters: ['role:沈砚'], deductions: [] })
    renderDeduce({
      meta: {
        chars: [{ id: 'role:沈砚', name: '沈砚' }, { id: 'role:季棠', name: '季棠' }],
        deductions: [], involved_characters: ['role:沈砚'], scene_truth: '已有场景真相',
      },
    })
    await screen.findByRole('combobox', { name: '投射角色' })

    fireEvent.change(screen.getByRole('combobox', { name: '投射角色' }), { target: { value: 'role:季棠' } })
    fireEvent.click(screen.getByRole('button', { name: '加入并切换角色' }))

    await waitFor(() => expect(apiMock.patchChapter).toHaveBeenCalledWith(3, {
      involved_characters: ['role:沈砚', 'role:季棠'],
    }, 'demo'))
    expect(deduceSelState.setSelected).toHaveBeenCalledWith('role:季棠')
  })

  it('⑨角色投射提示不预设男性代词，并要求遵循角色档案称谓', async () => {
    deduceSelState.selected = 'role:季棠'
    renderDeduce({ meta: { chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '已有场景真相' } })
    await screen.findByRole('button', { name: '生成' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    const [instruction] = apiMock.chatWrite.mock.calls[0]
    expect(instruction).toContain('严格遵循角色档案已有的称谓和代词')
    expect(instruction).toContain('不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史')
    expect(instruction).not.toContain('写他这一场')
    expect(instruction).not.toContain('只含他所知所感')
  })

  it('⑩角色投射生成后先做服务端事实对齐，失败时不得自动写入 deductions', async () => {
    deduceSelState.selected = 'role:季棠'
    apiMock.chatWrite.mockImplementation((_instruction, handlers) => {
      handlers.onProposalStart?.()
      handlers.onProposal?.({ prose: '黑水从闸底涌出。' })
      handlers.onDone?.()
    })
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    } })
    await screen.findByRole('textbox', { name: '限知投影' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(apiMock.validateDeduction).toHaveBeenCalledWith(
      3, '黑水从闸底涌出。', 'role:季棠', 'demo',
    ))
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(apiMock.patchChapter).not.toHaveBeenCalledWith(3, expect.objectContaining({ deductions: expect.anything() }), 'demo')
  })

  it('⑪首稿越过事实边界时带着校验反馈自动返修一次，返修合格后才进入待确认保存态', async () => {
    deduceSelState.selected = 'role:季棠'
    apiMock.validateDeduction
      .mockResolvedValueOnce({ ok: false, issues: [{ reason: '黑水无场景真相来源' }] })
      .mockResolvedValueOnce({ ok: true })
    apiMock.chatWrite
      .mockImplementationOnce((_instruction, handlers) => {
        handlers.onProposalStart?.()
        handlers.onProposal?.({ prose: '黑水从闸底涌出。' })
        handlers.onDone?.()
      })
      .mockImplementationOnce((_instruction, handlers) => {
        handlers.onProposalStart?.()
        handlers.onProposal?.({ prose: '### 看到/听到\n季棠看见闸门震颤。' })
        handlers.onDone?.()
      })
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    } })
    await screen.findByRole('textbox', { name: '限知投影' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(apiMock.chatWrite).toHaveBeenCalledTimes(2))
    const [repairInstruction] = apiMock.chatWrite.mock.calls[1]
    expect(repairInstruction).toContain('黑水无场景真相来源')
    expect(repairInstruction).toContain('只保留能够由场景真相直接支持的主张')
    await waitFor(() => expect(apiMock.validateDeduction).toHaveBeenLastCalledWith(
      3, '### 看到/听到\n季棠看见闸门震颤。', 'role:季棠', 'demo',
    ))
    expect(apiMock.patchChapter).not.toHaveBeenCalledWith(3, expect.objectContaining({ deductions: expect.anything() }), 'demo')
    expect(screen.getByRole('status').textContent).toContain('事实对齐通过')
  })

  it('⑪b 两次自由稿都未过事实门时切换服务端可追溯摘录，并只在摘录复核通过后待保存', async () => {
    deduceSelState.selected = 'role:季棠'
    const safe = '### 看到/听到\n季棠用潮骨灯照出黑盐纹。\n\n### 知道\n季棠看出潮闸在主动索名。'
    apiMock.validateDeduction
      .mockResolvedValueOnce({ ok: false, issues: [{ reason: '首稿无来源' }] })
      .mockResolvedValueOnce({ ok: false, issues: [{ reason: '返修稿无来源' }] })
      .mockResolvedValueOnce({ ok: true })
    apiMock.groundedDeductionFallback.mockResolvedValueOnce({ candidate: safe, mode: 'verbatim_fallback' })
    apiMock.chatWrite
      .mockImplementationOnce((_instruction, handlers) => { handlers.onProposal?.({ prose: '首稿越界。' }); handlers.onDone?.() })
      .mockImplementationOnce((_instruction, handlers) => { handlers.onProposal?.({ prose: '返修仍越界。' }); handlers.onDone?.() })
    renderDeduce({ meta: { chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '已有场景真相' } })
    await screen.findByRole('textbox', { name: '限知投影' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(apiMock.groundedDeductionFallback).toHaveBeenCalledWith(3, 'role:季棠', 'demo'))
    await waitFor(() => expect(apiMock.validateDeduction).toHaveBeenLastCalledWith(3, safe, 'role:季棠', 'demo'))
    expect(screen.getByRole('status').textContent).toContain('事实对齐通过')
  })

  it('⑫生成流超过作者等待上限时中止请求并恢复生成入口，且不把半成品标为待保存投影', async () => {
    const abort = vi.fn()
    apiMock.chatWrite.mockReturnValue({ abort })
    deduceSelState.selected = 'role:季棠'
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    } })
    await screen.findByRole('button', { name: '生成' })

    vi.useFakeTimers()
    try {
      fireEvent.click(screen.getByRole('button', { name: '生成' }))
      expect(screen.getByRole('button', { name: '演绎中…' })).toBeTruthy()

      await act(async () => { await vi.advanceTimersByTimeAsync(120_000) })

      expect(abort).toHaveBeenCalledTimes(1)
      expect(screen.getByRole('button', { name: '生成' })).toBeTruthy()
      expect(apiMock.validateDeduction).not.toHaveBeenCalled()
      expect(screen.getByRole('status').textContent).toContain('未完成内容不会自动保存为投影')
    } finally {
      vi.useRealTimers()
    }
  })
})

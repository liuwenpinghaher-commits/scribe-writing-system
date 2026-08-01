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
  runWrite: vi.fn(),
  aiRunApproval: vi.fn(() => Promise.resolve({ status: 'resumed' })),
  aiRunPendingApproval: vi.fn(() => Promise.resolve({ runs: [] })),
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
      await waitFor(() => expect(screen.getByTestId('deduce-readonly').textContent).toContain('真相正文内容'))

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
    await waitFor(() => expect(screen.getByTestId('deduce-readonly').textContent).toContain('真相正文内容'))

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
    await waitFor(() => expect(screen.getByTestId('deduce-readonly').textContent).toContain('焦三的限知内容'))

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
    await waitFor(() => expect(screen.getByTestId('deduce-readonly').textContent).toContain(longProse))

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
    await screen.findByTestId('deduce-readonly')
    // 只读空态把纯空白视为无内容(与 noProse 一致)
    expect(screen.getByRole('button', { name: '就这条演绎和主编讨论' }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: '让主编改这条演绎' }).disabled).toBe(true)
  })

  it('⑦生成演绎时经只读预览 Run 携带当前上下文快照，不能绕过阶段工具面', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '已有真相' } })
    await waitFor(() => expect(screen.getByTestId('deduce-readonly').textContent).toContain('已有真相'))

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    expect(apiMock.runWrite).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
      chapter: 3,
      phase: 'deduce_preview',
      context: { context_session_id: 'ctx-deduce', context_revision: 7, context_hash: 'a'.repeat(64) },
    }))
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑦b场景真相预览明确要求先读取当前章节，避免受限 Run 在未取正典时假完成', async () => {
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '已有真相' } })
    await screen.findByTestId('deduce-readonly')

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    const [instruction] = apiMock.runWrite.mock.calls[0]
    expect(instruction).toContain('必须先调用一次 s3_get_chapter')
    expect(instruction).toContain('不得调用写工具')
  })

  it('⑧四栏工作台加入角色只切换演绎目标，不以主编种子或 REST 旁路改 involved', async () => {
    renderDeduce({
      meta: {
        chars: [
          { id: 'role:沈砚', name: '沈砚' },
          { id: 'role:季棠', name: '季棠' },
        ],
        deductions: [],
        scene_truth: '真相',
        involved_characters: ['role:季棠'],
      },
    })
    const select = await screen.findByLabelText('投射角色')
    fireEvent.change(select, { target: { value: 'role:沈砚' } })
    fireEvent.click(screen.getByRole('button', { name: /加入并切换角色/ }))
    await waitFor(() => expect(screen.getByTestId('chief-intent-sentinel').textContent).toContain('沈砚'))
    expect(apiMock.patchChapter).not.toHaveBeenCalled()
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑨角色投射提示不预设男性代词，并要求遵循角色档案称谓', async () => {
    deduceSelState.selected = 'role:季棠'
    renderDeduce({ meta: { chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '已有场景真相' } })
    await screen.findByRole('button', { name: '生成' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    const [instruction] = apiMock.runWrite.mock.calls[0]
    expect(instruction).toContain('严格遵循角色档案已有的称谓和代词')
    expect(instruction).toContain('不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史')
    expect(instruction).not.toContain('写他这一场')
    expect(instruction).not.toContain('只含他所知所感')
  })

  it('⑩角色投影预览先经服务端事实对齐，失败时不能提交审批或 REST 写 deductions', async () => {
    deduceSelState.selected = 'role:季棠'
    apiMock.runWrite.mockImplementation((_instruction, handlers) => {
      handlers.onDelta?.('黑水从闸底涌出。')
      handlers.onDone?.()
    })
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    } })
    await screen.findByTestId('deduce-readonly')

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(apiMock.validateDeduction).toHaveBeenCalledWith(
      3, '黑水从闸底涌出。', 'role:季棠', 'demo',
    ))
    expect(screen.getByTestId('deduce-submit-preview').disabled).toBe(true)
    expect(apiMock.patchChapter).not.toHaveBeenCalledWith(3, expect.objectContaining({ deductions: expect.anything() }), 'demo')
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑪受限 Run 失败时不把流式半成品标记为章节已保存', async () => {
    deduceSelState.selected = 'role:季棠'
    apiMock.runWrite.mockImplementation((_instruction, handlers) => {
      handlers.onDelta?.('黑水从闸底涌出。')
      handlers.onError?.('阶段工具策略校验失败')
    })
    const onSaved = vi.fn()
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    }, onSaved })
    await screen.findByTestId('deduce-readonly')

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(screen.getByRole('button', { name: '生成' })).toBeTruthy())
    expect(onSaved).not.toHaveBeenCalled()
    expect(apiMock.patchChapter).not.toHaveBeenCalledWith(3, expect.objectContaining({ deductions: expect.anything() }), 'demo')
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑪b通过事实对齐的角色预览提交时，第二个 Run 才携带完整 deductions 集合走受限 MCP 写入', async () => {
    deduceSelState.selected = 'role:季棠'
    apiMock.validateDeduction.mockResolvedValueOnce({ ok: true })
    apiMock.runWrite
      .mockImplementationOnce((_instruction, handlers) => { handlers.onDelta?.('### 看到/听到\n季棠看见闸门震颤。'); handlers.onDone?.() })
      .mockImplementationOnce(() => ({ abort: vi.fn() }))
    renderDeduce({ meta: { chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '已有场景真相' } })
    await screen.findByTestId('deduce-readonly')

    fireEvent.click(screen.getByRole('button', { name: '生成' }))

    await waitFor(() => expect(screen.getByTestId('deduce-submit-preview').disabled).toBe(false))
    fireEvent.click(screen.getByTestId('deduce-submit-preview'))
    const [instruction, options] = apiMock.runWrite.mock.calls[1]
    expect(instruction).toContain('s3_patch_chapter_plan')
    expect(instruction).toContain('"deductions"')
    expect(instruction).toContain('"involved_characters"')
    expect(options.phase).toBe('deduce')
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑪c作者可先修订场景真相预览，提交 Run 必须携带修订后的内容而非模型原文', async () => {
    apiMock.runWrite
      .mockImplementationOnce((_instruction, handlers) => {
        handlers.onDelta?.('模型原始场景真相')
        handlers.onDone?.()
      })
      .mockImplementationOnce(() => ({ abort: vi.fn() }))
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '' } })

    fireEvent.click(await screen.findByRole('button', { name: '生成' }))
    await waitFor(() => expect(screen.getByTestId('deduce-submit-preview').disabled).toBe(false))

    fireEvent.click(screen.getByRole('button', { name: '编辑预览' }))
    fireEvent.change(screen.getByTestId('deduce-preview-editor'), {
      target: { value: '作者修订后的场景真相' },
    })
    fireEvent.click(screen.getByRole('button', { name: '完成预览编辑' }))
    fireEvent.click(screen.getByTestId('deduce-submit-preview'))

    const [instruction, options] = apiMock.runWrite.mock.calls[1]
    expect(instruction).toContain('作者修订后的场景真相')
    expect(instruction).not.toContain('模型原始场景真相')
    expect(options.phase).toBe('deduce')
  })

  it('⑫生成流超过作者等待上限时中止请求并恢复生成入口，且不把半成品标为待保存投影', async () => {
    const abort = vi.fn()
    apiMock.runWrite.mockReturnValue({ abort })
    deduceSelState.selected = 'role:季棠'
    renderDeduce({ meta: {
      chars: [{ id: 'role:季棠', name: '季棠' }], deductions: [], scene_truth: '潮闸震颤。',
    } })
    await screen.findByRole('button', { name: '生成' })

    vi.useFakeTimers()
    try {
      fireEvent.click(screen.getByRole('button', { name: '生成' }))
      await act(async () => { await vi.advanceTimersByTimeAsync(360_000) })

      expect(abort).toHaveBeenCalledTimes(1)
      expect(screen.getByRole('button', { name: '生成' })).toBeTruthy()
      expect(apiMock.patchChapter).not.toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })

  it('⑬受限 Run 请求写入时，作者可在演绎工作台批准而不是被迫绕回未受限主编对话', async () => {
    apiMock.runWrite
      .mockImplementationOnce((_instruction, handlers) => { handlers.onDelta?.('新的场景真相'); handlers.onDone?.(); return { abort: vi.fn() } })
      .mockImplementationOnce((_instruction, handlers) => {
        queueMicrotask(() => {
          handlers.onRun?.({ run_id: 'deduce_run_1' })
          handlers.onApproval?.({ run_id: 'deduce_run_1', approval_id: 'approval_1', message: '允许写入第3章演绎？' })
        })
        return { abort: vi.fn() }
      })
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '已有真相' } })
    await screen.findByRole('button', { name: '生成' })

    fireEvent.click(screen.getByRole('button', { name: '生成' }))
    await waitFor(() => expect(screen.getByTestId('deduce-submit-preview').disabled).toBe(false))
    fireEvent.click(screen.getByTestId('deduce-submit-preview'))

    expect(await screen.findByText('允许写入第3章演绎？')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '批准演绎写入' }))
    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledWith('deduce_run_1', {
      approval_id: 'approval_1', decision: 'approve',
    }))
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
  })

  it('⑭刷新重挂后从持久 Run trace 恢复本章待审批卡，并仍可批准', async () => {
    apiMock.aiRunPendingApproval.mockResolvedValueOnce({
      runs: [{
        run_id: 'deduce_run_after_refresh',
        approval_id: 'approval_after_refresh',
        message: '刷新后仍须由作者确认写入第3章演绎。',
      }],
    })
    const onSaved = vi.fn()
    renderDeduce({ meta: { chars: [], deductions: [], scene_truth: '等待批准的真相' }, onSaved })

    expect(await screen.findByText('刷新后仍须由作者确认写入第3章演绎。')).toBeTruthy()
    expect(apiMock.aiRunPendingApproval).toHaveBeenCalledWith({ chapter: 3, phase: 'deduce' }, 'demo')

    fireEvent.click(screen.getByRole('button', { name: '批准演绎写入' }))
    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledWith('deduce_run_after_refresh', {
      approval_id: 'approval_after_refresh', decision: 'approve',
    }))
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
  })
})

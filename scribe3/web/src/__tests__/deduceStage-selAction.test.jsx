import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DeduceStage } from '../DeduceStage'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

// Task 4:演绎条目级「聊这条/改这条」——当前演绎目标(truth 或角色)的编辑区工具条两钮,
// 话术经 setChiefIntent 预填右栏 + 派发 s3-right-tab 聚焦;phase='deduce'(与 ChapterStudio
// setChapterPhase('deduce')/ChiefDock DiscussionDock 消费口径一致,核实见 Step 1)。
// 落地(替换当前目标 prose)复用既有 fillPending——零新逻辑,本测试不重复覆盖。

// 演绎当前选中目标(truth/character_id)由 deduceContext 的 DeduceProvider 持有,固定初值
// 'truth' 且不接受外部初值,故本文件直接打桩该 hook 以覆盖角色目标场景。
const deduceSelState = vi.hoisted(() => ({ selected: 'truth' }))
vi.mock('../deduceContext', () => ({
  useDeduceSel: () => ({ selected: deduceSelState.selected, setSelected: () => {} }),
}))

vi.mock('../api', () => ({
  api: {
    patchChapter: vi.fn(() => Promise.resolve({})),
    chapter: vi.fn(() => Promise.resolve({ deductions: [] })),
    chatWrite: vi.fn(),
  },
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
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// 上下文快照 hook 桩:各测试改写 ctx.value 注入 focus/revision/降级态。
const ctx = vi.hoisted(() => ({
  value: { snapshot: null, restoring: false, error: null, capabilities: null },
}))
vi.mock('./ContextSnapshotContext', () => ({
  useContextSnapshot: () => ctx.value,
}))

// 真端点契约:/ai/runtime-status 顶层只有 ok,降级在 summary.degraded(app._hermes_runtime_status)。
const apiMock = vi.hoisted(() => ({
  getMemoryTrace: vi.fn(),
  aiRuntimeStatus: vi.fn(() => Promise.resolve({ ok: true, summary: { degraded: {} } })),
}))
vi.mock('../api', () => ({ api: apiMock }))

import { ContextInspector } from './ContextInspector'

const SNAPSHOT = {
  session_id: 'sess-1', revision: 7, context_hash: 'h',
  focus: { type: 'chapter', id: '7', label: '铜炉认主' },
}

const CAPS_ON = {
  flags: {
    snapshot_v1: true,
    editorial_thread_v1: false,
    memory_fabric_v1: true,
    context_inspector_v1: true,
    assembler_v1: true,
  },
  versions: {},
}

const TRACE = {
  available: true,
  availability: 'ready',
  view_version: 'context-turn-view.v1',
  trace_id: 'trace-1', snapshot_revision: 7,
  channels: { structured: 2, bm25: 3 },
  block_tokens: {
    focus: 20, global: 40, canonical: 120, recent: 80,
    procedural: 0, reference: 0, uncertainty: 0, provenance: 50,
  },
  blocks: [
    { name: 'focus', token_estimate: 20, source_ids: ['focus:q'], source_count: 1 },
    { name: 'global', token_estimate: 40, source_ids: ['intent:north'], source_count: 1 },
    { name: 'canonical', token_estimate: 120, source_ids: ['fact:origin'], source_count: 1 },
    { name: 'recent', token_estimate: 80, source_ids: ['mem:12'], source_count: 1 },
    { name: 'procedural', token_estimate: 0, source_ids: [], source_count: 0 },
    { name: 'reference', token_estimate: 0, source_ids: [], source_count: 0 },
    { name: 'uncertainty', token_estimate: 0, source_ids: [], source_count: 0 },
    { name: 'provenance', token_estimate: 50, source_ids: ['prov:1'], source_count: 1 },
  ],
  selected: [
    { source_id: 'fact:origin', source_kind: 'canonical', reason: 'canonical', confidence: 1.0, observed_at: null, secret: false, text: '柳怀玉是铜炉旁的孤儿' },
    { source_id: 'mem:12', source_kind: 'episodic', reason: 'relevance_rank', confidence: 0.72, observed_at: '2026-07-10T00:00:00+00:00', secret: false, text: '他在庙会见过那盏灯' },
  ],
  rejected: [
    { source_id: 'mem:99', source_kind: 'episodic', reason: 'conflicts_with_canonical', confidence: 0.6, observed_at: '2026-07-09T00:00:00+00:00', secret: false, text: '被正典压制的传闻' },
  ],
  latency_ms: { total: 42 },
}

beforeEach(() => {
  vi.clearAllMocks()
  ctx.value = { snapshot: SNAPSHOT, restoring: false, error: null, capabilities: CAPS_ON }
  apiMock.getMemoryTrace.mockResolvedValue(TRACE)
  apiMock.aiRuntimeStatus.mockResolvedValue({ ok: true, summary: { degraded: {} } })
})

describe('ContextInspector · capabilities 诚实门控', () => {
  it('context_inspector_v1 关时不渲染(不暗示检查器已就绪)', () => {
    ctx.value = {
      snapshot: SNAPSHOT, restoring: false, error: null,
      capabilities: { flags: { ...CAPS_ON.flags, context_inspector_v1: false }, versions: {} },
    }
    render(<ContextInspector />)
    expect(screen.queryByTestId('context-inspector')).toBeNull()
    expect(apiMock.getMemoryTrace).not.toHaveBeenCalled()
  })

  it('capabilities 缺席时不渲染(安全默认=关)', () => {
    ctx.value = { snapshot: SNAPSHOT, restoring: false, error: null }
    render(<ContextInspector />)
    expect(screen.queryByTestId('context-inspector')).toBeNull()
  })
})

describe('ContextInspector · 第1层常显', () => {
  it('显示当前 focus、revision 与"主编知道你在看什么"', async () => {
    render(<ContextInspector />)
    expect(screen.getByTestId('context-inspector-focus').textContent).toBe('铜炉认主')
    expect(screen.getByTestId('context-inspector-revision').textContent).toContain('版本 7')
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('current'))
    expect(screen.getByTestId('context-inspector-status').textContent).toContain('主编知道你在看什么')
  })
})

describe('ContextInspector · 跨作品 trace 隔离', () => {
  it('按快照所属作品读取 trace，不依赖可能尚未同步的全局 work', async () => {
    ctx.value = {
      snapshot: { ...SNAPSHOT, work: 'book-context-isolated' },
      restoring: false,
      error: null,
      capabilities: CAPS_ON,
    }

    render(<ContextInspector />)

    await waitFor(() => expect(apiMock.getMemoryTrace).toHaveBeenCalledWith(
      'sess-1', 7, 'book-context-isolated',
    ))
  })
})

describe('ContextInspector · 第2层展开', () => {
  it('展开后显示八块 token + 块级源数', async () => {
    render(<ContextInspector />)
    await screen.findByTestId('context-inspector-focus')
    fireEvent.click(screen.getByTestId('context-inspector-toggle'))
    for (const k of ['focus', 'global', 'canonical', 'recent', 'procedural', 'reference', 'uncertainty', 'provenance']) {
      expect(screen.getByTestId(`context-block-${k}`)).toBeTruthy()
    }
    expect(screen.getByTestId('context-block-canonical').textContent).toContain('120 词元')
    expect(screen.getByTestId('context-block-canonical').textContent).toContain('正典')
    expect(screen.getByTestId('context-block-canonical').textContent).toContain('1 源')
    expect(screen.getByTestId('context-block-recent').textContent).toContain('1 源')
    expect(screen.getByTestId('context-block-focus').textContent).toContain('20 词元')
    expect(screen.getByTestId('context-block-focus').textContent).toContain('焦点')
  })
})

describe('ContextInspector · 第3层证据', () => {
  it('服务端尚未确认的乐观导航不请求该 revision 的 trace，避免瞬时 404', async () => {
    // 生产端先乐观推进 revision，再异步持久化；此间请求 trace 会以尚不存在的
    // revision 打到后端。这里钉住“未确认即不读”的消费边界。
    ctx.value = {
      snapshot: { ...SNAPSHOT, revision: 8 },
      snapshotConfirmed: false,
      restoring: false,
      error: null,
      capabilities: CAPS_ON,
    }

    render(<ContextInspector />)

    await Promise.resolve()
    expect(apiMock.getMemoryTrace).not.toHaveBeenCalled()
  })

  it('展开显示 selected/rejected 的 source id、时态、信心、理由', async () => {
    render(<ContextInspector />)
    await screen.findByTestId('context-inspector-focus')
    fireEvent.click(screen.getByTestId('context-inspector-toggle'))
    await screen.findByTestId('context-inspector-evidence')
    const sels = screen.getAllByTestId('evidence-selected')
    expect(sels).toHaveLength(2)
    expect(sels[0].getAttribute('data-source-id')).toBe('fact:origin')
    expect(sels[0].textContent).toContain('正典 · 恒真')
    expect(sels[0].textContent).toContain('信心 100%')
    const rej = screen.getByTestId('evidence-rejected')
    expect(rej.textContent).toContain('与正典冲突')
  })

  it('私密证据只显"秘密事实已屏蔽",不渲染 value(即便后端漏值)', async () => {
    apiMock.getMemoryTrace.mockResolvedValue({
      ...TRACE,
      selected: [{ source_id: 'fact:hidden', source_kind: 'canonical', reason: 'canonical', confidence: 1.0, observed_at: null, secret: true, masked: true, text: '绝密身份明文' }],
      rejected: [],
    })
    render(<ContextInspector />)
    await screen.findByTestId('context-inspector-focus')
    fireEvent.click(screen.getByTestId('context-inspector-toggle'))
    await screen.findByTestId('context-inspector-evidence')
    expect(screen.getByTestId('evidence-secret-masked').textContent).toContain('秘密事实已屏蔽')
    expect(screen.queryByText(/绝密身份明文/)).toBeNull()
  })

  it('有效快照尚未编译时诚实空态，不画假 0 块网格', async () => {
    // B∪C：available=false / not_compiled_yet → 不渲染假 0 tok 网格
    apiMock.getMemoryTrace.mockResolvedValue({
      available: false, availability: 'not_compiled_yet',
      session_id: 'sess-1', snapshot_revision: 7,
      reason: 'not_retrieved_yet', view_version: 'context-turn-view.v1',
    })
    render(<ContextInspector />)
    await screen.findByTestId('context-inspector-focus')
    fireEvent.click(screen.getByTestId('context-inspector-toggle'))
    await waitFor(() => expect(screen.getByTestId('context-inspector-no-evidence')).toBeTruthy())
    expect(screen.getByTestId('context-inspector-no-evidence').textContent).toMatch(/尚未完成|未编译/)
    expect(screen.queryByTestId('context-inspector-blocks')).toBeNull()
    expect(screen.queryByText(/没有相关事实/)).toBeNull()
    expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('current')
  })
})

describe('ContextInspector · 降级状态', () => {
  it('stale_context 错误 → 显示"上下文已过期"', async () => {
    ctx.value = {
      snapshot: SNAPSHOT, restoring: false, error: { code: 'stale_context' },
      capabilities: CAPS_ON,
    }
    render(<ContextInspector />)
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('stale'))
    expect(screen.getByTestId('context-inspector-status').textContent).toContain('过期')
  })

  it('runtime chat 降级 → hermes_offline', async () => {
    apiMock.aiRuntimeStatus.mockResolvedValue({ ok: false, summary: { degraded: { chat: true } } })
    render(<ContextInspector />)
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('hermes_offline'))
    expect(screen.getByTestId('context-inspector-status').textContent).toContain('离线')
  })

  // U-001 回归:网关在跑但周边检查降级(磁盘等)→ 黄字 hermes_degraded,不得谎报离线。
  it('probe degraded 但可用 → hermes_degraded 黄字(不是离线)', async () => {
    apiMock.aiRuntimeStatus.mockResolvedValue({
      ok: true,
      profiles: [{ profile: 'default', ok: true, degraded: true, degraded_reasons: ['disk'] }],
      summary: { degraded: {} },
    })
    render(<ContextInspector />)
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('hermes_degraded'))
    const txt = screen.getByTestId('context-inspector-status').textContent
    expect(txt).toContain('降级')
    expect(txt).not.toContain('离线')
    expect(txt).not.toContain('记忆检索不可用')
  })

  it('runtime write_runs 降级(chat 正常)→ hermes_read_only', async () => {
    apiMock.aiRuntimeStatus.mockResolvedValue({ ok: false, summary: { degraded: { write_runs: true } } })
    render(<ContextInspector />)
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('hermes_read_only'))
  })

  it('trace 拉取非 404 失败 → retrieval_degraded', async () => {
    apiMock.getMemoryTrace.mockRejectedValue(Object.assign(new Error('HTTP 500'), { status: 500 }))
    render(<ContextInspector />)
    await waitFor(() =>
      expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('retrieval_degraded'))
  })

  it('无会话(降级直通)→ optimistic,不崩', () => {
    ctx.value = { snapshot: null, restoring: false, error: null, capabilities: CAPS_ON }
    render(<ContextInspector />)
    expect(screen.getByTestId('context-inspector-status').getAttribute('data-status')).toBe('optimistic')
    expect(screen.getByTestId('context-inspector-focus').textContent).toBe('未选中')
  })
})

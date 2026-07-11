import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'

afterEach(() => {
  api.setWork('main')
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

const mockFetch = (ok, status, body) => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    status,
    json: async () => body,
  })
}

describe('api works 写操作 — res.ok 检查', () => {
  it('createWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '内部错误' })
    await expect(api.createWork('测试书')).rejects.toThrow('HTTP 500')
  })

  it('renameWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '重命名失败' })
    await expect(api.renameWork('test-slug', '新书名')).rejects.toThrow('HTTP 500')
  })

  it('deleteWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '删除失败' })
    await expect(api.deleteWork('test-slug')).rejects.toThrow('HTTP 500')
  })

  it('createWork 成功时返回 json', async () => {
    mockFetch(true, 201, { slug: 'new-book', title: '新书' })
    const result = await api.createWork('新书')
    expect(result).toEqual({ slug: 'new-book', title: '新书' })
  })

  it('materials 支持分页参数并保留 work 隔离', async () => {
    mockFetch(true, 200, { items: [], next_cursor: null, total: 0 })
    api.setWork('book_a')

    await api.materials({ kind: 'research', limit: 200, cursor: 2, view: 'referenced', q: '借命' })

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/materials?kind=research&limit=200&cursor=2&view=referenced&q=%E5%80%9F%E5%91%BD&work=book_a')
  })

  it('materialGraph 支持 focus/limit/hop 图谱参数', async () => {
    mockFetch(true, 200, { nodes: [], edges: [], truncated: false })

    await api.materialGraph({ focus: 'material:1', limit: 50, hop: 2 })

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/materials/graph?focus=material%3A1&limit=50&hop=2&work=main')
  })

  it('aiRunCreate/Approval 带当前 work 隔离', async () => {
    mockFetch(true, 200, { run_id: 'run_1' })
    api.setWork('book_a')

    await api.aiRunCreate({ input: '整理设定', instructions: '先核实' })
    await api.aiRunTrace('run_1')
    await api.aiRunApproval('run_1', { approval_id: 'ap_1', decision: 'approve' })

    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/api/ai/runs?work=book_a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: '整理设定', instructions: '先核实' }),
    })
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/api/ai/runs/run_1/trace?work=book_a')
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, '/api/ai/runs/run_1/approval?work=book_a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_id: 'ap_1', decision: 'approve' }),
    })
  })

  it('aiRunEvents 把 approval SSE 交给回调', () => {
    let instance = null
    const close = vi.fn()
    vi.stubGlobal('EventSource', class {
      constructor(url) {
        this.url = url
        this.close = close
        instance = this
      }
    })
    api.setWork('book_a')
    const onApproval = vi.fn()
    const onApprovalResolved = vi.fn()
    const onDone = vi.fn()

    const es = api.aiRunEvents('run_1', { onApproval, onApprovalResolved, onDone })

    expect(es).toBe(instance)
    expect(instance.url).toBe('/api/ai/runs/run_1/events?work=book_a')
    instance.onmessage({ data: JSON.stringify({ approval: { run_id: 'run_1', approval_id: 'ap_1', message: '允许?' } }) })
    instance.onmessage({ data: JSON.stringify({ approval_resolved: { run_id: 'run_1', approval_id: 'ap_1', decision: 'approve' } }) })
    instance.onmessage({ data: JSON.stringify({ done: true }) })

    expect(onApproval).toHaveBeenCalledWith({ run_id: 'run_1', approval_id: 'ap_1', message: '允许?' })
    expect(onApprovalResolved).toHaveBeenCalledWith({ run_id: 'run_1', approval_id: 'ap_1', decision: 'approve' })
    expect(close).toHaveBeenCalled()
    expect(onDone).toHaveBeenCalled()
  })

  it('aiRunEvents 把 tool_output SSE 交给回调', () => {
    let instance = null
    vi.stubGlobal('EventSource', class {
      constructor(url) {
        this.url = url
        this.close = vi.fn()
        instance = this
      }
    })
    const onToolOutput = vi.fn()

    api.aiRunEvents('run_1', { onToolOutput })
    instance.onmessage({ data: JSON.stringify({ tool_output: { ok: true }, tool_call_id: 'call_1' }) })

    expect(onToolOutput).toHaveBeenCalledWith({ ok: true }, 'call_1')
  })

  it('runWrite 创建 Hermes Run 并把事件桥接给写作回调', async () => {
    let instance = null
    const close = vi.fn()
    vi.stubGlobal('EventSource', class {
      constructor(url) {
        this.url = url
        this.close = close
        instance = this
      }
    })
    mockFetch(true, 200, { run_id: 'run_42' })
    api.setWork('book_a')
    const onApproval = vi.fn()
    const onDelta = vi.fn()
    const onRun = vi.fn()
    const onDone = vi.fn()

    const handle = api.runWrite('请登记伏笔', {
      instructions: '先核实再写入',
      onApproval,
      onDelta,
      onRun,
      onDone,
    })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/ai/runs?work=book_a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: '请登记伏笔', instructions: '先核实再写入' }),
    })
    expect(onRun).toHaveBeenCalledWith({ run_id: 'run_42' })
    expect(instance.url).toBe('/api/ai/runs/run_42/events?work=book_a')

    instance.onmessage({ data: JSON.stringify({ delta: '已核实' }) })
    instance.onmessage({ data: JSON.stringify({ approval: { run_id: 'run_42', approval_id: 'ap_1', message: '允许?' } }) })
    instance.onmessage({ data: JSON.stringify({ done: true }) })

    expect(onDelta).toHaveBeenCalledWith('已核实')
    expect(onApproval).toHaveBeenCalledWith({ run_id: 'run_42', approval_id: 'ap_1', message: '允许?' })
    expect(onDone).toHaveBeenCalled()

    handle.abort()
    expect(close).toHaveBeenCalled()
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/ai/runs/run_42/stop?work=book_a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: undefined,
    })
  })

  it('chatStream 把 tool_output SSE 交给回调', () => {
    let instance = null
    vi.stubGlobal('EventSource', class {
      constructor(url) {
        this.url = url
        this.close = vi.fn()
        instance = this
      }
    })
    const onToolOutput = vi.fn()

    api.chatStream('查资料', {
      onDelta: vi.fn(),
      onToolOutput,
      onDone: vi.fn(),
      onError: vi.fn(),
    })
    instance.onmessage({ data: JSON.stringify({ tool_output: '工具结果', tool_call_id: 'call_2' }) })

    expect(onToolOutput).toHaveBeenCalledWith('工具结果', 'call_2')
  })
})

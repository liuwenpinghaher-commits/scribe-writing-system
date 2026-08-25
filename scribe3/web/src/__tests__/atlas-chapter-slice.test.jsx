import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AtlasView } from '../views/AtlasView'

// 章切片:默认全书(不传 chapter);选中截至第 N 章后 ego 请求带 chapter=N。

const apiMock = vi.hoisted(() => ({
  graph: vi.fn(),
  chapters: vi.fn(),
}))

const sigmaMock = vi.hoisted(() => ({
  currentGraph: null,
  events: null,
}))

vi.mock('../api', () => ({ api: apiMock }))

vi.mock('@react-sigma/core', () => ({
  SigmaContainer: ({ children }) => <div data-testid="sigma-container">{children}</div>,
  useLoadGraph: () => (graph) => { sigmaMock.currentGraph = graph },
  useRegisterEvents: () => (events) => { sigmaMock.events = events },
  useSigma: () => ({
    getGraph: () => sigmaMock.currentGraph,
    getCamera: () => ({ animatedReset: vi.fn() }),
    graphToViewport: () => ({ x: 0, y: 0 }),
  }),
}))

const graphPayload = {
  nodes: [
    { id: 'role:小翠', type: 'character', label: '小翠' },
    { id: 'fact:井底有骨', type: 'proposition', label: '井底有骨' },
  ],
  edges: [{ src: 'role:小翠', dst: 'fact:井底有骨', rel: 'knows' }],
}

describe('AtlasView 章切片', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    sigmaMock.currentGraph = null
    sigmaMock.events = null
    apiMock.graph.mockResolvedValue(graphPayload)
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 3 }, { seq: 5 }])
  })

  it('挂载时消费 s3.atlas.focus 作为 ego 中心并清除 session', async () => {
    sessionStorage.setItem('s3.atlas.focus', 'role:小翠')
    render(<AtlasView onNavigateToObject={vi.fn()} />)

    await waitFor(() => {
      const egoCalls = apiMock.graph.mock.calls.filter(
        ([opts]) => opts && opts.focus === 'role:小翠',
      )
      expect(egoCalls.length).toBeGreaterThan(0)
    })
    expect(sessionStorage.getItem('s3.atlas.focus')).toBeNull()
  })

  it('可消费 fact: 命题焦点', async () => {
    sessionStorage.setItem('s3.atlas.focus', 'fact:井底有骨')
    render(<AtlasView onNavigateToObject={vi.fn()} />)
    await waitFor(() => {
      expect(apiMock.graph.mock.calls.some(([o]) => o?.focus === 'fact:井底有骨')).toBe(true)
    })
    expect(sessionStorage.getItem('s3.atlas.focus')).toBeNull()
  })

  it('传入 chapter 时首个 ego 请求带该章', async () => {
    render(<AtlasView chapter={3} onNavigateToObject={vi.fn()} />)
    await waitFor(() => {
      expect(apiMock.graph.mock.calls.some(([o]) => o?.focus && o?.chapter === 3)).toBe(true)
    })
    expect(screen.getByLabelText('章切片')).toHaveValue('3')
  })

  it('默认全书:ego 请求不带 chapter', async () => {
    render(<AtlasView onNavigateToObject={vi.fn()} />)

    await waitFor(() => {
      const egoCalls = apiMock.graph.mock.calls.filter(
        ([opts]) => opts && typeof opts === 'object' && opts.focus,
      )
      expect(egoCalls.length).toBeGreaterThan(0)
    })

    const egoCalls = apiMock.graph.mock.calls.filter(
      ([opts]) => opts && typeof opts === 'object' && opts.focus,
    )
    for (const [opts] of egoCalls) {
      expect(opts).not.toHaveProperty('chapter')
      // 即使有 chapter 键,值也应为 null/undefined(全书)
      expect(opts.chapter == null).toBe(true)
    }
  })

  it('切换截至第 3 章后 ego 请求带 chapter=3', async () => {
    render(<AtlasView onNavigateToObject={vi.fn()} />)

    const slice = await screen.findByLabelText('章切片')
    fireEvent.change(slice, { target: { value: '3' } })

    await waitFor(() => {
      const withCh = apiMock.graph.mock.calls.filter(
        ([opts]) => opts && opts.focus && opts.chapter === 3,
      )
      expect(withCh.length).toBeGreaterThan(0)
    })

    expect(slice).toHaveValue('3')
  })

  it('默认列表可读：无画布也能选中并看到下一笔', async () => {
    render(<AtlasView onNavigateToObject={vi.fn()} />)
    expect(await screen.findByRole('region', { name: '图谱对象列表' })).toBeTruthy()
    expect(screen.queryByTestId('atlas-canvas')).toBeNull()
    expect(await screen.findByTestId('atlas-node-detail')).toBeTruthy()
    expect(screen.getByTestId('atlas-next-stroke')).toBeTruthy()
    expect(screen.getByText('谁知道什么')).toBeTruthy()
  })

  it('从切片切回全书后 ego 请求不再带 chapter', async () => {
    render(<AtlasView onNavigateToObject={vi.fn()} />)

    const slice = await screen.findByLabelText('章切片')
    fireEvent.change(slice, { target: { value: '3' } })
    await waitFor(() => {
      expect(apiMock.graph.mock.calls.some(([o]) => o?.chapter === 3)).toBe(true)
    })

    fireEvent.change(slice, { target: { value: '' } })

    await waitFor(() => {
      const lastEgo = [...apiMock.graph.mock.calls]
        .reverse()
        .find(([opts]) => opts && opts.focus)
      expect(lastEgo).toBeTruthy()
      expect(lastEgo[0].chapter == null).toBe(true)
    })
  })
})

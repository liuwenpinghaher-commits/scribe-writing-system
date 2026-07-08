import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { FramePanel } from '../FramePanel'
import { SelectionProvider, useSelection } from '../selectionContext'

const apiMock = vi.hoisted(() => ({
  frame: vi.fn(),
  irony: vi.fn(),
  intent: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

function FocusProbe() {
  const { focus } = useSelection()
  return <output data-testid="focus-label">{focus?.label || ''}</output>
}

function renderFrame(props = {}) {
  return render(
    <SelectionProvider>
      <FramePanel
        focalizer="role:小翠"
        chapter={3}
        focalizerOptions={[
          { id: 'role:小翠', name: '小翠' },
          { id: 'role:柳怀玉', name: '柳怀玉' },
        ]}
        {...props}
      />
      <FocusProbe />
    </SelectionProvider>,
  )
}

describe('FramePanel 限知帧决策面板', () => {
  beforeEach(() => {
    apiMock.frame.mockResolvedValue([
      { id: 'f1', entity: '柳怀玉', attribute: '知道', value: '借命契存在', chapter: 1 },
      { id: 'f2', entity: '柳怀玉', attribute: '秘密', value: null, chapter: 2 },
    ])
    apiMock.irony.mockResolvedValue([
      { id: 'i1', entity: '读者', attribute: '真相', value: '续命者为空', chapter: 1 },
    ])
    apiMock.intent.mockResolvedValue({})
  })

  it('以二栏上下文树和详情栏展示可写/禁写/反讽/来源', async () => {
    renderFrame()

    await waitFor(() => expect(screen.getByRole('navigation', { name: '限知帧上下文树' })).toBeTruthy())
    expect(screen.getByRole('region', { name: '限知帧详情' })).toBeTruthy()
    expect(screen.getByText('可写事实总览')).toBeTruthy()

    expect(screen.getByRole('button', { name: /可写事实 1/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /禁止泄露 1/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /戏剧反讽 1/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /来源账本 3/ })).toBeTruthy()

    expect(screen.getByText(/借命契存在/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /禁止泄露 1/ }))
    expect(screen.getByText('禁止泄露总览')).toBeTruthy()
    expect(screen.getByText(/柳怀玉 · 秘密/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /柳怀玉 · 秘密/ }))
    const detail = screen.getByRole('region', { name: '限知帧详情' })
    expect(within(detail).getByText('事实详情')).toBeTruthy()
    expect(within(detail).getByText('私密/未知')).toBeTruthy()
    expect(screen.getByTestId('focus-label').textContent).toContain('柳怀玉·秘密')

    fireEvent.click(screen.getByRole('button', { name: /戏剧反讽 1/ }))
    expect(screen.getByText('戏剧反讽总览')).toBeTruthy()
    expect(screen.getByText(/续命者为空/)).toBeTruthy()
  })

  it('按 demo 渲染向右延展的三列上下文画布和完整详情返回', async () => {
    renderFrame()

    await waitFor(() => expect(screen.getByRole('region', { name: '限知帧画布' })).toBeTruthy())
    expect(screen.getByText('分组')).toBeTruthy()
    expect(screen.getByText('当前分类')).toBeTruthy()
    expect(screen.getByText('就地详情')).toBeTruthy()
    expect(screen.getByRole('button', { name: '向右延展' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '向下压缩' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /禁止泄露 1/ }))
    fireEvent.click(screen.getByRole('button', { name: /柳怀玉 · 秘密/ }))
    const detail = screen.getByRole('article', { name: '事实详情' })
    expect(within(detail).getByText('为什么禁写')).toBeTruthy()
    expect(within(detail).getByText('可写替代')).toBeTruthy()
    expect(within(detail).getByText('关联跳转')).toBeTruthy()

    fireEvent.click(within(detail).getByRole('button', { name: '打开完整详情' }))
    expect(screen.getByRole('region', { name: '完整限知详情' })).toBeTruthy()
    expect(screen.getByText('返回机制')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '返回上下文树' }))
    expect(screen.getByRole('region', { name: '限知帧画布' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: '完整限知详情' })).toBeNull()
  })

  it('切换视角时重新读取该角色的限知树', async () => {
    apiMock.frame.mockImplementation((focalizer) => Promise.resolve(
      focalizer === 'role:柳怀玉'
        ? [{ id: 'f3', entity: '柳怀玉', attribute: '确信', value: '自己安全', chapter: 3 }]
        : [{ id: 'f1', entity: '小翠', attribute: '知道', value: '借命契存在', chapter: 1 }],
    ))
    apiMock.irony.mockResolvedValue([])

    renderFrame()

    await waitFor(() => expect(apiMock.frame).toHaveBeenCalledWith('role:小翠', 3))
    fireEvent.click(screen.getByRole('button', { name: /小翠 · 知道/ }))
    expect(screen.getByTestId('focus-label').textContent).toContain('小翠·知道')

    fireEvent.change(screen.getByLabelText('限知视角'), { target: { value: 'role:柳怀玉' } })

    await waitFor(() => expect(apiMock.frame).toHaveBeenLastCalledWith('role:柳怀玉', 3))
    expect(screen.getByTestId('focus-label').textContent).toBe('')
    expect(screen.getByText(/自己安全/)).toBeTruthy()
  })
})

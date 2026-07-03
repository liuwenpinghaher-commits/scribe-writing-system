// 块三必修1单测:一次性 suppress 标记——「聚焦+跳章」复合动作只吞掉紧随的那一次 sel 镜像,
// 之后任何 sel 变化(含 300ms 内快速连点)正常镜像,意图不丢。
import { describe, it, expect } from 'vitest'
import { render, act } from '@testing-library/react'
import { SelectionProvider, SelMirror, useSelection, consumeSuppress } from '../selectionContext.jsx'

describe('consumeSuppress(纯逻辑)', () => {
  it('置位只消费一次:第一次 true 并复位,第二次 false', () => {
    const ref = { current: true }
    expect(consumeSuppress(ref)).toBe(true)
    expect(ref.current).toBe(false)
    expect(consumeSuppress(ref)).toBe(false)
  })
  it('未置位不消费', () => {
    const ref = { current: false }
    expect(consumeSuppress(ref)).toBe(false)
  })
})

// 探针:把 context API 抓到外部 holder,供测试驱动 setFocus/suppressNextMirror 并读 focus。
function Probe({ hold }) {
  const api = useSelection()
  hold.api = api
  return <span data-testid="focus">{api.focus ? `${api.focus.origin}:${api.focus.type}:${api.focus.label}` : 'null'}</span>
}

const selNode = (type, id, label) => ({ mode: 'node', node: { id, type, ref: id, label } })

describe('SelMirror × suppress 标记(集成)', () => {
  it('聚焦+跳章:跳章那次 sel 变化被吞;紧接着(无等待)再点树节点正常镜像', () => {
    const hold = {}
    const ui = (sel) => (
      <SelectionProvider>
        <SelMirror sel={sel} />
        <Probe hold={hold} />
      </SelectionProvider>
    )
    const selA = selNode('chapter', 'ch:4', '4 第4章')
    const { rerender, getByTestId } = render(ui(selA))
    expect(getByTestId('focus').textContent).toBe('sel:chapter:4 第4章')

    // 复合动作:显式聚焦伏笔 + 置 suppress + 跳章(sel → ch:1)
    act(() => {
      hold.api.setFocus({ type: 'promise', id: 'p1', label: '借命契', origin: 'panel' })
      hold.api.suppressNextMirror()
    })
    act(() => { rerender(ui(selNode('chapter', 'ch:1', '1 第1章'))) })
    expect(getByTestId('focus').textContent).toBe('panel:promise:借命契')   // 跳章不冲掉伏笔聚焦

    // 立刻(同 tick,无任何时间窗)再点项目树角色 → 正常镜像,意图不丢
    act(() => { rerender(ui(selNode('character', 'character:崔判', '崔判'))) })
    expect(getByTestId('focus').textContent).toBe('sel:character:崔判')
  })

  it('无 suppress 的普通 sel 变化始终镜像(不误吞)', () => {
    const hold = {}
    const ui = (sel) => (
      <SelectionProvider>
        <SelMirror sel={sel} />
        <Probe hold={hold} />
      </SelectionProvider>
    )
    const { rerender, getByTestId } = render(ui(selNode('chapter', 'ch:4', '4 第4章')))
    act(() => { rerender(ui(selNode('chapter', 'ch:2', '2 第2章'))) })
    expect(getByTestId('focus').textContent).toBe('sel:chapter:2 第2章')
    act(() => { rerender(ui(selNode('chapter', 'ch:3', '3 第3章'))) })
    expect(getByTestId('focus').textContent).toBe('sel:chapter:3 第3章')
  })
})

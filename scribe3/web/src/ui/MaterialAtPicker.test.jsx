import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MaterialAtPicker } from './MaterialAtPicker.jsx'

describe('MaterialAtPicker', () => {
  it('renders multi-domain options and picks on click', () => {
    const onPick = vi.fn()
    render(
      <MaterialAtPicker
        open
        query="崔"
        items={[
          { key: 'ch:1', domain: 'chapter', type: 'chapter', title: '1 开篇', refToken: 'ch:1' },
          { key: 'character:崔判', domain: 'codex', type: 'character', title: '崔判', refToken: 'character:崔判' },
          { key: 'material:m1', domain: 'material', type: 'material', title: '霜白城墙', kind: 'snippet', refToken: 'material:m1', subtitle: '会话摘录' },
        ]}
        activeIndex={0}
        onActiveIndexChange={() => {}}
        onPick={onPick}
      />,
    )
    expect(screen.getByTestId('material-at-picker').textContent).toMatch(/全书对象|章\/视图/)
    expect(screen.getAllByTestId('material-at-option')).toHaveLength(3)
    fireEvent.mouseDown(screen.getByText('崔判'))
    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({
      domain: 'codex', refToken: 'character:崔判',
    }))
  })

  it('hidden when closed', () => {
    const { container } = render(<MaterialAtPicker open={false} items={[]} />)
    expect(container.querySelector('[data-testid="material-at-picker"]')).toBeNull()
  })
})

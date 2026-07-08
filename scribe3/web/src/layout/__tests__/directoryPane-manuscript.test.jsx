import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DirectoryPane } from '../DirectoryPane'

vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node }) => <div data-testid="legacy-container-outline">{node.id}</div>,
}))
vi.mock('../../Materials', () => ({
  MaterialList: () => <div data-testid="material-list" />,
}))

const manuscript = {
  id: 'manuscript_root',
  type: 'manuscript_root',
  label: '手稿',
  children: [
    {
      id: 'vol:1',
      type: 'volume',
      label: '第一卷',
      children: [
        { id: 'ch:1', type: 'chapter', ref: 1, label: '第 1 章 入城' },
        {
          id: 'ch:2',
          type: 'chapter',
          ref: 2,
          label: '第 2 章 借命契',
          children: [
            { id: 'scene:2:1', type: 'scene', ref: { seq: 2, idx: 1 }, label: '场景 1 炉灰' },
          ],
        },
      ],
    },
  ],
}

const entry = { id: 'entry:manuscript', type: 'entry_capability', capability: 'manuscript', label: '手稿', source: manuscript }

describe('DirectoryPane 手稿目录', () => {
  it('在卷章目录上方渲染 sticky 当前选择区', () => {
    render(<DirectoryPane entry={entry} seq={2} sel={{ node: { type: 'chapter', ref: 2 } }} onSelectItem={() => {}} />)

    expect(screen.getByTestId('directory-sticky-header').textContent).toContain('当前')
    expect(screen.getByText('书级工具')).toBeTruthy()
    expect(screen.getByRole('button', { name: /第一卷/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /第 2 章/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /场景 1 炉灰/ })).toBeTruthy()
  })

  it('点击章只传出章节节点,并保留目录头', () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry} seq={2} onSelectItem={onSelectItem} />)

    fireEvent.click(screen.getByRole('button', { name: /第 1 章/ }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:1',
      type: 'chapter',
      ref: 1,
    }))
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
  })
})

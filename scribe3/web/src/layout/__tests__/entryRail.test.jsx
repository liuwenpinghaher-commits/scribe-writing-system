import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EntryRail } from '../EntryRail'

const tree = {
  manuscript: { id: 'manuscript_root', type: 'manuscript_root', label: '旧项目树' },
  codex: { id: 'codex_root', type: 'codex_root', label: '设定库' },
  materials: { id: 'material_root', type: 'material_root', label: '素材库' },
}

describe('EntryRail', () => {
  it('渲染完整左栏能力入口,并把项目改为手稿', () => {
    render(<EntryRail tree={tree} activeId="entry:manuscript" onEntry={() => {}} />)

    for (const label of ['手稿', '设定', '素材', '演绎', '伏笔', '母题', '搜索']) {
      expect(screen.getByRole('button', { name: new RegExp(label) })).toBeTruthy()
    }
    expect(screen.queryByRole('button', { name: /校验/ })).toBeNull()
    expect(screen.queryByText('项目')).toBeNull()
  })

  it('点击能力时传出 entry_capability 节点', () => {
    const onEntry = vi.fn()
    render(<EntryRail tree={tree} activeId={null} onEntry={onEntry} />)

    fireEvent.click(screen.getByRole('button', { name: /演绎/ }))

    expect(onEntry).toHaveBeenCalledWith(expect.objectContaining({
      id: 'entry:deduce',
      type: 'entry_capability',
      capability: 'deduce',
      label: '演绎',
    }))
  })
})

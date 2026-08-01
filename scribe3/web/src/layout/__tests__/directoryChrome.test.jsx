import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DirectoryHeader } from '../DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_ROW_ACTIVE } from '../DirectoryRow'
import { CapabilityDirectory } from '../CapabilityDirectories'
import { ManuscriptDirectory } from '../ManuscriptDirectory'
import { CodexDirectory } from '../CodexDirectory'
import { SearchDirectory } from '../../capabilities/search/SearchDirectory'
import { IssueDirectory } from '../../capabilities/issues/IssueDirectory'
import { MaterialList } from '../../Materials'

vi.mock('../../hooks/useIssueLedger', () => ({
  useIssueLedger: () => ({
    loading: false,
    err: '',
    issues: [
      { id: 'iss-1', title: 'POV 泄露', severity: 'error', chapter: 2, source: 'qc' },
    ],
    degraded: [],
    reload: vi.fn(),
  }),
}))

vi.mock('../../api', () => ({
  api: {
    search: vi.fn(),
    listUnverified: vi.fn(() => Promise.resolve([])),
    materials: vi.fn(() => Promise.resolve([
      { id: 1, title: 'A', kind: 'note', tags: [], pinned: false, recall_count: 0 },
    ])),
    materialRecall: vi.fn(() => Promise.resolve([])),
    chapters: vi.fn(() => Promise.resolve([{ seq: 9, title: '实时章' }])),
  },
}))

// 避免 MaterialList 侧车导入 MaterialNetwork → sigma/WebGL 在 jsdom 崩
vi.mock('../../MaterialImport', () => ({ MaterialImport: () => null }))
vi.mock('../../MaterialNetwork', () => ({ MaterialNetwork: () => null }))
vi.mock('../../editor/RichEditor', () => ({
  RichEditor: () => null,
  useUnsavedGuard: vi.fn(),
}))

describe('Directory chrome contract', () => {
  it('DirectoryHeader exposes directory-sticky-header and optional search only with handler', () => {
    const { rerender } = render(<DirectoryHeader title="手稿" count={3} />)
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    expect(screen.getByText('手稿')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.queryByRole('searchbox')).toBeNull()

    rerender(
      <DirectoryHeader title="搜索" query="a" onQueryChange={() => {}} searchLabel="全局搜索" />,
    )
    expect(screen.getByRole('searchbox', { name: '全局搜索' })).toBeTruthy()
  })

  it('DirectoryHeader action buttons default to type=button (safe inside forms)', () => {
    render(
      <form onSubmit={(e) => e.preventDefault()}>
        <DirectoryHeader
          title="搜索"
          query="q"
          onQueryChange={() => {}}
          searchLabel="全局搜索"
          primaryAction={{ label: '搜索', onClick: () => {} }}
          secondaryActions={[{ label: '语义召回', onClick: () => {} }]}
        />
      </form>,
    )
    expect(screen.getByRole('button', { name: '搜索' }).getAttribute('type')).toBe('button')
    expect(screen.getByRole('button', { name: '语义召回' }).getAttribute('type')).toBe('button')
  })

  it('DirectoryHeader stacks search above actions; action labels stay nowrap (no CJK vertical wrap)', () => {
    render(
      <DirectoryHeader
        title="素材库"
        count={0}
        query=""
        onQueryChange={() => {}}
        searchLabel="搜索素材"
        primaryAction={{ label: '新建', onClick: () => {} }}
        secondaryActions={[
          { label: '导入', onClick: () => {} },
          { label: '网络', onClick: () => {} },
        ]}
      />,
    )
    const header = screen.getByTestId('directory-sticky-header')
    const search = screen.getByRole('searchbox', { name: '搜索素材' })
    const actions = screen.getByTestId('directory-header-actions')
    // 搜索与动作分块：动作容器不含 search，搜索为 full-width 输入
    expect(actions.contains(search)).toBe(false)
    expect(search.className).toMatch(/w-full/)
    for (const name of ['导入', '网络', '新建']) {
      const btn = within(actions).getByRole('button', { name })
      expect(btn.className).toMatch(/whitespace-nowrap/)
      expect(btn.className).toMatch(/shrink-0/)
    }
    expect(within(header).getByText('素材库')).toBeTruthy()
  })

  it('DirectoryRow is dense title+meta with single active class family', () => {
    const onClick = vi.fn()
    render(<DirectoryRow title="第 1 章 入城" meta="草稿" active onClick={onClick} />)
    const row = screen.getByRole('button', { name: '第 1 章 入城' })
    expect(row.textContent).toMatch(/第 1 章 入城/)
    expect(row.textContent).toMatch(/草稿/)
    expect(row.className).toContain(DIR_ROW_ACTIVE.split(' ')[0])
    expect(row.className).not.toMatch(/border-line/)
    expect(row.className).not.toContain('panel-elevated')
    fireEvent.click(row)
    expect(onClick).toHaveBeenCalled()
  })

  it('CapabilityDirectory has no bordered card wall on groups', () => {
    const { container } = render(
      <CapabilityDirectory capability="promise" seq={3} onSelectItem={vi.fn()} />,
    )
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    // group headers are rows, not border border-line cards
    const groupButtons = container.querySelectorAll('button')
    for (const b of groupButtons) {
      if (b.className.includes('border-line') && b.className.includes('border ')) {
        // allow only left accent if any; full card walls fail
        expect(b.className).not.toMatch(/border border-line bg-surface/)
      }
    }
    expect(container.innerHTML).not.toContain('panel-elevated')
  })
})

describe('Directory surfaces row density', () => {
  const manuscript = {
    id: 'manuscript_root',
    type: 'manuscript_root',
    label: '手稿',
    children: [
      {
        id: 'vol:1',
        type: 'volume',
        ref: '1',
        label: '第一卷',
        children: [{ id: 'ch:1', type: 'chapter', ref: 1, label: '第 1 章 入城', phase: 'draft' }],
      },
    ],
  }

  it('ManuscriptDirectory: header + volume/chapter title+meta', () => {
    render(
      <ManuscriptDirectory
        entry={{ capability: 'manuscript', source: manuscript, label: '手稿' }}
        sel={{ node: { type: 'chapter', ref: 1 } }}
        seq={1}
        onSelectItem={vi.fn()}
      />,
    )
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    expect(screen.getByText('手稿')).toBeTruthy()
    expect(screen.getByRole('button', { name: /第一卷/ })).toBeTruthy()
    const ch = screen.getByRole('button', { name: /第 1 章 入城/ })
    expect(ch.textContent).toMatch(/第 1 章 入城/)
  })

  it('ManuscriptDirectory 会补入打开作品后由主编新增的实时章节', async () => {
    render(
      <ManuscriptDirectory
        entry={{ capability: 'manuscript', source: { id: 'manuscript_root', children: [] }, label: '手稿' }}
        sel={{ node: { type: 'manuscript_root' } }}
        onSelectItem={vi.fn()}
      />,
    )
    expect(await screen.findByRole('button', { name: /第 9 章 实时章/ })).toBeTruthy()
  })

  it('CodexDirectory: sticky header and category title without mandatory dual-line essay as only scan', () => {
    const root = {
      id: 'codex_root',
      type: 'codex_root',
      label: '设定库',
      children: [
        {
          id: 'cat:character',
          type: 'codex_category',
          ref: 'character',
          label: '角色',
          children: [{ id: 'character:甲', type: 'character', ref: '甲', label: '甲' }],
        },
      ],
    }
    render(<CodexDirectory root={root} selected={null} onSelectItem={vi.fn()} />)
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    const cat = screen.getByRole('button', { name: '角色' })
    expect(cat.textContent).toMatch(/角色/)
    // count meta present; long desc not required as always-on primary essay
    expect(cat.textContent).toMatch(/1/)
  })

  it('SearchDirectory uses shared header testid', () => {
    render(<SearchDirectory onSelectItem={vi.fn()} />)
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    expect(screen.getByRole('searchbox', { name: /搜索|全局/ })).toBeTruthy()
  })

  it('IssueDirectory row is title + meta', () => {
    render(<IssueDirectory seq={2} onSelectItem={vi.fn()} />)
    expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
    const row = screen.getByRole('button', { name: /POV 泄露/ })
    expect(row.textContent).toMatch(/POV 泄露/)
    expect(row.textContent).toMatch(/第 2 章|qc/)
  })
})

describe('DirectorySectionLabel', () => {
  it('renders section label without card chrome', () => {
    render(<DirectorySectionLabel>分类</DirectorySectionLabel>)
    expect(screen.getByText('分类').className).not.toMatch(/border-line/)
  })
})

describe('Materials list-first chrome', () => {
  it('MaterialList uses shared sticky header and chip filters not 2x2 grid wall', async () => {
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)
    await waitFor(() => expect(screen.getByTestId('directory-sticky-header')).toBeTruthy())
    const chips = screen.getByTestId('material-smart-views')
    expect(chips.className).toMatch(/flex/)
    expect(chips.className).not.toMatch(/grid-cols-2/)
    expect(screen.getByTestId('material-item-list')).toBeTruthy()
  })
})

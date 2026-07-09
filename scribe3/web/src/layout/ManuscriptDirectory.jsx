import { DirectoryHeader } from './DirectoryHeader'

const BOOK_TOOLS = [
  { id: 'book:outline', type: 'book_outline', ref: null, label: '全书大纲', marker: '纲' },
  { id: 'book:northstar', type: 'book_northstar', ref: null, label: '北极星', marker: '星' },
  { id: 'view:progress', type: 'view', ref: 'progress', label: '进度', marker: '度' },
]

export function chapterNodeFrom(row) {
  if (row?.type === 'scene') {
    return { id: row.id, type: 'scene', ref: row.ref, label: row.label }
  }
  const seq = row?.ref ?? row?.seq
  return {
    id: `ch:${seq}`,
    type: 'chapter',
    ref: seq,
    label: row?.label || `${seq}`,
    phase: 'outline',
  }
}

function currentSeqOf(sel, seq) {
  const node = sel?.node
  if (node?.type === 'scene') return node.ref?.seq ?? seq
  if (node?.type === 'chapter') return node.ref ?? seq
  return seq
}

function collectRows(node, depth = 0, rows = []) {
  for (const child of node?.children || []) {
    if (child.type === 'volume') {
      rows.push({ kind: 'volume', node: child, depth })
      collectRows(child, depth + 1, rows)
    } else if (child.type === 'chapter') {
      rows.push({ kind: 'chapter', node: child, depth })
      collectRows(child, depth + 1, rows)
    } else if (child.type === 'scene') {
      rows.push({ kind: 'scene', node: child, depth })
    }
  }
  return rows
}

function chapterCount(node) {
  return (node?.children || []).reduce((sum, child) => (
    sum + (child.type === 'chapter' ? 1 : chapterCount(child))
  ), 0)
}

function rowMeta(row) {
  if (row.kind === 'volume') return `${chapterCount(row.node)}章`
  if (row.kind === 'scene') return '场景'
  return row.node.phase || ''
}

function BookTools({ onSelectItem }) {
  return (
    <div data-testid="manuscript-book-tools">
      <div className="px-1 py-1 text-f10 font-semibold uppercase tracking-wider text-faint/60">书级</div>
      <div className="grid gap-0.5">
        {BOOK_TOOLS.map((tool) => (
          <button
            key={tool.id}
            type="button"
            aria-label={tool.label}
            onClick={() => {
              const { marker, ...node } = tool
              onSelectItem?.(node)
            }}
            className="grid min-h-8 w-full grid-cols-[18px_1fr_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-f12 text-faint hover:bg-hover hover:text-ink"
          >
            <span aria-hidden="true" className="grid h-5 w-5 place-items-center rounded bg-brand/10 text-f10 font-semibold text-brand">{tool.marker}</span>
            <span className="min-w-0 truncate">{tool.label}</span>
            <span aria-hidden="true" className="text-f10 text-faint">书</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export function ManuscriptDirectory({ entry, sel, seq, onSelectItem, onJumpChapter }) {
  const root = entry?.source || entry
  const rows = collectRows(root)
  const currentSeq = currentSeqOf(sel, seq)
  const currentRow = rows.find((row) => row.kind === 'chapter' && row.node.ref === currentSeq)
  const currentLabel = currentRow?.node?.label || (currentSeq != null ? `第 ${currentSeq} 章` : '')

  return (
    <div data-testid="manuscript-directory" className="h-full min-h-0 flex flex-col">
      <DirectoryHeader
        title="手稿"
        badge={currentSeq != null ? `第 ${currentSeq} 章` : '卷章'}
        current={currentLabel}
        subtitle="卷 / 章 / 场景目录"
        currentCardTestId="manuscript-current-card"
        inputPlaceholder="跳章 / 过滤"
        secondaryAction="上一章"
        primaryAction="同步"
        chips={['当前卷', '未完成', '含伏笔', '含母题']}
        onSecondary={() => {
          if (currentSeq != null) onJumpChapter?.(Math.max(1, currentSeq - 1))
        }}
        onPrimary={() => {
          if (currentSeq != null) onSelectItem?.(chapterNodeFrom({ type: 'chapter', ref: currentSeq, label: currentLabel }))
        }}
      />
      <div data-testid="manuscript-volume-list" className="flex-1 min-h-0 overflow-auto px-2 py-2">
        <BookTools onSelectItem={onSelectItem} />
        <div className="mt-3 px-1 py-1 text-f10 font-semibold uppercase tracking-wider text-faint/60">卷章</div>
        {rows.length === 0 ? (
          <div className="px-2 py-6 text-center text-f12 text-faint/60">暂无章节。</div>
        ) : rows.map((row) => {
          const active = row.kind === 'chapter' && row.node.ref === currentSeq
          const disabled = row.kind === 'volume'
          const marker = row.kind === 'volume' ? '▾' : row.kind === 'scene' ? '·' : ''
          return (
            <button
              key={row.node.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectItem?.(chapterNodeFrom(row.node))}
              className={`my-0.5 grid min-h-8 w-full grid-cols-[18px_1fr_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-f12 ${
                active ? 'bg-brand/10 text-brand font-semibold' : 'text-ink hover:bg-hover'
              } ${disabled ? 'cursor-default text-faint hover:bg-transparent' : ''}`}
              style={{ paddingLeft: `${8 + row.depth * 16}px` }}
            >
              <span className="w-5 text-center text-faint">{marker}</span>
              <span className="min-w-0 truncate">{row.node.label}</span>
              <span className="text-f10 text-faint">{rowMeta(row)}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

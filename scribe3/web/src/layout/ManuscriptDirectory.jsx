import { useCallback, useState } from 'react'
import { api } from '../api'
import { ConfirmDialog } from '../ui/Dialog'
import { showToast } from '../ui/Toast'

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

function volumeNodeFrom(row) {
  return {
    id: row?.id || `vol:${row?.ref ?? ''}`,
    type: 'volume',
    ref: row?.ref ?? null,
    label: row?.label || '未命名卷',
    children: row?.children || [],
  }
}

function manuscriptNodeFrom(row) {
  if (row?.kind === 'volume') return volumeNodeFrom(row.node)
  return chapterNodeFrom(row.node)
}

function currentSeqOf(sel, seq) {
  const node = sel?.node
  if (node?.type === 'volume') return null
  if (node?.type === 'scene') return node.ref?.seq ?? seq
  if (node?.type === 'chapter') return node.ref ?? seq
  return seq
}

function currentVolumeOf(sel, rows) {
  const node = sel?.node
  if (node?.type !== 'volume') return null
  return rows.find((row) => row.kind === 'volume' && String(row.node.ref ?? '') === String(node.ref ?? ''))?.node || node
}

function collectRows(node, depth = 0, rows = [], volume = null) {
  for (const child of node?.children || []) {
    if (child.type === 'volume') {
      rows.push({ kind: 'volume', node: child, depth, volume: child })
      collectRows(child, depth + 1, rows, child)
    } else if (child.type === 'chapter') {
      rows.push({ kind: 'chapter', node: child, depth, volume })
      collectRows(child, depth + 1, rows, volume)
    } else if (child.type === 'scene') {
      rows.push({ kind: 'scene', node: child, depth, volume })
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

function archivedChapterLabel(chapter) {
  const seq = chapter?.seq
  const title = String(chapter?.title || '').trim()
  if (!title) return `第 ${seq} 章`
  if (/^第\s*[\d一二三四五六七八九十百千万零〇两]+\s*章/.test(title)) return title
  return `第 ${seq} 章 ${title}`
}

function impactBody(impact) {
  const refs = impact?.references || []
  return (
    <div className="space-y-2">
      <div>永久删除后无法从归档箱恢复。确认前请核对影响清单。</div>
      {refs.length ? (
        <div className="flex flex-wrap gap-1.5">
          {refs.map((ref) => (
            <span key={`${ref.kind}:${ref.count}`} className="rounded bg-soft px-1.5 py-0.5">
              {ref.kind} {ref.count}
            </span>
          ))}
        </div>
      ) : (
        <div>未发现关联记录。</div>
      )}
    </div>
  )
}

function ArchiveBox({ onSelectItem, onArchivedChanged }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [pendingDelete, setPendingDelete] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.archivedChapters()
      setRows(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e?.body?.detail || e?.message || '读取归档箱失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const toggleOpen = async () => {
    const nextOpen = !open
    setOpen(nextOpen)
    if (nextOpen) await load()
  }

  const restoreChapter = async (chapter) => {
    try {
      await api.restoreChapter(chapter.seq)
      await load()
      onArchivedChanged?.()
      onSelectItem?.(chapterNodeFrom({ seq: chapter.seq, label: archivedChapterLabel(chapter) }))
      showToast('章节已恢复', { tone: 'ok' })
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '恢复章节失败', { tone: 'danger' })
    }
  }

  const askDelete = async (chapter) => {
    try {
      const impact = await api.chapterImpact(chapter.seq)
      setPendingDelete({ chapter, impact })
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '读取影响清单失败', { tone: 'danger' })
    }
  }

  const deletePermanent = async () => {
    const target = pendingDelete
    if (!target) return
    try {
      await api.deleteChapter(target.chapter.seq, target.impact?.confirm_impact_token || '')
      await load()
      onArchivedChanged?.()
      showToast('章节已永久删除', { tone: 'ok' })
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '永久删除失败', { tone: 'danger' })
    }
  }

  return (
    <div className="shrink-0 border-t border-line/60 px-2 py-2" data-testid="manuscript-archive-box">
      <button
        type="button"
        aria-expanded={open}
        data-testid="manuscript-archive-toggle"
        onClick={toggleOpen}
        className="grid min-h-8 w-full grid-cols-[18px_1fr_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-f12 text-faint hover:bg-hover hover:text-ink"
      >
        <span className="text-center">{open ? '▾' : '▸'}</span>
        <span className="min-w-0 truncate">归档箱</span>
        <span className="text-meta">{loading ? '读取中' : (open && rows.length ? `${rows.length}章` : '隐藏章节')}</span>
      </button>
      {open && (
        <div className="mt-1 space-y-1" data-testid="manuscript-archive-list">
          {error && <div className="px-2 py-2 text-f12 text-danger">{error}</div>}
          {!error && loading && <div className="px-2 py-2 text-f12 text-faint">正在读取归档章节...</div>}
          {!error && !loading && rows.length === 0 && (
            <div className="px-2 py-2 text-f12 text-faint/70">归档箱为空</div>
          )}
          {!error && rows.map((chapter) => {
            const label = archivedChapterLabel(chapter)
            return (
              <div key={chapter.seq} className="rounded-md px-2 py-2 hover:bg-hover">
                <div className="min-w-0">
                  <div className="truncate text-f12 text-ink">{label}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5 text-meta text-faint">
                    {chapter.archive_reason ? <span>{chapter.archive_reason}</span> : <span>无归档说明</span>}
                    {chapter.archived_at ? <span>{String(chapter.archived_at).slice(0, 10)}</span> : null}
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-1.5">
                  <button
                    type="button"
                    aria-label={`恢复${label}`}
                    onClick={() => restoreChapter(chapter)}
                    className="h-7 rounded-md bg-soft px-2 text-meta text-ink hover:bg-brand/10 hover:text-brand"
                  >
                    恢复
                  </button>
                  <button
                    type="button"
                    aria-label={`永久删除${label}`}
                    onClick={() => askDelete(chapter)}
                    className="h-7 rounded-md px-2 text-meta text-danger hover:bg-danger/10"
                  >
                    永久删除
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
      <ConfirmDialog
        open={!!pendingDelete}
        title={`永久删除${pendingDelete ? archivedChapterLabel(pendingDelete.chapter) : ''}`}
        body={pendingDelete ? impactBody(pendingDelete.impact) : null}
        danger
        confirmText="永久删除"
        onConfirm={deletePermanent}
        onClose={() => setPendingDelete(null)}
      />
    </div>
  )
}

export function ManuscriptDirectory({ entry, sel, seq, onSelectItem, onCreateChapter, onArchivedChanged }) {
  const root = entry?.source || entry
  const rows = collectRows(root)
  const currentSeq = currentSeqOf(sel, seq)
  const currentVolume = currentVolumeOf(sel, rows)

  return (
    <div data-testid="manuscript-directory" className="h-full min-h-0 flex flex-col">
      <div data-testid="manuscript-volume-list" className="flex-1 min-h-0 overflow-auto px-2 py-2">
        <div className="px-1 py-1 text-meta font-semibold uppercase tracking-wider text-faint/60">卷章</div>
        {rows.length === 0 ? (
          <div className="px-2 py-6 text-center text-f12 text-faint/60">暂无章节。</div>
        ) : rows.map((row) => {
          const active = row.kind === 'volume'
            ? !!currentVolume && String(row.node.ref ?? '') === String(currentVolume.ref ?? '')
            : row.kind === 'chapter' && row.node.ref === currentSeq
          const marker = row.kind === 'volume' ? '▾' : row.kind === 'scene' ? '·' : ''
          const rowClass = `my-0.5 grid min-h-8 w-full grid-cols-[18px_1fr_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-f12 ${
            active ? 'bg-brand/10 text-brand font-semibold' : 'text-ink hover:bg-hover'
          } ${row.kind === 'volume' && !active ? 'text-faint' : ''}`
          if (row.kind === 'volume') {
            return (
              <div key={row.node.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-1">
                <button
                  type="button"
                  onClick={() => onSelectItem?.(manuscriptNodeFrom(row))}
                  className={rowClass}
                  style={{ paddingLeft: `${8 + row.depth * 16}px` }}
                >
                  <span className="w-5 text-center text-faint">{marker}</span>
                  <span className="min-w-0 truncate">{row.node.label}</span>
                  <span className="text-meta text-faint">{rowMeta(row)}</span>
                </button>
                <button
                  type="button"
                  aria-label={`在${row.node.label}中新建章`}
                  title="新建章"
                  onClick={(event) => {
                    event.stopPropagation()
                    onCreateChapter?.(row.node.ref ?? null)
                  }}
                  className="h-7 rounded-md border border-line bg-canvas px-2 text-meta text-faint hover:border-brand/40 hover:text-brand"
                >
                  +章
                </button>
              </div>
            )
          }
          return (
            <button
              key={row.node.id}
              type="button"
              onClick={() => onSelectItem?.(manuscriptNodeFrom(row))}
              className={rowClass}
              style={{ paddingLeft: `${8 + row.depth * 16}px` }}
            >
              <span className="w-5 text-center text-faint">{marker}</span>
              <span className="min-w-0 truncate">{row.node.label}</span>
              <span className="text-meta text-faint">{rowMeta(row)}</span>
            </button>
          )
        })}
      </div>
      <ArchiveBox onSelectItem={onSelectItem} onArchivedChanged={onArchivedChanged} />
    </div>
  )
}

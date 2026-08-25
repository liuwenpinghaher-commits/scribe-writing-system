import { List, Lock } from 'lucide-react'
import { groupAtlasNodes } from '../../lib/atlasReadable.js'

function Row({ n, pickedId, onPick, onOpen }) {
  const lab = n.listLabel
  const dot = n.type === 'character'
    ? 'var(--color-brand)'
    : n.secret ? 'var(--color-secret)' : 'var(--color-irony)'
  return (
    <li className="flex items-center gap-0.5">
      <button
        type="button"
        data-testid="atlas-list-pick"
        aria-label={`选中 ${lab}`}
        onClick={() => onPick?.({
          id: n.id,
          label: n.label || n.id,
          type: n.type,
          secret: !!n.secret,
        })}
        className={`flex-1 min-w-0 text-left px-2 py-1.5 rounded-lg text-f12 text-ink hover:bg-soft inline-flex items-center gap-1.5 transition-colors cursor-pointer ${pickedId === n.id ? 'bg-soft' : ''}`}
      >
        <i className="w-2 h-2 rounded-full shrink-0" style={{ background: dot }} />
        {n.secret && <Lock size={11} className="shrink-0 text-faint" />}
        <span className="truncate">{lab}</span>
      </button>
      <button
        type="button"
        data-testid="atlas-list-open-codex"
        aria-label={`打开设定 ${lab}`}
        onClick={() => onOpen?.(n)}
        className="shrink-0 px-1.5 py-1 text-meta text-faint hover:text-brand rounded cursor-pointer"
      >
        设定
      </button>
    </li>
  )
}

function Block({ title, nodes, pickedId, onPick, onOpen }) {
  if (!nodes.length) return null
  return (
    <div className="px-1 pb-2">
      <div className="px-2 pt-2 pb-1 text-meta text-faint">{title} · {nodes.length}</div>
      <ul>
        {nodes.map((n) => (
          <Row key={n.id} n={n} pickedId={pickedId} onPick={onPick} onOpen={onOpen} />
        ))}
      </ul>
    </div>
  )
}

export function AtlasNodeList({ nodes, pickedId, onPick, onOpen }) {
  const groups = groupAtlasNodes(nodes)
  const total = (nodes || []).length
  if (!total) return null
  return (
    <div
      role="region"
      aria-label="图谱对象列表"
      data-testid="atlas-node-list"
      className="w-72 shrink-0 border-r border-line/50 bg-surface overflow-y-auto"
    >
      <div className="sticky top-0 bg-surface/95 backdrop-blur px-3 py-2 border-b border-line/50 flex items-center gap-1.5 text-meta font-medium text-faint">
        <List size={12} />谁 · {total}
      </div>
      <Block title="人" nodes={groups.characters} pickedId={pickedId} onPick={onPick} onOpen={onOpen} />
      <Block title="知情" nodes={groups.propositions} pickedId={pickedId} onPick={onPick} onOpen={onOpen} />
      <Block title="其它" nodes={groups.others} pickedId={pickedId} onPick={onPick} onOpen={onOpen} />
    </div>
  )
}

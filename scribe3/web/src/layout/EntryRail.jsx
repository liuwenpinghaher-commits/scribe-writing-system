// 栏1 · 一级入口:手稿 / 设定 / 素材 + 工艺 / 检查能力,分组竖排。
// 与旧混合树的根本区别:点入口只切换第二栏目录,绝不像旧树那样 node.toggle() 就地展开
// (那正是"条目挤进第一栏"的病灶)。横切视图入口统一放在顶栏,不再挤进本栏。

function countOf(node) {
  const b = (node?.badges || []).find((x) => x.kind === 'count')
  return b?.value
}

const CAPABILITY_GROUPS = [
  { key: 'content', label: '内容', items: [
    { capability: 'manuscript', label: '手稿' },
    { capability: 'codex', label: '设定' },
    { capability: 'materials', label: '素材' },
  ] },
  { key: 'craft', label: '工艺', items: [
    { capability: 'deduce', label: '演绎' },
    { capability: 'promise', label: '伏笔' },
    { capability: 'motif', label: '母题' },
  ] },
  { key: 'check', label: '检查', items: [
    { capability: 'search', label: '搜索' },
    { capability: 'review', label: '校验' },
  ] },
]

function sourceFor(tree, capability) {
  if (capability === 'manuscript') return tree?.manuscript
  if (capability === 'codex') return tree?.codex
  if (capability === 'materials') return tree?.materials
  return null
}

function entryFor(tree, item) {
  const source = sourceFor(tree, item.capability)
  return {
    id: `entry:${item.capability}`,
    type: 'entry_capability',
    capability: item.capability,
    label: item.label,
    source,
  }
}

export function EntryRail({ tree, activeId, onEntry }) {
  return (
    <div className="h-full overflow-auto py-3 px-1.5" data-testid="entry-rail">
      {CAPABILITY_GROUPS.map((g) => (
        <div key={g.key} className="mb-3.5">
          <div className="px-2.5 py-1 text-meta uppercase tracking-wider text-faint/50 select-none">{g.label}</div>
          {g.items.map((it) => {
            const entry = entryFor(tree, it)
            const active = entry.id === activeId
            const n = countOf(entry.source)
            return (
              <button
                key={entry.id}
                onClick={() => onEntry(entry)}
                className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-xl text-f13 text-left transition-colors ${active ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-soft'}`}
              >
                <span className="truncate flex-1">{entry.label}</span>
                {n != null && <span className={`text-meta shrink-0 ${active ? 'text-brand/70' : 'text-faint/70'}`}>{n}</span>}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

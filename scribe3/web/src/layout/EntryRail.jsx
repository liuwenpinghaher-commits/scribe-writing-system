// 栏1 · 一级入口:从 project-tree 派生的扁平入口(手稿 / 设定各类 / 素材),分组竖排。
// 与旧混合树的根本区别:点入口只切换第二栏目录,绝不像旧树那样 node.toggle() 就地展开
// (那正是"条目挤进第一栏"的病灶)。横切视图入口统一放在顶栏,不再挤进本栏。
//
// 数据零新增:入口就是各 root/category 节点本身(手稿=manuscript_root,设定=codex.children,
// 素材=material_root),只取 {id,type,ref,label,badges},children 交给第二栏懒渲染。

function countOf(node) {
  const b = (node?.badges || []).find((x) => x.kind === 'count')
  return b?.value
}

export function EntryRail({ tree, activeId, onEntry }) {
  const groups = [
    { key: 'ms', label: '手稿', items: tree?.manuscript ? [tree.manuscript] : [] },
    { key: 'codex', label: '设定', items: tree?.codex?.children || [] },
    { key: 'mat', label: '素材', items: tree?.materials ? [tree.materials] : [] },
  ]
  return (
    <div className="h-full overflow-auto py-2" data-testid="entry-rail">
      {groups.map((g) => g.items.length > 0 && (
        <div key={g.key} className="mb-3">
          <div className="px-3 py-1 text-f10 uppercase tracking-wider text-faint/60 select-none">{g.label}</div>
          {g.items.map((it) => {
            const active = it.id === activeId
            const n = countOf(it)
            return (
              <button
                key={it.id}
                onClick={() => onEntry(it)}
                className={`w-full flex items-center gap-2 px-3 py-1.5 text-f13 text-left transition-colors ${active ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-hover'}`}
              >
                <span className="truncate flex-1">{it.label}</span>
                {n != null && <span className={`text-f11 shrink-0 ${active ? 'text-brand/70' : 'text-faint/70'}`}>{n}</span>}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

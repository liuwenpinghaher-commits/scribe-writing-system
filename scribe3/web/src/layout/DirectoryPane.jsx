import { ContainerOutline } from '../ContainerOutline'
import { MaterialList } from '../Materials'

// 栏2 · 目录:据入口类型分发到现成列表组件。**常驻不被替换**——点条目走 onSelectItem
// (更新共享 sel → 只刷新栏3详情),本栏由 entry 驱动、entry 不变则保持挂载。这正是四栏钻取
// 相对旧"一柱擎天"的核心修复:目录列表与条目详情分处两个物理列,互不覆盖。
//
// 复用契约(与 DetailPane 权威接线一致):
//   ContainerOutline({ node, onOpenChapter, onSelect })  —— 手稿卡片墙 / 设定分类 PlainList
//   MaterialList({ node, onSelect })                     —— 素材库(自带搜索/召回/记忆网络)

const chapterNode = (seq, title = '') => ({ id: `ch:${seq}`, type: 'chapter', ref: seq, label: `${seq} ${title}`.trim(), phase: 'outline' })
const BOOK_TOOLS = [
  { id: 'book:outline', type: 'book_outline', ref: null, label: '全书大纲' },
  { id: 'book:northstar', type: 'book_northstar', ref: null, label: '北极星' },
  { id: 'view:progress', type: 'view', ref: 'progress', label: '进度' },
]

function BookTools({ onSelectItem }) {
  return (
    <div className="shrink-0 border-b border-line bg-surface px-3 py-2">
      <div className="text-f10 uppercase tracking-wider text-faint/60 mb-1">书级工具</div>
      <div className="grid grid-cols-3 gap-1">
        {BOOK_TOOLS.map((tool) => (
          <button key={tool.id} onClick={() => onSelectItem?.(tool)}
            className="h-7 rounded-md border border-line bg-canvas px-2 text-f12 text-ink hover:border-brand/40 hover:text-brand transition-colors cursor-pointer">
            {tool.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function DirectoryPane({ entry, onSelectItem }) {
  if (!entry) {
    return (
      <div className="h-full grid place-items-center px-4 text-center text-f12 text-faint/50" data-testid="directory-empty">
        选择左侧入口查看目录
      </div>
    )
  }
  const t = entry.type
  if (t === 'material_root' || t === 'material_category') {
    return <MaterialList key={entry.id} node={entry} onSelect={onSelectItem} />
  }
  if (t === 'manuscript_root') {
    return (
      <div className="h-full min-h-0 flex flex-col">
        <BookTools onSelectItem={onSelectItem} />
        <div className="flex-1 min-h-0">
          <ContainerOutline
            key={entry.id}
            node={entry}
            onOpenChapter={(c) => onSelectItem(chapterNode(c.seq, c.title))}
            onSelect={onSelectItem}
          />
        </div>
      </div>
    )
  }
  // 手稿根/卷 → 卡片墙;设定分类/设定根 → PlainList(均走 ContainerOutline)
  return (
    <ContainerOutline
      key={entry.id}
      node={entry}
      onOpenChapter={(c) => onSelectItem(chapterNode(c.seq, c.title))}
      onSelect={onSelectItem}
    />
  )
}

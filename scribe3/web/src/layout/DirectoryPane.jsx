import { ContainerOutline } from '../ContainerOutline'
import { MaterialList } from '../Materials'
import { ManuscriptDirectory } from './ManuscriptDirectory'
import { CapabilityDirectory } from './CapabilityDirectories'
import { SearchDirectory } from '../capabilities/search/SearchDirectory'
import { IssueDirectory } from '../capabilities/issues/IssueDirectory'
import { CodexDirectory } from './CodexDirectory'

// 栏2 · 目录:据入口类型分发到现成列表组件。**常驻不被替换**——点条目走 onSelectItem
// (更新共享 sel → 只刷新栏3详情),本栏由 entry 驱动、entry 不变则保持挂载。这正是四栏钻取
// 相对旧"一柱擎天"的核心修复:目录列表与条目详情分处两个物理列,互不覆盖。
//
// 复用契约(与 DetailPane 权威接线一致):
//   ContainerOutline({ node, onOpenChapter, onSelect })  —— 手稿卡片墙 / 设定分类 PlainList
//   MaterialList({ node, onSelect })                     —— 素材库(自带搜索/召回/记忆网络)

const chapterNode = (seq, title = '') => ({ id: `ch:${seq}`, type: 'chapter', ref: seq, label: `${seq} ${title}`.trim(), phase: 'outline' })

export function DirectoryPane({ entry, onSelectItem, sel, seq, onJumpChapter, onCreateChapter, onArchivedChanged }) {
  if (!entry) {
    return (
      <div className="h-full grid place-items-center px-4 text-center text-f12 text-faint/50" data-testid="directory-empty">
        选择左侧入口查看目录
      </div>
    )
  }
  const capability = entry.capability
  if (capability === 'manuscript') {
    return <ManuscriptDirectory entry={entry} sel={sel} seq={seq} onSelectItem={onSelectItem} onJumpChapter={onJumpChapter} onCreateChapter={onCreateChapter} onArchivedChanged={onArchivedChanged} />
  }
  if (capability === 'materials') {
    return <MaterialList key={entry.id} node={entry.source || entry} onSelect={onSelectItem} />
  }
  if (capability === 'codex') {
    return <CodexDirectory root={entry.source || entry} selected={sel?.node} onSelectItem={onSelectItem} />
  }
  if (capability === 'search') {
    return <SearchDirectory onSelectItem={onSelectItem} />
  }
  if (capability === 'review') {
    return <IssueDirectory seq={seq} onSelectItem={onSelectItem} />
  }
  if (['deduce', 'promise', 'motif'].includes(capability)) {
    return <CapabilityDirectory capability={capability} seq={seq} onSelectItem={onSelectItem} />
  }

  const t = entry.type
  if (t === 'material_root' || t === 'material_category') {
    return <MaterialList key={entry.id} node={entry} onSelect={onSelectItem} />
  }
  if (t === 'manuscript_root') {
    return <ManuscriptDirectory entry={entry} sel={sel} seq={seq} onSelectItem={onSelectItem} onJumpChapter={onJumpChapter} onCreateChapter={onCreateChapter} onArchivedChanged={onArchivedChanged} />
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

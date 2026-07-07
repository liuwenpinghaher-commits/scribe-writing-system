import { useState } from 'react'
import { RightDock } from '../studioDocks'
import { DetailPane } from '../DetailPane'
import { EntryRail } from './EntryRail'
import { DirectoryPane } from './DirectoryPane'

// 四栏钻取壳(阶段3-2):栏1 一级入口 | 栏2 目录(常驻) | 栏3 详情 | 栏4 主编。
//
// 两级选中,互不干扰:
//   · entry(本壳内部 state)—— 选中的"一级入口/分类",驱动栏2 目录列表。
//   · sel  (BinderLayout 共享 state)—— 选中的"条目",驱动栏3 详情 + 栏4 主编上下文。
// 点入口 → 只改 entry(换栏2);点目录条目 → 走 onSelectNode 改共享 sel(只换栏3),栏2 保持挂载。
// 这就是对旧"一柱擎天"(目录/详情路由到同一列互相替换)的根治。
//
// 视图入口(type==='view')直接进共享 sel 的 view 模式:栏3 全画布、栏2 隐藏。
// 全程在 V2 flag 后,BinderLayout 旧三栏(flag 关)一行不改、永远可回退。
export function FourPaneShell({
  tree, onSelectNode, sel, work, reload, onJumpChapter,
  chapterSel, curSeq, leftSeq, onRestored, collapseRight,
}) {
  const [entry, setEntry] = useState(null)
  const isView = sel?.mode === 'view'

  const handleEntry = (node) => {
    if (node.type === 'view') { onSelectNode?.(node); setEntry(null) }  // 视图 → 全画布,无栏2
    else setEntry(node)
  }
  const activeEntryId = isView ? (sel.viewKey ? `view:${sel.viewKey}` : null) : entry?.id

  return (
    <div className="h-full flex flex-col bg-canvas" data-testid="four-col">
      <div className="flex-1 min-h-0 flex">
        {/* 栏1 · 一级入口 */}
        <div className="w-[168px] shrink-0 border-r border-line bg-surface overflow-hidden">
          <EntryRail tree={tree} activeId={activeEntryId} onEntry={handleEntry} />
        </div>
        {/* 栏2 · 目录(视图态隐藏) */}
        {!isView && (
          <div className="w-[248px] shrink-0 border-r border-line bg-surface/60 overflow-hidden" data-testid="col-directory">
            <DirectoryPane entry={entry} onSelectItem={onSelectNode} />
          </div>
        )}
        {/* 栏3 · 详情(复用 DetailPane,仅喂条目/视图) */}
        <div className="flex-1 min-w-0 overflow-hidden flex flex-col" data-testid="detail">
          <DetailPane sel={sel} work={work} onSelectNode={onSelectNode}
            onTreeChanged={reload} onJumpChapter={onJumpChapter} />
        </div>
        {/* 栏4 · 主编(复用 RightDock,随共享 sel 切上下文) */}
        <div className="w-[300px] shrink-0 border-l border-line bg-surface overflow-hidden">
          <RightDock sel={sel} chapterSel={chapterSel} seq={curSeq} lastSeq={leftSeq}
            onRestored={onRestored} onCollapse={collapseRight} />
        </div>
      </div>
    </div>
  )
}

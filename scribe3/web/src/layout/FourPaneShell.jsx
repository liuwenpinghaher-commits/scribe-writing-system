import { RightDock, useLeftDockCapabilities } from '../studioDocks'
import { DetailPane } from '../DetailPane'
import { Rail } from '../shell'
import { ErrorBoundary } from '../ErrorBoundary'
import { cn } from '../lib/utils'
import { useEffect, useState } from 'react'
import { PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { Group, Panel, Separator, useDefaultLayout, usePanelRef } from 'react-resizable-panels'
import { DirectoryPane } from './DirectoryPane'
import { targetNodeToSelection } from './targetNavigation'

const FOUR_PANE_LAYOUT_ID = 's3.fourPane.layout.v2'
const FOUR_PANE_DEFAULT_LAYOUT = { directory: 14, detail: 62, right: 24 }
const DIRECTORY_PANEL = { default: 14, min: 10, max: 24 }
const RIGHT_PANEL = { default: 24, min: 18, max: 36 }
const RESIZER_CLASS = 'relative w-2 -mx-[3.5px] bg-transparent cursor-col-resize data-[separator]:hover:bg-brand/20 transition-colors after:absolute after:inset-y-0 after:left-1/2 after:-translate-x-1/2 after:w-px after:bg-line'
const RESTORE_BUTTON_CLASS = 'absolute top-2 z-20 h-7 w-7 rounded-lg border border-line bg-surface text-faint shadow-sm hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer'

function collapsedStorageKey(work, side) {
  return `s3.${work || 'default'}.${side}Collapsed`
}

function readCollapsed(work, side) {
  try { return localStorage.getItem(collapsedStorageKey(work, side)) === '1' } catch { return false }
}

function writeCollapsed(work, side, collapsed) {
  try { localStorage.setItem(collapsedStorageKey(work, side), collapsed ? '1' : '0') } catch { /* */ }
}

function callPanel(panel, method) {
  try { panel?.[method]?.() } catch { /* panel may be unmounted in view mode */ }
}

function entrySource(tree, key) {
  if (key === 'manuscript') return tree?.manuscript
  if (key === 'codex') return tree?.codex
  if (key === 'materials') return tree?.materials
  return null
}

function entryForActive(tree, active) {
  if (!active?.key) return null
  return {
    id: `entry:${active.key}`,
    type: 'entry_capability',
    capability: active.key,
    label: active.label,
    source: entrySource(tree, active.key),
  }
}

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
  tree, selId, expanded, toggle, onSelectNode, treeCbs, sel, work, reload, onJumpChapter,
  chapterSel, curSeq, leftSeq, onRestored, collapseLeft, collapseRight,
}) {
  const isView = sel?.mode === 'view'
  const [directoryRefresh, setDirectoryRefresh] = useState(0)
  const directoryRef = usePanelRef()
  const rightRef = usePanelRef()
  const [directoryCollapsed, setDirectoryCollapsed] = useState(() => readCollapsed(work, 'directory'))
  const [rightCollapsed, setRightCollapsed] = useState(() => readCollapsed(work, 'right'))
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id: FOUR_PANE_LAYOUT_ID })
  const { caps, active, setTab } = useLeftDockCapabilities({
    tree,
    selId,
    expanded,
    onToggle: toggle,
    onSelect: onSelectNode,
    treeCbs,
    seq: leftSeq,
    work,
    includeStageTabs: false,
    splitProjectRoots: true,
  })
  const activeEntry = entryForActive(tree, active)
  useEffect(() => {
    setDirectoryCollapsed(readCollapsed(work, 'directory'))
    setRightCollapsed(readCollapsed(work, 'right'))
  }, [work])
  useEffect(() => {
    if (isView) return
    if (directoryCollapsed) callPanel(directoryRef.current, 'collapse')
    else callPanel(directoryRef.current, 'expand')
  }, [directoryCollapsed, directoryRef, isView])
  useEffect(() => {
    if (rightCollapsed) callPanel(rightRef.current, 'collapse')
    else callPanel(rightRef.current, 'expand')
  }, [rightCollapsed, rightRef])
  const collapseDirectory = () => {
    setDirectoryCollapsed(true)
    writeCollapsed(work, 'directory', true)
    callPanel(directoryRef.current, 'collapse')
  }
  const expandDirectory = () => {
    setDirectoryCollapsed(false)
    writeCollapsed(work, 'directory', false)
    callPanel(directoryRef.current, 'expand')
  }
  const toggleDirectory = () => {
    if (directoryCollapsed) expandDirectory()
    else collapseDirectory()
  }
  const collapseRightPanel = () => {
    setRightCollapsed(true)
    writeCollapsed(work, 'right', true)
    callPanel(rightRef.current, 'collapse')
  }
  const expandRightPanel = () => {
    setRightCollapsed(false)
    writeCollapsed(work, 'right', false)
    callPanel(rightRef.current, 'expand')
  }
  const handleActive = (key) => {
    const nextKey = key || (isView ? active?.key : '')
    if (!nextKey) { toggleDirectory(); return }
    setTab(nextKey)
    if (directoryCollapsed) expandDirectory()
    if (isView) onSelectNode?.(null)
  }
  const handleNavigateToObject = (target) => {
    const next = targetNodeToSelection(target)
    if (!next) return
    if (next.entry) setTab(next.entry)
    if (next.node) onSelectNode?.(next.node)
  }
  const handleTreeChanged = () => {
    reload?.()
    setDirectoryRefresh((v) => v + 1)
  }

  return (
    <div className="h-full flex flex-col bg-canvas" data-testid="four-col">
      <div className="flex-1 min-h-0 flex">
        {/* 栏1 · 小 tab 轨,与旧左右栏 Rail 同构 */}
        <div className="shrink-0 bg-surface overflow-hidden" data-testid="left-entry-rail">
          <Rail side="left" caps={caps} active={active.key} onActive={handleActive} />
        </div>
        <Group
          orientation="horizontal"
          defaultLayout={defaultLayout ?? FOUR_PANE_DEFAULT_LAYOUT}
          onLayoutChanged={onLayoutChanged}
          className="flex-1 min-w-0 h-full"
        >
          {/* 栏2 · DirectoryPane 生产路由(视图态隐藏),常驻不被栏3详情替换 */}
          {!isView && (
            <>
              <Panel
                id="directory"
                panelRef={directoryRef}
                defaultSize={`${DIRECTORY_PANEL.default}%`}
                minSize={`${DIRECTORY_PANEL.min}%`}
                maxSize={`${DIRECTORY_PANEL.max}%`}
                collapsible
                collapsedSize="0%"
                onResize={(size) => {
                  const collapsed = size.asPercentage < 1
                  setDirectoryCollapsed(collapsed)
                  writeCollapsed(work, 'directory', collapsed)
                }}
                className={cn('border-r border-line bg-surface/60 min-h-0 overflow-hidden')}
              >
                <div
                  className="h-full min-w-0"
                  data-testid="col-directory-panel"
                  data-default-size={String(DIRECTORY_PANEL.default)}
                  data-min-size={String(DIRECTORY_PANEL.min)}
                  data-max-size={String(DIRECTORY_PANEL.max)}
                >
                  {!directoryCollapsed && (
                    <div className="h-full min-w-0" data-testid="col-directory">
                      <ErrorBoundary key={`${active?.key}:${leftSeq ?? ''}:${directoryRefresh}`}>
                        <DirectoryPane
                          entry={activeEntry}
                          onSelectItem={onSelectNode}
                          sel={sel}
                          seq={leftSeq}
                          onJumpChapter={onJumpChapter}
                        />
                      </ErrorBoundary>
                    </div>
                  )}
                </div>
              </Panel>
              <Separator className={RESIZER_CLASS} data-testid="directory-resize-handle" />
            </>
          )}
          {/* 栏3 · 详情(复用 DetailPane,仅喂条目/视图) */}
          <Panel
            id="detail"
            minSize={isView ? '56%' : '34%'}
            className="relative min-w-0 overflow-hidden flex flex-col"
            data-testid="detail-panel"
          >
            {directoryCollapsed && !isView && (
              <button type="button" data-testid="directory-restore-button" aria-label="展开目录" title="展开目录"
                onClick={expandDirectory} className={`${RESTORE_BUTTON_CLASS} left-2`}>
                <PanelLeftOpen size={15} />
              </button>
            )}
            {rightCollapsed && (
              <button type="button" data-testid="right-restore-button" aria-label="展开主编栏" title="展开主编栏"
                onClick={expandRightPanel} className={`${RESTORE_BUTTON_CLASS} right-2`}>
                <PanelRightOpen size={15} />
              </button>
            )}
            <div className="h-full min-w-0 overflow-hidden flex flex-col" data-testid="detail">
              <DetailPane sel={sel} work={work} onSelectNode={onSelectNode}
                onTreeChanged={handleTreeChanged} onJumpChapter={onJumpChapter}
                onNavigateToObject={handleNavigateToObject} />
            </div>
          </Panel>
          <Separator className={RESIZER_CLASS} data-testid="right-resize-handle" />
          {/* 栏4 · 主编(复用 RightDock,随共享 sel 切上下文) */}
          <Panel
            id="right"
            panelRef={rightRef}
            defaultSize={`${RIGHT_PANEL.default}%`}
            minSize={`${RIGHT_PANEL.min}%`}
            maxSize={`${RIGHT_PANEL.max}%`}
            collapsible
            collapsedSize="0%"
            onResize={(size) => {
              const collapsed = size.asPercentage < 5
              setRightCollapsed(collapsed)
              writeCollapsed(work, 'right', collapsed)
            }}
            className="border-l border-line bg-surface overflow-hidden"
            data-testid="right-panel"
          >
            {!rightCollapsed && (
              <div className="relative h-full min-h-0">
                <button type="button" data-testid="right-collapse-button" aria-label="收起主编栏" title="收起主编栏"
                  onClick={collapseRightPanel}
                  className="absolute right-2 top-2 z-20 h-7 w-7 rounded-lg border border-line bg-surface text-faint shadow-sm hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer">
                  <PanelRightClose size={15} />
                </button>
                <RightDock sel={sel} chapterSel={chapterSel} seq={curSeq} lastSeq={leftSeq}
                  onRestored={onRestored} onCollapse={collapseRightPanel} />
              </div>
            )}
          </Panel>
        </Group>
      </div>
    </div>
  )
}

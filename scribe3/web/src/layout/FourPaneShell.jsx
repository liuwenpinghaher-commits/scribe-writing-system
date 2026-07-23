import { RightDock, useLeftDockCapabilities } from '../studioDocks'
import { DetailPane } from '../DetailPane'
import { Rail } from '../shell'
import { ErrorBoundary } from '../ErrorBoundary'
import { cn } from '../lib/utils'
import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, PanelRightClose } from 'lucide-react'
import { Group, Panel, Separator, useDefaultLayout, usePanelRef } from 'react-resizable-panels'
import { DirectoryPane } from './DirectoryPane'
import { targetNodeToSelection } from './targetNavigation'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { showToast } from '../ui/Toast'
import { useContextSnapshot } from '../context/ContextSnapshotContext'
import { entryPatch, nodePatch, viewPatch } from '../context/contextSnapshot'
import { routeOf, selectionFromSnapshot } from './contextSelection'
import {
  FOUR_PANE_BOUNDS, FOUR_PANE_DEFAULT, sanitizeLayout,
} from './sanitizeLayout'
import { planEntryChange } from './entrySelection'

const FOUR_PANE_LAYOUT_ID = 's3.fourPane.layout.v2'
const FOUR_PANE_DEFAULT_LAYOUT = FOUR_PANE_DEFAULT
const DIRECTORY_PANEL = {
  default: FOUR_PANE_DEFAULT.directory,
  min: FOUR_PANE_BOUNDS.directory.min,
  max: FOUR_PANE_BOUNDS.directory.max,
}
// max 58(原 36):作者要能把主编对话拉很宽读长回复;中区 minSize 兜底,不会被挤没
const RIGHT_PANEL = {
  default: FOUR_PANE_DEFAULT.right,
  min: FOUR_PANE_BOUNDS.right.min,
  max: FOUR_PANE_BOUNDS.right.max,
}
// 拖拽把手:不用负 margin 叠层(旧 -mx 会在窄窗/拖拽时挤乱相邻栏命中区)
const RESIZER_CLASS = 'w-1 shrink-0 bg-transparent cursor-col-resize hover:bg-brand/20 active:bg-brand/30 transition-colors data-[separator]:bg-line/30'
// 还原按钮 = 贴栏3 左/右缘、垂直居中的细把手。Upstream 式软面 + 轻阴影。
const RESTORE_BUTTON_CLASS = 'absolute top-1/2 -translate-y-1/2 z-20 h-14 w-3.5 border-0 bg-surface text-faint shadow-[var(--shadow-panel)] hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer'

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
// Task 5(统一上下文):上述两级选中的"语义事实"统一记录进 ContextSnapshot——
// 每个语义动作(入口/条目/对象定位)只发一个完整 NavigationIntent,快照 revision
// 盖在栏3/栏4容器上,四栏同帧共享同一 revision;子组件 props 合同不变。
//
// 视图入口(type==='view')直接进共享 sel 的 view 模式:栏3 全画布、栏2 隐藏。
// 唯一布局壳（旧三栏 + s3.layout.v2 回退已删除）。
export function FourPaneShell({
  tree, selId, expanded, toggle, onSelectNode, treeCbs, sel, work, reload, onJumpChapter,
  chapterSel, curSeq, leftSeq, onRestored,
}) {
  const [directoryRefresh, setDirectoryRefresh] = useState(0)
  const directoryRef = usePanelRef()
  const rightRef = usePanelRef()
  const [directoryCollapsed, setDirectoryCollapsed] = useState(() => readCollapsed(work, 'directory'))
  const [rightCollapsed, setRightCollapsed] = useState(() => readCollapsed(work, 'right'))
  // 栏宽布局按作品隔离:换书不串栏宽偏好(与 readCollapsed/writeCollapsed 的作品级 key 同粒度)。
  // 保留 FOUR_PANE_LAYOUT_ID 前缀,换常量名会作废用户已保存的栏宽。
  // sanitize:纠偏 localStorage 损坏/缺键/和≠100 的布局,防拖拽后整页错乱。
  const { defaultLayout: rawLayout, onLayoutChanged: persistLayout } = useDefaultLayout({
    id: `${FOUR_PANE_LAYOUT_ID}:${work || 'main'}`,
  })
  const defaultLayout = sanitizeLayout(rawLayout)
  const onLayoutChanged = (layout, meta) => {
    persistLayout?.(sanitizeLayout(layout), meta)
  }
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
  // Task 5 · 单一 ContextSnapshot:四栏语义状态(入口/焦点/详情路由/revision)
  // 收敛进快照;每个语义动作只发【一个】完整 NavigationIntent。Provider 缺席
  // (旧测试直渲/旧三栏)时 snapshot=null、navigate=no-op,以下全部回退现状。
  const { snapshot, navigate, navigated, error: ctxError } = useContextSnapshot()
  // 入口投影:导航发生后以快照为准(跨窗口 409 对齐也走这里);未导航时回退
  // leftTab 偏好(服务端初始快照的默认 entry 不抢用户上次停留的入口)。
  const projectedEntryKey = navigated && snapshot?.entry ? snapshot.entry : active?.key
  const activeCap = projectedEntryKey === active?.key ? active : (caps.find((c) => c.key === projectedEntryKey) || active)
  const activeEntry = entryForActive(tree, activeCap)
  // 快照 revision 盖到栏3/栏4容器:同一帧同一 revision,即"四栏原子性"的可见凭据
  const ctxRevision = snapshot ? String(snapshot.revision) : undefined
  // 内容投影:导航发生后以快照为渲染事实源(含跨窗口 409 对齐到 latest),让栏2/3/4
  // 的选中态与 revision 同帧翻页;未导航(Provider 缺席/本地模式)时降级直通原 sel。
  // 事件回调仍只改本地 sel/onSelectNode——投影是只读的下行,不改变上行写路径。
  const effectiveSel = navigated ? selectionFromSnapshot(snapshot, sel) : sel
  // isView 读投影后的 effectiveSel(而非本地 sel):栏2 显隐 / 栏3 minSize / 目录折叠
  // effect 全由它驱动,内容也读 effectiveSel——两者同源才不会在跨 view 边界对齐时
  // 布局与内容自相矛盾。降级(navigated=false)时 effectiveSel===sel,行为不变。
  const isView = effectiveSel?.mode === 'view'
  // entry 双向对齐(I-1),按"这一轮是谁先动"判方向,防止两侧互相覆盖打成请求循环:
  //   · 快照侧变化(409 对齐 latest / 另一窗口推进)→ 服务端赢,本窗口 leftTab 跟随(setTab);
  //     跟随引起的 active 变化在下一轮里两侧已相等,绝不反向发 intent;
  //   · 本地 tab 旁路直改(s3-open-capability 事件等)→ 补记一次语义导航进快照,
  //     快照保持唯一事实源,不再冒出第二个来源。
  const entrySyncRef = useRef({ active: active?.key, snap: snapshot?.entry })
  useEffect(() => {
    const a = active?.key
    const s = snapshot?.entry
    const prev = entrySyncRef.current
    entrySyncRef.current = { active: a, snap: s }
    if (!navigated || !a || !s || a === s) return
    if (s !== prev.snap) {
      // 快照侧先动(服务端对齐信号)→ UI 跟随,不反向补记
      if (caps.some((c) => c.key === s)) setTab(s)
      return
    }
    // 本地 tab 旁路(s3-open-capability)的 navigate+栏3 收敛改由下方 open-capability
    // 监听与 handleActive 统一走 planEntryChange，此处不再裸 entryPatch，避免双发 revision。
  }, [navigated, active?.key, snapshot?.entry, caps, setTab])
  // I-2(同型于 I-1 entry 对齐):sel 的旁路直改也要补记进快照。顶栏横切视图
  // (App.onView)/ 时间线跳章(App.handleJumpChapter)都在本组件之外直改 sel、
  // 不经 handleSelectItem 的 navigate——若不补记,navigated 后投影以快照为事实源,
  // 会把用户刚点的视图/章盖回快照里的旧 focus(实症:进手稿后图谱/时间线/仪表盘
  // 打不开)。按"这一轮谁先动"判方向:快照侧先动(409 对齐/另窗口)→ 投影已让
  // UI 跟随,绝不反向补记打成循环;本地侧先动 → 补记一次语义导航。
  // 路由口径必须用 contextSelection.routeOf(与投影同源),否则漏边沿/误补记。
  const selSyncRef = useRef({ local: routeOf(sel), snap: snapshot?.detail_route })
  useEffect(() => {
    const local = routeOf(sel)
    const snap = snapshot?.detail_route
    const prev = selSyncRef.current
    selSyncRef.current = { local, snap }
    if (!navigated || !snap || local === snap) return
    if (snap !== prev.snap) return   // 快照侧先动:UI 跟随投影,不反向补记
    if (local === prev.local) return // 双方都没动(无关重渲):不动快照
    if (sel?.mode === 'view' && sel.viewKey) navigate(viewPatch(sel.viewKey))
    // 旁路只可能带来章跳转(App.handleJumpChapter);其余节点类都走 handleSelectItem,
    // 空选(node:null,如退出视图)由 handleActive 的 entryPatch 先行收敛,不在此补记
    else if (sel?.node) navigate(nodePatch(sel.node))
  }, [navigated, sel, snapshot?.detail_route, navigate])

  // 409 对齐后向用户说明(fail-soft:只提示,不打断)
  useEffect(() => {
    if (ctxError?.code === 'stale_context') showToast(ctxError.message, { tone: 'warn' })
  }, [ctxError])
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
  // rail 点击与 s3-open-capability 共用：一次 plan → 一次 navigate + 可选 onSelectNode
  const applyEntryKey = (nextKey) => {
    if (!nextKey) return
    const label = caps.find((c) => c.key === nextKey)?.label || ''
    if (isView) {
      navigate(entryPatch(nextKey, label))
      onSelectNode?.(null)
      return
    }
    const plan = planEntryChange(nextKey, sel?.node, tree, label)
    navigate(plan.patch)
    if (plan.select !== undefined) onSelectNode?.(plan.select)
  }
  const handleActive = (key) => {
    const nextKey = key || (isView ? activeCap?.key : '')
    if (!nextKey) { toggleDirectory(); return }
    setTab(nextKey)
    if (directoryCollapsed) expandDirectory()
    applyEntryKey(nextKey)
  }
  // 顶栏搜索 / ⌘K 只 setTab 的旁路：同样收敛栏3，消除「搜索目录 + 伏笔详情」
  // 用 ref 读最新 plan 输入，避免把 sel/tree 放进 effect 依赖导致频繁重绑
  const entryApplyRef = useRef({ applyEntryKey, directoryCollapsed, expandDirectory, caps })
  entryApplyRef.current = { applyEntryKey, directoryCollapsed, expandDirectory, caps }
  useEffect(() => {
    const onOpenCapability = (e) => {
      const raw = e?.detail?.capability
      const key = raw === 'recall' ? 'search' : raw === 'issues' ? 'review' : raw
      const { applyEntryKey: apply, directoryCollapsed: collapsed, expandDirectory: expand, caps: capList } = entryApplyRef.current
      if (!key || !capList.some((c) => c.key === key)) return
      if (collapsed) expand()
      apply(key)
    }
    window.addEventListener('s3-open-capability', onOpenCapability)
    return () => window.removeEventListener('s3-open-capability', onOpenCapability)
  }, [])
  // 语义动作"选中条目"(栏2目录 / 栏3详情内跳转共用):一个 intent + 既有 sel 链路
  const handleSelectItem = (node) => {
    if (node) navigate(nodePatch(node, projectedEntryKey))
    onSelectNode?.(node)
  }
  const handleNavigateToObject = (target) => {
    const next = targetNodeToSelection(target)
    if (!next) return
    // 跨入口对象定位 = 仍只发一个完整 intent(entry+focus 原子收敛)
    if (next.node) navigate({ ...nodePatch(next.node, next.entry || projectedEntryKey), reason: 'explicit' })
    else if (next.entry) navigate(entryPatch(next.entry))
    if (next.entry) setTab(next.entry)
    if (next.node) onSelectNode?.(next.node)
  }
  const handleTreeChanged = () => {
    reload?.()
    setDirectoryRefresh((v) => v + 1)
  }
  // 禁止 api.createChapter REST 直写;主编 s3_add_chapter 审批落库
  const handleCreateChapter = (volume) => {
    const volHint = volume != null && volume !== ''
      ? `请归属 volume_id=${volume}。`
      : '可不指定卷(未分卷)。'
    seedChiefNarrativeWrite(
      'chapter',
      '新建章节',
      `请用 s3_add_chapter 新建一章。${volHint}未获批准不得声称已落库。`,
    )
  }
  const handleChapterArchived = (seq) => {
    reload?.()
    setDirectoryRefresh((v) => v + 1)
    if (sel?.node?.type === 'chapter' && Number(sel.node.ref) === Number(seq)) onSelectNode?.(null)
  }

return (
    <div className="h-full min-h-0 flex flex-col bg-canvas overflow-hidden" data-testid="four-col">
      <div className="flex-1 min-h-0 min-w-0 flex overflow-hidden">
        {/* 栏1 · 小 tab 轨,与旧左右栏 Rail 同构 · 固定宽,绝不参与拖拽百分比 */}
        <div className="w-14 shrink-0 bg-surface overflow-hidden shadow-[1px_0_0_0_color-mix(in_srgb,var(--color-line)_70%,transparent)]" data-testid="left-entry-rail">
          <Rail side="left" caps={caps} active={activeCap?.key} onActive={handleActive} />
        </div>
        <Group
          orientation="horizontal"
          defaultLayout={defaultLayout ?? FOUR_PANE_DEFAULT_LAYOUT}
          onLayoutChanged={onLayoutChanged}
          className="flex-1 min-w-0 min-h-0 h-full overflow-hidden"
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
                  // 低于 min 的一半即视为折叠,避免「半开半关」窄条把中文挤成竖排
                  const collapsed = size.asPercentage < DIRECTORY_PANEL.min * 0.5
                  setDirectoryCollapsed(collapsed)
                  writeCollapsed(work, 'directory', collapsed)
                }}
                className={cn('border-r border-line/50 bg-surface min-h-0 min-w-0 overflow-hidden')}
              >
                <div
                  className="h-full min-h-0 min-w-[10rem] max-w-full overflow-hidden"
                  data-testid="col-directory-panel"
                  data-default-size={String(DIRECTORY_PANEL.default)}
                  data-min-size={String(DIRECTORY_PANEL.min)}
                  data-max-size={String(DIRECTORY_PANEL.max)}
                >
                  {!directoryCollapsed && (
                    <div className="h-full min-h-0 min-w-0 overflow-hidden" data-testid="col-directory">
                      <ErrorBoundary key={`${activeCap?.key}:${leftSeq ?? ''}:${directoryRefresh}`}>
                        <DirectoryPane
                          entry={activeEntry}
                          onSelectItem={handleSelectItem}
                          sel={effectiveSel}
                          seq={leftSeq}
                          onJumpChapter={onJumpChapter}
                          onCreateChapter={handleCreateChapter}
                          onAddVolume={treeCbs?.onAddVolume}
                          onArchivedChanged={handleTreeChanged}
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
            defaultSize={`${FOUR_PANE_DEFAULT.detail}%`}
            minSize={isView ? '56%' : `${FOUR_PANE_BOUNDS.detail.min}%`}
            className="relative min-w-0 min-h-0 overflow-hidden flex flex-col"
            data-testid="detail-panel"
          >
            {directoryCollapsed && !isView && (
              <button type="button" data-testid="directory-restore-button" aria-label="展开目录" title="展开目录"
                onClick={expandDirectory} className={`${RESTORE_BUTTON_CLASS} left-0 border-l-0 rounded-r-lg`}>
                <ChevronRight size={14} />
              </button>
            )}
            {rightCollapsed && (
              <button type="button" data-testid="right-restore-button" aria-label="展开主编栏" title="展开主编栏"
                onClick={expandRightPanel} className={`${RESTORE_BUTTON_CLASS} right-0 border-r-0 rounded-l-lg`}>
                <ChevronLeft size={14} />
              </button>
            )}
            <div className="h-full min-h-0 min-w-0 overflow-hidden flex flex-col" data-testid="detail" data-context-revision={ctxRevision}>
              <DetailPane sel={effectiveSel} work={work} entryKey={projectedEntryKey}
                onSelectNode={handleSelectItem}
                onTreeChanged={handleTreeChanged} onJumpChapter={onJumpChapter}
                onNavigateToObject={handleNavigateToObject}
                onChapterArchived={handleChapterArchived} />
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
              const collapsed = size.asPercentage < RIGHT_PANEL.min * 0.5
              setRightCollapsed(collapsed)
              writeCollapsed(work, 'right', collapsed)
            }}
            className="border-l border-line/50 bg-surface min-h-0 min-w-0 overflow-hidden"
            data-testid="right-panel"
          >
            {!rightCollapsed && (
              <div className="relative h-full min-h-0 min-w-0 max-w-full overflow-hidden" data-testid="right-dock" data-context-revision={ctxRevision}>
                <button type="button" data-testid="right-collapse-button" aria-label="收起主编栏" title="收起主编栏"
                  onClick={collapseRightPanel}
                  className="absolute right-2 top-2 z-20 h-7 w-7 rounded-md bg-soft/80 text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer">
                  <PanelRightClose size={15} />
                </button>
                <RightDock sel={effectiveSel} chapterSel={chapterSel} seq={curSeq} lastSeq={leftSeq}
                  onRestored={onRestored} onCollapse={collapseRightPanel} />
              </div>
            )}
          </Panel>
        </Group>
      </div>
    </div>
  )
}

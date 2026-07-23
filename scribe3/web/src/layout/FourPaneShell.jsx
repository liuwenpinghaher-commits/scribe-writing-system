import { RightDock, useLeftDockCapabilities } from '../studioDocks'
import { DetailPane } from '../DetailPane'
import { Rail } from '../shell'
import { ErrorBoundary } from '../ErrorBoundary'
import { cn } from '../lib/utils'
import { Fragment, useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Group, Panel, Separator, useDefaultLayout, usePanelRef } from 'react-resizable-panels'
import { DirectoryPane } from './DirectoryPane'
import { targetNodeToSelection } from './targetNavigation'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { showToast } from '../ui/Toast'
import { useContextSnapshot } from '../context/ContextSnapshotContext'
import { entryPatch, nodePatch, viewPatch } from '../context/contextSnapshot'
import { routeOf, selectionFromSnapshot } from './contextSelection'
import { sanitizeLayout } from './sanitizeLayout'
import { planEntryChange } from './entrySelection'
import { useChiefSlot } from '../ChiefSlotContext'
import {
  LAYOUT_BOUNDS_BY_MODE,
  LAYOUT_DEFAULTS_BY_MODE,
  layoutStorageId,
  panelOrderForMode,
  resolveLayoutMode,
  restoreSlotsForOrder,
} from './layoutMode'
// 拖拽把手:不用负 margin 叠层(旧 -mx 会在窄窗/拖拽时挤乱相邻栏命中区)
const RESIZER_CLASS = 'w-1 shrink-0 bg-transparent cursor-col-resize hover:bg-brand/20 active:bg-brand/30 transition-colors data-[separator]:bg-line/30'
// 还原按钮 = 贴相邻栏缘、垂直居中的细把手（宿主随 panelOrder 变化，不写死 detail）。
const RESTORE_BUTTON_CLASS = 'absolute top-1/2 -translate-y-1/2 z-20 h-14 w-3.5 border-0 bg-surface text-faint shadow-[var(--shadow-panel)] hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer'

function restoreEdgeClass(edge) {
  return edge === 'right'
    ? 'right-0 border-r-0 rounded-l-lg'
    : 'left-0 border-l-0 rounded-r-lg'
}

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

// 四栏钻取壳:栏1 入口 | 栏2 目录 | 详情 + 主编(顺序/宽度随 layoutMode)。
// 模式 phase-auto:大纲/节拍/演绎/草稿/非章 → collaboration(会话主);
// 正文 final / 全画布 view → reading(详情主)。
// 两级选中: entry→栏2; sel→详情 + 主编上下文。
// 唯一布局壳（旧三栏已删除）。
export function FourPaneShell({
  tree, selId, expanded, toggle, onSelectNode, treeCbs, sel, work, reload, onJumpChapter,
  chapterSel, curSeq, leftSeq, onRestored,
}) {
  const [directoryRefresh, setDirectoryRefresh] = useState(0)
  const directoryRef = usePanelRef()
  const rightRef = usePanelRef()
  const [directoryCollapsed, setDirectoryCollapsed] = useState(() => readCollapsed(work, 'directory'))
  // 主编默认展开。不从 localStorage 恢复 rightCollapsed——历史 onResize 误折叠已污染
  // 多书 key，进书若恢复折叠会卸掉 RightDock，作者/e2e 都找不到输入框。
  const [rightCollapsed, setRightCollapsed] = useState(false)
  // 布局 Group 在 key 重挂/进书时会连发 onResize(含瞬时 ~0%)；未就绪时忽略。
  const layoutResizeReadyRef = useRef(false)
  // expand 动画中 size 会短暂 <0.5%；此窗口内禁止 onResize 再写折叠。
  const ignoreRightCollapseUntilRef = useRef(0)
  const { chapterPhase } = useChiefSlot()
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
  // 单一 layoutMode:storage id / defaults / bounds / panel order 全部同源,禁止 early/late 双路径。
  const layoutMode = resolveLayoutMode({
    phase: chapterPhase,
    isView,
    isChapterContext: chapterPhase != null
      || effectiveSel?.node?.type === 'chapter'
      || effectiveSel?.node?.type === 'scene',
  })
  const layoutDefaults = LAYOUT_DEFAULTS_BY_MODE[layoutMode]
  const layoutBounds = LAYOUT_BOUNDS_BY_MODE[layoutMode]
  const panelOrder = panelOrderForMode(layoutMode)
  // 栏宽按 work + mode 隔离(v3);协作/阅读各记一份,旧 v2 detail-primary 不污染协作默认
  const { defaultLayout: rawLayout, onLayoutChanged: persistLayout } = useDefaultLayout({
    id: layoutStorageId(work, layoutMode),
  })
  const defaultLayout = sanitizeLayout(rawLayout, { defaults: layoutDefaults, bounds: layoutBounds })
  const onLayoutChanged = (layout, meta) => {
    persistLayout?.(sanitizeLayout(layout, { defaults: layoutDefaults, bounds: layoutBounds }), meta)
  }
  const restoreSlots = restoreSlotsForOrder(panelOrder, {
    directoryCollapsed,
    rightCollapsed,
    isView,
  })
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
    // 切书：主编强制展开，并清掉该书被污染的折叠位
    ignoreRightCollapseUntilRef.current = Date.now() + 900
    setRightCollapsed(false)
    writeCollapsed(work, 'right', false)
  }, [work])
  // work/mode 切换后短暂关闭 onResize 折叠判定，等 Group 布局稳定
  useEffect(() => {
    layoutResizeReadyRef.current = false
    ignoreRightCollapseUntilRef.current = Date.now() + 900
    setRightCollapsed(false)
    const t = window.setTimeout(() => { layoutResizeReadyRef.current = true }, 600)
    return () => window.clearTimeout(t)
  }, [work, layoutMode])
  useEffect(() => {
    if (isView) return
    if (directoryCollapsed) callPanel(directoryRef.current, 'collapse')
    else callPanel(directoryRef.current, 'expand')
  }, [directoryCollapsed, directoryRef, isView])
  useEffect(() => {
    if (rightCollapsed) callPanel(rightRef.current, 'collapse')
    else {
      ignoreRightCollapseUntilRef.current = Date.now() + 900
      callPanel(rightRef.current, 'expand')
    }
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
    ignoreRightCollapseUntilRef.current = Date.now() + 900
    setRightCollapsed(false)
    writeCollapsed(work, 'right', false)
    callPanel(rightRef.current, 'expand')
  }
  // e2e / 外部：s3-expand-right 强制展开主编（避免仅靠 DOM 点把手失败）
  const expandRightPanelRef = useRef(() => {})
  expandRightPanelRef.current = expandRightPanel
  useEffect(() => {
    const onExpand = () => expandRightPanelRef.current?.()
    window.addEventListener('s3-expand-right', onExpand)
    return () => window.removeEventListener('s3-expand-right', onExpand)
  }, [])
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
    // 图谱等横切视图:写 atlas focus 后切 view(BinderLayout 识别 type=view)
    if (next.viewKey) {
      if (next.atlasFocus) {
        try { sessionStorage.setItem('s3.atlas.focus', String(next.atlasFocus)) } catch { /* */ }
      }
      navigate(viewPatch(next.viewKey))
      onSelectNode?.({ type: 'view', id: `view:${next.viewKey}` })
      return
    }
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
  // 设定删/归档批准落库后:CodexDetail 广播 → 刷树(即使仍在当前详情)
  useEffect(() => {
    const onRefresh = () => handleTreeChanged()
    window.addEventListener('s3-codex-tree-refresh', onRefresh)
    return () => window.removeEventListener('s3-codex-tree-refresh', onRefresh)
  }, [reload])
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

  const renderRestoreButtons = (hostId) => {
    const nodes = []
    if (restoreSlots.directory?.hostId === hostId) {
      const edge = restoreSlots.directory.edge
      nodes.push(
        <button
          key="directory-restore"
          type="button"
          data-testid="directory-restore-button"
          data-restore-host={hostId}
          data-restore-edge={edge}
          aria-label="展开目录"
          title="展开目录"
          onClick={expandDirectory}
          className={`${RESTORE_BUTTON_CLASS} ${restoreEdgeClass(edge)}`}
        >
          {edge === 'right' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
        </button>,
      )
    }
    if (restoreSlots.right?.hostId === hostId) {
      const edge = restoreSlots.right.edge
      nodes.push(
        <button
          key="right-restore"
          type="button"
          data-testid="right-restore-button"
          data-restore-host={hostId}
          data-restore-edge={edge}
          aria-label="展开主编栏"
          title="展开主编栏"
          onClick={expandRightPanel}
          className={`${RESTORE_BUTTON_CLASS} ${restoreEdgeClass(edge)}`}
        >
          {edge === 'right' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
        </button>,
      )
    }
    return nodes
  }

  const renderDirectoryPanel = () => (
    <Panel
      id="directory"
      panelRef={directoryRef}
      defaultSize={`${layoutDefaults.directory}%`}
      minSize={`${layoutBounds.directory.min}%`}
      maxSize={`${layoutBounds.directory.max}%`}
      collapsible
      collapsedSize="0%"
      onResize={(size) => {
        if (!layoutResizeReadyRef.current) return
        // 滞后：<0.5% 才折；>2% 才展。避免 expand 过程中瞬时小值又被压回折叠。
        if (size.asPercentage < 0.5) {
          setDirectoryCollapsed(true)
          writeCollapsed(work, 'directory', true)
        } else if (size.asPercentage > 2) {
          setDirectoryCollapsed(false)
          writeCollapsed(work, 'directory', false)
        }
      }}
      className={cn('border-r border-line/50 bg-surface min-h-0 min-w-0 overflow-hidden')}
    >
      <div
        className="relative h-full min-h-0 min-w-[10rem] max-w-full overflow-hidden"
        data-testid="col-directory-panel"
        data-default-size={String(layoutDefaults.directory)}
        data-min-size={String(layoutBounds.directory.min)}
        data-max-size={String(layoutBounds.directory.max)}
        data-layout-mode={layoutMode}
      >
        {renderRestoreButtons('directory')}
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
  )

  const renderDetailPanel = () => (
    <Panel
      id="detail"
      defaultSize={`${layoutDefaults.detail}%`}
      minSize={isView ? '56%' : `${layoutBounds.detail.min}%`}
      maxSize={`${layoutBounds.detail.max}%`}
      className="relative min-w-0 min-h-0 overflow-hidden flex flex-col"
    >
      <div
        className="relative h-full min-h-0 min-w-0 overflow-hidden flex flex-col"
        data-testid="detail-panel"
        data-layout-mode={layoutMode}
        data-default-size={String(layoutDefaults.detail)}
        data-min-size={String(isView ? 56 : layoutBounds.detail.min)}
        data-max-size={String(layoutBounds.detail.max)}
      >
        {renderRestoreButtons('detail')}
        <div className="h-full min-h-0 min-w-0 overflow-hidden flex flex-col" data-testid="detail" data-context-revision={ctxRevision}>
          <DetailPane sel={effectiveSel} work={work} entryKey={projectedEntryKey}
            onSelectNode={handleSelectItem}
            onTreeChanged={handleTreeChanged} onJumpChapter={onJumpChapter}
            onNavigateToObject={handleNavigateToObject}
            onChapterArchived={handleChapterArchived} />
        </div>
      </div>
    </Panel>
  )

  const renderRightPanel = () => (
    <Panel
      id="right"
      panelRef={rightRef}
      defaultSize={`${layoutDefaults.right}%`}
      minSize={`${layoutBounds.right.min}%`}
      maxSize={`${layoutBounds.right.max}%`}
      collapsible
      collapsedSize="0%"
      onResize={(size) => {
        if (!layoutResizeReadyRef.current) return
        // 同目录：滞后判定，防 expand 过程瞬时小值再次 setRightCollapsed(true)
        if (size.asPercentage > 2) {
          setRightCollapsed(false)
          writeCollapsed(work, 'right', false)
          return
        }
        if (size.asPercentage < 0.5) {
          // expand 守卫窗内禁止误折叠（动画途中 size 会短暂贴近 0）
          if (Date.now() < ignoreRightCollapseUntilRef.current) return
          setRightCollapsed(true)
          writeCollapsed(work, 'right', true)
        }
      }}
      className="border-l border-line/50 bg-surface min-h-0 min-w-0 overflow-hidden"
    >
      <div
        className="relative h-full min-h-0 min-w-0 max-w-full overflow-hidden"
        data-testid="right-panel"
        data-layout-mode={layoutMode}
        data-default-size={String(layoutDefaults.right)}
        data-min-size={String(layoutBounds.right.min)}
        data-max-size={String(layoutBounds.right.max)}
        data-collapsed={rightCollapsed ? '1' : '0'}
      >
        {renderRestoreButtons('right')}
        {!rightCollapsed && (
          <div className="relative h-full min-h-0 min-w-0 max-w-full overflow-hidden" data-testid="right-dock" data-context-revision={ctxRevision}>
            {/* 收起唯一入口：右轨再点当前 tab（主编等）→ onCollapse；不叠右上角浮钮 */}
            <RightDock sel={effectiveSel} chapterSel={chapterSel} seq={curSeq} lastSeq={leftSeq}
              onRestored={onRestored} onCollapse={collapseRightPanel} />
          </div>
        )}
      </div>
    </Panel>
  )

  const panelRenderers = {
    directory: renderDirectoryPanel,
    detail: renderDetailPanel,
    right: renderRightPanel,
  }

  // view 模式隐藏目录;顺序仍按 mode(协作:主编|详情, 阅读:详情|主编)
  const visibleOrder = isView
    ? panelOrder.filter((id) => id !== 'directory')
    : panelOrder

  return (
    <div
      className="h-full min-h-0 flex flex-col bg-canvas overflow-hidden"
      data-testid="four-col"
      data-layout-mode={layoutMode}
    >
      <div className="flex-1 min-h-0 min-w-0 flex overflow-hidden">
        <div className="w-14 shrink-0 bg-surface overflow-hidden shadow-[1px_0_0_0_color-mix(in_srgb,var(--color-line)_70%,transparent)]" data-testid="left-entry-rail">
          <Rail side="left" caps={caps} active={activeCap?.key} onActive={handleActive} />
        </div>
        {/* key=mode:切换协作/阅读时重挂 Group,应用该 mode 的 defaultLayout */}
        <Group
          key={`layout-${layoutMode}-${work || 'main'}`}
          orientation="horizontal"
          defaultLayout={defaultLayout ?? layoutDefaults}
          onLayoutChanged={onLayoutChanged}
          className="flex-1 min-w-0 min-h-0 h-full overflow-hidden"
        >
          {visibleOrder.map((id, i) => (
            <Fragment key={id}>
              {i > 0 && (
                <Separator
                  className={RESIZER_CLASS}
                  data-testid={
                    // 目录后的第一条分隔 = directory-resize; 其余 = right-resize(主编相关)
                    visibleOrder[i - 1] === 'directory' ? 'directory-resize-handle' : 'right-resize-handle'
                  }
                />
              )}
              {panelRenderers[id]()}
            </Fragment>
          ))}
        </Group>
      </div>
    </div>
  )
}

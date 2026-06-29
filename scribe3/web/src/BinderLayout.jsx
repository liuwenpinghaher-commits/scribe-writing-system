import { useCallback, useEffect, useRef, useState } from 'react'
import { Group, Panel, Separator, useDefaultLayout, usePanelRef } from 'react-resizable-panels'
import { PanelLeftOpen } from 'lucide-react'
import { api } from './api'
import { ProjectTree, CONTAINER_TYPES } from './ProjectTree'
import { DetailPane } from './DetailPane'
import { ChiefDock } from './ChiefDock'
import { showToast } from './ui/Toast'

// 收集容器节点 id(默认展开两根 + 各分类容器折叠;手稿支卷默认展开)
function defaultExpanded(tree) {
  const s = new Set(['manuscript_root', 'codex_root'])
  for (const v of tree?.manuscript?.children || []) s.add(v.id)   // 卷默认展开
  return s
}

// 章/场景节点不显示 ChiefDock —— 让位 WriteLayout 内部主编对话(Step1 避免双 chat)
function isChapterSel(sel) {
  if (sel?.mode !== 'node') return false
  const t = sel.node?.type
  return t === 'chapter' || t === 'scene'
}

/**
 * 统一三栏布局(react-resizable-panels v4):
 *   [左 ProjectTree(可折叠)] | [中 DetailPane] | [右 ChiefDock 主编常驻(可折叠,默认开)]
 * sel 单一真相源:{mode:'node', node} | {mode:'view', viewKey},由父层(App)持有。
 * useDefaultLayout 持久化各栏宽度;左/右 collapsible 折叠+展开。
 */
export function BinderLayout({ work, sel, onSel, onJumpChapter }) {
  const [tree, setTree] = useState(null)
  const [expanded, setExpanded] = useState(() => new Set(['manuscript_root', 'codex_root']))
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const initedRef = useRef(false)
  const leftRef = usePanelRef()
  const rightRef = usePanelRef()

  // 布局持久化:panelIds 覆盖含/不含右栏两种布局,避免章/非章切换时漂移。
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: 's3.binder.panels.v4',
    panelIds: ['tree', 'detail', 'chief'],
  })

  const reload = useCallback(() => api.projectTree().then((t) => {
    setTree(t)
    if (!initedRef.current) { setExpanded(defaultExpanded(t)); initedRef.current = true }
  }).catch(() => {}), [])

  useEffect(() => { initedRef.current = false; reload() }, [work])

  // live SSE:别处改数据后服务端推事件 → 防抖 600ms 重拉项目树,保持树/大纲不 stale。
  useEffect(() => {
    let timer = null
    const es = api.live(() => {
      clearTimeout(timer)
      timer = setTimeout(reload, 600)
    }, {
      onGiveUp: () => showToast('实时同步已断开,改动可能不会自动刷新;刷新页面可重连。', { tone: 'danger', duration: 6000 }),
    })
    return () => {
      clearTimeout(timer)
      es.close()
    }
  }, [reload])

  const toggle = (id) => setExpanded((prev) => {
    const n = new Set(prev)
    n.has(id) ? n.delete(id) : n.add(id)
    return n
  })

  const onSelectNode = (node) => {
    if (node.type === 'view') { onSel({ mode: 'view', viewKey: node.id.split(':')[1] }); return }
    onSel({ mode: 'node', node })
  }

  // 卷 CRUD 回调(ProjectTree 发起 → BinderLayout 执行 → 树重载)
  const handleVolumeRename = async (vid, newTitle) => {
    try { await api.patchVolume(vid, { title: newTitle }); reload() } catch (e) { console.error(e) }
  }

  const handleVolumeDelete = async (vid, label) => {
    const vols = tree?.manuscript?.children || []
    const volNode = vols.find((v) => v.ref === vid)
    const chCount = volNode?.children?.length ?? 0
    const msg = chCount > 0
      ? `删除卷「${label}」?\n该卷下 ${chCount} 章将移至「未分卷」(章内容不丢失)。`
      : `删除卷「${label}」?`
    if (!window.confirm(msg)) return
    try { await api.deleteVolume(vid); reload() } catch (e) { console.error(e) }
  }

  const handleAddVolume = async () => {
    const title = window.prompt('新建卷标题:')
    if (!title?.trim()) return
    try {
      const vols = tree?.manuscript?.children || []
      const maxOrder = vols.reduce((m, v) => Math.max(m, v.sort_order ?? 0), 0)
      await api.addVolume(title.trim(), maxOrder + 1)
      reload()
    } catch (e) { console.error(e) }
  }

  // 拖拽重排:章跨卷/卷内排序 → 走 sort_order(及 volume),绝不动 seq。
  // volume = 目标卷裸 id 或 null(未分卷);order = 该卷内章 seq 的全量新序。
  const handleReorder = async (volume, order) => {
    try { await api.reorderChapters(volume, order); reload() } catch (e) { console.error(e) }
  }

  const selId = sel?.mode === 'node' ? sel.node?.id : null
  const chapterSel = isChapterSel(sel)
  // 章节点让位内部 chat(不渲染右栏);其余节点常驻主编。
  const showChief = !chapterSel

  const toggleRight = () => {
    const p = rightRef.current
    if (!p) return
    if (p.isCollapsed()) p.expand(); else p.collapse()
  }
  const expandLeft = () => { leftRef.current?.expand() }

  return (
    <div className="h-full bg-canvas min-h-0">
      <Group orientation="horizontal" defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged} className="h-full">
        {/* 左:项目树(可折叠) */}
        <Panel
          id="tree"
          panelRef={leftRef}
          defaultSize={18} minSize={12} maxSize={32}
          collapsible collapsedSize={0}
          onResize={(size) => setLeftCollapsed(size.asPercentage < 1)}
          className="bg-surface"
        >
          <div className="h-full overflow-hidden">
            <ProjectTree tree={tree} selId={selId} expanded={expanded} onToggle={toggle} onSelect={onSelectNode}
              onVolumeRename={handleVolumeRename}
              onVolumeDelete={handleVolumeDelete}
              onAddVolume={handleAddVolume}
              onReorder={handleReorder} />
          </div>
        </Panel>
        <Separator className="w-px bg-line data-[separator]:hover:bg-brand/50 transition-colors" />

        {/* 中:DetailPane */}
        <Panel id="detail" minSize={30} className="relative min-w-0">
          {/* 左栏折叠时的悬浮展开按钮 */}
          {leftCollapsed && (
            <button onClick={expandLeft} title="展开项目树"
              className="absolute left-2 top-2 z-10 w-7 h-7 rounded-lg bg-surface border border-line text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer shadow-sm">
              <PanelLeftOpen size={15} />
            </button>
          )}
          <main className="h-full min-w-0 overflow-hidden flex flex-col">
            <DetailPane sel={sel} work={work} onSelectNode={onSelectNode}
              onTreeChanged={reload} onJumpChapter={onJumpChapter} />
          </main>
        </Panel>

        {/* 右:ChiefDock 主编常驻(非章节点显示;章节点让位 WriteLayout 内部 chat) */}
        {showChief && (
          <>
            <Separator className="w-px bg-line data-[separator]:hover:bg-brand/50 transition-colors" />
            <Panel
              id="chief"
              panelRef={rightRef}
              defaultSize={26} minSize={16} maxSize={42}
              collapsible collapsedSize={3}
              onResize={(size) => setRightCollapsed(size.asPercentage < 5)}
              className="bg-surface border-l border-line"
            >
              <ChiefDock sel={sel} collapsed={rightCollapsed} onToggle={toggleRight} />
            </Panel>
          </>
        )}
      </Group>
    </div>
  )
}

export { CONTAINER_TYPES }

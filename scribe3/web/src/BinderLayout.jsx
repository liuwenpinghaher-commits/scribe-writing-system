import { useCallback, useEffect, useRef, useState } from 'react'
import { Group, Panel, Separator, usePanelRef } from 'react-resizable-panels'
import { PanelLeftOpen } from 'lucide-react'
import { api } from './api'
import { ProjectTree, CONTAINER_TYPES } from './ProjectTree'
import { DetailPane } from './DetailPane'
import { LeftDock, RightDock } from './studioDocks'
import { RestoreContext } from './WriteLayout'
import { ChiefDock } from './ChiefDock'
import { ChiefSlotProvider } from './ChiefSlotContext'
import { DeduceProvider } from './deduceContext'
import { SelectionProvider, SelMirror } from './selectionContext'
import { showToast } from './ui/Toast'
import { ConfirmDialog, InputDialog } from './ui/Dialog.jsx'

// 收集容器节点 id(默认展开三根 + 各分类容器折叠;手稿支卷默认展开)
function defaultExpanded(tree) {
  const s = new Set(['manuscript_root', 'codex_root', 'material_root'])
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
  const [expanded, setExpanded] = useState(() => new Set(['manuscript_root', 'codex_root', 'material_root']))
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  // F3:右坞「恢复到此版本」→ bump → 经 RestoreContext 通知中区 WriteLayout 重拉本章正文,
  // 恢复即同步编辑器(否则续编辑会用旧内容覆盖刚恢复的版本)。
  const [restoreTick, setRestoreTick] = useState(0)
  const [delVol, setDelVol] = useState(null)   // {vid,label,body} 删卷确认
  const [addingVol, setAddingVol] = useState(false)  // 新建卷输入
  const initedRef = useRef(false)
  const leftRef = usePanelRef()
  const rightRef = usePanelRef()

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

  const handleVolumeDelete = (vid, label) => {
    const vols = tree?.manuscript?.children || []
    const volNode = vols.find((v) => v.ref === vid)
    const chCount = volNode?.children?.length ?? 0
    const body = chCount > 0
      ? `该卷下 ${chCount} 章将移至「未分卷」(章内容不丢失)。`
      : undefined
    setDelVol({ vid, label, body })
  }

  const doVolumeDelete = async () => {
    if (!delVol) return
    try { await api.deleteVolume(delVol.vid); reload() } catch (e) { console.error(e) }
  }

  const handleAddVolume = () => setAddingVol(true)

  const doAddVolume = async (title) => {
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
  // 当前章号(chapter/scene 节点的 ref 即 seq)——喂给右栏数据面板/主编切换。
  const curSeq = chapterSel && sel?.node?.ref != null ? Number(sel.node.ref) : null
  // 块四b 塌栏 UX:左栏数据面板改用「上次章 seq」记忆。点伏笔/母题/角色等非章节点时 curSeq 变 null,
  // 若直接喂 null,左栏(伏笔/母题/帧/演绎/校验)会塌回仅项目树、还把当前 tab 复位掉。改以最近一次的章 seq
  // 喂左栏 → 点行浏览详情时数据面板不被弹出,可继续看该书台账。右栏仍用 curSeq(存档/主编按真实选中切)。
  const lastChapterSeqRef = useRef(null)
  if (curSeq != null) lastChapterSeqRef.current = curSeq
  const leftSeq = curSeq != null ? curSeq : lastChapterSeqRef.current
  const treeCbs = { onVolumeRename: handleVolumeRename, onVolumeDelete: handleVolumeDelete, onAddVolume: handleAddVolume, onReorder: handleReorder }
  // 波B Step3:右栏常驻。章节点 → 右栏=写作槽(WriteLayout 的 WriteChat 经 portal 进来);
  // 非章节点 → 右栏=讨论 chat(现状)。ChiefDock 据 chapterSel 切换内容。
  const showChief = true

  const toggleRight = () => {
    const p = rightRef.current
    if (!p) return
    if (p.isCollapsed()) p.expand(); else p.collapse()
  }
  const expandLeft = () => { leftRef.current?.expand() }

  return (
    <SelectionProvider>
    <ChiefSlotProvider>
    <DeduceProvider>
    {/* 块三:sel(项目树/视图级)变化 → 镜像进通用选中总线 focus(显式聚焦短窗口内避让,见 SelMirror) */}
    <SelMirror sel={sel} />
    <ConfirmDialog
      open={!!delVol}
      title={delVol ? `删除卷「${delVol.label}」?` : ''}
      body={delVol?.body}
      danger
      confirmText="删除"
      onConfirm={doVolumeDelete}
      onClose={() => setDelVol(null)}
    />
    <InputDialog
      open={addingVol}
      title="新建卷"
      placeholder="卷标题…"
      confirmText="创建"
      onConfirm={doAddVolume}
      onClose={() => setAddingVol(false)}
    />
    <RestoreContext.Provider value={restoreTick}>
    <div className="h-full bg-canvas min-h-0">
      <Group orientation="horizontal" defaultLayout={{ left: 22, detail: 52, right: 26 }} className="h-full">
        {/* 左栏:竖图标轨(项目树/帧/演绎/伏笔/素材/校验)+ 面板 —— 项目树与数据面板同栏,消灭独立第4栏 */}
        <Panel
          id="left"
          panelRef={leftRef}
          defaultSize="22%" minSize="15%" maxSize="40%"
          collapsible collapsedSize="0%"
          onResize={(size) => setLeftCollapsed(size.asPercentage < 1)}
          className="bg-surface"
        >
          <LeftDock tree={tree} selId={selId} expanded={expanded} onToggle={toggle} onSelect={onSelectNode}
            treeCbs={treeCbs} seq={leftSeq} />
        </Panel>
        <Separator className="relative w-2 -mx-[3.5px] bg-transparent cursor-col-resize data-[separator]:hover:bg-brand/20 transition-colors after:absolute after:inset-y-0 after:left-1/2 after:-translate-x-1/2 after:w-px after:bg-line" />

        {/* 中栏:编辑器(章导航 + 四阶段 tab + 阶段编辑器) */}
        <Panel id="detail" minSize="34%" className="relative min-w-0">
          {leftCollapsed && (
            <button onClick={expandLeft} title="展开左栏"
              className="absolute left-2 top-2 z-10 w-7 h-7 rounded-lg bg-surface border border-line text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer shadow-sm">
              <PanelLeftOpen size={15} />
            </button>
          )}
          <main className="h-full min-w-0 overflow-hidden flex flex-col">
            <DetailPane sel={sel} work={work} onSelectNode={onSelectNode}
              onTreeChanged={reload} onJumpChapter={onJumpChapter} />
          </main>
        </Panel>
        <Separator className="relative w-2 -mx-[3.5px] bg-transparent cursor-col-resize data-[separator]:hover:bg-brand/20 transition-colors after:absolute after:inset-y-0 after:left-1/2 after:-translate-x-1/2 after:w-px after:bg-line" />

        {/* 右栏:面板(主编/存档)+ 竖图标轨(镜像) */}
        <Panel
          id="right"
          panelRef={rightRef}
          defaultSize="26%" minSize="18%" maxSize="44%"
          collapsible collapsedSize="0%"
          onResize={(size) => setRightCollapsed(size.asPercentage < 5)}
          className="bg-surface border-l border-line"
        >
          <RightDock sel={sel} chapterSel={chapterSel} seq={curSeq}
            onRestored={() => setRestoreTick((t) => t + 1)} />
        </Panel>
      </Group>
    </div>
    </RestoreContext.Provider>
    </DeduceProvider>
    </ChiefSlotProvider>
    </SelectionProvider>
  )
}

export { CONTAINER_TYPES }

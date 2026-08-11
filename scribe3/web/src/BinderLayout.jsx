import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import {
  seedChiefNarrativeWrite,
  seedChiefReorderChapters,
  seedChiefDeleteVolume,
} from './lib/chiefSeed.js'
import { CONTAINER_TYPES } from './ProjectTree'
import { buildPropositionCategory } from './codexTree'
import { RestoreContext } from './WriteLayout'
import { ChiefSlotProvider } from './ChiefSlotContext'
import { DeduceProvider } from './deduceContext'
import { SelectionProvider, SelMirror } from './selectionContext'
import { showToast } from './ui/Toast'
import { ConfirmDialog, InputDialog } from './ui/Dialog.jsx'
import { FourPaneShell } from './layout/FourPaneShell'
import { ContextSnapshotProvider } from './context/ContextSnapshotContext'

// 批D 件1:命题分类扫描章。命题(proposition)是章级时态数据(valid_from/valid_to),
// 用大哨兵章拉「当前仍开区间」的全部命题投影进项目树(与 DynamicRelations 的 chapter=9999 同范式)。
const PROP_SCAN_CHAPTER = 100000

// 收集容器节点 id。entity_first：设定库着陆展开主分类，**不**展开世界真相(cat:proposition)。
// 刷新不持久化 open（每次首载 defaultExpanded；用户手动展开仅会话内）。
const ENTITY_FIRST_OPEN_CATS = new Set([
  'character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif',
])

function defaultExpanded(tree) {
  const s = new Set(['manuscript_root', 'codex_root', 'material_root'])
  for (const v of tree?.manuscript?.children || []) s.add(v.id)   // 卷默认展开
  for (const c of tree?.codex?.children || []) {
    const ref = c.ref || (c.id || '').replace(/^cat:/, '')
    // 世界真相 / proposition：默认折叠（KD-16）
    if (ref === 'proposition') continue
    if (ENTITY_FIRST_OPEN_CATS.has(ref) || c.id === `cat:${ref}`) {
      if (c.id) s.add(c.id)
    }
  }
  return s
}

// 章/场景节点不显示 ChiefDock —— 让位 WriteLayout 内部主编对话(Step1 避免双 chat)
function isChapterSel(sel) {
  if (sel?.mode !== 'node') return false
  const t = sel.node?.type
  return t === 'chapter' || t === 'scene'
}

/**
 * 作品写作台壳：唯一布局为四栏（入口轨 | 目录 | 详情 | 主编）。
 * 旧三栏（LeftDock + DetailPane + RightDock + s3.layout.v2 flag）已移除。
 * sel 单一真相源:{mode:'node', node} | {mode:'view', viewKey},由父层(App)持有。
 */
export function BinderLayout({ work, sel, onSel, onJumpChapter, onWorkflowContinue }) {
  const [tree, setTree] = useState(null)
  const [expanded, setExpanded] = useState(() => new Set(['manuscript_root', 'codex_root', 'material_root']))
  // F3:右坞「恢复到此版本」→ bump → 经 RestoreContext 通知中区 WriteLayout 重拉本章正文,
  // 恢复即同步编辑器(否则续编辑会用旧内容覆盖刚恢复的版本)。
  const [restoreTick, setRestoreTick] = useState(0)
  const [delVol, setDelVol] = useState(null)   // {vid,label,body} 删卷确认
  const [addingVol, setAddingVol] = useState(false)  // 新建卷输入
  const initedRef = useRef(false)

  const reload = useCallback(() => Promise.all([
    api.projectTree(),
    api.facts(PROP_SCAN_CHAPTER).catch(() => []),   // 命题分类:后端 /project-tree 不含,前端注入
  ]).then(([t, facts]) => {
    // 批D 件1:把「命题」分类注入设定支(幂等 —— 已注入则不重复;live SSE 每次重拉都重建)。
    if (t?.codex?.children && !t.codex.children.some((c) => c.ref === 'proposition')) {
      t.codex.children.push(buildPropositionCategory(facts))
    }
    setTree(t)
    if (!initedRef.current) { setExpanded(defaultExpanded(t)); initedRef.current = true }
  }).catch(() => {}), [])

  useEffect(() => { initedRef.current = false; reload() }, [work])

  // live SSE:别处改数据后服务端推事件 → 防抖 600ms 重拉项目树,保持树/大纲不 stale。
  useEffect(() => {
    let timer = null
    const es = api.live((ev) => {
      // 评分卡/作品意图等面板订阅 s3-live；单 SSE 复用（SCRIBE3_LIVE_MAX 配额）。
      // S-8：透传 table/action/id，供面板按 id 精准刷新。
      try { window.dispatchEvent(new CustomEvent('s3-live', { detail: ev })) } catch { /* */ }
      clearTimeout(timer)
      // 项目树：结构相关表全量重拉；仅带无关表时仍刷新（树聚合多表），id 留给叶子面板
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
    if (!node) { onSel({ mode: 'node', node: null }); return }
    if (node.type === 'view') { onSel({ mode: 'view', viewKey: node.id.split(':')[1] }); return }
    onSel({ mode: 'node', node })
  }

  // 卷重命名:叙事 title 走主编种子(禁止 patchVolume 作者直写)
  const handleVolumeRename = async (vid, newTitle) => {
    seedChiefNarrativeWrite('volume', `分卷 ${vid}`, `请将卷名更新为: ${newTitle}`)
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
    seedChiefDeleteVolume(delVol.vid, delVol.label)
  }

  const handleAddVolume = () => setAddingVol(true)

  const addVolInflight = useRef(false)   // 断头修复#84:确认对话框双击/双触发 → 建两个同名卷
  const doAddVolume = (title) => {
    if (!title?.trim() || addVolInflight.current) return
    addVolInflight.current = true
    try {
      const vols = tree?.manuscript?.children || []
      const maxOrder = vols.reduce((m, v) => Math.max(m, v.sort_order ?? 0), 0)
      // 禁止 api.addVolume REST 直写;主编 s3_add_volume 审批落库
      seedChiefNarrativeWrite(
        'volume',
        `新建分卷「${title.trim()}」`,
        `请用 s3_add_volume 创建卷 title=${title.trim()}, sort_order=${maxOrder + 1}。未获批准不得声称已落库。`,
      )
    } finally {
      addVolInflight.current = false
    }
  }

  // 拖拽重排:章跨卷/卷内排序 → 走 sort_order(及 volume),绝不动 seq。
  // volume = 目标卷裸 id 或 null(未分卷);order = 该卷内章 seq 的全量新序。
  const handleReorder = async (volume, order) => {
    seedChiefReorderChapters(volume, order)
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
      {/* 统一上下文快照：切书(work)重建会话；建不起来时 Provider 降级本地直通 */}
      <ContextSnapshotProvider work={work}>
        <FourPaneShell
          tree={tree}
          selId={selId}
          expanded={expanded}
          toggle={toggle}
          onSelectNode={onSelectNode}
          treeCbs={treeCbs}
          leftSeq={leftSeq}
          sel={sel}
          work={work}
          reload={reload}
          onJumpChapter={onJumpChapter}
          chapterSel={chapterSel}
          curSeq={curSeq}
          onRestored={() => setRestoreTick((t) => t + 1)}
          onWorkflowContinue={onWorkflowContinue}
        />
      </ContextSnapshotProvider>
    </div>
    </RestoreContext.Provider>
    </DeduceProvider>
    </ChiefSlotProvider>
    </SelectionProvider>
  )
}

export { CONTAINER_TYPES }

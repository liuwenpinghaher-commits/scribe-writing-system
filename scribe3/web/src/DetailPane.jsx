import { ChapterStudio } from './ChapterStudio'
import { CodexDetail } from './CodexDetail'
import { CodexNew } from './CodexNew'
import { MaterialDetail, MaterialList, MaterialNew } from './Materials'
import { AtlasView } from './views/AtlasView'
import { InsightView } from './views/InsightView'
import { OverviewView } from './views/OverviewView'
import { TimelineView } from './views/TimelineView'
import { ContainerOutline } from './ContainerOutline'
import { ErrorBoundary } from './ErrorBoundary'

// 素材分类 ref → 新建条目对应的叶节点 type(用于创建后选中)
const CAT_LEAF_TYPE = {
  character: 'character', faction: 'faction', item: 'item', term: 'term',
  world_rule: 'world_rule', promise: 'promise', motif: 'motif',
}

const CODEX_LEAF = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif'])
const CONTAINER = new Set(['manuscript_root', 'codex_root', 'volume', 'codex_category'])
// 手稿容器(卷/手稿根)→ 章卡片墙/大纲表多模式;其余容器(素材分类)→ 子项列表
const MANUSCRIPT_CONTAINER = new Set(['manuscript_root', 'volume'])

// 把卡片/行点击的章 → 章 TreeNode(与 WriteLayout.onSeqChange 同形),选中后中间栏切写作台
const chapterNode = (seq, title = '') => ({ id: `ch:${seq}`, type: 'chapter', ref: seq, label: `${seq} ${title}`.trim() })

/**
 * 中间栏:按 sel 路由。
 *  - mode==='view'      → 横切视图(图谱/时间线/仪表盘/进度/概览)
 *  - node.type 章/场景  → 完整写作台 WriteLayout(传 seq)
 *  - node.type 素材叶   → CodexDetail 详情卡
 *  - node.type 容器     → 子项列表(MVP)
 */
export function DetailPane(props) {
  // 崩溃隔离:整个中区路由包一层 ErrorBoundary。key 用能标识当前视图/章的值
  // (横切视图=viewKey,节点=node.id),切换视图/章时 key 变化 → React 重建边界 → 清掉错误态自恢复。
  const { sel } = props
  const boundaryKey = sel?.mode === 'view'
    ? `view:${sel.viewKey}`
    : (sel?.node?.id ?? 'empty')
  return (
    <ErrorBoundary key={boundaryKey}>
      {renderDetail(props)}
    </ErrorBoundary>
  )
}

function renderDetail({ sel, work, onSelectNode, onTreeChanged, onJumpChapter }) {
  // —— 横切视图 ——
  if (sel?.mode === 'view') {
    const k = sel.viewKey
    const openView = (vk) => onSelectNode?.({ type: 'view', id: `view:${vk}` })
    if (k === 'atlas') return <AtlasView key={work} />
    if (k === 'insight') return <InsightView key={work} onJumpChapter={onJumpChapter} />
    if (k === 'timeline') return <TimelineView key={work} onJumpChapter={onJumpChapter} />
    if (k === 'overview') return <OverviewView key={work} onJumpChapter={onJumpChapter} onOpenView={openView} />
    if (k === 'progress') return <InsightView key={`${work}-progress`} onJumpChapter={onJumpChapter} focus="progress" />  // 仪表盘聚焦码字进度面板
    return <div className="p-8 text-faint">未实现的视图:{k}</div>
  }

  const node = sel?.node
  if (!node) {
    return (
      <div className="h-full grid place-items-center text-f13 text-faint/60">
        从左侧项目树选一个章开始写,或选一个设定项查看详情。
      </div>
    )
  }

  // —— 章 / 场景 → 章工作台(四阶段 tab:大纲/节拍/草稿/正文;正文复用 WriteLayout)——
  // 场景:正文是单一编辑器 blob,无场景级 DOM 锚点,暂无法滚到具体场景;
  // 点场景即打开其所属章(正确章,非假跳),并把 idx 透传给 ChapterStudio 供未来定位。
  if (node.type === 'chapter' || node.type === 'scene') {
    const seq = node.type === 'scene' ? node.ref?.seq : node.ref
    const sceneIdx = node.type === 'scene' ? node.ref?.idx : null
    return <ChapterStudio key={work} work={work} seq={seq} sceneIdx={sceneIdx}
      onSeqChange={(s) => onSelectNode?.({ id: `ch:${s}`, type: 'chapter', ref: s, label: `${s}` })} />
  }

  // —— 素材新建 → 新建表单(创建后重载树并选中新条目) ——
  if (node.type === 'codex_new') {
    const cat = node.ref
    return <CodexNew key={node.id} catType={cat} label={node.label}
      onCancel={() => onSelectNode?.({ id: `cat:${cat}`, type: 'codex_category', ref: cat, label: node.label })}
      onCreated={(catType, ref) => {
        onTreeChanged?.()
        const leafType = CAT_LEAF_TYPE[catType]
        if (leafType && ref != null) {
          onSelectNode?.({ id: `${leafType}:${ref}`, type: leafType, ref, label: String(ref) })
        } else {
          onSelectNode?.({ id: `cat:${catType}`, type: 'codex_category', ref: catType, label: node.label })
        }
      }} />
  }

  // —— 素材库(非正典材料,块四a-1)——
  if (node.type === 'material_new') {
    const kind = node.ref || 'note'
    const backToCat = () => onSelectNode?.({ id: `matcat:${kind}`, type: 'material_category', ref: kind, label: node.label })
    return <MaterialNew key={node.id} kind={kind}
      onCancel={backToCat}
      onCreated={(mid, title) => {
        onTreeChanged?.()
        if (mid != null) onSelectNode?.({ id: `material:${mid}`, type: 'material', ref: mid, label: title || String(mid) })
        else backToCat()
      }} />
  }
  if (node.type === 'material') {
    return <MaterialDetail key={node.id} node={node} onChanged={onTreeChanged}
      onDeleted={() => {
        onTreeChanged?.()
        const kind = node.meta?.kind
        onSelectNode?.(kind
          ? { id: `matcat:${kind}`, type: 'material_category', ref: kind, label: '素材' }
          : { id: 'material_root', type: 'material_root', ref: null, label: '素材库' })
      }} />
  }
  if (node.type === 'material_root' || node.type === 'material_category') {
    return <MaterialList key={node.id} node={node} onSelect={onSelectNode} />
  }

  // —— 素材叶 → 详情卡 ——
  if (CODEX_LEAF.has(node.type)) {
    return <CodexDetail key={node.id} node={node} onChanged={onTreeChanged} onDeleted={onTreeChanged} />
  }

  // —— 手稿容器(卷/手稿根)→ 卡片墙/大纲表多模式 ——
  if (MANUSCRIPT_CONTAINER.has(node.type)) {
    return <ContainerOutline key={node.id} node={node}
      onOpenChapter={(c) => onSelectNode?.(chapterNode(c.seq, c.title))}
      onSelect={onSelectNode} />
  }

  // —— 其余容器(素材分类)→ 子项列表 ——
  if (CONTAINER.has(node.type)) {
    return <ContainerOutline key={node.id} node={node} onSelect={onSelectNode}
      onOpenChapter={(c) => onSelectNode?.(chapterNode(c.seq, c.title))} />
  }

  return <div className="p-8 text-faint">未知节点类型:{node.type}</div>
}

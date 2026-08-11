import { lazy, Suspense } from 'react'
import { CodexNew } from './CodexNew'
import { MaterialDetail, MaterialImportPane, MaterialNetworkPane, MaterialNew } from './Materials'
import { ErrorBoundary } from './ErrorBoundary'
import { ContainerOutline } from './ContainerOutline'
import { NorthStarPanel } from './NorthStarPanel'
import { VolumeDetailPane } from './layout/VolumeDetailPane'
import { ObjectFrame } from './layout/ObjectFrame'
import { presentationForNode } from './layout/objectRegistry'
import { ReferenceWorks } from './quality/ReferenceWorks'
import { QualityReview } from './quality/QualityReview'
import { emptyDetailCopy } from './layout/entrySelection'

const lazyNamed = (load, name) => lazy(() => load().then((mod) => ({ default: mod[name] })))
const ChapterStudio = lazyNamed(() => import('./ChapterStudio'), 'ChapterStudio')
const CodexDetail = lazyNamed(() => import('./CodexDetail'), 'CodexDetail')
const PropositionDetail = lazyNamed(() => import('./CodexDetail'), 'PropositionDetail')
const CapabilityGroupDetailPane = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'CapabilityGroupDetailPane')
const DeduceDetailPane = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'DeduceDetailPane')
const MotifDetailPane = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'MotifDetailPane')
const PromiseDetailPane = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'PromiseDetailPane')
const RecallResultDetail = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'RecallResultDetail')
const ReviewIssueDetail = lazyNamed(() => import('./layout/CapabilityDetailPanes'), 'ReviewIssueDetail')
const QualityContractEditor = lazyNamed(() => import('./quality/QualityContractEditor'), 'QualityContractEditor')
const AtlasView = lazyNamed(() => import('./views/AtlasView'), 'AtlasView')
const InsightView = lazyNamed(() => import('./views/InsightView'), 'InsightView')
const OverviewView = lazyNamed(() => import('./views/OverviewView'), 'OverviewView')
const TimelineView = lazyNamed(() => import('./views/TimelineView'), 'TimelineView')
const JourneyView = lazyNamed(() => import('./views/JourneyView'), 'JourneyView')
const CanonInboxView = lazyNamed(() => import('./views/CanonInboxView'), 'CanonInboxView')
const StorylineHub = lazyNamed(() => import('./views/StorylineHub'), 'StorylineHub')
const BenchmarkLibrary = lazyNamed(() => import('./views/BenchmarkLibrary'), 'BenchmarkLibrary')
const EventGraphPanel = lazyNamed(() => import('./views/EventGraphPanel'), 'EventGraphPanel')

function DetailLoading() {
  return <div className="h-full grid place-items-center text-f13 text-faint/60">加载视图…</div>
}

// 对象外框包裹:仅当 presentationForNode(node) 有呈现数据(chapter/character/material 三类)才套 ObjectFrame。
// 本 Task 只包 character/material(见下方两条分支调用),章节留给 Task 7;其余类型 presentationForNode 返回 null,
// withFrame 原样返回详情元素——从而「谁套外框」只有一处真相,不散落 if 判断。
// 注意:内层详情组件的 props 一律不改(外框只是外层壳),写作/设定/素材现有逻辑零回归。
function withFrame(node, element) {
  const pres = presentationForNode(node)
  if (!pres) return element
  return (
    <ObjectFrame breadcrumb={pres.breadcrumb} title={pres.title}>
      {element}
    </ObjectFrame>
  )
}

// 设定分类 ref → 新建条目对应的叶节点 type(用于创建后选中)
const CAT_LEAF_TYPE = {
  character: 'character', faction: 'faction', item: 'item', term: 'term',
  world_rule: 'world_rule', promise: 'promise', motif: 'motif', proposition: 'proposition',
}

const CODEX_LEAF = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif'])
const CONTAINER = new Set(['manuscript_root', 'codex_root', 'codex_category', 'material_root', 'material_category'])

/**
 * 中间栏:按 sel 路由。
 *  - mode==='view'      → 横切视图(图谱/时间线/仪表盘/进度/概览)
 *  - node.type 章/场景  → 完整写作台 WriteLayout(传 seq)
 *  - node.type 设定叶   → CodexDetail 详情卡
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
    <div className="h-full min-h-0 flex flex-col overflow-hidden" data-testid="detail-pane-root">
      <ErrorBoundary key={boundaryKey}>
        <Suspense fallback={<DetailLoading />}>
          {renderDetail(props)}
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}

function renderDetail({ sel, work, onSelectNode, onTreeChanged, onJumpChapter, onNavigateToObject, onChapterArchived, entryKey, qualitySeq, onWorkflowContinue }) {
  // onNavigateToObject: 设定详情「在图谱中打开」等跨栏定位(须透传 CodexDetail)
  // —— 横切视图 ——
  if (sel?.mode === 'view') {
    const k = sel.viewKey
    const openView = (vk) => onSelectNode?.({ type: 'view', id: `view:${vk}` })
    if (k === 'atlas') return <AtlasView key={work} onNavigateToObject={onNavigateToObject} />
    if (k === 'insight') return <InsightView key={work} onJumpChapter={onJumpChapter} onNavigateToObject={onNavigateToObject} />
    if (k === 'timeline') return <TimelineView key={work} onJumpChapter={onJumpChapter} onNavigateToObject={onNavigateToObject} />
    if (k === 'overview') return <OverviewView key={work} onJumpChapter={onJumpChapter} onOpenView={openView} />
    if (k === 'journey') {
      return (
        <JourneyView
          key={work}
          work={work}
          onJumpChapter={onJumpChapter}
          onContinue={onWorkflowContinue}
          onOpenView={openView}
        />
      )
    }
    if (k === 'canon-inbox') {
      return (
        <CanonInboxView
          key={`${work}-canon-inbox`}
          work={work}
          onJumpChapter={onJumpChapter}
        />
      )
    }
    if (k === 'settings') return <div className="p-8 text-f13 text-faint" data-testid="settings-moved">设置已迁至顶栏「系统中心」（全页）。请点齿轮打开。</div>
    if (k === 'progress') return <InsightView key={`${work}-progress`} onJumpChapter={onJumpChapter} onNavigateToObject={onNavigateToObject} focus="progress" />  // 仪表盘聚焦码字进度面板
    if (k === 'storyline') return <StorylineHub key={`${work}-storyline`} work={work} />
    if (k === 'benchmarks') return <BenchmarkLibrary key={`${work}-benchmarks`} />
    if (k === 'event-graph') return <EventGraphPanel key={`${work}-event-graph`} work={work} />
    return <div className="p-8 text-faint">未实现的视图:{k}</div>
  }

  const node = sel?.node
  if (!node) {
    const copy = emptyDetailCopy(entryKey)
    return (
      <div className="h-full grid place-items-center text-center px-6 text-f13 text-faint/60" data-testid="detail-empty">
        <div>
          <div className="text-ink/70 mb-1">{copy.title}</div>
          <div>{copy.hint}</div>
        </div>
      </div>
    )
  }

  if (node.type === 'book_outline') {
    return <ContainerOutline key="book:outline" node={{ id: 'manuscript_root', type: 'manuscript_root', ref: null, label: '全书大纲' }} onSelect={onSelectNode}
      onOpenChapter={(c) => onSelectNode?.({ id: `ch:${c.seq}`, type: 'chapter', ref: c.seq, label: `${c.seq} ${c.title || ''}`.trim(), phase: 'outline' })} />
  }
  if (node.type === 'book_northstar') return <NorthStarPanel scope="book" />
  if (node.type === 'volume') return <VolumeDetailPane key={node.id} node={node} onSelectNode={onSelectNode} onChanged={onTreeChanged} />

  if (node.type === 'capability_group') return <CapabilityGroupDetailPane key={node.id} node={node} />
  if (node.type === 'deduce_view') return <DeduceDetailPane key={node.id} node={node} work={work} />
  if (node.type === 'promise_view') return <PromiseDetailPane key={node.id} node={node} work={work} />
  if (node.type === 'motif_view') return <MotifDetailPane key={node.id} node={node} work={work} />
  if (node.type === 'recall_result') return <RecallResultDetail key={node.id} node={node} onOpenTarget={onNavigateToObject || onSelectNode} />
  // 无真实 recheck 实现时不传 handler，IssueDetail 不渲染假「重新检查」按钮
  if (node.type === 'review_issue') return <ReviewIssueDetail key={node.id} node={node} onLocate={onNavigateToObject || onSelectNode} />
  if (node.type === 'references') return <ReferenceWorks key={node.id} work={work} />
  // 质量工作台是作品级入口，目录节点本身不带 seq；沿用本书最近一次明确选择的
  // 章节，让作者从手稿切到质量审阅时不必重复输入章节号。
  if (node.type === 'quality_review') return <QualityReview key={node.id} work={work} seq={node.ref?.seq ?? node.meta?.seq ?? qualitySeq} onLocateEvidence={onNavigateToObject} />
  if (node.type === 'quality_contract') return <QualityContractEditor key={node.id} work={work} />

  // —— 章 / 场景 → 章工作台(四阶段 tab:大纲/节拍/草稿/正文;正文复用 WriteLayout)——
  // 场景:正文是单一编辑器 blob,无场景级 DOM 锚点,暂无法滚到具体场景;
  // 点场景即打开其所属章(正确章,非假跳),并把 idx 透传给 ChapterStudio 供未来定位。
  if (node.type === 'chapter' || node.type === 'scene') {
    const seq = node.type === 'scene' ? node.ref?.seq : node.ref
    const sceneIdx = node.type === 'scene' ? node.ref?.idx : null
    return <ChapterStudio key={work} work={work} seq={seq} sceneIdx={sceneIdx} initialPhase={node.phase}
      onSelectNode={onSelectNode}
      onSeqChange={(s) => onSelectNode?.({ id: `ch:${s}`, type: 'chapter', ref: s, label: `${s}` })}
      onArchived={onChapterArchived} />
  }

  // —— 设定新建 → 新建表单(创建后重载树并选中新条目) ——
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
  if (node.type === 'material_import') {
    const backToMaterials = () => onSelectNode?.({ id: 'material_root', type: 'material_root', ref: null, label: '素材库' })
    return <MaterialImportPane key={node.id}
      onCancel={backToMaterials}
      onImported={() => {
        onTreeChanged?.()
        backToMaterials()
      }} />
  }
  if (node.type === 'material_network') {
    return <MaterialNetworkPane key={node.id} onSelect={onSelectNode} />
  }
  if (node.type === 'material') {
    return withFrame(node, <MaterialDetail key={node.id} node={node} onChanged={onTreeChanged}
      onDeleted={() => {
        onTreeChanged?.()
        const kind = node.meta?.kind
        onSelectNode?.(kind
          ? { id: `matcat:${kind}`, type: 'material_category', ref: kind, label: '素材' }
          : { id: 'material_root', type: 'material_root', ref: null, label: '素材库' })
      }} />)
  }
  if (node.type === 'material_root' || node.type === 'material_category') return <ContainerDetailEmpty node={node} />

  // —— 命题叶(批D 件1)→ 独立安全详情块(不走 DetailView 整行 PATCH,防私密值/leak_markers 被有损回写抹掉) ——
  if (node.type === 'proposition') {
    return <PropositionDetail key={node.id} node={node} onChanged={onTreeChanged}
      onNavigateToObject={onNavigateToObject}
      onDeleted={() => { onTreeChanged?.(); onSelectNode?.({ id: 'cat:proposition', type: 'codex_category', ref: 'proposition', label: '命题' }) }} />
  }

  // —— 设定叶 → 详情卡(character 套对象外框;faction/item/term/world_rule/promise/motif 暂不套,
  //    由 withFrame 内 presentationForNode 判定:仅 character 有呈现数据 → 只有它被包)——
  if (CODEX_LEAF.has(node.type)) {
    return withFrame(node, (
      <CodexDetail
        key={node.id}
        node={node}
        onChanged={onTreeChanged}
        onDeleted={onTreeChanged}
        onNavigateToObject={onNavigateToObject}
      />
    ))
  }

  // —— 容器只驱动栏2目录;栏3只承载条目详情/横切视图 ——
  if (CONTAINER.has(node.type)) return <ContainerDetailEmpty node={node} />

  return <div className="p-8 text-faint">未知节点类型:{node.type}</div>
}

function ContainerDetailEmpty({ node }) {
  return (
    <div className="h-full grid place-items-center text-center px-6 text-f13 text-faint/60">
      <div>
        <div className="text-ink/70 mb-1">{node?.label || '目录'}</div>
        <div>选择目录条目查看详情。</div>
      </div>
    </div>
  )
}

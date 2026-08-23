import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Compass, FolderTree, Eye, Sparkles, Bookmark, LayoutList, ShieldCheck, MessageSquare, Archive, TriangleAlert, Check, ScrollText, Gauge, Loader2, Search, BookOpen, Library } from 'lucide-react'
import { Rail } from './shell'
import { cn } from './lib/utils'
import { api } from './api'
import { Empty, Tag, SectionTitle, Skeleton } from './ui'
import { ProjectTree } from './ProjectTree'
import { BriefPanel } from './BriefPanel'
import { NorthStarPanel } from './NorthStarPanel'
import { resolveRightTab } from './lib/chiefMode'
import { useChiefSlot } from './ChiefSlotContext'
import { FramePanel } from './FramePanel'
import { DeduceTree } from './DeduceTree'
import { VersionPanel } from './VersionPanel'
import { ChiefDock } from './ChiefDock'
import { ErrorBoundary } from './ErrorBoundary'
import { usePref } from './lib/usePref'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { useToast, showToast } from './ui/Toast.jsx'
import { useSelection } from './selectionContext'
import { useWorkScopedPref } from './hooks/useWorkScopedPref'
import { SearchDirectory } from './capabilities/search/SearchDirectory'
import { IssueDirectory } from './capabilities/issues/IssueDirectory'
import { ReferenceWorks } from './quality/ReferenceWorks'
import { liveTouchesChapter, liveTouchesTable } from './lib/liveRefresh.js'

// 三栏写作台的「左栏」:VSCode 式竖图标轨 + 一个面板。图标切换:项目树/帧/演绎/伏笔/母题/校验。
// 项目树是第一个 tab(默认),数据面板并列其后 —— 消灭独立第4栏,导航与数据同栏。
export function useLeftDockCapabilities({
  tree, selId, expanded, onToggle, onSelect, treeCbs, seq,
  includeStageTabs = true, splitProjectRoots = false, renderMaterialRoot, work = 'main',
}) {
  const [tab, setTab] = useWorkScopedPref(work, 'leftTab', splitProjectRoots ? 'manuscript' : 'tree')
  const [focalizer, setFocalizer] = useState('')
  const [ledger, setLedger] = useState(undefined)   // undefined=加载中/未知,null=加载失败,object=数据
  const [motifs, setMotifs] = useState([])

  useEffect(() => {
    let cancelled = false
    const pullLedger = () => {
      api.promisesLedger(work)
        .then((l) => { if (!cancelled) setLedger(l && typeof l === 'object' ? l : {}) })
        .catch(() => { if (!cancelled) setLedger(null) })
    }
    const pullMotifs = () => {
      api.motifs(work)
        .then((m) => { if (!cancelled) setMotifs(Array.isArray(m) ? m : []) })
        .catch(() => {})
    }
    setLedger(undefined)
    pullLedger()
    pullMotifs()
    const onLive = (e) => {
      const d = e?.detail || {}
      if (liveTouchesTable(d, ['promise', 'foreshadow'])) pullLedger()
      if (liveTouchesTable(d, ['motif'])) pullMotifs()
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      cancelled = true
      window.removeEventListener('s3-live', onLive)
    }
  }, [seq, work])
  useEffect(() => {
    if (seq == null) { setFocalizer(''); return }
    let cancelled = false
    const pull = () => api.chapter(seq, work)
      .then((ch) => { if (!cancelled) setFocalizer(ch?.focalizer || '') })
      .catch(() => { if (!cancelled) setFocalizer('') })
    pull()
    // 断头修复#14(focalizer 双源):顶栏改视角存稿后 chapter 表变更经 s3-live 推送——
    // 监听重拉,左栏帧面板不再按库中旧视角渲染(文档明令避免的"各自拉取不一致")。
    // S-8: 有 id 时仅本章刷新，避免他章 LIVE 刷爆左栏。
    const onLive = (e) => {
      if (liveTouchesChapter(e?.detail, seq)) pull()
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      cancelled = true
      window.removeEventListener('s3-live', onLive)
    }
  }, [seq, work])

  const caps = useMemo(() => {
    // bare:true 的面板自带内边距/需边到边(项目树/演绎树),不套统一 p-3;其余数据面板走容器统一 padding。
    const projectTree = (subtree) => (
      <div className="h-full overflow-hidden">
        <ProjectTree tree={subtree} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} {...treeCbs} />
      </div>
    )
    // Task 3 · 入口分组:group 字段驱动左轨的「内容/工艺/检查」三组渲染。
    //   content=可导航的内容根(手稿/设定库/素材库,拆分前是项目树+简报)
    //   craft  =工艺构建工具(帧/演绎/伏笔/母题,拆分前含北极星)
    //   inspect=检查工具(搜索；校验台账不再占一等入口，深链仍可进)
    // 全部入口都标了组:非拆分旧 LeftDock 的 tree/brief/northstar/frame 也各归其组,
    // 分组渲染后顺序与旧版逐项一致(见 GROUPS 顺序),不因分组丢入口、不乱序。
    const base = splitProjectRoots ? [
      { key: 'manuscript', icon: BookOpen, bare: true, group: 'content', label: '手稿', render: () => projectTree({ manuscript: tree?.manuscript }) },
      { key: 'codex', icon: FolderTree, bare: true, group: 'content', label: '设定库', render: () => projectTree({ codex: tree?.codex }) },
      { key: 'materials', icon: Archive, bare: true, group: 'content', label: '素材库', render: () => (
        renderMaterialRoot
          ? renderMaterialRoot(tree?.materials || { id: 'material_root', type: 'material_root', label: '素材库' })
          : projectTree({ materials: tree?.materials })
      ) },
    ] : [
      { key: 'tree', icon: FolderTree, bare: true, group: 'content', label: '项目树', render: () => projectTree(tree) },
    ]
    base.push({ key: 'references', icon: Library, bare: true, group: 'content', label: '技法标尺', render: () => <ReferenceWorks work={work} /> })
    if (includeStageTabs) {
      base.push(
        { key: 'brief', icon: ScrollText, group: 'content', label: '简报', render: () => <BriefPanel seq={seq} /> },
        { key: 'northstar', icon: Compass, group: 'craft', label: '北极星', render: () => <NorthStarPanel seq={seq} /> },   // 任务10:双级 scorecard
        { key: 'frame', icon: Eye, group: 'craft', label: '帧/意图', render: () => <FramePanel focalizer={focalizer} chapter={seq} /> },
      )
    }
    base.push(
      { key: 'deduce', icon: Sparkles, bare: true, group: 'craft', label: '演绎 · 角色限知', render: () => <DeduceTree seq={seq} /> },
      // 断头修复#13:badge 两端早已就绪(Rail 渲染✓ 数据✓),此前 caps 不传——红点永不显示
      { key: 'promise', icon: Bookmark, group: 'craft', label: '伏笔',
        badge: _promiseBadge(ledger, seq),
        render: () => <PromisesPanel ledger={ledger} seq={seq} onSelect={onSelect} /> },
      { key: 'motif', icon: LayoutList, group: 'craft', label: '母题', render: () => <MotifsPanel motifs={motifs} seq={seq} work={work} onSelect={onSelect} /> },
      // 断头修复(死 leftCaps 回填③):语义召回检索——原 WriteLayout renderRecall 不可达
      { key: 'search', icon: Search, group: 'inspect', label: '搜索',
        render: () => splitProjectRoots ? <SearchDirectory onSelectItem={onSelect} /> : <RecallPanel /> },
    )
    // 校验不占左轨：日常看护栏/全量体检。hidden 保留 key，仪表盘弱章等深链仍能进台账。
    base.push({
      key: 'review', icon: ShieldCheck, group: 'inspect', label: '校验', hidden: true,
      render: () => splitProjectRoots ? <IssueDirectory seq={seq} onSelectItem={onSelect} /> : <QCPanel seq={seq} />,
    })
    return base
  }, [tree, selId, expanded, onToggle, treeCbs, seq, includeStageTabs, splitProjectRoots, renderMaterialRoot, focalizer, ledger, motifs, onSelect])

  // tab 失效(如旧版 recall key 或切到无正文的章)→ 回退当前入口组首项
  const normalizedTab = tab === 'recall' ? 'search' : tab
  const active = caps.find((c) => c.key === normalizedTab) || caps[0]
  useEffect(() => {
    if (tab !== normalizedTab) {
      setTab(normalizedTab)
      return
    }
    if (!caps.find((c) => c.key === normalizedTab)) setTab(caps[0]?.key || (splitProjectRoots ? 'manuscript' : 'tree'))
  }, [caps, normalizedTab, setTab, splitProjectRoots, tab])

  useEffect(() => {
    const onOpenCapability = (e) => {
      const raw = e?.detail?.capability
      const key = raw === 'recall' ? 'search' : raw === 'issues' ? 'review' : raw
      if (key) setTab(key)
    }
    window.addEventListener('s3-open-capability', onOpenCapability)
    return () => window.removeEventListener('s3-open-capability', onOpenCapability)
  }, [setTab])

  return { caps, active, setTab }
}

export function LeftDock({ tree, selId, expanded, onToggle, onSelect, treeCbs, seq, work = 'main', onCollapse }) {
  const { caps, active, setTab } = useLeftDockCapabilities({ tree, selId, expanded, onToggle, onSelect, treeCbs, seq, work })

  return (
    <div className="h-full flex min-h-0 min-w-0 bg-surface overflow-hidden">
      {/* Rail 点当前高亮项发空串=折叠信号(设计:点当前项收起该栏)——此前被
          `k || active.key` 吞掉,折叠从未接通;现空串走 onCollapse 收起整栏。 */}
      <div className="shrink-0">
        <Rail side="left" caps={caps} active={active.key} onActive={(k) => (k ? setTab(k) : onCollapse?.())} />
      </div>
      {/* 崩溃隔离:左栏面板(项目树/帧/演绎/伏笔/母题/校验)包一层边界,单栏崩溃不拖垮中区/右栏。
          key=tab+章 → 切 tab / 切章时重建复位,用户切走再切回可自恢复。 */}
      <div className={cn('flex-1 min-w-0 min-h-0 overflow-y-auto border-l border-line', active.bare ? '' : 'p-3')}>
        <ErrorBoundary key={`${active.key}:${seq ?? ''}`}>{active.render()}</ErrorBoundary>
      </div>
    </div>
  )
}

// 三栏写作台的「右栏」:面板 + 竖图标轨(镜像)。图标切换:主编对话/版本存档。
// 伏笔 badge(断头修复#13):待办数=仍悬(setup<本章且未收)+超期;ledger 未就绪不显。
function _promiseBadge(ledger, seq) {
  if (!ledger || typeof ledger !== 'object' || seq == null) return undefined
  const open = Array.isArray(ledger.open) ? ledger.open : []
  const n = open.filter((p) => p && (p.payoff_chapter == null || p.payoff_chapter > seq)
    && ((p.window || {}).state === 'overdue'
        || (p.setup_chapter != null && p.setup_chapter < seq))).length
  return n || undefined
}

// 语义召回检索面板(死 leftCaps 回填③:原 WriteLayout renderRecall)。
function RecallPanel() {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState([])
  const run = (e) => { e.preventDefault(); if (q.trim()) api.recall(q.trim(), 8).then(setHits).catch(() => setHits([])) }
  return (
    <div>
      <SectionTitle>语义召回设定</SectionTitle>
      <form onSubmit={run} className="flex gap-1.5 mb-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="按意思搜,如「炼丹复活」"
          className="flex-1 h-8 px-2.5 rounded-lg border border-line bg-canvas text-f12" />
        <button type="submit" className="h-8 px-2.5 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">搜</button>
      </form>
      {hits.length === 0 ? <Empty>输入意思,向量召回最相关设定(非字面)</Empty>
        : hits.map((f) => (
          <div key={f.id} className="text-f12 text-ink py-1 border-b border-line/40 last:border-0">
            <span className="text-faint">{f.attribute}</span>:{f.value}
          </div>
        ))}
    </div>
  )
}

// 决策收件箱(主编主动化 T4):等作者的事项一处集中(needs_human/升格候选/pulse decision)。
// 「聊这个」经窗口事件 s3-chief-seed 预填聊天输入框(WriteChat/DiscussionDock 两端监听)。
function InboxPanel({ seq, onCount }) {
  const [data, setData] = useState(null)
  const [confirmFinalize, setConfirmFinalize] = useState(null)   // R1-3:delivered 终选二次确认(null=无)
  const [dismissBusy, setDismissBusy] = useState(null)
  const pullRef = useRef(null)
  useEffect(() => {
    let dead = false, timer = null
    // 切章时清空：避免短暂展示上一章 inbox 造成「事项串章」
    setData(null)
    // Task 8:失败同时向上报 null——Rail badge 与面板同源同真相,不留"面板报错、badge 还挂着旧数"的错位
    const pull = () => api.inbox(seq).then((d) => { if (!dead) { setData(d); onCount?.(d.count) } }).catch(() => { if (!dead) { setData({ items: [], count: 0, failed: true }); onCount?.(null) } })
    pullRef.current = pull
    pull()
    // R2-5:+idea(#想法待批)+lesson(升格候选)——此前含死过滤 lesson、缺 idea 致 badge 不刷
    const TABLES = new Set(['chapter', 'promise', 'lesson', 'chapter_scorecard', 'idea'])
    const onLive = (e) => { if (!TABLES.has(e?.detail?.table)) return; clearTimeout(timer); timer = setTimeout(pull, 600) }
    window.addEventListener('s3-live', onLive)
    return () => { dead = true; clearTimeout(timer); window.removeEventListener('s3-live', onLive) }
  }, [seq])
  // Task 8:loading/error 统一走 AsyncState(loading→role=status,error→role=alert+重试),
  // 重试直接复用既有 pullRef,不改轮询/live 监听。
  if (!data) return <AsyncState state="loading" title="加载收件箱" message="正在拉取等你决策的事项…" />
  // R1-8:拉取失败绝不渲染成"一切有账"(fail-safe 掩盖器是最危险的假绿——pilot parked/needs_human 的唯一出口)
  if (data.failed) {
    return <AsyncState state="error" title="收件箱拉取失败" onRetry={() => pullRef.current?.()}
      message="这不代表没有事项(可能后端/网络异常)。" />
  }
  if (!data.items.length) return <Empty>没有等你的事项——主编在岗,一切有账。</Empty>
  const KIND_LABEL = { needs_human: '需人裁决', promotable_lesson: '升格候选', pulse_decision: '章内决策',
    pilot_outline: '大纲待放行', pilot_delivered: '交付待终选', pilot_parked: '驾驶停靠',
    idea_setting: '想法 · 动设定', idea_revise: '想法 · 改旧章', idea_unclear: '想法 · 待澄清',
    daily_digest: '每日摘报',
    selection_l1: '选择 · 待点选', selection_l2: '选择 · 待终选', selection_failed: '选择 · 失败',
    hermes_approval: '主编 · 待批准写入' }
  const approve = (seqP, expectState) =>
    api.pilotApprove(seqP, expectState)
      .then((r) => {
        showToast(`第 ${seqP} 章已放行 → ${r.state}`, { tone: 'ok' })
        try { window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'chapter' } })) } catch { /* */ }
        pullRef.current?.()
      })
      .catch((e) => showToast(e?.body?.detail || '放行失败', { tone: 'danger' }))
  const doDismiss = (id) => {
    if (!id || dismissBusy) return
    setDismissBusy(id)
    api.dismissInboxItem(id).then(() => {
      showToast('已忽略', { tone: 'ok' })
      pullRef.current?.()
    }).catch((e) => showToast(e?.body?.detail || '忽略失败', { tone: 'danger' }))
      .finally(() => setDismissBusy(null))
  }
  const doResolve = (id) =>
    api.resolveIdea(id).then(() => {
      showToast('已处理,移出收件箱', { tone: 'ok' })
      try { window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'idea' } })) } catch { /* */ }
      pullRef.current?.()
    })
      .catch((e) => showToast(e?.body?.detail || '处理失败', { tone: 'danger' }))
  const doPilotReset = (seqP) =>
    api.pilotResetStep(seqP).then(() => {
      showToast(`第 ${seqP} 章已解卡`, { tone: 'ok' })
      try { window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'chapter' } })) } catch { /* */ }
      pullRef.current?.()
    })
      .catch((e) => showToast(e?.body?.detail || '解卡失败', { tone: 'danger' }))
  const openDeliveredChapter = (seqP) => {
    try { window.dispatchEvent(new CustomEvent('s3-open-chapter', { detail: { seq: seqP, tab: 'prose' } })) } catch { /* */ }
  }
  const degraded = data.degraded_sources || []
  return (
    <div className="space-y-2">
      <SectionTitle icon={TriangleAlert} right={`${data.count}`}>决策收件箱</SectionTitle>
      {/* R2-18:部分来源失败如实告知,不把残缺清单当完整(对齐 pulse「没查≠没病」) */}
      {degraded.length > 0 && (
        <div className="text-meta text-danger bg-danger/8 rounded px-2 py-1 leading-snug">
          部分来源加载失败({degraded.join(' / ')}):清单可能不全,没查≠没病。
        </div>
      )}
      {data.items.map((it) => (
        <div key={it.id || `${it.kind}:${it.seq || ''}:${(it.message || '').slice(0, 24)}`}
          className="rounded-lg border border-line bg-canvas px-2.5 py-2"
          data-testid={`inbox-item-${it.kind}`}>
          <div className="text-meta text-faint mb-0.5">{KIND_LABEL[it.kind] || it.kind}{it.seq ? ` · 第${it.seq}章` : ''}</div>
          <div className="text-f12 text-ink leading-snug">{it.message}</div>
          {it.id && (
            <button type="button" data-testid="inbox-dismiss"
              disabled={!!dismissBusy}
              onClick={() => doDismiss(it.id)}
              className="mt-1 text-meta text-faint hover:text-ink hover:underline cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
              {dismissBusy === it.id ? '忽略中…' : '忽略'}
            </button>
          )}
          {/* R2-4:交付卡结构化渲染(埋/收清单+QC+完整拿不准)——此前后端产出前端永不显示 */}
          {it.kind === 'pilot_delivered' && it.card && (
            <DeliveryCard card={it.card} seq={it.seq} onOpenProse={openDeliveredChapter} />
          )}
          {/* B-8:大纲提案就地可编辑的可发现性——放行会吃到你的最新大纲(expand_beats 重读库) */}
          {it.kind === 'pilot_outline' && (
            <div className="text-meta text-faint mt-0.5 leading-snug">想改?到左栏「项目树/大纲」或中区大纲 tab 编辑后再放行。</div>
          )}
          {it.action?.kind === 'pilot_approve' && (
            <button type="button" onClick={() => {
              // R1-3:delivered→finalize=宪法级终选背书,二次确认;outline 轻放行直发
              if (it.action.expect_state === 'delivered') setConfirmFinalize({ seq: it.action.payload, expect: it.action.expect_state })
              else approve(it.action.payload, it.action.expect_state)
            }} className="mt-1 text-meta text-brand hover:underline cursor-pointer">
              {it.action.expect_state === 'delivered' ? '终选定稿 →' : '放行 · 继续推进 →'}
            </button>
          )}
          {it.action?.kind === 'chat' && (
            <button type="button" onClick={() => {
              // 审查 P0-2:监听者可能未挂载(切 tab 后才渲)——pending 落 sessionStorage,
              // 挂载时消费;事件保留给已挂载者即时响应。
              try { sessionStorage.setItem('s3.chief.seed', it.action.payload) } catch { /* */ }
              try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: it.action.payload })) } catch { /* */ }
              try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
            }} className="mt-1 text-meta text-brand hover:underline cursor-pointer">跟主编聊这个 →</button>
          )}
          {/* R1-5:想法待批 resolve 出口——处理完毕移出收件箱,防 pending_approval 永久积压 */}
          {it.resolve?.kind === 'idea_resolve' && (
            <button type="button" onClick={() => doResolve(it.resolve.payload)}
              className="mt-1 ml-3 text-meta text-faint hover:text-ink hover:underline cursor-pointer">已处理 · 移出 →</button>
          )}
          {/* pilot parked 收件箱就地解卡（与 PilotDock 同源 API） */}
          {it.resolve?.kind === 'pilot_reset' && (
            <button type="button" onClick={() => doPilotReset(it.resolve.payload)}
              className="mt-1 ml-3 text-meta text-faint hover:text-ink hover:underline cursor-pointer">解卡 · 重跑当前步 →</button>
          )}
          {(it.action?.kind === 'open_select') && (
            <button
              type="button"
              data-testid="inbox-open-select"
              onClick={() => {
                if (it.seq != null) {
                  try { window.dispatchEvent(new CustomEvent('s3-open-chapter', { detail: { seq: it.seq } })) } catch { /* */ }
                }
                try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'selection' })) } catch { /* */ }
              }}
              className="mt-1 text-meta text-brand hover:underline cursor-pointer"
            >
              在主编里打开选择 →
            </button>
          )}
          {(it.action?.kind === 'open_chief') && (
            <button
              type="button"
              data-testid="inbox-open-chief"
              onClick={() => {
                if (it.seq != null) {
                  try { window.dispatchEvent(new CustomEvent('s3-open-chapter', { detail: { seq: it.seq } })) } catch { /* */ }
                }
                try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
              }}
              className="mt-1 text-meta text-brand hover:underline cursor-pointer"
            >
              回主编批准 →
            </button>
          )}
          {(it.kind === 'pilot_outline' || it.kind === 'pilot_delivered' || it.kind === 'pilot_parked') && (
            <button
              type="button"
              data-testid="inbox-open-pilot"
              onClick={() => {
                try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'pilot' })) } catch { /* */ }
              }}
              className="mt-1 ml-3 text-meta text-brand hover:underline cursor-pointer"
            >
              在主编里打开驾驶 →
            </button>
          )}
        </div>
      ))}
      <ConfirmDialog
        open={confirmFinalize != null}
        title="终选定稿这一章?"
        body="放行 delivered 章将执行 finalize（宪法级终选背书,盲评/审计以终选为准)。确认这就是你要定的稿?"
        confirmText="终选定稿"
        onConfirm={() => { const f = confirmFinalize; setConfirmFinalize(null); approve(f.seq, f.expect) }}
        onClose={() => setConfirmFinalize(null)}
      />
    </div>
  )
}

// R2-4:交付卡——主编交付时算的埋/收清单 + QC 命中数 + 自审拿不准,终选决策的关键依据。
// PR-6c: card.buckets = {redline, story, style} 三项计数（triage 分桶；先戏后辞可见）
function DeliveryCard({ card, seq, onOpenProse }) {
  const proms = Array.isArray(card.promises) ? card.promises : []
  const lc = (card.low_confidence || '').trim()
  const b = card.buckets && typeof card.buckets === 'object' ? card.buckets : null
  const bRed = b ? (Number(b.redline) || 0) : null
  const bStory = b ? (Number(b.story) || 0) : null
  const bStyle = b ? (Number(b.style) || 0) : null
  return (
    <div className="mt-1.5 rounded-md bg-soft/50 border border-line/60 px-2 py-1.5 space-y-1 text-meta" data-testid="delivery-card">
      <div className="flex gap-3 text-faint items-center flex-wrap">
        <span className="tnum">{card.words ?? '?'} 字</span>
        <span className={card.qc ? 'text-danger' : 'text-ok'}>质检 {card.qc || 0} 处</span>
        {seq != null && typeof onOpenProse === 'function' && (
          <button type="button" onClick={() => onOpenProse(seq)}
            className="text-brand hover:underline cursor-pointer ml-auto">打开正文 →</button>
        )}
      </div>
      {b && (
        <div className="flex gap-2 text-faint items-center flex-wrap" data-testid="delivery-card-buckets">
          <span className={bRed > 0 ? 'text-danger' : ''}>红线 {bRed}</span>
          <span className={bStory > 0 ? 'text-warn' : ''}>戏 {bStory}</span>
          <span>辞 {bStyle}</span>
        </div>
      )}
      {proms.length > 0 && <div className="text-fore leading-snug">本章伏笔:{proms.join('、')}</div>}
      {lc && lc !== '无' && <div className="text-fore leading-snug"><span className="text-faint">主编拿不准:</span>{lc}</div>}
    </div>
  )
}


export function useRightDockController({ sel, chapterSel, seq, lastSeq, onRestored }) {
  const [tab, setTab] = usePref('s3.rightTab', 'chief')
  const { setChiefMode } = useChiefSlot()
  // Task 8:undefined=尚未拉到(未知),null=拉取失败(未知),number=真实待办数。
  // 此前 useState(0)+静默 catch 把失败谎报成"0 待办"——收件箱是 needs_human 的唯一出口,
  // 可见状态谎报是信任问题:未知就如实显示未知(Rail 上「?」+ 可访问名),绝不显示 0。
  const [inboxCount, setInboxCount] = useState(undefined)
  // 审查 P1-9:badge 常驻拉取(此前依赖面板挂载,badge 恒 0 是死指标);
  // live 按表过滤+600ms 防抖(P1-8 同款,防 ingest 期风暴)。
  useEffect(() => {
    let timer = null
    let dead = false
    const pull = () => api.inbox(seq)
      .then((data) => { if (!dead) setInboxCount(typeof data?.count === 'number' ? data.count : 0) })
      .catch(() => { if (!dead) setInboxCount(null) })
    pull()
    const tables = new Set(['chapter', 'promise', 'lesson', 'chapter_scorecard', 'idea'])
    const onLive = (event) => {
      if (!tables.has(event?.detail?.table)) return
      clearTimeout(timer)
      timer = setTimeout(pull, 600)
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      dead = true
      clearTimeout(timer)
      window.removeEventListener('s3-live', onLive)
    }
  }, [seq])
  const caps = useMemo(() => {
    // Task 8 · scope 作用域分组(裁决):chief/selection 作用于「当前对象」(随选中变),
    // context/versions/pilot 作用于「章节」(选中章才有意义),inbox 是「全局」常驻。
    // key 全部保留不动——s3.rightTab 偏好与 s3-right-tab 事件继续按旧 key 工作。
    const next = [{ key: 'chief', icon: MessageSquare, label: '主编', bare: true, scope: 'object', render: () => <ChiefDock sel={sel} chapterSel={chapterSel} lastSeq={lastSeq} onRestored={onRestored} /> }]
    // 选择环 / 主编驾驶已收进主编模式条，不再占右栏 tab。
    if (seq != null) next.push({ key: 'versions', icon: Archive, label: '存档', scope: 'chapter', render: () => <div className="p-3"><RightVersionPanel seq={seq} onRestored={onRestored} /></div> })
    // 主编主动化 T4:决策收件箱——badge=等作者事项数(needs_human/升格候选/pulse decision);
    // Task 8 三态:数字仅真实拿到且>0 时显示;undefined=首拉悬挂期 badge 留空不显
    //(有意取舍:防每次挂载先闪「?」再变数字);null=拉取失败,才转 badgeUnknown 显「?」。
    next.push({ key: 'inbox', icon: TriangleAlert, label: '收件箱 · 等你决策', scope: 'global',
      badge: typeof inboxCount === 'number' && inboxCount > 0 ? inboxCount : undefined,
      badgeUnknown: inboxCount === null ? '收件箱状态未知' : undefined,
      render: () => <div className="p-3"><InboxPanel seq={seq} onCount={setInboxCount} /></div> })
    return next
  }, [sel, chapterSel, seq, lastSeq, onRestored, inboxCount])
  const active = caps.find((cap) => cap.key === tab) || caps[0]
  const activate = useCallback((key) => {
    const { tab: nextTab, mode } = resolveRightTab(key)
    if (mode) setChiefMode(mode)
    setTab(caps.some((cap) => cap.key === nextTab) ? nextTab : 'chief')
  }, [caps, setTab, setChiefMode])

  useEffect(() => {
    const { tab: nextTab, mode } = resolveRightTab(tab)
    if (mode) {
      setChiefMode(mode)
      setTab('chief')
      return
    }
    if (!caps.some((cap) => cap.key === tab)) setTab('chief')
  }, [caps, tab, setTab, setChiefMode])

  return { caps, active, activeKey: active.key, activate }
}

export function RightDock({ active, seq }) {
  if (!active) return null
  return (
    <div data-testid="right-dock-content" className="h-full min-h-0 min-w-0 bg-surface overflow-hidden">
      <div className={cn('h-full min-w-0 min-h-0 overflow-hidden', active.bare ? '' : 'overflow-y-auto bg-canvas/30')}>
        <ErrorBoundary key={`${active.key}:${seq ?? ''}`}>{active.render()}</ErrorBoundary>
      </div>
    </div>
  )
}

// 右栏存档面板:VersionPanel 的「恢复到此版本」在此接线。
// 走专用 /chapters/{seq}/restore-version:跳过工艺门、留「从存档恢复」checkpoint、默认知重抽。
// 恢复=覆盖当前正文的危险操作 → ConfirmDialog 二次确认;成功/失败均 toast。
function RightVersionPanel({ seq, onRestored }) {
  const toast = useToast()
  const [refreshKey, setRefreshKey] = useState(0)
  const [pending, setPending] = useState(null)   // 待确认恢复的版本正文(null=无)
  const doRestore = async (prose) => {
    try {
      await api.restoreChapterVersion(seq, {
        prose,
        label: '从存档恢复',
        reingest: true,
      })
      setRefreshKey((k) => k + 1)
      // F3:落库成功后通知中区 WriteLayout 重拉本章 → 编辑器同步为恢复版,
      // 防止编辑器仍持旧正文、用户续编辑保存时把恢复结果覆盖掉。
      onRestored?.()
      toast('已恢复到该版本(正文已回写,知识将按恢复稿重抽)')
    } catch (e) {
      toast('恢复失败:' + (e?.body?.detail || e?.message || ''), { tone: 'danger' })
    }
  }
  return (
    <>
      <VersionPanel seq={seq} refreshKey={refreshKey} onRestore={(prose) => setPending(prose ?? '')} />
      <ConfirmDialog
        open={pending != null}
        title="恢复到此版本?"
        body="当前正文将被该存档版本覆盖(可再从存档回看/恢复,但未存档的改动会丢失)。"
        danger
        confirmText="恢复"
        onConfirm={() => { const p = pending; setPending(null); doRestore(p) }}
        onClose={() => setPending(null)}
      />
    </>
  )
}

// 埋 → 收 章号呈现:未收显「待收」。
function PromiseSpan({ p }) {
  const setup = p.setup_chapter != null ? `第${p.setup_chapter}章` : '第—章'
  const payoff = p.payoff_chapter != null ? `第${p.payoff_chapter}章` : '待收'
  return <span className="text-meta text-faint tnum">埋 {setup} → 收 {payoff}</span>
}

function PromiseRow({ p, danger, tag, onSelect }) {
  // 块四b:点行 = 发通用 focus(主编 focusTalk 聚焦此伏笔)+ 导航中区出 CodexDetail 伏笔详情
  //  (与点项目树「伏笔叶」同形 → 复用既有 CODEX_LEAF→CodexDetail 路径,不再只跳章)。
  const { setFocus, suppressNextMirror } = useSelection()
  // 复合动作「聚焦+导航」:onSelect 改 sel → SelMirror 会把 sel 镜像成 focus(origin:'sel')覆盖掉
  // 刚设的 panel 聚焦;故前置一次性 suppress 标记吞掉随之而来的那一次 sel 镜像,保住 panel focusTalk
  // (与块三「聚焦+跳章」同一机制,必修1:因果标记替代时间窗)。
  const pick = () => {
    setFocus({
      type: 'promise', id: p.id, label: p.text || '',
      payload: { setup_chapter: p.setup_chapter, payoff_chapter: p.payoff_chapter, status: p.status, overdue: !!p.overdue },
      origin: 'panel',
    })
    if (onSelect) {
      suppressNextMirror()
      onSelect({ id: `promise:${p.id}`, type: 'promise', ref: p.id, label: p.text || '' })
    }
  }
  return (
    <button type="button" onClick={pick}
      title="查看伏笔详情(埋/收/线索/编辑)"
      className="w-full text-left mb-2 pb-2 border-b border-line/50 last:border-0 cursor-pointer rounded hover:bg-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 -mx-1 px-1">
      <div className={cn('text-f13 leading-snug', danger ? 'text-danger' : 'text-ink')}>{p.text}</div>
      <div className="flex items-center gap-1.5 mt-0.5">
        <PromiseSpan p={p} />
        {tag}
      </div>
    </button>
  )
}

function PromiseGroup({ title, icon, tone, items, danger, tag, onSelect }) {
  if (!items || items.length === 0) return null
  const Icon = icon
  return (
    <div className="mb-3 last:mb-0">
      <div className={cn('flex items-center gap-1 text-meta uppercase tracking-wider mb-1.5', tone || 'text-faint')}>
        {Icon && <Icon size={12} className="shrink-0" />}
        {title} · {items.length}
      </div>
      {items.map((p) => <PromiseRow key={p.id} p={p} danger={danger} tag={tag} onSelect={onSelect} />)}
    </div>
  )
}

function PromisesPanel({ ledger, seq, onSelect }) {
  if (ledger === undefined) return <div><SectionTitle icon={Bookmark}>伏笔 · 埋/收台账</SectionTitle><Skeleton className="w-2/3" /><Skeleton className="w-full mt-2" /></div>
  if (ledger === null) return <div><SectionTitle icon={Bookmark}>伏笔 · 埋/收台账</SectionTitle><Empty>伏笔台账加载失败,切走再切回可重试</Empty></div>
  const open = Array.isArray(ledger.open) ? ledger.open : []
  const closed = Array.isArray(ledger.closed) ? ledger.closed : []
  const herring = Array.isArray(ledger.red_herring) ? ledger.red_herring : []
  // 单遍优先级分桶(每条只进一个桶):本章收 > 本章埋 > 仍悬 > 其余
  const payThis = [], setThis = [], still = [], rest = []
  for (const p of [...open, ...closed]) {
    const isOpen = p.status !== 'closed' && (p.payoff_chapter == null || p.payoff_chapter > (seq ?? -1))
    if (seq != null && p.payoff_chapter === seq) payThis.push(p)
    else if (seq != null && p.setup_chapter === seq) setThis.push(p)
    else if (seq != null && isOpen && p.setup_chapter != null && p.setup_chapter < seq) still.push(p)
    else rest.push(p)
  }
  const overdue = still.filter((p) => p.overdue)
  const stillRest = still.filter((p) => !p.overdue)
  const empty = payThis.length + setThis.length + still.length + herring.length + rest.length === 0
  return (
    <div>
      <SectionTitle icon={Bookmark}>伏笔 · 埋/收台账</SectionTitle>
      {empty ? <Empty>暂无伏笔——正文里埋下线索后自动入账</Empty> : <>
        {/* 窄栏减负:默认只重点展开「本章相关」(本章收/埋/超期/仍悬) */}
        <PromiseGroup title="本章收" icon={Check} tone="text-ok font-semibold" items={payThis}
          tag={<Tag tone="ok">本章收</Tag>} onSelect={onSelect} />
        <PromiseGroup title="本章埋" items={setThis} tag={<Tag tone="brand">本章埋</Tag>} onSelect={onSelect} />
        <PromiseGroup title="超期未收" icon={TriangleAlert} tone="text-danger font-semibold" items={overdue} danger
          tag={<Tag tone="danger">超期</Tag>} onSelect={onSelect} />
        <PromiseGroup title="仍悬(截至本章)" items={stillRest} onSelect={onSelect} />
        {/* 障眼法 / 已了结 / 无关 强折叠(可点开)—— 与本章无关的噪声不占窄栏视野 */}
        {(herring.length + rest.length > 0) && (
          <details className="mt-1">
            <summary className="text-meta uppercase tracking-wider text-faint cursor-pointer list-none hover:text-fore">
              其它 · 障眼法 / 已了结 / 无关 · {herring.length + rest.length}
            </summary>
            <div className="mt-2">
              <PromiseGroup title="障眼法" items={herring} tag={<Tag tone="fore">障眼法</Tag>} onSelect={onSelect} />
              <PromiseGroup title="已了结 / 无关" items={rest} onSelect={onSelect} />
            </div>
          </details>
        )}
      </>}
    </div>
  )
}

function MotifRow({ m, evidence, highlight, onSelect }) {
  // 块三:点行 = 选中该母题 → 发通用 focus(主编聚焦该母题,不跳转)。
  const { setFocus, suppressNextMirror } = useSelection()
  const pick = () => {
    setFocus({
      type: 'motif', id: m.id, label: m.name,
      payload: { theme: m.theme, evidence: evidence || null },
      origin: 'panel',
    })
    if (onSelect) {
      suppressNextMirror()
      onSelect({ id: `motif:${m.id}`, type: 'motif', ref: m.id, label: m.name })
    }
  }
  return (
    <button type="button" onClick={pick} title="聚焦此母题"
      className={cn('block w-full text-left mb-2.5 pb-2.5 border-b border-line/50 last:border-0 cursor-pointer rounded hover:bg-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40',
        highlight && 'rounded-md bg-brand/5 px-2 -mx-1')}>
      <div className="text-f13 font-semibold text-ink">{m.name}</div>
      {m.theme && <div className="text-f12 text-fore mt-0.5">{m.theme}</div>}
      {evidence && <div className="text-f12 text-brand mt-0.5 leading-snug">「{evidence}」</div>}
      {!evidence && m.unfolding && <div className="text-f12 text-faint mt-0.5 leading-snug">{m.unfolding}</div>}
    </button>
  )
}

function MotifsPanel({ motifs, seq, work, onSelect }) {
  const [inst, setInst] = useState(undefined)   // undefined=加载 / null=失败 / []=空
  useEffect(() => {
    if (seq == null) { setInst([]); return }
    let ignore = false
    setInst(undefined)
    api.motifInstances(seq, work).then((r) => { if (!ignore) setInst(Array.isArray(r) ? r : []) }).catch(() => { if (!ignore) setInst(null) })
    return () => { ignore = true }
  }, [seq, work])
  const list = Array.isArray(inst) ? inst : []
  // 归一 motif_id / m.id(防 motif: 前缀或类型不一致导致「本章触及」永远为空)
  const normId = (id) => String(id ?? '').replace(/^motif:/, '')
  const evById = new Map(list.map((i) => [normId(i.motif_id), i.evidence]))
  const touched = motifs.filter((m) => evById.has(normId(m.id)))
  const rest = motifs.filter((m) => !evById.has(normId(m.id)))
  return (
    <div>
      <SectionTitle icon={LayoutList}>母题 · 设定库</SectionTitle>
      {motifs.length === 0 ? <Empty>暂无母题——在设定库立母题后在此追踪</Empty> : <>
        <div className="text-meta uppercase tracking-wider text-brand mb-1.5">本章触及 · {touched.length}</div>
        {inst === undefined ? <Skeleton className="w-2/3" />
          : inst === null ? <Empty>本章母题加载失败,切走再切回可重试</Empty>
          : touched.length === 0 ? <Empty>本章暂无触及——写/反哺本章后自动检测</Empty>
          : touched.map((m) => <MotifRow key={m.id} m={m} evidence={evById.get(normId(m.id))} highlight onSelect={onSelect} />)}
        {rest.length > 0 && (
          <details className="mt-3">
            <summary className="text-meta uppercase tracking-wider text-faint cursor-pointer list-none">全书母题 · {rest.length}</summary>
            <div className="mt-1.5">{rest.map((m) => <MotifRow key={m.id} m={m} onSelect={onSelect} />)}</div>
          </details>
        )}
      </>}
    </div>
  )
}

// 单条检测器:命中数为 0 显灰;非零可点开看命中短语。
function QCItem({ label, hits }) {
  const [open, setOpen] = useState(false)
  const list = Array.isArray(hits) ? hits : []
  const count = list.length
  // 命中短语抽取:各检测器返回结构不同(phrase / line / span / text)
  const phrases = list.map((h) => (typeof h === 'string' ? h
    : h?.phrase ?? h?.line ?? h?.span ?? h?.text ?? '')).filter(Boolean)
  const tone = count === 0 ? 'text-faint' : count >= 3 ? 'text-danger' : 'text-fore'
  return (
    <div className="border-b border-line/40 last:border-0">
      <button
        disabled={phrases.length === 0}
        onClick={() => setOpen((o) => !o)}
        className={cn('w-full flex items-center justify-between py-1 text-f13',
          phrases.length ? 'cursor-pointer hover:bg-soft/60 rounded px-1 -mx-1' : 'cursor-default')}>
        <span className="text-ink">{label}</span>
        <span className={cn('tnum font-medium', tone)}>{count}</span>
      </button>
      {open && phrases.length > 0 && (
        <ul className="pb-1.5 pl-1 space-y-0.5">
          {phrases.slice(0, 12).map((p, i) => (
            <li key={i} className="text-meta text-faint leading-snug break-all">· {p}</li>
          ))}
          {phrases.length > 12 && <li className="text-meta text-faint/60">…共 {phrases.length} 处</li>}
        </ul>
      )}
    </div>
  )
}

// M2a 张力检查(Task9 露出):按钮触发 POST /tension-check(rubric 走 LLM,可能慢),
// 渲染 8 项 {item,pass,detail,fix}。确定性 3 项即时返回;rubric 失败降级只显确定性项。
const TENSION_LABEL = {
  promise_progress: '伏笔进展', open_loops: '开环账本', irony_surface: '信息差盘点',
  dramatic_question: '戏剧问题', outcome_grammar: '结局语法', value_shift: '价值反转',
  micro_tension: '微张力', hook: '续读钩子',
}
function TensionCheck({ seq }) {
  const [state, setState] = useState('idle')   // idle / loading / done / error
  const [res, setRes] = useState(null)
  const run = async () => {
    setState('loading'); setRes(null)
    try {
      const r = await api.tensionCheck(seq)
      setRes(r); setState('done')
    } catch (e) { setRes({ error: e?.body?.detail || e?.message || '请求失败' }); setState('error') }
  }
  const items = res?.items || []
  return (
    <div className="mt-4 border-t border-line pt-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-f12 font-semibold text-ink inline-flex items-center gap-1.5"><Gauge size={13} className="text-faint" />叙事张力检查</div>
        <button onClick={run} disabled={state === 'loading'}
          className="h-6 px-2.5 rounded-lg text-meta bg-soft border border-line text-ink hover:bg-brand/10 disabled:opacity-40 cursor-pointer transition-colors inline-flex items-center gap-1">
          {state === 'loading' && <Loader2 size={11} className="animate-spin" />}{state === 'loading' ? '检查中…' : '张力检查'}
        </button>
      </div>
      {res?.error === 'no_prose' && <Empty>保存正文后可做张力检查</Empty>}
      {res?.error && res.error !== 'no_prose' && <div className="text-f12 text-danger">检查失败:{res.error}</div>}
      {state === 'done' && !res?.error && (
        <div className="space-y-1.5">
          {items.map((it, i) => (
            <div key={i} className="text-f12">
              <div className="flex items-center gap-1.5">
                <span className={cn('shrink-0 w-1.5 h-1.5 rounded-full', it.pass ? 'bg-ok' : 'bg-danger')} />
                <span className="text-ink font-medium">{TENSION_LABEL[it.item] || it.item}</span>
                <span className="text-faint">{it.detail}</span>
              </div>
              {!it.pass && it.fix && <div className="text-meta text-faint/70 leading-snug pl-3 mt-0.5">→ {it.fix}</div>}
            </div>
          ))}
          {res?.rubric_failed && <div className="text-meta text-faint inline-flex items-center gap-1"><TriangleAlert size={11} />rubric(LLM)判定失败,仅含确定性 3 项</div>}
        </div>
      )}
    </div>
  )
}

function QCPanel({ seq }) {
  const [qc, setQc] = useState(undefined)   // undefined=加载中,null=失败,{}=无正文,object=数据
  const [ingest, setIngest] = useState(null)  // KR3:反哺状态角标
  useEffect(() => {
    if (seq == null) { setQc({}); setIngest(null); return }
    setQc(undefined)
    api.qc(seq).then(setQc).catch(() => setQc(null))
    api.ingestStatus?.(seq).then(setIngest).catch(() => setIngest(null))
  }, [seq])
  const items = [
    ['复读(章内)', qc?.repetition],
    ['跨章复读', qc?.cross_repetition],
    ['整句重复', qc?.duplicate_lines],
    ['排比句式', qc?.structural],
    ['情感直说', qc?.emotion_telling],
    ['辞藻升华', qc?.purple],
    ['AI 腔', qc?.ai_tics],
    ['过饱和', qc?.oversaturation],
  ]
  const noProse = qc && typeof qc === 'object' && Object.keys(qc).length === 0
  return (
    <div>
      <SectionTitle icon={ShieldCheck}>确定性质检 · 本章正文</SectionTitle>
      {ingest?.failed && (
        <div
          data-testid="qc-ingest-fail-banner"
          className="mb-2 rounded-md border border-danger/40 bg-danger/8 px-2 py-1.5 text-meta text-danger"
          role="status"
        >
          反哺(ingest)失败:{ingest.ingest_message || ingest.ingest_status}
          ——知识账本可能落后;可点写作台「反哺失败·点重试」或手点反哺。
        </div>
      )}
      {!ingest?.failed && !ingest?.pending && ingest?.ingest_status === 'ok' && ingest?.ingest_message && (
        <div
          data-testid="qc-ingest-ok-banner"
          className="mb-2 rounded-md border border-line bg-soft/60 px-2 py-1.5 text-meta text-ink"
          role="status"
        >
          {ingest.ingest_message}
        </div>
      )}
      {ingest?.pending && (
        <div className="mb-2 text-meta text-faint">反哺进行中…</div>
      )}
      {qc === undefined ? <><Skeleton className="w-full" /><Skeleton className="w-full mt-2" /><Skeleton className="w-3/4 mt-2" /></>
        : qc === null ? <Empty>质检加载失败，切走再切回可重试</Empty>
        : noProse ? <Empty>保存正文后自动体检</Empty>
        : <div>{items.map(([label, hits]) => <QCItem key={label} label={label} hits={hits} />)}</div>}
      {seq != null && qc !== undefined && <TensionCheck seq={seq} />}
    </div>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import { GitCompare, Compass, FolderTree, Eye, Sparkles, Bookmark, LayoutList, ShieldCheck, MessageSquare, Archive, TriangleAlert, Check, ScrollText, Gauge, Loader2, Search, Bot } from 'lucide-react'
import { Rail } from './shell'
import { cn } from './lib/utils'
import { api } from './api'
import { Empty, Tag, SectionTitle, Skeleton } from './ui'
import { ProjectTree } from './ProjectTree'
import { BriefPanel } from './BriefPanel'
import { NorthStarPanel } from './NorthStarPanel'
import { SelectionPanel } from './SelectionPanel'
import { FramePanel } from './FramePanel'
import { DeduceTree } from './DeduceTree'
import { VersionPanel } from './VersionPanel'
import { ChiefDock } from './ChiefDock'
import { ErrorBoundary } from './ErrorBoundary'
import { usePref } from './lib/usePref'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { useToast, showToast } from './ui/Toast.jsx'
import { useSelection } from './selectionContext'

// 三栏写作台的「左栏」:VSCode 式竖图标轨 + 一个面板。图标切换:项目树/帧/演绎/伏笔/母题/校验。
// 项目树是第一个 tab(默认),数据面板并列其后 —— 消灭独立第4栏,导航与数据同栏。
export function LeftDock({ tree, selId, expanded, onToggle, onSelect, treeCbs, seq, onCollapse }) {
  const [tab, setTab] = usePref('s3.leftTab', 'tree')
  const [focalizer, setFocalizer] = useState('')
  const [ledger, setLedger] = useState(undefined)   // undefined=加载中/未知,null=加载失败,object=数据
  const [motifs, setMotifs] = useState([])
  const [qcCount, setQcCount] = useState(0)   // 断头修复#13:校验 tab 红点数据源

  useEffect(() => {
    setLedger(undefined)
    api.promisesLedger().then((l) => setLedger(l && typeof l === 'object' ? l : {})).catch(() => setLedger(null))
    api.motifs().then((m) => setMotifs(Array.isArray(m) ? m : [])).catch(() => {})
    // 断头修复#13:QC 命中总数喂校验 tab badge(轻端点,读存稿缓存)
    if (seq != null) {
      api.qc(seq).then((q) => {
        const cnt = (x) => Array.isArray(x) ? x.length : (typeof x === 'number' ? x : 0)
        setQcCount(q && typeof q === 'object'
          ? Object.values(q).reduce((s, v) => s + cnt(v), 0) : 0)
      }).catch(() => setQcCount(0))
    } else setQcCount(0)
  }, [seq])
  useEffect(() => {
    if (seq == null) { setFocalizer(''); return }
    const pull = () => api.chapter(seq).then((ch) => setFocalizer(ch?.focalizer || '')).catch(() => setFocalizer(''))
    pull()
    // 断头修复#14(focalizer 双源):顶栏改视角存稿后 chapter 表变更经 s3-live 推送——
    // 监听重拉,左栏帧面板不再按库中旧视角渲染(文档明令避免的"各自拉取不一致")。
    const onLive = (e) => { if ((e?.detail?.table || e?.detail?.tb) === 'chapter') pull() }
    window.addEventListener('s3-live', onLive)
    return () => window.removeEventListener('s3-live', onLive)
  }, [seq])

  const caps = useMemo(() => {
    // bare:true 的面板自带内边距/需边到边(项目树/演绎树),不套统一 p-3;其余数据面板走容器统一 padding。
    const base = [
      { key: 'tree', icon: FolderTree, bare: true, label: '项目树', render: () => (
        <div className="h-full overflow-hidden"><ProjectTree tree={tree} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} {...treeCbs} /></div>
      ) },
    ]
    if (seq == null) return base   // 未选章:只给项目树
    base.push(
      { key: 'brief', icon: ScrollText, label: '简报', render: () => <BriefPanel seq={seq} /> },
      { key: 'northstar', icon: Compass, label: '北极星', render: () => <NorthStarPanel seq={seq} /> },   // 任务10:双级 scorecard
      { key: 'frame', icon: Eye, label: '帧/意图', render: () => <FramePanel focalizer={focalizer} chapter={seq} /> },
      { key: 'deduce', icon: Sparkles, bare: true, label: '演绎 · 角色限知', render: () => <DeduceTree seq={seq} /> },
      // 断头修复#13:badge 两端早已就绪(Rail 渲染✓ 数据✓),此前 caps 不传——红点永不显示
      { key: 'promise', icon: Bookmark, label: '伏笔',
        badge: _promiseBadge(ledger, seq),
        render: () => <PromisesPanel ledger={ledger} seq={seq} onSelect={onSelect} /> },
      { key: 'motif', icon: LayoutList, label: '母题', render: () => <MotifsPanel motifs={motifs} seq={seq} onSelect={onSelect} /> },
      // 断头修复(死 leftCaps 回填③):语义召回检索——原 WriteLayout renderRecall 不可达
      { key: 'recall', icon: Search, label: '检索 · 语义召回', render: () => <RecallPanel /> },
    )
    base.push({ key: 'review', icon: ShieldCheck, label: '校验 · QC/泄露',
      badge: qcCount || undefined, render: () => <QCPanel seq={seq} /> })
    return base
  }, [tree, selId, expanded, seq, focalizer, ledger, motifs, qcCount, onSelect])

  // tab 失效(如切到无正文的章,校验 tab 消失)→ 回退项目树
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('tree') }, [caps, tab, setTab])

  return (
    <div className="h-full flex min-h-0 bg-surface">
      {/* Rail 点当前高亮项发空串=折叠信号(设计:点当前项收起该栏)——此前被
          `k || active.key` 吞掉,折叠从未接通;现空串走 onCollapse 收起整栏。 */}
      <Rail side="left" caps={caps} active={active.key} onActive={(k) => (k ? setTab(k) : onCollapse?.())} />
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
  const pullRef = useRef(null)
  useEffect(() => {
    let dead = false, timer = null
    const pull = () => api.inbox(seq).then((d) => { if (!dead) { setData(d); onCount?.(d.count) } }).catch(() => { if (!dead) setData({ items: [], count: 0, failed: true }) })
    pullRef.current = pull
    pull()
    // R2-5:+idea(#想法待批)+lesson(升格候选)——此前含死过滤 lesson、缺 idea 致 badge 不刷
    const TABLES = new Set(['chapter', 'promise', 'lesson', 'chapter_scorecard', 'idea'])
    const onLive = (e) => { if (!TABLES.has(e?.detail?.table)) return; clearTimeout(timer); timer = setTimeout(pull, 600) }
    window.addEventListener('s3-live', onLive)
    return () => { dead = true; clearTimeout(timer); window.removeEventListener('s3-live', onLive) }
  }, [seq])
  if (!data) return <Skeleton className="w-full" />
  // R1-8:拉取失败绝不渲染成"一切有账"(fail-safe 掩盖器是最危险的假绿——pilot parked/needs_human 的唯一出口)
  if (data.failed) return <Empty>收件箱拉取失败——这不代表没有事项(可能后端/网络异常)。请稍后切走再切回重试。</Empty>
  if (!data.items.length) return <Empty>没有等你的事项——主编在岗,一切有账。</Empty>
  const KIND_LABEL = { needs_human: '需人裁决', promotable_lesson: '升格候选', pulse_decision: '章内决策',
    pilot_outline: '大纲待放行', pilot_delivered: '交付待终选', pilot_parked: 'Pilot 停靠',
    idea_setting: '想法 · 动设定', idea_revise: '想法 · 改旧章' }
  const approve = (seqP, expectState) =>
    api.pilotApprove(seqP, expectState)
      .then((r) => { showToast(`第 ${seqP} 章已放行 → ${r.state}`, { tone: 'ok' }); pullRef.current?.() })
      .catch((e) => showToast(e?.body?.detail || '放行失败', { tone: 'danger' }))
  const doResolve = (id) =>
    api.resolveIdea(id).then(() => { showToast('已处理,移出收件箱', { tone: 'ok' }); pullRef.current?.() })
      .catch((e) => showToast(e?.body?.detail || '处理失败', { tone: 'danger' }))
  const degraded = data.degraded_sources || []
  return (
    <div className="space-y-2">
      <SectionTitle icon={TriangleAlert} right={`${data.count}`}>决策收件箱</SectionTitle>
      {/* R2-18:部分来源失败如实告知,不把残缺清单当完整(对齐 pulse「没查≠没病」) */}
      {degraded.length > 0 && (
        <div className="text-f10 text-danger bg-danger/8 rounded px-2 py-1 leading-snug">
          部分来源加载失败({degraded.join(' / ')}):清单可能不全,没查≠没病。
        </div>
      )}
      {data.items.map((it, i) => (
        <div key={i} className="rounded-lg border border-line bg-canvas px-2.5 py-2">
          <div className="text-f10 text-faint mb-0.5">{KIND_LABEL[it.kind] || it.kind}{it.seq ? ` · 第${it.seq}章` : ''}</div>
          <div className="text-f12 text-ink leading-snug">{it.message}</div>
          {/* R2-4:交付卡结构化渲染(埋/收清单+QC+完整拿不准)——此前后端产出前端永不显示 */}
          {it.kind === 'pilot_delivered' && it.card && <DeliveryCard card={it.card} />}
          {/* B-8:大纲提案就地可编辑的可发现性——放行会吃到你的最新大纲(expand_beats 重读库) */}
          {it.kind === 'pilot_outline' && (
            <div className="text-f10 text-faint mt-0.5 leading-snug">想改?到左栏「项目树/大纲」或中区大纲 tab 编辑后再放行。</div>
          )}
          {it.action?.kind === 'pilot_approve' && (
            <button onClick={() => {
              // R1-3:delivered→finalize=宪法级终选背书,二次确认;outline 轻放行直发
              if (it.action.expect_state === 'delivered') setConfirmFinalize({ seq: it.action.payload, expect: it.action.expect_state })
              else approve(it.action.payload, it.action.expect_state)
            }} className="mt-1 text-f11 text-brand hover:underline cursor-pointer">
              {it.action.expect_state === 'delivered' ? '终选定稿 →' : '放行 · 继续推进 →'}
            </button>
          )}
          {it.action?.kind === 'chat' && (
            <button onClick={() => {
              // 审查 P0-2:监听者可能未挂载(切 tab 后才渲)——pending 落 sessionStorage,
              // 挂载时消费;事件保留给已挂载者即时响应。
              try { sessionStorage.setItem('s3.chief.seed', it.action.payload) } catch { /* */ }
              try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: it.action.payload })) } catch { /* */ }
              try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
            }} className="mt-1 text-f11 text-brand hover:underline cursor-pointer">跟主编聊这个 →</button>
          )}
          {/* R1-5:想法待批 resolve 出口——处理完毕移出收件箱,防 pending_approval 永久积压 */}
          {it.resolve?.kind === 'idea_resolve' && (
            <button onClick={() => doResolve(it.resolve.payload)}
              className="mt-1 ml-3 text-f11 text-faint hover:text-ink hover:underline cursor-pointer">已处理 · 移出 →</button>
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
function DeliveryCard({ card }) {
  const proms = Array.isArray(card.promises) ? card.promises : []
  const lc = (card.low_confidence || '').trim()
  return (
    <div className="mt-1.5 rounded-md bg-soft/50 border border-line/60 px-2 py-1.5 space-y-1 text-f11">
      <div className="flex gap-3 text-faint">
        <span className="tnum">{card.words ?? '?'} 字</span>
        <span className={card.qc ? 'text-danger' : 'text-ok'}>QC {card.qc || 0} 处</span>
      </div>
      {proms.length > 0 && <div className="text-fore leading-snug">本章伏笔:{proms.join('、')}</div>}
      {lc && lc !== '无' && <div className="text-fore leading-snug"><span className="text-faint">主编拿不准:</span>{lc}</div>}
    </div>
  )
}

// R1-4:Pilot 驾驶舱——章生命周期状态机的 UI 起点(此前 5 个 api 包装零消费,状态机只能 curl 进入)。
// 状态徽章 + 手动推进/解卡/退出 + 连写到第 N 章/暂停 + 停靠文案 + stalled 提醒,轮询 run-status。
const PILOT_STATE_LABEL = {
  idle: '未启动', outline_proposed: '大纲待放行', beats_ready: '节拍就绪', deduced: '演绎就绪',
  drafting: '草稿生成中', checked: '体检通过', delivered: '已交付 · 待终选', finalized: '已定稿',
}
function PilotDock({ seq }) {
  const [st, setSt] = useState(null)
  const [run, setRun] = useState(null)
  const [until, setUntil] = useState('')
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  useEffect(() => {
    if (seq == null) return undefined
    let dead = false
    const tick = () => {
      if (dead) return
      api.pilotStatus(seq).then((s) => { if (!dead) setSt(s) }).catch(() => {})
      api.pilotRunStatus().then((r) => { if (!dead) setRun(r) }).catch(() => {})
    }
    tick()
    const t = setInterval(tick, 3500)   // 常驻轮询:连写进度/停靠/stalled 实时可见(窄查,轻)
    return () => { dead = true; clearInterval(t) }
  }, [seq])
  if (seq == null) return <Empty>选一章后可用 Pilot 驱动写作</Empty>
  const refresh = () => {
    api.pilotStatus(seq).then(setSt).catch(() => {})
    api.pilotRunStatus().then(setRun).catch(() => {})
  }
  const act = (fn, okMsg) => {
    setBusy(true)
    return fn().then(() => { toast(okMsg); refresh() })
      .catch((e) => toast(e?.body?.detail || '操作失败', { tone: 'danger' }))
      .finally(() => setBusy(false))
  }
  const state = st?.state || 'idle'
  const running = !!run?.running
  const untilN = Number(until)
  return (
    <div className="space-y-3">
      <SectionTitle icon={Bot}>Pilot · 主编驾驶</SectionTitle>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="px-2 py-0.5 rounded-full bg-brand/10 text-brand text-f11 font-medium">{PILOT_STATE_LABEL[state] || state}</span>
        {st?.stalled && <span className="px-2 py-0.5 rounded-full bg-danger/10 text-danger text-f10">卡住 · 超 30 分未推进</span>}
        {st?.next_action && !st?.parked && !running && <span className="text-f10 text-faint">下一步:{st.next_action}</span>}
      </div>
      {st?.parked && <div className="text-f11 text-danger bg-danger/8 rounded px-2 py-1.5 leading-snug">停靠:{st.parked}</div>}
      <div className="flex gap-2 flex-wrap">
        <button disabled={busy || running || state === 'finalized'}
          onClick={() => act(() => api.pilotStep(seq), '已推进一步')}
          className="h-7 px-2.5 rounded-lg text-f11 bg-brand text-brandfg disabled:opacity-40 cursor-pointer">推进一步 →</button>
        {(st?.parked || st?.stalled) && (
          <button disabled={busy} onClick={() => act(() => api.pilotResetStep(seq), '已解卡,可重跑当前步')}
            className="h-7 px-2.5 rounded-lg text-f11 bg-soft border border-line text-ink cursor-pointer">解卡</button>
        )}
        {state !== 'idle' && state !== 'finalized' && (
          <button disabled={busy}
            onClick={() => { if (window.confirm('退出 Pilot 编排?不动正文/草料,想再用从头 step 即可。')) act(() => api.pilotDismiss(seq), '已退出 Pilot') }}
            className="h-7 px-2.5 rounded-lg text-f11 text-faint hover:text-danger cursor-pointer">退出</button>
        )}
      </div>
      <div className="border-t border-line pt-2.5">
        {running ? (
          <div className="space-y-1.5">
            <div className="text-f11 text-brand inline-flex items-center gap-1.5">
              <Loader2 size={12} className="animate-spin" />连写中 · 第 {run.cur_seq ?? '?'} 章(目标第 {run.until ?? '?'} 章)
            </div>
            <button disabled={busy} onClick={() => act(() => api.pilotPause(), '已暂停(步边界生效)')}
              className="h-7 px-2.5 rounded-lg text-f11 bg-soft border border-line text-ink cursor-pointer">暂停连写</button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-f11 text-faint">连写到第</span>
            <input value={until} onChange={(e) => setUntil(e.target.value.replace(/\D/g, ''))} placeholder={String((seq ?? 0) + 3)}
              className="w-14 h-7 px-2 rounded-lg border border-line bg-canvas text-f11 text-center" />
            <span className="text-f11 text-faint">章(终选留你,不自动定稿)</span>
            <button disabled={busy || !until || untilN < seq}
              onClick={() => act(() => api.pilotRun(seq, untilN), '连写已启动')}
              className="h-7 px-2.5 rounded-lg text-f11 bg-brand text-brandfg disabled:opacity-40 cursor-pointer">开始连写</button>
          </div>
        )}
        {run?.stopped && !running && <div className="text-f10 text-faint mt-1.5 leading-snug">上次连写:{run.stopped}</div>}
      </div>
    </div>
  )
}

export function RightDock({ sel, chapterSel, seq, lastSeq, onRestored, onCollapse }) {
  const [tab, setTab] = usePref('s3.rightTab', 'chief')
  const [inboxCount, setInboxCount] = useState(0)
  // 审查 P1-9:badge 常驻拉取(此前依赖面板挂载,badge 恒 0 是死指标);
  // live 按表过滤+600ms 防抖(P1-8 同款,防 ingest 期风暴)。
  useEffect(() => {
    let timer = null, dead = false
    const pull = () => api.inbox(seq).then((d) => { if (!dead) setInboxCount(d.count) }).catch(() => {})
    pull()
    const TABLES = new Set(['chapter', 'promise', 'lesson', 'chapter_scorecard', 'idea'])   // R2-5:+idea/lesson
    const onLive = (e) => {
      if (!TABLES.has(e?.detail?.table)) return
      clearTimeout(timer); timer = setTimeout(pull, 600)
    }
    window.addEventListener('s3-live', onLive)
    return () => { dead = true; clearTimeout(timer); window.removeEventListener('s3-live', onLive) }
  }, [seq])
  // 断头修复#12:中区"让主编改这处/体检送主编"需要把右栏切到主编 tab——
  // 此前 WriteLayout 的 setRightActive 信号无人消费;现经窗口事件接通。
  useEffect(() => {
    const on = (e) => { if (e?.detail) setTab(String(e.detail)) }
    window.addEventListener('s3-right-tab', on)
    return () => window.removeEventListener('s3-right-tab', on)
  }, [setTab])
  const caps = useMemo(() => {
    const c = [{ key: 'chief', icon: MessageSquare, label: '主编', bare: true, render: () => <ChiefDock sel={sel} chapterSel={chapterSel} lastSeq={lastSeq} /> }]
    if (seq != null) c.push({ key: 'selection', icon: GitCompare, label: '选择环 · 3候选终选', render: () => <div className="p-3"><SelectionPanel seq={seq} onFinalized={onRestored} /></div> })   // P2审查P1-2:终选落库=恢复语义,bump restoreTick 防编辑器stale buffer盖稿
    if (seq != null) c.push({ key: 'versions', icon: Archive, label: '存档', render: () => <div className="p-3"><RightVersionPanel seq={seq} onRestored={onRestored} /></div> })
    // R1-4:Pilot 驾驶舱——章生命周期状态机 UI 起点(推进/连写/暂停/解卡/退出)
    if (seq != null) c.push({ key: 'pilot', icon: Bot, label: 'Pilot · 主编驾驶', render: () => <div className="p-3"><PilotDock seq={seq} /></div> })
    // 主编主动化 T4:决策收件箱——badge=等作者事项数(needs_human/升格候选/pulse decision)
    c.push({ key: 'inbox', icon: TriangleAlert, label: '收件箱 · 等你决策', badge: inboxCount || undefined,
      render: () => <div className="p-3"><InboxPanel seq={seq} onCount={setInboxCount} /></div> })
    return c
  }, [sel, chapterSel, seq, onRestored, inboxCount])
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('chief') }, [caps, tab, setTab])
  return (
    <div className="h-full flex min-h-0 bg-surface">
      {/* 崩溃隔离:右栏面板(主编对话/存档)包一层边界,右栏崩溃不影响中区书稿与左栏。
          key=tab+章 → 切 tab / 切章时重建复位。 */}
      <div className={cn('flex-1 min-w-0 min-h-0', active.bare ? '' : 'overflow-y-auto')}>
        <ErrorBoundary key={`${active.key}:${seq ?? ''}`}>{active.render()}</ErrorBoundary>
      </div>
      {/* 同左栏:点当前项=折叠信号 → 收起右栏 */}
      <Rail side="right" caps={caps} active={active.key} onActive={(k) => (k ? setTab(k) : onCollapse?.())} />
    </div>
  )
}

// 右栏存档面板:VersionPanel 的「恢复到此版本」在此接线。
// RightDock 不持有当前 prose / WriteLayout 的 persist 闭包,故 onRestore 直接把该版本正文
// 经 api.saveChapter 落库到 chapter 正文(保留原 title/focalizer),再 bump refreshKey 刷新存档列表。
// 恢复=覆盖当前正文的危险操作 → ConfirmDialog 二次确认;成功/失败均 toast。
function RightVersionPanel({ seq, onRestored }) {
  const toast = useToast()
  const [refreshKey, setRefreshKey] = useState(0)
  const [pending, setPending] = useState(null)   // 待确认恢复的版本正文(null=无)
  const doRestore = async (prose) => {
    try {
      // 保留原章标题/focalizer,只覆盖正文;取不到则以 undefined 交后端保持不变。
      let title, focalizer
      try { const ch = await api.chapter(seq); title = ch?.title; focalizer = ch?.focalizer } catch { /* 取不到就不带,后端保持原值 */ }
      await api.saveChapter(seq, prose, title, focalizer)
      setRefreshKey((k) => k + 1)
      // F3:落库成功后通知中区 WriteLayout 重拉本章 → 编辑器同步为恢复版,
      // 防止编辑器仍持旧正文、用户续编辑保存时把恢复结果覆盖掉。
      onRestored?.()
      toast('已恢复到该版本(正文已回写)')
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
  return <span className="text-f10 text-faint tnum">埋 {setup} → 收 {payoff}</span>
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
      <div className={cn('flex items-center gap-1 text-f11 uppercase tracking-wider mb-1.5', tone || 'text-faint')}>
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
            <summary className="text-f11 uppercase tracking-wider text-faint cursor-pointer list-none hover:text-fore">
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

function MotifsPanel({ motifs, seq, onSelect }) {
  const [inst, setInst] = useState(undefined)   // undefined=加载 / null=失败 / []=空
  useEffect(() => {
    if (seq == null) { setInst([]); return }
    let ignore = false
    setInst(undefined)
    api.motifInstances(seq).then((r) => { if (!ignore) setInst(Array.isArray(r) ? r : []) }).catch(() => { if (!ignore) setInst(null) })
    return () => { ignore = true }
  }, [seq])
  const list = Array.isArray(inst) ? inst : []
  const evById = new Map(list.map((i) => [i.motif_id, i.evidence]))
  const touched = motifs.filter((m) => evById.has(m.id))
  const rest = motifs.filter((m) => !evById.has(m.id))
  return (
    <div>
      <SectionTitle icon={LayoutList}>母题 · 设定库</SectionTitle>
      {motifs.length === 0 ? <Empty>暂无母题——在设定库立母题后在此追踪</Empty> : <>
        <div className="text-f11 uppercase tracking-wider text-brand mb-1.5">本章触及 · {touched.length}</div>
        {inst === undefined ? <Skeleton className="w-2/3" />
          : inst === null ? <Empty>本章母题加载失败,切走再切回可重试</Empty>
          : touched.length === 0 ? <Empty>本章暂无触及——写/反哺本章后自动检测</Empty>
          : touched.map((m) => <MotifRow key={m.id} m={m} evidence={evById.get(m.id)} highlight onSelect={onSelect} />)}
        {rest.length > 0 && (
          <details className="mt-3">
            <summary className="text-f11 uppercase tracking-wider text-faint cursor-pointer list-none">全书母题 · {rest.length}</summary>
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
            <li key={i} className="text-f11 text-faint leading-snug break-all">· {p}</li>
          ))}
          {phrases.length > 12 && <li className="text-f11 text-faint/60">…共 {phrases.length} 处</li>}
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
          className="h-6 px-2.5 rounded-lg text-f11 bg-soft border border-line text-ink hover:bg-brand/10 disabled:opacity-40 cursor-pointer transition-colors inline-flex items-center gap-1">
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
              {!it.pass && it.fix && <div className="text-f11 text-faint/70 leading-snug pl-3 mt-0.5">→ {it.fix}</div>}
            </div>
          ))}
          {res?.rubric_failed && <div className="text-f11 text-faint">⚠ rubric(LLM)判定失败,仅含确定性 3 项</div>}
        </div>
      )}
    </div>
  )
}

function QCPanel({ seq }) {
  const [qc, setQc] = useState(undefined)   // undefined=加载中,null=失败,{}=无正文,object=数据
  useEffect(() => { setQc(undefined); api.qc(seq).then(setQc).catch(() => setQc(null)) }, [seq])
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
      <SectionTitle icon={ShieldCheck}>确定性 QC · 本章正文</SectionTitle>
      {qc === undefined ? <><Skeleton className="w-full" /><Skeleton className="w-full mt-2" /><Skeleton className="w-3/4 mt-2" /></>
        : qc === null ? <Empty>QC 加载失败,切走再切回可重试</Empty>
        : noProse ? <Empty>保存正文后自动体检</Empty>
        : <div>{items.map(([label, hits]) => <QCItem key={label} label={label} hits={hits} />)}</div>}
      {seq != null && qc !== undefined && <TensionCheck seq={seq} />}
    </div>
  )
}

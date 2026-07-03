import { useEffect, useMemo, useState } from 'react'
import { FolderTree, Eye, Sparkles, Bookmark, LayoutList, ShieldCheck, MessageSquare, Archive, TriangleAlert, Check, ScrollText, Gauge, Loader2 } from 'lucide-react'
import { Rail } from './shell'
import { cn } from './lib/utils'
import { api } from './api'
import { Empty, Tag, SectionTitle, Skeleton } from './ui'
import { ProjectTree } from './ProjectTree'
import { BriefPanel } from './BriefPanel'
import { FramePanel } from './FramePanel'
import { DeduceTree } from './DeduceTree'
import { VersionPanel } from './VersionPanel'
import { ChiefDock } from './ChiefDock'
import { ErrorBoundary } from './ErrorBoundary'
import { usePref } from './lib/usePref'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'
import { useSelection } from './selectionContext'

// 三栏写作台的「左栏」:VSCode 式竖图标轨 + 一个面板。图标切换:项目树/帧/演绎/伏笔/母题/校验。
// 项目树是第一个 tab(默认),数据面板并列其后 —— 消灭独立第4栏,导航与数据同栏。
export function LeftDock({ tree, selId, expanded, onToggle, onSelect, treeCbs, seq, onJumpChapter }) {
  const [tab, setTab] = usePref('s3.leftTab', 'tree')
  const [focalizer, setFocalizer] = useState('')
  const [ledger, setLedger] = useState(undefined)   // undefined=加载中/未知,null=加载失败,object=数据
  const [motifs, setMotifs] = useState([])

  useEffect(() => {
    setLedger(undefined)
    api.promisesLedger().then((l) => setLedger(l && typeof l === 'object' ? l : {})).catch(() => setLedger(null))
    api.motifs().then((m) => setMotifs(Array.isArray(m) ? m : [])).catch(() => {})
  }, [seq])
  useEffect(() => {
    if (seq == null) { setFocalizer(''); return }
    api.chapter(seq).then((ch) => setFocalizer(ch?.focalizer || '')).catch(() => setFocalizer(''))
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
      { key: 'frame', icon: Eye, label: '帧/意图', render: () => <FramePanel focalizer={focalizer} chapter={seq} /> },
      { key: 'deduce', icon: Sparkles, bare: true, label: '演绎 · 角色限知', render: () => <DeduceTree seq={seq} /> },
      { key: 'promise', icon: Bookmark, label: '伏笔', render: () => <PromisesPanel ledger={ledger} seq={seq} onJumpChapter={onJumpChapter} /> },
      { key: 'motif', icon: LayoutList, label: '母题', render: () => <MotifsPanel motifs={motifs} seq={seq} /> },
    )
    base.push({ key: 'review', icon: ShieldCheck, label: '校验 · QC/泄露', render: () => <QCPanel seq={seq} /> })
    return base
  }, [tree, selId, expanded, seq, focalizer, ledger, motifs, onJumpChapter])

  // tab 失效(如切到无正文的章,校验 tab 消失)→ 回退项目树
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('tree') }, [caps, tab, setTab])

  return (
    <div className="h-full flex min-h-0 bg-surface">
      <Rail side="left" caps={caps} active={active.key} onActive={(k) => setTab(k || active.key)} />
      {/* 崩溃隔离:左栏面板(项目树/帧/演绎/伏笔/母题/校验)包一层边界,单栏崩溃不拖垮中区/右栏。
          key=tab+章 → 切 tab / 切章时重建复位,用户切走再切回可自恢复。 */}
      <div className={cn('flex-1 min-w-0 min-h-0 overflow-y-auto border-l border-line', active.bare ? '' : 'p-3')}>
        <ErrorBoundary key={`${active.key}:${seq ?? ''}`}>{active.render()}</ErrorBoundary>
      </div>
    </div>
  )
}

// 三栏写作台的「右栏」:面板 + 竖图标轨(镜像)。图标切换:主编对话/版本存档。
export function RightDock({ sel, chapterSel, seq, onRestored }) {
  const [tab, setTab] = usePref('s3.rightTab', 'chief')
  const caps = useMemo(() => {
    const c = [{ key: 'chief', icon: MessageSquare, label: '主编', bare: true, render: () => <ChiefDock sel={sel} chapterSel={chapterSel} /> }]
    if (seq != null) c.push({ key: 'versions', icon: Archive, label: '存档', render: () => <div className="p-3"><RightVersionPanel seq={seq} onRestored={onRestored} /></div> })
    return c
  }, [sel, chapterSel, seq, onRestored])
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('chief') }, [caps, tab, setTab])
  return (
    <div className="h-full flex min-h-0 bg-surface">
      {/* 崩溃隔离:右栏面板(主编对话/存档)包一层边界,右栏崩溃不影响中区书稿与左栏。
          key=tab+章 → 切 tab / 切章时重建复位。 */}
      <div className={cn('flex-1 min-w-0 min-h-0', active.bare ? '' : 'overflow-y-auto')}>
        <ErrorBoundary key={`${active.key}:${seq ?? ''}`}>{active.render()}</ErrorBoundary>
      </div>
      <Rail side="right" caps={caps} active={active.key} onActive={(k) => setTab(k || active.key)} />
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

function PromiseRow({ p, danger, tag, onJumpChapter }) {
  // 联动跳章(P2):有 setup_chapter 且拿到 onJumpChapter → 整条可点,跳到埋设章。
  const { setFocus, suppressNextMirror } = useSelection()
  const jumpTo = p.setup_chapter != null ? p.setup_chapter : p.payoff_chapter
  const canJump = onJumpChapter && jumpTo != null
  // 块三:点行 = 选中该伏笔 → 发通用 focus(主编聚焦);可跳时仍跳埋设章。
  // 复合动作「聚焦+跳章」:跳章前置一次性 suppress 标记,SelMirror 只消费掉这一次 sel 变化
  // (不冲掉伏笔聚焦);之后任何 sel 变化正常镜像(必修1:因果标记替代时间窗)。
  const pick = () => {
    setFocus({
      type: 'promise', id: p.id, label: p.text || '',
      payload: { setup_chapter: p.setup_chapter, payoff_chapter: p.payoff_chapter, status: p.status, overdue: !!p.overdue },
      origin: 'panel',
    })
    if (canJump) { suppressNextMirror(); onJumpChapter(jumpTo) }
  }
  return (
    <button type="button" onClick={pick}
      title={canJump ? `聚焦此伏笔,并跳到第${jumpTo}章` : '聚焦此伏笔'}
      className="w-full text-left mb-2 pb-2 border-b border-line/50 last:border-0 cursor-pointer rounded hover:bg-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 -mx-1 px-1">
      <div className={cn('text-f13 leading-snug', danger ? 'text-danger' : 'text-ink')}>{p.text}</div>
      <div className="flex items-center gap-1.5 mt-0.5">
        <PromiseSpan p={p} />
        {tag}
      </div>
    </button>
  )
}

function PromiseGroup({ title, icon, tone, items, danger, tag, onJumpChapter }) {
  if (!items || items.length === 0) return null
  const Icon = icon
  return (
    <div className="mb-3 last:mb-0">
      <div className={cn('flex items-center gap-1 text-f11 uppercase tracking-wider mb-1.5', tone || 'text-faint')}>
        {Icon && <Icon size={12} className="shrink-0" />}
        {title} · {items.length}
      </div>
      {items.map((p) => <PromiseRow key={p.id} p={p} danger={danger} tag={tag} onJumpChapter={onJumpChapter} />)}
    </div>
  )
}

function PromisesPanel({ ledger, seq, onJumpChapter }) {
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
        <PromiseGroup title="本章收" icon={Check} tone="text-ok font-semibold" items={payThis}
          tag={<Tag tone="ok">本章收</Tag>} onJumpChapter={onJumpChapter} />
        <PromiseGroup title="本章埋" items={setThis} tag={<Tag tone="brand">本章埋</Tag>} onJumpChapter={onJumpChapter} />
        <PromiseGroup title="超期未收" icon={TriangleAlert} tone="text-danger font-semibold" items={overdue} danger
          tag={<Tag tone="danger">超期</Tag>} onJumpChapter={onJumpChapter} />
        <PromiseGroup title="仍悬(截至本章)" items={stillRest} onJumpChapter={onJumpChapter} />
        <PromiseGroup title="障眼法" items={herring} tag={<Tag tone="fore">障眼法</Tag>} onJumpChapter={onJumpChapter} />
        {rest.length > 0 && (
          <details className="mt-1">
            <summary className="text-f11 uppercase tracking-wider text-faint cursor-pointer list-none">已了结 / 与本章无关 · {rest.length}</summary>
            <div className="mt-1.5">{rest.map((p) => <PromiseRow key={p.id} p={p} onJumpChapter={onJumpChapter} />)}</div>
          </details>
        )}
      </>}
    </div>
  )
}

function MotifRow({ m, evidence, highlight }) {
  // 块三:点行 = 选中该母题 → 发通用 focus(主编聚焦该母题,不跳转)。
  const { setFocus } = useSelection()
  const pick = () => setFocus({
    type: 'motif', id: m.id, label: m.name,
    payload: { theme: m.theme, evidence: evidence || null },
    origin: 'panel',
  })
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

function MotifsPanel({ motifs, seq }) {
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
          : touched.map((m) => <MotifRow key={m.id} m={m} evidence={evById.get(m.id)} highlight />)}
        {rest.length > 0 && (
          <details className="mt-3">
            <summary className="text-f11 uppercase tracking-wider text-faint cursor-pointer list-none">全书母题 · {rest.length}</summary>
            <div className="mt-1.5">{rest.map((m) => <MotifRow key={m.id} m={m} />)}</div>
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

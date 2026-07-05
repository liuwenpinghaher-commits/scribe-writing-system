import { useEffect, useState } from 'react'
import { ScrollText, GitBranch, Bookmark, TriangleAlert, Layers, Activity, DatabaseZap, Loader2 } from 'lucide-react'
import { api } from './api'
import { SectionTitle, Empty, Skeleton, Tag } from './ui'
import { showToast } from './ui/Toast'

const TIER_LABEL = { chapter: '章级', arc: '卷级', book: '书级' }
const TIER_OPTS = ['chapter', 'arc', 'book']

// 小节容器:标题 + 内容;items 为空不渲染(判空看各桶,与后端 T7「text 恒含标题行」解耦)。
function Block({ icon, title, count, tone, children }) {
  return (
    <div className="mb-3.5 last:mb-0">
      <div className={`flex items-center gap-1.5 text-f11 uppercase tracking-wider mb-1.5 ${tone || 'text-faint'}`}>
        {icon && (() => { const I = icon; return <I size={12} className="shrink-0" /> })()}
        {title}{count != null ? ` · ${count}` : ''}
      </div>
      {children}
    </div>
  )
}

// 一条超期伏笔的「三选一」决策行:立即兑现 / 展期(改窗口 tier)/ 弃置(标障眼法)。
// 均写真库 → 操作后回调父层重拉简报+伏笔,决策项随之消失(反馈闭环)。
function DecisionRow({ p, seq, onActed }) {
  const [busy, setBusy] = useState(false)
  const run = async (fn, okMsg) => {
    if (busy) return
    setBusy(true)
    try { await fn(); showToast(okMsg, { tone: 'ok' }); onActed?.() }
    catch (e) { showToast(e?.body?.detail || e?.message || '操作失败', { tone: 'danger' }) }
    finally { setBusy(false) }
  }
  const changeTier = (tier) => run(
    () => api.editPromise(p.id, { text: p.text, setup_chapter: p.setup_chapter, promise_kind: p.kind || 'promise', tier }),
    `已展期为${TIER_LABEL[tier] || tier}`)
  return (
    <div className="mb-2 pb-2 border-b border-line/50 last:border-0">
      <div className="text-f13 text-ink leading-snug">{p.text}</div>
      <div className="flex items-center gap-1.5 mt-1 flex-wrap">
        <button disabled={busy} onClick={() => run(() => api.advancePromise(p.id, seq), '已在本章兑现')}
          className="h-6 px-2 rounded-md text-f11 bg-ok/10 text-ok hover:bg-ok/20 disabled:opacity-40 cursor-pointer transition-colors">立即兑现</button>
        <label className="inline-flex items-center gap-1 text-f10 text-faint">展期
          <select disabled={busy} value={p.tier || 'chapter'} onChange={(e) => changeTier(e.target.value)}
            className="h-6 rounded-md border border-line bg-canvas px-1 text-f11 text-ink outline-none focus:border-brand cursor-pointer">
            {TIER_OPTS.map((t) => <option key={t} value={t}>{TIER_LABEL[t]}</option>)}
          </select>
        </label>
        <button disabled={busy} onClick={() => run(() => api.markHerring(p.id), '已弃置(标为障眼法)')}
          className="h-6 px-2 rounded-md text-f11 bg-soft text-faint hover:text-danger disabled:opacity-40 cursor-pointer transition-colors">弃置</button>
        {busy && <Loader2 size={12} className="animate-spin text-faint" />}
      </div>
    </div>
  )
}

const Lines = ({ items }) => (
  <div className="space-y-1.5">
    {items.map((t, i) => <div key={i} className="text-f13 text-ink leading-snug whitespace-pre-wrap">{t}</div>)}
  </div>
)

// 章前创作简报(左栏 tab):GET /chapter-brief 渲染各 section;超期伏笔挂三选一决策按钮。
// 判空:看 sections 各桶(arcs/directives/reminders/overdue/heartbeat/loops/injection),
// 不看 text(后端 T7:text 恒含「## 本章创作简报」标题行,据此判空会永远非空)。
export function BriefPanel({ seq }) {
  const [brief, setBrief] = useState(undefined)   // undefined=加载 / null=失败 / object
  const [proms, setProms] = useState([])
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (seq == null) { setBrief(null); return }
    let ignore = false
    setBrief(undefined)
    api.chapterBrief(seq).then((b) => { if (!ignore) setBrief(b && typeof b === 'object' ? b : null) }).catch(() => { if (!ignore) setBrief(null) })
    api.promises().then((p) => { if (!ignore) setProms(Array.isArray(p) ? p : []) }).catch(() => { if (!ignore) setProms([]) })
    return () => { ignore = true }
  }, [seq, tick])

  if (seq == null) return <div><SectionTitle icon={ScrollText}>章前简报</SectionTitle><Empty>选一章查看本章创作简报</Empty></div>
  if (brief === undefined) return <div><SectionTitle icon={ScrollText}>章前简报</SectionTitle><Skeleton className="w-2/3" /><Skeleton className="w-full mt-2" /><Skeleton className="w-3/4 mt-2" /></div>
  if (brief === null) return <div><SectionTitle icon={ScrollText}>章前简报</SectionTitle><Empty>简报加载失败,切走再切回可重试</Empty></div>

  const s = brief.sections || {}
  const arcs = s.arcs || []
  const pd = s.promises || {}
  const directives = pd.directives || []
  const reminders = pd.reminders || []
  const loops = s.loops || {}
  const heartbeat = s.heartbeat || []
  const inj = s.injection || {}
  const chosen = inj.chosen || []
  // 超期决策项:后端 decisions 是文案(无 pid),用 /promises 的 overdue+open 行(带 pid/tier)驱动可操作按钮。
  const overdue = proms.filter((p) => p.overdue && p.status === 'open')

  const empty = arcs.length === 0 && directives.length === 0 && reminders.length === 0
    && overdue.length === 0 && heartbeat.length === 0 && !(loops.weighted > 0) && chosen.length === 0

  return (
    <div>
      <SectionTitle icon={ScrollText} right={`第 ${seq} 章`}>章前简报</SectionTitle>
      {empty ? <Empty>本章暂无简报项</Empty> : (
        <>
          {arcs.length > 0 && (
            <Block icon={GitBranch} title="弧光指令" count={arcs.length} tone="text-brand">
              <div className="space-y-2">
                {arcs.map((t, i) => (
                  <div key={i} className="text-f12 text-ink leading-relaxed whitespace-pre-wrap rounded-md bg-brand/[0.04] px-2 py-1.5 border-l-2 border-brand/40">{t}</div>
                ))}
              </div>
            </Block>
          )}
          {directives.length > 0 && (
            <Block icon={Bookmark} title="伏笔 · 本章指令" count={directives.length}><Lines items={directives} /></Block>
          )}
          {overdue.length > 0 && (
            <Block icon={TriangleAlert} title="伏笔 · 待决策(超期)" count={overdue.length} tone="text-danger font-semibold">
              {overdue.map((p) => <DecisionRow key={p.id} p={p} seq={seq} onActed={() => setTick((t) => t + 1)} />)}
            </Block>
          )}
          {reminders.length > 0 && (
            <Block icon={Bookmark} title="伏笔 · 在窗提醒" count={reminders.length}>
              <div className="text-f12 text-faint leading-snug">{reminders.join('；')}</div>
            </Block>
          )}
          {loops.weighted > 0 && (
            <Block icon={Layers} title="开环账本" tone={loops.over_cap ? 'text-danger font-semibold' : 'text-faint'}>
              <div className="text-f13 text-ink">加权开环 <span className="tnum">{loops.weighted}</span> / {loops.cap}
                {loops.over_cap && <Tag tone="danger">已超上限,先收一条</Tag>}
              </div>
            </Block>
          )}
          {heartbeat.length > 0 && (
            <Block icon={Activity} title="待激活角色" count={heartbeat.length} tone="text-fore">
              <div className="space-y-1">
                {heartbeat.map((h, i) => (
                  <div key={i} className="text-f12 leading-snug">
                    <span className="text-f13 text-ink font-medium">{h.name}</span>
                    <span className="text-faint"> · 上次第{h.last_active}章</span>
                    {h.agenda && <span className="text-fore"> · {h.agenda}</span>}
                  </div>
                ))}
              </div>
            </Block>
          )}
          {chosen.length > 0 && (
            <Block icon={DatabaseZap} title="设定注入清单" count={chosen.length}>
              <div className="space-y-0.5">
                {chosen.map((c, i) => <div key={c.id ?? i} className="text-f12 text-faint leading-snug break-all">· {c.text}</div>)}
                {inj.dropped > 0 && <div className="text-f11 text-faint/60">…另有 {inj.dropped} 条超预算未注入</div>}
              </div>
            </Block>
          )}
        </>
      )}
    </div>
  )
}

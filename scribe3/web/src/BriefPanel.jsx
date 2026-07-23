import { useEffect, useState } from 'react'
import { ScrollText, GitBranch, Bookmark, TriangleAlert, Layers, Activity, DatabaseZap } from 'lucide-react'
import { api } from './api'
import { SectionTitle, Empty, Skeleton, Tag } from './ui'
import { seedChiefCodexWrite } from './lib/chiefSeed.js'

// 小节容器:标题 + 内容;items 为空不渲染(判空看各桶,与后端 T7「text 恒含标题行」解耦)。
function Block({ icon, title, count, tone, children }) {
  return (
    <div className="mb-3.5 last:mb-0">
      <div className={`flex items-center gap-1.5 text-meta uppercase tracking-wider mb-1.5 ${tone || 'text-faint'}`}>
        {icon && (() => { const I = icon; return <I size={12} className="shrink-0" /> })()}
        {title}{count != null ? ` · ${count}` : ''}
      </div>
      {children}
    </div>
  )
}

// 超期伏笔决策:只读展示 + 主编种子(禁止 advance/editPromise/markHerring 作者直写)。
function DecisionRow({ p, seq }) {
  const seed = (hint) => seedChiefCodexWrite('promises', p, hint)
  return (
    <div className="mb-2 pb-2 border-b border-line/50 last:border-0" data-testid="brief-promise-decision">
      <div className="text-f13 text-ink leading-snug">{p.text}</div>
      <div className="flex items-center gap-1.5 mt-1 flex-wrap">
        <button type="button"
          onClick={() => seed(`请在第 ${seq} 章兑现/回收此伏笔,提交写入提案。`)}
          className="h-6 px-2 rounded-md text-meta bg-ok/10 text-ok hover:bg-ok/20 cursor-pointer transition-colors">
          让主编兑现
        </button>
        <button type="button"
          onClick={() => seed(`请展期此伏笔(调整 tier/窗口),提交写入提案。当前 tier=${p.tier || 'chapter'}。`)}
          className="h-6 px-2 rounded-md text-meta bg-soft text-faint hover:text-ink cursor-pointer transition-colors">
          让主编展期
        </button>
        <button type="button"
          onClick={() => seed('请将此伏笔标为障眼法(弃置),提交写入提案。')}
          className="h-6 px-2 rounded-md text-meta bg-soft text-faint hover:text-danger cursor-pointer transition-colors">
          让主编弃置
        </button>
      </div>
    </div>
  )
}

const Lines = ({ items }) => (
  <div className="space-y-1.5">
    {items.map((t, i) => <div key={i} className="text-f13 text-ink leading-snug whitespace-pre-wrap">{t}</div>)}
  </div>
)

// 章前创作简报(左栏 tab):GET /chapter-brief 渲染各 section;超期伏笔挂主编决策种子。
export function BriefPanel({ seq }) {
  const [brief, setBrief] = useState(undefined)   // undefined=加载 / null=失败 / object
  const [proms, setProms] = useState([])

  useEffect(() => {
    if (seq == null) { setBrief(null); return }
    let ignore = false
    setBrief(undefined)
    api.chapterBrief(seq).then((b) => { if (!ignore) setBrief(b && typeof b === 'object' ? b : null) }).catch(() => { if (!ignore) setBrief(null) })
    api.promises().then((p) => { if (!ignore) setProms(Array.isArray(p) ? p : []) }).catch(() => { if (!ignore) setProms([]) })
    return () => { ignore = true }
  }, [seq])

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
              {overdue.map((p) => <DecisionRow key={p.id} p={p} seq={seq} />)}
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
                {inj.dropped > 0 && <div className="text-meta text-faint/60">…另有 {inj.dropped} 条超预算未注入</div>}
              </div>
            </Block>
          )}
        </>
      )}
    </div>
  )
}

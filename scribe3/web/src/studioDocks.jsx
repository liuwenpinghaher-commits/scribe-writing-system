import { useEffect, useMemo, useState } from 'react'
import { FolderTree, Eye, Sparkles, Bookmark, LayoutList, ShieldCheck, MessageSquare, Archive } from 'lucide-react'
import { Rail } from './shell'
import { cn } from './lib/utils'
import { api } from './api'
import { ProjectTree } from './ProjectTree'
import { FramePanel } from './FramePanel'
import { DeducePanel } from './DeducePanel'
import { VersionPanel } from './VersionPanel'
import { ChiefDock } from './ChiefDock'
import { usePref } from './lib/usePref'

// 三栏写作台的「左栏」:VSCode 式竖图标轨 + 一个面板。图标切换:项目树/帧/演绎/伏笔/素材/校验。
// 项目树是第一个 tab(默认),数据面板并列其后 —— 消灭独立第4栏,导航与数据同栏。
export function LeftDock({ tree, selId, expanded, onToggle, onSelect, treeCbs, seq }) {
  const [tab, setTab] = usePref('s3.leftTab', 'tree')
  const [focalizer, setFocalizer] = useState('')
  const [chars, setChars] = useState([])
  const [promises, setPromises] = useState([])
  const [motifs, setMotifs] = useState([])

  useEffect(() => { api.entities().then((es) => setChars(es.filter((e) => e.kind === 'character'))).catch(() => {}) }, [])
  useEffect(() => { api.promises().then((p) => setPromises(Array.isArray(p) ? p : [])).catch(() => {}); api.motifs().then((m) => setMotifs(Array.isArray(m) ? m : [])).catch(() => {}) }, [seq])
  useEffect(() => {
    if (seq == null) { setFocalizer(''); return }
    api.chapter(seq).then((ch) => setFocalizer(ch?.focalizer || '')).catch(() => setFocalizer(''))
  }, [seq])

  const caps = useMemo(() => {
    const base = [
      { key: 'tree', icon: FolderTree, label: '项目树', render: () => (
        <div className="h-full overflow-hidden"><ProjectTree tree={tree} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} {...treeCbs} /></div>
      ) },
    ]
    if (seq == null) return base   // 未选章:只给项目树
    base.push(
      { key: 'frame', icon: Eye, label: '帧/意图', render: () => <div className="p-3"><FramePanel focalizer={focalizer} chapter={seq} /></div> },
      { key: 'deduce', icon: Sparkles, label: '演绎 · 角色限知', render: () => <div className="p-3"><DeducePanel chars={chars} chapter={seq} /></div> },
      { key: 'promise', icon: Bookmark, label: '伏笔', render: () => <PromisesPanel promises={promises} /> },
      { key: 'material', icon: LayoutList, label: '素材 · 母题', render: () => <MotifsPanel motifs={motifs} /> },
    )
    base.push({ key: 'review', icon: ShieldCheck, label: '校验 · QC/泄露', render: () => <QCPanel seq={seq} /> })
    return base
  }, [tree, selId, expanded, seq, focalizer, chars, promises, motifs])

  // tab 失效(如切到无正文的章,校验 tab 消失)→ 回退项目树
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('tree') }, [caps, tab, setTab])

  return (
    <div className="h-full flex min-h-0 bg-surface">
      <Rail side="left" caps={caps} active={active.key} onActive={(k) => setTab(k || active.key)} />
      <div className="flex-1 min-w-0 min-h-0 overflow-y-auto border-l border-line">{active.render()}</div>
    </div>
  )
}

// 三栏写作台的「右栏」:面板 + 竖图标轨(镜像)。图标切换:主编对话/版本存档。
export function RightDock({ sel, chapterSel, seq }) {
  const [tab, setTab] = usePref('s3.rightTab', 'chief')
  const caps = useMemo(() => {
    const c = [{ key: 'chief', icon: MessageSquare, label: '主编', bare: true, render: () => <ChiefDock sel={sel} chapterSel={chapterSel} /> }]
    if (seq != null) c.push({ key: 'versions', icon: Archive, label: '存档', render: () => <div className="p-3"><VersionPanel seq={seq} /></div> })
    return c
  }, [sel, chapterSel, seq])
  const active = caps.find((c) => c.key === tab) || caps[0]
  useEffect(() => { if (!caps.find((c) => c.key === tab)) setTab('chief') }, [caps, tab, setTab])
  return (
    <div className="h-full flex min-h-0 bg-surface">
      <div className={cn('flex-1 min-w-0 min-h-0', active.bare ? '' : 'overflow-y-auto')}>{active.render()}</div>
      <Rail side="right" caps={caps} active={active.key} onActive={(k) => setTab(k || active.key)} />
    </div>
  )
}

function PromisesPanel({ promises }) {
  return (
    <div className="p-3">
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1.5">伏笔 · 埋/收</div>
      {promises.length === 0 ? <div className="text-[13px] text-faint/50">无</div> : promises.map((p) => (
        <div key={p.id} className="mb-2 pb-2 border-b border-line/50 last:border-0">
          <div className="text-[12.5px] text-ink leading-snug">{p.text}</div>
          <div className="text-[10px] text-faint mt-0.5">埋:第{p.setup_chapter ?? '—'}章 · {p.status === 'paid' ? '已收' : '待收'}</div>
        </div>
      ))}
    </div>
  )
}

function MotifsPanel({ motifs }) {
  return (
    <div className="p-3">
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1.5">母题</div>
      {motifs.length === 0 ? <div className="text-[13px] text-faint/50">无</div> : motifs.map((m) => (
        <div key={m.id} className="mb-2.5 pb-2.5 border-b border-line/50 last:border-0">
          <div className="text-[13px] font-semibold text-ink">{m.name}</div>
          {m.theme && <div className="text-[12px] text-fore mt-0.5">{m.theme}</div>}
          {m.unfolding && <div className="text-[12px] text-faint mt-0.5 leading-snug">{m.unfolding}</div>}
        </div>
      ))}
    </div>
  )
}

function QCPanel({ seq }) {
  const [qc, setQc] = useState(null)
  useEffect(() => { api.qc(seq).then(setQc).catch(() => setQc(null)) }, [seq])
  const n = (x) => Array.isArray(x) ? x.length : (x || 0)
  return (
    <div className="p-3">
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1.5">确定性 QC · 本章正文</div>
      {!qc ? <div className="text-[13px] text-faint/50">保存正文后自动体检</div> : (
        <div className="text-[12.5px] text-ink space-y-1">
          <div>复读:{n(qc.repetition)}</div>
          <div>排比:{n(qc.structural)}</div>
          <div>升华:{n(qc.purple)}</div>
          <div>AI腔:{n(qc.ai_tics)}</div>
          <div>过饱和:{n(qc.oversaturation)}</div>
        </div>
      )}
    </div>
  )
}

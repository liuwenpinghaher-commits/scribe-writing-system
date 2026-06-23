import { useEffect, useState } from 'react'
import {
  ChevronLeft, ChevronRight, Save, MessagesSquare, ShieldCheck, Bookmark,
  Users, AlignCenter, Search, CircleAlert, CircleCheck, Lock,
  BookText, LayoutList, Flame,
} from 'lucide-react'
import { api } from './api'
import { Shell } from './shell'
import { Btn, SectionTitle, Empty, Row, Tag } from './ui'
import { ProseEditor } from './editor/ProseEditor'
import { DraftCard } from './editor/DraftCard'
import { WriteChat } from './WriteChat'
import { NorthStarBar } from './NorthStarBar'

// 写作台(对话驱动):中区手稿 + 右轨主编对话出草稿卡。限知/校验后台支撑。与推演台共用同一份数据。
export function WriteLayout({ work }) {
  api.setWork(work)
  const [chapter, setChapter] = useState(1)
  const [entities, setEntities] = useState([])
  const [focalizer, setFocalizer] = useState('')
  const [prose, setProse] = useState('')
  const [proposal, setProposal] = useState(null)
  const [seedQuote, setSeedQuote] = useState('')
  const [lastQuote, setLastQuote] = useState('')
  const [qc, setQc] = useState(null)
  const [leaks, setLeaks] = useState(0)
  const [causal, setCausal] = useState([])
  const [promises, setPromises] = useState([])
  const [chapters, setChapters] = useState([])
  const [facts, setFacts] = useState([])
  const [events, setEvents] = useState([])
  const [motifs, setMotifs] = useState([])
  const [recallQ, setRecallQ] = useState('')
  const [recallHits, setRecallHits] = useState([])
  const [focusMode, setFocusMode] = useState(false)
  const [saved, setSaved] = useState(true)
  const [leftActive, setLeftActive] = useState('outline')
  const [rightActive, setRightActive] = useState('chat')
  const [tick, setTick] = useState(0)

  useEffect(() => { api.entities().then(setEntities); api.motifs().then(setMotifs) }, [tick])
  useEffect(() => {
    api.chapter(chapter).then((ch) => { setProse(ch?.prose || ''); setSaved(true) })
    api.causal(chapter).then(setCausal)
    api.promises().then(setPromises)
    api.qc(chapter).then(setQc)
    api.chapters().then(setChapters)
    api.facts(chapter).then(setFacts)
    api.events(chapter).then(setEvents)
  }, [chapter, tick])
  const runRecall = async (e) => { e.preventDefault(); if (!recallQ.trim()) return; setRecallHits(await api.recall(recallQ.trim(), 8)) }

  const chars = entities.filter((e) => e.kind === 'character')
  const focName = (chars.find((c) => c.id === focalizer) || {}).name || '—'
  const wordCount = prose.replace(/\s/g, '').length
  const openProm = promises.filter((p) => p.status === 'open')
  const overdue = (p) => p.status === 'open' && p.setup_chapter + 3 < chapter
  const qcN = qc ? (qc.repetition?.length || qc.repetition || 0) + (qc.structural?.length || qc.structural || 0) + (qc.purple?.length || qc.purple || 0) : 0

  const persist = async (text) => {
    const r = await api.saveChapter(chapter, text, '', focalizer)
    setQc(r.qc); setLeaks(r.leaks || 0); setSaved(true)
    api.ingest(chapter).catch(() => {}); setTick((t) => t + 1)
  }
  const acceptProposal = async () => {
    const p = proposal; if (!p) return
    let next = prose
    if (p.scope === 'chapter') next = p.prose
    else if (p.scope === 'append') next = (prose ? prose + '\n\n' : '') + p.prose
    else next = (lastQuote && prose.includes(lastQuote)) ? prose.replace(lastQuote, p.prose) : (prose ? prose + '\n\n' + p.prose : p.prose)
    setProse(next); setProposal(null); setLastQuote('')
    await persist(next)
  }
  const save = () => persist(prose)
  const discussSel = (text) => { if (!text?.trim()) return; setLastQuote(text); setSeedQuote(text); setRightActive('chat') }

  const topbarMid = (
    <div className="shrink-0 border-b border-line bg-surface px-4 h-11 flex items-center gap-2">
      <button onClick={() => setChapter((c) => Math.max(1, c - 1))} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="上一章"><ChevronLeft size={16} /></button>
      <span className="text-[13px] text-ink tnum w-14 text-center">第 {chapter} 章</span>
      <button onClick={() => setChapter((c) => c + 1)} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="下一章"><ChevronRight size={16} /></button>
      <span className="text-[12px] text-faint ml-2">视角</span>
      <select value={focalizer} onChange={(e) => setFocalizer(e.target.value)}
        className="h-7 rounded-lg border border-line bg-canvas px-2 text-[12.5px] text-ink outline-none focus:border-brand cursor-pointer">
        <option value="">（未定)</option>
        {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <div className="ml-auto flex items-center gap-2">
        {leaks > 0 && <Tag tone="danger">穿帮 {leaks}</Tag>}
        <span className="text-[11px] text-faint tnum">{wordCount} 字</span>
        <button onClick={() => setFocusMode((v) => !v)} title="专注模式" aria-pressed={focusMode}
          className={`w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer ${focusMode ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}><AlignCenter size={15} /></button>
        <Btn variant="soft" onClick={save} className={saved ? 'text-ok' : ''}><Save size={14} />{saved ? '已存' : '保存'}</Btn>
      </div>
    </div>
  )

  const center = (
    <div className="flex flex-col h-full">
      <NorthStarBar />
      {topbarMid}
      <div className="flex-1 min-h-0 overflow-y-auto bg-canvas">
        <div className="max-w-[48rem] mx-auto px-6 py-8">
          <DraftCard proposal={proposal} streaming={false} onAccept={acceptProposal} onReject={() => { setProposal(null); setLastQuote('') }} />
          <ProseEditor value={prose} onChange={(t) => { setProse(t); setSaved(false) }}
            chapterKey={`${work}-${chapter}`} focusMode={focusMode} onDiscuss={discussSel}
            placeholder="右侧跟主编提思路让它写,或直接在此落笔。" />
        </div>
      </div>
    </div>
  )

  const leftCaps = [
    { key: 'outline', label: '大纲 · 章节', icon: BookText, render: () => (
      <div>
        <SectionTitle icon={BookText} right={`${chapters.length} 章`}>章节</SectionTitle>
        {chapters.length === 0 && <Empty>暂无章节,写完保存即生成</Empty>}
        {chapters.map((c) => (
          <button key={c.seq} onClick={() => setChapter(c.seq)}
            className={`w-full text-left rounded-lg px-2.5 py-2 mb-0.5 text-[13px] transition-colors cursor-pointer ${c.seq === chapter ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <span className="tnum text-faint mr-1.5">第{c.seq}章</span>{c.title || '无题'}
          </button>
        ))}
      </div>
    ) },
    { key: 'structure', label: '本章结构 · fabula', icon: LayoutList, render: () => (
      <div>
        <SectionTitle icon={LayoutList} right={`${events.length}`}>本章事件</SectionTitle>
        {events.length === 0 ? <Empty>本章未设计事件</Empty> : events.map((ev) => (
          <Row key={ev.id}><Tag tone="brand">{ev.type}</Tag><span className="ml-1 text-faint">{ev.id}</span>{!ev.goal && <span className="ml-1 text-danger">· 缺目标</span>}</Row>
        ))}
        <div className="h-3" />
        <SectionTitle right={`${facts.length}`}>本章事实</SectionTitle>
        {facts.length === 0 ? <Empty>无</Empty> : facts.slice(0, 60).map((f) => (
          <Row key={f.id} icon={f.secret ? Lock : undefined}><span className="text-faint">{f.attribute}</span>:{f.value}</Row>
        ))}
      </div>
    ) },
    { key: 'motifs', label: '母题', icon: Flame, render: () => (
      <div>
        <SectionTitle icon={Flame} right={`${motifs.length}`}>母题 · 参照不透支</SectionTitle>
        {motifs.length === 0 ? <Empty>无</Empty> : motifs.map((m) => (
          <div key={m.id} className="mb-2.5 pb-2.5 border-b border-line/50 last:border-0">
            <div className="text-[13px] font-semibold text-ink">{m.name}</div>
            {m.theme && <div className="text-[12px] text-fore mt-0.5">{m.theme}</div>}
            {m.unfolding && <div className="text-[12px] text-faint mt-0.5 leading-snug">{m.unfolding}</div>}
          </div>
        ))}
      </div>
    ) },
    { key: 'recall', label: '设定检索 · 语义', icon: Search, render: () => (
      <div>
        <SectionTitle icon={Search}>语义召回设定</SectionTitle>
        <form onSubmit={runRecall} className="flex gap-1.5 mb-3">
          <input value={recallQ} onChange={(e) => setRecallQ(e.target.value)} placeholder="按意思搜,如「炼丹复活」"
            className="flex-1 h-8 rounded-lg border border-line bg-canvas px-2.5 text-[13px] outline-none focus:border-brand" />
          <Btn variant="primary" size="sm" type="submit">搜</Btn>
        </form>
        {recallHits.length === 0 ? <Empty>输入意思,向量召回最相关设定(非字面)</Empty>
          : recallHits.map((f) => <Row key={f.id}><span className="text-faint">{f.attribute}</span>:{f.value}</Row>)}
      </div>
    ) },
  ]

  const rightCaps = [
    { key: 'chat', label: '主编对话', icon: MessagesSquare, bare: true, render: () => (
      <WriteChat chapter={chapter} focalizer={focalizer} seedQuote={seedQuote}
        onSeedUsed={() => setSeedQuote('')} onProposal={(p) => setProposal(p)} />
    ) },
    { key: 'verify', label: '校验 · 双层QC', icon: ShieldCheck, badge: qcN + leaks + causal.length, render: () => (
      <div>
        <SectionTitle icon={ShieldCheck}>软校验 · 不挡接受</SectionTitle>
        {leaks > 0 ? <Row tone="danger" icon={Lock}>限知泄露 {leaks} 处:写了 {focName} 不该知道的私密</Row> : <Row tone="ok" icon={CircleCheck}>限知:无泄露</Row>}
        {qcN > 0 ? <Row tone="warn" icon={CircleAlert}>确定性 QC:{qcN} 处(复读/排比/升华)</Row> : <Row tone="ok" icon={CircleCheck}>确定性 QC 干净</Row>}
        {causal.length > 0 ? <Row tone="danger" icon={CircleAlert}>因果违规 {causal.length} 处</Row> : <Row tone="ok" icon={CircleCheck}>因果完整</Row>}
        <div className="text-[11px] text-faint mt-2 leading-snug">保存/接受草稿时自动跑。北极星意图喂主编当写作纲领。</div>
      </div>
    ) },
    { key: 'foreshadow', label: '伏笔', icon: Bookmark, badge: openProm.filter(overdue).length, render: () => (
      <div>
        <SectionTitle icon={Bookmark} right={`${openProm.length} 未回收`}>伏笔 · 超期红</SectionTitle>
        {openProm.length === 0 ? <Empty>无未回收伏笔</Empty> : openProm.map((p) => (
          <Row key={p.id} tone={overdue(p) ? 'danger' : 'fore'} icon={Bookmark}>{p.text.slice(0, 40)}<span className="text-faint"> · 第{p.setup_chapter}章埋{overdue(p) ? ' · 超期' : ''}</span></Row>
        ))}
      </div>
    ) },
    { key: 'present', label: '本章在场', icon: Users, render: () => (
      <div>
        <SectionTitle icon={Users}>可在场角色 · 点击设为视角</SectionTitle>
        {chars.length === 0 ? <Empty>无角色</Empty> : chars.map((c) => (
          <button key={c.id} onClick={() => setFocalizer(c.id)}
            className={`w-full flex items-center gap-2 rounded-lg px-2.5 py-2 mb-0.5 text-[13px] transition-colors cursor-pointer ${c.id === focalizer ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <span className={`w-2 h-2 rounded-full shrink-0 ${c.id === focalizer ? 'bg-brand' : 'bg-line'}`} />
            <span className="truncate">{c.name}</span>{c.id === focalizer && <span className="ml-auto text-[11px] text-brand">视角</span>}
          </button>
        ))}
      </div>
    ) },
  ]

  return <Shell center={center} left={{ caps: leftCaps, active: leftActive, onActive: setLeftActive }}
    right={{ caps: rightCaps, active: rightActive, onActive: setRightActive }} />
}

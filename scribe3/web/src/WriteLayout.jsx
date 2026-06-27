import { useEffect, useState } from 'react'
import {
  ChevronLeft, ChevronRight, Save, MessagesSquare, ShieldCheck, Bookmark,
  Users, AlignCenter, Search, CircleAlert, CircleCheck, Lock,
  BookText, LayoutList, Flame, Sparkles, Eye,
} from 'lucide-react'
import { api } from './api'
import { Shell } from './shell'
import { Btn, SectionTitle, Empty, Row, Tag } from './ui'
import { ProseEditor } from './editor/ProseEditor'
import { applyProposal } from './editor/applyProposal.js'
import { DraftCard } from './editor/DraftCard'
import { WriteChat } from './WriteChat'
import { DeducePanel } from './DeducePanel'
import { NorthStarBar } from './NorthStarBar'
import { loadButtons, addButton } from './lib/rewriteButtons.js'
import { VersionPanel } from './VersionPanel.jsx'
import { FramePanel } from './FramePanel.jsx'
import { InputDialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'

// 写作台(对话驱动):中区手稿 + 右轨主编对话出草稿卡。限知/校验后台支撑。与推演台共用同一份数据。
export function WriteLayout({ work }) {
  api.setWork(work)
  const toast = useToast()
  const [chapter, setChapter] = useState(1)
  const [entities, setEntities] = useState([])
  const [focalizer, setFocalizer] = useState('')
  const [prose, setProse] = useState('')
  const [proposal, setProposal] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [seedQuote, setSeedQuote] = useState('')
  const [lastQuote, setLastQuote] = useState('')
  const [lastSel, setLastSel] = useState(null)
  const [qc, setQc] = useState(null)
  const [leaks, setLeaks] = useState(0)
  const [guard, setGuard] = useState({ leaks: [], qc: { repetition: 0, structural: 0, purple: 0 } })
  const [guardOn, setGuardOn] = useState(() => localStorage.getItem('scribe3:guardOn') !== '0')
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
  const [btns, setBtns] = useState(() => loadButtons(work))
  const [leftActive, setLeftActive] = useState('outline')
  const [rightActive, setRightActive] = useState('chat')
  const [tick, setTick] = useState(0)
  const [verTick, setVerTick] = useState(0)
  const [dlg, setDlg] = useState(null)

  useEffect(() => {
    if (!guardOn) { setGuard({ leaks: [], qc: { repetition: 0, structural: 0, purple: 0 } }); return }
    if (!prose.trim()) return
    let alive = true
    const t = setTimeout(() => {
      api.checkProse(chapter, prose, focalizer)
        .then((r) => { if (alive) setGuard({ leaks: r.leaks || [], qc: r.qc || { repetition: 0, structural: 0, purple: 0 } }) })
        .catch(() => {})
    }, 3000)
    return () => { alive = false; clearTimeout(t) }
  }, [prose, chapter, focalizer, guardOn])

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
    const r = applyProposal(prose, p, lastSel)
    if (!r.ok && r.drifted) {
      toast('原文已变动,请重新选中要替换的文字', { tone: 'danger' })
      setProposal(null); return
    }
    setProse(r.next); setProposal(null); setLastQuote(''); setLastSel(null)
    await persist(r.next)
  }
  const acceptCandidate = async (text) => {
    const r = applyProposal(prose, { scope: 'selection', prose: text }, lastSel)
    if (!r.ok && r.drifted) { toast('原文已变动,请重新选中要替换的文字', { tone: 'danger' }); setCandidates([]); return }
    setProse(r.next); setCandidates([]); setLastQuote(''); setLastSel(null)
    await persist(r.next)
  }
  const save = () => persist(prose)
  const discussSel = (sel) => {
    const text = typeof sel === 'string' ? sel : sel?.text
    if (!text?.trim()) return
    setLastSel(typeof sel === 'string' ? null : sel)
    setLastQuote(text)
    setSeedQuote(`把这段改一下,给我 2-3 个侧重不同的候选:「${text}」`)
    setCandidates([])
    setRightActive('chat')
  }
  const deduceToChief = (name, prose) => { setSeedQuote(`【${name}·演绎草稿(限知素材)】\n${prose}\n\n请据这份演绎草稿,以作者视角写本章。`); setRightActive('chat') }

  const topbarMid = (
    <div className="shrink-0 border-b border-line bg-surface px-4 h-11 flex items-center gap-2">
      <button onClick={() => setChapter((c) => Math.max(1, c - 1))} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="上一章"><ChevronLeft size={16} /></button>
      <span className="text-[13px] text-ink tnum w-14 text-center">第 {chapter} 章</span>
      <button onClick={() => setChapter((c) => c + 1)} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="下一章"><ChevronRight size={16} /></button>
      <span className="text-[12px] text-faint ml-2">本章视角</span>
      <select value={focalizer} onChange={(e) => setFocalizer(e.target.value)} title="默认作者视角(全知);选某角色=本章限知该角色,开启穿帮校验"
        className="h-7 rounded-lg border border-line bg-canvas px-2 text-[12.5px] text-ink outline-none focus:border-brand cursor-pointer">
        <option value="">作者视角(全知)</option>
        {chars.map((c) => <option key={c.id} value={c.id}>限知:{c.name}</option>)}
      </select>
      <div className="ml-auto flex items-center gap-2">
        {guardOn && focalizer && guard.leaks.length > 0 && (
          <span title={guard.leaks.map((l) => l.marker).join('、')}
                className="text-[11px] text-danger tnum cursor-default">🔒 {guard.leaks.length}</span>
        )}
        {guardOn && (guard.qc.repetition + guard.qc.purple) > 0 && (
          <span title="复读/升华(AI腔)" className="text-[11px] text-faint tnum cursor-default">⚠ {guard.qc.repetition + guard.qc.purple}</span>
        )}
        <button onClick={() => { const v = !guardOn; setGuardOn(v); localStorage.setItem('scribe3:guardOn', v ? '1' : '0') }}
                title={guardOn ? '护栏开(点击关闭,完全静默)' : '护栏关'}
                className={`text-[11px] px-1.5 h-6 rounded-lg cursor-pointer ${guardOn ? 'text-brand' : 'text-faint'}`}>护栏</button>
        <span className="text-[11px] text-faint tnum">{wordCount} 字</span>
        <button onClick={() => setFocusMode((v) => !v)} title="专注模式" aria-pressed={focusMode}
          className={`w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer ${focusMode ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}><AlignCenter size={15} /></button>
        <Btn variant="soft" onClick={save} className={saved ? 'text-ok' : ''}><Save size={14} />{saved ? '已存' : '保存'}</Btn>
        <Btn variant="soft" onClick={() => setDlg({ kind: 'checkpoint' })}>存档点</Btn>
        <Btn variant="primary" onClick={async () => {
          await persist(prose)
          await api.checkpoint(chapter, prose, '定稿', 'final', qc || {})
          setVerTick((t) => t + 1)
        }}>存为正文</Btn>
      </div>
    </div>
  )

  const center = (
    <div className="flex flex-col h-full">
      <NorthStarBar />
      {topbarMid}
      {lastSel && (
        <div className="flex flex-wrap gap-1.5 px-3 py-2 border-b border-line bg-surface">
          {btns.map((b) => (
            <button key={b} onClick={() => {
              setSeedQuote(`把这段按「${b}」改,给我 2-3 个候选:「${lastSel.text}」`)
              setCandidates([]); setRightActive('chat')
            }} className="h-6 px-2 rounded-lg border border-line text-[11px] text-ink hover:bg-soft cursor-pointer">{b}</button>
          ))}
          <button onClick={() => setDlg({ kind: 'rewrite' })} className="h-6 px-2 rounded-lg border border-dashed border-line text-[11px] text-faint hover:bg-soft cursor-pointer">+ 存为按钮</button>
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-y-auto bg-canvas">
        <div className="max-w-[48rem] mx-auto px-6 py-8">
          <DraftCard proposal={proposal} candidates={candidates} streaming={false} onAccept={acceptProposal} onReject={() => { setProposal(null); setCandidates([]); setLastQuote(''); setLastSel(null) }} onAcceptCandidate={acceptCandidate} />
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
    { key: 'versions', label: '存档', icon: Bookmark, render: () => (
      <VersionPanel seq={chapter} refreshKey={verTick}
        onRestore={(text) => { setProse(text); persist(text) }} />
    ) },
    { key: 'frame', label: '帧/意图', icon: Eye, render: () => (
      <FramePanel focalizer={focalizer} chapter={chapter} />
    ) },
  ]

  const rightCaps = [
    { key: 'chat', label: '主编对话', icon: MessagesSquare, bare: true, render: () => (
      <WriteChat chapter={chapter} focalizer={focalizer} seedQuote={seedQuote}
        onSeedUsed={() => setSeedQuote('')} onProposal={(p) => {
          if (p.scope === 'selection') setCandidates((cs) => [...cs, p.prose])
          else setProposal(p)
        }} />
    ) },
    { key: 'deduce', label: '演绎 · 角色限知', icon: Sparkles, render: () => (
      <DeducePanel chars={chars} chapter={chapter} onToChief={deduceToChief} />
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

  return (
    <>
      <Shell center={center} left={{ caps: leftCaps, active: leftActive, onActive: setLeftActive }}
        right={{ caps: rightCaps, active: rightActive, onActive: setRightActive }} />
      <InputDialog
        open={!!dlg}
        title={dlg?.kind === 'checkpoint' ? '给这个存档点起个名(可留空)' : '存一个常用改写指令(如「压缩、去形容词」)'}
        placeholder={dlg?.kind === 'checkpoint' ? '例:重写结尾前' : '例:压缩、去形容词'}
        confirmText={dlg?.kind === 'checkpoint' ? '存档' : '保存按钮'}
        onConfirm={async (val) => {
          if (dlg?.kind === 'checkpoint') {
            await api.checkpoint(chapter, prose, val || '', 'checkpoint', qc || {})
            setVerTick((t) => t + 1)
          } else if (dlg?.kind === 'rewrite') {
            if (val) setBtns(addButton(work, val))
          }
        }}
        onClose={() => setDlg(null)}
      />
    </>
  )
}

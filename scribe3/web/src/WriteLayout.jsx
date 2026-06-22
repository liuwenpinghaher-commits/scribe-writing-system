import { useEffect, useState } from 'react'
import {
  BookText, LayoutList, Flame, Search, Eye, Drama, ShieldCheck, Bookmark,
  Feather, Save, Sparkles, Radio, ChevronLeft, ChevronRight,
  CircleAlert, CircleCheck, Lock,
} from 'lucide-react'
import { api } from './api'
import { Shell } from './shell'
import { Btn, SectionTitle, Empty, Row, Tag } from './ui'

// 写作台:Shell(左轨结构 / 中区限知散文 / 右轨知识帧·反讽·QC·伏笔)。work 由父级传,key 切书重挂。
export function WriteLayout({ work }) {
  api.setWork(work)   // 每次渲染同步当前书(在 effect 取数前生效)

  const [chapter, setChapter] = useState(1)
  const [entities, setEntities] = useState([])
  const [focalizer, setFocalizer] = useState('')
  const [facts, setFacts] = useState([])
  const [events, setEvents] = useState([])
  const [frame, setFrame] = useState([])
  const [causal, setCausal] = useState([])
  const [irony, setIrony] = useState([])
  const [promises, setPromises] = useState([])
  const [motifs, setMotifs] = useState([])
  const [chapters, setChapters] = useState([])
  const [qc, setQc] = useState(null)
  const [prose, setProse] = useState('')
  const [rendering, setRendering] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [tick, setTick] = useState(0)
  const [live, setLive] = useState(false)
  const [recallQ, setRecallQ] = useState('')
  const [recallHits, setRecallHits] = useState([])
  const [leftActive, setLeftActive] = useState('outline')
  const [rightActive, setRightActive] = useState('frame')

  useEffect(() => {
    const es = api.live(() => setTick((t) => t + 1))
    es.onopen = () => setLive(true); es.onerror = () => setLive(false)
    return () => es.close()
  }, [])

  useEffect(() => {
    api.entities().then((es) => {
      setEntities(es)
      const c = es.filter((e) => e.kind === 'character')
      if (c.length) setFocalizer((f) => f || c[0].id)
    })
    api.chapters().then(setChapters)
    api.promises().then(setPromises)
    api.motifs().then(setMotifs)
  }, [tick])

  useEffect(() => {
    api.facts(chapter).then(setFacts)
    api.events(chapter).then(setEvents)
    api.causal(chapter).then(setCausal)
    api.qc(chapter).then(setQc)
  }, [chapter, tick])

  useEffect(() => { setSaved(false); api.chapter(chapter).then((ch) => setProse(ch?.prose || '')) }, [chapter])

  useEffect(() => {
    if (!focalizer) return
    api.frame(focalizer, chapter).then(setFrame)
    api.irony(focalizer, chapter).then(setIrony)
  }, [focalizer, chapter, tick])

  const chars = entities.filter((e) => e.kind === 'character')
  const focName = (chars.find((c) => c.id === focalizer) || {}).name || '—'

  const render = async () => {
    setRendering(true)
    try { const r = await api.render(focalizer, chapter); setProse(r.prose || '(空)'); setSaved(false) }
    catch (e) { setProse('渲染失败:' + e.message) } finally { setRendering(false) }
  }
  const save = async () => { await api.saveChapter(chapter, prose, '', focalizer); setSaved(true); api.qc(chapter).then(setQc); setTick((t) => t + 1) }
  const ingest = async () => { setIngesting(true); try { await api.ingest(chapter); setTick((t) => t + 1) } finally { setIngesting(false) } }
  const runRecall = async (e) => { e.preventDefault(); if (!recallQ.trim()) return; setRecallHits(await api.recall(recallQ.trim(), 8)) }

  const wordCount = prose.replace(/\s/g, '').length
  const overdue = (p) => p.status === 'open' && p.setup_chapter + 3 < chapter
  const openProm = promises.filter((p) => p.status === 'open')
  const qcIssues = qc ? (qc.repetition?.length || 0) + (qc.structural?.length || 0) + (qc.purple?.length || 0) : 0

  const leftCaps = [
    { key: 'outline', label: '大纲 · 章节', icon: BookText, render: () => (
      <div>
        <SectionTitle icon={BookText} right={`${chapters.length} 章`}>章节</SectionTitle>
        {chapters.length === 0 && <Empty>暂无章节,渲染后保存即生成</Empty>}
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
    { key: 'frame', label: '知识帧', icon: Eye, render: () => (
      <div>
        <div className="text-[12px] text-faint mb-2 leading-snug"><span className="text-ink font-medium">{focName}</span> 截至第{chapter}章所知——<span className="text-brand">渲染只用这些,帧外私密写不出</span>。</div>
        <SectionTitle icon={Eye} right={`${frame.length}`}>此刻所知</SectionTitle>
        {frame.length === 0 ? <Empty>该视角暂无已知事实</Empty> : frame.map((f) => (
          <Row key={f.id} icon={f.secret ? Lock : undefined}><span className="text-faint">{f.attribute}</span>:{f.value}</Row>
        ))}
      </div>
    ) },
    { key: 'irony', label: '戏剧反讽', icon: Drama, badge: irony.length, render: () => (
      <div>
        <div className="text-[12px] text-faint mb-2 leading-snug">读者已知、而 <span className="text-ink">{focName}</span> 不知——写出煎熬,但他的台词只能用帧内信息。</div>
        <SectionTitle icon={Drama} right={`${irony.length}`}>反讽点</SectionTitle>
        {irony.length === 0 ? <Empty>无</Empty> : irony.map((f) => <Row key={f.id} tone="irony" icon={Drama}>{f.value}</Row>)}
      </div>
    ) },
    { key: 'verify', label: '校验 · 双层 QC', icon: ShieldCheck, badge: causal.length + qcIssues, render: () => (
      <div>
        <SectionTitle icon={ShieldCheck}>连贯性(因果完整)</SectionTitle>
        {causal.length === 0 ? <Row tone="ok" icon={CircleCheck}>干净</Row>
          : causal.map((v, i) => <Row key={i} tone="danger" icon={CircleAlert}>{v.event}:{v.reason}</Row>)}
        <div className="h-3" />
        <SectionTitle right={qcIssues ? `${qcIssues} 处` : ''}>质检(已存正文 · 确定性)</SectionTitle>
        {!qc ? <Empty>—</Empty> : qcIssues === 0 ? <Row tone="ok" icon={CircleCheck}>干净</Row> : (
          <>
            {qc.repetition?.length > 0 && <Row tone="danger" icon={CircleAlert}>跨段复读 {qc.repetition.length} 处</Row>}
            {qc.structural?.length > 0 && <Row tone="danger" icon={CircleAlert}>排比/单字断句 {qc.structural.length} 处</Row>}
            {qc.purple?.length > 0 && <Row tone="danger" icon={CircleAlert}>升华句 {qc.purple.length} 处</Row>}
          </>
        )}
        <div className="mt-2 text-[11px] text-faint/80 leading-snug">语义判官(双高潮/声音崩)走 Hermes,见 s3_discipline_check。</div>
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
  ]

  const topbar = (
    <header className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-2 px-4">
      <button onClick={() => setChapter((c) => Math.max(1, c - 1))} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="上一章"><ChevronLeft size={16} /></button>
      <span className="text-[13px] text-ink tnum w-14 text-center">第 {chapter} 章</span>
      <button onClick={() => setChapter((c) => c + 1)} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer" aria-label="下一章"><ChevronRight size={16} /></button>
      <span className="ml-auto inline-flex items-center gap-1 text-[11px]" title={live ? 'LIVE 已连·改一处处处同步' : 'LIVE 未连'}>
        <Radio size={12} className={live ? 'text-ok' : 'text-faint'} /><span className={live ? 'text-ok' : 'text-faint'}>{live ? 'LIVE' : '离线'}</span>
      </span>
    </header>
  )

  const center = (
    <div className="flex flex-col h-full">
      <div className="shrink-0 border-b border-line bg-surface px-4 h-12 flex items-center gap-2">
        <span className="text-[12px] text-faint">视角</span>
        <select value={focalizer} onChange={(e) => setFocalizer(e.target.value)}
          className="h-8 rounded-lg border border-line bg-canvas px-2.5 text-[13px] text-ink outline-none focus:border-brand cursor-pointer">
          {chars.length === 0 && <option value="">（无角色)</option>}
          {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <span className="text-[11px] text-faint">此刻知 <span className="text-brand font-medium tnum">{frame.length}</span> 条</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[11px] text-faint tnum">{wordCount} 字</span>
          <Btn variant="primary" onClick={render} disabled={rendering || !focalizer}><Feather size={14} />{rendering ? '渲染中…' : '渲染本场'}</Btn>
          <Btn variant="soft" onClick={save} disabled={!prose || rendering} className={saved ? 'text-ok' : ''}><Save size={14} />{saved ? '已存' : '保存'}</Btn>
          <Btn variant="ghost" onClick={ingest} disabled={!saved || ingesting} title="读定稿抽『谁新知道什么』→更新账本"><Sparkles size={14} />{ingesting ? '回写中…' : '回写'}</Btn>
        </div>
      </div>
      <div className="px-4 py-1.5 shrink-0 text-[11.5px] text-faint border-b border-line/60">
        限知渲染:只喂 <span className="text-ink">{focName}</span> 的知识帧({frame.length} 条),帧外私密物理上写不进去。
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto bg-canvas">
        <div className="max-w-[70ch] mx-auto px-6 py-8">
          {rendering ? (
            <div className="space-y-3 animate-pulse">
              {[...Array(6)].map((_, i) => <div key={i} className="h-4 bg-soft rounded" style={{ width: `${70 + (i % 3) * 10}%` }} />)}
              <div className="text-[12px] text-faint pt-2">渲染中(走 Hermes,doubao 可能较慢)…</div>
            </div>
          ) : (
            <textarea value={prose} onChange={(e) => { setProse(e.target.value); setSaved(false) }}
              placeholder={`选视角 → 渲染本场。散文只渲染 ${focName} 知道的事。`}
              className="manuscript w-full min-h-[60vh] bg-transparent text-ink outline-none resize-none placeholder:text-faint/50 placeholder:italic placeholder:font-sans placeholder:text-[14px]" />
          )}
        </div>
      </div>
    </div>
  )

  return (
    <Shell topbar={topbar} center={center}
      left={{ caps: leftCaps, active: leftActive, onActive: setLeftActive }}
      right={{ caps: rightCaps, active: rightActive, onActive: setRightActive }} />
  )
}

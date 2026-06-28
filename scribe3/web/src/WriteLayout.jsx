import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, Save, MessagesSquare, ShieldCheck, ShieldOff, Bookmark,
  Users, AlignCenter, Search, CircleAlert, CircleCheck, Lock,
  BookText, LayoutList, Flame, Sparkles, Eye, ChevronDown, Check,
} from 'lucide-react'
import { api } from './api'
import { verifyIssues } from './verifyIssues.js'
import { Shell } from './shell'
import { Btn, SectionTitle, Empty, Row, Tag } from './ui'
import { Chip } from './ui/Chip'
import { ProseEditor } from './editor/ProseEditor'
import { applyProposal } from './editor/applyProposal.js'
import { DraftCard } from './editor/DraftCard'
import { WriteChat } from './WriteChat'
import { DeducePanel } from './DeducePanel'
import { NorthStarBar } from './NorthStarBar'
import { loadButtons, addButton } from './lib/rewriteButtons.js'
import { chapterLabel } from './chapterLabel.js'
import { VersionPanel } from './VersionPanel.jsx'
import { FramePanel } from './FramePanel.jsx'
import { InputDialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'

// 写作台(对话驱动):中区手稿 + 右轨主编对话出草稿卡。限知/校验后台支撑。与推演台共用同一份数据。
export function WriteLayout({ work }) {
  api.setWork(work)
  const toast = useToast()
  const proseEditorRef = useRef(null)  // F-05: ref to ProseEditor for focusIssue
  const [chapter, setChapter] = useState(1)
  const [entities, setEntities] = useState([])
  const [focalizer, setFocalizer] = useState('')
  const [prose, setProse] = useState('')
  const [proposal, setProposal] = useState(null)
  const [proposalStreaming, setProposalStreaming] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [seedQuote, setSeedQuote] = useState('')
  const [lastQuote, setLastQuote] = useState('')
  const [lastSel, setLastSel] = useState(null)
  const [qc, setQc] = useState(null)
  const [leaks, setLeaks] = useState(0)
  const [guard, setGuard] = useState({ leaks: [], qc: { repetition: 0, structural: 0, purple: 0, ai_tics: 0, oversaturation: 0 }, issues: [] })
  const [postCheckResult, setPostCheckResult] = useState(null)
  const [postChecking, setPostChecking] = useState(false)
  const [guardOn, setGuardOn] = useState(() => localStorage.getItem('scribe3:guardOn') !== '0')
  const [causal, setCausal] = useState([])
  const [promises, setPromises] = useState([])
  const [chapters, setChapters] = useState([])
  const [facts, setFacts] = useState([])
  const [events, setEvents] = useState([])
  const [motifs, setMotifs] = useState([])
  const [recallQ, setRecallQ] = useState('')
  const [recallHits, setRecallHits] = useState([])
  const [presentQ, setPresentQ] = useState('')
  const [focusMode, setFocusMode] = useState(false)
  const [chTitle, setChTitle] = useState('')
  const [saved, setSaved] = useState(true)
  const [btns, setBtns] = useState(() => loadButtons(work))
  const [leftActive, setLeftActive] = useState('material')
  const [rightActive, setRightActive] = useState('chat')
  const [matSeg, setMatSeg] = useState('outline')
  const [revSeg, setRevSeg] = useState('verify')
  const [tick, setTick] = useState(0)
  const [verTick, setVerTick] = useState(0)
  const [dlg, setDlg] = useState(null)
  const [serif, setSerif] = useState(() => localStorage.getItem('scribe3:serif') === '1')
  const [saveMenu, setSaveMenu] = useState(false)
  const saveMenuRef = useRef(null)
  const [guardPop, setGuardPop] = useState(false)
  const guardPopRef = useRef(null)
  const narrowRef = useRef(false)

  // 窄屏(<1100px)自动折叠右栏:仅在「进入窄屏」的瞬间收起一次,不与用户重新打开较劲
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1099px)')
    const apply = (matches) => {
      if (matches && !narrowRef.current) { setRightActive(''); narrowRef.current = true }
      else if (!matches) { narrowRef.current = false }
    }
    apply(mq.matches)
    const onChange = (e) => apply(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    if (!saveMenu) return
    const onDown = (e) => { if (saveMenuRef.current && !saveMenuRef.current.contains(e.target)) setSaveMenu(false) }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [saveMenu])

  useEffect(() => {
    if (!guardPop) return
    const onDown = (e) => { if (guardPopRef.current && !guardPopRef.current.contains(e.target)) setGuardPop(false) }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [guardPop])

  useEffect(() => {
    if (!guardOn) { setGuard({ leaks: [], qc: { repetition: 0, structural: 0, purple: 0 }, issues: [] }); return }
    if (!prose.trim()) return
    let alive = true
    const t = setTimeout(() => {
      api.checkProse(chapter, prose, focalizer)
        .then((r) => {
          if (alive) setGuard({
            leaks: r.leaks || [],
            qc: r.qc || { repetition: 0, structural: 0, purple: 0 },
            issues: r.issues || [],  // F-05: 带 range 的 issues 列表
          })
        })
        .catch(() => {})
    }, 3000)
    return () => { alive = false; clearTimeout(t) }
  }, [prose, chapter, focalizer, guardOn])

  useEffect(() => { api.entities().then(setEntities); api.motifs().then(setMotifs) }, [tick])
  useEffect(() => {
    api.chapter(chapter).then((ch) => { setProse(ch?.prose || ''); setFocalizer(ch?.focalizer || ''); setChTitle(ch?.title || ''); setSaved(true) })
    api.causal(chapter).then(setCausal)
    api.promises().then(setPromises)
    api.qc(chapter).then(setQc)
    api.chapters().then(setChapters)
    api.facts(chapter).then(setFacts)
    api.events(chapter).then(setEvents)
  }, [chapter, tick])
  const runRecall = async (e) => { e.preventDefault(); if (!recallQ.trim()) return; setRecallHits(await api.recall(recallQ.trim(), 8)) }

  const runPostCheck = async () => {
    if (!prose.trim() || postChecking) return
    setPostChecking(true)
    setPostCheckResult(null)
    try {
      const r = await api.postCheck(chapter, prose, focalizer)
      setPostCheckResult(r)
    } catch (e) {
      setPostCheckResult({ error: e.message || '请求失败' })
    } finally {
      setPostChecking(false)
    }
  }

  const sendPostCheckToChief = () => {
    if (!postCheckResult) return
    const r = postCheckResult
    const lines = []
    if (r.quality?.total > 0) {
      const bd = r.quality
      const parts = []
      if (bd.repetition > 0) parts.push(`复读 ${bd.repetition} 处`)
      if (bd.structural > 0) parts.push(`排比 ${bd.structural} 处`)
      if (bd.purple > 0) parts.push(`升华 ${bd.purple} 处`)
      if (bd.ai_tics > 0) parts.push(`AI腔 ${bd.ai_tics} 处`)
      if (bd.oversaturation > 0) parts.push(`过饱和 ${bd.oversaturation} 处`)
      lines.push(`QC 问题：${parts.join('、')}`)
    }
    if (r.leaks?.length > 0) {
      lines.push(`限知泄露 ${r.leaks.length} 处：${r.leaks.map((l) => l.marker).join('、')}`)
    }
    if (r.discipline?.violations?.length > 0) {
      lines.push(`纪律违规：${r.discipline.violations.join('、')}`)
    }
    if (lines.length === 0) lines.push('体检通过,无问题')
    setSeedQuote(`本章体检发现:\n${lines.join('\n')}\n\n请据此修订本章。`)
    setRightActive('chat')
  }

  const chars = entities.filter((e) => e.kind === 'character')
  const focName = (chars.find((c) => c.id === focalizer) || {}).name || '—'
  const wordCount = prose.replace(/\s/g, '').length
  const openProm = promises.filter((p) => p.status === 'open')
  // P3-e1 Fix 1: 单源 overdue — 读 backend 预判断的 overdue 字段,不在前端重算阈值
  // (backend 用 OVERDUE_SLACK 常量 + intent.overdue_threshold 覆盖,保证全局一致)
  const overdue = (p) => Boolean(p.overdue)
  const qcN = qc ? (qc.repetition?.length || qc.repetition || 0) + (qc.structural?.length || qc.structural || 0) + (qc.purple?.length || qc.purple || 0) : 0

  const persist = async (text) => {
    const r = await api.saveChapter(chapter, text, chTitle, focalizer)
    setQc(r.qc); setLeaks(r.leaks || 0); setSaved(true)
    setTick((t) => t + 1)
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
    <div className="shrink-0 border-b border-line bg-surface px-3 h-11 flex items-center gap-2 min-w-0">
      {/* 左:章节导航 — 固定不缩 */}
      <div className="flex items-center gap-1 shrink-0">
        <button onClick={() => setChapter((c) => Math.max(1, c - 1))} aria-label="上一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronLeft size={16} /></button>
        <span className="text-[13px] text-ink tnum whitespace-nowrap px-1">第 {chapter} 章</span>
        <button onClick={() => setChapter((c) => c + 1)} aria-label="下一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronRight size={16} /></button>
      </div>

      {/* 中:视角 — 可伸缩并截断,绝不把别人挤掉 */}
      <div className="flex items-center gap-1.5 min-w-0 flex-1">
        <span className="hidden xl:inline text-[12px] text-faint shrink-0">本章视角</span>
        <select value={focalizer} onChange={(e) => setFocalizer(e.target.value)}
          title="默认作者视角(全知);选某角色=本章限知该角色,开启穿帮校验"
          className="h-7 min-w-0 max-w-[180px] rounded-lg border border-line bg-canvas px-2 text-[12.5px] text-ink outline-none focus:border-brand cursor-pointer truncate">
          <option value="">作者视角(全知)</option>
          {chars.map((c) => <option key={c.id} value={c.id}>限知:{c.name}</option>)}
        </select>
      </div>

      {/* 右:状态 + 操作 — 全部 shrink-0,永不被裁 */}
      <div className="flex items-center gap-2 shrink-0">
        {/* 护栏芯片 */}
        {(() => {
          const qcTotal = (guard.qc.repetition || 0) + (guard.qc.structural || 0) + (guard.qc.purple || 0) + (guard.qc.ai_tics || 0) + (guard.qc.oversaturation || 0)
          const guardTone = !guardOn ? 'faint' : (focalizer && guard.leaks.length > 0 ? 'danger' : (qcTotal > 0 ? 'warn' : 'ok'))
          const issueCount = (focalizer ? guard.leaks.length : 0) + qcTotal
          return (
            <div ref={guardPopRef} className="relative shrink-0">
              <Chip
                tone={guardTone}
                icon={guardOn ? ShieldCheck : ShieldOff}
                onClick={() => setGuardPop((v) => !v)}
              >
                护栏{guardOn && guardTone !== 'ok' ? ` ${issueCount}` : ''}
              </Chip>
              {guardPop && (
                <div className="absolute right-0 top-full mt-1 z-20 min-w-[200px] rounded-lg border border-line bg-surface shadow-lg py-2 px-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[.07em] text-faint mb-2">护栏状态</div>
                  {/* F-05: 带 range 的 issues — 可点跳转到正文 */}
                  {guard.issues && guard.issues.length > 0 ? (
                    <div className="mb-2">
                      <div className="text-[11.5px] text-faint mb-1">问题({guard.issues.length}条 · 点击定位)</div>
                      <div className="space-y-0.5 max-h-40 overflow-y-auto">
                        {guard.issues.map((iss, idx) => (
                          <button key={idx}
                            onClick={() => { proseEditorRef.current?.focusIssue(iss); setGuardPop(false) }}
                            className="w-full text-left flex items-start gap-1.5 px-1.5 py-1 rounded hover:bg-soft cursor-pointer text-[11.5px] leading-snug">
                            <span className={`shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full ${
                              iss.type === 'leak' ? 'bg-danger' :
                              iss.type === 'ai_tics' ? 'bg-gray-400' :
                              iss.type === 'purple' ? 'bg-purple-500' :
                              iss.type === 'repetition' ? 'bg-amber-500' : 'bg-warn'
                            }`} />
                            <span className="text-ink truncate flex-1">{iss.message}</span>
                            {iss.range && <span className="shrink-0 text-brand text-[10px]">跳→</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                  {/* 限知泄露 */}
                  <div className="mb-2">
                    <div className="text-[11.5px] text-faint mb-0.5 flex items-center gap-1"><Lock size={11} />限知泄露词</div>
                    {focalizer && guard.leaks.length > 0
                      ? <div className="text-[12px] text-danger leading-snug">{guard.leaks.map((l) => l.marker).join('、')}</div>
                      : <div className="text-[12px] text-ok">无泄露</div>
                    }
                  </div>
                  {/* 五类 QC */}
                  <div className="mb-3">
                    <div className="text-[11.5px] text-faint mb-0.5">确定性 QC(五类)</div>
                    <div className={`text-[12px] ${qcTotal > 0 ? 'text-warn' : 'text-ok'}`}>
                      {qcTotal > 0 ? (
                        <span>
                          {(guard.qc.repetition || 0) > 0 && <span>复读 {guard.qc.repetition} </span>}
                          {(guard.qc.structural || 0) > 0 && <span>排比 {guard.qc.structural} </span>}
                          {(guard.qc.purple || 0) > 0 && <span>升华 {guard.qc.purple} </span>}
                          {(guard.qc.ai_tics || 0) > 0 && <span>AI腔 {guard.qc.ai_tics} </span>}
                          {(guard.qc.oversaturation || 0) > 0 && <span>过饱和 {guard.qc.oversaturation} </span>}
                        </span>
                      ) : '干净'}
                    </div>
                  </div>
                    </>
                  )}
                  {/* 开/关 toggle */}
                  <button
                    className="w-full flex items-center gap-2 rounded-lg px-2 h-8 text-[12.5px] text-ink hover:bg-soft cursor-pointer border border-line"
                    onClick={() => { const v = !guardOn; setGuardOn(v); localStorage.setItem('scribe3:guardOn', v ? '1' : '0') }}
                  >
                    {guardOn ? <ShieldCheck size={13} className="text-brand shrink-0" /> : <ShieldOff size={13} className="text-faint shrink-0" />}
                    <span>{guardOn ? '护栏开' : '护栏关'}</span>
                    <span className="ml-auto text-[11px] text-faint">{guardOn ? '点击关闭' : '点击开启'}</span>
                  </button>
                  <div className="text-[10.5px] text-faint mt-1.5 leading-snug">关=完全静默,不校验</div>
                </div>
              )}
            </div>
          )
        })()}
        <span className="text-[11px] text-faint tnum whitespace-nowrap shrink-0">{wordCount} 字</span>

        {/* 保存▾ 分段按钮:主=保存,▾ 展开 存档点/专注模式 */}
        <div ref={saveMenuRef} className="relative shrink-0">
          <div className="inline-flex items-center rounded-lg overflow-hidden ring-1 ring-line">
            <button onClick={save} title="保存本章"
              className={`inline-flex items-center gap-1 h-7 px-2.5 text-[12px] cursor-pointer whitespace-nowrap hover:bg-soft ${saved ? 'text-ok' : 'text-ink'}`}>
              <Save size={14} />{saved ? '已存' : '保存'}
            </button>
            <button onClick={() => setSaveMenu((v) => !v)} aria-label="更多保存选项" aria-expanded={saveMenu}
              className="h-7 px-1 text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer border-l border-line">
              <ChevronDown size={13} />
            </button>
          </div>
          {saveMenu && (
            <div className="absolute right-0 top-full mt-1 z-20 min-w-[140px] rounded-lg border border-line bg-surface shadow-lg py-1">
              <button onClick={() => { setSaveMenu(false); setDlg({ kind: 'checkpoint' }) }}
                className="w-full flex items-center gap-2 px-3 h-8 text-[12.5px] text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <Bookmark size={13} className="text-faint shrink-0" />存档点
              </button>
              <button onClick={() => { setSaveMenu(false); setFocusMode((v) => !v) }}
                className="w-full flex items-center gap-2 px-3 h-8 text-[12.5px] text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <AlignCenter size={13} className="text-faint shrink-0" />专注模式
                {focusMode && <Check size={13} className="ml-auto text-brand shrink-0" />}
              </button>
              <button onClick={() => { setSaveMenu(false); const v = !serif; setSerif(v); localStorage.setItem('scribe3:serif', v ? '1' : '0') }}
                className="w-full flex items-center gap-2 px-3 h-8 text-[12.5px] text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <BookText size={13} className="text-faint shrink-0" />阅读字体:{serif ? '衬线' : '黑体'}
                {serif && <Check size={13} className="ml-auto text-brand shrink-0" />}
              </button>
            </div>
          )}
        </div>

        <Btn variant="primary" className="shrink-0 whitespace-nowrap" onClick={async () => {
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
          <DraftCard proposal={proposal} candidates={candidates} streaming={proposalStreaming} onAccept={acceptProposal} onReject={() => { setProposal(null); setProposalStreaming(false); setCandidates([]); setLastQuote(''); setLastSel(null) }} onAcceptCandidate={acceptCandidate} />
          <div className={`manuscript${serif ? ' serif' : ''}`}>
            <ProseEditor ref={proseEditorRef} value={prose} onChange={(t) => { setProse(t); setSaved(false) }}
              chapterKey={`${work}-${chapter}`} focusMode={focusMode} onDiscuss={discussSel}
              placeholder="右侧跟主编提思路让它写,或直接在此落笔。" />
          </div>
        </div>
      </div>
    </div>
  )

  // ——— 各子区渲染(从原 11 tab 抽出,内容/handler 不变,合并复用)———
  const renderOutline = () => (
    <div>
      <SectionTitle icon={BookText} right={`${chapters.length} 章`}>章节</SectionTitle>
      {chapters.length === 0 && <Empty>暂无章节,写完保存即生成</Empty>}
      {chapters.map((c) => (
        <button key={c.seq} onClick={() => setChapter(c.seq)}
          className={`w-full text-left rounded-lg px-2.5 py-2 mb-0.5 text-[13px] transition-colors cursor-pointer ${c.seq === chapter ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
          {chapterLabel(c.seq, c.title || '')}
        </button>
      ))}
    </div>
  )
  const renderStructure = () => (
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
  )
  const renderMotifs = () => (
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
  )
  const renderRecall = () => (
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
  )
  const renderVerify = () => (
    <div>
      <SectionTitle icon={ShieldCheck}>软校验 · 不挡接受</SectionTitle>
      {leaks > 0 ? <Row tone="danger" icon={Lock}>限知泄露 {leaks} 处:写了 {focName} 不该知道的私密</Row> : <Row tone="ok" icon={CircleCheck}>限知:无泄露</Row>}
      {qcN > 0 ? <Row tone="warn" icon={CircleAlert}>确定性 QC:{qcN} 处(复读/排比/升华)</Row> : <Row tone="ok" icon={CircleCheck}>确定性 QC 干净</Row>}
      {causal.length > 0 ? <Row tone="danger" icon={CircleAlert}>因果违规 {causal.length} 处</Row> : <Row tone="ok" icon={CircleCheck}>因果完整</Row>}
      <div className="text-[11px] text-faint mt-2 leading-snug">保存/接受草稿时自动跑。北极星意图喂主编当写作纲领。</div>

      {/* 生成后全量体检 */}
      <div className="mt-4 border-t border-line pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11.5px] font-semibold text-ink">生成后体检(全量)</div>
          <button
            onClick={runPostCheck}
            disabled={postChecking || !prose.trim()}
            className="h-6 px-2.5 rounded-lg text-[11px] bg-soft border border-line text-ink hover:bg-brand/10 disabled:opacity-40 cursor-pointer transition-colors"
          >
            {postChecking ? '检查中…' : '立即体检'}
          </button>
        </div>
        {postCheckResult && !postCheckResult.error && (
          <div className="space-y-1.5">
            {/* F-05: 带 range 的 issues 可点跳转 */}
            {postCheckResult.issues && postCheckResult.issues.length > 0 && (
              <div className="rounded-lg border border-line divide-y divide-line/50">
                {postCheckResult.issues.map((iss, idx) => (
                  <button key={idx}
                    onClick={() => proseEditorRef.current?.focusIssue(iss)}
                    className="w-full text-left flex items-start gap-2 px-2 py-1.5 hover:bg-soft cursor-pointer text-[11.5px] leading-snug first:rounded-t-lg last:rounded-b-lg">
                    <span className={`shrink-0 mt-1 w-1.5 h-1.5 rounded-full ${
                      iss.type === 'leak' ? 'bg-danger' :
                      iss.type === 'ai_tics' ? 'bg-gray-400' :
                      iss.type === 'purple' ? 'bg-purple-500' :
                      iss.type === 'repetition' ? 'bg-amber-500' :
                      iss.type === 'discipline' ? 'bg-danger' : 'bg-warn'
                    }`} />
                    <span className="text-ink flex-1 truncate">{iss.message}</span>
                    {iss.range && <span className="shrink-0 text-[10px] text-brand">跳→</span>}
                  </button>
                ))}
              </div>
            )}
            {/* QC 五类(计数汇总) */}
            <div className={`text-[12px] rounded-lg px-2 py-1.5 ${(postCheckResult.quality?.total || 0) > 0 ? 'bg-warn/10 text-warn' : 'bg-ok/10 text-ok'}`}>
              <span className="font-medium">QC</span>
              {(postCheckResult.quality?.total || 0) > 0 ? (
                <span className="ml-1">
                  {postCheckResult.quality.repetition > 0 && <span>复读 {postCheckResult.quality.repetition} </span>}
                  {postCheckResult.quality.structural > 0 && <span>排比 {postCheckResult.quality.structural} </span>}
                  {postCheckResult.quality.purple > 0 && <span>升华 {postCheckResult.quality.purple} </span>}
                  {postCheckResult.quality.ai_tics > 0 && <span>AI腔 {postCheckResult.quality.ai_tics} </span>}
                  {postCheckResult.quality.oversaturation > 0 && <span>过饱和 {postCheckResult.quality.oversaturation} </span>}
                </span>
              ) : ' 干净'}
            </div>
            {/* 泄露 */}
            <div className={`text-[12px] rounded-lg px-2 py-1.5 ${postCheckResult.leaks?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
              <span className="font-medium">泄露</span>
              {postCheckResult.leaks?.length > 0
                ? <span className="ml-1">{postCheckResult.leaks.length} 处:{postCheckResult.leaks.map((l) => l.marker).join('、')}</span>
                : ' 无'}
            </div>
            {/* 纪律 */}
            {postCheckResult.discipline && (
              <div className={`text-[12px] rounded-lg px-2 py-1.5 ${postCheckResult.discipline.violations?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
                <span className="font-medium">纪律</span>
                {postCheckResult.discipline.violations?.length > 0
                  ? <span className="ml-1">{postCheckResult.discipline.violations.join('、')}</span>
                  : ' 守纪'}
              </div>
            )}
            {postCheckResult.degraded && (
              <div className="text-[11px] text-faint">⚠ 纪律判 LLM 调用失败,仅含确定性结果</div>
            )}
            {/* 一键修 */}
            <button
              onClick={sendPostCheckToChief}
              className="w-full mt-1 h-7 rounded-lg border border-brand/40 bg-brand/5 text-brand text-[12px] hover:bg-brand/15 cursor-pointer transition-colors"
            >
              让主编修这章
            </button>
          </div>
        )}
        {postCheckResult?.error && (
          <div className="text-[11.5px] text-danger">体检失败:{postCheckResult.error}</div>
        )}
      </div>
    </div>
  )
  const renderForeshadow = () => (
    <div>
      <SectionTitle icon={Bookmark} right={`${openProm.length} 未回收`}>伏笔 · 超期红</SectionTitle>
      {openProm.length === 0 ? <Empty>无未回收伏笔</Empty> : openProm.map((p) => (
        <Row key={p.id} tone={overdue(p) ? 'danger' : 'fore'} icon={Bookmark}>{p.text.slice(0, 40)}<span className="text-faint"> · 第{p.setup_chapter}章埋{overdue(p) ? ' · 超期' : ''}</span></Row>
      ))}
    </div>
  )
  const renderPresent = () => {
    const impOrder = ['protagonist', 'major', 'minor']
    const impLabel = { protagonist: '主角', major: '重要角色', minor: '次要角色' }
    const q = presentQ.trim().toLowerCase()
    const filtered = chars.filter((c) => !q || c.name.toLowerCase().includes(q))
    // group by importance if any char has it; else single group
    const hasImportance = chars.some((c) => c.importance)
    const CharBtn = ({ c }) => (
      <button key={c.id} onClick={() => setFocalizer(c.id)}
        className={`w-full flex items-center gap-2 rounded-lg px-2.5 py-2 mb-0.5 text-[13px] transition-colors cursor-pointer ${c.id === focalizer ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
        <span className={`w-2 h-2 rounded-full shrink-0 ${c.id === focalizer ? 'bg-brand' : 'bg-line'}`} />
        <span className="truncate">{c.name}</span>
        {c.id === focalizer && <span className="ml-auto text-[11px] text-brand">视角</span>}
      </button>
    )
    let body
    if (filtered.length === 0) {
      body = <div className="text-[12px] text-faint py-2 text-center">无匹配角色</div>
    } else if (hasImportance) {
      const groups = {}
      filtered.forEach((c) => {
        const k = impOrder.includes(c.importance) ? c.importance : 'minor'
        ;(groups[k] = groups[k] || []).push(c)
      })
      body = impOrder.filter((k) => groups[k]).map((k) => (
        <div key={k} className="mb-2">
          <div className="text-[11px] text-faint px-1 mb-0.5 mt-1">{impLabel[k]}</div>
          {groups[k].map((c) => <CharBtn key={c.id} c={c} />)}
        </div>
      ))
    } else {
      body = filtered.map((c) => <CharBtn key={c.id} c={c} />)
    }
    return (
      <div>
        <SectionTitle icon={Users}>可在场角色 · 点击设为视角</SectionTitle>
        {chars.length === 0 ? <Empty>无角色</Empty> : (
          <>
            <input value={presentQ} onChange={(e) => setPresentQ(e.target.value)}
              placeholder="搜角色…" className="w-full h-8 rounded-lg border border-line bg-canvas px-2.5 text-[13px] outline-none focus:border-brand mb-2" />
            {body}
          </>
        )}
      </div>
    )
  }

  // 小分段控件:一排药丸按钮,active 高亮
  const Segmented = ({ value, onChange, options }) => (
    <div className="flex items-center gap-1 mb-3 -mt-0.5">
      {options.map((o) => (
        <button key={o.key} onClick={() => onChange(o.key)}
          className={`h-6 px-2 rounded-lg text-[11.5px] whitespace-nowrap transition-colors cursor-pointer ${value === o.key ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )

  const reviewBadge = verifyIssues({ leaks, qcN, causal: causal.length }) + openProm.filter(overdue).length

  const leftCaps = [
    { key: 'material', label: '素材 · 大纲/结构/母题/检索', icon: LayoutList, render: () => (
      <div>
        <Segmented value={matSeg} onChange={setMatSeg} options={[
          { key: 'outline', label: '大纲' }, { key: 'structure', label: '结构' },
          { key: 'motifs', label: '母题' }, { key: 'recall', label: '检索' },
        ]} />
        {matSeg === 'outline' && renderOutline()}
        {matSeg === 'structure' && renderStructure()}
        {matSeg === 'motifs' && renderMotifs()}
        {matSeg === 'recall' && renderRecall()}
      </div>
    ) },
    { key: 'frame', label: '帧/意图', icon: Eye, render: () => (
      <FramePanel focalizer={focalizer} chapter={chapter} />
    ) },
    { key: 'versions', label: '存档', icon: Bookmark, render: () => (
      <VersionPanel seq={chapter} refreshKey={verTick}
        onRestore={(text) => { setProse(text); persist(text) }} />
    ) },
  ]

  const rightCaps = [
    { key: 'chat', label: '主编对话', icon: MessagesSquare, bare: true, render: () => (
      <WriteChat chapter={chapter} focalizer={focalizer} seedQuote={seedQuote}
        onSeedUsed={() => setSeedQuote('')}
        onProposalStart={(s) => {
          setProposal({ scope: s.scope, prose: '' })
          setProposalStreaming(true)
        }}
        onProposalChunk={(c) => {
          setProposal((prev) => prev ? { ...prev, prose: prev.prose + c.text } : { scope: 'chapter', prose: c.text })
        }}
        onProposal={(p) => {
          if (p.scope === 'selection') { setCandidates((cs) => [...cs, p.prose]); setProposal(null); setProposalStreaming(false) }
          else { setProposal(p); setProposalStreaming(false) }
        }} />
    ) },
    { key: 'review', label: '校验 · 校验/伏笔/在场', icon: ShieldCheck, badge: reviewBadge, render: () => (
      <div>
        <Segmented value={revSeg} onChange={setRevSeg} options={[
          { key: 'verify', label: '校验' }, { key: 'foreshadow', label: '伏笔' }, { key: 'present', label: '在场' },
        ]} />
        {revSeg === 'verify' && renderVerify()}
        {revSeg === 'foreshadow' && renderForeshadow()}
        {revSeg === 'present' && renderPresent()}
      </div>
    ) },
    { key: 'deduce', label: '演绎 · 角色限知', icon: Sparkles, render: () => (
      <DeducePanel chars={chars} chapter={chapter} onToChief={deduceToChief} />
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

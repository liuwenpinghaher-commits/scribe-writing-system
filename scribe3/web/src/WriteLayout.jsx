import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  ChevronLeft, ChevronRight, Save, MessagesSquare, ShieldCheck, ShieldOff, Bookmark,
  Users, AlignCenter, Search, CircleAlert, CircleCheck, Lock,
  BookText, LayoutList, Flame, Sparkles, Eye, ChevronDown, Check,
  DatabaseZap, Loader2,
} from 'lucide-react'
import { api } from './api'
import { verifyIssues } from './verifyIssues.js'
import { Shell } from './shell'
import { Btn, SectionTitle, Empty, Row, Tag } from './ui'
import { Chip } from './ui/Chip'
import { ProseEditor } from './editor/ProseEditor'
import { applyProposal } from './editor/applyProposal.js'
import { issueLabel, issueDot, ignoreIssue, filterIgnored, expandToSentence } from './editor/guardIssues.js'
import { DraftCard } from './editor/DraftCard'
import { WriteChat } from './WriteChat'
import { DeducePanel } from './DeducePanel'
import { NorthStarBar } from './NorthStarBar'
import { loadButtons, addButton } from './lib/rewriteButtons.js'
import { VersionPanel } from './VersionPanel.jsx'
import { FramePanel } from './FramePanel.jsx'
import { InputDialog } from './ui/Dialog.jsx'
import { useToast, dismissToast } from './ui/Toast.jsx'
import { useChiefSlot } from './ChiefSlotContext'

// 写作台(对话驱动):中区手稿 + 右轨主编对话出草稿卡。限知/校验后台支撑。与推演台共用同一份数据。
// seq: 外部(项目树)驱动的当前章号(F-06)。给定时同步到内部 chapter 状态;
// onSeqChange: 内部步进器换章时回调,让项目树选中态跟随。
export function WriteLayout({ work, seq, sceneIdx, onSeqChange }) {
  api.setWork(work)
  const toast = useToast()
  // 波B Step3:WriteChat 经 portal 渲染进右栏 ChiefDock 的槽。slotEl 为该槽 DOM。
  const { slotEl } = useChiefSlot()
  const proseEditorRef = useRef(null)  // F-05: ref to ProseEditor for focusIssue
  const [chapter, _setChapter] = useState(seq || 1)
  // persistDirtyOldChapter:切章前若有未保存内容,静默保存旧章(fire-and-forget,不阻断切章)
  // 全部从 dirtyRef 读取,完全脱离 state 闭包,任何调用时机都拿到最新值。
  const persistDirtyOldChapter = (targetSeq) => {
    const { seq: oldSeq, prose: oldProse, chTitle: oldChTitle, focalizer: oldFocalizer, dirty } = dirtyRef.current
    if (!dirty || oldProse === undefined || oldSeq == null || oldSeq === targetSeq) return
    api.saveChapter(oldSeq, oldProse, oldChTitle, oldFocalizer)
      .then(() => { dirtyRef.current.dirty = false; setSaved(true) })
      .catch(() => { toast(`第 ${oldSeq} 章自动保存失败,请回该章手动保存`, { tone: 'danger' }) })
  }

  // setChapter:改内部状态 + 通知外部(项目树),保持单一真相源同步
  // 内部步进器(上/下一章按钮)走此路径:切章前先 persist 旧章
  const setChapter = (next) => {
    _setChapter((prev) => {
      const v = typeof next === 'function' ? next(prev) : next
      if (v !== prev) {
        persistDirtyOldChapter(v)
        onSeqChange?.(v)
      }
      return v
    })
  }
  // 外部 seq 变化(树点章)→ 切章前若有未保存内容先 persist 旧章,再同步内部章号
  useEffect(() => {
    if (seq == null || seq === chapter) return
    persistDirtyOldChapter(seq)
    _setChapter(seq)
  }, [seq])
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
  // F-05 完整:点正文波浪线弹的悬浮卡 { issue, x, y };忽略后 bump 触发 decoration 重推
  const [issueCard, setIssueCard] = useState(null)
  const [ignoreTick, setIgnoreTick] = useState(0)
  const [guardOn, setGuardOn] = useState(() => localStorage.getItem('scribe3:guardOn') !== '0')
  const [causal, setCausal] = useState([])
  const [promises, setPromises] = useState([])
  const [facts, setFacts] = useState([])
  const [events, setEvents] = useState([])
  const [motifs, setMotifs] = useState([])
  const [recallQ, setRecallQ] = useState('')
  const [recallHits, setRecallHits] = useState([])
  const [presentQ, setPresentQ] = useState('')
  const [focusMode, setFocusMode] = useState(false)
  const [factsExpanded, setFactsExpanded] = useState(false)  // 本章事实:默认前60条,「展开全部」可达全量
  const [chTitle, setChTitle] = useState('')
  const [saved, setSaved] = useState(true)
  // dirty 切章防丢:用 ref 追踪当前章号 + 实时正文 + chTitle + focalizer + dirty 状态,
  // 全部从 ref 读,完全脱离 state 闭包,确保切章时拿到最新值。
  const dirtyRef = useRef({ seq: chapter, prose: '', chTitle: '', focalizer: '', dirty: false })
  const [btns, setBtns] = useState(() => loadButtons(work))
  const [leftActive, setLeftActive] = useState('frame')   // 默认展开「帧/意图」数据面板(设计要求左栏 tabs 常显;点图标可收起)
  const [rightActive, setRightActive] = useState('chat')
  const [matSeg, setMatSeg] = useState('structure')
  const [revSeg, setRevSeg] = useState('verify')
  const [tick, setTick] = useState(0)
  const [verTick, setVerTick] = useState(0)
  const [dlg, setDlg] = useState(null)
  const [serif, setSerif] = useState(() => localStorage.getItem('scribe3:serif') === '1')
  // 达标 toast:记录上次 persist 前的 today_words,save 后比较是否跨过 daily_word_goal
  const prevTodayWordsRef = useRef(null)
  const [saveMenu, setSaveMenu] = useState(false)
  const saveMenuRef = useRef(null)
  const [guardPop, setGuardPop] = useState(false)
  const guardPopRef = useRef(null)
  const narrowRef = useRef(false)
  // 进度显性化(批二):/progress 返回 today_words/daily_word_goal/current_streak/total_words/total_word_goal。
  // 挂载 + 存章后刷新;拉取失败置 null → 顶栏优雅降级为只显字数。
  const [progress, setProgress] = useState(null)
  const [progPop, setProgPop] = useState(false)
  const progPopRef = useRef(null)
  // ingest 反哺设定库:busy 态防重复点击
  const [ingesting, setIngesting] = useState(false)

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
    if (!progPop) return
    const onDown = (e) => { if (progPopRef.current && !progPopRef.current.contains(e.target)) setProgPop(false) }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [progPop])

  // 进度:挂载/换 work 时拉一次;失败静默(顶栏降级为只显字数)
  const refreshProgress = () => api.progress().then(setProgress).catch(() => setProgress(null))
  useEffect(() => { refreshProgress() }, [work])

  // beforeunload 兜底:有未保存修改时,关/刷新页面弹浏览器原生提示
  useEffect(() => {
    if (saved) return
    const handler = (e) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [saved])

  // Cmd/Ctrl+S 保存本章(阻止浏览器"保存网页"框)。用 ref 持最新 save,避免重复绑定/闭包过期。
  const saveRef = useRef(null)
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 's' || e.key === 'S')) {
        e.preventDefault()
        saveRef.current?.()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

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

  // F-06 场景级跳转:章正文异步加载完成后 +1,供 focusScene 效果在内容就位后再跳。
  const [proseLoadTick, setProseLoadTick] = useState(0)
  useEffect(() => { api.entities().then(setEntities); api.motifs().then(setMotifs) }, [tick])
  useEffect(() => {
    api.chapter(chapter).then((ch) => {
      const p = ch?.prose || ''
      const f = ch?.focalizer || ''; const t = ch?.title || ''
      setProse(p); setFocalizer(f); setChTitle(t); setSaved(true)
      // 新章加载完成后重置 dirtyRef,以新章 seq + 新章正文 + focalizer + chTitle 为基准
      dirtyRef.current = { seq: chapter, prose: p, chTitle: t, focalizer: f, dirty: false }
      setProseLoadTick((n) => n + 1)
    })
    api.causal(chapter).then(setCausal)
    api.promises().then(setPromises)
    api.qc(chapter).then(setQc)
    api.facts(chapter).then(setFacts)
    api.events(chapter).then(setEvents)
  }, [chapter, tick])
  // F-06 场景级跳转:sceneIdx 给定 + 正文已加载 → 等编辑器 setContent 落定后跳到该场景。
  // 依赖 [sceneIdx, proseLoadTick]:点不同场景(idx 变)或换章重载(tick 变)都重跳。
  // 只对当前章的场景跳(seq===chapter,避免树点章号与场景号错配时跳错章)。
  useEffect(() => {
    if (sceneIdx == null) return
    if (seq != null && seq !== chapter) return
    if (proseLoadTick === 0) return
    // 用 timeout 让 ProseEditor 的 setContent(value 变化)effect 先落定再定位
    const t = setTimeout(() => { proseEditorRef.current?.focusScene?.(sceneIdx) }, 60)
    return () => clearTimeout(t)
  }, [sceneIdx, proseLoadTick, seq, chapter])

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
    // 记住 save 前当日字数,用于达标判定(fail-soft:拉不到就跳过)
    let prevToday = prevTodayWordsRef.current
    if (prevToday === null) {
      try {
        const pp = await api.progress()
        prevToday = pp.today_words ?? 0
        prevTodayWordsRef.current = prevToday
      } catch { prevToday = 0 }
    }

    let r
    try {
      r = await api.saveChapter(chapter, text, chTitle, focalizer)
    } catch (e) {
      // 保存失败:danger 提示,保持 saved=false + dirty=true 以便重试;不吞错
      toast(e?.body?.detail || ('保存失败:' + (e?.message || '')), { tone: 'danger' })
      throw e
    }
    setQc(r.qc); setLeaks(r.leaks || 0); setSaved(true)
    // 手动保存成功:重置 dirtyRef
    dirtyRef.current.dirty = false
    dirtyRef.current.prose = text
    setTick((t) => t + 1)

    // 达标 toast:save 后拉 progress,比较是否刚跨过 daily_word_goal
    try {
      const np = await api.progress()
      setProgress(np)  // 存章后刷新顶栏进度显示
      const dailyGoal = np.daily_word_goal
      const newToday = np.today_words ?? 0
      prevTodayWordsRef.current = newToday  // 更新缓存
      if (dailyGoal && prevToday < dailyGoal && newToday >= dailyGoal) {
        const streakMsg = np.current_streak > 1 ? ` · 连胜 ${np.current_streak} 天` : ''
        toast(`🎉 今日目标达成 ${dailyGoal.toLocaleString()} 字！${streakMsg}`)
      }
    } catch { /* 达标判定失败不影响存稿 */ }
  }
  const acceptProposal = async () => {
    const p = proposal; if (!p) return
    const r = applyProposal(prose, p, lastSel)
    if (!r.ok && r.drifted) {
      toast('原文已变动,请重新选中要替换的文字', { tone: 'danger' })
      setProposal(null); return
    }
    setProse(r.next); setProposal(null); setLastQuote(''); setLastSel(null)
    await persist(r.next).catch(() => {})  // 失败已在 persist 内 toast,dirty 保留可重存
  }
  const acceptCandidate = async (text) => {
    const r = applyProposal(prose, { scope: 'selection', prose: text }, lastSel)
    if (!r.ok && r.drifted) { toast('原文已变动,请重新选中要替换的文字', { tone: 'danger' }); setCandidates([]); return }
    setProse(r.next); setCandidates([]); setLastQuote(''); setLastSel(null)
    await persist(r.next).catch(() => {})  // 失败已在 persist 内 toast,dirty 保留可重存
  }
  // persist 内部已 toast 报错;此处吞掉 reject 避免 unhandled rejection(dirty/saved 已由 persist 保留)
  const save = () => persist(prose).catch(() => {})
  saveRef.current = save  // Cmd/Ctrl+S 走最新 save(每次渲染刷新 ref)

  // 反哺设定库(批二):把本章正文喂回知识库(幂等 purge+重抽本章)。
  // /ingest 返回 {applied, delta} 或 {applied:-1, parse_failed:true}。applied=新增知识边条数。
  // 待核实体(_resolve_char 抽出的库外人名)是 ingest 副作用,不在 /ingest 返回里 → 事后查 /ingest-unverified 计数。
  const runIngest = async () => {
    if (ingesting) return
    setIngesting(true)
    setSaveMenu(false)
    const busy = toast('正在反哺设定库…（抽取知识,可能稍慢）', { duration: 60000 })
    try {
      const r = await api.ingest(chapter)
      try { dismissToast(busy) } catch { /* noop */ }
      if (r?.parse_failed) {
        toast('本章知识抽取失败,可重试', { tone: 'warn' })
        return
      }
      const applied = r?.applied ?? 0
      // 待核实体:ingest 后查 pending 数(fail-soft,拉不到就不显该项)
      let pending = null
      try { pending = (await api.listUnverified()).length } catch { pending = null }
      const parts = [`新增 ${applied} 条知识`]
      if (pending != null) parts.push(`${pending} 条待核实体`)
      toast(`已反哺:${parts.join(' / ')}`, { tone: 'ok' })
      setTick((t) => t + 1)  // 刷新本章事实/待核引用等派生数据
    } catch (e) {
      try { dismissToast(busy) } catch { /* noop */ }
      toast('反哺失败:' + (e?.body?.detail || e?.message || '请求出错'), { tone: 'danger' })
    } finally {
      setIngesting(false)
    }
  }
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

  // F-05 完整:正文常驻波浪线的 issue 列表(过滤掉已忽略的)。
  // 只依赖 guard.issues / ignoreTick:guard.issues 由 3s 防抖按当前 prose 重算,
  // 期间打字靠 decoration set.map 平滑跟随(不重建)。prose 在此非响应式读取,稳定引用。
  const proseRef = useRef(prose)
  proseRef.current = prose
  const editorIssues = useMemo(
    () => filterIgnored(proseRef.current, guard.issues || []),
    [guard.issues, ignoreTick],
  )

  // 点正文波浪线 → 弹悬浮卡(GuardDecoration 经 ProseEditor onIssueClick 回调)
  const onUnderlineClick = (iss) => {
    // 用当前光标/选区附近坐标定位卡片;失败兜底到屏幕中部
    let x = window.innerWidth / 2, y = window.innerHeight / 2
    try {
      const r = window.getSelection()?.getRangeAt(0)?.getBoundingClientRect()
      if (r && (r.left || r.top)) { x = r.left; y = r.bottom + 6 }
    } catch { /* 无选区 */ }
    setIssueCard({ issue: iss, x, y })
  }

  // 悬浮卡 / 面板「让主编改这处」→ 复用 discussSel→applyProposal 句级链路
  const sendIssueToChief = (iss) => {
    setIssueCard(null)
    // 把短语 range 扩到整句给主编完整上下文
    const range = iss.range && Array.isArray(iss.range) ? expandToSentence(prose, iss.range) : null
    const text = range ? prose.slice(range[0], range[1]) : (iss.text || '')
    if (!text.trim()) return
    // 复用现有选区改写链路:lastSel 携 {from,to,text} → 候选 → applyProposal 精准替换
    setLastSel(range ? { text, from: range[0], to: range[1] } : null)
    setLastQuote(text)
    setSeedQuote(`这处有「${issueLabel(iss.type)}」问题(${iss.message}),把这一句改一下,给我 2-3 个候选:「${text}」`)
    setCandidates([])
    setRightActive('chat')
  }

  // 「忽略」→ 持久化到 localStorage(prose 指纹 + issue key),并撤掉波浪线
  const ignoreIssueHandler = (iss) => {
    ignoreIssue(prose, iss)
    setIssueCard(null)
    setIgnoreTick((t) => t + 1)
  }

  const topbarMid = (
    <div className="shrink-0 border-b border-line bg-surface px-3 h-11 flex items-center gap-2 min-w-0">
      {/* 左:章节导航 — 固定不缩 */}
      <div className="flex items-center gap-1 shrink-0">
        <button onClick={() => setChapter((c) => Math.max(1, c - 1))} aria-label="上一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronLeft size={16} /></button>
        <span className="text-f13 text-ink tnum whitespace-nowrap px-1">第 {chapter} 章</span>
        <button onClick={() => setChapter((c) => c + 1)} aria-label="下一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronRight size={16} /></button>
      </div>

      {/* 中:视角 — 可伸缩并截断,绝不把别人挤掉 */}
      <div className="flex items-center gap-1.5 min-w-0 flex-1">
        <span className="hidden xl:inline text-f12 text-faint shrink-0">本章视角</span>
        <select value={focalizer} onChange={(e) => { setFocalizer(e.target.value); dirtyRef.current.focalizer = e.target.value }}
          title="默认作者视角(全知);选某角色=本章限知该角色,开启穿帮校验"
          className="h-7 min-w-0 max-w-[180px] rounded-lg border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand cursor-pointer truncate">
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
                  <div className="text-f11 font-semibold uppercase tracking-[.07em] text-faint mb-2">护栏状态</div>
                  {/* F-05: 带 range 的 issues — 可点跳转到正文(过滤已忽略) */}
                  {editorIssues && editorIssues.length > 0 ? (
                    <div className="mb-2">
                      <div className="text-f12 text-faint mb-1">问题({editorIssues.length}条 · 点击定位)</div>
                      <div className="space-y-0.5 max-h-40 overflow-y-auto">
                        {editorIssues.map((iss, idx) => (
                          <button key={idx}
                            onClick={() => { proseEditorRef.current?.focusIssue(iss); setGuardPop(false) }}
                            className="w-full text-left flex items-start gap-1.5 px-1.5 py-1 rounded hover:bg-soft cursor-pointer text-f12 leading-snug">
                            <span className={`shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full ${issueDot(iss.type)}`} />
                            <span className="text-ink truncate flex-1">{iss.message}</span>
                            {iss.range && <span className="shrink-0 text-brand text-f10">跳→</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                  {/* 限知泄露 */}
                  <div className="mb-2">
                    <div className="text-f12 text-faint mb-0.5 flex items-center gap-1"><Lock size={11} />限知泄露词</div>
                    {focalizer && guard.leaks.length > 0
                      ? <div className="text-f12 text-danger leading-snug">{guard.leaks.map((l) => l.marker).join('、')}</div>
                      : <div className="text-f12 text-ok">无泄露</div>
                    }
                  </div>
                  {/* 五类 QC */}
                  <div className="mb-3">
                    <div className="text-f12 text-faint mb-0.5">确定性 QC(五类)</div>
                    <div className={`text-f12 ${qcTotal > 0 ? 'text-warn' : 'text-ok'}`}>
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
                    className="w-full flex items-center gap-2 rounded-lg px-2 h-8 text-f13 text-ink hover:bg-soft cursor-pointer border border-line"
                    onClick={() => { const v = !guardOn; setGuardOn(v); localStorage.setItem('scribe3:guardOn', v ? '1' : '0') }}
                  >
                    {guardOn ? <ShieldCheck size={13} className="text-brand shrink-0" /> : <ShieldOff size={13} className="text-faint shrink-0" />}
                    <span>{guardOn ? '护栏开' : '护栏关'}</span>
                    <span className="ml-auto text-f11 text-faint">{guardOn ? '点击关闭' : '点击开启'}</span>
                  </button>
                  <div className="text-f11 text-faint mt-1.5 leading-snug">关=完全静默,不校验</div>
                </div>
              )}
            </div>
          )
        })()}
        {/* 进度(批二):默认紧凑显本章字数;有今日目标时附「今日 x/目标」细进度。
            点开 popover 看今日/全书完整进度。/progress 拉不到(progress===null)则降级为纯字数,不崩。 */}
        {(() => {
          const p = progress
          const dailyGoal = p?.daily_word_goal
          const todayW = p?.today_words ?? 0
          const streak = p?.current_streak ?? 0
          const totalW = p?.total_words ?? null
          const totalGoal = p?.total_word_goal
          const dailyPct = dailyGoal ? Math.min(100, Math.round((todayW / dailyGoal) * 100)) : null
          const totalPct = (totalW != null && totalGoal) ? Math.min(100, Math.round((totalW / totalGoal) * 100)) : null
          return (
            <div ref={progPopRef} className="relative shrink-0">
              <button onClick={() => setProgPop((v) => !v)} title="写作进度"
                className="inline-flex items-center gap-1.5 h-7 px-1.5 rounded-lg text-faint hover:bg-soft hover:text-ink cursor-pointer whitespace-nowrap">
                <span className="text-f11 tnum">{wordCount} 字</span>
                {dailyGoal ? (
                  <span className="hidden sm:inline text-f11 tnum text-faint">
                    · 今日 {todayW.toLocaleString()}/{dailyGoal.toLocaleString()}
                    {streak > 1 && <span className="text-warn"> 🔥{streak}</span>}
                  </span>
                ) : null}
              </button>
              {progPop && (
                <div className="absolute right-0 top-full mt-1 z-20 min-w-[220px] rounded-lg border border-line bg-surface shadow-lg py-2 px-3">
                  <div className="text-f11 font-semibold uppercase tracking-[.07em] text-faint mb-2">写作进度</div>
                  <div className="mb-2.5">
                    <div className="flex items-baseline justify-between text-f12">
                      <span className="text-faint">本章</span>
                      <span className="text-ink tnum">{wordCount.toLocaleString()} 字</span>
                    </div>
                  </div>
                  {p == null ? (
                    <div className="text-f12 text-faint">进度数据暂不可用</div>
                  ) : (
                    <>
                      <div className="mb-2.5">
                        <div className="flex items-baseline justify-between text-f12 mb-1">
                          <span className="text-faint flex items-center gap-1">今日{streak > 1 && <span className="text-warn text-f11">🔥{streak} 连胜</span>}</span>
                          <span className="text-ink tnum">{todayW.toLocaleString()}{dailyGoal ? ` / ${dailyGoal.toLocaleString()}` : ''} 字</span>
                        </div>
                        {dailyPct != null && (
                          <div className="h-1.5 rounded-full bg-soft overflow-hidden">
                            <div className={`h-full rounded-full ${dailyPct >= 100 ? 'bg-ok' : 'bg-brand'}`} style={{ width: `${dailyPct}%` }} />
                          </div>
                        )}
                      </div>
                      {totalW != null && (
                        <div>
                          <div className="flex items-baseline justify-between text-f12 mb-1">
                            <span className="text-faint">全书</span>
                            <span className="text-ink tnum">{totalW.toLocaleString()}{totalGoal ? ` / ${totalGoal.toLocaleString()}` : ''} 字</span>
                          </div>
                          {totalPct != null && (
                            <div className="h-1.5 rounded-full bg-soft overflow-hidden">
                              <div className={`h-full rounded-full ${totalPct >= 100 ? 'bg-ok' : 'bg-brand'}`} style={{ width: `${totalPct}%` }} />
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )
        })()}

        {/* 保存▾ 分段按钮:主=保存,▾ 展开 存档点/专注模式 */}
        <div ref={saveMenuRef} className="relative shrink-0">
          <div className="inline-flex items-center rounded-lg overflow-hidden ring-1 ring-line">
            <button onClick={save} title="保存本章"
              className={`inline-flex items-center gap-1 h-7 px-2.5 text-f12 cursor-pointer whitespace-nowrap hover:bg-soft ${saved ? 'text-ok' : 'text-ink'}`}>
              <Save size={14} />{saved ? '已存' : '保存'}
            </button>
            <button onClick={() => setSaveMenu((v) => !v)} aria-label="更多保存选项" aria-expanded={saveMenu}
              className="h-7 px-1 text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer border-l border-line">
              <ChevronDown size={13} />
            </button>
          </div>
          {saveMenu && (
            <div className="absolute right-0 top-full mt-1 z-20 min-w-[168px] rounded-lg border border-line bg-surface shadow-lg py-1">
              <button onClick={() => { setSaveMenu(false); setDlg({ kind: 'checkpoint' }) }}
                className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <Bookmark size={13} className="text-faint shrink-0" />存档点
              </button>
              {/* 反哺设定库(批二):把本章正文喂回知识库,抽新知/待核实体。busy 态防重复点。 */}
              <button onClick={runIngest} disabled={ingesting}
                title="把本章正文喂回设定库(抽取新知识与待核实体)"
                className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap disabled:opacity-60 disabled:cursor-wait">
                {ingesting ? <Loader2 size={13} className="text-brand shrink-0 animate-spin" /> : <DatabaseZap size={13} className="text-faint shrink-0" />}
                {ingesting ? '反哺中…' : '反哺设定库'}
              </button>
              <button onClick={() => { setSaveMenu(false); setFocusMode((v) => !v) }}
                className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <AlignCenter size={13} className="text-faint shrink-0" />专注模式
                {focusMode && <Check size={13} className="ml-auto text-brand shrink-0" />}
              </button>
              <button onClick={() => { setSaveMenu(false); const v = !serif; setSerif(v); localStorage.setItem('scribe3:serif', v ? '1' : '0') }}
                className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
                <BookText size={13} className="text-faint shrink-0" />阅读字体:{serif ? '衬线' : '黑体'}
                {serif && <Check size={13} className="ml-auto text-brand shrink-0" />}
              </button>
            </div>
          )}
        </div>

        <Btn variant="primary" className="shrink-0 whitespace-nowrap" onClick={async () => {
          try {
            await persist(prose)  // 失败已在 persist 内 toast;抛出后不落定稿存档点
            await api.checkpoint(chapter, prose, '定稿', 'final', qc || {})
            setVerTick((t) => t + 1)
          } catch { /* persist 已提示,存为正文中止 */ }
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
            }} className="h-6 px-2 rounded-lg border border-line text-f11 text-ink hover:bg-soft cursor-pointer">{b}</button>
          ))}
          <button onClick={() => setDlg({ kind: 'rewrite' })} className="h-6 px-2 rounded-lg border border-dashed border-line text-f11 text-faint hover:bg-soft cursor-pointer">+ 存为按钮</button>
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-y-auto bg-canvas">
        <div className="max-w-[48rem] mx-auto px-6 py-8">
          <DraftCard proposal={proposal} candidates={candidates} streaming={proposalStreaming} onAccept={acceptProposal} onReject={() => { setProposal(null); setProposalStreaming(false); setCandidates([]); setLastQuote(''); setLastSel(null) }} onAcceptCandidate={acceptCandidate} />
          <div className={`manuscript${serif ? ' serif' : ''}`}>
            <ProseEditor ref={proseEditorRef} value={prose} onChange={(t) => { setProse(t); setSaved(false); dirtyRef.current.prose = t; dirtyRef.current.dirty = true }}
              chapterKey={`${work}-${chapter}`} focusMode={focusMode} onDiscuss={discussSel}
              issues={editorIssues} onIssueClick={onUnderlineClick}
              placeholder="右侧跟主编提思路让它写,或直接在此落笔。" />
          </div>
        </div>
      </div>
    </div>
  )

  // ——— 各子区渲染(从原 11 tab 抽出,内容/handler 不变,合并复用)———
  // F-06: renderOutline(扁平章按钮列)已下线——章导航由左侧项目树承载。
  const renderStructure = () => (
    <div>
      <SectionTitle icon={LayoutList} right={`${events.length}`}>本章事件</SectionTitle>
      {events.length === 0 ? <Empty>本章未设计事件</Empty> : events.map((ev) => (
        <Row key={ev.id}><Tag tone="brand">{ev.type}</Tag><span className="ml-1 text-faint">{ev.id}</span>{!ev.goal && <span className="ml-1 text-danger">· 缺目标</span>}</Row>
      ))}
      <div className="h-3" />
      <SectionTitle right={`${facts.length}`}>本章事实</SectionTitle>
      {facts.length === 0 ? <Empty>无</Empty> : (factsExpanded ? facts : facts.slice(0, 60)).map((f) => (
        <Row key={f.id} icon={f.secret ? Lock : undefined}><span className="text-faint">{f.attribute}</span>:{f.value}</Row>
      ))}
      {facts.length > 60 && (
        <button onClick={() => setFactsExpanded((v) => !v)}
          className="mt-1.5 text-f11 text-brand hover:text-brand/80 cursor-pointer">
          {factsExpanded ? '收起' : `展开全部 ${facts.length} 条`}
        </button>
      )}
    </div>
  )
  const renderMotifs = () => (
    <div>
      <SectionTitle icon={Flame} right={`${motifs.length}`}>母题 · 参照不透支</SectionTitle>
      {motifs.length === 0 ? <Empty>无</Empty> : motifs.map((m) => (
        <div key={m.id} className="mb-2.5 pb-2.5 border-b border-line/50 last:border-0">
          <div className="text-f13 font-semibold text-ink">{m.name}</div>
          {m.theme && <div className="text-f12 text-fore mt-0.5">{m.theme}</div>}
          {m.unfolding && <div className="text-f12 text-faint mt-0.5 leading-snug">{m.unfolding}</div>}
        </div>
      ))}
    </div>
  )
  const renderRecall = () => (
    <div>
      <SectionTitle icon={Search}>语义召回设定</SectionTitle>
      <form onSubmit={runRecall} className="flex gap-1.5 mb-3">
        <input value={recallQ} onChange={(e) => setRecallQ(e.target.value)} placeholder="按意思搜,如「炼丹复活」"
          className="flex-1 h-8 rounded-lg border border-line bg-canvas px-2.5 text-f13 outline-none focus:border-brand" />
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
      <div className="text-f11 text-faint mt-2 leading-snug">保存/接受草稿时自动跑。北极星意图喂主编当写作纲领。</div>

      {/* 生成后全量体检 */}
      <div className="mt-4 border-t border-line pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-f12 font-semibold text-ink">生成后体检(全量)</div>
          <button
            onClick={runPostCheck}
            disabled={postChecking || !prose.trim()}
            className="h-6 px-2.5 rounded-lg text-f11 bg-soft border border-line text-ink hover:bg-brand/10 disabled:opacity-40 cursor-pointer transition-colors"
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
                  <div key={idx}
                    className="w-full flex items-start gap-2 px-2 py-1.5 hover:bg-soft text-f12 leading-snug first:rounded-t-lg last:rounded-b-lg group">
                    <button onClick={() => proseEditorRef.current?.focusIssue(iss)}
                      className="flex items-start gap-2 flex-1 min-w-0 text-left cursor-pointer">
                      <span className={`shrink-0 mt-1 w-1.5 h-1.5 rounded-full ${issueDot(iss.type)}`} />
                      <span className="text-ink flex-1 truncate">{iss.message}</span>
                    </button>
                    {iss.range && (
                      <button onClick={() => sendIssueToChief(iss)} title="让主编改这处"
                        className="shrink-0 text-f10 text-brand opacity-0 group-hover:opacity-100 hover:underline cursor-pointer transition-opacity">
                        改这处
                      </button>
                    )}
                    {iss.range && <span className="shrink-0 text-f10 text-brand">跳→</span>}
                  </div>
                ))}
              </div>
            )}
            {/* QC 五类(计数汇总) */}
            <div className={`text-f12 rounded-lg px-2 py-1.5 ${(postCheckResult.quality?.total || 0) > 0 ? 'bg-warn/10 text-warn' : 'bg-ok/10 text-ok'}`}>
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
            <div className={`text-f12 rounded-lg px-2 py-1.5 ${postCheckResult.leaks?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
              <span className="font-medium">泄露</span>
              {postCheckResult.leaks?.length > 0
                ? <span className="ml-1">{postCheckResult.leaks.length} 处:{postCheckResult.leaks.map((l) => l.marker).join('、')}</span>
                : ' 无'}
            </div>
            {/* 纪律 */}
            {postCheckResult.discipline && (
              <div className={`text-f12 rounded-lg px-2 py-1.5 ${postCheckResult.discipline.violations?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
                <span className="font-medium">纪律</span>
                {postCheckResult.discipline.violations?.length > 0
                  ? <span className="ml-1">{postCheckResult.discipline.violations.join('、')}</span>
                  : ' 守纪'}
              </div>
            )}
            {postCheckResult.degraded && (
              <div className="text-f11 text-faint">⚠ 纪律判 LLM 调用失败,仅含确定性结果</div>
            )}
            {/* 一键修 */}
            <button
              onClick={sendPostCheckToChief}
              className="w-full mt-1 h-7 rounded-lg border border-brand/40 bg-brand/5 text-brand text-f12 hover:bg-brand/15 cursor-pointer transition-colors"
            >
              让主编修这章
            </button>
          </div>
        )}
        {postCheckResult?.error && (
          <div className="text-f12 text-danger">体检失败:{postCheckResult.error}</div>
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
      <button key={c.id} onClick={() => { setFocalizer(c.id); dirtyRef.current.focalizer = c.id }}
        className={`w-full flex items-center gap-2 rounded-lg px-2.5 py-2 mb-0.5 text-f13 transition-colors cursor-pointer ${c.id === focalizer ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
        <span className={`w-2 h-2 rounded-full shrink-0 ${c.id === focalizer ? 'bg-brand' : 'bg-line'}`} />
        <span className="truncate">{c.name}</span>
        {c.id === focalizer && <span className="ml-auto text-f11 text-brand">视角</span>}
      </button>
    )
    let body
    if (filtered.length === 0) {
      body = <div className="text-f12 text-faint py-2 text-center">无匹配角色</div>
    } else if (hasImportance) {
      const groups = {}
      filtered.forEach((c) => {
        const k = impOrder.includes(c.importance) ? c.importance : 'minor'
        ;(groups[k] = groups[k] || []).push(c)
      })
      body = impOrder.filter((k) => groups[k]).map((k) => (
        <div key={k} className="mb-2">
          <div className="text-f11 text-faint px-1 mb-0.5 mt-1">{impLabel[k]}</div>
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
              placeholder="搜角色…" className="w-full h-8 rounded-lg border border-line bg-canvas px-2.5 text-f13 outline-none focus:border-brand mb-2" />
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
          className={`h-6 px-2 rounded-lg text-f12 whitespace-nowrap transition-colors cursor-pointer ${value === o.key ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )

  const reviewBadge = verifyIssues({ leaks, qcN, causal: causal.length }) + openProm.filter(overdue).length

  // 波B Step3:左轨承载全部数据/校验/演绎面板(原右轨的 校验/演绎 并入左轨,消除第4列)。
  // 写作 chat 不再是这里的 cap —— 它经 portal 渲染进右栏 ChiefDock(见下方 chatPortal)。
  const leftCaps = [
    // F-06: 「大纲」段下线——章导航职能交给左侧项目树(树取代扁平章列)。
    // 结构/母题/检索暂留(分期摊风险)。
    { key: 'material', label: '素材 · 结构/母题/检索', icon: LayoutList, render: () => (
      <div>
        <Segmented value={matSeg} onChange={setMatSeg} options={[
          { key: 'structure', label: '结构' },
          { key: 'motifs', label: '母题' }, { key: 'recall', label: '检索' },
        ]} />
        {matSeg === 'structure' && renderStructure()}
        {matSeg === 'motifs' && renderMotifs()}
        {matSeg === 'recall' && renderRecall()}
      </div>
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
    { key: 'frame', label: '帧/意图', icon: Eye, render: () => (
      <FramePanel focalizer={focalizer} chapter={chapter} />
    ) },
    { key: 'versions', label: '存档', icon: Bookmark, render: () => (
      <VersionPanel seq={chapter} refreshKey={verTick}
        onRestore={(text) => { setProse(text); persist(text).catch(() => {}) }} />
    ) },
  ]

  // 铁律:WriteChat 组件实例、props、onProposal/onProposalStart/onProposalChunk 回调
  // 与原 rightCaps.chat.render 一字不差 —— 同一组件、同一闭包(共享 WriteLayout 全部状态),
  // 只把 DOM 落点从「内部 Shell 右栏」改成「ChiefDock 右栏槽」(portal)。
  const writeChatEl = (
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
  )
  // 槽就绪 → portal 进右栏;未就绪(极短时序窗口)→ 兜底浮窗,绝不丢 chat、不破坏主布局。
  // portal 在不同 container 间移动只搬 DOM、不卸载组件,WriteChat 内部状态(对话历史等)全程保留。
  const chatPortal = slotEl
    ? createPortal(writeChatEl, slotEl)
    : (
      <div className="fixed bottom-3 right-3 z-40 w-[332px] h-[60vh] rounded-xl border border-line bg-surface shadow-xl overflow-hidden flex flex-col min-h-0">
        {writeChatEl}
      </div>
    )

  return (
    <>
      {/* 数据面板(素材/校验/演绎/帧/存档)已上移到 BinderLayout 左栏 LeftDock;正文中区只留编辑器 */}
      <Shell center={center} />
      {chatPortal}
      {/* F-05 完整:点正文波浪线弹出的悬浮卡 — 类别 + message + 让主编改这处 + 忽略 */}
      {issueCard && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIssueCard(null)} />
          <div className="fixed z-50 w-[260px] rounded-xl border border-line bg-surface shadow-xl p-3"
            style={{
              left: Math.min(Math.max(8, issueCard.x), window.innerWidth - 272),
              top: Math.min(issueCard.y, window.innerHeight - 140),
            }}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className={`w-2 h-2 rounded-full shrink-0 ${issueDot(issueCard.issue.type)}`} />
              <span className="text-f12 font-semibold text-ink">{issueLabel(issueCard.issue.type)}</span>
            </div>
            <div className="text-f12 text-fore leading-snug mb-2">{issueCard.issue.message}</div>
            {issueCard.issue.text && (
              <div className="text-f12 text-faint leading-snug mb-2.5 line-clamp-2 border-l-2 border-line pl-2">
                「{issueCard.issue.text}」
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <button onClick={() => sendIssueToChief(issueCard.issue)}
                className="flex-1 h-7 inline-flex items-center justify-center gap-1 rounded-lg border border-brand/40 bg-brand/5 text-brand text-f12 hover:bg-brand/15 cursor-pointer transition-colors">
                <Sparkles size={12} />让主编改这处
              </button>
              <button onClick={() => ignoreIssueHandler(issueCard.issue)}
                className="h-7 px-2.5 rounded-lg border border-line text-faint text-f12 hover:bg-soft cursor-pointer transition-colors">
                忽略
              </button>
            </div>
          </div>
        </>
      )}
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

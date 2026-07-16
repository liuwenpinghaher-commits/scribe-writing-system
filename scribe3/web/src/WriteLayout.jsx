import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Save, MessagesSquare, ShieldCheck, ShieldOff, Bookmark,
  Users, AlignCenter, Search, CircleAlert, CircleCheck, CircleDashed, Lock,
  BookText, LayoutList, Flame, Sparkles, Eye, ChevronDown, Check,
  DatabaseZap, Loader2, AlertTriangle,
} from 'lucide-react'
import { api } from './api'
import { causalStatus } from './causalStatus.js'
import { Shell } from './shell'
import { Btn, Input, SectionTitle, Empty, Row, Tag } from './ui'
import { Chip } from './ui/Chip'
import { ProseEditor } from './editor/ProseEditor'
import { applyProposal } from './editor/applyProposal.js'
import { issueLabel, issueDot, ignoreIssue, filterIgnored, expandToSentence } from './editor/guardIssues.js'
import { DraftCard } from './editor/DraftCard'
import { WriteChat } from './WriteChat'
import { NorthStarBar } from './NorthStarBar'
import { PulseBar } from './PulseBar'
import { ChapterMemoryRefs } from './ChapterMemoryRefs'
import { loadButtons, addButton } from './lib/rewriteButtons.js'
import { InputDialog } from './ui/Dialog.jsx'
import { useToast, dismissToast, showToast } from './ui/Toast.jsx'
import { useChiefSlot } from './ChiefSlotContext'

// 右坞「恢复到此版本」同步编辑器(F3/彻查 G-E4):BinderLayout 持有的共享信号。
// 右坞 doRestore 落库后 bump restoreTick;WriteLayout(经 DetailPane 隔开、无法直接传 prop)
// 用 useContext 消费,把 restoreTick 加进本章重拉 effect 依赖 → 恢复即重拉库中最新正文,
// 覆盖编辑器旧内容(=用户确认丢弃未存改动的恢复语义),杜绝续编辑覆盖恢复结果。
// 定义在此(WriteLayout 不反向 import BinderLayout/studioDocks)→ 供两者 import 且零环。
export const RestoreContext = createContext(0)

// 写作台(对话驱动):中区手稿 + 右轨主编对话出草稿卡。限知/校验后台支撑。与推演台共用同一份数据。
// seq: 外部(项目树)驱动的当前章号(F-06)。给定时同步到内部 chapter 状态。
// (Task 7:内部上一章/下一章步进器已删——章导航唯一真身在 ChapterStudio 的 ObjectFrame,
//  换章单向走外部 seq prop;onSeqChange 形参已随之删除,唯一调用方 ChapterStudio 不再传。)
export function WriteLayout({ work, seq, sceneIdx }) {
  api.setWork(work)
  const toast = useToast()
  // 波B Step3:WriteChat 经 portal 渲染进右栏 ChiefDock 的槽。slotEl 为该槽 DOM。
  const { slotEl } = useChiefSlot()
  // 隐藏保活容器:切到非主编 tab(选择环/存档/Pilot/收件箱)时 slotEl=null,WriteChat
  // portal 进此隐藏 div——不可见不遮挡,但组件不卸载、对话历史/输入全程保留
  // (根治旧兜底 fixed 浮窗切 tab 后浮起遮挡 + 浮窗外框套输入框的框套框)。
  const [hiddenSlotEl, setHiddenSlotEl] = useState(null)
  // F3:右坞恢复信号。bump 时本章重拉 effect 重跑 → 编辑器同步为库中最新(恢复版)正文。
  const restoreTick = useContext(RestoreContext)
  const proseEditorRef = useRef(null)  // F-05: ref to ProseEditor for focusIssue
  const [chapter, _setChapter] = useState(seq || 1)
  // (Task 7:章导航上界 maxSeq 拉取已上移 ChapterStudio——本组件不再有内部步进器。)
  // 审查 P1-3:保存失败时的本地暂存(localStorage)——自动保存的两条失败路径
  // (切章 fire-and-forget / 卸载兜底 flush)里编辑内容随实例销毁,暂存是唯一找回渠道。
  const stashKey = (w, s) => `s3_unsaved:${w || 'main'}:${s}`
  const stashUnsaved = (w, s, p, t, f) => {
    try {
      localStorage.setItem(stashKey(w, s), JSON.stringify({ prose: p, chTitle: t, focalizer: f, ts: Date.now() }))
    } catch { /* 配额满等:暂存失败不再有兜底,toast 文案已如实 */ }
  }
  const [stash, setStash] = useState(null)   // 挂载检测到的未保存暂存稿(横幅数据)

  // persistDirtyOldChapter:切章前若有未保存内容,静默保存旧章(fire-and-forget,不阻断切章)
  // 全部从 dirtyRef 读取,完全脱离 state 闭包,任何调用时机都拿到最新值。
  const persistDirtyOldChapter = (targetSeq) => {
    const { seq: oldSeq, prose: oldProse, chTitle: oldChTitle, focalizer: oldFocalizer, dirty } = dirtyRef.current
    if (!dirty || oldProse === undefined || oldSeq == null || oldSeq === targetSeq) return
    // 乐观置净:先标 dirty=false,避免与卸载兜底 flush(见下)对同一改动重复保存;失败再恢复
    dirtyRef.current.dirty = false
    api.saveChapter(oldSeq, oldProse, oldChTitle, oldFocalizer, work)
      .then(() => { setSaved(true) })
      .catch((e) => {
        // 审查 P1-3:失败即暂存本地(唯一可靠去处——此 catch 异步到达时多半已切章,
        // dirtyRef 已被新章加载重置,恢复 dirty 会误标新章,须 seq 守卫)。
        stashUnsaved(work, oldSeq, oldProse, oldChTitle, oldFocalizer)
        if (dirtyRef.current.seq === oldSeq) dirtyRef.current.dirty = true
        toast(e?.status === 409 ? `第 ${oldSeq} 章生成在途,本次编辑已暂存本地,回该章可恢复`
          : `第 ${oldSeq} 章自动保存失败,编辑已暂存本地,回该章可恢复`, { tone: 'danger' })
      })
  }

  // (Task 7:内部步进器 setChapter 包装已删——换章只剩「外部 seq 变化」一条路径,见下 effect。)
  // 外部 seq 变化(树点章)→ 切章前若有未保存内容先 persist 旧章,再同步内部章号
  useEffect(() => {
    if (seq == null || seq === chapter) return
    persistDirtyOldChapter(seq)
    _setChapter(seq)
  }, [seq])
  // 切章丢稿根治(F1/彻查 G-B3):外部切章(项目树点章)由上层 DetailPane 的
  // ErrorBoundary(key=节点 id=ch:seq)整树重挂 WriteLayout —— 旧实例直接卸载,上面的
  // [seq] 同步 effect 来不及在旧实例里 flush。ProseEditor 无 onBlur,未手存正文只活在
  // dirtyRef 里,重挂即永久丢失。此处补一个「卸载兜底 flush」:组件卸载时若 dirtyRef 仍脏,
  // fire-and-forget 落库旧章(fetch 不随组件卸载中断)。与 persistDirtyOldChapter 的乐观
  // 置净配合去重:内部步进已 persist 的改动此刻 dirty 已 false,不重复保存。
  // Critical(切书):⌘K 切书时 App.open 先同步 api.setWork(B) 再触发重挂,此刻全局 WORK 已是 B,
  // 若 saveChapter 走全局 WORK 会把 A 的正文写进 B(静默跨书损坏)。故传本实例捕获的 work(空 deps
  // 闭包捕获、key=${work} 保证实例内稳定)钉死目标书 —— 见 api.saveChapter 的 work 形参。
  useEffect(() => {
    return () => {
      const { seq: oldSeq, prose: oldProse, chTitle: oldChTitle, focalizer: oldFocalizer, dirty } = dirtyRef.current
      if (!dirty || oldProse === undefined || oldSeq == null) return
      dirtyRef.current.dirty = false
      api.saveChapter(oldSeq, oldProse, oldChTitle, oldFocalizer, work)
        .catch((e) => {
          // 审查 P1-3:组件已卸载,编辑器与 dirtyRef 均已销毁,"请手动保存"无从执行,
          // "编辑不会丢"更是空话——暂存 localStorage 是此路径唯一真兑现。
          stashUnsaved(work, oldSeq, oldProse, oldChTitle, oldFocalizer)
          showToast(e?.status === 409 ? `第 ${oldSeq} 章生成在途,本次编辑已暂存本地,回该章可恢复`
            : `第 ${oldSeq} 章保存失败,编辑已暂存本地,回该章可恢复`, { tone: 'danger' })
        })
    }
  }, [])
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
  // 批D P1-5:/causal 现返回 {no_event_data, violations}(非裸 list)。持整个对象,派生态经 causalStatus。
  // 初值 null → causalStatus 归一为「无数据」中性态,首帧不闪「因果完整✅」假绿。
  const [causal, setCausal] = useState(null)
  const [motifs, setMotifs] = useState([])
  const [focusMode, setFocusMode] = useState(false)
  const [chTitle, setChTitle] = useState('')
  const [saved, setSaved] = useState(true)
  // dirty 切章防丢:用 ref 追踪当前章号 + 实时正文 + chTitle + focalizer + dirty 状态,
  // 全部从 ref 读,完全脱离 state 闭包,确保切章时拿到最新值。
  const dirtyRef = useRef({ seq: chapter, prose: '', chTitle: '', focalizer: '', dirty: false })
  const [btns, setBtns] = useState(() => loadButtons(work))
  // 断头修复#12:右栏 tab 由 RightDock(usePref)独立持有——原 rightActive 死状态删除,
  // "让主编改这处"等改经窗口事件切右栏到主编 tab(RightDock 端监听 s3-right-tab)。
  const focusChiefTab = () => {
    try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
  }
  const [tick, setTick] = useState(0)
  const [dlg, setDlg] = useState(null)
  const [serif, setSerif] = useState(() => localStorage.getItem('scribe3:serif') === '1')
  // 达标 toast:记录上次 persist 前的 today_words,save 后比较是否跨过 daily_word_goal
  const prevTodayWordsRef = useRef(null)
  const [saveMenu, setSaveMenu] = useState(false)
  const saveMenuRef = useRef(null)
  const [guardPop, setGuardPop] = useState(false)
  const guardPopRef = useRef(null)
  // 进度显性化(批二):/progress 返回 today_words/daily_word_goal/current_streak/total_words/total_word_goal。
  // 挂载 + 存章后刷新;拉取失败置 null → 顶栏优雅降级为只显字数。
  const [progress, setProgress] = useState(null)
  const [progPop, setProgPop] = useState(false)
  const progPopRef = useRef(null)
  // ingest 反哺设定库:busy 态防重复点击
  const [ingesting, setIngesting] = useState(false)

  // (原窄屏自动收右栏 effect 已删:它 set 的 rightActive 是零消费死状态,自 F-06 起
  // 无任何实际效果;右栏收起现由 BinderLayout 折叠体系承担——点轨当前项/拖分隔条。)

  // 主编主动化 T5·时机D(M9 卡文诊断):每 60s 采样正文长度,连续 5 个采样点
  // 净变化 ≤0(删多写少/零输入)→ 主编问一句(每章一次;纯话术零表,三处方)。
  const stuckRef = useRef({ seq: null, samples: [] })
  useEffect(() => {
    const t = setInterval(() => {
      const s = stuckRef.current
      if (s.seq !== chapter) { s.seq = chapter; s.samples = [] }
      // 审查 P1-5:删旧闭包 prose 回退(空新章会回退到旧章长度,采样恒等误报卡文);
      // dirtyRef 载入时已同步,是唯一权威源。输入框/编辑器聚焦中不打断(计划坑防)。
      if (localStorage.getItem(`s3.pulse.mute.${work || 'main'}.stuck`) === '1') return   // R2-10:键含 work
      const ae = document.activeElement
      const typing = ae && (ae.tagName === 'TEXTAREA' || ae.tagName === 'INPUT' || ae.isContentEditable)
      s.samples.push((dirtyRef.current.prose || '').length)
      if (typing && s.samples.length >= 6) { s.samples = s.samples.slice(-5); return }
      if (s.samples.length < 6) return
      s.samples = s.samples.slice(-6)
      const delta = s.samples[5] - s.samples[0]
      const spokeKey = `s3.spoke.${work || 'main'}.${chapter}.stuck`
      if (delta <= 0 && s.samples[0] > 0 && localStorage.getItem(spokeKey) !== '1') {
        localStorage.setItem(spokeKey, '1')
        toast('这五分钟正文没往前走(依据:字数采样)——卡住了?', {
          tone: 'info', duration: 8000,
          action: { label: '聊聊', onClick: () => {
            try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: '我卡住了。帮我诊断:是情节卡(回查本章目标与对手/冲突要不要升级/要不要切配角视角)、语言卡(换个叙述距离或语感重起这段),还是心态卡(先写烂再改)?给我一个最小可行的下一步。' })) } catch { /* */ }
            focusChiefTab()
          } },
          // R2-10:stuck 维静音写入点(此前 s3.pulse.mute.stuck 是死键,防烦协议对卡文维不成立)
          cancel: { label: '不再提醒', onClick: () => { try { localStorage.setItem(`s3.pulse.mute.${work || 'main'}.stuck`, '1') } catch { /* */ } } },
        })
      }
    }, 60000)
    return () => clearInterval(t)
  }, [chapter, work])

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
            leaks_error: r.leaks_error || null,     // U-011: 检测器故障红字显示
            issues_error: r.issues_error || null,
            qc: r.qc || { repetition: 0, structural: 0, purple: 0 },
            issues: r.issues || [],  // F-05: 带 range 的 issues 列表
          })
        })
        // U-011: /check 整个失败此前被静默吞(护栏面板悄悄保持旧状态=假绿)——标故障红字
        .catch((e) => { if (alive) setGuard((g) => ({ ...g, leaks_error: `护栏检查失败:${e?.message || e}` })) })
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
      // 审查 P1-3:检测本章暂存稿——与库中一致(后来存上了)静默清除;不一致弹恢复横幅。
      try {
        const raw = localStorage.getItem(stashKey(work, chapter))
        if (raw) {
          const st0 = JSON.parse(raw)
          if ((st0?.prose ?? '') === p) { localStorage.removeItem(stashKey(work, chapter)); setStash(null) }
          else setStash({ ...st0, seq: chapter })
        } else setStash(null)
      } catch { setStash(null) }
    })
    api.causal(chapter).then(setCausal)
    api.qc(chapter).then(setQc)
    // restoreTick:右坞恢复后 bump → 重拉本章,setProse 为库中恢复版并重置 dirtyRef。
  }, [chapter, tick, restoreTick])
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
    focusChiefTab()
  }

  const chars = entities.filter((e) => e.kind === 'character')
  const focName = (chars.find((c) => c.id === focalizer) || {}).name || '—'
  const wordCount = prose.replace(/\s/g, '').length
  const qcN = qc ? (qc.repetition?.length || qc.repetition || 0) + (qc.structural?.length || qc.structural || 0) + (qc.purple?.length || qc.purple || 0) : 0
  // U-011:检测器故障(后端 detector_errors)——"QC 0"可能是真没问题、也可能是检测器炸了没检。
  // 有 detector_errors 就红字标出"本次未检",不让假绿蒙混。
  const qcErrNames = qc?.detector_errors ? Object.keys(qc.detector_errors) : []
  // /causal 三态派生:状态条(renderVerify)与校验徽章(reviewBadge)同源,防「因果完整✅」假绿。
  const cstat = causalStatus(causal)

  // ——— 体检卡(断头修复:原死 leftCaps 的 renderVerify 回填中区正文列;结构/事件/
  // 检索/伏笔列表已由左栏各 tab 承载,「在场选视角」与顶栏视角下拉重复故删,
  // 其余死渲染函数与 leftCaps 数组一并移除,见台账 D-029)———
  const renderCheckupCard = () => ((postCheckResult || postChecking) ? (
    <div className="mb-4 rounded-xl border border-line bg-surface p-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <div className="text-f12 font-semibold text-ink">全量体检</div>
        {postChecking && <Loader2 size={13} className="animate-spin text-brand" />}
        <button onClick={() => setPostCheckResult(null)}
          className="ml-auto text-meta text-faint hover:text-ink cursor-pointer">关闭</button>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-meta">
        <span className={leaks > 0 ? 'text-danger' : 'text-ok'}>泄露 {leaks}</span>
        <span className={qcN > 0 ? 'text-warn' : 'text-ok'}>QC {qcN}</span>
        {qcErrNames.length > 0 && (
          <span className="text-danger" title={`失败检测器:${qcErrNames.join('、')}`}>
            ⚠ 检测器故障·本次未检({qcErrNames.join('、')})
          </span>
        )}
        <span className={cstat.state === 'violations' ? 'text-danger' : 'text-faint'}>
          因果 {cstat.state === 'violations' ? `${cstat.count} 违规` : cstat.state === 'no-data' ? '无数据' : '完整'}
        </span>
      </div>
      {postCheckResult && !postCheckResult.error && (
        <div className="space-y-1.5">
          {postCheckResult.issues && postCheckResult.issues.length > 0 && (
            <div className="rounded-lg border border-line divide-y divide-line/50 max-h-56 overflow-y-auto">
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
                      className="shrink-0 text-meta text-brand opacity-0 group-hover:opacity-100 hover:underline cursor-pointer transition-opacity">
                      改这处
                    </button>
                  )}
                  {iss.range && <span className="shrink-0 text-meta text-brand">跳→</span>}
                </div>
              ))}
            </div>
          )}
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
          <div className={`text-f12 rounded-lg px-2 py-1.5 ${postCheckResult.leaks?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
            <span className="font-medium">泄露</span>
            {postCheckResult.leaks?.length > 0
              ? <span className="ml-1">{postCheckResult.leaks.length} 处:{postCheckResult.leaks.map((l) => l.marker).join('、')}</span>
              : ' 无'}
          </div>
          {postCheckResult.discipline && (
            <div className={`text-f12 rounded-lg px-2 py-1.5 ${postCheckResult.discipline.violations?.length > 0 ? 'bg-danger/10 text-danger' : 'bg-ok/10 text-ok'}`}>
              <span className="font-medium">纪律</span>
              {postCheckResult.discipline.violations?.length > 0
                ? <span className="ml-1">{postCheckResult.discipline.violations.join('、')}</span>
                : ' 守纪'}
            </div>
          )}
          {/* 断头修复 T2.2:跨章一致性检测一直在跑、响应一直携带——这是 UI 首个消费点 */}
          {Array.isArray(postCheckResult.cross_consistency) && (
            <div className={`text-f12 rounded-lg px-2 py-1.5 ${postCheckResult.cross_consistency.length > 0 ? 'bg-warn/10 text-warn' : 'bg-ok/10 text-ok'}`}>
              <span className="font-medium">跨章一致</span>
              {postCheckResult.cross_consistency.length > 0 ? (
                <div className="mt-0.5 space-y-0.5">
                  {postCheckResult.cross_consistency.slice(0, 6).map((h, i) => (
                    <div key={i} className="text-meta leading-snug">· {h.message || h.note || h.type}</div>
                  ))}
                  {postCheckResult.cross_consistency.length > 6 && (
                    <div className="text-meta text-faint">…共 {postCheckResult.cross_consistency.length} 处</div>
                  )}
                </div>
              ) : ' 无疑点'}
            </div>
          )}
          {(postCheckResult.degraded_stages || []).length > 0 && (
            <div className="text-meta text-faint inline-flex items-center gap-1"><AlertTriangle size={11} />部分检测降级({postCheckResult.degraded_stages.join('、')}):没查≠没病</div>
          )}
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
  ) : null)

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
    // 主编主动化 T5·时机B:落稿后有命中 → 主编摘要一条(每章一次,防烦协议)
    try {
      const cnt = (x) => Array.isArray(x) ? x.length : (x || 0)
      // 审查 P2-13:补齐 6 键(此前漏 cross_repetition/duplicate_lines/emotion_telling)
      const qcn = r.qc ? cnt(r.qc.repetition) + cnt(r.qc.structural) + cnt(r.qc.purple)
        + cnt(r.qc.cross_repetition) + cnt(r.qc.duplicate_lines) + cnt(r.qc.emotion_telling) : 0
      const lk = r.leaks || 0
      const spokeKey = `s3.spoke.${work || 'main'}.${chapter}.postsave`
      if ((qcn > 0 || lk > 0) && localStorage.getItem(spokeKey) !== '1'
          && localStorage.getItem(`s3.pulse.mute.${work || 'main'}.quality`) !== '1') {   // R2-10:键含 work
        localStorage.setItem(spokeKey, '1')
        toast(`本章落稿体检:泄露 ${lk} · QC ${qcn}(依据:存稿自动检)`, {
          tone: 'warn',
          action: { label: '要我修吗', onClick: () => {
            try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: `本章存稿检出泄露 ${lk} 处、QC ${qcn} 处,请按清单逐处修复,保持其余原样` })) } catch { /* */ }
            focusChiefTab()
          } },
        })
      }
    } catch { /* 提醒失败不影响保存 */ }
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
    const intent = (typeof sel === 'object' && sel?.intent) || 'edit'
    if (intent === 'discuss') {
      // 聊这段:只讨论不改稿——引用进对话让作者接着问,不设 lastSel(不进候选替换链路)
      setLastSel(null)
      setLastQuote(text)
      setSeedQuote(`就正文这段和你聊聊(先不改稿):「${text}」\n`)
      setCandidates([])
      focusChiefTab()
      return
    }
    setLastSel(typeof sel === 'string' ? null : sel)
    setLastQuote(text)
    setSeedQuote(`把这段改一下,给我 2-3 个侧重不同的候选:「${text}」`)
    setCandidates([])
    focusChiefTab()
  }

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
    focusChiefTab()
  }

  // 「忽略」→ 持久化到 localStorage(prose 指纹 + issue key),并撤掉波浪线
  const ignoreIssueHandler = (iss) => {
    ignoreIssue(prose, iss)
    setIssueCard(null)
    setIgnoreTick((t) => t + 1)
  }

  const topbarMid = (
    <div className="shrink-0 border-b border-line bg-surface px-3 h-11 flex items-center gap-2 min-w-0">
      {/* (Task 7:章节导航子块已删——单套章导航在 ChapterStudio 的 ObjectFrame。) */}
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
                  <div className="text-meta font-semibold uppercase tracking-[.07em] text-faint mb-2">护栏状态</div>
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
                            {iss.range && <span className="shrink-0 text-brand text-meta">跳→</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                  {/* 限知泄露 */}
                  <div className="mb-2">
                    <div className="text-f12 text-faint mb-0.5 flex items-center gap-1"><Lock size={11} />限知泄露词</div>
                    {/* U-011:检测器炸了(leaks_error)必须红字区分——"无泄露"可能是真干净,也可能是没检 */}
                    {guard.leaks_error
                      ? <div className="text-f12 text-danger leading-snug">⚠ 泄露检测器故障·本次未检:{guard.leaks_error}</div>
                      : focalizer && guard.leaks.length > 0
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
                    <span className="ml-auto text-meta text-faint">{guardOn ? '点击关闭' : '点击开启'}</span>
                  </button>
                  <div className="text-meta text-faint mt-1.5 leading-snug">关=完全静默,不校验</div>
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
                <span className="text-meta tnum">{wordCount} 字</span>
                {dailyGoal ? (
                  <span className="hidden sm:inline text-meta tnum text-faint">
                    · 今日 {todayW.toLocaleString()}/{dailyGoal.toLocaleString()}
                    {streak > 1 && <span className="text-warn inline-flex items-center gap-0.5 ml-1"><Flame size={11} />{streak}</span>}
                  </span>
                ) : null}
              </button>
              {progPop && (
                <div className="absolute right-0 top-full mt-1 z-20 min-w-[220px] rounded-lg border border-line bg-surface shadow-lg py-2 px-3">
                  <div className="text-meta font-semibold uppercase tracking-[.07em] text-faint mb-2">写作进度</div>
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
                          <span className="text-faint flex items-center gap-1">今日{streak > 1 && <span className="text-warn text-meta inline-flex items-center gap-0.5"><Flame size={10} />{streak} 连胜</span>}</span>
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
              {/* 全量体检(断头修复:原死 leftCaps 的唯一入口回填)——含 LLM 纪律判,结果卡出现在正文上方 */}
              <button onClick={() => { setSaveMenu(false); runPostCheck() }} disabled={postChecking || !prose.trim()}
                title="全量体检:QC/泄露/纪律/时间线/跨章一致(含 LLM 判,较慢)"
                className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap disabled:opacity-60">
                {postChecking ? <Loader2 size={13} className="text-brand shrink-0 animate-spin" /> : <ShieldCheck size={13} className="text-faint shrink-0" />}
                {postChecking ? '体检中…' : '全量体检'}
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
          } catch { /* persist 已提示,存为正文中止 */ }
        }}>存为正文</Btn>
      </div>
    </div>
  )

  const center = (
    <div className="flex flex-col h-full">
      <div className="flex items-center border-b border-line bg-surface">
        <NorthStarBar />
        {/* 主编主动化 T2:六维脉搏条——信号自动可见,「聊这个」预填右栏写作对话 */}
        <PulseBar seq={chapter} onChat={(p) => { setSeedQuote(p); focusChiefTab() }} />
        <ChapterMemoryRefs chapter={chapter} />
      </div>
      {topbarMid}
      {lastSel && (
        <div className="flex flex-wrap gap-1.5 px-3 py-2 border-b border-line bg-surface">
          {btns.map((b) => (
            <button key={b} onClick={() => {
              setSeedQuote(`把这段按「${b}」改,给我 2-3 个候选:「${lastSel.text}」`)
              setCandidates([]); focusChiefTab()
            }} className="h-6 px-2 rounded-lg border border-line text-meta text-ink hover:bg-soft cursor-pointer">{b}</button>
          ))}
          <button onClick={() => setDlg({ kind: 'rewrite' })} className="h-6 px-2 rounded-lg border border-dashed border-line text-meta text-faint hover:bg-soft cursor-pointer">+ 存为按钮</button>
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-y-auto bg-canvas">
        <div className="max-w-[48rem] mx-auto px-6 py-8">
          {stash && stash.seq === chapter && (
            <div className="mb-4 px-3 py-2 rounded-lg border border-amber-300 bg-amber-50 text-f12 text-ink flex items-center gap-3">
              <span className="flex-1">检测到本章未保存的暂存稿({(stash.prose || '').length} 字,{new Date(stash.ts).toLocaleTimeString()}),与当前正文不一致。</span>
              <button onClick={() => {
                setProse(stash.prose || ''); dirtyRef.current.prose = stash.prose || ''
                dirtyRef.current.dirty = true; setSaved(false)
                try { localStorage.removeItem(stashKey(work, chapter)) } catch { /* */ }
                setStash(null)
              }} className="h-6 px-2 rounded-lg border border-amber-400 hover:bg-amber-100 cursor-pointer shrink-0">恢复到编辑器</button>
              <button onClick={() => {
                try { localStorage.removeItem(stashKey(work, chapter)) } catch { /* */ }
                setStash(null)
              }} className="h-6 px-2 rounded-lg border border-line text-faint hover:bg-soft cursor-pointer shrink-0">丢弃</button>
            </div>
          )}
          {renderCheckupCard()}
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


  // 铁律:WriteChat 组件实例、props、onProposal/onProposalStart/onProposalChunk 回调
  // 与原 rightCaps.chat.render 一字不差 —— 同一组件、同一闭包(共享 WriteLayout 全部状态),
  // 只把 DOM 落点从「内部 Shell 右栏」改成「ChiefDock 右栏槽」(portal)。
  const writeChatEl = (
    <WriteChat chapter={chapter} focalizer={focalizer} seedQuote={seedQuote} phase="final"
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
  // 槽就绪(主编 tab)→ portal 进右栏槽;否则(非主编 tab / 槽未就绪的极短窗口)→ portal 进
  // 隐藏保活容器(display:none),不可见不遮挡、状态全保留。portal 在 container 间移动只搬
  // DOM、不卸载组件,WriteChat 内部状态(对话历史等)全程保留。
  const chatTarget = slotEl || hiddenSlotEl
  const chatPortal = chatTarget ? createPortal(writeChatEl, chatTarget) : null

  return (
    <>
      {/* 数据面板(素材/校验/演绎/帧/存档)已上移到 BinderLayout 左栏 LeftDock;正文中区只留编辑器 */}
      <Shell center={center} />
      {/* 隐藏保活容器:非主编 tab 时 WriteChat portal 落这里(display:none),保状态不遮挡 */}
      <div ref={setHiddenSlotEl} className="hidden" aria-hidden="true" />
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
          } else if (dlg?.kind === 'rewrite') {
            if (val) setBtns(addButton(work, val))
          }
        }}
        onClose={() => setDlg(null)}
      />
    </>
  )
}

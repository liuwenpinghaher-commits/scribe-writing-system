import { useEffect, useRef, useState } from 'react'
import { Sparkles, Loader2, MessagesSquare } from 'lucide-react'
import { api } from './api'
import { useDeduceSel } from './deduceContext'
import { useStageProposal, useChiefSlot, ProposalBar } from './ChiefSlotContext'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'
import { SelectionQuoteActions } from './ui/SelectionQuoteActions.jsx'
import { useContextSnapshot } from './context/ContextSnapshotContext'

// Task 4:话术引用截断——chiefIntent 只是预填输入框,长演绎全文引用会塞爆(spec §4 要点4)。
const QUOTE_MAX = 400
const GENERATE_TIMEOUT_MS = 120000
const GENERATE_TIMEOUT_TEXT = '生成等待超过 2 分钟，已停止等待；未完成内容不会自动保存为投影。'
const truncateQuote = (s) => {
  const t = (s || '').trim()
  return t.length > QUOTE_MAX ? t.slice(0, QUOTE_MAX) + '…' : t
}

// 演绎中区:只读展示 + 主编种子(禁止作者 REST / 表单失焦直写 scene_truth·deductions)。
// 生成结果经种子送主编审批,不本地 dirty 落库。
export function DeduceStage({ seq, meta, onSaved, work }) {
  const toast = useToast()
  const { selected, setSelected } = useDeduceSel()
  const { setChiefIntent } = useChiefSlot()
  const { snapshot } = useContextSnapshot()
  const [preview, setPreview] = useState('') // 生成预览(只读,不直写)
  const [busy, setBusy] = useState(false)
  const [grounding, setGrounding] = useState(null)
  const [roleToAdd, setRoleToAdd] = useState('')
  const generationRef = useRef(null)
  const chars = meta?.chars || []
  const cur = selected === 'truth'
    ? { name: '场景真相', prose: meta?.scene_truth || '' }
    : (meta?.deductions || []).find((d) => d.character_id === selected)
      || { character_id: selected, character_name: (chars.find((c) => c.id === selected) || {}).name || selected, prose: '' }

  const displayText = preview || cur.prose || ''
  const targetName = selected === 'truth' ? '场景真相' : (cur.character_name || selected)

  useEffect(() => {
    setPreview('')
    setGrounding(null)
  }, [selected, seq])

  const askChiefWrite = (content, hintExtra = '') => {
    const body = content != null ? content : displayText
    seedChiefNarrativeWrite(
      'deduce',
      `第 ${seq} 章·${targetName}`,
      `${hintExtra || '请将以下演绎内容写入并提交审批。'}\n字段: ${selected === 'truth' ? 'scene_truth' : 'deductions.' + selected}\n\n${body || '（空）'}`,
    )
    toast('已送主编审批写入(不直接落库)', { tone: 'ok' })
  }

  const { pending, clear } = useStageProposal('deduce', seq, selected)
  const fillPending = () => {
    if (!pending) return
    askChiefWrite(pending.content, '请用以下主编提案覆盖当前演绎:')
    clear()
  }
  const appendPending = () => {
    if (!pending) return
    const next = (displayText ? displayText + '\n\n' : '') + pending.content
    askChiefWrite(next, '请将以下内容并入当前演绎:')
    clear()
  }

  const noProse = !displayText.trim()
  const notifyChief = () => { try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ } }
  const chatCur = () => {
    if (noProse) return
    setChiefIntent({ phase: 'deduce', seq, text: `就本章「${targetName}」的演绎和你聊聊(先不改):「${truncateQuote(displayText)}」\n` })
    notifyChief()
  }
  const editCur = () => {
    if (noProse) return
    setChiefIntent({ phase: 'deduce', seq, text: `把本章「${targetName}」这条演绎改一下,直接给出改后的完整演绎:「${truncateQuote(displayText)}」` })
    notifyChief()
  }

  const addAndSelectRole = async () => {
    if (!roleToAdd) return
    const name = (chars.find((c) => c.id === roleToAdd) || {}).name || roleToAdd
    seedChiefNarrativeWrite(
      'deduce',
      `第 ${seq} 章涉及角色`,
      `请将角色「${name}」(${roleToAdd})加入第 ${seq} 章 involved_characters 并提交审批。`,
    )
    setSelected(roleToAdd)
    setRoleToAdd('')
    toast('已送主编审批加入角色', { tone: 'ok' })
  }

  const stopGeneration = (message = '已停止生成；未完成内容不会自动保存为投影。') => {
    const run = generationRef.current
    if (!run) return
    run.stopped = true
    clearTimeout(run.timer)
    generationRef.current = null
    try { run.abort?.() } catch (_) { /* */ }
    setBusy(false)
    if (selected !== 'truth') setGrounding({ ok: false, reason: message })
    toast(message, { tone: 'warn' })
  }

  const gen = () => {
    if (busy) return
    const target = selected
    const run = { stopped: false, abort: null, timer: null }
    generationRef.current = run
    setBusy(true)
    setGrounding(null)
    setPreview('')
    let acc = ''
    const finish = () => {
      clearTimeout(run.timer)
      if (generationRef.current === run) generationRef.current = null
    }
    const instr = target === 'truth'
      ? `请为第 ${seq} 章写「场景真相」(全知客观)。用 markdown。`
      : `请为第 ${seq} 章写角色「${targetName}」的限知投影。严格遵循角色档案已有的称谓和代词;不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史。信息不足时写“未知”或留白。保留五个 markdown 三级标题。`
    const runPass = (instruction, attempt = 0) => {
      const request = api.chatWrite(instruction, {
        chapter: seq, phase: 'deduce', focalizer: target === 'truth' ? '' : target,
        context: snapshot ? {
          context_session_id: snapshot.session_id,
          context_revision: snapshot.revision,
          context_hash: snapshot.context_hash,
        } : null,
        onProposalStart: () => { if (!run.stopped) { acc = ''; setPreview('') } },
        onProposalChunk: (c) => { if (!run.stopped) { acc += (c?.text ?? c ?? ''); setPreview(acc) } },
        onDelta: (d) => { if (!run.stopped) { acc += d; setPreview(acc) } },
        onProposal: (p) => { if (!run.stopped) { acc = p.prose ?? p.text ?? acc; setPreview(acc) } },
        onDone: async () => {
          if (run.stopped) return
          finish()
          const v = acc.trim()
          if (!v) {
            setBusy(false)
            toast('演绎未返回可用内容，请重试。', { tone: 'danger' })
            return
          }
          setPreview(v)
          if (target === 'truth') {
            setBusy(false)
            askChiefWrite(v, '请将生成的场景真相写入并提交审批:')
            return
          }
          try {
            const review = await api.validateDeduction(seq, v, target, work)
            if (review?.ok) {
              setBusy(false)
              setGrounding({ ok: true })
              askChiefWrite(v, '事实对齐通过。请将以下角色投影写入并提交审批:')
            } else {
              const reason = review?.issues?.[0]?.reason || '存在无法由场景真相支持的主张'
              if (attempt === 0) {
                toast(`首稿未通过事实对齐，正按校验反馈返修：${reason}`, { tone: 'warn', duration: 7000 })
                const repair = `上一稿未通过场景真相事实对齐，原因：${reason}。请重写完整的角色限知投影，只保留能够由场景真相直接支持的主张；不要补充人物、物件、动作、时间、物理现象或前史。信息不足时写“未知”或留白。保留五个 markdown 三级标题。\n\n【待修稿】\n${v.slice(0, 6000)}`
                runPass(repair, 1)
                return
              }
              try {
                const fallback = await api.groundedDeductionFallback(seq, target, work)
                const safe = (fallback?.candidate || '').trim()
                if (!safe) throw new Error('服务端未返回可追溯投影')
                setPreview(safe)
                const safeReview = await api.validateDeduction(seq, safe, target, work)
                if (!safeReview?.ok) throw new Error(safeReview?.issues?.[0]?.reason || '可追溯投影复核失败')
                setBusy(false)
                setGrounding({ ok: true })
                askChiefWrite(safe, '自由稿未过门,已用可追溯摘录。请写入并提交审批:')
              } catch (fallbackError) {
                setBusy(false)
                const fallbackReason = fallbackError?.body?.detail || fallbackError?.message || reason
                setGrounding({ ok: false, reason: fallbackReason })
                toast(`投射未送审：${fallbackReason}`, { tone: 'danger', duration: 7000 })
              }
            }
          } catch (e) {
            setBusy(false)
            setGrounding({ ok: false, reason: '事实对齐服务不可用' })
            toast('投射未送审：事实对齐服务不可用，请稍后重试。', { tone: 'danger', duration: 7000 })
          }
        },
        onError: (e) => {
          if (run.stopped) return
          finish()
          setBusy(false); toast('演绎失败:' + e, { tone: 'danger' })
        },
      })
      run.abort = () => request?.abort?.()
      run.timer = setTimeout(() => {
        if (run.stopped || generationRef.current !== run) return
        run.stopped = true
        clearTimeout(run.timer)
        generationRef.current = null
        try { run.abort?.() } catch (_) { /* */ }
        setBusy(false)
        if (target !== 'truth') setGrounding({ ok: false, reason: GENERATE_TIMEOUT_TEXT })
        toast(GENERATE_TIMEOUT_TEXT, { tone: 'warn', duration: 7000 })
      }, GENERATE_TIMEOUT_MS)
    }
    runPass(instr)
  }

  const hasChapter = Number.isInteger(Number(seq)) && Number(seq) >= 1
  if (!hasChapter) return (
    <div data-testid="deduce-stage-missing-chapter" className="p-6 text-f13 text-faint">
      请先在「手稿」中选择一个章节，再进行场景真相和角色限知演绎。
    </div>
  )

  return (
    <div
      data-testid="deduce-stage"
      className="w-full max-w-[min(1120px,calc(100%-48px))] mx-auto px-6 py-6 h-full flex flex-col min-h-0"
    >
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <h3 className="type-section text-ink">{selected === 'truth' ? '场景真相 · 全知' : `${cur.character_name} · 限知投影`}</h3>
        {chars.length > 0 && (
          <div className="flex items-center gap-1 ml-auto">
            <select aria-label="投射角色" value={roleToAdd} onChange={(e) => setRoleToAdd(e.target.value)}
              className="h-[34px] max-w-32 rounded-lg border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand cursor-pointer">
              <option value="">加入角色…</option>
              {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <Btn variant="ghost" size="sm" onClick={addAndSelectRole} disabled={!roleToAdd}>
              加入并切换角色
            </Btn>
          </div>
        )}
        <Btn variant="ghost" size="sm" onClick={chatCur} disabled={noProse}
          title={noProse ? '就这条演绎和主编讨论(该演绎还没有内容)' : '就这条演绎和主编讨论'}
          aria-label="就这条演绎和主编讨论" className={chars.length > 0 ? '' : 'ml-auto'}>
          <MessagesSquare size={13} />聊这条
        </Btn>
        <Btn variant="ghost" size="sm" onClick={editCur} disabled={noProse}
          title={noProse ? '让主编改这条演绎(该演绎还没有内容)' : '让主编改这条演绎'}
          aria-label="让主编改这条演绎">
          <Sparkles size={13} />改这条
        </Btn>
        {busy && <Btn variant="ghost" size="sm" onClick={() => stopGeneration()}>停止</Btn>}
        <Btn variant="primary" size="sm" onClick={gen} disabled={busy}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}{busy ? '演绎中…' : '生成'}
        </Btn>
        <Btn variant="primary" size="sm" data-testid="deduce-ask-chief" onClick={() => askChiefWrite()}>
          让主编写入
        </Btn>
      </div>
      {pending && (
        <ProposalBar
          text={`主编生成了「${selected === 'truth' ? '场景真相' : cur.character_name}」的内容(${pending.content.replace(/\s/g, '').length} 字)。`}
          actions={[{ label: '送审填入', variant: 'primary', onClick: fillPending }, { label: '送审追加', onClick: appendPending }]}
          onDismiss={clear}
        />
      )}
      <SelectionQuoteActions
        scopeLabel={selected === 'truth' ? `第 ${seq} 章场景真相` : `第 ${seq} 章「${targetName}」限知`}
        className="flex-1 min-h-0 overflow-y-auto type-stage whitespace-pre-wrap"
        data-testid="deduce-readonly"
        disabled={noProse}
      >
        <div aria-label={selected === 'truth' ? '场景真相' : '限知投影'}>
          {displayText.trim()
            ? displayText
            : <span className="text-faint">（空 · 由主编审批写入；可先「生成」预览再送审）</span>}
        </div>
      </SelectionQuoteActions>
      {selected !== 'truth' && grounding && (
        <div role="status" className={`text-f12 mt-2 ${grounding.ok ? 'text-ok' : 'text-danger'}`}>
          {grounding.ok ? '事实对齐通过：已/可送主编审批写入。' : `事实对齐未通过：${grounding.reason}`}
        </div>
      )}
      <div className="text-f12 text-faint mt-2">只读检视;写入一律主编审批。所有角色投影都从「场景真相」派生。</div>
    </div>
  )
}

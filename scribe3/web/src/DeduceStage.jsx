import { useEffect, useRef, useState } from 'react'
import { Sparkles, Loader2, MessagesSquare } from 'lucide-react'
import { api } from './api'
import { useDeduceSel } from './deduceContext'
import { useChiefSlot } from './ChiefSlotContext'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { SelectionQuoteActions } from './ui/SelectionQuoteActions.jsx'
import { useContextSnapshot } from './context/ContextSnapshotContext'

// Task 4:话术引用截断——chiefIntent 只是预填输入框,长演绎全文引用会塞爆(spec §4 要点4)。
const QUOTE_MAX = 400
// TokenPlan 的工具搜索、MCP 联查与长推理在高负载时会超过两分钟；不得在模型
// 仍正常执行时由 UI 取消作者的 Run。作者仍可通过显式停止随时中止。
export const GENERATE_TIMEOUT_MS = 360000
const GENERATE_TIMEOUT_TEXT = '生成等待超过 6 分钟，已停止等待；未完成内容不会自动保存为投影。'
const truncateQuote = (s) => {
  const t = (s || '').trim()
  return t.length > QUOTE_MAX ? t.slice(0, QUOTE_MAX) + '…' : t
}

// 演绎中区:只读展示 + 阶段专用 Run。它不能借普通 chatWrite 或主编种子绕过
// scribe3_deduce 的物理工具面；唯一写入口是 s3_generate_stage(stage=deduce)。
export function DeduceStage({ seq, meta, onSaved, work }) {
  const toast = useToast()
  const { selected, setSelected } = useDeduceSel()
  const { setChiefIntent } = useChiefSlot()
  const { snapshot } = useContextSnapshot()
  const [preview, setPreview] = useState('') // 生成预览(本地草案,不直写正典)
  const [previewDraft, setPreviewDraft] = useState('')
  const [editingPreview, setEditingPreview] = useState(false)
  const [previewReady, setPreviewReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [approval, setApproval] = useState(null)
  const [roleToAdd, setRoleToAdd] = useState('')
  // H3：并行多视角（preview | deduce 并列）
  const [parallelFocals, setParallelFocals] = useState('')
  const [parallelMode, setParallelMode] = useState('preview') // preview | deduce
  const [parallelPlan, setParallelPlan] = useState(null)
  const [parallelResults, setParallelResults] = useState(null)
  const [parallelBusy, setParallelBusy] = useState(false)
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
    setPreviewDraft('')
    setEditingPreview(false)
    setPreviewReady(false)
  }, [selected, seq])

  useEffect(() => {
    setApproval(null)
  }, [seq])

  // 审批是持久 Run trace 的事实，不是本地 React state。刷新/重挂后从本章 deduce
  // scope 恢复，且只暴露最小审批卡字段；避免跨章、跨阶段或已决审批错误回显。
  useEffect(() => {
    let active = true
    const chapter = Number(seq)
    if (!Number.isInteger(chapter) || chapter < 1) return () => { active = false }
    api.aiRunPendingApproval({ chapter, phase: 'deduce' }, work)
      .then(({ runs } = {}) => {
        const pending = Array.isArray(runs) ? runs[0] : null
        if (!active || !pending?.run_id || !pending?.approval_id) return
        setApproval((current) => current || { ...pending, status: 'pending' })
      })
      // 恢复查询失败不应伪造“无待审批”；当前 Run 的 SSE 仍可正常交付审批卡。
      .catch(() => {})
    return () => { active = false }
  }, [seq, work])

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
    setChiefIntent({
      phase: 'deduce', seq,
      text: `请在演绎工作台选择角色「${name}」(${roleToAdd})后生成；章节演绎写入必须走受限 Run 的审批。`,
    })
    notifyChief()
    setSelected(roleToAdd)
    setRoleToAdd('')
    toast('已切换角色；请用「生成」经受限 Run 提交演绎审批。', { tone: 'ok' })
  }

  const stopGeneration = (message = '已停止生成；未完成内容不会自动保存为投影。') => {
    const run = generationRef.current
    if (!run) return
    run.stopped = true
    clearTimeout(run.timer)
    generationRef.current = null
    try { run.abort?.() } catch (_) { /* */ }
    setBusy(false)
    toast(message, { tone: 'warn' })
  }

  // 作者编辑仍只改本地预览；真正的世界写入只能在随后 deduce Run 的 MCP 审批后发生。
  // 角色投影修改后重新过事实对齐，不能让编辑态成为绕过限知校验的旁路。
  const beginPreviewEdit = () => {
    if (busy || !preview.trim()) return
    setPreviewDraft(preview)
    setEditingPreview(true)
    setPreviewReady(false)
  }

  const finishPreviewEdit = async () => {
    const candidate = previewDraft.trim()
    if (!candidate) {
      toast('预览不能为空；可继续编辑或取消。', { tone: 'danger' })
      return
    }
    if (selected === 'truth') {
      setPreview(candidate)
      setEditingPreview(false)
      setPreviewReady(true)
      toast('已保留作者修订；确认后可提交审批写入。', { tone: 'ok' })
      return
    }
    setBusy(true)
    try {
      const review = await api.validateDeduction(seq, candidate, selected, work)
      if (!review?.ok) {
        setPreviewReady(false)
        toast(`修订后的投影未通过事实对齐：${review?.issues?.[0]?.reason || '存在无来源主张'}`, { tone: 'danger' })
        return
      }
      setPreview(candidate)
      setEditingPreview(false)
      setPreviewReady(true)
      toast('作者修订已通过事实对齐；确认后可提交审批写入。', { tone: 'ok' })
    } catch (_) {
      setPreviewReady(false)
      toast('修订后的投影未送审：事实对齐服务不可用。', { tone: 'danger' })
    } finally {
      setBusy(false)
    }
  }

  const resolveApproval = async (decision) => {
    const current = approval
    if (!current?.run_id || current.status !== 'pending') return
    setApproval({ ...current, status: 'submitting' })
    try {
      const result = await api.aiRunApproval(current.run_id, {
        approval_id: current.approval_id,
        decision,
      })
      if (result?.trace_status && result.trace_status !== 'completed') {
        const reason = result?.policy_violations?.[0]?.code || '终态审计未完成'
        setBusy(false)
        setApproval({ ...current, status: 'error', error: reason })
        return
      }
      const activeRun = generationRef.current
      if (activeRun?.runId === current.run_id) {
        clearTimeout(activeRun.timer)
        generationRef.current = null
      }
      setBusy(false)
      setPreviewReady(false)
      setApproval({ ...current, status: decision === 'approve' ? 'approved' : 'denied' })
      if (decision === 'approve') onSaved?.()
    } catch (e) {
      setBusy(false)
      setApproval({ ...current, status: 'error', error: e?.body?.detail || e?.message || '审批提交失败' })
    }
  }

  const gen = () => {
    if (busy) return
    const target = selected
    const run = { stopped: false, abort: null, timer: null }
    generationRef.current = run
    setBusy(true)
    setApproval(null)
    setPreview('')
    setPreviewDraft('')
    setEditingPreview(false)
    setPreviewReady(false)
    let acc = ''
    const finish = () => {
      clearTimeout(run.timer)
      if (generationRef.current === run) generationRef.current = null
    }
    const instr = target === 'truth'
      ? `请为第 ${seq} 章生成全知客观的「场景真相」预览。必须先调用一次 s3_get_chapter 读取当前章节与世界约束；只输出可供作者审阅的 markdown，不得调用写工具或改动任何正典。`
      : `请为第 ${seq} 章角色「${targetName}」生成限知投影预览。严格遵循角色档案已有的称谓和代词；不得新增场景真相中不存在的人物、物件、动作、时间、物理现象或人物前史。信息不足时写“未知”或留白。保留五个 markdown 三级标题；只输出可供作者审阅的内容，不得调用写工具或改动任何正典。`
    const request = api.runWrite(instr, {
        chapter: seq, phase: 'deduce_preview', focalizer: target === 'truth' ? '' : target,
        context: snapshot ? {
          context_session_id: snapshot.session_id,
          context_revision: snapshot.revision,
          context_hash: snapshot.context_hash,
        } : null,
        onDelta: (d) => { if (!run.stopped) { acc += d; setPreview(acc) } },
        onDone: async () => {
          if (run.stopped) return
          finish()
          const v = acc.trim()
          if (!v) {
            setBusy(false)
            toast('演绎预览未返回可用内容，请重试。', { tone: 'danger' })
            return
          }
          setPreview(v)
          setBusy(false)
          if (target === 'truth') {
            setPreviewReady(true)
            toast('场景真相预览已生成；确认后可提交审批写入。', { tone: 'ok' })
            return
          }
          try {
            const review = await api.validateDeduction(seq, v, target, work)
            if (review?.ok) {
              setPreviewReady(true)
              toast('投影预览已通过事实对齐；确认后可提交审批写入。', { tone: 'ok' })
            } else {
              toast(`投影预览未通过事实对齐：${review?.issues?.[0]?.reason || '存在无来源主张'}`, { tone: 'danger' })
            }
          } catch (_) {
            toast('投影预览未送审：事实对齐服务不可用。', { tone: 'danger' })
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
        toast(GENERATE_TIMEOUT_TEXT, { tone: 'warn', duration: 7000 })
      }, GENERATE_TIMEOUT_MS)
  }

  const submitPreview = () => {
    const candidate = preview.trim()
    if (!previewReady || !candidate || busy) return
    const target = selected
    const existing = Array.isArray(meta?.deductions) ? meta.deductions : []
    const existingInvolved = Array.isArray(meta?.involved_characters) ? meta.involved_characters : []
    const payload = target === 'truth'
      ? { scene_truth: candidate }
      : {
          involved_characters: [...new Set([...existingInvolved, target])],
          deductions: [
            ...existing.filter((d) => d?.character_id !== target),
            { character_id: target, prose: candidate },
          ],
        }
    const run = { stopped: false, abort: null, timer: null, runId: null }
    generationRef.current = run
    setBusy(true)
    setApproval(null)
    const instruction = `将以下已经由作者审阅的第 ${seq} 章演绎提案写入。只能调用一次 s3_generate_stage(stage=deduce, persist=true)。调用会请求作者审批。\n\n${JSON.stringify(payload)}`
    const request = api.runWrite(instruction, {
      chapter: seq, phase: 'deduce',
      context: snapshot ? {
        context_session_id: snapshot.session_id,
        context_revision: snapshot.revision,
        context_hash: snapshot.context_hash,
      } : null,
      onRun: (started) => { run.runId = started?.run_id || started?.id || run.runId },
      onApproval: (next) => {
        if (run.stopped) return
        run.runId = next?.run_id || run.runId
        setApproval({ ...next, run_id: run.runId, status: 'pending' })
      },
      onApprovalResolved: (resolved) => {
        if (!resolved?.run_id) return
        setApproval((current) => current?.run_id === resolved.run_id
          ? { ...current, ...resolved, status: resolved.decision === 'approve' ? 'approved' : 'denied' }
          : current)
      },
      onDone: () => {
        if (run.stopped) return
        clearTimeout(run.timer)
        if (generationRef.current === run) generationRef.current = null
        setBusy(false)
        setPreviewReady(false)
        onSaved?.()
        toast('演绎已按批准内容写入；请以章节回读内容为准。', { tone: 'ok' })
      },
      onError: (e) => {
        if (run.stopped) return
        clearTimeout(run.timer)
        if (generationRef.current === run) generationRef.current = null
        setBusy(false)
        toast('演绎提交失败:' + e, { tone: 'danger' })
      },
    })
    run.abort = () => request?.abort?.()
    run.timer = setTimeout(() => stopGeneration('演绎审批等待超过 6 分钟，未批准内容不会写入。'), GENERATE_TIMEOUT_MS)
  }

  const runParallelPlan = async (execute = false) => {
    setParallelBusy(true)
    setParallelResults(null)
    try {
      const focals = parallelFocals.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean)
      const body = {
        focalizers: focals.length ? focals : (chars.slice(0, 2).map((c) => c.name || c.id)),
        max_parallel: 2,
        mode: parallelMode === 'deduce' ? 'deduce' : 'preview',
        execute: !!execute,
      }
      const r = typeof api.parallelDeduce === 'function'
        ? await api.parallelDeduce(seq, body, work)
        : await api.post(`/chapters/${seq}/deduce/parallel`, body)
      if (execute) {
        setParallelResults(r)
        setParallelPlan(r?.plan || null)
        if (r?.all_stub || (r?.ok_count === 0 && (r?.results || []).length)) {
          toast('并行结束：无成功路（stub 不计成功）', { tone: 'warn' })
        } else {
          toast(`并行演绎结束 · ok ${r?.ok_count ?? 0}/${(r?.results || []).length}`, { tone: 'ok' })
        }
      } else {
        setParallelPlan(r)
        toast(`已生成 plan（${body.mode} · dry-run）`, { tone: 'ok' })
      }
    } catch (e) {
      toast(e?.body?.detail || e?.message || '并行演绎失败', { tone: 'danger' })
    } finally {
      setParallelBusy(false)
    }
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
      className="w-full max-w-[min(1120px,calc(100%-24px))] mx-auto px-4 py-2 h-full flex flex-col min-h-0"
    >
      <details
        className="mb-2 shrink-0 rounded-lg border border-line/60 bg-surface/50 px-3 py-1.5"
        data-testid="parallel-deduce-panel"
      >
        <summary className="cursor-pointer text-f12 font-medium text-ink">
          多视角并行演绎
          <span className="ml-2 font-normal text-faint">默认收起 · 确认执行才打 LLM</span>
        </summary>
        <div className="mt-2 space-y-2">
        <p className="text-f12 text-faint">
          preview（:8646 只读）与 deduce（:8645）并列；默认 dry-run；确认执行才打 LLM（限并发 · 章锁 · soft）。
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-line overflow-hidden text-f12" role="group" aria-label="并行模式">
            <button
              type="button"
              data-testid="parallel-mode-preview"
              className={`h-8 px-2 cursor-pointer ${parallelMode === 'preview' ? 'bg-brand/15 text-brand' : 'bg-canvas text-faint'}`}
              onClick={() => setParallelMode('preview')}
            >
              preview
            </button>
            <button
              type="button"
              data-testid="parallel-mode-deduce"
              className={`h-8 px-2 cursor-pointer border-l border-line ${parallelMode === 'deduce' ? 'bg-brand/15 text-brand' : 'bg-canvas text-faint'}`}
              onClick={() => setParallelMode('deduce')}
            >
              deduce
            </button>
          </div>
          <input
            className="h-8 min-w-[12rem] flex-1 rounded-lg border border-line bg-canvas px-2 text-f12"
            placeholder="视角名，逗号分隔（可空=角色前两名）"
            value={parallelFocals}
            onChange={(e) => setParallelFocals(e.target.value)}
            data-testid="parallel-deduce-focals"
          />
          <Btn size="sm" disabled={parallelBusy} onClick={() => runParallelPlan(false)} data-testid="parallel-deduce-plan">
            {parallelBusy ? '…' : '预览 plan'}
          </Btn>
          <Btn size="sm" variant="primary" disabled={parallelBusy} onClick={() => runParallelPlan(true)} data-testid="parallel-deduce-execute">
            确认执行
          </Btn>
        </div>
        {parallelPlan && (
          <pre className="text-f12 text-faint max-h-24 overflow-auto whitespace-pre-wrap" data-testid="parallel-deduce-plan-out">
            {JSON.stringify(parallelPlan.runs || parallelPlan, null, 0).slice(0, 800)}
          </pre>
        )}
        {parallelResults?.results && (
          <ul className="text-f12 space-y-1" data-testid="parallel-deduce-results">
            {parallelResults.results.map((r, i) => (
              <li key={i} className="border-b border-line/40 py-1">
                <strong>{r.focalizer || '_default'}</strong>
                <span className="text-faint"> · {r.status}</span>
                <div className="text-f12 text-faint truncate">{(r.summary || r.error || '').slice(0, 200)}</div>
              </li>
            ))}
          </ul>
        )}
        </div>
      </details>
      <div className="flex items-center gap-2 mb-2 flex-wrap shrink-0">
        <h3 className="text-f13 font-medium text-ink">{selected === 'truth' ? '场景真相 · 全知' : `${cur.character_name} · 限知投影`}</h3>
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
        <Btn variant="primary" size="sm" onClick={gen} disabled={busy || editingPreview}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}{busy ? '演绎中…' : '生成'}
        </Btn>
        <Btn variant="ghost" size="sm" onClick={beginPreviewEdit} disabled={busy || !preview.trim() || editingPreview}>
          编辑预览
        </Btn>
        <Btn variant="primary" size="sm" data-testid="deduce-submit-preview" onClick={submitPreview} disabled={!previewReady || busy || editingPreview}>
          提交演绎审批
        </Btn>
      </div>
      {approval && (
        <div data-testid="deduce-run-approval" className="mb-3 border-l-2 border-brand/50 bg-surface px-3 py-2">
          <div className="text-f12 font-medium text-ink">演绎 Run 请求审批</div>
          <div className="mt-1 text-f12 text-faint whitespace-pre-wrap">{approval.message || '需要你确认后才会写入章节演绎。'}</div>
          <div className="mt-2 flex items-center gap-2">
            {approval.status === 'pending' && <>
              <Btn variant="primary" size="sm" aria-label="批准演绎写入" onClick={() => resolveApproval('approve')}>批准</Btn>
              <Btn variant="ghost" size="sm" aria-label="拒绝演绎写入" onClick={() => resolveApproval('deny')}>拒绝</Btn>
            </>}
            {approval.status === 'submitting' && <span className="text-f12 text-faint">提交中…</span>}
            {approval.status === 'approved' && <span className="text-f12 text-ok">已批准，等待 Run 完成。</span>}
            {approval.status === 'denied' && <span className="text-f12 text-danger">已拒绝，未写入。</span>}
            {approval.status === 'error' && <span className="text-f12 text-danger">审批失败：{String(approval.error || '未知错误')}</span>}
          </div>
        </div>
      )}
      {editingPreview ? (
        <div className="flex-1 min-h-0 flex flex-col gap-2">
          <textarea
            aria-label="编辑预览"
            data-testid="deduce-preview-editor"
            value={previewDraft}
            onChange={(event) => setPreviewDraft(event.target.value)}
            className="flex-1 min-h-0 w-full resize-none rounded-md border border-line bg-canvas p-3 text-f13 leading-6 text-ink outline-none focus:border-brand"
          />
          <div className="flex justify-end gap-2">
            <Btn variant="ghost" size="sm" onClick={() => { setPreviewDraft(''); setEditingPreview(false); setPreviewReady(true) }} disabled={busy}>取消编辑</Btn>
            <Btn variant="primary" size="sm" onClick={finishPreviewEdit} disabled={busy}>完成预览编辑</Btn>
          </div>
        </div>
      ) : (
        <SelectionQuoteActions
          scopeLabel={selected === 'truth' ? `第 ${seq} 章场景真相` : `第 ${seq} 章「${targetName}」限知`}
          className="flex-1 min-h-0 overflow-y-auto type-stage whitespace-pre-wrap"
          data-testid="deduce-readonly"
          disabled={noProse}
        >
          <div aria-label={selected === 'truth' ? '场景真相' : '限知投影'}>
            {displayText.trim()
              ? displayText
              : <span className="text-faint">（空 · 点击「生成」后由受限 Run 请求审批写入）</span>}
          </div>
        </SelectionQuoteActions>
      )}
    </div>
  )
}

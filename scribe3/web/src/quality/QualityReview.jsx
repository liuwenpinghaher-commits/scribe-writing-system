import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, Gauge, Loader2, Quote } from 'lucide-react'
import { api } from '../api'
import { Btn, Card, Empty, SectionTitle, Tag } from '../ui.jsx'
import { AsyncState } from '../ui/AsyncState.jsx'

const STATE_LABEL = {
  evaluable: '可评价', insufficient: '证据不足', degraded: '降级',
  conflicted: '分歧', not_applicable: '不适用',
}
const STATE_TONE = {
  evaluable: 'ok', insufficient: 'faint', degraded: 'danger',
  conflicted: 'danger', not_applicable: 'faint',
}

function ScoreInput({ value, onChange, label, path }) {
  return (
    <input
      type="number" min="1" max="5" step="1"
      role="spinbutton"
      aria-label={label}
      data-field-path={path}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
      className="w-14 h-8 rounded-md border border-line bg-canvas px-2 text-f13 text-ink text-center outline-none transition-colors focus:border-brand"
    />
  )
}

function DimensionRow({ dim, chapter, authorDrafts, onAuthorDraft, onAuthorSubmit, submitting, submitError, onLocateEvidence }) {
  const sys = dim.system
  const ref = dim.reference
  const draft = authorDrafts[dim.dimension] || {}
  const author = draft.score ?? dim.author?.score ?? null
  const decision = draft.decision ?? dim.author?.decision ?? 'accept'
  const reason = draft.reason ?? dim.author?.reason ?? ''
  const counterEvidence = draft.counterEvidence ?? dim.author?.counter_evidence ?? []
  const threeAxesPresent = author != null && sys != null && ref != null
  const evidence = Array.isArray(sys?.evidence) ? sys.evidence : []
  const toggleCounterEvidence = (anchor) => {
    const exists = counterEvidence.some((item) => (
      item.chapter_version_id === anchor.chapter_version_id
      && item.start_utf16 === anchor.start_utf16
      && item.end_utf16 === anchor.end_utf16
    ))
    onAuthorDraft(dim.dimension, {
      counterEvidence: exists
        ? counterEvidence.filter((item) => !(item.chapter_version_id === anchor.chapter_version_id
          && item.start_utf16 === anchor.start_utf16 && item.end_utf16 === anchor.end_utf16))
        : [...counterEvidence, anchor],
    })
  }
  return (
    <div className="rounded-lg border border-line bg-canvas p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-f14 font-semibold text-ink">{dim.dimension}</span>
        <Tag tone={STATE_TONE[dim.state] || 'faint'}>{STATE_LABEL[dim.state] || dim.state}</Tag>
        {dim.conflicted && <Tag tone="danger"><AlertTriangle size={10} className="mr-0.5 inline" />分歧</Tag>}
        {sys && <span className="text-meta text-faint">系统 <b className="text-ink tnum">{sys.score}</b></span>}
        {ref && <span className="text-meta text-faint">参考 <b className="text-ink tnum">{ref.score}</b></span>}
        {author != null && <span className="text-meta text-faint">作者 <b className="text-ink tnum">{author}</b></span>}
        {threeAxesPresent && dim.decision_index != null && (
          <span className="ml-auto inline-flex items-center gap-1 text-meta text-brand" data-field-path={`dimension.${dim.dimension}.decision_index`}>
            <Gauge size={11} />决策指数 <b className="tnum">{Number(dim.decision_index).toFixed(1)}</b>
          </span>
        )}
      </div>
        {sys?.mechanism && <div className="text-meta text-muted" data-field-path={`dimension.${dim.dimension}.mechanism`}>{sys.mechanism}</div>}
      {evidence.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {evidence.map((ev, i) => (
            <button
              key={i}
              onClick={() => onLocateEvidence?.({ chapter, quote: ev.quote, start_utf16: ev.start_utf16, end_utf16: ev.end_utf16 })}
              className="inline-flex items-center gap-1 rounded border border-line bg-soft px-1.5 py-0.5 text-meta text-faint transition-colors hover:text-ink hover:border-faint/50 cursor-pointer"
              title="点击定位证据"
            >
              <Quote size={10} />{ev.quote}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 pt-0.5">
        <span className="text-meta text-faint">作者评分</span>
        <ScoreInput
          value={author}
          label={`${dim.dimension} 作者评分`}
          path={`dimension.${dim.dimension}.author_score`}
          onChange={(v) => onAuthorDraft(dim.dimension, { score: v })}
        />
        <span className="text-meta text-faint/60">1–5</span>
      </div>
      <div className="grid gap-2 pt-1">
        <label className="text-meta text-faint">
          作者裁决
          <select
            aria-label={`${dim.dimension} 作者裁决`}
            data-field-path={`dimension.${dim.dimension}.author_decision`}
            value={decision}
            onChange={(e) => onAuthorDraft(dim.dimension, { decision: e.target.value })}
            className="ml-2 h-7 rounded border border-line bg-canvas px-2 text-f12 text-ink outline-none"
          >
            <option value="accept">采纳</option>
            <option value="revise">修订</option>
            <option value="reject">拒绝</option>
          </select>
        </label>
        <textarea
          aria-label={`${dim.dimension} 裁决理由`}
          data-field-path={`dimension.${dim.dimension}.author_reason`}
          value={reason}
          onChange={(e) => onAuthorDraft(dim.dimension, { reason: e.target.value })}
          placeholder="说明为何采纳、要求修订或拒绝这项判断…"
          className="min-h-16 w-full resize-y rounded-md border border-line bg-canvas px-2 py-1.5 text-f13 text-ink outline-none focus:border-brand"
        />
        {evidence.length > 0 && (
          <div className="flex flex-wrap gap-2 text-meta text-faint">
            {evidence.map((anchor, index) => {
              const selected = counterEvidence.some((item) => (
                item.chapter_version_id === anchor.chapter_version_id
                && item.start_utf16 === anchor.start_utf16 && item.end_utf16 === anchor.end_utf16
              ))
              return (
                <label key={`${anchor.start_utf16}-${index}`} className="inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggleCounterEvidence(anchor)}
                    aria-label={`${dim.dimension} 反证 ${anchor.quote}`}
                  />
                  作为反证：{anchor.quote}
                </label>
              )
            })}
          </div>
        )}
        <div className="flex items-center gap-2">
          <Btn
            size="sm"
            onClick={() => onAuthorSubmit(dim, { score: author, decision, reason, counterEvidence })}
            disabled={submitting || author == null || !reason.trim() || evidence.length === 0}
          >
            {submitting ? '保存裁决中…' : '提交裁决'}
          </Btn>
          <span className="text-meta text-faint/70">裁决会追加留痕；不会覆盖历史决定。</span>
        </div>
        {submitError && <div role="alert" className="text-meta text-danger">{submitError}</div>}
      </div>
    </div>
  )
}

export function QualityReview({ work, seq, onLocateEvidence }) {
  const [evaluation, setEvaluation] = useState(null)
  const [state, setState] = useState('idle')
  const [authorDrafts, setAuthorDrafts] = useState({})
  const [submittingDimension, setSubmittingDimension] = useState(null)
  const [submitErrors, setSubmitErrors] = useState({})
  const [chapterInput, setChapterInput] = useState(seq == null ? '' : String(seq))
  const [contractId, setContractId] = useState('')
  const [contractRevision, setContractRevision] = useState(1)
  const [selectedFingerprintIds, setSelectedFingerprintIds] = useState([])
  const [approvedFingerprints, setApprovedFingerprints] = useState([])
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState('')
  // 创建/重试会切换到新的冻结 job；旧请求晚返回时不得覆盖新 job 的空壳状态。
  const evaluationEpoch = useRef(0)

  useEffect(() => {
    let live = true
    api.approvedReferenceFingerprints(work)
      .then((rows) => { if (live) setApprovedFingerprints(Array.isArray(rows) ? rows : []) })
      .catch(() => { if (live) setApprovedFingerprints([]) })
    return () => { live = false }
  }, [work])

  const activeSeq = Number.isInteger(Number(chapterInput)) && Number(chapterInput) > 0
    ? Number(chapterInput) : null

  const load = useCallback((background = false) => {
    const requestEpoch = evaluationEpoch.current
    if (activeSeq == null) {
      setEvaluation(null)
      setState('idle')
      return
    }
    if (!background) setState('loading')
    api.qualityEvaluation(activeSeq, work)
      .then((ev) => {
        if (requestEpoch !== evaluationEpoch.current) return
        setEvaluation(ev)
        setState(ev?.status || 'ready')
        if (ev?.status !== 'queued' && ev?.status !== 'running') setRetrying(false)
      })
      .catch(() => {
        if (requestEpoch === evaluationEpoch.current) setState('error')
      })
  }, [activeSeq, work])

  useEffect(() => {
    evaluationEpoch.current += 1
    load()
  }, [load])

  useEffect(() => {
    if (state !== 'queued' && state !== 'running') return undefined
    const timer = window.setInterval(() => load(true), 1_000)
    return () => window.clearInterval(timer)
  }, [state, load])

  useEffect(() => {
    if (seq != null) setChapterInput(String(seq))
  }, [seq])

  const updateAuthorDraft = (dimension, patch) => {
    setAuthorDrafts((prev) => ({
      ...prev,
      [dimension]: { ...prev[dimension], ...patch },
    }))
  }

  const submitAuthorVerdict = async (dim, draft) => {
    if (activeSeq == null || draft.score == null || !draft.reason.trim() || !dim.system?.evidence?.length) return
    setSubmittingDimension(dim.dimension)
    setSubmitErrors((previous) => ({ ...previous, [dim.dimension]: '' }))
    try {
      await api.qualityAuthorJudgment({
        work,
        seq: activeSeq,
        dimension: dim.dimension,
        score: draft.score,
        decision: draft.decision,
        reason: draft.reason.trim(),
        evidence: dim.system.evidence,
        counter_evidence: draft.counterEvidence,
      })
      setAuthorDrafts((prev) => {
        const next = { ...prev }
        delete next[dim.dimension]
        return next
      })
      load()
    } catch {
      // 失败时保留作者输入，便于修订后重试；不假装保存成功。
      setSubmitErrors((previous) => ({
        ...previous,
        [dim.dimension]: '裁决保存失败，请检查理由和正文证据后重试。',
      }))
    } finally {
      setSubmittingDimension(null)
    }
  }

  const createEvaluation = async () => {
    if (activeSeq == null || !contractId.trim() || creating) return
    evaluationEpoch.current += 1
    setCreating(true)
    setCreateError('')
    try {
      const reference_fingerprint_ids = [...new Set(selectedFingerprintIds.filter(Boolean))]
      const created = await api.qualityCreateSnapshot({
        work,
        seq: activeSeq,
        contract_id: contractId.trim(),
        contract_revision: Number(contractRevision) || 1,
        reference_fingerprint_ids,
      })
      setEvaluation({ chapter: activeSeq, dimensions: [], ...created })
      setAuthorDrafts({})
      setState(created?.status || 'queued')
    } catch (err) {
      // 只向作者展示后端对 4xx 明确给出的业务校验原因；网络/500 等不可
      // 信任的上游错误仍使用通用文案，避免把请求体、认证信息或异常栈带到界面。
      const detail = typeof err?.body?.detail === 'string' ? err.body.detail.trim() : ''
      const clientError = Number.isInteger(err?.status) && err.status >= 400 && err.status < 500
      setCreateError(clientError && detail
        ? `创建评价失败：${detail.slice(0, 300)}`
        : '创建评价失败。请确认章节已有冻结版本、合同已批准，且参考指纹已批准。')
    } finally {
      setCreating(false)
    }
  }

  const retryEvaluation = async () => {
    const jobId = evaluation?.job_id
    if (!jobId || retrying) return
    evaluationEpoch.current += 1
    setRetrying(true)
    setRetryError('')
    try {
      const scheduled = await api.qualityRetryJob(jobId, work)
      setEvaluation((previous) => ({ ...previous, ...scheduled, chapter: activeSeq, dimensions: [] }))
      setState(scheduled?.status || 'queued')
    } catch {
      setRetryError('重试未能提交。请稍后重试；本次冻结正文和原有证据不会被覆盖。')
      setRetrying(false)
    }
  }

  const starter = (
    <Card className="space-y-3" data-testid="quality-evaluation-starter">
      <div>
        <div className="text-f14 font-semibold text-ink">创建章节评价</div>
        <div className="mt-1 text-meta text-faint">评价会冻结当前章节版本，并以已批准的合同和参考技法执行十维判断。</div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="text-meta text-faint">章节号
          <input aria-label="章节号" type="number" min="1" value={chapterInput}
            onChange={(e) => setChapterInput(e.target.value)}
            className="mt-1 h-8 w-full rounded border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand" />
        </label>
        <label className="text-meta text-faint">质量合同 ID
          <input aria-label="质量合同 ID" value={contractId}
            onChange={(e) => setContractId(e.target.value)} placeholder="先在“质量合同”保存并批准"
            className="mt-1 h-8 w-full rounded border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand" />
        </label>
        <label className="text-meta text-faint">合同修订
          <input aria-label="合同修订" type="number" min="1" value={contractRevision}
            onChange={(e) => setContractRevision(e.target.value)}
            className="mt-1 h-8 w-full rounded border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand" />
        </label>
        <div className="sm:col-span-2 space-y-1.5">
          <div className="text-meta text-faint">已批准技法标尺（从库选择，非手填 ID）</div>
          {approvedFingerprints.length === 0 && (
            <div className="text-meta text-faint" data-testid="quality-no-approved-fps">
              暂无已批准指纹。请先在「技法标尺」导入、生成并批准。
            </div>
          )}
          <div className="flex flex-col gap-1.5" data-testid="quality-fingerprint-picker" role="group" aria-label="已批准参考指纹">
            {approvedFingerprints.map((fp) => {
              const checked = selectedFingerprintIds.includes(fp.fingerprint_id)
              return (
                <label key={fp.fingerprint_id} className="inline-flex items-start gap-2 text-f13 text-ink">
                  <input
                    type="checkbox"
                    aria-label={`选择标尺 ${fp.title || fp.fingerprint_id}`}
                    checked={checked}
                    onChange={() => setSelectedFingerprintIds((prev) => (
                      checked
                        ? prev.filter((id) => id !== fp.fingerprint_id)
                        : [...prev, fp.fingerprint_id]
                    ))}
                  />
                  <span>
                    <span className="font-medium">{fp.title || '未命名标尺'}</span>
                    <span className="text-meta text-faint"> · 版本 {fp.revision}</span>
                    {fp.full_book_fingerprint && (
                      <span className="block text-meta text-faint">{fp.full_book_fingerprint}</span>
                    )}
                  </span>
                </label>
              )
            })}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Btn size="sm" onClick={createEvaluation} disabled={activeSeq == null || !contractId.trim() || creating}>
          {creating ? '创建评价中…' : '创建章节评价'}
        </Btn>
        {activeSeq == null && <span className="text-meta text-faint">先选择章节，再创建快照。</span>}
      </div>
      {createError && <div role="alert" className="text-meta text-danger">{createError}</div>}
    </Card>
  )

  if (state === 'loading') {
    return <div className="h-full overflow-y-auto"><div className="max-w-2xl mx-auto px-6 py-5 space-y-4">{starter}<div className="flex items-center gap-2 text-faint"><Loader2 size={16} className="animate-spin" />加载质量评价…</div></div></div>
  }
  if (state === 'error') {
    return <div className="h-full overflow-y-auto"><div className="max-w-2xl mx-auto px-6 py-5 space-y-4">{starter}<AsyncState state="error" title="质量评价加载失败" onRetry={load} /></div></div>
  }
  const jobStatus = evaluation?.status || state
  const isRunning = jobStatus === 'queued' || jobStatus === 'running'
  const isRetryableFailure = jobStatus === 'retryable_failed'
  const isPermanentFailure = jobStatus === 'failed'
  const hasEvaluation = jobStatus === 'ready'
    && Array.isArray(evaluation?.dimensions) && evaluation.dimensions.length > 0
  const chapter = evaluation?.chapter ?? activeSeq
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 space-y-4">
        <SectionTitle icon={Gauge} right={chapter == null ? '未选择章节' : `第 ${chapter} 章${hasEvaluation ? ` · ${evaluation.dimensions.length} 维` : ''}`}>质量审阅</SectionTitle>
        {starter}
        {isRunning && <Card className="flex items-center gap-2 text-faint" data-testid="quality-job-running">
          <Loader2 size={16} className="animate-spin" />正在执行质量判断，完成后会自动显示十维证据与作者裁决。
        </Card>}
        {isRetryableFailure && <Card className="space-y-2" data-testid="quality-job-retryable-failed">
          <div className="text-f13 text-ink">本次冻结评价未完成</div>
          <div className="text-meta text-faint">{evaluation?.error_message || '质量作业可安全重试；未写入任何半成品评价。'}</div>
          <div className="flex items-center gap-2">
            <Btn size="sm" onClick={retryEvaluation} disabled={retrying}>{retrying ? '正在提交重试…' : '重试本次冻结评价'}</Btn>
            {retryError && <span role="alert" className="text-meta text-danger">{retryError}</span>}
          </div>
        </Card>}
        {isPermanentFailure && <Card className="space-y-1" data-testid="quality-job-failed">
          <div className="text-f13 text-danger">质量作业失败</div>
          <div className="text-meta text-faint">{evaluation?.error_message || '请检查合同与冻结内容后新建评价。'}</div>
        </Card>}
        {!hasEvaluation && !isRunning && !isRetryableFailure && !isPermanentFailure && <Empty>{activeSeq == null ? '先选择章节，再创建快照并启动评价。' : '暂无质量评价。填写合同后即可创建章节评价。'}</Empty>}
        {hasEvaluation && <div className="space-y-3">
          {evaluation.dimensions.map((dim) => (
            <DimensionRow
              key={dim.dimension}
              dim={dim}
              chapter={chapter}
              authorDrafts={authorDrafts}
              onAuthorDraft={updateAuthorDraft}
              onAuthorSubmit={submitAuthorVerdict}
              submitting={submittingDimension === dim.dimension}
              submitError={submitErrors[dim.dimension]}
              onLocateEvidence={onLocateEvidence}
            />
          ))}
        </div>}
        {hasEvaluation && <div className="text-meta text-faint/70 pb-4">维度指数仅用于同一维度内排序,不跨维度求和。</div>}
      </div>
    </div>
  )
}

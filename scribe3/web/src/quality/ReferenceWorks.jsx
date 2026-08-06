import { useCallback, useEffect, useRef, useState } from 'react'
import { Archive, Check, Fingerprint, Loader2, Plus, Upload } from 'lucide-react'
import { api } from '../api'
import { Btn, Card, Empty, Input, SectionTitle, Tag, Textarea } from '../ui.jsx'
import { AsyncState } from '../ui/AsyncState.jsx'

const STATUS_LABEL = { imported: '已导入', pending_review: '待审', approved: '已批准' }
const STATUS_TONE = { imported: 'faint', pending_review: 'brand', approved: 'ok' }

function FingerprintCard({ fp, work, onApproved, canApprove }) {
  const [approving, setApproving] = useState(false)
  const [corrections, setCorrections] = useState(() => JSON.stringify(fp.fingerprint || {}, null, 2))
  const [error, setError] = useState('')
  const approve = async () => {
    let parsed
    try {
      parsed = JSON.parse(corrections)
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('校订内容必须是 JSON 对象')
    } catch (err) {
      setError(err?.message || '指纹校订不是有效 JSON')
      return
    }
    setApproving(true)
    setError('')
    try {
      await api.referenceApproveFingerprint(fp.reference_work_id, fp.fingerprint_id, { work, corrections: parsed })
      onApproved?.()
    } catch (err) {
      setError(err?.message || '指纹批准失败')
    } finally {
      setApproving(false)
    }
  }
  const data = fp.fingerprint || {}
  const meta = data.analysis_meta || {}
  return (
    <div className="rounded-lg border border-line bg-canvas p-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <Fingerprint size={13} className="text-faint shrink-0" />
        <span className="text-f13 font-medium text-ink" data-field-path="fingerprint.full_book">{data.full_book_fingerprint || '—'}</span>
        <Tag tone={STATUS_TONE[fp.status] || 'faint'}>{STATUS_LABEL[fp.status] || fp.status}</Tag>
        <span className="ml-auto text-meta text-faint tnum">rev {fp.revision}</span>
      </div>
      {meta.segment_count != null && (
        <div className="text-meta text-faint" data-field-path="fingerprint.analysis_meta">
          分层分析：{meta.segment_count} 段 · {meta.chars_analyzed ?? '—'} 字 · {meta.pipeline || 'map_reduce'}
        </div>
      )}
      {data.applicable_scope && <div className="text-meta text-muted" data-field-path="fingerprint.scope">适用:{data.applicable_scope}</div>}
      {Array.isArray(data.transferable_mechanisms) && data.transferable_mechanisms.length > 0 && (
        <div className="text-meta text-faint" data-field-path="fingerprint.transferable">可迁移:{data.transferable_mechanisms.join('、')}</div>
      )}
      {canApprove && (
        <div className="pt-1 space-y-2">
          <label className="grid gap-1 text-meta text-faint">
            <span>指纹校订</span>
            <Textarea
              variant="bordered"
              aria-label="指纹校订"
              data-field-path="fingerprint.corrections"
              value={corrections}
              onChange={(event) => setCorrections(event.target.value)}
              rows={6}
            />
          </label>
          {error && <div role="alert" className="text-meta text-danger">{error}</div>}
          <Btn variant="soft" size="xs" onClick={approve} disabled={approving} aria-label="批准指纹">
            {approving ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}批准
          </Btn>
        </div>
      )}
    </div>
  )
}

function ReferenceCard({ reference: r, work, onChanged }) {
  const [fingerprints, setFingerprints] = useState(null)
  const [err, setErr] = useState('')
  const [generating, setGenerating] = useState(false)
  const [fpStage, setFpStage] = useState('')
  const load = useCallback(() => {
    setErr('')
    api.referenceFingerprints(r.reference_work_id)
      .then(setFingerprints)
      .catch((e) => setErr(e?.message || '指纹加载失败'))
  }, [r.reference_work_id])
  useEffect(() => { load() }, [load])

  const latestApprovedRevision = fingerprints
    ? Math.max(-1, ...fingerprints
      .filter((fp) => fp.status === 'approved')
      .map((fp) => Number(fp.revision) || 0))
    : -1

  const pollFingerprintJob = async (jobId) => {
    for (let i = 0; i < 900; i += 1) {
      const job = await api.referenceFingerprintJob(jobId, work)
      setFpStage(job.stage || '')
      if (job.done) {
        if (job.error) throw new Error(job.error)
        return job
      }
      await new Promise((resolve) => setTimeout(resolve, 500))
    }
    throw new Error('指纹分析超时')
  }

  const generate = async () => {
    setGenerating(true)
    setErr('')
    setFpStage('排队中…')
    try {
      const started = await api.referenceGenerateFingerprint(r.reference_work_id, { work })
      if (started?.job_id) {
        await pollFingerprintJob(started.job_id)
      }
      load()
      onChanged?.()
      setFpStage('')
    } catch (e) {
      const detail = typeof e?.body?.detail === 'string' ? e.body.detail : ''
      setErr(detail || e?.message || '指纹生成失败')
      setFpStage('')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Card className="p-3.5 space-y-2.5" data-testid={`reference-card-${r.reference_work_id}`}>
      <div className="flex items-center gap-2">
        <Archive size={14} className="text-faint shrink-0" />
        <span className="text-f14 font-semibold text-ink" data-field-path="reference.title">{r.title}</span>
        <Tag tone={STATUS_TONE[r.status] || 'faint'}>{STATUS_LABEL[r.status] || r.status}</Tag>
      </div>
      {err && <div role="alert" className="text-meta text-danger">{err}</div>}
      {fpStage && <div className="text-meta text-muted" data-testid="fingerprint-job-stage">{fpStage}</div>}
      {fingerprints && fingerprints.length > 0 && (
        <div className="space-y-2">
          {fingerprints.map((fp) => (
            <FingerprintCard
              key={fp.fingerprint_id + ':' + fp.revision}
              fp={fp}
              work={work}
              canApprove={fp.status !== 'approved' && (Number(fp.revision) || 0) > latestApprovedRevision}
              onApproved={() => { load(); onChanged?.() }}
            />
          ))}
        </div>
      )}
      {fingerprints && fingerprints.length === 0 && (
        <div className="flex items-center gap-2">
          <Empty>尚无指纹。先分析这部作品的可迁移技法，再由作者批准。</Empty>
          <Btn variant="soft" size="xs" onClick={generate} disabled={generating} aria-label="生成指纹">
            {generating ? <Loader2 size={12} className="animate-spin" /> : <Fingerprint size={12} />}
            {generating ? '分析中…' : '生成指纹'}
          </Btn>
        </div>
      )}
      {fingerprints && fingerprints.length > 0 && (
        <Btn variant="ghost" size="xs" onClick={generate} disabled={generating} aria-label="重新生成指纹">
          {generating ? <Loader2 size={12} className="animate-spin" /> : <Fingerprint size={12} />}
          {generating ? '分析中…' : '再分析'}
        </Btn>
      )}
    </Card>
  )
}

export function ReferenceWorks({ work, initialReferences = null }) {
  const [refs, setRefs] = useState(initialReferences)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importStage, setImportStage] = useState('')
  const [importErr, setImportErr] = useState('')
  const titleRef = useRef(null)
  const fileRef = useRef(null)

  const reload = useCallback(() => {
    api.referenceWorks()
      .then(setRefs)
      .catch((e) => {
        setImportErr(e?.message || '参考作品加载失败')
        setRefs([])
      })
  }, [])

  useEffect(() => {
    let active = true
    if (initialReferences !== null) {
      setRefs(initialReferences)
      return () => { active = false }
    }
    setRefs(null)
    api.referenceWorks()
      .then((records) => { if (active) setRefs(records) })
      .catch((e) => {
        if (!active) return
        setImportErr(e?.message || '参考作品加载失败')
        setRefs([])
      })
    return () => { active = false }
  }, [work, initialReferences])

  const pollJob = async (jobId) => {
    for (let i = 0; i < 600; i += 1) {
      const job = await api.referenceImportJob(jobId, work)
      setImportStage(job.stage || '')
      if (job.done) {
        if (job.error) throw new Error(job.error)
        return job
      }
      await new Promise((r) => setTimeout(r, 400))
    }
    throw new Error('导入超时')
  }

  const doImport = async () => {
    if (!title.trim()) return
    if (!file && !text.trim()) return
    setImporting(true)
    setImportErr('')
    setImportStage('')
    try {
      if (file) {
        const createdJob = await api.referenceImportFile({ work, title: title.trim(), file })
        const job = await pollJob(createdJob.job_id)
        setTitle('')
        setText('')
        setFile(null)
        if (fileRef.current) fileRef.current.value = ''
        if (initialReferences !== null) {
          // 受控列表场景：拉真实列表合并
          reload()
        } else {
          reload()
        }
        if (job.reference_work_id) {
          setImportStage(`已导入 ${job.title || title}`)
        }
      } else {
        const created = await api.referenceImport({ work, title: title.trim(), text })
        setRefs((prev) => [...(prev || []), created])
        setTitle('')
        setText('')
      }
    } catch (e) {
      const detail = typeof e?.body?.detail === 'string' ? e.body.detail : ''
      setImportErr(detail || e?.message || '导入失败')
    } finally {
      setImporting(false)
    }
  }

  const canImport = Boolean(title.trim() && (file || text.trim()))

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 space-y-5">
        <div>
          <SectionTitle icon={Plus} right="技法标尺">导入参考标尺</SectionTitle>
          <p className="text-meta text-faint mb-2.5">
            整书请上传文件（txt/md/docx/pdf 等）；粘贴仅适合短样。标尺与「素材库」分离：此处用于质量评价与已批准技法注入，不进素材召回。
          </p>
          <div className="space-y-2.5">
            <label className="block">
              <span className="block text-helper font-medium text-ink mb-1">标题</span>
              <Input variant="bordered" ref={titleRef} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="作品名…" aria-label="参考作品标题" data-field-path="reference.title" />
            </label>
            <label className="block">
              <span className="block text-helper font-medium text-ink mb-1">文件上传（推荐）</span>
              <input
                ref={fileRef}
                type="file"
                accept=".txt,.md,.markdown,.docx,.pdf,.epub,.html,.htm"
                aria-label="参考作品文件"
                data-testid="reference-file-input"
                className="block w-full text-f13 text-ink file:mr-3 file:rounded file:border-0 file:bg-brand/10 file:px-3 file:py-1.5 file:text-f13 file:text-brand"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="block">
              <span className="block text-helper font-medium text-ink mb-1">短样粘贴（次要）</span>
              <Textarea variant="bordered" value={text} onChange={(e) => setText(e.target.value)} placeholder="仅短样粘贴；整书请用文件上传…" aria-label="参考作品正文" rows={3} data-field-path="reference.text" disabled={Boolean(file)} />
            </label>
            {importStage && <div className="text-meta text-muted" data-testid="reference-import-stage">{importStage}</div>}
            {importErr && <div role="alert" className="text-meta text-danger">{importErr}</div>}
            <Btn variant="primary" onClick={doImport} disabled={importing || !canImport}>
              {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
              {importing ? '导入中…' : '导入标尺'}
            </Btn>
          </div>
        </div>

        <div>
          <SectionTitle icon={Archive} right={refs ? `${refs.length} 部` : null}>技法标尺</SectionTitle>
          {refs === null && <Empty>加载中…</Empty>}
          {refs !== null && refs.length === 0 && <Empty>还没有参考标尺。上传一部喜欢的作品，生成并批准指纹后用于质量评价与写稿技法。</Empty>}
          {refs && refs.length > 0 && (
            <div className="space-y-3">
              {refs.map((r) => <ReferenceCard key={r.reference_work_id} reference={r} work={work} onChanged={reload} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

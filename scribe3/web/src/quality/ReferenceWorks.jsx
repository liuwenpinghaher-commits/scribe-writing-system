import { useCallback, useEffect, useRef, useState } from 'react'
import { Archive, Check, Fingerprint, Loader2, Plus } from 'lucide-react'
import { api } from '../api'
import { Btn, Card, Empty, Input, Row, SectionTitle, Tag, Textarea } from '../ui.jsx'
import { AsyncState } from '../ui/AsyncState.jsx'

const STATUS_LABEL = { imported: '已导入', pending_review: '待审', approved: '已批准' }
const STATUS_TONE = { imported: 'faint', pending_review: 'brand', approved: 'ok' }

function FingerprintCard({ fp, work, onApproved }) {
  const [approving, setApproving] = useState(false)
  const approve = async () => {
    setApproving(true)
    try {
      await api.referenceApproveFingerprint(fp.reference_work_id, { work, fingerprint_id: fp.fingerprint_id })
      onApproved?.()
    } finally {
      setApproving(false)
    }
  }
  const data = fp.fingerprint || {}
  return (
    <div className="rounded-lg border border-line bg-canvas p-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <Fingerprint size={13} className="text-faint shrink-0" />
        <span className="text-f13 font-medium text-ink" data-field-path="fingerprint.full_book">{data.full_book_fingerprint || '—'}</span>
        <Tag tone={STATUS_TONE[fp.status] || 'faint'}>{STATUS_LABEL[fp.status] || fp.status}</Tag>
        <span className="ml-auto text-meta text-faint tnum">rev {fp.revision}</span>
      </div>
      {data.applicable_scope && <div className="text-meta text-muted" data-field-path="fingerprint.scope">适用:{data.applicable_scope}</div>}
      {Array.isArray(data.transferable_mechanisms) && data.transferable_mechanisms.length > 0 && (
        <div className="text-meta text-faint" data-field-path="fingerprint.transferable">可迁移:{data.transferable_mechanisms.join('、')}</div>
      )}
      {fp.status !== 'approved' && (
        <div className="pt-1">
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
  const load = useCallback(() => {
    setErr('')
    api.referenceFingerprints(r.reference_work_id)
      .then(setFingerprints)
      .catch((e) => setErr(e?.message || '指纹加载失败'))
  }, [r.reference_work_id])
  useEffect(() => { load() }, [load])

  return (
    <Card className="p-3.5 space-y-2.5">
      <div className="flex items-center gap-2">
        <Archive size={14} className="text-faint shrink-0" />
        <span className="text-f14 font-semibold text-ink" data-field-path="reference.title">{r.title}</span>
        <Tag tone={STATUS_TONE[r.status] || 'faint'}>{STATUS_LABEL[r.status] || r.status}</Tag>
      </div>
      {err && <div role="alert" className="text-meta text-danger">{err}</div>}
      {fingerprints && fingerprints.length > 0 && (
        <div className="space-y-2">
          {fingerprints.map((fp) => (
            <FingerprintCard key={fp.fingerprint_id + ':' + fp.revision} fp={fp} work={work} onApproved={() => { load(); onChanged?.() }} />
          ))}
        </div>
      )}
      {fingerprints && fingerprints.length === 0 && <Empty>尚无指纹,可在评价时生成。</Empty>}
    </Card>
  )
}

export function ReferenceWorks({ work, initialReferences = null }) {
  const [refs, setRefs] = useState(initialReferences)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [importing, setImporting] = useState(false)
  const [importErr, setImportErr] = useState('')
  const titleRef = useRef(null)

  const doImport = async () => {
    if (!title.trim() || !text.trim()) return
    setImporting(true)
    setImportErr('')
    try {
      const created = await api.referenceImport({ work, title: title.trim(), text })
      setRefs((prev) => [...(prev || []), created])
      setTitle('')
      setText('')
    } catch (e) {
      setImportErr(e?.message || '导入失败')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 space-y-5">
        <div>
          <SectionTitle icon={Plus} right="参考空间">导入喜欢的作品</SectionTitle>
          <div className="space-y-2.5">
            <label className="block">
              <span className="block text-helper font-medium text-ink mb-1">标题</span>
              <Input ref={titleRef} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="作品名…" aria-label="参考作品标题" data-field-path="reference.title" />
            </label>
            <label className="block">
              <span className="block text-helper font-medium text-ink mb-1">正文</span>
              <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="粘贴参考文本…" aria-label="参考作品正文" rows={4} data-field-path="reference.text" />
            </label>
            {importErr && <div role="alert" className="text-meta text-danger">{importErr}</div>}
            <Btn variant="primary" onClick={doImport} disabled={importing || !title.trim() || !text.trim()}>
              {importing && <Loader2 size={14} className="animate-spin" />}导入
            </Btn>
          </div>
        </div>

        <div>
          <SectionTitle icon={Archive} right={refs ? `${refs.length} 部` : null}>参考作品</SectionTitle>
          {refs === null && <Empty>加载中…</Empty>}
          {refs !== null && refs.length === 0 && <Empty>还没有参考作品。导入一部喜欢的作品,供质量评价参照。</Empty>}
          {refs && refs.length > 0 && (
            <div className="space-y-3">
              {refs.map((r) => <ReferenceCard key={r.reference_work_id} reference={r} work={work} onChanged={() => {}} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

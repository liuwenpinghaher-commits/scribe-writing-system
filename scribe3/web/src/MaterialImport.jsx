import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowLeft, ClipboardType, Link2, Loader2, Trash2, Upload } from 'lucide-react'
import { api } from './api'
import { MATERIAL_KINDS } from './materialKinds'
import { Btn, Input, Textarea } from './ui.jsx'
import { useToast } from './ui/Toast'

// 素材导入(素材库=主编联想记忆 · 导入界面):三来源(文件/粘贴文本/网址)→ 后端异步解析
// → SSE 进度 → 可编辑预览 → 确认落库。每步 fail-soft(try/catch + toast),不打断整体流程。
const KIND_LABEL = Object.fromEntries(MATERIAL_KINDS.map((k) => [k.key, k.label]))
const fallbackKind = (k) => (KIND_LABEL[k] ? k : (MATERIAL_KINDS[0]?.key || 'note'))

const SOURCES = [
  { key: 'file', label: '文件', icon: Upload },
  { key: 'text', label: '粘贴文本', icon: ClipboardType },
  { key: 'url', label: '网址', icon: Link2 },
]
const ACCEPT = '.txt,.md,.markdown,.pdf,.docx'
// 后端进度 stage 落到这些词即视为终态(与 done>=total 双保险)
const TERMINAL = /^(done|complete|completed|finished|success|完成|已完成)$/i

export function MaterialImport({ onImported, onCancel }) {
  const toast = useToast()
  const [tab, setTab] = useState('file')
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [dragOver, setDragOver] = useState(false)

  // phase: 'input'(选来源) | 'running'(解析中/含错误态) | 'preview'(可编辑预览)
  const [phase, setPhase] = useState('input')
  const [jobId, setJobId] = useState(null)
  const [prog, setProg] = useState(null)     // { stage, done, total }
  const [items, setItems] = useState([])     // 预览列表(每条可改 title/kind、删除)
  const [err, setErr] = useState(null)       // running 阶段的软错误
  const [submitting, setSubmitting] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [commitResult, setCommitResult] = useState(null)

  const esRef = useRef(null)          // 当前 EventSource
  const settledRef = useRef(false)    // 完成/失败只结算一次
  const gotMsgRef = useRef(false)     // 是否收到过进度事件(区分「流正常收尾」与「压根没连上」)
  const keyRef = useRef(0)            // 预览条稳定 key
  const fileInputRef = useRef(null)

  // 卸载兜底:关闭 SSE,避免泄漏连接 / setState-after-unmount
  useEffect(() => () => { try { esRef.current?.close() } catch { /* */ } }, [])

  const closeES = () => { try { esRef.current?.close() } catch { /* */ } esRef.current = null }

  const resetToInput = () => {
    closeES()
    settledRef.current = false
    gotMsgRef.current = false
    setPhase('input'); setJobId(null); setProg(null); setItems([]); setErr(null); setCommitResult(null)
  }

  // —— 选文件(拖拽 / 点击) ——
  const pickFiles = (list) => {
    const f = list && list[0]
    if (f) { setFile(f); setErr(null) }
  }
  const onDrop = (e) => { e.preventDefault(); setDragOver(false); pickFiles(e.dataTransfer?.files) }

  // —— 提交:构造 FormData(file/text/url/source)→ materialImport → 拿 job_id → 开 SSE ——
  const submit = async () => {
    if (tab === 'file' && !file) { toast('请选择要导入的文件', { tone: 'danger' }); return }
    if (tab === 'text' && !text.trim()) { toast('请粘贴要导入的文本', { tone: 'danger' }); return }
    if (tab === 'url' && !url.trim()) { toast('请输入网址', { tone: 'danger' }); return }

    const fd = new FormData()
    if (tab === 'file') { fd.append('file', file); fd.append('source', file.name) }
    else if (tab === 'text') { fd.append('text', text); fd.append('source', '粘贴文本') }
    else if (tab === 'url') { fd.append('url', url.trim()); fd.append('source', url.trim()) }

    settledRef.current = false
    gotMsgRef.current = false
    setErr(null); setCommitResult(null); setSubmitting(true)
    try {
      const r = await api.materialImport(fd)
      const id = r?.job_id ?? r?.id ?? null
      if (!id) throw new Error('后端未返回 job_id')
      setJobId(id)
      setProg({ stage: '正在上传解析…', done: 0, total: 0 })
      setPhase('running')
      openProgress(id)
    } catch (e) {
      toast(e?.body?.detail || e?.message || '导入失败', { tone: 'danger' })
    } finally {
      setSubmitting(false)
    }
  }

  // —— SSE 进度订阅:事件 data 是 JSON {stage, done, total, error} ——
  const openProgress = (id) => {
    closeES()
    settledRef.current = false
    gotMsgRef.current = false
    setErr(null)
    let es
    try {
      es = new EventSource(api.materialImportProgressUrl(id))
    } catch {
      // 连 EventSource 都构造不出来:任务可能已在后端跑完,兜底直接取预览
      finishToPreview(id)
      return
    }
    esRef.current = es
    es.onmessage = (ev) => {
      gotMsgRef.current = true
      let d
      try { d = JSON.parse(ev.data) } catch { return }
      if (d && d.error) {
        settledRef.current = true
        closeES()
        setErr(String(d.error))
        toast('导入解析失败', { tone: 'danger' })
        return
      }
      const total = Number(d?.total) || 0
      const done = Number(d?.done) || 0
      setProg({ stage: d?.stage || '处理中…', done, total })
      if ((total > 0 && done >= total) || TERMINAL.test(String(d?.stage || ''))) {
        settledRef.current = true
        closeES()
        finishToPreview(id)
      }
    }
    es.onerror = () => {
      // EventSource 在服务端正常结束流时也会触发 onerror。若已结算则忽略;
      // 若此前收到过进度(流是正常收尾)→ 兜底取预览;否则视为连不上 → 报错留重试入口。
      if (settledRef.current) return
      settledRef.current = true
      closeES()
      if (gotMsgRef.current) { finishToPreview(id) }
      else { setErr('进度连接中断'); toast('进度连接中断,可重试', { tone: 'danger' }) }
    }
  }

  // —— done 后取预览,渲染成可编辑列表 ——
  const finishToPreview = async (id) => {
    try {
      const r = await api.materialImportPreview(id)
      const list = Array.isArray(r?.items) ? r.items : []
      setItems(list.map((it) => ({
        _key: 'imp-' + (keyRef.current++),
        title: it?.title || '',
        kind: fallbackKind(it?.kind),
        ref_tags: Array.isArray(it?.ref_tags) ? it.ref_tags : [],
        body: it?.body || '',
        summary: it?.summary || '',
        source: it?.source || '',
      })))
      setErr(null)
      setCommitResult(null)
      setPhase('preview')
      if (!list.length) toast('未从来源中解析出可导入的素材', { tone: 'warn' })
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '获取预览失败')
      toast('获取预览失败', { tone: 'danger' })
    }
  }

  const retryProgress = () => { if (jobId) openProgress(jobId) }

  // —— 预览条编辑 ——
  const patchItem = (key, patch) => setItems((arr) => arr.map((it) => (it._key === key ? { ...it, ...patch } : it)))
  const removeItem = (key) => setItems((arr) => arr.filter((it) => it._key !== key))

  // —— 确认:materialImportCommit(job_id, editedItems)→ {created} ——
  const commit = async () => {
    if (!jobId) return
    if (!items.length) { toast('没有可导入的素材', { tone: 'danger' }); return }
    if (items.some((it) => !it.title.trim())) { toast('每条素材都需要标题', { tone: 'danger' }); return }
    setCommitting(true)
    try {
      const payload = items.map(({ _key, ...rest }) => ({ ...rest, title: rest.title.trim() }))
      const r = await api.materialImportCommit(jobId, payload)
      const created = r?.created ?? payload.length
      onImported?.(r)
      const failed = Array.isArray(r?.failed) ? r.failed : []
      const warnings = Array.isArray(r?.warnings) ? r.warnings : []
      if (failed.length || warnings.length) {
        setCommitResult({ created, failed, warnings })
        const failedItems = failed
          .map((f) => payload[Number(f.index)])
          .filter(Boolean)
          .map((it) => ({ ...it, _key: 'imp-' + (keyRef.current++) }))
        setItems(failedItems)
        toast(failed.length ? `部分导入成功:成功 ${created} 条,失败 ${failed.length} 条` : `已导入 ${created} 条素材,但有 ${warnings.length} 条警告`, { tone: failed.length ? 'warn' : 'ok' })
      } else {
        toast(`已导入 ${created} 条素材`, { tone: 'ok' })
        resetToInput()
      }
    } catch (e) {
      toast(e?.body?.detail || e?.message || '导入提交失败', { tone: 'danger' })
    } finally {
      setCommitting(false)
    }
  }

  const pct = prog && prog.total > 0 ? Math.min(100, Math.round((prog.done / prog.total) * 100)) : null
  const phaseHint = phase === 'preview' ? ' · 预览' : phase === 'running' ? ' · 解析中' : ''

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 h-full flex flex-col min-h-0">
        <div className="flex items-center gap-3 mb-3 shrink-0">
          {onCancel && (
            <button onClick={onCancel}
              className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150">
              <ArrowLeft size={16} />返回
            </button>
          )}
          <span className="text-f11 text-faint/50">导入素材{phaseHint}</span>
        </div>

        {/* ——— 输入阶段:来源切换 + 对应输入 ——— */}
        {phase === 'input' && (
          <>
            <div className="flex items-center gap-1 mb-4 shrink-0">
              {SOURCES.map((s) => {
                const Icon = s.icon
                const on = tab === s.key
                return (
                  <button key={s.key} onClick={() => setTab(s.key)}
                    className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-f13 border transition-colors cursor-pointer ${on ? 'border-brand text-brand bg-brand/10 font-medium' : 'border-line text-faint hover:text-ink'}`}>
                    <Icon size={14} />{s.label}
                  </button>
                )
              })}
            </div>

            <div className="flex-1 min-h-0">
              {tab === 'file' && (
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`rounded-xl border border-dashed px-6 py-12 flex flex-col items-center justify-center gap-2 text-center cursor-pointer transition-colors ${dragOver ? 'border-brand bg-brand/5' : 'border-line hover:border-brand/40'}`}>
                  <Upload size={22} className="text-faint" />
                  {file
                    ? <div className="text-f13 text-ink">已选择:<span className="font-medium">{file.name}</span></div>
                    : <div className="text-f13 text-faint">拖拽文件到此,或 <span className="text-brand">点击选择</span></div>}
                  <div className="text-f11 text-faint/60">支持 txt / md / pdf / docx</div>
                  <input ref={fileInputRef} type="file" accept={ACCEPT} className="hidden"
                    aria-label="选择要导入的文件"
                    onChange={(e) => pickFiles(e.target.files)} />
                </div>
              )}
              {tab === 'text' && (
                <Textarea value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="把要导入的文本粘贴到这里…(会自动切分为若干素材)"
                  aria-label="粘贴要导入的文本" className="min-h-[240px] h-full" />
              )}
              {tab === 'url' && (
                <div>
                  <Input value={url} onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://…" aria-label="要导入的网址"
                    onKeyDown={(e) => { if (e.key === 'Enter') submit() }} />
                  <div className="text-f11 text-faint mt-2 leading-snug">将抓取该网址正文,解析并切分为素材。</div>
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-line flex items-center gap-2 shrink-0">
              <Btn variant="primary" onClick={submit} disabled={submitting}>
                {submitting && <Loader2 size={14} className="animate-spin" />}开始导入
              </Btn>
              {onCancel && <Btn variant="ghost" onClick={onCancel} disabled={submitting}>取消</Btn>}
            </div>
          </>
        )}

        {/* ——— 解析中 / 错误态 ——— */}
        {phase === 'running' && (
          <div className="flex-1 min-h-0 flex flex-col items-center justify-center gap-4">
            {err ? (
              <div className="flex flex-col items-center gap-3 text-center">
                <AlertTriangle size={22} className="text-danger" />
                <div className="text-f13 text-ink">{err}</div>
                <div className="flex items-center gap-2">
                  <Btn variant="soft" size="sm" onClick={retryProgress}>重试连接</Btn>
                  <Btn variant="ghost" size="sm" onClick={resetToInput}>返回重导</Btn>
                </div>
              </div>
            ) : (
              <div className="w-full max-w-sm flex flex-col gap-3">
                <div className="flex items-center justify-center gap-2 text-f13 text-ink">
                  <Loader2 size={15} className="animate-spin text-brand" />{prog?.stage || '处理中…'}
                </div>
                <div className="h-2 rounded-full bg-soft overflow-hidden">
                  <div className={`h-full bg-brand transition-[width] duration-300 ${pct == null ? 'animate-pulse' : ''}`}
                    style={{ width: (pct == null ? 35 : pct) + '%' }} />
                </div>
                <div className="text-f11 text-faint text-center tnum">
                  {prog?.total ? `${prog.done}/${prog.total}` : '正在解析…'}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ——— 预览阶段:可编辑列表 + 确认 ——— */}
        {phase === 'preview' && (
          <div className="flex-1 min-h-0 flex flex-col">
            {commitResult && (
              <div role="status" className="mb-3 rounded-lg border border-line bg-soft px-3 py-2 text-f12 text-ink leading-relaxed shrink-0">
                <div className="font-medium text-ink">部分导入成功</div>
                <div className="text-faint">成功 {commitResult.created} 条 · 失败 {commitResult.failed.length} 条{commitResult.warnings.length ? ` · 警告 ${commitResult.warnings.length} 条` : ''}</div>
                {commitResult.failed.length > 0 && (
                  <div className="mt-1.5 space-y-1">
                    {commitResult.failed.map((f) => (
                      <div key={`${f.index}-${f.title}`} className="text-f12">
                        <span className="font-medium">{f.title || `第 ${Number(f.index) + 1} 条`}</span>
                        <span className="text-faint">: {f.reason || '提交失败'}</span>
                      </div>
                    ))}
                  </div>
                )}
                {commitResult.warnings.length > 0 && (
                  <div className="mt-1.5 space-y-1">
                    {commitResult.warnings.map((w) => (
                      <div key={`${w.index}-${w.stage}`} className="text-f12">
                        <span className="font-medium">{w.title || `第 ${Number(w.index) + 1} 条`}</span>
                        <span className="text-faint">: {w.stage || 'warning'} · {w.reason || '处理降级'}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="text-f12 text-faint mb-3 shrink-0">
              解析出 {items.length} 条素材,确认前可改标题 / 分类或删除。
            </div>
            {items.length === 0 ? (
              <div className="flex-1 text-f13 text-faint/60 py-8 text-center">
                没有可导入的素材。
                <button onClick={resetToInput} className="text-brand hover:underline cursor-pointer ml-1">重新导入</button>
              </div>
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
                {items.map((it) => (
                  <div key={it._key} className="rounded-xl border border-line bg-surface px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Input value={it.title} onChange={(e) => patchItem(it._key, { title: e.target.value })}
                        placeholder="素材标题…" aria-label="素材标题" size="sm" className="flex-1 text-f14 font-medium" />
                      <select value={it.kind} onChange={(e) => patchItem(it._key, { kind: e.target.value })}
                        aria-label="素材分类"
                        className="h-7 rounded-md border border-line bg-canvas px-1.5 text-f12 text-ink outline-none cursor-pointer">
                        {MATERIAL_KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
                      </select>
                      <button onClick={() => removeItem(it._key)} title="删除此条" aria-label="删除此条"
                        className="text-faint hover:text-danger shrink-0 cursor-pointer">
                        <Trash2 size={14} />
                      </button>
                    </div>
                    {(it.summary || it.body) && (
                      <div className="mt-1.5 text-f12 text-faint leading-snug line-clamp-2">{it.summary || it.body}</div>
                    )}
                    {(it.ref_tags?.length > 0 || it.source) && (
                      <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                        {(it.ref_tags || []).map((t, i) => (
                          <span key={i} className="text-f11 text-faint bg-soft rounded px-1.5 py-0.5">{t}</span>
                        ))}
                        {it.source && <span className="text-f11 text-faint/60 truncate">来源:{it.source}</span>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 pt-3 border-t border-line flex items-center gap-2 shrink-0">
              <Btn variant="primary" onClick={commit} disabled={committing || items.length === 0}>
                {committing && <Loader2 size={14} className="animate-spin" />}确认导入{items.length ? ` (${items.length})` : ''}
              </Btn>
              <Btn variant="ghost" onClick={resetToInput} disabled={committing}>重新导入</Btn>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

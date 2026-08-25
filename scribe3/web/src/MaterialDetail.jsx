import { useEffect, useRef, useState } from 'react'
import { Loader2, MessagesSquare, Quote, SendToBack, Trash2, MapPin } from 'lucide-react'
import { api } from './api'
import { useUnsavedGuard } from './editor/RichEditor'
import { useChiefSlot } from './ChiefSlotContext'
import { useSelection } from './selectionContext'
import { Btn } from './ui.jsx'
import { ConfirmDialog, InputDialog } from './ui/Dialog.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { useToast } from './ui/Toast'
import { KIND_LABEL } from './materialKinds'
import { seedCiteMaterial, seedDiscussMaterial } from './lib/sessionClip.js'
import { MaterialForm, parseTags, joinTags } from './MaterialForm'

export function MaterialDetail({ node, onChanged, onDeleted }) {
  const toast = useToast()
  const { setStageProposal } = useChiefSlot()
  const { focus, setFocus } = useSelection()
  const [row, setRow] = useState(null)
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [reloadTick, setReloadTick] = useState(0)
  const [delOpen, setDelOpen] = useState(false)
  const [delLoading, setDelLoading] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState(null)
  const [saving, setSaving] = useState(false)
  const [insertOpen, setInsertOpen] = useState(false)
  const [refs, setRefs] = useState([])   // 正向溯源:这条记忆用在了哪些章
  const dirtyRef = useRef(false)
  useUnsavedGuard(() => dirtyRef.current)

  const currentChapterSeq = (() => {
    if (focus?.type === 'chapter') {
      const n = Number(focus.id ?? focus.ref ?? focus.payload?.seq)
      if (Number.isInteger(n) && n >= 1) return n
    }
    return null
  })()

  useEffect(() => {
    let alive = true
    api.materialRefs(node.ref).then((r) => { if (alive) setRefs(r || []) }).catch(() => {})
    return () => { alive = false }
  }, [node?.ref])

  useEffect(() => {
    let alive = true
    setLoading(true); setLoadErr('')
    // 单条读取,禁止全表扫描
    api.material(node.ref)
      .then((m) => {
        if (!alive) return
        setRow(m || null)
        setDraft(m ? {
          title: m.title || '', body: m.body || '', kind: m.kind || 'note',
          tagsText: joinTags(m.tags), refTagsText: joinTags(m.ref_tags),
          source: m.source || '', summary: m.summary || '', pinned: !!m.pinned,
        } : null)
        dirtyRef.current = false
        if (m) setFocus({ type: 'material', id: m.id, label: m.title || '—', payload: { kind: m.kind, source: m.source, origin: m.origin }, origin: 'panel' })
      })
      .catch((e) => { if (alive) { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败') } })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [node?.id, node?.ref, reloadTick]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载中…</div>
  if (loadErr) return (
    <div className="p-4">
      <AsyncState state="error" title="素材加载失败" message={loadErr} onRetry={() => setReloadTick((t) => t + 1)} />
    </div>
  )
  if (!row || !draft) return <div className="p-6 text-f13 text-faint">未找到该素材(可能已删除)。</div>

  const save = async () => {
    if (!draft.title.trim()) { toast('标题不能为空', { tone: 'danger' }); return }
    if (saving) return
    const fields = {
      title: draft.title.trim(),
      body: draft.body,
      kind: draft.kind,
      tags: parseTags(draft.tagsText),
      ref_tags: parseTags(draft.refTagsText),
      source: draft.source.trim() || '',
      summary: draft.summary.trim() || '',
      pinned: !!draft.pinned,
    }
    setSaving(true)
    try {
      await api.editMaterial(row.id, fields)
      const updated = { ...row, ...fields }
      setRow(updated)
      dirtyRef.current = false
      toast('素材已保存', { tone: 'ok' })
      onChanged?.(updated)
    } catch (e) {
      toast(e?.body?.detail || e?.message || '素材保存失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const openDelete = async () => {
    if (delLoading) return
    setDelLoading(true)
    try {
      const impact = await api.objectImpact('material', row.id)
      setDeleteImpact(impact || null)
      setDelOpen(true)
    } catch (e) {
      toast(e?.body?.detail || e?.message || '读取删除影响失败', { tone: 'danger' })
    } finally {
      setDelLoading(false)
    }
  }

  const lifecycleAction = deleteImpact?.recommended_action === 'archive' ? 'archive' : 'delete'
  const lifecycleLabel = lifecycleAction === 'archive' ? '归档' : '删除'
  const doDelete = async () => {
    if (delLoading) return
    setDelLoading(true)
    try {
      if (lifecycleAction === 'archive') {
        await api.editMaterial(row.id, { archived: true })
      } else {
        await api.delMaterial(row.id, deleteImpact?.confirm_impact_token || '')
      }
      dirtyRef.current = false
      toast(`素材已${lifecycleLabel}`, { tone: 'ok' })
      setDelOpen(false)
      onDeleted?.()
    } catch (e) {
      toast(e?.body?.detail || e?.message || `${lifecycleLabel}素材失败`, { tone: 'danger' })
    } finally {
      setDelLoading(false)
    }
  }

  const impactRefs = Array.isArray(deleteImpact?.references) ? deleteImpact.references.filter((r) => Number(r?.count || 0) > 0) : []
  const deleteBody = deleteImpact
    ? `影响范围: ${impactRefs.length ? impactRefs.map((r) => `${r.kind}: ${r.count}`).join('; ') : '未发现引用'}。建议操作: ${lifecycleLabel}。${lifecycleAction === 'archive' ? '确认归档只会从默认列表和召回中隐藏,不会清理相关引用。' : '确认删除会同步清理相关引用。'}`
    : '正在读取影响范围…'

  // 素材→写作桥:正文经块二 stageProposal 通道发布(phase='draft'),
  // 由目标章「草稿」tab 的提示条「填入/追加」闭环落地——不直写编辑器。
  // 此刻只是待采纳提案，不能先写 material_reference；实际采用由 DraftTab 统一记账，
  // 否则会把作者弃用的提案伪报为已消费，并与 DraftTab 的采用记账重复计数。
  const publishToDraft = async (seqText) => {
    const seq = Number(String(seqText || '').trim())
    if (!Number.isInteger(seq) || seq < 1) { toast('请输入有效章号(正整数)', { tone: 'danger' }); return }
    const content = (draft.body || draft.summary || '').trim()
    if (!content) { toast('素材正文为空,无可插入内容', { tone: 'danger' }); return }
    setStageProposal({ phase: 'draft', seq, target: null, content, materialId: row.id, ts: Date.now() })
    toast(`已发布到第 ${seq} 章草稿，待作者填入后再记引用账本`)
  }

  const insertCurrentChapter = () => {
    if (!currentChapterSeq) {
      setInsertOpen(true)
      return
    }
    publishToDraft(String(currentChapterSeq))
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 h-full flex flex-col min-h-0">
        <div className="flex items-center gap-2 mb-3 shrink-0 flex-wrap">
          {/* 类型元数据:text-meta(Task 1 语义 token),与列表/引用脚注同一节奏 */}
          <span className="text-meta text-faint/50">
            素材 · {KIND_LABEL[draft.kind] || draft.kind}
            {row.origin ? ` · ${row.origin}` : ''}
            {row.archived ? ' · 已归档' : ''}
          </span>
          <div className="ml-auto flex items-center gap-1.5 flex-wrap justify-end">
            <Btn
              variant="soft"
              size="sm"
              data-testid="material-discuss-chief"
              onClick={() => {
                seedDiscussMaterial({
                  id: row.id,
                  title: draft.title || row.title,
                  kind: draft.kind || row.kind,
                  source: draft.source || row.source,
                })
                toast('已聚焦主编讨论本条素材', { tone: 'ok' })
              }}
              title="打开主编并以稳定素材 id 讨论本条"
            >
              <MessagesSquare size={13} />聊聊这条
            </Btn>
            <Btn
              variant="soft"
              size="sm"
              data-testid="material-cite-chief"
              onClick={() => {
                seedCiteMaterial({
                  id: row.id,
                  title: draft.title || row.title,
                  kind: draft.kind || row.kind,
                })
                toast('已引用素材到主编输入(含 ref=material:id)', { tone: 'ok' })
              }}
              title="引用本素材到主编会话(显式 material id,非纯粘贴)"
            >
              <Quote size={13} />引用到会话
            </Btn>
            <Btn variant="soft" size="sm" onClick={insertCurrentChapter}
              disabled={!(draft.body || draft.summary || '').trim()}
              data-testid="material-insert-current"
              title={currentChapterSeq
                ? `插入当前第 ${currentChapterSeq} 章草稿，填入后才记引用`
                : '把素材发布到某章草稿(填入/追加)，填入后才记引用'}>
              <SendToBack size={13} />{currentChapterSeq ? `插入第${currentChapterSeq}章` : '插入到草稿'}
            </Btn>
            {!currentChapterSeq && (
              <Btn variant="ghost" size="sm" onClick={() => setInsertOpen(true)}
                disabled={!(draft.body || draft.summary || '').trim()}
                data-testid="material-insert-other">
                指定章号
              </Btn>
            )}
            <Btn variant="primary" size="sm" onClick={save} disabled={saving} data-testid="material-save">
              {saving ? '保存中…' : '保存'}
            </Btn>
            <Btn variant="ghost" size="sm" onClick={openDelete} disabled={delLoading} className="hover:text-danger" title="删除素材">
              {delLoading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}删除
            </Btn>
          </div>
        </div>
        <MaterialForm draft={draft} onDraft={(d) => { setDraft(d); dirtyRef.current = true }}
          editorKey={`material:${row.id}`} showPinned />
        <div className="text-f12 text-faint mt-2 leading-snug shrink-0">素材是参考记忆:借鉴非照搬,不进知识图谱/不被反哺;正典设定请放「设定库」。</div>
        {refs.length > 0 && (
          <div className="mt-3 pt-3 border-t border-line shrink-0">
            {/* 「用在哪」元数据:text-meta,与来源/类型同一节奏 */}
            <div className="text-meta text-faint mb-1.5 inline-flex items-center gap-1"><MapPin size={11} />这条记忆被写作参考过 {refs.length} 次(正向溯源)</div>
            <div className="flex flex-wrap gap-1.5">
              {refs.map((r, i) => (
                <span key={i} className="text-meta text-ink bg-soft rounded px-2 py-0.5" title={r.reason || ''}>
                  第{r.chapter}章{r.dimension ? `·参考${r.dimension}` : ''}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <ConfirmDialog
        open={delOpen}
        title={`${lifecycleLabel}素材「${row.title}」?`}
        body={deleteBody}
        danger={lifecycleAction !== 'archive'}
        confirmText={lifecycleLabel}
        onConfirm={doDelete}
        onClose={() => setDelOpen(false)}
      />
      <InputDialog
        open={insertOpen}
        title="插入到第几章的草稿?"
        placeholder="章号,如 4"
        confirmText="发布"
        onConfirm={publishToDraft}
        onClose={() => setInsertOpen(false)}
      />
    </div>
  )
}

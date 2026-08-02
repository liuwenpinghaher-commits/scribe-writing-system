import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, FilePlus2, Loader2, MessagesSquare, Network, Plus, Quote, Search, SendToBack, Trash2, Upload, MapPin } from 'lucide-react'
import { api } from './api'
import { RichEditor, useUnsavedGuard } from './editor/RichEditor'
import { useChiefSlot } from './ChiefSlotContext'
import { useSelection } from './selectionContext'
import { Btn, Input } from './ui.jsx'
import { ConfirmDialog, InputDialog } from './ui/Dialog.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { useToast } from './ui/Toast'
import { MATERIAL_KINDS } from './materialKinds'
import { MaterialImport } from './MaterialImport'
import { MaterialNetwork } from './MaterialNetwork'
import { DirectoryHeader } from './layout/DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './layout/DirectoryRow'
import { handleSelAction } from './lib/selAction'
import { seedCiteMaterial, seedDiscussMaterial } from './lib/sessionClip.js'

// 素材库:非正典写作材料。MATERIAL_KINDS 抽到 materialKinds.js(破 MaterialImport 循环 import),此处 re-export 兼容既有 from './Materials' 引用。
export { MATERIAL_KINDS } from './materialKinds'
const KIND_LABEL = Object.fromEntries(MATERIAL_KINDS.map((k) => [k.key, k.label]))

const matLeafNode = (m) => ({ id: `material:${m.id}`, type: 'material', ref: m.id, label: m.title || '—', meta: { kind: m.kind } })

// 逗号分隔字符串 ↔ tags 数组
const parseTags = (s) => String(s || '').split(/[,，]/).map((t) => t.trim()).filter(Boolean)
const joinTags = (arr) => (Array.isArray(arr) ? arr : []).join(', ')

// ——— 表单主体(新建/详情共用):标题 + kind + tags + ref_tags + summary + source + pinned + body ———
function MaterialForm({ draft, onDraft, editorKey, showPinned = false }) {
  const set = (k, v) => onDraft({ ...draft, [k]: v })
  return (
    <div className="flex flex-col gap-2.5 flex-1 min-h-0">
      <Input variant="bordered" value={draft.title} onChange={(e) => set('title', e.target.value)}
        placeholder="素材标题…" aria-label="素材标题" className="text-object-title font-medium" />
      <div className="flex items-center gap-2 flex-wrap">
        <label className="inline-flex items-center gap-1.5 text-f12 text-faint">
          分类
          <select value={draft.kind} onChange={(e) => set('kind', e.target.value)} aria-label="素材分类"
            className="h-8 rounded-md border border-line bg-canvas px-1.5 text-f13 text-ink outline-none cursor-pointer">
            {MATERIAL_KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
          </select>
        </label>
        <Input variant="bordered" value={draft.tagsText} onChange={(e) => set('tagsText', e.target.value)}
          placeholder="标签(逗号分隔)" aria-label="素材标签" className="flex-1 min-w-32" />
        <Input variant="bordered" value={draft.refTagsText} onChange={(e) => set('refTagsText', e.target.value)}
          placeholder="参考维度(风格/剧情/手法…)" aria-label="参考维度" className="flex-1 min-w-32" />
        <Input variant="bordered" value={draft.source} onChange={(e) => set('source', e.target.value)}
          placeholder="来源(出处/链接,可空)" aria-label="素材来源" className="flex-1 min-w-32" />
        {showPinned && (
          <label className="inline-flex items-center gap-1.5 text-f12 text-faint cursor-pointer">
            <input type="checkbox" checked={!!draft.pinned} onChange={(e) => set('pinned', e.target.checked)}
              data-testid="material-pinned-toggle" aria-label="核心记忆(置顶)" />
            核心记忆
          </label>
        )}
      </div>
      <Input variant="bordered" value={draft.summary} onChange={(e) => set('summary', e.target.value)}
        placeholder="手法摘要(写作注入优先;借鉴非照搬)" aria-label="手法摘要" data-testid="material-summary" />
      <RichEditor
        value={draft.body}
        editorKey={editorKey}
        ariaLabel="素材正文"
        onChange={(md) => set('body', md)}
        placeholder="研究资料 / 参考片段 / 灵感剪藏 / 待用桥段 / 笔记……(markdown)"
        className="flex-1 min-h-0"
        onSelAction={(sel) => handleSelAction(sel, {
          scopeLabel: draft.title?.trim() ? `素材「${draft.title.trim()}」` : '素材正文',
        })}
      />
    </div>
  )
}

// ——— 新建(material_new 节点):作者直管非正典素材 ———
export function MaterialNew({ kind, onCancel, onCreated }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState({
    title: '', body: '', kind: KIND_LABEL[kind] ? kind : 'note',
    tagsText: '', refTagsText: '', source: '', summary: '', pinned: false,
  })
  const create = async () => {
    if (!draft.title.trim()) { toast('请填写素材标题', { tone: 'danger' }); return }
    if (saving) return
    const payload = {
      title: draft.title.trim(), body: draft.body, kind: draft.kind,
      tags: parseTags(draft.tagsText), ref_tags: parseTags(draft.refTagsText),
      source: draft.source.trim() || '', summary: draft.summary.trim() || '',
      pinned: !!draft.pinned, origin: 'manual',
    }
    setSaving(true)
    try {
      const result = await api.addMaterial(payload)
      toast('素材已保存', { tone: 'ok' })
      onCreated?.(result?.id ?? null, payload.title)
    } catch (e) {
      toast(e?.body?.detail || e?.message || '素材保存失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="h-full overflow-y-auto" data-testid="material-new">
      <div className="max-w-2xl mx-auto px-6 py-5 h-full flex flex-col min-h-0">
        <div className="flex items-center gap-3 mb-3 shrink-0">
          {onCancel && <button onClick={onCancel} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16} />返回</button>}
          <span className="text-meta text-faint/50">新建素材{KIND_LABEL[kind] ? ` · ${KIND_LABEL[kind]}` : ''}</span>
        </div>
        <p className="text-meta text-faint mb-2" data-testid="material-new-dialogue-hint">
          素材是非正典参考记忆，由作者直接管理。
        </p>
        <MaterialForm draft={draft} onDraft={setDraft} editorKey="material:new" showPinned />
        <div className="mt-4 pt-3 border-t border-line flex items-center gap-2 shrink-0">
          <Btn variant="primary" onClick={create} disabled={saving} data-testid="material-new-submit">
            {saving ? '保存中…' : '保存素材'}
          </Btn>
          {onCancel && <Btn variant="ghost" onClick={onCancel}>取消</Btn>}
        </div>
      </div>
    </div>
  )
}

// ——— 详情/编辑(material 叶节点)+ 素材→写作桥 ———
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
                ? `插入当前第 ${currentChapterSeq} 章草稿并记引用`
                : '把素材发布到某章草稿(填入/追加),并记 material_reference'}>
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

export function MaterialImportPane({ onCancel, onImported }) {
  return <MaterialImport onCancel={onCancel} onImported={onImported} />
}

export function MaterialNetworkPane({ onSelect }) {
  return <MaterialNetwork onSelect={(m) => onSelect?.(matLeafNode(m))} />
}

const materialRefCount = (m) => Number(m?.recall_count || m?.ref_count || 0)

const normalizeMaterialRows = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

const MATERIAL_PAGE_SIZE = 200

const normalizeMaterialPage = (payload) => {
  const items = normalizeMaterialRows(payload)
  if (Array.isArray(payload)) return { items, nextCursor: null, total: items.length }
  const rawTotal = Number(payload?.total)
  return {
    items,
    nextCursor: payload?.next_cursor ?? null,
    total: Number.isFinite(rawTotal) ? rawTotal : items.length,
  }
}

// ——— 栏2素材工作台:服务端 view 过滤 + 分页 + 健康度 ———
export function MaterialList({ node, onSelect }) {
  const isCat = node?.type === 'material_category'
  const kind = isCat ? node.ref : null
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  const [activeView, setActiveView] = useState('all')
  const [activeKind, setActiveKind] = useState(kind || 'all')
  const [activeOrigin, setActiveOrigin] = useState('all') // all|manual|import|session_clip|chief
  const [reloadTick, setReloadTick] = useState(0)
  const [pageInfo, setPageInfo] = useState({ nextCursor: null, total: null })
  const [loadingMore, setLoadingMore] = useState(false)
  const [health, setHealth] = useState(null)
  const [recallDegraded, setRecallDegraded] = useState([])

  useEffect(() => {
    setActiveKind(kind || 'all')
    setActiveView('all')
    setActiveOrigin('all')
  }, [kind])

  useEffect(() => {
    let alive = true
    // 测试 mock 可能未挂 materialsHealth:跳过不炸
    if (typeof api.materialsHealth !== 'function') {
      setHealth(null)
      return () => { alive = false }
    }
    api.materialsHealth()
      .then((h) => { if (alive) setHealth(h) })
      .catch(() => { if (alive) setHealth(null) })
    return () => { alive = false }
  }, [reloadTick])

  // 服务端 view/kind/origin 分页;搜索走三通道召回(with_meta 透出 degraded)
  useEffect(() => {
    let alive = true
    const needle = q.trim()
    setErr(null)
    setLoadingMore(false)
    setPageInfo({ nextCursor: null, total: null })
    setRecallDegraded([])
    const selectedKind = isCat ? kind : (activeKind === 'all' ? null : activeKind)
    const originFilter = activeOrigin === 'all' ? undefined : activeOrigin
    if (!needle) {
      api.materials({
        kind: selectedKind || undefined,
        view: activeView || 'all',
        origin: originFilter,
        limit: MATERIAL_PAGE_SIZE,
      })
        .then((r) => {
          if (!alive) return
          const page = normalizeMaterialPage(r)
          setRows(page.items)
          setPageInfo({ nextCursor: page.nextCursor, total: page.total })
          setErr(null)
        })
        .catch((e) => { if (alive) { setRows(null); setErr(e?.body?.detail || e?.message || '素材加载失败') } })
      return () => { alive = false }
    }
    const t = setTimeout(() => {
      api.materialRecall(needle, undefined, true)
        .then((r) => {
          if (!alive) return
          let items = normalizeMaterialRows(r).map((x) => ({ ...x, id: x.material_id || x.id }))
          // 搜索结果客户端再叠 origin/kind(服务端 recall 未带 origin 参)
          if (selectedKind) items = items.filter((m) => m.kind === selectedKind)
          if (originFilter) items = items.filter((m) => (m.origin || 'manual') === originFilter)
          setRows(items)
          setPageInfo({ nextCursor: null, total: items.length })
          setRecallDegraded(Array.isArray(r?.degraded_sources) ? r.degraded_sources : [])
          setErr(null)
        })
        .catch((e) => { if (alive) { setRows(null); setErr(e?.body?.detail || e?.message || '素材加载失败') } })
    }, 350)
    return () => { alive = false; clearTimeout(t) }
  }, [node?.id, kind, q, reloadTick, activeView, activeKind, activeOrigin, isCat])

  const sourceRows = rows || []
  const selectedKind = isCat ? kind : (activeKind === 'all' ? null : activeKind)
  const originFilter = activeOrigin === 'all' ? undefined : activeOrigin
  // 服务端已按 view/origin 过滤;搜索路径上客户端再滤
  const filtered = sourceRows

  const countForKind = (k) => sourceRows.filter((m) => m.kind === k).length
  const title = isCat ? `素材 · ${KIND_LABEL[kind] || kind}` : '素材库'
  const newKind = selectedKind || kind || 'note'

  const newNode = () => onSelect?.({ id: `matnew:${newKind}`, type: 'material_new', ref: newKind, label: KIND_LABEL[newKind] || node?.label })
  const importNode = () => onSelect?.({ id: 'material:import', type: 'material_import', ref: newKind, label: '导入素材' })
  const networkNode = () => onSelect?.({ id: 'material:network', type: 'material_network', ref: null, label: '记忆网络' })
  const retryLoad = () => {
    setErr(null)
    setRows(null)
    setPageInfo({ nextCursor: null, total: null })
    setReloadTick((t) => t + 1)
  }
  const hasMore = pageInfo.nextCursor !== null && pageInfo.nextCursor !== undefined && pageInfo.nextCursor !== ''
  const loadMore = async () => {
    if (!hasMore || loadingMore) return
    setLoadingMore(true)
    try {
      const page = normalizeMaterialPage(await api.materials({
        kind: selectedKind || undefined,
        view: activeView || 'all',
        origin: originFilter,
        limit: MATERIAL_PAGE_SIZE,
        cursor: pageInfo.nextCursor,
      }))
      setRows((prev) => [...(prev || []), ...page.items])
      setPageInfo({ nextCursor: page.nextCursor, total: page.total })
      setErr(null)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '素材加载失败')
    } finally {
      setLoadingMore(false)
    }
  }

  if (err) return (
    <div className="p-3">
      <AsyncState state="error" title="素材加载失败" message={err} onRetry={retryLoad} />
    </div>
  )
  if (!rows) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载素材…</div>

  const smartViews = [
    { key: 'all', label: '全部' },
    { key: 'pinned', label: '核心记忆' },
    { key: 'referenced', label: '已引用' },
    { key: 'untagged', label: '无标签' },
    { key: 'recent', label: '最近' },
    { key: 'archived', label: '已归档' },
  ]
  const originFilters = [
    { key: 'all', label: '全部来源' },
    { key: 'manual', label: '手建' },
    { key: 'import', label: '来自导入' },
    { key: 'session_clip', label: '剪藏' },
    { key: 'chief', label: '历史主编记录' },
  ]

  return (
    <div data-testid="material-workbench" className={DIR_SHELL}>
      <div data-testid="material-workbench-header">
        <DirectoryHeader
          title={title}
          count={pageInfo.total != null ? pageInfo.total : filtered.length}
          query={q}
          onQueryChange={setQ}
          searchLabel="搜索素材"
          searchPlaceholder="标题 / 正文 / 标签"
          primaryAction={{ label: '新建', onClick: newNode }}
          secondaryActions={[
            { label: '导入', onClick: importNode },
            { label: '网络', onClick: networkNode },
          ]}
        />
        <div data-testid="material-smart-views" className="flex flex-wrap gap-1 px-3 pb-2 border-b border-line/40 bg-surface">
          {smartViews.map((v) => (
            <button key={v.key} type="button" onClick={() => setActiveView(v.key)}
              className={`h-6 px-2 rounded-md text-meta whitespace-nowrap transition-colors cursor-pointer ${activeView === v.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {v.label}
            </button>
          ))}
        </div>
        <div data-testid="material-origin-filters" className="flex flex-wrap gap-1 px-3 pb-2 border-b border-line/40 bg-surface">
          {originFilters.map((o) => (
            <button key={o.key} type="button" onClick={() => setActiveOrigin(o.key)}
              aria-pressed={activeOrigin === o.key}
              className={`h-6 px-2 rounded-md text-meta whitespace-nowrap transition-colors cursor-pointer ${activeOrigin === o.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {o.label}
            </button>
          ))}
        </div>
        {health && (
          <div data-testid="material-health" className="px-3 py-1.5 text-meta text-faint border-b border-line/30 bg-surface/80">
            健康度: 共 {health.total ?? 0} · 未召回 {health.never_recalled ?? 0} · 无摘要 {health.no_summary ?? 0} · 无标签 {health.untagged ?? 0}
          </div>
        )}
        {recallDegraded.length > 0 && (
          <div role="status" data-testid="material-recall-degraded" className="px-3 py-1.5 text-meta text-danger border-b border-line/30">
            召回降级: {recallDegraded.map((s) => `${s.source}: ${s.reason}`).join('；')}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        <div className="mb-2">
          <DirectorySectionLabel>分类</DirectorySectionLabel>
          <div data-testid="material-kind-list" className="space-y-0.5">
            {!isCat && (
              <DirectoryRow
                title="全部分类"
                meta={String(pageInfo.total ?? sourceRows.length)}
                active={activeKind === 'all'}
                onClick={() => setActiveKind('all')}
                aria-label="全部分类"
              />
            )}
            {MATERIAL_KINDS.map((k) => (
              <DirectoryRow
                key={k.key}
                title={k.label}
                meta={String(countForKind(k.key))}
                active={(selectedKind || activeKind) === k.key}
                onClick={() => setActiveKind(k.key)}
                aria-label={k.label}
              />
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-f13 text-faint/60 py-8 text-center">
            {q.trim() ? '没有匹配的素材。' : <>还没有素材。<button type="button" onClick={newNode} className="text-brand hover:underline cursor-pointer ml-1">新建一条</button></>}
          </div>
        ) : (
          <div className="space-y-0.5" data-testid="material-item-list">
            <DirectorySectionLabel>素材</DirectorySectionLabel>
            {filtered.map((m) => (
              <DirectoryRow
                key={m.id}
                title={m.title || '—'}
                leading={m.pinned ? <span className="text-brand shrink-0" aria-hidden>·</span> : null}
                meta={`${KIND_LABEL[m.kind] || m.kind}${m.origin ? ` · ${m.origin}` : ''}${materialRefCount(m) > 0 ? ` · ${materialRefCount(m)}次` : ''}`}
                onClick={() => onSelect?.(matLeafNode(m))}
                aria-label={m.title || '—'}
              />
            ))}
            {hasMore && (
              <button type="button" onClick={loadMore} disabled={loadingMore}
                className="mt-2 w-full h-8 rounded-md bg-soft text-f12 text-faint hover:bg-brand/10 hover:text-brand disabled:opacity-50 cursor-pointer">
                {loadingMore ? '加载中…' : `加载更多 (${sourceRows.length}/${pageInfo.total ?? '?'})`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

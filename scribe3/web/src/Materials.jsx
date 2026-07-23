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
import { seedChiefAddMaterial } from './lib/chiefSeed.js'
import { seedCiteMaterial, seedDiscussMaterial } from './lib/sessionClip.js'

// 素材库:非正典写作材料。MATERIAL_KINDS 抽到 materialKinds.js(破 MaterialImport 循环 import),此处 re-export 兼容既有 from './Materials' 引用。
export { MATERIAL_KINDS } from './materialKinds'
const KIND_LABEL = Object.fromEntries(MATERIAL_KINDS.map((k) => [k.key, k.label]))

const matLeafNode = (m) => ({ id: `material:${m.id}`, type: 'material', ref: m.id, label: m.title || '—', meta: { kind: m.kind } })

// 逗号分隔字符串 ↔ tags 数组
const parseTags = (s) => String(s || '').split(/[,，]/).map((t) => t.trim()).filter(Boolean)
const joinTags = (arr) => (Array.isArray(arr) ? arr : []).join(', ')

// ——— 表单主体(新建/详情共用):标题 + kind + tags + source + RichEditor 正文 ———
function MaterialForm({ draft, onDraft, editorKey }) {
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
        <Input variant="bordered" value={draft.source} onChange={(e) => set('source', e.target.value)}
          placeholder="来源(出处/链接,可空)" aria-label="素材来源" className="flex-1 min-w-32" />
      </div>
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

// ——— 新建(material_new 节点):草稿内存;「让主编写入」→ s3_add_material 待批(禁 REST 直写) ———
export function MaterialNew({ kind, onCancel, onCreated }) {
  const toast = useToast()
  const [draft, setDraft] = useState({ title: '', body: '', kind: KIND_LABEL[kind] ? kind : 'note', tagsText: '', source: '' })
  const create = () => {
    if (!draft.title.trim()) { toast('请填写素材标题', { tone: 'danger' }); return }
    seedChiefAddMaterial({
      title: draft.title.trim(),
      body: draft.body,
      kind: draft.kind,
      tags: parseTags(draft.tagsText),
      source: draft.source.trim() || '',
    })
    toast('已交给主编写入素材,请在右栏批准', { tone: 'ok' })
    onCreated?.(null, draft.title.trim())
  }
  return (
    <div className="h-full overflow-y-auto" data-testid="material-new">
      <div className="max-w-2xl mx-auto px-6 py-5 h-full flex flex-col min-h-0">
        <div className="flex items-center gap-3 mb-3 shrink-0">
          {onCancel && <button onClick={onCancel} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16} />返回</button>}
          <span className="text-meta text-faint/50">新建素材{KIND_LABEL[kind] ? ` · ${KIND_LABEL[kind]}` : ''}</span>
        </div>
        <p className="text-meta text-faint mb-2" data-testid="material-new-dialogue-hint">
          素材写入须经主编 s3_add_material 待批,不直连 REST。
        </p>
        <MaterialForm draft={draft} onDraft={setDraft} editorKey="material:new" />
        <div className="mt-4 pt-3 border-t border-line flex items-center gap-2 shrink-0">
          <Btn variant="primary" onClick={create} data-testid="material-new-submit-chief">
            让主编写入(待批)
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
  const { setFocus } = useSelection()
  const [row, setRow] = useState(null)
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [reloadTick, setReloadTick] = useState(0)
  const [saving, setSaving] = useState(false)
  const [delOpen, setDelOpen] = useState(false)
  const [delLoading, setDelLoading] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState(null)
  const [insertOpen, setInsertOpen] = useState(false)
  const [refs, setRefs] = useState([])   // 正向溯源:这条记忆用在了哪些章
  const dirtyRef = useRef(false)
  useUnsavedGuard(() => dirtyRef.current)

  useEffect(() => {
    let alive = true
    api.materialRefs(node.ref).then((r) => { if (alive) setRefs(r || []) }).catch(() => {})
    return () => { alive = false }
  }, [node?.ref])

  useEffect(() => {
    let alive = true
    setLoading(true); setLoadErr('')
    api.materials()
      .then((payload) => {
        if (!alive) return
        // 兼容数组与 { items, next_cursor, total } 分页形态
        const list = normalizeMaterialRows(payload)
        const m = list.find((r) => r.id === node.ref || r.material_id === node.ref) || null
        setRow(m)
        setDraft(m ? { title: m.title || '', body: m.body || '', kind: m.kind || 'note', tagsText: joinTags(m.tags), source: m.source || '' } : null)
        dirtyRef.current = false
        // 块三:选中素材 → 通用选中总线显式聚焦,主编按 focusTalk 的 material 分支给聚焦话术
        if (m) setFocus({ type: 'material', id: m.id, label: m.title || '—', payload: { kind: m.kind, source: m.source }, origin: 'panel' })
      })
      // 请求失败 ≠ 素材不存在:进 error 态给真实错误 + 重试,不谎称「可能已删除」
      .catch((e) => { if (alive) { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败') } })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [node?.id, reloadTick]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载中…</div>
  if (loadErr) return (
    <div className="p-4">
      <AsyncState state="error" title="素材加载失败" message={loadErr} onRetry={() => setReloadTick((t) => t + 1)} />
    </div>
  )
  if (!row || !draft) return <div className="p-6 text-f13 text-faint">未找到该素材(可能已删除)。</div>

  const save = async () => {
    if (!draft.title.trim()) { toast('标题不能为空', { tone: 'danger' }); return }
    setSaving(true)
    try {
      await api.editMaterial(row.id, {
        title: draft.title.trim(), body: draft.body, kind: draft.kind,
        tags: parseTags(draft.tagsText), source: draft.source.trim() || '',
      })
      dirtyRef.current = false
      toast('素材已保存')
      onChanged?.()
    } catch (e) { toast(e?.body?.detail || e?.message || '保存失败', { tone: 'danger' }) }
    finally { setSaving(false) }
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
    try {
      if (lifecycleAction === 'archive') await api.archiveObject('material', row.id)
      else await api.deleteObject('material', row.id, deleteImpact?.confirm_impact_token || '')
      dirtyRef.current = false
      onDeleted?.()
    } catch (e) { toast(e?.body?.detail || e?.message || `${lifecycleLabel}失败`, { tone: 'danger' }) }
  }

  const impactRefs = Array.isArray(deleteImpact?.references) ? deleteImpact.references.filter((r) => Number(r?.count || 0) > 0) : []
  const deleteBody = deleteImpact
    ? `影响范围: ${impactRefs.length ? impactRefs.map((r) => `${r.kind}: ${r.count}`).join('; ') : '未发现引用'}。建议操作: ${lifecycleLabel}。${lifecycleAction === 'archive' ? '确认归档只会从默认列表和召回中隐藏,不会清理相关引用。' : '确认删除会同步清理相关引用。'}`
    : '正在读取影响范围…'

  // 素材→写作桥:正文经块二 stageProposal 通道发布(phase='draft'),
  // 由目标章「草稿」tab 的提示条「填入/追加」闭环落地——不直写编辑器。
  const publishToDraft = (seqText) => {
    const seq = Number(String(seqText || '').trim())
    if (!Number.isInteger(seq) || seq < 1) { toast('请输入有效章号(正整数)', { tone: 'danger' }); return }
    const content = (draft.body || '').trim()
    if (!content) { toast('素材正文为空,无可插入内容', { tone: 'danger' }); return }
    setStageProposal({ phase: 'draft', seq, target: null, content, materialId: row.id, ts: Date.now() })
    toast(`已发布到第 ${seq} 章草稿:打开该章「草稿」tab,用提示条填入/追加`)
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 h-full flex flex-col min-h-0">
        <div className="flex items-center gap-2 mb-3 shrink-0 flex-wrap">
          {/* 类型元数据:text-meta(Task 1 语义 token),与列表/引用脚注同一节奏 */}
          <span className="text-meta text-faint/50">素材 · {KIND_LABEL[draft.kind] || draft.kind}</span>
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
            <Btn variant="soft" size="sm" onClick={() => setInsertOpen(true)} disabled={!(draft.body || '').trim()}
              title="把素材正文发布到某章草稿的提示条(填入/追加),不直写编辑器">
              <SendToBack size={13} />插入到草稿
            </Btn>
            <Btn variant="primary" size="sm" onClick={save} disabled={saving}>
              {saving && <Loader2 size={13} className="animate-spin" />}保存
            </Btn>
            <Btn variant="ghost" size="sm" onClick={openDelete} disabled={delLoading} className="hover:text-danger" title="删除素材">
              {delLoading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}删除
            </Btn>
          </div>
        </div>
        <MaterialForm draft={draft} onDraft={(d) => { setDraft(d); dirtyRef.current = true }} editorKey={`material:${row.id}`} />
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

const materialTags = (m) => [
  ...(Array.isArray(m?.ref_tags) ? m.ref_tags : []),
  ...(Array.isArray(m?.tags) ? m.tags : []),
].filter(Boolean)

const materialRefCount = (m) => Number(m?.recall_count || m?.ref_count || 0)

const viewMatcher = (key, recentIds) => {
  if (key === 'pinned') return (m) => !!m?.pinned
  if (key === 'referenced') return (m) => materialRefCount(m) > 0
  if (key === 'untagged') return (m) => materialTags(m).length === 0
  if (key === 'recent') return (m) => recentIds.has(m?.id)
  return () => true
}

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

// ——— 栏2素材工作台:搜索第一行 + 动作第二行 + 智能视图/分类/素材列表 ———
export function MaterialList({ node, onSelect }) {
  const isCat = node?.type === 'material_category'
  const kind = isCat ? node.ref : null
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  const [activeView, setActiveView] = useState('all')
  const [activeKind, setActiveKind] = useState(kind || 'all')
  const [reloadTick, setReloadTick] = useState(0) // 导入后刷新列表
  const [pageInfo, setPageInfo] = useState({ nextCursor: null, total: null })
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    setActiveKind(kind || 'all')
    setActiveView('all')
  }, [kind])

  // 空 q:按 kind 列全部;非空 q:三通道召回搜索(语义+关键词+图,debounce 350ms)取代客户端 substring
  useEffect(() => {
    let alive = true
    const needle = q.trim()
    setErr(null)
    setLoadingMore(false)
    setPageInfo({ nextCursor: null, total: null })
    if (!needle) {
      api.materials({ kind: kind || undefined, limit: MATERIAL_PAGE_SIZE })
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
      api.materialRecall(needle)
        .then((r) => {
          if (!alive) return
          const items = normalizeMaterialRows(r).map((x) => ({ ...x, id: x.material_id || x.id }))
          setRows(items)
          setPageInfo({ nextCursor: null, total: items.length })
          setErr(null)
        })
        .catch((e) => { if (alive) { setRows(null); setErr(e?.body?.detail || e?.message || '素材加载失败') } })
    }, 350)
    return () => { alive = false; clearTimeout(t) }
  }, [node?.id, kind, q, reloadTick])

  const sourceRows = rows || []
  const selectedKind = isCat ? kind : (activeKind === 'all' ? null : activeKind)
  const recentIds = new Set(sourceRows.slice(0, 12).map((m) => m?.id))
  const matchesView = viewMatcher(activeView, recentIds)
  const filtered = sourceRows
    .filter((m) => !selectedKind || m.kind === selectedKind)
    .filter(matchesView)

  const countForView = (key) => {
    const match = viewMatcher(key, recentIds)
    return sourceRows.filter((m) => (!selectedKind || m.kind === selectedKind) && match(m)).length
  }
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
        kind: kind || undefined,
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
      {/* 统一 AsyncState:标题固定、message 透传真实错误(不吞后端 detail) */}
      <AsyncState state="error" title="素材加载失败" message={err} onRetry={retryLoad} />
    </div>
  )
  if (!rows) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载素材…</div>

  const smartViews = [
    { key: 'all', label: '全部' },
    { key: 'pinned', label: '核心记忆' },
    { key: 'referenced', label: '已引用' },
    { key: 'untagged', label: '无标签' },
    { key: 'recent', label: '最近导入' },
  ]

  return (
    <div data-testid="material-workbench" className={DIR_SHELL}>
      <div data-testid="material-workbench-header">
        <DirectoryHeader
          title={title}
          count={filtered.length}
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
              <span className="ml-1 tabular-nums opacity-70">{countForView(v.key)}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        <div className="mb-2">
          <DirectorySectionLabel>分类</DirectorySectionLabel>
          <div data-testid="material-kind-list" className="space-y-0.5">
            {!isCat && (
              <DirectoryRow
                title="全部分类"
                meta={String(sourceRows.length)}
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
                meta={`${KIND_LABEL[m.kind] || m.kind}${materialRefCount(m) > 0 ? ` · ${materialRefCount(m)}次` : ''}`}
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

import { useState } from 'react'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { api } from './api'
import { DetailView } from './views/CodexView'
import { Btn } from './ui.jsx'
import { isChapterNum } from './lib/utils'

// 素材分类 ref → DetailView type
const CAT_TO_TYPE = {
  character: 'chars',
  faction: 'factions',
  item: 'items',
  term: 'terms',
  world_rule: 'rules',
  promise: 'promises',
  motif: 'motifs',
  proposition: 'facts',   // 批D 件1:命题生产入口(POST /facts,含 secret/leak_markers)
}

// 各类型空草稿(给必要默认值,避免后端 422)
function emptyDraft(catType) {
  switch (catType) {
    case 'character': return { name: '' }
    case 'faction': return { name: '' }
    case 'item': return { name: '', symbolic_state: 'active' }
    case 'term': return { name: '' }
    case 'world_rule': return { name: '', category: 'magic' }
    case 'promise': return { text: '', setup_chapter: 1, tier: 'chapter', resolution: '' }
    case 'motif': return { name: '' }
    case 'proposition': return { entity: '', attribute: '', value: '', valid_from: 1, secret: false, leak_markers: [] }
    default: return { name: '' }
  }
}

// 校验:创建前最小必填
function isValid(catType, d) {
  if (catType === 'promise') {
    const requiresResolution = d.tier === 'arc' || d.tier === 'book'
    return !!(d.text && d.text.trim() && (!requiresResolution || (d.resolution && d.resolution.trim())))
  }
  // 命题:主体 + 属性 + 值三者必填(对齐后端 FactIn 无默认的 entity/attribute/value)。
  // 批D Minor①:生效章须 ≥1(默认 1;用户在 DetailView 数字框可清空/输 0,valid_from 语义 1-based)。
  if (catType === 'proposition') return !!(d.entity && d.entity.trim() && d.attribute && d.attribute.trim() && d.value && d.value.trim() && isChapterNum(d.valid_from))
  return !!(d.name && d.name.trim())
}

// 调用对应新建端点;返回新建条目可用于选中的 ref(name 或 id)
async function createRecord(catType, d) {
  if (catType === 'character') { await api.addChar(d); return d.name }
  if (catType === 'faction') { await api.post('/factions', d); return d.name }
  if (catType === 'item') { await api.post('/items', d); return d.name }
  if (catType === 'term') { await api.post('/terms', d); return d.name }
  if (catType === 'world_rule') { await api.post('/world-rules', d); return d.name }
  if (catType === 'promise') { const r = await api.addPromiseNew(d); return r?.id || r?.pid || null }
  if (catType === 'motif') { const r = await api.addMotifNew(d); return r?.id || r?.mid || null }
  if (catType === 'proposition') { const r = await api.addFact(d); return r?.oid ? String(r.oid).split(':').pop() : null }
  return null
}

/**
 * 素材新建表单:复用 CodexView 的 DetailView(isNew),草稿留内存,
 * 「创建」时才落库。创建成功 → onCreated(catType, ref) 让父层重载树并选中。
 */
export function CodexNew({ catType, label, onCancel, onCreated }) {
  const type = CAT_TO_TYPE[catType]
  const [draft, setDraft] = useState(() => emptyDraft(catType))
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  if (!type) return <div className="p-6 text-f13 text-faint">未知设定类型:{catType}</div>

  const create = async () => {
    if (!isValid(catType, draft)) {
      setErr(catType === 'promise'
        ? ((draft.tier === 'arc' || draft.tier === 'book') ? '卷级和书级伏笔必须填写作者存档的真实答案' : '请填写伏笔内容')
        : catType === 'proposition' ? '请填写主体、属性、值,生效章须为 ≥1 的章号' : '请填写名称')
      return
    }
    setSaving(true); setErr('')
    try {
      const ref = await createRecord(catType, draft)
      onCreated?.(catType, ref)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '创建失败')
      setSaving(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <div className="flex items-center gap-3 mb-1">
          {onCancel && <button onClick={onCancel} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
          <span className="text-meta text-faint/50">新建{label || ''}</span>
        </div>
        {/* DetailView 在 isNew 模式:onUpdate 只改内存草稿,不落库;onDelete 即取消 */}
        <DetailView
          type={type}
          row={draft}
          isNew
          onBack={null}
          onUpdate={(updated) => setDraft(updated)}
          onDelete={onCancel}
        />
        {/* 校验/创建错误以 alert 语义呈现(屏读即时播报),信息如实来自校验规则或后端 detail */}
        {err && <div role="alert" className="mt-3 text-f12 text-danger">{err}</div>}
        <div className="mt-4 pt-3 border-t border-line flex items-center gap-2">
          <Btn variant="primary" onClick={create} disabled={saving}>
            {saving && <Loader2 size={14} className="animate-spin" />}创建
          </Btn>
          {onCancel && <Btn variant="ghost" onClick={onCancel} disabled={saving}>取消</Btn>}
        </div>
      </div>
    </div>
  )
}

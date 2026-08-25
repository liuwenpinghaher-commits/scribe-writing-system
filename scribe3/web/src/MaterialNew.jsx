import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { api } from './api'
import { Btn } from './ui.jsx'
import { useToast } from './ui/Toast'
import { KIND_LABEL } from './materialKinds'
import { MaterialForm, parseTags } from './MaterialForm'

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

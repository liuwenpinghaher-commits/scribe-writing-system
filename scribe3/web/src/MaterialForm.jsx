import { RichEditor } from './editor/RichEditor'
import { Input } from './ui.jsx'
import { MATERIAL_KINDS } from './materialKinds'
import { handleSelAction } from './lib/selAction'

export const parseTags = (s) => String(s || '').split(/[,，]/).map((t) => t.trim()).filter(Boolean)
export const joinTags = (arr) => (Array.isArray(arr) ? arr : []).join(', ')

export function MaterialForm({ draft, onDraft, editorKey, showPinned = false }) {
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

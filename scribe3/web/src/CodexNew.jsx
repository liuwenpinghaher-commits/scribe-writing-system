import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { DetailView } from './views/CodexView'
import { Btn } from './ui.jsx'
import { isChapterNum } from './lib/utils'
import { seedChiefCodexCreate } from './lib/chiefSeed.js'

// 素材分类 ref → DetailView type
const CAT_TO_TYPE = {
  character: 'chars',
  faction: 'factions',
  item: 'items',
  term: 'terms',
  world_rule: 'rules',
  promise: 'promises',
  motif: 'motifs',
  proposition: 'facts',
}

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

function isValid(catType, d) {
  if (catType === 'promise') {
    const requiresResolution = d.tier === 'arc' || d.tier === 'book'
    return !!(d.text && d.text.trim() && (!requiresResolution || (d.resolution && d.resolution.trim())))
  }
  if (catType === 'proposition') {
    return !!(d.entity && d.entity.trim() && d.attribute && d.attribute.trim()
      && d.value && d.value.trim() && isChapterNum(d.valid_from))
  }
  return !!(d.name && d.name.trim())
}

/**
 * 设定新建:草稿仅内存;「提交主编写入」走 chief seed + MCP 待批。
 * 禁止表单直写 REST(emergency 默认关时 403 的死路径)。
 */
export function CodexNew({ catType, label, onCancel, onCreated }) {
  const type = CAT_TO_TYPE[catType]
  const [draft, setDraft] = useState(() => emptyDraft(catType))
  const [err, setErr] = useState('')
  const [seeded, setSeeded] = useState(false)

  if (!type) return <div className="p-6 text-f13 text-faint">未知设定类型:{catType}</div>

  const submitToChief = () => {
    if (!isValid(catType, draft)) {
      setErr(catType === 'promise'
        ? ((draft.tier === 'arc' || draft.tier === 'book')
          ? '卷级和书级伏笔必须填写作者存档的真实答案' : '请填写伏笔内容')
        : catType === 'proposition'
          ? '请填写主体、属性、值,生效章须为 ≥1 的章号'
          : '请填写名称')
      return
    }
    setErr('')
    seedChiefCodexCreate(catType, draft)
    setSeeded(true)
    // 不落库:批准后库变;父层可选 onCreated 仅作 UI 提示(无 ref)
    onCreated?.(catType, null)
  }

  return (
    <div className="h-full overflow-y-auto" data-testid="codex-new">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <div className="flex items-center gap-3 mb-1">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"
            >
              <ArrowLeft size={16} />返回
            </button>
          )}
          <span className="text-meta text-faint/50">新建{label || ''}</span>
        </div>
        <div
          role="status"
          data-testid="codex-new-dialogue-hint"
          className="mb-3 rounded border border-line bg-surface/60 px-3 py-2 text-meta text-faint leading-snug"
        >
          设定写入须经主编待批(s3_ 工具),不直连 REST。填完点下方按钮把草稿交给主编。
        </div>
        <DetailView
          type={type}
          row={draft}
          isNew
          onBack={null}
          onUpdate={(updated) => setDraft(updated)}
          onDelete={onCancel}
        />
        {err && <div role="alert" className="mt-3 text-f12 text-danger">{err}</div>}
        {seeded && (
          <div role="status" data-testid="codex-new-seeded" className="mt-3 text-f12 text-ok">
            已交给主编,请在右栏批准写入提案。
          </div>
        )}
        <div className="mt-4 pt-3 border-t border-line flex items-center gap-2">
          <Btn variant="primary" onClick={submitToChief} data-testid="codex-new-submit-chief">
            让主编写入(待批)
          </Btn>
          {onCancel && <Btn variant="ghost" onClick={onCancel}>取消</Btn>}
        </div>
      </div>
    </div>
  )
}

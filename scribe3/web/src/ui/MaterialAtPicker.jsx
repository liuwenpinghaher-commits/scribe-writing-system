import { AT_DOMAIN_LABEL } from '../lib/atCatalog.js'

const MATERIAL_KIND_LABEL = {
  research: '研究', reference: '参考', snippet: '片段',
  inspiration: '灵感', note: '笔记', emotion_module: '情绪卡',
}

const TYPE_LABEL = {
  character: '角色',
  faction: '势力',
  item: '物件',
  term: '术语',
  world_rule: '世界规则',
  promise: '伏笔',
  motif: '母题',
  material: '素材',
  chapter: '章',
  volume: '卷',
  view: '视图',
  event: '事件',
  arc: '弧光',
  relation: '关系',
  fact: '命题',
}

function domainBadge(item) {
  return AT_DOMAIN_LABEL[item?.domain] || '引用'
}

function typeLabel(item) {
  if (!item) return ''
  if (item.domain === 'material' || item.type === 'material') {
    return MATERIAL_KIND_LABEL[item.kind] || item.kind || '素材'
  }
  return TYPE_LABEL[item.type] || item.type || ''
}

/**
 * 主编 compose 的 @ 引用浮层（章节/视图/设定/事件/命题/素材）。
 */
export function MaterialAtPicker({
  open,
  query = '',
  items = [],
  loading = false,
  error = '',
  activeIndex = 0,
  onActiveIndexChange,
  onPick,
  'data-testid': testId = 'material-at-picker',
}) {
  if (!open) return null
  const list = Array.isArray(items) ? items : []

  return (
    <div
      role="listbox"
      aria-label="引用系统对象"
      data-testid={testId}
      className="absolute bottom-full left-0 right-0 mb-1 max-h-56 overflow-y-auto rounded-md border border-line bg-surface shadow-lg z-30"
    >
      <div className="sticky top-0 px-2.5 py-1.5 text-meta text-faint bg-surface border-b border-line/60">
        @ 引用全书对象{query ? ` · 「${query}」` : ''}
        {loading ? ' · 加载中…' : ` · ${list.length} 条`}
      </div>
      {error && (
        <div className="px-2.5 py-2 text-f12 text-danger" data-testid="material-at-error">{error}</div>
      )}
      {!loading && !error && list.length === 0 && (
        <div className="px-2.5 py-3 text-f12 text-faint" data-testid="material-at-empty">
          无匹配项。可试章节名、角色名、素材标题，或划选「存」写入素材。
        </div>
      )}
      {list.map((m, i) => {
        const key = m.key || m.refToken || m.id || i
        const active = i === activeIndex
        const badge = domainBadge(m)
        const kind = typeLabel(m)
        const title = m.title || m.label || m.refToken || key
        const sub = m.subtitle || m.source || ''
        return (
          <button
            key={String(key)}
            type="button"
            role="option"
            aria-selected={active}
            data-testid="material-at-option"
            data-domain={m.domain || ''}
            data-type={m.type || ''}
            data-active={active ? '1' : '0'}
            className={`w-full text-left px-2.5 py-1.5 text-f12 border-0 cursor-pointer ${
              active ? 'bg-brand/10 text-brand' : 'text-ink hover:bg-soft'
            }`}
            onMouseEnter={() => onActiveIndexChange?.(i)}
            onMouseDown={(e) => {
              e.preventDefault()
              onPick?.(m)
            }}
          >
            <span className="text-meta text-faint mr-1.5">{badge}</span>
            <span className="font-medium">{title}</span>
            {kind ? <span className="text-meta text-faint ml-1.5">{kind}</span> : null}
            {sub ? (
              <span className="block text-meta text-faint truncate mt-0.5">{sub}</span>
            ) : null}
          </button>
        )
      })}
      <div className="sticky bottom-0 px-2.5 py-1 text-meta text-faint bg-surface border-t border-line/60">
        ↑↓ 选择 · Enter 引用 · Esc 关闭 · 章/视图/设定/事件/命题/素材
      </div>
    </div>
  )
}

/** 键盘导航：循环 */
export function nextAtActiveIndex(cur, delta, len) {
  if (len <= 0) return 0
  return (cur + delta + len * 10) % len
}

export function normalizeMaterialRows(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

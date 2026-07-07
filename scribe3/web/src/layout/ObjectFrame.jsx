import { registry } from './objectRegistry'

// 通用对象模板(spec §4 地基):任何对象套同一插槽——
//   顶栏条 = 面包屑 › 对象名 + 对象横向 tab + 状态徽章;   中央 = 该对象详情(children 传入)。
// 详情组件在后续 Task4 按类型接现有组件(编辑器/CodexDetail/MaterialDetail);右侧辅助 tab 由 FourPane 组合。
// 未知类型友好兜底,不崩(spec §5-E 全状态有姿态的一部分)。
export function ObjectFrame({ type, obj, activeTab, onTab, children }) {
  const r = registry[type]
  if (!r) return <div className="p-6 text-f13 text-faint">未知对象类型:{type}</div>
  const tabs = r.tabs || []
  const cur = activeTab || tabs[tabs.length - 1]
  return (
    <div className="h-full flex flex-col">
      <div className="h-10 shrink-0 border-b border-line flex items-center gap-2 px-4">
        <span className="text-f11 text-faint truncate min-w-0">{r.crumb(obj)}</span>
        <div className="flex gap-0.5 ml-1 shrink-0">
          {tabs.map((t) => (
            <button key={t} onClick={() => onTab?.(t)}
              className={`px-2 py-0.5 rounded text-f12 whitespace-nowrap transition-colors ${t === cur ? 'bg-brand text-brandfg font-medium' : 'text-faint hover:text-ink'}`}>
              {t}
            </button>
          ))}
        </div>
        <span className="ml-auto text-f11 text-faint shrink-0">{r.status(obj)}</span>
      </div>
      <div className="flex-1 min-h-0 overflow-auto">{children}</div>
    </div>
  )
}

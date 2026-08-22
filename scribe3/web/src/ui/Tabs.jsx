import { useRef } from 'react'

export function Tabs({ value, onValueChange, items, ariaLabel }) {
  const tabsRef = useRef([])
  const move = (index, delta) => {
    if (!items.length) return
    const nextIndex = (index + delta + items.length) % items.length
    onValueChange(items[nextIndex].value)
    tabsRef.current[nextIndex]?.focus()
  }

  // roving tabindex 焦点锚:value 可为 null/无匹配(如章工作台辅助视图开着时阶段页签整体去激活)
  // ——此时按 WAI-ARIA 惯例让第一个 tab 收 tabIndex=0,tablist 保持键盘可达;有选中值时行为不变。
  const hasSelected = items.some((item) => item.value === value)
  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex items-center gap-0.5 rounded-md bg-soft/80 p-1">
      {items.map((item, index) => (
        <button
          key={item.value}
          ref={(node) => { tabsRef.current[index] = node }}
          type="button"
          role="tab"
          aria-selected={item.value === value}
          tabIndex={item.value === value || (!hasSelected && index === 0) ? 0 : -1}
          onClick={() => onValueChange(item.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') { event.preventDefault(); move(index, 1) }
            if (event.key === 'ArrowLeft') { event.preventDefault(); move(index, -1) }
          }}
          title={item.title || undefined}
          className="h-7 rounded-md px-2.5 text-helper text-faint transition-colors aria-selected:bg-surface aria-selected:text-brand aria-selected:shadow-sm"
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

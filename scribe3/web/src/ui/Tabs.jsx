import { useRef } from 'react'

export function Tabs({ value, onValueChange, items, ariaLabel }) {
  const tabsRef = useRef([])
  const move = (index, delta) => {
    if (!items.length) return
    const nextIndex = (index + delta + items.length) % items.length
    onValueChange(items[nextIndex].value)
    tabsRef.current[nextIndex]?.focus()
  }

  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex items-center gap-1 rounded-lg bg-soft p-1">
      {items.map((item, index) => (
        <button
          key={item.value}
          ref={(node) => { tabsRef.current[index] = node }}
          type="button"
          role="tab"
          aria-selected={item.value === value}
          tabIndex={item.value === value ? 0 : -1}
          onClick={() => onValueChange(item.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') { event.preventDefault(); move(index, 1) }
            if (event.key === 'ArrowLeft') { event.preventDefault(); move(index, -1) }
          }}
          className="h-8 rounded-md px-3 text-helper text-faint aria-selected:bg-surface aria-selected:text-brand aria-selected:ring-1 aria-selected:ring-line"
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

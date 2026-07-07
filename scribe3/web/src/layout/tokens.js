// 设计 token 单一真源(阶段1a)。值用 var() 引用现有 CSS 变量,不发明新值、不改观感。
// 目的:把散在各组件里手写的样式收敛到一处,后续新布局/组件统一引用,视觉才一致。
export const T = {
  color: {
    brand: 'var(--color-brand)', brandfg: 'var(--color-brandfg)',
    ink: 'var(--color-ink)', faint: 'var(--color-faint)', line: 'var(--color-line)',
    surface: 'var(--color-surface)', canvas: 'var(--color-canvas)', soft: 'var(--color-soft)',
  },
  radius: { sm: '6px', md: '8px', lg: '10px', xl: '12px' },
  space: { 1: '4px', 2: '8px', 3: '12px', 4: '16px', 6: '24px' },
  font: { f10: '10px', f11: '11px', f12: '12px', f13: '13px', f15: '15px', f18: '18px' },
  h: { input: '36px', bar: '46px', rail: '56px' },
}

// 字段类统一 className(承接已修的 CodexDetail 字段统一,推广全局:rounded-lg/h-9/px-3)
export const CX = {
  input: 'w-full rounded-lg border border-line bg-canvas px-3 h-9 text-f13 text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60',
  textarea: 'w-full rounded-lg border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 resize-y',
}

// 像素参考（设计意图）；实际栏宽由 layoutMode 百分比驱动。
// v8：目录约 18% / 详情 42% / 会话 40%（在常见 1280–1600 内容区接近下表 ideal）。
export const PC_LAYOUT = Object.freeze({
  topbar: 44,
  rail: 56,
  directory: { min: 200, ideal: 260, max: 320 },
  detail: { min: 480, ideal: 640 },
  right: { min: 320, ideal: 480, max: 560 },
})

// 设计 token 单一真源(阶段1a)。值用 var() 引用现有 CSS 变量,不发明新值、不改观感。
// 目的:把散在各组件里手写的样式收敛到一处,后续新布局/组件统一引用,视觉才一致。
export const T = {
  color: {
    brand: 'var(--color-brand)', brandfg: 'var(--color-brandfg)',
    ink: 'var(--color-ink)', faint: 'var(--color-faint)', line: 'var(--color-line)',
    surface: 'var(--color-surface)', canvas: 'var(--color-canvas)', soft: 'var(--color-soft)',
  },
  // 与 index.css --radius-* 对齐：控件 6 / 面板 8 / 略大 10
  radius: { sm: '4px', md: '6px', lg: '8px', xl: '10px', pane: 'var(--radius-pane)' },
  space: { 1: '4px', 2: '8px', 3: '12px', 4: '16px', 6: '24px' },
  font: {
    meta: 'var(--text-meta)',
    helper: 'var(--text-helper)',
    body: 'var(--text-body)',
    stage: 'var(--text-stage)',
    section: 'var(--text-section-title)',
    page: 'var(--text-page-title)',
    prose: 'var(--text-prose)',
    // 兼容旧 fNN 调用
    f10: '10px', f11: '11px', f12: '12px', f13: '13px', f15: '15px', f18: '17px',
  },
  h: { input: '36px', bar: '46px', rail: '56px' },
}

// 字段类统一 className(与 ui.jsx Input/Textarea variant 对齐)
// ghost=Notion 默认;bordered=新建/设置等常显表单
export const CX = {
  input: 'w-full rounded-md border border-transparent bg-transparent hover:bg-soft/50 px-3 h-9 text-f13 text-ink outline-none transition-colors focus:border-brand focus:bg-canvas placeholder:text-faint/60',
  inputBordered: 'w-full rounded-md border border-line bg-canvas px-3 h-9 text-f13 text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60',
  textarea: 'w-full rounded-md border border-transparent bg-transparent hover:bg-soft/50 px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand focus:bg-canvas placeholder:text-faint/60 resize-y',
  textareaBordered: 'w-full rounded-md border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 resize-y',
}

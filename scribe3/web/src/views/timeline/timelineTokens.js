export function tok(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export const palette = () => ({
  brand: tok('--color-brand', '#2f6b5d'),
  irony: tok('--color-irony', '#4f76a3'),
  secret: tok('--color-secret', '#9c5f86'),
  fore: tok('--color-fore', '#c2683a'),
  ok: tok('--color-ok', '#2f6b4f'),
  danger: tok('--color-danger', '#9d3838'),
  faint: tok('--color-faint', '#65706a'),
})

export const EVENT_TYPE_COLOR = () => {
  const p = palette()
  return {
    炼器: p.secret, 战斗: p.danger, 拜师: p.irony,
    对话: p.ok, 决策: p.fore, 失去: p.secret, 获得: p.ok,
  }
}

export const evColor = (t) => EVENT_TYPE_COLOR()[t] || palette().faint
export const ARC_COLORS = () => {
  const p = palette()
  return { ability: p.secret, relation: p.irony, personality: p.secret, composite: p.fore }
}
export const arcColor = (ct) => ARC_COLORS()[ct] || palette().faint
export const PROMISE_COLOR = () => palette().fore
export const PROMISE_HERRING = () => palette().faint
export const stripRole = (id) => (id || '').replace(/^role:/, '')
export const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
))

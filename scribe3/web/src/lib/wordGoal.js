/** 整稿目标字数：0 / 空 / 非数字一律回落，避免除零得到 Infinity。 */
export function safeWordGoal(n, fallback = 100000) {
  const v = Number(n)
  return Number.isFinite(v) && v > 0 ? v : fallback
}

/** 进度百分比：永远是有限数，夹在 0–100。 */
export function wordGoalPct(words, goal, fallback = 100000) {
  const g = safeWordGoal(goal, fallback)
  const w = Number(words)
  const ww = Number.isFinite(w) ? Math.max(0, w) : 0
  const pct = Math.round((ww / g) * 100)
  if (!Number.isFinite(pct)) return 0
  return Math.min(100, Math.max(0, pct))
}

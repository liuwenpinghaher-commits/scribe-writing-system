// 可复用改写指令按钮:按 work 隔离,存 localStorage(改造⑤)。
const key = (work) => `scribe3:rewriteBtns:${work}`
export function loadButtons(work) {
  try { return JSON.parse(localStorage.getItem(key(work)) || '[]') }
  catch { return [] }
}
export function addButton(work, label) {
  const t = (label || '').trim()
  if (!t) return loadButtons(work)
  const cur = loadButtons(work)
  if (cur.includes(t)) return cur
  const next = [...cur, t]
  localStorage.setItem(key(work), JSON.stringify(next))
  return next
}
export function removeButton(work, label) {
  const next = loadButtons(work).filter((x) => x !== label)
  localStorage.setItem(key(work), JSON.stringify(next))
  return next
}

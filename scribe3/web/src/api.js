// scribe3 后端 API(3321,CORS 放开)。前端读 NS=scribe3 + 驱动渲染。
const BASE = 'http://127.0.0.1:3321'
const j = (p) => fetch(BASE + p).then((r) => r.json())
const q = (s) => encodeURIComponent(s)
export const getEntities = () => j('/entities')
export const getFacts = (ch) => j(`/facts?chapter=${ch}`)
export const getEvents = (ch) => j(`/events?chapter=${ch}`)
export const getFrame = (foc, ch) => j(`/frame?focalizer=${q(foc)}&chapter=${ch}`)
export const getCausal = (ch) => j(`/causal?chapter=${ch}`)
export const getIrony = (foc, ch) => j(`/irony?focalizer=${q(foc)}&chapter=${ch}`)
export const postRender = (foc, ch) =>
  fetch(BASE + '/render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ focalizer: foc, chapter: ch }) }).then((r) => r.json())
// SSE:订阅 NS=scribe3 变更(改一处处处同步)。onChange 收到 {table} 即触发重取。
export const openLive = (onChange) => {
  const es = new EventSource(BASE + '/live')
  es.onmessage = (e) => { try { onChange(JSON.parse(e.data)) } catch (_) {} }
  return es
}
// 章节正文(manuscript)+ QC
export const getChapter = (seq) => j(`/chapter?seq=${seq}`)
export const getQc = (seq) => j(`/qc?seq=${seq}`)
export const saveChapter = (seq, prose, title, focalizer) =>
  fetch(BASE + '/save-chapter', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seq, prose, title, focalizer }) }).then((r) => r.json())
export const getPromises = () => j('/promises')

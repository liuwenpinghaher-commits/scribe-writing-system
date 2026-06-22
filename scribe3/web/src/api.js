// scribe3 后端 API(:3321,CORS 放开)。前端读 NS=scribe3 + 驱动渲染/QC/回写。
const BASE = 'http://127.0.0.1:3321'
const j = (p) => fetch(BASE + p).then((r) => r.json())
const q = (s) => encodeURIComponent(s)
const post = (p, body) => fetch(BASE + p, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: body ? JSON.stringify(body) : undefined,
}).then((r) => r.json())

export const api = {
  entities: () => j('/entities'),
  facts: (ch) => j(`/facts?chapter=${ch}`),
  events: (ch) => j(`/events?chapter=${ch}`),
  frame: (foc, ch) => j(`/frame?focalizer=${q(foc)}&chapter=${ch}`),
  irony: (foc, ch) => j(`/irony?focalizer=${q(foc)}&chapter=${ch}`),
  causal: (ch) => j(`/causal?chapter=${ch}`),
  promises: () => j('/promises'),
  motifs: () => j('/motifs'),
  recall: (text, k = 6) => j(`/recall?q=${q(text)}&k=${k}`),
  chapters: () => j('/chapters'),
  chapter: (seq) => j(`/chapter?seq=${seq}`),
  qc: (seq) => j(`/qc?seq=${seq}`),
  render: (foc, ch) => post('/render', { focalizer: foc, chapter: ch }),
  saveChapter: (seq, prose, title, focalizer) => post('/save-chapter', { seq, prose, title, focalizer }),
  ingest: (seq) => post(`/ingest?seq=${seq}`),
  live: (onChange) => {
    const es = new EventSource(BASE + '/live')
    es.onmessage = (e) => { try { onChange(JSON.parse(e.data)) } catch (_) { /* */ } }
    return es
  },
}

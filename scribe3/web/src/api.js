// scribe3 后端 API(:3321)· 多书:每次调用带当前 work(一书一 DB)。
const BASE = 'http://127.0.0.1:3321'
let WORK = 'main'
const enc = encodeURIComponent
const ww = (p) => p + (p.includes('?') ? '&' : '?') + 'work=' + enc(WORK)
const j = (p) => fetch(BASE + ww(p)).then((r) => r.json())
const jraw = (p) => fetch(BASE + p).then((r) => r.json())
const post = (p, body) => fetch(BASE + ww(p), {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: body ? JSON.stringify(body) : undefined,
}).then((r) => r.json())
const patch = (p, body) => fetch(BASE + ww(p), {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then((r) => r.json())
const del = (p) => fetch(BASE + ww(p), { method: 'DELETE' }).then((r) => r.json())
const put = (p, body) => fetch(BASE + ww(p), {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then((r) => r.json())

export const api = {
  setWork: (w) => { WORK = w },
  works: () => jraw('/works'),
  createWork: (title) => fetch(BASE + '/works', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  }).then((r) => r.json()),
  renameWork: (slug, title) => fetch(BASE + '/works/' + enc(slug), {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  }).then((r) => r.json()),
  deleteWork: (slug) => fetch(BASE + '/works/' + enc(slug), { method: 'DELETE' }).then((r) => r.json()),

  entities: () => j('/entities'),
  facts: (ch) => j(`/facts?chapter=${ch}`),
  events: (ch) => j(`/events?chapter=${ch}`),
  frame: (foc, ch) => j(`/frame?focalizer=${enc(foc)}&chapter=${ch}`),
  irony: (foc, ch) => j(`/irony?focalizer=${enc(foc)}&chapter=${ch}`),
  causal: (ch) => j(`/causal?chapter=${ch}`),
  promises: () => j('/promises'),
  motifs: () => j('/motifs'),
  graph: (chapter) => j('/graph' + (chapter ? `?chapter=${chapter}` : '')),
  quality: () => j('/quality'),
  intent: () => j('/intent'),
  putIntent: (b) => put('/intent', b),

  // 设定库增删改
  addChar: (b) => post('/characters', b),
  editChar: (local, b) => patch('/characters/' + enc(local), b),
  delChar: (local) => del('/characters/' + enc(local)),
  addFact: (b) => post('/facts', b),
  editFact: (local, b) => patch('/facts/' + enc(local), b),
  delFact: (local) => del('/facts/' + enc(local)),
  addPromiseNew: (b) => post('/promises-new', b),
  editPromise: (pid, b) => patch('/promises/' + enc(pid), b),
  delPromise: (pid) => del('/promises/' + enc(pid)),
  addMotifNew: (b) => post('/motifs-new', b),
  editMotif: (mid, b) => patch('/motifs/' + enc(mid), b),
  delMotif: (mid) => del('/motifs/' + enc(mid)),
  recall: (text, k = 6) => j(`/recall?q=${enc(text)}&k=${k}`),
  chapters: () => j('/chapters'),
  chapter: (seq) => j(`/chapter?seq=${seq}`),
  qc: (seq) => j(`/qc?seq=${seq}`),
  render: (foc, ch) => post('/render', { focalizer: foc, chapter: ch }),
  saveChapter: (seq, prose, title, focalizer) => post('/save-chapter', { seq, prose, title, focalizer }),
  ingest: (seq) => post(`/ingest?seq=${seq}`),
  live: (onChange) => {
    const es = new EventSource(BASE + ww('/live'))
    es.onmessage = (e) => { try { onChange(JSON.parse(e.data)) } catch (_) { /* */ } }
    return es
  },
}

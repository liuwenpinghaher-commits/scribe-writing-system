// scribe3 后端 API · 多书:每次调用带当前 work(一书一 DB)。
// 生产经 VITE_API_BASE 注入;开发缺省回退本机 :3321。
const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:3321'
let WORK = 'main'
const enc = encodeURIComponent
const ww = (p) => p + (p.includes('?') ? '&' : '?') + 'work=' + enc(WORK)

async function handle(res) {
  if (!res.ok) {
    let body = null
    try { body = await res.json() } catch { /* non-JSON error */ }
    throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, body })
  }
  return res.json()
}

const j = (p) => fetch(BASE + ww(p)).then(handle)
const jraw = (p) => fetch(BASE + p).then(handle)
const post = (p, body) => fetch(BASE + ww(p), {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: body ? JSON.stringify(body) : undefined,
}).then(handle)
const patch = (p, body) => fetch(BASE + ww(p), {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then(handle)
const del = (p) => fetch(BASE + ww(p), { method: 'DELETE' }).then(handle)
const put = (p, body) => fetch(BASE + ww(p), {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then(handle)

export const api = {
  setWork: (w) => { WORK = w },
  get: (p) => fetch(BASE + ww(p)).then(handle),
  del: (p) => fetch(BASE + ww(p), { method: 'DELETE' }).then(handle),
  post: (p, b) => post(p, b),
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
  saveChapter: (seq, prose, title, focalizer) => post('/save-chapter', { seq, prose, title, focalizer }),
  ingest: (seq) => post(`/ingest?seq=${seq}`),
  live: (onChange) => {
    const es = new EventSource(BASE + ww('/live'))
    es.onmessage = (e) => { try { onChange(JSON.parse(e.data)) } catch (_) { /* */ } }
    return es
  },
  chatWrite: (msg, { chapter = 1, focalizer = '', images = [], onDelta, onTool, onProposal, onDone, onError }) => {
    const ctrl = new AbortController()
    fetch(BASE + ww('/chat/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ msg, chapter, focalizer, images }),
      signal: ctrl.signal,
    }).then(async (res) => {
      if (!res.ok) { onError?.(`HTTP ${res.status}`); return }
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop() ?? ''
          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const payload = line.slice(5).trim()
            if (!payload) continue
            try {
              const d = JSON.parse(payload)
              if (d.delta) onDelta?.(d.delta)
              else if (d.tool) onTool?.(d.tool)
              else if (d.proposal) onProposal?.(d.proposal)
              else if (d.done) { onDone?.(); return }
              else if (d.error) { onError?.(d.error); return }
            } catch (_) { /* */ }
          }
        }
        onDone?.()
      } catch (e) {
        if (e.name !== 'AbortError') onError?.(e.message || '流中断')
      }
    }).catch((e) => {
      if (e.name !== 'AbortError') onError?.(e.message || '网络错误')
    })
    return ctrl
  },
  chatStream: (msg, { onDelta, onTool, onDone, onError, agentic }) => {
    const path = (agentic ? '/chat/agentic-stream' : '/chat/stream') + '?msg=' + enc(msg)
    const es = new EventSource(BASE + ww(path))
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.delta) onDelta(d.delta)
        else if (d.tool) { onTool && onTool(d.tool, d.tool_args) }
        else if (d.done) { es.close(); onDone() }
        else if (d.error) { es.close(); onError(d.error) }
      } catch (_) { /* */ }
    }
    es.onerror = () => { es.close(); onError('连接中断') }
    return es
  },
}

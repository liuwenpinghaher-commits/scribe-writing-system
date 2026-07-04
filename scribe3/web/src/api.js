// scribe3 后端 API · 多书:每次调用带当前 work(一书一 DB)。
// 生产经 VITE_API_BASE 注入;开发缺省回退本机 :3321。
const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:3321'
let WORK = 'main'
const enc = encodeURIComponent
// work 可选覆盖:缺省读模块全局 WORK;显式传入把 ?work= 钉死到指定书,
// 防止「保存构造 URL 瞬间 WORK 已被切书翻成别的书」而写错书(卸载兜底 flush 关键)。
const ww = (p, work) => p + (p.includes('?') ? '&' : '?') + 'work=' + enc(work ?? WORK)

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
const post = (p, body, work) => fetch(BASE + ww(p, work), {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: body ? JSON.stringify(body) : undefined,
}).then(handle)
const patch = (p, body, work) => fetch(BASE + ww(p, work), {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then(handle)
const del = (p) => fetch(BASE + ww(p), { method: 'DELETE' }).then(handle)
const put = (p, body) => fetch(BASE + ww(p), {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then(handle)

// 伏笔请求体:前端行数据用 `kind`,后端 PromIn 读 `promise_kind`。有 kind 时补一份 promise_kind
// 同值(不删 kind,后端忽略多余字段),避免整行回传时 promise_kind 缺省 'promise' 覆盖 red_herring。
const promKindOut = (b) =>
  (b && typeof b === 'object' && b.kind !== undefined) ? { ...b, promise_kind: b.kind } : b

export const api = {
  setWork: (w) => { WORK = w },
  getWork: () => WORK,
  get: (p) => fetch(BASE + ww(p)).then(handle),
  del: (p) => fetch(BASE + ww(p), { method: 'DELETE' }).then(handle),
  post: (p, b) => post(p, b),
  works: () => jraw('/works'),
  createWork: (title) => fetch(BASE + '/works', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  }).then(handle),
  renameWork: (slug, title) => fetch(BASE + '/works/' + enc(slug), {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  }).then(handle),
  deleteWork: (slug) => fetch(BASE + '/works/' + enc(slug), { method: 'DELETE' }).then(handle),

  entities: () => j('/entities'),
  facts: (ch) => j(`/facts?chapter=${ch}`),
  events: (ch) => j(`/events?chapter=${ch}`),
  frame: (foc, ch) => j(`/frame?focalizer=${enc(foc)}&chapter=${ch}`),
  irony: (foc, ch) => j(`/irony?focalizer=${enc(foc)}&chapter=${ch}`),
  // 批D P1-5:返回 {no_event_data: bool, violations: [{event, reason}]}(非裸 list)。
  // 消费端经 causalStatus 归一化三态,勿对结果直接 .length(见 WriteLayout / causalStatus.js)。
  causal: (ch) => j(`/causal?chapter=${ch}`),
  promises: () => j('/promises'),
  promisesLedger: () => j('/promises/ledger'),
  motifs: () => j('/motifs'),
  motifInstances: (ch) => j(`/motif-instances?chapter=${ch}`),
  graph: (opts = {}) => {
    const { chapter, focus, limit, hop } = typeof opts === 'object' && opts !== null ? opts : { chapter: opts }
    const qs = []
    if (chapter != null) qs.push('chapter=' + enc(chapter))
    if (focus != null && focus !== '') qs.push('focus=' + enc(focus))
    if (limit != null) qs.push('limit=' + enc(limit))
    if (hop != null) qs.push('hop=' + enc(hop))
    return j('/graph' + (qs.length ? '?' + qs.join('&') : ''))
  },
  // axis: 'story'(故事编年,默认)| 'narrative'(叙事顺序);完整期双轴(spec §3.1)
  timeline: (from = 1, to, axis) => j('/timeline?ch_from=' + from
    + (to != null ? '&ch_to=' + to : '')
    + (axis ? '&axis=' + enc(axis) : '')),
  quality: () => j('/quality'),
  intent: () => j('/intent'),
  putIntent: (b) => put('/intent', b),
  progress: (window = 'all') => j('/progress?window=' + encodeURIComponent(window)),

  // 设定库增删改
  addChar: (b) => post('/characters', b),
  editChar: (local, b) => patch('/characters/' + enc(local), b),
  delChar: (local) => del('/characters/' + enc(local)),
  addFact: (b) => post('/facts', b),
  editFact: (local, b) => patch('/facts/' + enc(local), b),
  delFact: (local) => del('/facts/' + enc(local)),
  // 批D 件1:命题时态演进(限知引擎核心)。supersede=关闭同 entity+attribute 开区间先驱并写新值
  // (改命题值的时态正确路径,保历史);forget=令某 knower(默认 reader)从某章起不再知此命题。
  supersedeFact: (b) => post('/facts/supersede', b),
  forgetKnowledge: (b) => post('/knowledge/forget', b),
  // 批D 件2:角色关系(character_relation)—— GET 读 + 建立/演变/结束。relation 受控词表见 migration 029
  // (DB ASSERT 校验,越界值 500);src/dst 须带本体前缀(role:名),后端 _split/entity 依赖冒号。
  characterRelations: (chapter) => j('/character-relations' + (chapter != null ? `?chapter=${enc(chapter)}` : '')),
  addCharacterRelation: (b) => post('/character-relations', b),
  evolveRelation: (b) => post('/character-relations/evolve', b),
  endRelation: (b) => post('/character-relations/end', b),
  // 事件叙事位编辑(尾1):narrative_position=null 清除回退 story_chapter
  patchEventNarrative: (eid, narrative_position) =>
    patch('/events/' + enc(eid) + '/narrative', { narrative_position }),
  // 伏笔:前端统一用 `kind`(与 GET /promises 行数据、后端 DB 字段同名);但请求体模型 PromIn
  // 读 `promise_kind`(缺省 'promise')。整行回传编辑其它字段时,若不带 promise_kind → 后端把
  // red_herring 静默重置为 promise(P1-3)。此处在线上把 kind 转译为 promise_kind,保留原值。
  addPromiseNew: (b) => post('/promises-new', promKindOut(b)),
  editPromise: (pid, b) => patch('/promises/' + enc(pid), promKindOut(b)),
  delPromise: (pid) => del('/promises/' + enc(pid)),
  advancePromise: (pid, payoff_chapter) => post('/promises/' + enc(pid) + '/advance', { payoff_chapter }),
  markHerring: (pid) => post('/promises/' + enc(pid) + '/mark-herring'),
  addPromiseClue: (pid, note, chapter) => post('/promises/' + enc(pid) + '/clues', { note, chapter }),
  removePromiseClue: (pid, idx) => del('/promises/' + enc(pid) + '/clues/' + idx),
  addMotifNew: (b) => post('/motifs-new', b),
  editMotif: (mid, b) => patch('/motifs/' + enc(mid), b),
  delMotif: (mid) => del('/motifs/' + enc(mid)),
  // 工艺引擎(P0 露出):章前简报 / 角色弧光锚 / 弧光里程碑 / 张力检查(镜像既有方法,work 走 ww 惯例)
  northStarChapter: (seq) => j(`/north-star/chapter/${seq}`),   // 北极星任务10:章级 scorecard
  northStarBook: () => j('/north-star/book'),                   // 北极星任务10:书级四维
  chapterBrief: (seq, focalizer = '') => j(`/chapter-brief?seq=${seq}` + (focalizer ? `&focalizer=${enc(focalizer)}` : '')),
  charAnchors: (id) => j(`/char-anchors?character_id=${enc(id)}`),
  patchCharAnchors: (id, anchors) => patch('/char-anchors', { character_id: id, anchors }),
  postArcBeat: (b) => post('/arc-beats', b),
  delArcBeat: (id) => del('/arc-beats/' + enc(id)),
  charStates: (id) => j(`/char-states?character_id=${enc(id)}`),
  // 声音演变后半环(P1-11 消费端):列全书 open flags(前端按角色过滤)/ 单条 resolve / 一键折叠进 voice_profile。
  // ⚠ 后端无 GET voice_profile 端点——演化后的声线指纹只在 /voice-flags/fold 的响应里返回(见 CharVoice)。
  // fold 的 character_id 须带本体前缀(如 role:单嫣);后端 _split 依赖冒号,裸名会 500。
  voiceFlags: () => j('/voice-flags'),
  resolveVoiceFlag: (fid) => post('/voice-flags/' + enc(fid) + '/resolve'),
  foldVoiceFlags: (characterId) => post('/voice-flags/fold', { character_id: characterId }),
  // POST 但只读(登记在后端 KNOWN_REST_WRITE_ROUTES);rubric 走 LLM 可能慢,调用方给 loading 态
  tensionCheck: (seq) => post(`/tension-check?seq=${seq}`),
  // 素材库(非正典材料;镜像 motif 方法组)
  materials: (kind) => j('/materials' + (kind ? `?kind=${enc(kind)}` : '')),
  addMaterial: (b) => post('/materials', b),
  editMaterial: (mid, b) => patch('/materials/' + enc(mid), b),
  delMaterial: (mid) => del('/materials/' + enc(mid)),
  listUnverified: (status = 'pending') => j(`/ingest-unverified?status=${enc(status)}`),
  acceptUnverified: (id) => api.post('/ingest-unverified/' + enc(id) + '/accept'),
  ignoreUnverified: (id) => api.post('/ingest-unverified/' + enc(id) + '/ignore'),
  recall: (text, k = 6) => j(`/recall?q=${enc(text)}&k=${k}`),
  chapters: () => j('/chapters'),
  projectTree: () => j('/project-tree'),
  outline: () => j('/outline'),
  // 拖拽重排:只改 sort_order(及 volume),不动 seq
  reorderChapters: (volume, order) => post('/chapters/reorder', { volume, order }),
  // 卷 CRUD
  listVolumes: () => j('/volumes'),
  addVolume: (title, sort_order = 0, color = null) => post('/volumes', { title, sort_order, color }),
  patchVolume: (vid, fields) => patch('/volumes/' + enc(vid), fields),
  deleteVolume: (vid) => del('/volumes/' + enc(vid)),
  // 改章梗概/卷/标签/标题(不碰正文/embedding/qc)
  // work 可选:大纲/节拍卸载兜底 flush 传入捕获的 work,钉死目标书,防切书写错书(F5,同 saveDraft/saveChapter)。
  patchChapter: (seq, b, work) => patch('/chapters/' + seq, b, work),
  // work 可选:演绎卸载兜底 flush 读现状(合并 deductions)时钉住目标书,防切书读错书(F6,同 patchChapter 钉书)。
  chapter: (seq, work) => fetch(BASE + ww(`/chapter?seq=${seq}`, work)).then(handle),
  // 四阶段草稿:存草稿(留 draft 版 + 写 chapter.draft)/ 取最新草稿(刷新恢复)
  // work 可选:卸载兜底 flush 传入捕获的 work,钉死目标书,防切书写错书。
  saveDraft: (seq, prose, summary = '', work) => post(`/save-draft?seq=${seq}`, { prose, summary }, work),
  latestDraft: (seq) => j(`/latest-draft?seq=${seq}`),
  qc: (seq) => j(`/qc?seq=${seq}`),
  // work 可选:卸载兜底 flush / 切章 persist 传入捕获的 work,钉死目标书,防切书写错书。
  saveChapter: (seq, prose, title, focalizer, work) => post('/save-chapter', { seq, prose, title, focalizer }, work),
  ingest: (seq) => post(`/ingest?seq=${seq}`),
  // 命名存档点 + 护栏校验(改造③④)
  checkpoint: (seq, prose, label = '', kind = 'checkpoint', qc = {}) =>
    post(`/checkpoint?seq=${seq}`, { prose, label, kind, qc }),
  chapterVersions: (seq) => j(`/chapter-versions?seq=${seq}`),
  chapterVersion: (vid) => j('/chapter-version/' + enc(vid)),
  checkProse: (seq, prose, focalizer = '') =>
    post(`/check?seq=${seq}`, { prose, focalizer }),
  postCheck: (seq, prose, focalizer = '', brief = '') =>
    post(`/post-check?seq=${seq}`, { prose, focalizer, brief }),
  // SSE /live:浏览器原生 EventSource 出错会立即无退避重连,易把 /live 连接数顶到
  // 后端 _LIVE_MAX(默认 5)触发 429 静默失败。这里自管重连:出错即 close,按指数退避
  // (1s→2s→4s→…封顶 30s)再开;连续失败到阈值给一次 toast 提示并停。
  // 返回 { close() } 与旧 EventSource.close() 调用点兼容。
  live: (onChange, { onGiveUp } = {}) => {
    let es = null
    let timer = null
    let attempt = 0
    let stopped = false
    const MAX_ATTEMPT = 6           // 约 1+2+4+8+16+30 ≈ 1 分钟后放弃
    const open = () => {
      if (stopped) return
      es = new EventSource(BASE + ww('/live'))
      es.onmessage = (e) => { attempt = 0; try { onChange(JSON.parse(e.data)) } catch (_) { /* */ } }
      es.onerror = () => {
        try { es.close() } catch (_) { /* */ }
        es = null
        if (stopped) return
        attempt += 1
        if (attempt > MAX_ATTEMPT) { onGiveUp?.(); return }
        const delay = Math.min(30000, 1000 * 2 ** (attempt - 1))
        clearTimeout(timer)
        timer = setTimeout(open, delay)
      }
    }
    open()
    return {
      close: () => {
        stopped = true
        clearTimeout(timer)
        try { es?.close() } catch (_) { /* */ }
      },
    }
  },
  chatWrite: (msg, { chapter = 1, focalizer = '', images = [], phase = '', onDelta, onTool, onProposalStart, onProposalChunk, onProposal, onDone, onError }) => {
    const ctrl = new AbortController()
    fetch(BASE + ww('/chat/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ msg, chapter, focalizer, images, phase }),
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
              else if (d.proposal_start) onProposalStart?.(d.proposal_start)
              else if (d.proposal_chunk) onProposalChunk?.(d.proposal_chunk)
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

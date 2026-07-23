// scribe3 后端 API · 多书:每次调用带当前 work(一书一 DB)。
// 生产经 VITE_API_BASE 注入;开发缺省回退同源 '/api'(vite.config server.proxy 转发到 :3321)。
// 同源缘由:直连跨端口 :3321 时,浏览器扩展/安全策略常在请求发出前拦截 POST(F12 里连
// 请求都看不到),而 GET 简单请求能过——表现为「GET 正常但选择环等 POST 请求未送达」。
// 走同源 /api 后浏览器眼里全是本源请求,跨端口/跨源/preflight/扩展拦截整类消失。
const BASE = import.meta.env.VITE_API_BASE ?? '/api'
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

const j = (p, work) => fetch(BASE + ww(p, work)).then(handle)
const jraw = (p) => fetch(BASE + p).then(handle)
const post = (p, body, work) => fetch(BASE + ww(p, work), {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: body ? JSON.stringify(body) : undefined,
}).then(handle)
// raw 变体(不挂 ?work=):设置中心/网关这组端点是**全局**配置(不按书隔离),
// 混入 work= 只是死参数,但会误导排查(看着像分书隔离实则无效)——照 jraw 惯例补齐。
const postRaw = (p, body) => fetch(BASE + p, {
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
const putRaw = (p, body) => fetch(BASE + p, {
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
  // 废弃箱(Task 3):/works/{slug} DELETE 已改为软删(移入废弃箱),真删走 purge。
  archivedWorks: () => jraw('/works/archived'),
  restoreWork: (slug) => fetch(BASE + '/works/' + enc(slug) + '/restore', { method: 'POST' }).then(handle),
  // purge 需带 confirm_title 请求体——顶层 del()/内部 del() 均不支持 body,故这里直写 fetch
  // (与本文件 createWork/renameWork/deleteWork 同款「works 全局端点,不挂 ?work=」写法一致)。
  purgeWork: (slug, confirm_title) => fetch(BASE + '/works/' + enc(slug) + '/purge', {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm_title }),
  }).then(handle),

  entities: () => j('/entities'),
  facts: (ch) => j(`/facts?chapter=${ch}`),
  events: (ch) => j(`/events?chapter=${ch}`),
  frame: (foc, ch) => j(`/frame?focalizer=${enc(foc)}&chapter=${ch}`),
  irony: (foc, ch) => j(`/irony?focalizer=${enc(foc)}&chapter=${ch}`),
  // 批D P1-5:返回 {no_event_data: bool, violations: [{event, reason}]}(非裸 list)。
  // 消费端经 causalStatus 归一化三态,勿对结果直接 .length(见 WriteLayout / causalStatus.js)。
  causal: (ch) => j(`/causal?chapter=${ch}`),
  promises: () => j('/promises'),
  promisesLedger: (work) => j('/promises/ledger', work),
  motifs: (work) => j('/motifs', work),
  motifInstances: (ch, work) => j(`/motif-instances?chapter=${ch}`, work),
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
  // 质量缓存由正文保存/回写时维护；规则升级或历史缓存过期时作者可显式刷新。
  refreshQuality: () => post('/quality/refresh', {}),
  // 质量决策纵向链:参考作品导入/指纹、章节评价与作者评分。
  referenceImport: (b) => post('/references/import', b),
  referenceFingerprints: (id) => j(`/references/${enc(id)}/fingerprints`),
  referenceGenerateFingerprint: (id, b) => post(`/references/${enc(id)}/fingerprints`, b),
  referenceApproveFingerprint: (id, b) => post(`/references/${enc(id)}/fingerprints/approve`, b),
  qualityEvaluation: (seq) => j(`/quality/evaluation?seq=${enc(seq)}`),
  qualityAuthorJudgment: (b) => post('/quality/author-judgment', b),
  intent: () => j('/intent'),
  /** 全量 intent(含叙事北极星)——emergency 关时 403;作者叙事请走主编 s3_set_intent */
  putIntent: (b) => put('/intent', b),
  /** 工程配额-only(字数目标/逾期);不经世界写闸 */
  putIntentGoals: (b) => put('/intent-goals', b),
  progress: (window = 'all') => j('/progress?window=' + encodeURIComponent(window)),

  // CX-Task 7:设定字段注册表元数据(只读)——前端据此渲染表单,不再硬编码字段清单。
  // 目前后端只注册了 'faction' 一个 kind(阶段1);其余四类未注册,调用会 404(调用方自行 fallback)。
  codexSchema: (kind) => j('/codex-schema/' + enc(kind)),
  // 通用实体关系(entity_relation,CX-Task 5):entity 传完整前缀 oid(如 faction:秘会);
  // truth 字段默认掩码(reveal_secret 不传即 false),前端不做 reveal 入口,照掩码原样显示。
  entityRelations: (entity) => j('/entity-relations' + (entity ? `?entity=${enc(entity)}` : '')),
  addEntityRelation: (b) => post('/entity-relations', b),
  delEntityRelation: (a, b) => del(`/entity-relations?a=${enc(a)}&b=${enc(b)}`),
  // 势力结构化一致性校验(只读,CX-Task 6):关系矛盾/核心圈超编/信物传承章超前/权力占比超100%。
  factionConsistency: () => j('/faction-consistency'),

  // 设定库增删改
  addChar: (b) => post('/characters', b),
  editChar: (local, b) => patch('/characters/' + enc(local), b),
  delChar: (local, token = '') => del('/characters/' + enc(local) + (token ? `?confirm_impact_token=${enc(token)}` : '')),
  addFact: (b) => post('/facts', b),
  editFact: (local, b) => patch('/facts/' + enc(local), b),
  delFact: (local, token = '') => del('/facts/' + enc(local) + (token ? `?confirm_impact_token=${enc(token)}` : '')),
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
  // 断头修复 P1-9:物品状态变更端点(记 state_history)此前前端零调用方
  itemState: (name, state, chapter, reason) => post('/items/' + enc(name) + '/state', { state, chapter, reason }),
  // 断头修复#22:草稿轻量质检(后端全绿、前端此前零调用)
  draftCheck: (seq, prose, focalizer) => post(`/draft-check?seq=${seq}`, { prose, focalizer }),
  addMotifNew: (b) => post('/motifs-new', b),
  editMotif: (mid, b) => patch('/motifs/' + enc(mid), b),
  delMotif: (mid) => del('/motifs/' + enc(mid)),
  // 工艺引擎(P0 露出):章前简报 / 角色弧光锚 / 弧光里程碑 / 张力检查(镜像既有方法,work 走 ww 惯例)
  selectChapter: (seq, force = false) => post('/select/chapter', { chapter: seq, force }),   // 北极星任务11:关键章 3 候选(force=非关键章确认后越过)
  selectFinalize: (seq, payload) => post('/select/finalize', { chapter: seq, ...payload }),   // 终选+理由入 lesson
  northStarChapter: (seq) => j(`/north-star/chapter/${seq}`),   // 北极星任务10:章级 scorecard
  northStarBook: () => j('/north-star/book'),                   // 北极星任务10:书级四维
  chapterBrief: (seq, focalizer = '') => j(`/chapter-brief?seq=${seq}` + (focalizer ? `&focalizer=${enc(focalizer)}` : '')),
  chapterPulse: (seq) => j(`/chapter-pulse?seq=${seq}`),   // 主编主动化 T1:六维脉搏
  inbox: (seq) => j('/inbox' + (seq != null ? `?seq=${seq}` : '')),   // T4:决策收件箱
  // Chapter Pilot(主编主动化 T6-T11)
  pilotStep: (seq, mode = 'manual', steer = '') => post('/pilot/step', { seq, mode, steer }),
  pilotApprove: (seq, expect_state = '') => post('/pilot/approve', { seq, expect_state }),   // R1-3:带 expect_state 知情背书,防 stale 误触终选
  pilotStatus: (seq) => j(`/pilot/status?seq=${seq}`),
  pilotRun: (start_seq, until_seq) => post('/pilot/run', { start_seq, until_seq }),
  pilotPause: () => post('/pilot/pause'),
  pilotRunStatus: () => j('/pilot/run-status'),
  pilotDismiss: (seq) => post('/pilot/dismiss', { seq }),         // R1-4:pilot 僵尸态退出
  pilotResetStep: (seq) => post('/pilot/reset-step', { seq }),   // R1-4:stalled/parked 解卡重跑当前步
  // Hermes Runs/Approval:长任务事件流 + 人类审批闭环
  // H-10 全系统预算:日帽(app+MCP 共享台账)+ token 真实用量(trace 聚合)
  aiUsage: (days = 7) => j(`/ai/usage?days=${days}`),
  aiRunCreate: (body) => post('/ai/runs', body),
  aiRunStatus: (runId) => j('/ai/runs/' + enc(runId)),
  aiRunTrace: (runId) => j('/ai/runs/' + enc(runId) + '/trace'),
  aiRunApproval: (runId, body) => post('/ai/runs/' + enc(runId) + '/approval', body),
  aiRunStop: (runId) => post('/ai/runs/' + enc(runId) + '/stop'),
  aiRunEvents: (runId, {
    onDelta, onTool, onToolOutput, onApproval, onApprovalResolved, onRun, onDone, onError,
  } = {}) => {
    const es = new EventSource(BASE + ww('/ai/runs/' + enc(runId) + '/events'))
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.delta) onDelta?.(d.delta)
        else if (d.tool) onTool?.(d.tool, d.tool_args)
        else if (d.tool_output) onToolOutput?.(d.tool_output, d.tool_call_id)
        else if (d.approval) onApproval?.(d.approval)
        else if (d.approval_resolved) onApprovalResolved?.(d.approval_resolved)
        else if (d.run) onRun?.(d.run)
        else if (d.done) { es.close(); onDone?.() }
        else if (d.error) { es.close(); onError?.(d.error) }
      } catch (_) { /* */ }
    }
    es.onerror = () => { es.close(); onError?.('连接中断') }
    return es
  },
  runWrite: (input, {
    instructions = '', context = null, onDelta, onTool, onToolOutput, onApproval, onApprovalResolved, onRun, onDone, onError,
  } = {}) => {
    let es = null
    let runId = null
    let stopped = false
    // Task 13:发起时上下文绑定(会话/版本)随创建带上,后端据此快照 origin focus/hash
    // 供审批重校验;未传 context(存量/非线程)→ body 保持 {input, instructions} 不变。
    const body = { input, instructions }
    if (context) {
      if (context.context_session_id != null) body.context_session_id = context.context_session_id
      if (context.context_revision != null) body.context_revision = context.context_revision
    }
    api.aiRunCreate(body).then((run) => {
      if (stopped) return
      runId = run?.run_id || run?.id
      if (!runId) throw new Error('Hermes Run 未返回 run_id')
      onRun?.({ ...run, run_id: runId })
      es = api.aiRunEvents(runId, {
        onDelta, onTool, onToolOutput, onApproval, onApprovalResolved, onRun,
        onDone: () => { es = null; onDone?.() },
        onError,
      })
    }).catch((e) => {
      if (!stopped) onError?.(e?.body?.detail || e?.message || 'Hermes Run 创建失败')
    })
    const stop = () => {
      stopped = true
      try { es?.close?.() } catch (_) { /* */ }
      if (runId) api.aiRunStop(runId).catch(() => {})
    }
    return { abort: stop, close: stop }
  },
  // 统一上下文(Task 4):快照头三件套——与 body 字段(context_session_id/
  // context_revision/context_hash)**等价的绑定通道**:后端 enforce 逐字段取
  // body、缺失时回退这些请求头,两通道都缺才 400。后续所有 LLM 调用逐步换用。
  // 过期时后端 409 {detail:{code:'stale_context', latest}},handle 已把 body 挂上
  // error,消费端读 error.body.detail.code / .latest 直接对齐,无需再读一次。
  contextHeaders: (snapshot) => ({
    'X-Scribe-Context-Session': snapshot.session_id,
    'X-Scribe-Context-Revision': String(snapshot.revision),
    'X-Scribe-Context-Hash': snapshot.context_hash,
  }),
  createContextSession: (body) => post('/context/sessions', body),
  contextSession: (id) => j('/context/sessions/' + enc(id)),
  navigateContext: (id, intent) => post('/context/sessions/' + enc(id) + '/navigate', intent),
  contextSnapshot: (id, revision) => j('/context/sessions/' + enc(id) + '/snapshots/' + revision),
  // Task 14:某快照版本的记忆溯源 trace(上下文检查器数据源)。该版本暂无溯源 → 404
  // memory_trace_not_found(检索生产接线待 Task 16),检查器据此显"未检索到证据"。
  getMemoryTrace: (id, revision) => j('/context/sessions/' + enc(id) + '/trace/' + revision),
  // 运行时降级状态(Hermes 离线/只读判定源);全局端点,不带 work。
  aiRuntimeStatus: () => jraw('/ai/runtime-status'),
  // 能力下发:前端以后端 capabilities 为准(不靠 localStorage 开服务端能力)。
  // 全局端点,不带 work;回 { flags:{snapshot_v1,editorial_thread_v1,memory_fabric_v1,
  // context_inspector_v1,assembler_v1}, versions:{...} }；assembler_v1 恒 true。
  // 产品默认:snapshot/fabric/inspector 开。
  fetchCapabilities: () => jraw('/capabilities'),
  // 待审正典揭示(memory fabric 产品面):列队 + 批准/拒绝。
  listPendingClaims: (status = 'pending') =>
    j('/memory/pending-claims?status=' + enc(status || 'pending')),
  resolvePendingClaim: (claimId, body) =>
    post('/memory/pending-claims/' + enc(claimId) + '/resolve', body || {}),
  // Task 6:主编线程(一 work 一连续线程 + 每轮焦点标签)。
  // threads 列本 work 线程;threadMessages 拉某线程全部消息(切焦点不重载,由 ChiefDock 只调一次);
  // forkThread 显式分支(导航路径绝不调此)。
  threads: () => j('/chat/threads'),
  // P0b:opts={limit, before}——懒加载近窗 + 「载入更早」分页(before=最早一条的 ts)
  threadMessages: (id, opts = {}) => {
    const q = []
    if (opts.limit) q.push('limit=' + opts.limit)
    if (opts.before) q.push('before_ts=' + enc(opts.before))
    return j('/chat/threads/' + enc(id) + '/messages' + (q.length ? '?' + q.join('&') : ''))
  },
  exportThreadUrl: (id, format = 'md') => BASE + ww('/chat/threads/' + enc(id) + '/export?format=' + format),
  forkThread: (id, body) => post('/chat/threads/' + enc(id) + '/fork', body || {}),
  createThread: (title) => post('/chat/threads', title ? { title } : {}),          // P0a:显式新建会话
  patchThread: (id, fields) => patch('/chat/threads/' + enc(id), fields),          // P0a:{title}|{status}
  resolveIdea: (id) => post('/ideas/resolve', { id }),           // R1-5:想法待批处理完出收件箱
  addIdea: (text) => post('/ideas', { text }),
  charAnchors: (id) => j(`/char-anchors?character_id=${enc(id)}`),
  patchCharAnchors: (id, anchors) => patch('/char-anchors', { character_id: id, anchors }),
  postArcBeat: (b) => post('/arc-beats', b),
  delArcBeat: (id) => del('/arc-beats/' + enc(id)),
  charStates: (id) => j(`/char-states?character_id=${enc(id)}`),
  // 声音演变后半环(P1-11 消费端):列全书 open flags(前端按角色过滤)/ 单条 resolve / 一键折叠进 voice_profile。
  // 注意 后端无 GET voice_profile 端点——演化后的声线指纹只在 /voice-flags/fold 的响应里返回(见 CharVoice)。
  // fold 的 character_id 须带本体前缀(如 role:单嫣);后端 _split 依赖冒号,裸名会 500。
  voiceFlags: () => j('/voice-flags'),
  resolveVoiceFlag: (fid) => post('/voice-flags/' + enc(fid) + '/resolve'),
  foldVoiceFlags: (characterId) => post('/voice-flags/fold', { character_id: characterId }),
  // POST 但只读(登记在后端 KNOWN_REST_WRITE_ROUTES);rubric 走 LLM 可能慢,调用方给 loading 态
  tensionCheck: (seq) => post(`/tension-check?seq=${seq}`),
  // 素材库(非正典材料;镜像 motif 方法组)
  materials: (arg) => {
    const opts = arg && typeof arg === 'object' ? arg : { kind: arg }
    const qs = []
    if (opts.kind) qs.push('kind=' + enc(opts.kind))
    if (opts.limit != null) qs.push('limit=' + enc(opts.limit))
    if (opts.cursor != null) qs.push('cursor=' + enc(opts.cursor))
    if (opts.view) qs.push('view=' + enc(opts.view))
    if (opts.q) qs.push('q=' + enc(opts.q))
    if (opts.origin) qs.push('origin=' + enc(opts.origin))
    return j('/materials' + (qs.length ? '?' + qs.join('&') : ''))
  },
  material: (mid) => j('/materials/' + enc(mid)),
  materialsHealth: () => j('/materials/health'),
  addMaterial: (b) => post('/materials', b),
  /** 作者选区/会话私人剪藏(闸外 POST /author/session-clips；不经主编审批) */
  addSessionClip: (b) => post('/author/session-clips', b),
  editMaterial: (mid, b) => patch('/materials/' + enc(mid), b),
  delMaterial: (mid, token = '') => del('/materials/' + enc(mid) + (token ? `?confirm_impact_token=${enc(token)}` : '')),
  objectImpact: (type, id) => j('/objects/' + enc(type) + '/' + enc(id) + '/impact'),
  deleteObject: (type, id, token = '') => del('/objects/' + enc(type) + '/' + enc(id) + (token ? `?confirm_impact_token=${enc(token)}` : '')),
  archiveObject: (type, id) => post('/objects/' + enc(type) + '/' + enc(id) + '/archive'),
  // 素材记忆:三通道召回搜索 + 双向溯源 + 多格式导入
  materialRecall: (q, chapter, withMeta = false) => j(
    '/materials/recall?q=' + enc(q)
    + (chapter != null ? '&chapter=' + chapter : '')
    + (withMeta ? '&with_meta=true' : '')),
  materialRefs: (mid) => j('/materials/' + enc(mid) + '/refs'),
  materialRefsByChapter: (ch) => j('/materials/refs-by-chapter?chapter=' + ch),
  addMaterialReference: (mid, body) => post('/materials/' + enc(mid) + '/refs', body),
  materialGraph: (opts = {}) => {
    const qs = []
    if (opts.focus != null && opts.focus !== '') qs.push('focus=' + enc(opts.focus))
    if (opts.limit != null) qs.push('limit=' + enc(opts.limit))
    if (opts.hop != null) qs.push('hop=' + enc(opts.hop))
    return j('/materials/graph' + (qs.length ? '?' + qs.join('&') : ''))
  },
  materialImport: (formData) => fetch(BASE + ww('/materials/import'), { method: 'POST', body: formData }).then(handle),
  materialImportPreview: (jobId) => j('/materials/import/' + enc(jobId) + '/preview'),
  materialImportCommit: (jobId, items) => post('/materials/import/' + enc(jobId) + '/commit', { items }),
  materialImportProgressUrl: (jobId) => BASE + ww('/materials/import/' + enc(jobId) + '/progress'),
  search: (q) => j('/search?q=' + enc(q)),
  issues: (chapter) => j('/issues' + (chapter != null ? `?chapter=${enc(chapter)}` : '')),
  listUnverified: (status = 'pending') => j(`/ingest-unverified?status=${enc(status)}`),
  acceptUnverified: (id) => api.post('/ingest-unverified/' + enc(id) + '/accept'),
  ignoreUnverified: (id) => api.post('/ingest-unverified/' + enc(id) + '/ignore'),
  ignoreAllUnverified: (status = 'pending') => api.post('/ingest-unverified/ignore-all' + (status ? `?status=${enc(status)}` : '')),   // R2-12:批量清死水
  recall: (text, k = 6) => j(`/recall?q=${enc(text)}&k=${k}`),
  chapters: () => j('/chapters'),
  archivedChapters: () => j('/chapters/archived'),
  createChapter: (body = {}) => post('/chapters', body),
  archiveChapter: (seq, reason = '') => post('/chapters/' + seq + '/archive', { reason }),
  restoreChapter: (seq) => post('/chapters/' + seq + '/restore'),
  chapterImpact: (seq) => j('/chapters/' + seq + '/impact'),
  deleteChapter: (seq, token = '') => del('/chapters/' + seq + (token ? `?confirm_impact_token=${enc(token)}` : '')),
  projectTree: () => j('/project-tree'),
  outline: () => j('/outline'),
  // 拖拽重排:只改 sort_order(及 volume),不动 seq
  reorderChapters: (volume, order) => post('/chapters/reorder', { volume, order }),
  // 卷 CRUD
  listVolumes: () => j('/volumes'),
  addVolume: (title, sort_order = 0, color = null, intro = null) => post('/volumes', { title, sort_order, color, intro }),
  patchVolume: (vid, fields) => patch('/volumes/' + enc(vid), fields),
  deleteVolume: (vid) => del('/volumes/' + enc(vid)),
  // 改章梗概/卷/标签/标题(不碰正文/embedding/qc)
  // work 可选:大纲/节拍卸载兜底 flush 传入捕获的 work,钉死目标书,防切书写错书(F5,同 saveDraft/saveChapter)。
  patchChapter: (seq, b, work) => patch('/chapters/' + seq, b, work),
  // work 可选:演绎卸载兜底 flush 读现状(合并 deductions)时钉住目标书,防切书读错书(F6,同 patchChapter 钉书)。
  chapter: (seq, work) => fetch(BASE + ww(`/chapter?seq=${seq}`, work)).then(handle),
  // 角色投影只能以服务端场景真相为证据审查；客户端不传 source，避免伪造事实来源。
  validateDeduction: (seq, candidate, characterId = '', work) => post(
    `/chapters/${seq}/deductions/grounding`, { candidate, character_id: characterId }, work),
  // 两次自由生成仍越界时，取服务端场景真相逐字编排的安全兜底稿；该端点不写库。
  groundedDeductionFallback: (seq, characterId, work) => j(
    `/chapters/${seq}/deductions/grounded-fallback?character_id=${enc(characterId)}`, work),
  // 四阶段草稿:存草稿(留 draft 版 + 写 chapter.draft)/ 取最新草稿(刷新恢复)
  // work 可选:卸载兜底 flush 传入捕获的 work,钉死目标书,防切书写错书。
  saveDraft: (seq, prose, summary = '', work) => post(`/save-draft?seq=${seq}`, { prose, summary }, work),
  latestDraft: (seq) => j(`/latest-draft?seq=${seq}`),
  qc: (seq, work) => j(`/qc?seq=${seq}`, work),
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
  chatWrite: (msg, { chapter = 1, focalizer = '', images = [], phase = '', context = null, onDelta, onTool, onToolOutput, onProposalStart, onProposalChunk, onProposal, onApproval, onApprovalResolved, onDone, onError }) => {
    const ctrl = new AbortController()
    // Task 6:context 为线程模式下的绑定/焦点(thread_id/context_*/focus),
    // 逐字段并入请求体(后端 ChatWriteReq 全 optional,不传即现状)。
    const body = { msg, chapter, focalizer, images, phase, ...(context || {}) }
    fetch(BASE + ww('/chat/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
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
              else if (d.tool_output) onToolOutput?.(d.tool_output, d.tool_call_id)
              else if (d.proposal_start) onProposalStart?.(d.proposal_start)
              else if (d.proposal_chunk) onProposalChunk?.(d.proposal_chunk)
              else if (d.proposal) onProposal?.(d.proposal)
              else if (d.approval) onApproval?.(d.approval)
              else if (d.approval_resolved) onApprovalResolved?.(d.approval_resolved)
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
  chatStream: (msg, { onDelta, onTool, onToolOutput, onApproval, onApprovalResolved, onDone, onError, agentic, seq, thread }) => {
    // seq(时机C):讨论章号,后端据此注入脉搏速览,主编讨论时主动带出确定性信号
    // thread(P0a 多会话):显式会话线程;缺省=后端 active 默认线程(文档化默认,非降级)
    const path = (agentic ? '/chat/agentic-stream' : '/chat/stream') + '?msg=' + enc(msg)
      + (seq != null ? `&seq=${seq}` : '')
      + (thread ? `&thread=${enc(thread)}` : '')
    const es = new EventSource(BASE + ww(path))
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.delta) onDelta(d.delta)
        else if (d.tool) { onTool && onTool(d.tool, d.tool_args) }
        else if (d.tool_output) onToolOutput?.(d.tool_output, d.tool_call_id)
        else if (d.approval) onApproval?.(d.approval)
        else if (d.approval_resolved) onApprovalResolved?.(d.approval_resolved)
        else if (d.done) { es.close(); onDone() }
        else if (d.error) { es.close(); onError(d.error) }
      } catch (_) { /* */ }
    }
    es.onerror = () => { es.close(); onError('连接中断') }
    return es
  },
  // ── 统一设置中心 ──(全局端点,不按书隔离,一律走 raw 变体,不挂 ?work=)
  settings: () => jraw('/settings'),
  putSetting: (key, value) => putRaw('/settings/' + enc(key), { value }),
  resetSetting: (key) => postRaw('/settings/' + enc(key) + '/reset'),
  settingsAudit: (offset = 0) => jraw('/settings/audit?offset=' + offset),
  gatewayStatus: () => jraw('/gateway/status'),
  gatewayFiles: () => jraw('/gateway/files'),
  putGatewayFile: (id, content, base_sha256) => putRaw('/gateway/files', { id, content, base_sha256 }),
  gatewayRestart: (profile) => postRaw('/gateway/restart', { profile }),
  dashboardStatus: () => jraw('/gateway/dashboard/status'),
  dashboardStart: () => postRaw('/gateway/dashboard/start', {}),
  gatewayModelSummary: () => jraw('/gateway/model-summary'),
}

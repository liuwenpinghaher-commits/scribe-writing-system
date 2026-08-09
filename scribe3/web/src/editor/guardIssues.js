// F-05 完整:护栏 issue 的辅助纯函数——类别标签、忽略持久化、句边界扩展。

export const ISSUE_LABEL = {
  repetition: '复读',
  cross_rep: '跨章复读',
  structural: '结构重复',
  purple: '升华/抒情',
  ai_tics: 'AI腔',
  oversaturation: '过饱和',
  leak: '穿帮泄露',
  discipline: '纪律违规',
  setting: '设定校验',
  pressure: '压力节奏',
}

export function issueLabel(type) {
  return ISSUE_LABEL[type] || '问题'
}

// 圆点配色:与 index.css 六类语义色对齐(用于面板/悬浮卡圆点)。
export const ISSUE_DOT = {
  repetition: 'bg-amber-500',
  cross_rep: 'bg-amber-500',
  structural: 'bg-sky-500',
  purple: 'bg-purple-500',
  ai_tics: 'bg-gray-400',
  oversaturation: 'bg-orange-500',
  leak: 'bg-danger',
  discipline: 'bg-danger',
  setting: 'bg-warn',
  pressure: 'bg-brand',
}

export function issueDot(type) {
  return ISSUE_DOT[type] || 'bg-warn'
}

// ── 忽略持久化:按 (prose 指纹 + issue key) 存 localStorage ──

// 轻量 prose hash(djb2),用于把"忽略"绑定到当前正文版本。
function hashProse(prose) {
  let h = 5381
  const s = prose || ''
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0
  return h.toString(36)
}

// issue 的稳定 key:type + text(不含易变的 range/id)。
export function issueKey(issue) {
  return `${issue?.type || '?'}::${(issue?.text || '').slice(0, 40)}`
}

const STORE_KEY = 'scribe3:guardIgnored'

function readStore() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}') } catch { return {} }
}

function writeStore(obj) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(obj)) } catch { /* 存满忽略 */ }
}

// 把某 issue 在当前 prose 下标记为忽略。
export function ignoreIssue(prose, issue) {
  const bucket = hashProse(prose)
  const store = readStore()
  const set = new Set(store[bucket] || [])
  set.add(issueKey(issue))
  store[bucket] = [...set]
  writeStore(store)
}

// 取当前 prose 下的已忽略 key 集合。
export function ignoredKeys(prose) {
  const store = readStore()
  return new Set(store[hashProse(prose)] || [])
}

// 过滤掉已忽略的 issues。
export function filterIgnored(prose, issues) {
  const ignored = ignoredKeys(prose)
  return (issues || []).filter((it) => !ignored.has(issueKey(it)))
}

// 把短语 range 扩到所属句边界(就近向两侧找 。!?！?\n),给主编完整上下文。
const SENT_END = new Set(['。', '!', '?', '！', '？', '\n'])
export function expandToSentence(prose, range) {
  if (!Array.isArray(range) || range.length < 2 || !prose) return range
  let [s, e] = range
  s = Math.max(0, Math.min(s, prose.length))
  e = Math.max(s, Math.min(e, prose.length))
  // 向左:到上一个句末标点之后
  let from = s
  while (from > 0 && !SENT_END.has(prose[from - 1])) from--
  // 向右:到下一个句末标点(含)
  let to = e
  while (to < prose.length && !SENT_END.has(prose[to])) to++
  if (to < prose.length && SENT_END.has(prose[to])) to++
  // 去掉两端空白
  while (from < to && /\s/.test(prose[from])) from++
  while (to > from && /\s/.test(prose[to - 1])) to--
  return [from, to]
}

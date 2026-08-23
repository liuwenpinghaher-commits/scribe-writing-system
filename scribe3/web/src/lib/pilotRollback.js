import { showToast } from '../ui/Toast.jsx'

const STATES = [
  'idle', 'outline_proposed', 'beats_ready', 'deduced',
  'drafting', 'checked', 'delivered', 'finalized',
]

const LABELS = {
  idle: '待开写',
  outline_proposed: '大纲待放行',
  beats_ready: '节拍就绪',
  deduced: '演绎就绪',
  drafting: '草稿中',
  checked: '体检过',
  delivered: '待终选',
  finalized: '已定稿',
}

/**
 * 同一章状态序号回退 → 告诉作者「被打回了」。
 * sessionStorage 去重，旅程页和顶栏胶囊不会连弹两次。
 */
export function maybeToastRollback(snap) {
  const lane = snap?.chapter_lane
  if (!lane || lane.seq == null || !lane.pilot_state) return false
  const key = `s3.pilot.prev:${snap.work || 'main'}`
  const cur = { seq: Number(lane.seq), state: String(lane.pilot_state) }
  let prev = null
  try {
    prev = JSON.parse(sessionStorage.getItem(key) || 'null')
  } catch { prev = null }
  try {
    sessionStorage.setItem(key, JSON.stringify(cur))
  } catch { /* */ }
  if (!prev || Number(prev.seq) !== cur.seq) return false
  const a = STATES.indexOf(String(prev.state))
  const b = STATES.indexOf(cur.state)
  if (a < 0 || b < 0 || b >= a) return false
  const from = LABELS[prev.state] || prev.state
  const to = LABELS[cur.state] || cur.state
  showToast(`第${cur.seq}章被打回：从「${from}」回到「${to}」`, { tone: 'warn' })
  return true
}

/**
 * 仅作离线降级 fallback。权威源是后端 snapshot.next_step.domain
 *（scribe3.director.NEXT_STEP_DOMAIN）。有网时应优先用后端字段。
 */
export function domainHintFromNext(nextId, phase) {
  const map = {
    set_intent: 'intent.northstar',
    seed_motifs: 'motif.manage',
    add_chapter: 'chapter.outline',
    start_outline: 'chapter.outline',
    approve_outline: 'chapter.outline',
    confirm_beats: 'chapter.beats',
    start_draft: 'chapter.deduce',
    revise_draft: 'chapter.draft',
    handle_check: 'chapter.final',
    finalize_chapter: 'chapter.final',
    next_chapter: 'chapter.outline',
    book_complete: 'intent.northstar',
    unpark: phase ? `chapter.${phase}` : 'chapter.outline',
  }
  if (nextId && map[nextId]) return map[nextId]
  if (phase === 'design') return 'chapter.design'
  if (phase === 'outline') return 'chapter.outline'
  if (phase === 'beats') return 'chapter.beats'
  if (phase === 'deduce') return 'chapter.deduce'
  if (phase === 'draft') return 'chapter.draft'
  if (phase === 'final') return 'chapter.final'
  return null
}

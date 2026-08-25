/**
 * 仪表盘可读面：弱章排序、空态、呼吸默认章。
 * 不碰 recharts。仪表盘只回答「机器体检」。
 */

export function chapterScore(c) {
  return (Number(c?.qc_issues) || 0) + (Number(c?.causal) || 0)
}

/**
 * 弱章：问题多的在前；当前写作章若也弱，钉在顶。
 * 不按章筛掉全书体检。
 */
export function rankWeakChapters(chapters, { currentChapter, limit = 8 } = {}) {
  const cur = Number(currentChapter)
  const weak = (chapters || []).filter((c) => chapterScore(c) > 0)
  weak.sort((a, b) => {
    const aCur = Number.isFinite(cur) && Number(a.seq) === cur ? 1 : 0
    const bCur = Number.isFinite(cur) && Number(b.seq) === cur ? 1 : 0
    if (aCur !== bCur) return bCur - aCur
    return chapterScore(b) - chapterScore(a)
  })
  return weak.slice(0, limit)
}

/** kind: quality_error | cache_stale | no_chapters | no_weak | null */
export function weakChapterEmptyKind({ qErr, cacheStale, chapters } = {}) {
  if (qErr) return 'quality_error'
  if (cacheStale) return 'cache_stale'
  const chs = chapters || []
  if (chs.length === 0) return 'no_chapters'
  if (!chs.some((c) => chapterScore(c) > 0)) return 'no_weak'
  return null
}

export function weakChapterEmptyCopy(kind) {
  if (kind === 'quality_error') {
    return { title: '质量汇总读不到', body: '码字和伏笔台账还在。质检数字这次不算。' }
  }
  if (kind === 'cache_stale') {
    return { title: '质量缓存已过期', body: '先刷新缓存，再看弱章。' }
  }
  if (kind === 'no_chapters') {
    return { title: '还没有章', body: '先写一章。没有章就谈不上质检干净。' }
  }
  if (kind === 'no_weak') {
    return { title: '这几章质检干净', body: '没有 QC / 因果问题。不是总纲进度。' }
  }
  return { title: '', body: '' }
}

export function promiseEmptyKind({ led, ledErr } = {}) {
  if (ledErr) return 'ledger_error'
  if (!led) return 'loading'
  const open = led.open || []
  if (open.length === 0) return 'no_open'
  return null
}

export function promiseEmptyCopy(kind) {
  if (kind === 'ledger_error') {
    return { title: '伏笔台账读不到', body: '再试一次。' }
  }
  if (kind === 'no_open') {
    return { title: '还没有未收的账', body: '开口伏笔会出现在这里。' }
  }
  return { title: '加载伏笔…', body: '' }
}

/** 呼吸默认跟当前写作章，没有才退书末。 */
export function breathDefaultSeq(chapter, lastSeq) {
  const n = Number(chapter)
  if (Number.isFinite(n) && n > 0) return n
  const last = Number(lastSeq)
  if (Number.isFinite(last) && last > 0) return last
  return 1
}

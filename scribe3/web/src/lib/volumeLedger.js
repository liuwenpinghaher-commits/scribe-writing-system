/**
 * 本卷还没办的几笔（与后端台账同一套身份，纯函数）。
 * 今晚 = 当前 seq；还没办 = 同卷、不是今晚、无正文。清单不含今晚。
 */

export function chapterHasProse(ch) {
  if (!ch || typeof ch !== 'object') return false
  if (ch.has_prose === true) return true
  if (ch.has_prose === false) return false
  if (Number(ch.word_count || 0) > 0) return true
  return String(ch.prose || '').trim().length > 0
}

export function sameVolumeId(a, b) {
  const x = String(a ?? '').trim()
  const y = String(b ?? '').trim()
  if (!x || !y) return false
  return x === y || x.endsWith(`:${y}`) || y.endsWith(`:${x}`)
}

export function remainingLaterFromOutline(outline, seq, extra = {}) {
  const chapters = Array.isArray(outline?.chapters) ? outline.chapters : []
  const current = chapters.find((c) => Number(c.seq) === Number(seq))
  const vol = current?.volume ?? extra.volume
  if (vol == null || String(vol).trim() === '') return []
  return chapters
    .filter((c) => sameVolumeId(c.volume, vol))
    .filter((c) => Number(c.seq) !== Number(seq))
    .filter((c) => !chapterHasProse(c))
    .sort((a, b) => Number(a.seq) - Number(b.seq))
    .slice(0, 8)
}

export function volumeRemainingWork(outline, volumeId, excludeSeq) {
  const chapters = Array.isArray(outline?.chapters) ? outline.chapters : []
  if (volumeId == null || String(volumeId).trim() === '') return []
  return chapters
    .filter((c) => sameVolumeId(c.volume, volumeId))
    .filter((c) => excludeSeq == null || Number(c.seq) !== Number(excludeSeq))
    .filter((c) => !chapterHasProse(c))
    .sort((a, b) => Number(a.seq) - Number(b.seq))
    .slice(0, 8)
}

export function introLooksLikeOneChapterNight(intro, chapters) {
  const text = String(intro || '').trim()
  const peers = (chapters || []).filter(Boolean)
  if (peers.length < 2) return false
  const hits = peers.filter((c) => {
    const t = String(c.title || '').trim()
    return t.length >= 2 && text.includes(t)
  }).length
  return hits < 2
}

export function chapterAccountLine(ch) {
  const syn = String(ch?.synopsis || '').trim()
  return syn || '这章还没立要办的事'
}

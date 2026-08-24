/** 缺省当无正文。outline 降级 SQL 可能没有 has_prose。 */
export function chapterHasProse(chapter) {
  return chapter?.has_prose === true
}

/** KD-8：settled_note → hook_preview → 截断 synopsis → 还没写这一句 */
export function chapterOneLine(chapter) {
  const settled = String(chapter?.settled_note || '').trim()
  if (settled) return settled
  const hook = String(chapter?.hook_preview || '').trim()
  if (hook) return hook
  const synopsis = String(chapter?.synopsis || '').trim()
  if (synopsis) return synopsis.length > 80 ? `${synopsis.slice(0, 80)}…` : synopsis
  return '还没写这一句'
}

export function chapterCite(chapter) {
  const seq = chapter?.seq
  if (seq == null) return ''
  const title = String(chapter?.title || '').trim()
  return title ? `第 ${seq} 章《${title}》` : `第 ${seq} 章`
}

function lastMatching(chapters, pred) {
  for (let i = chapters.length - 1; i >= 0; i -= 1) {
    if (pred(chapters[i])) return chapters[i]
  }
  return null
}

/**
 * 从 outline.chapters 推进度陈述。不读 snapshot。
 * 有正文说「写到」，只有纲/设计说「立到」。禁止「约 0 字」。
 */
export function progressLineFromOutline(outline) {
  const chapters = Array.isArray(outline?.chapters) ? [...outline.chapters] : []
  chapters.sort((a, b) => {
    const ao = a.sort_order != null ? a.sort_order : a.seq
    const bo = b.sort_order != null ? b.sort_order : b.seq
    return (ao ?? 0) - (bo ?? 0)
  })
  const n = chapters.length
  if (!n) return '还没有章。'

  const currentProse = lastMatching(chapters, chapterHasProse)
  const currentPlan = lastMatching(chapters, (c) => chapterOneLine(c) !== '还没写这一句')
  const current = currentProse || currentPlan || chapters[chapters.length - 1]
  const words = chapters.reduce((sum, c) => sum + (Number(c.word_count) || 0), 0)

  if (currentProse) {
    const cite = chapterCite(currentProse)
    return words > 0
      ? `稿子写到${cite}。全书 ${n} 章，约 ${words} 字。`
      : `稿子写到${cite}。全书 ${n} 章。`
  }
  return `立到${chapterCite(current)}，还没有正文。全书 ${n} 章。`
}

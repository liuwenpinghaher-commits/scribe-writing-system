export function chapterSequence(start, end) {
  const first = Number(start)
  const last = Number(end)
  if (!Number.isInteger(first) || first < 1) throw new Error('起始章节必须是不小于 1 的整数')
  if (!Number.isInteger(last) || last < first) throw new Error('结束章节不能小于起始章节')
  return Array.from({ length: last - first + 1 }, (_, index) => first + index)
}

export function buildChapterCycleReport({ requested = [], steps = [] } = {}) {
  const bySeq = new Map((Array.isArray(steps) ? steps : []).map((step) => [Number(step?.seq), step]))
  const normalized = (Array.isArray(requested) ? requested : []).map((seq) => {
    const step = bySeq.get(Number(seq)) || {}
    const result = step.result && typeof step.result === 'object' ? step.result : {}
    const reasons = []
    if (step.exitCode !== 0) reasons.push('子旅程未以 0 退出')
    if (result.ok !== true) reasons.push('子旅程未显式成功')
    if (Number(result.chapter_seq) !== Number(seq)) reasons.push('artifact 章节号漂移')
    if (typeof step.artifact !== 'string' || !step.artifact.trim()) reasons.push('缺少 artifact')
    return { seq: Number(seq), ok: reasons.length === 0, reasons }
  })
  const failed_sequences = normalized.filter((step) => !step.ok).map((step) => step.seq)
  return { ok: failed_sequences.length === 0, chapters: normalized, failed_sequences }
}

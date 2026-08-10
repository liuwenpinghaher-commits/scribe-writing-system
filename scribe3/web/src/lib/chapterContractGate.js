/**
 * 章前契约软门（对齐 GATE-B normal 章 B1/B2/B3 发现层）。
 * 纯函数，无 IO。仅 UI soft 提示；不替代 evaluate_save_craft_gate。
 */

import { softGateIssues, softGateSummary } from './deduceGate.js'

/** GATE-B normal：非空 beat text 最少条数 */
export const MIN_BEAT_TEXTS = 3
/** synopsis / scene_truth 短于该字数 → warn（非 error） */
export const SHORT_FIELD_CHARS = 40

function trimText(value) {
  return String(value ?? '').trim()
}

/** 非空 beat text 条数（dict.text 或字符串） */
export function countBeatTexts(beats) {
  let n = 0
  for (const b of beats || []) {
    const t = typeof b === 'string'
      ? b
      : (b && typeof b === 'object' ? b.text : '')
    if (trimText(t)) n += 1
  }
  return n
}

/**
 * @param {object|null|undefined} ch chapter-like: synopsis, beats, scene_truth, …
 * @returns {{
 *   issues: Array<{ id: string, level: 'error'|'warn'|'info', message: string }>,
 *   needsAttention: boolean,
 *   hasError: boolean,
 *   synopsisOk: boolean,
 *   beatsOk: boolean,
 *   sceneTruthOk: boolean,
 *   beatCount: number,
 *   deduce: ReturnType<typeof softGateIssues>,
 * }}
 */
export function evaluateChapterContract(ch) {
  const meta = ch || {}
  const synopsis = trimText(meta.synopsis)
  const truth = trimText(meta.scene_truth)
  const beatCount = countBeatTexts(meta.beats)
  const issues = []

  if (!synopsis) {
    issues.push({
      id: 'missingSynopsis',
      level: 'error',
      message: '大纲 synopsis 为空',
    })
  } else if (synopsis.length < SHORT_FIELD_CHARS) {
    issues.push({
      id: 'shortSynopsis',
      level: 'warn',
      message: `大纲过短（${synopsis.length} 字，建议 ≥${SHORT_FIELD_CHARS}）`,
    })
  }

  if (beatCount < MIN_BEAT_TEXTS) {
    issues.push({
      id: 'missingBeats',
      level: 'error',
      message: `节拍不足（${beatCount}/${MIN_BEAT_TEXTS} 条非空）`,
    })
  }

  if (!truth) {
    issues.push({
      id: 'missingSceneTruth',
      level: 'error',
      message: '场景真相 scene_truth 为空',
    })
  } else if (truth.length < SHORT_FIELD_CHARS) {
    issues.push({
      id: 'shortSceneTruth',
      level: 'warn',
      message: `场景真相过短（${truth.length} 字，建议 ≥${SHORT_FIELD_CHARS}）`,
    })
  }

  const deduce = softGateIssues(meta)
  if (deduce.needsAttention) {
    const summary = softGateSummary(deduce)
    issues.push({
      id: 'deduceAttention',
      level: 'warn',
      message: summary || '演绎未齐',
    })
  }

  const hasError = issues.some((i) => i.level === 'error')
  return {
    issues,
    needsAttention: hasError || issues.some((i) => i.level === 'warn'),
    hasError,
    synopsisOk: Boolean(synopsis),
    beatsOk: beatCount >= MIN_BEAT_TEXTS,
    sceneTruthOk: Boolean(truth),
    beatCount,
    deduce,
  }
}

/** 任一 error 级契约缺口（B1/B2/B3）→ true；warn 不算 */
export function contractNeedsAttention(ch) {
  return evaluateChapterContract(ch).hasError
}

/** 中文一句摘要（可列多项 error + 首条 warn） */
export function contractSoftSummary(chOrIssues) {
  const evald = Array.isArray(chOrIssues)
    ? { issues: chOrIssues, hasError: chOrIssues.some((i) => i.level === 'error') }
    : evaluateChapterContract(chOrIssues)
  const errors = (evald.issues || []).filter((i) => i.level === 'error')
  const warns = (evald.issues || []).filter((i) => i.level === 'warn')
  const parts = [
    ...errors.map((i) => i.message),
    ...warns.slice(0, 2).map((i) => i.message),
  ]
  return parts.join('；') || ''
}

/** sessionStorage key：关闭契约 soft banner 当次会话 */
export function contractBannerDismissKey(work, seq) {
  return `s3.soft.contract:${work || 'main'}:${seq}`
}

export function isContractBannerDismissed(work, seq) {
  try {
    return sessionStorage.getItem(contractBannerDismissKey(work, seq)) === '1'
  } catch {
    return false
  }
}

export function dismissContractBanner(work, seq) {
  try {
    sessionStorage.setItem(contractBannerDismissKey(work, seq), '1')
  } catch { /* */ }
}

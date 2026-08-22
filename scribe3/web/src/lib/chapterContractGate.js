/**
 * 章前契约软门（对齐 GATE-B normal 章 B1/B2/B3 发现层）。
 * 纯函数，无 IO。仅 UI soft 提示；不替代 evaluate_save_craft_gate。
 *
 * stakes / 高压探测与后端 ``parse_stakes_presence`` /
 * ``brief.parse_chapter_meta`` 口径对齐（正则同源注释）。
 */

import { softGateIssues, softGateSummary } from './deduceGate.js'

/** GATE-B normal：非空 beat text 最少条数 */
export const MIN_BEAT_TEXTS = 3
/** 冰山地板：演绎/排演仍按字数；大纲/节拍改线索密度（不再用 500 吓人）。 */
export const ICEBERG_SYNOPSIS = 80
export const ICEBERG_BEAT_EACH = 0
export const ICEBERG_BEAT_SUM = 0
export const ICEBERG_DEDUCTION = 5000
/**
 * 可写 hard 下限（与定稿门字数地板对齐）。
 * 去空白后短于该值 → error（未达可写），不再仅 warn。
 */
export const MIN_WRITABLE_CHARS = 80
/** ≥可写 且 短于该值 → warn「可再写细」 */
export const SHORT_HINT_CHARS = 120
/** @deprecated 用 MIN_WRITABLE_CHARS；保留别名避免旧 import 炸 */
export const SHORT_FIELD_CHARS = MIN_WRITABLE_CHARS
/** 高压 role（与后端 parse_stakes_presence 对齐） */
const HIGH_PRESSURE_ROLES = new Set(['高压', '推进', '高潮', '决战'])

function trimText(value) {
  return String(value ?? '').trim()
}

/** 与后端 cn_len 一致：去掉全部空白后的长度 */
export function cnLen(value) {
  return trimText(value).replace(/\s+/g, '').length
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
 * 从 synopsis 解析 stakes / 压力级 / role（轻量；对齐后端）。
 * @returns {{
 *   present: boolean,
 *   stakes: string,
 *   highPressure: boolean,
 *   pressure: number,
 *   role: string,
 *   warning: string,
 * }}
 */
export function parseOutlineStakes(synopsis) {
  const text = String(synopsis || '')
  let stakes = ''
  let pressure = 0
  let role = ''
  const stakesM = text.match(/(?:stakes|赌注)\s*[:：]\s*([^\n]+)/i)
  if (stakesM) stakes = (stakesM[1] || '').trim()
  const pM = text.match(/压力级\s*[:：]\s*(\d)/)
  if (pM) pressure = Number(pM[1]) || 0
  const rM = text.match(/chapter_role\s*[:：]\s*(\S+)/i)
  if (rM) role = (rM[1] || '').trim()
  // 也认「角色:高压」类中文标注
  if (!role) {
    const r2 = text.match(/(?:章角色|本章角色|角色)\s*[:：]\s*(高压|推进|高潮|决战)/)
    if (r2) role = r2[1]
  }
  const highPressure = pressure >= 4 || HIGH_PRESSURE_ROLES.has(role)
  const present = Boolean(stakes)
  return {
    present,
    stakes,
    highPressure,
    pressure,
    role,
    warning: highPressure && !present ? 'missing_outline_stakes' : '',
  }
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
 *   stakesOk: boolean,
 *   stakes: ReturnType<typeof parseOutlineStakes>,
 *   beatCount: number,
 *   deduce: ReturnType<typeof softGateIssues>,
 * }}
 */
export function evaluateChapterContract(ch) {
  const meta = ch || {}
  const synopsis = trimText(meta.synopsis)
  const truth = trimText(meta.scene_truth)
  const playText = trimText(
    (meta.play && typeof meta.play === 'object' ? meta.play.text : meta.play) || meta.play_text,
  )
  const contractObj = (meta.contract && typeof meta.contract === 'object') ? meta.contract : null
  const contractBeats = Array.isArray(contractObj?.beats) ? contractObj.beats : []
  const fields = (contractObj && typeof contractObj.fields === 'object') ? contractObj.fields : null
  const hasPlay = playText.length > 0
  const hasContract = !!(fields && (fields.goal || fields.choice || fields.decision || fields.cost || fields.hook))
    || contractBeats.length > 0
  const designReady = hasPlay || hasContract
  const beatCount = designReady
    ? Math.max(countBeatTexts(contractBeats), countBeatTexts(meta.beats))
    : countBeatTexts(meta.beats)
  const stakes = parseOutlineStakes(synopsis)
  const issues = []

  const synN = cnLen(synopsis)
  const truthN = cnLen(truth)

  if (!synopsis) {
    issues.push({
      id: 'missingSynopsis',
      level: 'info',
      message: '材料还可再写：本章大纲还是空的',
    })
  } else if (synN < MIN_WRITABLE_CHARS) {
    issues.push({
      id: 'shortSynopsis',
      level: 'info',
      message: `材料还可再写：大纲 ${synN} 字（不挡先写日子）`,
    })
  } else if (synN < SHORT_HINT_CHARS) {
    issues.push({
      id: 'briefSynopsis',
      level: 'warn',
      message: `大纲可写但偏简（${synN} 字，可写到 ≥${SHORT_HINT_CHARS}）`,
    })
  }

  if (!designReady && beatCount < MIN_BEAT_TEXTS) {
    issues.push({
      id: 'missingBeats',
      level: 'info',
      message: `材料还可再写：节拍 ${beatCount}/${MIN_BEAT_TEXTS} 条`,
    })
  }

  if (!truth) {
    issues.push({
      id: 'missingSceneTruth',
      level: 'info',
      message: '材料还可再写：场景真相还是空的',
    })
  } else if (truthN < MIN_WRITABLE_CHARS) {
    issues.push({
      id: 'shortSceneTruth',
      level: 'info',
      message: `材料还可再写：场景真相 ${truthN} 字`,
    })
  } else if (truthN < SHORT_HINT_CHARS) {
    issues.push({
      id: 'briefSceneTruth',
      level: 'warn',
      message: `场景真相可写但偏简（${truthN} 字，可写到 ≥${SHORT_HINT_CHARS}）`,
    })
  }

  // 高压缺 stakes → warn only（不把「可开写」打成红 error）
  if (stakes.warning === 'missing_outline_stakes') {
    issues.push({
      id: 'missingOutlineStakes',
      level: 'warn',
      message: '这是高压章，大纲里最好写清「谁会付出什么代价」',
    })
  }

  const beatLens = (meta.beats || []).map((b) => {
    const t = typeof b === 'string' ? b : (b && b.text) || ''
    return cnLen(t)
  }).filter((n) => n > 0)
  const beatSum = beatLens.reduce((a, b) => a + b, 0)
  let dedSum = 0
  for (const d of meta.deductions || []) {
    dedSum += cnLen(typeof d === 'string' ? d : (d && (d.prose || d.text)) || '')
  }
  const hasSpine = !!(meta.chapter_spine && (meta.chapter_spine.goal || meta.chapter_spine.choice))
  const icebergThin = !designReady && (
    (!hasSpine && synN > 0 && synN < MIN_WRITABLE_CHARS) || dedSum < ICEBERG_DEDUCTION
  )
  if (icebergThin && (synN > 0 || beatLens.length > 0 || hasSpine || dedSum > 0)) {
    issues.push({
      id: 'icebergThin',
      level: 'warn',
      message: hasPlay || hasContract
        ? `演绎尚未齐（${dedSum}/${ICEBERG_DEDUCTION}）。这场戏已经有了，先补字缝。`
        : hasSpine
          ? `演绎尚未齐（${dedSum}/${ICEBERG_DEDUCTION}）。章纲已有短槽，开写前先补限知投影。`
          : `情节合同未齐（大纲 ${synN} 字，演绎 ${dedSum}/${ICEBERG_DEDUCTION}）。请先立责任、再写这场戏。`,
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
    synopsisOk: synN >= MIN_WRITABLE_CHARS,
    beatsOk: designReady || beatCount >= MIN_BEAT_TEXTS,
    playOk: hasPlay,
    designReady,
    sceneTruthOk: truthN >= MIN_WRITABLE_CHARS,
    stakesOk: stakes.present || !stakes.highPressure,
    stakes,
    beatCount,
    deduce,
    synopsisCnLen: synN,
    sceneTruthCnLen: truthN,
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

/**
 * 执行 soft 一行人话（同源 API 字段；前端不重算 soft_fulfill）。
 * @param {object|null|undefined} softStatus GET /chapter/execution-soft-status 响应
 */
export function executionSoftSummary(softStatus) {
  if (!softStatus || typeof softStatus !== 'object') return ''
  const parts = []
  const soft = softStatus.soft_fulfill
  if (soft && soft.ok_soft === false) {
    const gaps = Array.isArray(soft.gaps) ? soft.gaps : []
    const gapMap = {
      dialogue_low: '对白偏少',
      short_and_dialogue_low: '短稿且对白不足',
      weak_opener: '开篇外力弱',
      missing_event: '事件推进弱',
    }
    const gapText = gaps.map((g) => gapMap[g] || g).filter(Boolean).slice(0, 3).join('、')
    if (gapText) parts.push(gapText)
    else if (soft.steer_hint) parts.push(String(soft.steer_hint).slice(0, 80))
    else parts.push('执行对照未达标')
    if (soft.quotes != null) parts.push(`引号${soft.quotes}`)
  }
  const drift = softStatus.drift
  if (drift && drift.drift) {
    parts.push(drift.advisory ? String(drift.advisory).slice(0, 60) : '事件驱动相对成稿已变，建议强制重写核对')
  }
  const stakes = softStatus.stakes
  if (stakes && stakes.warning === 'missing_outline_stakes' && !parts.some((p) => p.includes('代价') || p.includes('赌注'))) {
    parts.push('高压章缺「代价」说明')
  }
  return parts.join('；') || ''
}

/** 契约 + 执行 soft 合并摘要（banner 用） */
export function mergedSoftBannerSummary(ch, softStatus) {
  const contract = contractSoftSummary(ch)
  const exec = executionSoftSummary(softStatus)
  if (contract && exec) return `开写前：${contract}。写完对照：${exec}`
  if (contract) return `开写前：${contract}`
  if (exec) return `写完对照：${exec}`
  return ''
}

/** 是否应展示合一 soft banner（契约 error 或执行 soft 有 gap/drift） */
export function shouldShowMergedSoftBanner(ch, softStatus) {
  if (contractNeedsAttention(ch)) return true
  if (!softStatus) return false
  const soft = softStatus.soft_fulfill
  if (soft && soft.ok_soft === false) return true
  if (softStatus.drift && softStatus.drift.drift) return true
  return false
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

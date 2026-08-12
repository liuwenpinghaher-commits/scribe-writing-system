// 环境安全与健康检查：禁止静默误连未知生产库写验收书。
// 约定：
//   - 本方案默认打「已部署 demo/验收栈」(E2E_BASE:3311 / E2E_API:3321)。
//   - 必须显式 E2E_ALLOW_DEPLOYED=1 才允许连接已占用的 3311/3321。
//   - Surreal 在 demo 上常映射 :8001；禁止在未声明时把 CI 临时库与 demo 混用。
//   - 黑名单书名/slug（E2E_REFUSE_TITLES / E2E_REFUSE_SLUGS）命中则 fail-loud。

import { log } from './log.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export function resolveEnv() {
  const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
  const API = process.env.E2E_API || 'http://127.0.0.1:3321'
  const WORD_TARGET = Number(process.env.E2E_WORD_TARGET || 50000)
  const TARGET_CHAPTERS = Number(process.env.E2E_TARGET_CHAPTERS || 18)
  const MIN_CHAPTER_NET = Number(process.env.E2E_MIN_PROSE || process.env.E2E_MIN_PROSE_LENGTH || 2500)
  const MIN_CHAPTER_HARD = Number(process.env.E2E_MIN_CHAPTER_HARD || 1200)
  const CHAPTER_MAX_MS = Number(process.env.E2E_CHAPTER_MAX_MS || 480000)
  const TOTAL_MAX_MS = Number(process.env.E2E_TOTAL_MAX_MS || 6 * 60 * 60 * 1000)
  const QUALITY_REPAIR_ROUNDS = Number(process.env.E2E_QUALITY_REPAIR_ROUNDS || 2)
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
  const BOOK = process.env.E2E_BOOK_TITLE || `50k全程验收·${stamp}`
  const WORK = process.env.E2E_WORK || ''
  return {
    BASE,
    API,
    BOOK,
    WORK,
    WORD_TARGET,
    TARGET_CHAPTERS,
    MIN_CHAPTER_NET,
    MIN_CHAPTER_HARD,
    CHAPTER_MAX_MS,
    TOTAL_MAX_MS,
    QUALITY_REPAIR_ROUNDS,
    ALLOW_DEPLOYED: process.env.E2E_ALLOW_DEPLOYED === '1',
    ALLOW_API_SEED: process.env.E2E_ALLOW_API_SEED === '1',
    RESUME: process.env.E2E_RESUME === '1' || process.argv.includes('--resume'),
    ART: process.env.E2E_ART || process.env.E2E_ARTIFACT_ROOT || '',
  }
}

function parseList(envKey) {
  return String(process.env[envKey] || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

async function fetchJson(url, { timeoutMs = 15000 } = {}) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const r = await fetch(url, { signal: ctrl.signal })
    const text = await r.text()
    let body = null
    try { body = JSON.parse(text) } catch { body = { raw: text.slice(0, 400) } }
    return { ok: r.ok, status: r.status, body }
  } finally {
    clearTimeout(t)
  }
}

/**
 * 启动前 fail-loud 护栏。
 * @returns {Promise<{ apiHealth: any, works: any[] }>}
 */
export async function assertSafeEnvironment(env = resolveEnv()) {
  const { BASE, API, ALLOW_DEPLOYED } = env
  log(`env_guard BASE=${BASE} API=${API} allow_deployed=${ALLOW_DEPLOYED}`)

  // 1) 健康探活
  const health = await fetchJson(`${API}/health`)
  if (!health.ok) {
    throw new Error(`后端不可达 ${API}/health status=${health.status} body=${JSON.stringify(health.body).slice(0, 200)}`)
  }
  log(`health ok status=${health.status}`)

  const ready = await fetchJson(`${API}/ready`).catch(() => ({ ok: false, status: 0, body: null }))
  if (ready.ok) log(`ready ok`)
  else log(`ready soft-fail status=${ready.status}（部分部署无 /ready，继续）`)

  // 2) 前端探活
  try {
    const r = await fetch(BASE, { signal: AbortSignal.timeout(15000) })
    if (!r.ok) throw new Error(`frontend HTTP ${r.status}`)
    log(`frontend ok ${BASE}`)
  } catch (e) {
    throw new Error(`前端不可达 ${BASE}: ${e.message}`)
  }

  // 3) 必须显式允许已部署栈，避免 CI 冒烟脚本误写 demo/生产
  if (!ALLOW_DEPLOYED) {
    throw new Error(
      '拒绝连接：未设置 E2E_ALLOW_DEPLOYED=1。' +
      '本 50k 方案只对「已声明的验收/demo 栈」写书；' +
      'CI 临时库请用 scripts/e2e_ci.sh，勿与本脚本混用。',
    )
  }

  // 4) 可选：拒绝命中生产书名/slug
  const worksRes = await fetchJson(`${API}/works`)
  const works = Array.isArray(worksRes.body)
    ? worksRes.body
    : (worksRes.body?.works || [])
  const refuseTitles = parseList('E2E_REFUSE_TITLES')
  const refuseSlugs = parseList('E2E_REFUSE_SLUGS')
  // 默认拒绝历史上被污染过的生产书（可被 E2E_REFUSE_*= 覆盖清空时设 E2E_REFUSE_TITLES=）
  const defaultRefuse = process.env.E2E_REFUSE_TITLES === undefined
    ? ['纸命', '印迹']
    : refuseTitles
  const titles = process.env.E2E_REFUSE_TITLES === undefined ? defaultRefuse : refuseTitles
  for (const w of works) {
    if (titles.some((t) => w?.title === t || String(w?.title || '').includes(t))) {
      // 列表里存在生产书不等于误写；仅当 E2E_WORK 指向它们时拦截
      if (env.WORK && (w.slug === env.WORK || w.title === env.WORK)) {
        throw new Error(`E2E_WORK 命中拒绝名单书：${w.slug} ${w.title}`)
      }
    }
    if (refuseSlugs.includes(w?.slug) && env.WORK === w.slug) {
      throw new Error(`E2E_WORK slug 在拒绝名单：${w.slug}`)
    }
  }

  // 5) Hermes 可选探活（不强制 8642-8644 全绿，但记录）
  const hermesPorts = String(process.env.E2E_HERMES_PORTS || '8642,8643,8644').split(',')
  for (const port of hermesPorts) {
    const p = port.trim()
    if (!p) continue
    try {
      const r = await fetch(`http://127.0.0.1:${p}/health`, { signal: AbortSignal.timeout(3000) })
      log(`hermes :${p} health=${r.status}`)
    } catch {
      log(`hermes :${p} unreachable（若 Run 超时请检查 systemd）`)
    }
  }

  // 6) Surreal 提醒：demo 映射 :8001 是正常的；禁止再起第二套
  if (process.env.E2E_SURREAL_URL && /:8001\b/.test(process.env.E2E_SURREAL_URL)) {
    log('注意：E2E_SURREAL_URL 指向 :8001（demo/生产映射口）。只读回查可，禁止本脚本直连灌库。')
  }

  await sleep(50)
  return { apiHealth: health.body, works }
}

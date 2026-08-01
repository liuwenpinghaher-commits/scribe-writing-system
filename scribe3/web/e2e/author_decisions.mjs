// 作者决策点击：批准写入 / 接受提案 — 必须真实 Playwright click，禁止 API 静默代替。
// 供融合验收与 full_journey 复用。
import { attachRunIdentityCapture } from './run_identity_capture.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
// FourPane 根壳是作品页的稳定标记；右坞/主编槽作为折叠态兼容信号，避免只以输入框
// 是否可见误判已退回作品库并重复导航。
const BOOK_SHELL_SELECTOR = '[data-testid="four-col"], [data-testid="right-dock"], [data-testid="chief-chat-shell"], [data-testid="chief-write-chat"]'

/** 作品库卡片的稳定可访问名；用完整标题避免同前缀验收书误开。 */
export function workEntryAccessibleName(bookTitle) {
  return `打开${String(bookTitle || '')}`
}

async function isBookShellVisible(page) {
  return page.locator(BOOK_SHELL_SELECTOR).first().isVisible().catch(() => false)
}

/**
 * 硬导航后的 App 会按 localStorage 自动恢复最近作品；也可能真的停在作品库。
 * 因此只能等待两种合法落点之一，不能单押库页卡片。
 */
async function waitForBookShellOrLibraryCard(page, card, { timeoutMs = 20000 } = {}) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await isBookShellVisible(page)) return 'book-shell'
    if (await card.isVisible().catch(() => false)) return 'library-card'
    await sleep(200)
  }
  throw new Error('作品恢复超时：既未进入作品壳，也未看到目标作品卡')
}

/**
 * 主编 Run 的终态不保证带可见文本：纯 MCP 写入会以审批/工具事件完成。
 * Run 必须由后端终态确认；普通对话则须经历 busy→idle，避免发送尚未起流时假绿。
 */
export function shouldFinishChiefWait({ busy, sawBusy = false, requestSeen = false, isHermesRun = false, runTerminal = false, text = '', previousText = '' } = {}) {
  // 上一轮的聊天气泡会一直留在 DOM；不先观察到本轮网络请求，就不能把稳定旧文本
  // 当作本轮完成。纯工具 Run 可能没有 delta，故只能依赖后端终态。
  if (!requestSeen) return false
  // Run 终态来自正典后端；其它面板遗留的 spinner 不应覆盖它，否则纯 MCP 写入会
  // 因无关页面加载一直等到超时。调用方仍会随后以只读回查确认实际写入。
  if (isHermesRun && runTerminal) return true
  if (busy) return false
  return isHermesRun ? !!runTerminal : !!sawBusy
}

// Hermes 已在远端完成、仅等待本地审计回写的状态不再会产生工具或文本事件。
// 验收应将其视为交互终态，随后由调用方用正典只读回查判断写入是否真的发生。
export function isTerminalHermesRunStatus(status) {
  return [
    'completed',
    'completed_unverified',
    'remote_completed_pending_audit',
    'failed',
    'stopped',
    'cancelled',
    'canceled',
  ].includes(String(status || '').toLowerCase())
}

/**
 * Hermes 创建 Run 时把 work 放在 JSON 载荷中，而不是 URL 查询参数。状态回读必须
 * 带回这一隔离键，否则后端会按 fail-closed 规则拒绝跨作品不明确的查询。
 */
export function resolveRunWork(requestUrl, postData) {
  try {
    const fromQuery = new URL(requestUrl).searchParams.get('work')
    if (fromQuery?.trim()) return fromQuery.trim()
  } catch { /* 继续尝试请求载荷 */ }
  try {
    const payload = typeof postData === 'string' ? JSON.parse(postData) : postData
    return typeof payload?.work === 'string' ? payload.work.trim() : ''
  } catch {
    return ''
  }
}

/**
 * Run 状态查询属于验收辅助链路；网关或浏览器连接异常时不能无限占住
 * chiefSay 的总时限。失败按“本轮尚未确认终态”处理，由外层继续轮询/到时退出。
 */
export async function fetchRunStatusWithTimeout(fetchImpl, url, timeoutMs = 15000) {
  const controller = new AbortController()
  let timer
  // AbortController 只能保证中止尚未完成的 fetch；Node 的 fetch 在已收到
  // header 后，第三方若永不结束 body，response.json() 仍可能不响应 abort。
  // 因此 timeout 还必须是独立的返回竞争，不能让验收总时限依赖 transport 行为。
  const deadline = new Promise((resolve) => {
    timer = setTimeout(() => {
      controller.abort()
      resolve(null)
    }, Math.max(1, timeoutMs))
  })
  const status = (async () => {
    try {
      const response = await fetchImpl(url, { signal: controller.signal })
      return response?.ok ? await response.json() : null
    } catch {
      return null
    }
  })()
  try {
    return await Promise.race([status, deadline])
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Playwright 操作本身也可能卡在浏览器/传输层。主编 Run 的总时限必须覆盖
 * 选槽、输入、发送和轮询全部阶段，不能只给其中的 fetch 加 timeout。
 */
export async function runWithDeadline(operation, { timeoutMs, label = '操作' } = {}) {
  let timer
  const completed = Promise.resolve()
    .then(operation)
    .then((value) => ({ timedOut: false, value }), (error) => ({ timedOut: false, error }))
  const deadline = new Promise((resolve) => {
    timer = setTimeout(() => {
      resolve({
        timedOut: true,
        error: new Error(`${label}超时（${timeoutMs}ms）`),
      })
    }, Math.max(1, timeoutMs || 1))
  })
  try {
    const outcome = await Promise.race([completed, deadline])
    if (outcome.error && !outcome.timedOut) throw outcome.error
    return outcome
  } finally {
    clearTimeout(timer)
  }
}

/**
 * 章节阶段切换会替换 textarea 节点；旧 locator 的 fill/press 在 Playwright 未设
 * 默认超时时可能永久等待。正文发送必须和主编 Run 一样有独立的总时限。
 */
export async function submitComposerWithDeadline(composer, message, { timeoutMs = 30000 } = {}) {
  const outcome = await runWithDeadline(
    async () => {
      await composer.fill(message)
      await composer.press('Enter')
    },
    { timeoutMs, label: '正文发送' },
  )
  if (outcome.timedOut) throw outcome.error
  return outcome.value
}

/** 导出纯函数：决策控件选择器（单元测试可断言，不依赖浏览器） */
export const DECISION_SELECTORS = {
  runApprove: '[data-testid="run-approve"]',
  runDeny: '[data-testid="run-deny"]',
  runApproveStale: '[data-testid="run-approve-stale"]',
  draftAccept: '[data-testid="draft-accept"]',
  draftReject: '[data-testid="draft-reject"]',
  draftUseCandidate: '[data-testid="draft-use-candidate"]',
  // placeholder 可能带 @ 提示后缀，用前缀匹配
  chiefComposer: 'textarea[placeholder^="就当前内容问主编"]',
  /** 章内写作槽 WriteChat（产出提案卡） */
  writeComposer: 'textarea[placeholder^="提思路"]',
  stageFill: '[data-testid="stage-fill"]',
  stageAppend: '[data-testid="stage-append"]',
}

/**
 * 阶段提案条「填入」或「追加」——大纲/节拍/演绎/草稿的闭环决策点击。
 */
export async function acceptStageFill(page, { prefer = 'fill', timeoutMs = 180000, pollMs = 2000 } = {}) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeoutMs) {
    await approveAllPending(page, { maxRounds: 2, settleMs: 400 })
    const fill = page.locator(DECISION_SELECTORS.stageFill).first()
    const append = page.locator(DECISION_SELECTORS.stageAppend).first()
    const byFillText = page.getByRole('button', { name: '填入' }).first()
    const byAppendText = page.getByRole('button', { name: '追加' }).first()
    if (prefer === 'append') {
      for (const btn of [append, byAppendText, fill, byFillText]) {
        if (await btn.isVisible().catch(() => false)) {
          await btn.click()
          await sleep(1000)
          return { kind: 'stage', label: 'append-or-fill' }
        }
      }
    } else {
      for (const btn of [fill, byFillText, append, byAppendText]) {
        if (await btn.isVisible().catch(() => false)) {
          await btn.click()
          await sleep(1000)
          return { kind: 'stage', label: 'fill-or-append' }
        }
      }
    }
    await sleep(pollMs)
  }
  throw new Error('acceptStageFill: timeout waiting for 填入/追加')
}

/**
 * 点击所有可见的 Hermes「批准」与「仍要批准」，直到一轮内点不动。
 * @returns {{ approved: number, staleApproved: number }}
 */
export async function approveAllPending(page, { maxRounds = 12, settleMs = 500 } = {}) {
  let approved = 0
  let staleApproved = 0
  for (let r = 0; r < maxRounds; r++) {
    let hit = false
    // 先点「仍要批准」(过期卡),再点普通批准——MCP elicitation 超时约 60s,必须尽快点
    const stale = page.locator(DECISION_SELECTORS.runApproveStale)
    const nStale = await stale.count()
    for (let i = 0; i < nStale; i++) {
      const btn = stale.nth(i)
      if (await btn.isVisible().catch(() => false)) {
        await btn.click()
        staleApproved++
        hit = true
        await sleep(settleMs)
      }
    }
    const appr = page.locator(DECISION_SELECTORS.runApprove)
    const n = await appr.count()
    for (let i = 0; i < n; i++) {
      const btn = appr.nth(i)
      if (await btn.isVisible().catch(() => false)) {
        // disabled 跳过
        if (await btn.isDisabled().catch(() => false)) continue
        await btn.click()
        approved++
        hit = true
        await sleep(settleMs)
      }
    }
    // 回退：aria-label / 文案「批准」
    if (!hit) {
      const byAria = page.getByRole('button', { name: '批准' })
      const ac = await byAria.count()
      for (let i = 0; i < ac; i++) {
        const btn = byAria.nth(i)
        if (await btn.isVisible().catch(() => false) && !(await btn.isDisabled().catch(() => true))) {
          await btn.click()
          approved++
          hit = true
          await sleep(settleMs)
        }
      }
    }
    if (!hit) break
  }
  return { approved, staleApproved }
}

/**
 * 等待 DraftCard 可接受并点击「接受」或「用此版」。
 * @returns {{ kind: 'accept'|'candidate', clicks: number }}
 */
export async function acceptDraftProposal(page, { timeoutMs = 300000, pollMs = 2000 } = {}) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeoutMs) {
    // 仍在书写中则等
    const writing = await page.locator('text=书写中').count().catch(() => 0)
    if (writing > 0) {
      await sleep(pollMs)
      continue
    }
    // 草稿阶段的 WriteChat 通过 StageProposal 交给中区渲染“填入/追加”，
    // 不是 DraftCard；两者都是作者明确采用生成稿的动作。
    const stageFill = page.locator(DECISION_SELECTORS.stageFill).first()
    if (await stageFill.isVisible().catch(() => false) && !(await stageFill.isDisabled().catch(() => true))) {
      await stageFill.click()
      await sleep(1500)
      return { kind: 'stage', clicks: 1 }
    }
    const cand = page.locator(DECISION_SELECTORS.draftUseCandidate).first()
    if (await cand.isVisible().catch(() => false)) {
      await cand.click()
      await sleep(1200)
      return { kind: 'candidate', clicks: 1 }
    }
    const acc = page.locator(DECISION_SELECTORS.draftAccept).first()
    if (await acc.isVisible().catch(() => false) && !(await acc.isDisabled().catch(() => true))) {
      await acc.click()
      await sleep(1500)
      return { kind: 'accept', clicks: 1 }
    }
    // 文案回退
    const byText = page.getByRole('button', { name: '接受' }).first()
    if (await byText.isVisible().catch(() => false) && !(await byText.isDisabled().catch(() => true))) {
      await byText.click()
      await sleep(1500)
      return { kind: 'accept', clicks: 1 }
    }
    // 同时清掉可能的审批
    await approveAllPending(page, { maxRounds: 2, settleMs: 400 })
    await sleep(pollMs)
  }
  throw new Error('acceptDraftProposal: timeout waiting for 接受/用此版')
}

/**
 * 草稿阶段的“填入”只把提案置入草稿编辑器，尚未写入 chapter.prose。
 * 这里强制第二次可见、可点击的作者决定，调用方再用 save-chapter 响应证明落库。
 */
export async function adoptDraftAsFinal(page, { timeoutMs = 120000 } = {}) {
  const adopt = page.getByRole('button', { name: '采用为正文', exact: true }).first()
  await adopt.waitFor({ state: 'visible', timeout: timeoutMs })
  if (await adopt.isDisabled().catch(() => true)) {
    throw new Error('草稿已填入但“采用为正文”不可用')
  }
  await adopt.click()
  return { kind: 'adopt', clicks: 1 }
}

/**
 * 若已退回作品库（Binder/主编壳不在），按书名重新进台。
 */
export async function ensureInBook(page, bookTitle, { base } = {}) {
  if (!bookTitle) return false
  if (await isBookShellVisible(page)) return true
  const BASE = base || process.env.E2E_BASE || 'http://127.0.0.1:3311'
  await page.goto(BASE, { waitUntil: 'domcontentloaded' }).catch(() => {})
  await sleep(800)
  // 库页精确点目标书卡。批量验收会生成同前缀作品，模糊/截断匹配会误开别的书。
  const card = page.getByRole('button', { name: workEntryAccessibleName(bookTitle), exact: true })
  const recovered = await waitForBookShellOrLibraryCard(page, card)
  if (recovered === 'book-shell') return true
  await card.click({ timeout: 10000 })
  await page.waitForSelector(BOOK_SHELL_SELECTOR, { timeout: 20000 })
  await sleep(800)
  return isBookShellVisible(page)
}

/**
 * 主编栏被折叠/被其它 tab 盖住时，恢复可见再找输入框。
 * r6 失败根因：resolveComposer 找不到 textarea（栏折叠或未切到主编）。
 *
 * 铁律：禁止再点已激活的「主编」轨。Rail 对 active tab 再点会传空串 → onCollapse，
 * 会把右坞整栏收起（r14: ensure 一进来就把 right=0 打成 right=1）。
 *
 * @param {{ bookTitle?: string }} [opts] 退库时用于 re-open
 */
export async function ensureChiefVisible(page, opts = {}) {
  const bookTitle = opts.bookTitle || process.env.E2E_BOOK_TITLE || ''

  // 退回作品库 → 先重新进书
  if (!(await page.locator(BOOK_SHELL_SELECTOR).count().catch(() => 0))) {
    await ensureInBook(page, bookTitle)
  }

  // 仅在有 dialog/modal 时 Escape，避免误触其它快捷
  const hasDialog = await page.locator('[role="dialog"], [data-state="open"]').count().catch(() => 0)
  if (hasDialog) await page.keyboard.press('Escape').catch(() => {})

  const usableComposer = async () => page.evaluate(() => {
    const okPh = (ph) => /问主编|提思路/.test(ph || '')
    return [...document.querySelectorAll('textarea')].some(
      (t) => okPh(t.placeholder) && t.offsetWidth > 20 && t.offsetHeight > 10,
    )
  }).catch(() => false)

  // 已有可用输入框：什么都别点（尤其别点主编轨）
  if (await usableComposer()) return

  // 最多两轮强制展开（长会话后 onResize 误折叠 / 把手点不中）
  for (let round = 0; round < 2 && !(await usableComposer()); round++) {
    // 每轮再确认未退库
    if (!(await page.locator(BOOK_SHELL_SELECTOR).count().catch(() => 0))) {
      await ensureInBook(page, bookTitle)
    }
    await page.evaluate(() => {
      try {
        for (const k of Object.keys(localStorage)) {
          if (k.endsWith('.rightCollapsed')) localStorage.setItem(k, '0')
        }
      } catch { /* */ }
      try {
        document.querySelectorAll('[data-testid="right-restore-button"]').forEach((n) => n.click())
      } catch { /* */ }
      try { window.dispatchEvent(new CustomEvent('s3-expand-right')) } catch { /* */ }
      try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
    }).catch(() => {})
    // Playwright 再点一遍可见把手 / aria
    const restores = page.locator('[data-testid="right-restore-button"], button[aria-label="展开主编栏"]')
    const n = await restores.count().catch(() => 0)
    for (let i = 0; i < n; i++) {
      const btn = restores.nth(i)
      if (await btn.isVisible().catch(() => false)) {
        await btn.click({ force: true }).catch(() => {})
        await sleep(350)
      }
    }
    // 仅当右坞在、主编壳不在、且轨按钮未 pressed 时才点「主编」
    const hasShell = await page.locator('[data-testid="chief-chat-shell"], [data-testid="chief-write-chat"]')
      .count().catch(() => 0)
    if (!hasShell) {
      const chiefTab = page.getByRole('button', { name: '主编', exact: true })
      const tc = await chiefTab.count().catch(() => 0)
      for (let i = 0; i < tc; i++) {
        const btn = chiefTab.nth(i)
        if (!(await btn.isVisible().catch(() => false))) continue
        const pressed = await btn.getAttribute('aria-pressed').catch(() => null)
        if (pressed === 'true') continue
        await btn.click({ force: true }).catch(() => {})
        await sleep(350)
      }
    }
    await page.locator('[data-testid="chief-chat-shell"], [data-testid="chief-write-chat"], [data-testid="right-dock"]')
      .first().waitFor({ state: 'attached', timeout: 6000 }).catch(() => {})
    await sleep(400 + round * 300)
  }
}

export async function resolveComposer(page, preferWrite, { retries = 8, bookTitle } = {}) {
  const book = bookTitle || process.env.E2E_BOOK_TITLE || ''
  const order = preferWrite
    ? [DECISION_SELECTORS.writeComposer, DECISION_SELECTORS.chiefComposer, 'textarea[placeholder^="提思路"]', 'textarea[placeholder^="就当前内容问主编"]', '[data-testid="chief-write-chat"] textarea', '[data-testid="chief-chat-shell"] textarea']
    : [DECISION_SELECTORS.chiefComposer, DECISION_SELECTORS.writeComposer, 'textarea[placeholder^="就当前内容问主编"]', 'textarea[placeholder^="提思路"]', '[data-testid="chief-chat-shell"] textarea', '[data-testid="chief-write-chat"] textarea']
  for (let attempt = 0; attempt <= retries; attempt++) {
    for (const sel of order) {
      const loc = page.locator(sel).first()
      if (!(await loc.count())) continue
      // 先 attached 即可；被遮挡时 force 聚焦
      try {
        await loc.waitFor({ state: 'attached', timeout: 1500 })
        const box = await loc.boundingBox().catch(() => null)
        if (box && box.width > 8 && box.height > 8) {
          await loc.click({ force: true }).catch(() => {})
          return loc
        }
        // 尺寸为 0 也可能仍可填（隐藏布局）
        if (await loc.isEditable().catch(() => false)) {
          await loc.focus().catch(() => {})
          return loc
        }
      } catch { /* next sel */ }
    }
    const any = page.locator('textarea').filter({ hasNot: page.locator('[disabled]') })
    const ac = await any.count().catch(() => 0)
    for (let i = ac - 1; i >= 0; i--) {
      const loc = any.nth(i)
      const box = await loc.boundingBox().catch(() => null)
      if (box && box.width > 20 && box.height > 12) {
        await loc.click({ force: true }).catch(() => {})
        return loc
      }
    }
    if (attempt < retries) {
      await ensureChiefVisible(page, { bookTitle: book })
      await sleep(700 + attempt * 200)
    }
  }
  // 诊断：折叠态 + textarea，便于分清「栏收了」还是「壳挂了没输入」
  const diag = await page.evaluate(() => ({
    right: document.querySelector('[data-testid="right-panel"]')?.getAttribute('data-collapsed'),
    inBook: !!document.querySelector('[data-testid="four-col"], [data-testid="right-dock"], [data-testid="chief-chat-shell"], [data-testid="chief-write-chat"]'),
    dock: !!document.querySelector('[data-testid="right-dock"]'),
    shell: !!document.querySelector('[data-testid="chief-chat-shell"]'),
    restore: document.querySelectorAll('[data-testid="right-restore-button"]').length,
    tas: [...document.querySelectorAll('textarea')].map((t) => ({
      ph: t.placeholder, w: t.offsetWidth, h: t.offsetHeight, vis: !!(t.offsetParent),
    })),
  })).catch(() => ({}))
  throw new Error(`resolveComposer: no chief/write textarea visible diag=${JSON.stringify(diag).slice(0, 600)}`)
}

/**
 * 向主编发送消息并等待流结束；其间自动点批准。
 * @param {{ preferWrite?: boolean, maxMs?: number, bookTitle?: string }} opts preferWrite=true 优先写作槽（提案卡）
 */
export async function chiefSay(page, msg, opts = {}) {
  const maxMs = opts.maxMs ?? 300000
  const outcome = await runWithDeadline(
    () => chiefSayWithinDeadline(page, msg, { ...opts, maxMs }),
    { timeoutMs: maxMs + 30000, label: '主编交互' },
  )
  if (outcome.timedOut) throw outcome.error
  return outcome.value
}

async function chiefSayWithinDeadline(page, msg, { maxMs = 300000, preferWrite = false, bookTitle, onProgress } = {}) {
  const book = bookTitle || process.env.E2E_BOOK_TITLE || ''
  const phaseTimeoutMs = Math.min(30_000, maxMs)
  onProgress?.('开始恢复主编栏')
  const visible = await runWithDeadline(
    () => ensureChiefVisible(page, { bookTitle: book }),
    { timeoutMs: phaseTimeoutMs, label: '恢复主编栏' },
  )
  if (visible.timedOut) throw visible.error
  onProgress?.('主编栏已恢复')
  onProgress?.('开始解析主编输入框')
  const composer = await runWithDeadline(
    () => resolveComposer(page, preferWrite, { bookTitle: book }),
    { timeoutMs: phaseTimeoutMs, label: '解析主编输入框' },
  )
  if (composer.timedOut) throw composer.error
  const ta = composer.value
  onProgress?.('主编输入框已解析')
  let requestSeen = false
  let isHermesRun = false
  let runId = ''
  let runWork = ''
  let runTerminal = false
  let runStatus = ''
  const detachRunIdentityCapture = attachRunIdentityCapture(page, ({ id, work }) => {
    // 创建响应是 run_id 的权威来源；请求监听只作为响应体不可读时的兼容回退。
    runId ||= id
    runWork ||= work
  })
  const observeWriteRequest = (request) => {
    if (request.method() !== 'POST') return
    let path = ''
    let url
    try { url = new URL(request.url()); path = url.pathname } catch { return }
    if (path === '/api/chat/write' || path === '/chat/write' || path === '/api/ai/runs' || path === '/ai/runs') {
      requestSeen = true
      if (path === '/api/ai/runs' || path === '/ai/runs') {
        isHermesRun = true
        runWork = resolveRunWork(url.href, request.postData())
        request.response()
          .then((response) => response?.ok() ? response.json() : null)
          .then((payload) => { runId = payload?.run_id || payload?.id || '' })
          .catch(() => {})
      }
    }
  }
  page.on('request', observeWriteRequest)
  onProgress?.('开始提交主编输入')
  await submitComposerWithDeadline(ta, msg, { timeoutMs: Math.min(30_000, maxMs) })
  onProgress?.('主编输入已提交')
  await sleep(1500)
  let last = ''
  // 累计全程点击的批准次数（此前只记末轮，导致 hermesApproved 假 0）
  let approved = 0
  let staleApproved = 0
  let sawBusy = false
  const t0 = Date.now()
  try {
    while (Date.now() - t0 < maxMs) {
      const mid = await approveAllPending(page, { maxRounds: 3, settleMs: 500 })
      approved += mid.approved
      staleApproved += mid.staleApproved
      await sleep(2500)
      if (runId && !runTerminal) {
        try {
          const apiBase = process.env.E2E_API || 'http://127.0.0.1:3321'
          const qs = runWork ? `?work=${encodeURIComponent(runWork)}` : ''
          const remainingMs = Math.max(1, maxMs - (Date.now() - t0))
          const status = await fetchRunStatusWithTimeout(
            fetch,
            `${apiBase}/ai/runs/${encodeURIComponent(runId)}${qs}`,
            Math.min(15000, remainingMs),
          )
          runStatus = typeof status?.status === 'string' ? status.status : runStatus
          runTerminal = isTerminalHermesRunStatus(status?.status)
        } catch { /* 轮询瞬时失败时继续等事件流 */ }
      }
      const { text, busy } = await page.evaluate(() => {
        const bubbles = [...document.querySelectorAll('.prose-chat')]
        const lastB = bubbles[bubbles.length - 1]
        const visibleSpinner = [...document.querySelectorAll('.animate-spin')]
          .some((node) => node instanceof HTMLElement && node.offsetParent !== null)
        return {
          text: lastB ? lastB.innerText : '',
          busy: !!lastB?.querySelector('.animate-spin') || visibleSpinner,
        }
      })
      // 提案卡已出现也算流可结束
      const hasDraft = await page.locator(DECISION_SELECTORS.draftAccept).count().catch(() => 0)
      sawBusy ||= busy
      if (shouldFinishChiefWait({ busy, sawBusy, requestSeen, isHermesRun, runTerminal, text, previousText: last })
        || (requestSeen && !runId && hasDraft > 0 && !busy)) break
      last = text
    }
  } finally {
    page.off('request', observeWriteRequest)
    detachRunIdentityCapture()
  }
  const tail = await approveAllPending(page, { maxRounds: 4, settleMs: 600 })
  approved += tail.approved
  staleApproved += tail.staleApproved
  return {
    reply: last,
    decisions: { approved, staleApproved },
    run: { id: runId, work: runWork, terminal: runTerminal, status: runStatus },
  }
}

// 作者决策点击：批准写入 / 接受提案 — 必须真实 Playwright click，禁止 API 静默代替。
// 供融合验收与 full_journey 复用。

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

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
 * 主编栏被折叠/被其它 tab 盖住时，恢复可见再找输入框。
 * r6 失败根因：resolveComposer 找不到 textarea（栏折叠或未切到主编）。
 *
 * 铁律：禁止再点已激活的「主编」轨。Rail 对 active tab 再点会传空串 → onCollapse，
 * 会把右坞整栏收起（r14: ensure 一进来就把 right=0 打成 right=1）。
 */
export async function ensureChiefVisible(page) {
  // 关掉可能挡输入的 dialog
  await page.keyboard.press('Escape').catch(() => {})

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

async function resolveComposer(page, preferWrite, { retries = 8 } = {}) {
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
      await ensureChiefVisible(page)
      await sleep(700 + attempt * 200)
    }
  }
  // 诊断：折叠态 + textarea，便于分清「栏收了」还是「壳挂了没输入」
  const diag = await page.evaluate(() => ({
    right: document.querySelector('[data-testid="right-panel"]')?.getAttribute('data-collapsed'),
    four: !!document.querySelector('[data-testid="four-col"]'),
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
 * @param {{ preferWrite?: boolean, maxMs?: number }} opts preferWrite=true 优先写作槽（提案卡）
 */
export async function chiefSay(page, msg, { maxMs = 300000, preferWrite = false } = {}) {
  await ensureChiefVisible(page)
  const ta = await resolveComposer(page, preferWrite)
  await ta.click()
  await ta.fill(msg)
  await ta.press('Enter')
  await sleep(1500)
  let last = ''
  // 累计全程点击的批准次数（此前只记末轮，导致 hermesApproved 假 0）
  let approved = 0
  let staleApproved = 0
  const t0 = Date.now()
  while (Date.now() - t0 < maxMs) {
    const mid = await approveAllPending(page, { maxRounds: 3, settleMs: 500 })
    approved += mid.approved
    staleApproved += mid.staleApproved
    await sleep(2500)
    const { text, busy } = await page.evaluate(() => {
      const bubbles = [...document.querySelectorAll('.prose-chat')]
      const lastB = bubbles[bubbles.length - 1]
      const bodyBusy = /书写中|主编在思考/.test(document.body.innerText || '')
      return {
        text: lastB ? lastB.innerText : '',
        busy: !!lastB?.querySelector('.animate-spin') || bodyBusy,
      }
    })
    const real = text && !text.includes('主编在思考') && text.trim().length > 8
    // 提案卡已出现也算流可结束
    const hasDraft = await page.locator(DECISION_SELECTORS.draftAccept).count().catch(() => 0)
    if ((!busy && real && text === last) || (hasDraft > 0 && !busy)) break
    last = text
  }
  const tail = await approveAllPending(page, { maxRounds: 4, settleMs: 600 })
  approved += tail.approved
  staleApproved += tail.staleApproved
  return { reply: last, decisions: { approved, staleApproved } }
}

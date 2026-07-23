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
  chiefComposer: 'textarea[placeholder="就当前内容问主编…"]',
  /** 章内写作槽 WriteChat（产出提案卡） */
  writeComposer: 'textarea[placeholder="提思路 / 提要求…"]',
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
 */
export async function ensureChiefVisible(page) {
  // 1) 折叠还原钮
  const restore = page.locator('[data-testid="right-restore-button"]')
  if (await restore.count() && await restore.first().isVisible().catch(() => false)) {
    await restore.first().click().catch(() => {})
    await sleep(500)
  }
  // 2) 右坞切到主编 tab
  await page.evaluate(() => {
    try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
  }).catch(() => {})
  const chiefTab = page.getByRole('button', { name: '主编', exact: true }).first()
  if (await chiefTab.count() && await chiefTab.isVisible().catch(() => false)) {
    await chiefTab.click().catch(() => {})
    await sleep(400)
  }
  // 3) 右栏仍 collapsed 再点一次还原
  const collapsed = page.locator('[data-testid="right-panel"][data-collapsed="1"]')
  if (await collapsed.count()) {
    const r2 = page.locator('[data-testid="right-restore-button"]').first()
    if (await r2.isVisible().catch(() => false)) await r2.click().catch(() => {})
    await sleep(400)
  }
}

async function resolveComposer(page, preferWrite, { retries = 3 } = {}) {
  const order = preferWrite
    ? [DECISION_SELECTORS.writeComposer, DECISION_SELECTORS.chiefComposer, 'textarea[data-testid="chief-chat-composer"] textarea', '[data-testid="chief-chat-composer"] textarea', 'textarea[placeholder="就当前内容问主编…"]', 'textarea[placeholder="提思路 / 提要求…"]']
    : [DECISION_SELECTORS.chiefComposer, DECISION_SELECTORS.writeComposer, 'textarea[placeholder="就当前内容问主编…"]', '[data-testid="chief-chat-composer"] textarea', 'textarea[placeholder="提思路 / 提要求…"]']
  for (let attempt = 0; attempt <= retries; attempt++) {
    for (const sel of order) {
      const loc = page.locator(sel).first()
      if (await loc.count() && await loc.isVisible().catch(() => false)) return loc
    }
    // 可见 textarea 回退
    const any = page.locator('textarea:visible').last()
    if (await any.count() && await any.isVisible().catch(() => false)) return any
    if (attempt < retries) {
      await ensureChiefVisible(page)
      await sleep(600)
    }
  }
  throw new Error('resolveComposer: no chief/write textarea visible')
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

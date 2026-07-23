// 探针：世界写入是否出现前端 run-approve 并被 Playwright 真实点击
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage, BASE, openBook } from './lib.mjs'
import {
  chiefSay, approveAllPending, DECISION_SELECTORS,
} from './author_decisions.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const WORK = process.env.E2E_WORK || 'book_b4e72480'
const BOOK = process.env.E2E_BOOK_TITLE || '融合验收·mruwfo36'
const ART = process.env.E2E_ART || new URL('../../../artifacts/e2e-20260722-book_b4e72480', import.meta.url).pathname
const logLines = []
const L = (m) => { const s = `[${new Date().toISOString()}] ${m}`; console.log(s); logLines.push(s) }

async function apiJson(path) {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

async function countApprovals(p) {
  return p.evaluate(() => {
    const appr = document.querySelectorAll('[data-testid="run-approve"]')
    const stale = document.querySelectorAll('[data-testid="run-approve-stale"]')
    const byAria = [...document.querySelectorAll('button')].filter((b) => (b.getAttribute('aria-label') || b.textContent || '').includes('批准'))
    const body = (document.body.innerText || '').slice(0, 4000)
    return {
      runApprove: appr.length,
      stale: stale.length,
      byAria: byAria.length,
      hasPendingText: /批准写入|等待批准|pending|审批/.test(body),
      snippet: body.match(/.{0,40}批准.{0,40}/)?.[0] || '',
    }
  })
}

const out = await withPage(async (p) => {
  mkdirSync(`${ART}/evidence`, { recursive: true })
  L(`BASE=${BASE}`)
  await openBook(p, BOOK)
  await sleep(1500)

  const marker = `HQ审批探针${Date.now().toString(36).slice(-6)}`
  const intentMsg = [
    '请登记/更新本书北极星意图并写入落库(需我审批):',
    `读者感受:压抑中见微光——${marker}`,
    `情感弧:由怯到决——${marker}`,
    '红线:不写超自然明机制;不洗白加害;不表单直填',
    '必须先 s3_get_intent 核实,再用 s3_set_intent 写入。未获批准不得声称已落库。',
  ].join('\n')

  // 发消息后持续轮询审批卡（比 chiefSay 更积极截图）
  const ta = p.locator(DECISION_SELECTORS.chiefComposer).or(p.locator('textarea:visible').last())
  await ta.first().click()
  await ta.first().fill(intentMsg)
  await ta.first().press('Enter')
  L('sent intent write request')

  let totalApproved = 0
  let totalStale = 0
  let sawPending = false
  const pollLog = []
  const t0 = Date.now()
  while (Date.now() - t0 < 300000) {
    const snap = await countApprovals(p)
    pollLog.push({ t: Date.now() - t0, ...snap })
    if (snap.runApprove > 0 || snap.stale > 0 || snap.byAria > 0) sawPending = true
    if (snap.runApprove > 0 || snap.stale > 0 || snap.byAria > 0) {
      await p.screenshot({ path: `${ART}/evidence/approval-ui-pending.png` }).catch(() => {})
      const d = await approveAllPending(p, { maxRounds: 6, settleMs: 900 })
      totalApproved += d.approved
      totalStale += d.staleApproved
      L(`clicked approved=${d.approved} stale=${d.staleApproved}`)
      await p.screenshot({ path: `${ART}/evidence/approval-ui-after-click.png` }).catch(() => {})
    }
    const busy = await p.locator('.animate-spin').count().catch(() => 0)
    const bodyBusy = await p.evaluate(() => /主编在思考|书写中/.test(document.body.innerText || ''))
    if (!bodyBusy && busy === 0 && Date.now() - t0 > 45000 && !sawPending) {
      // 可能已自动落库或失败
      break
    }
    if (!bodyBusy && busy === 0 && totalApproved + totalStale > 0 && Date.now() - t0 > 20000) break
    await sleep(2000)
  }

  let intent = null
  try { intent = await apiJson(`/intent?work=${encodeURIComponent(WORK)}`) } catch (e) { L(`intent fail ${e.message}`) }
  const markerInIntent = JSON.stringify(intent || {}).includes(marker)

  // 角色补丁同样探针
  const charMsg = [
    '请更新/更正角色沈砚的外貌档案并写入落库(需我审批):',
    `appearance:右手食指有握笔老茧,遇冷便僵(${marker})`,
    '必须用 s3_patch_character。先核实再写。',
  ].join('\n')
  await ta.first().click()
  await ta.first().fill(charMsg)
  await ta.first().press('Enter')
  L('sent char patch request')
  const t1 = Date.now()
  while (Date.now() - t1 < 240000) {
    const snap = await countApprovals(p)
    pollLog.push({ t: 'char+' + (Date.now() - t1), ...snap })
    if (snap.runApprove > 0 || snap.stale > 0 || snap.byAria > 0) {
      sawPending = true
      await p.screenshot({ path: `${ART}/evidence/approval-char-pending.png` }).catch(() => {})
      const d = await approveAllPending(p, { maxRounds: 6, settleMs: 900 })
      totalApproved += d.approved
      totalStale += d.staleApproved
      L(`char clicked approved=${d.approved} stale=${d.staleApproved}`)
    }
    const busy = await p.locator('.animate-spin').count().catch(() => 0)
    const bodyBusy = await p.evaluate(() => /主编在思考|书写中/.test(document.body.innerText || ''))
    if (!bodyBusy && busy === 0 && Date.now() - t1 > 40000) break
    await sleep(2000)
  }

  let charApp = ''
  try {
    const ents = await apiJson(`/entities?work=${encodeURIComponent(WORK)}`)
    const list = Array.isArray(ents) ? ents : (ents.entities || ents.items || [])
    for (const e of list) {
      if (String(e.name || e.label || e.id || '').includes('沈砚')) {
        charApp = e.appearance || ''
        break
      }
    }
  } catch (e) { L(`entities fail ${e.message}`) }

  const result = {
    totalApproved,
    totalStale,
    sawPending,
    marker,
    markerInIntent,
    intent,
    charApp,
    charHasMarker: String(charApp).includes(marker),
    pollSamples: pollLog.slice(0, 40),
    form_fill_count: 0,
    ui_approve_proven: totalApproved + totalStale > 0,
  }
  L(`RESULT ${JSON.stringify({ ...result, pollSamples: `n=${pollLog.length}` })}`)
  await p.screenshot({ path: `${ART}/evidence/approval-ui-final.png` }).catch(() => {})
  return result
})

try {
  mkdirSync(`${ART}/evidence`, { recursive: true })
  writeFileSync(`${ART}/evidence/hq-approval-ui-probe.log`, logLines.join('\n') + '\n')
  writeFileSync(`${ART}/evidence/hq-approval-ui-result.json`, JSON.stringify(out, null, 2))
} catch (e) {
  console.error(e)
}
console.log('HQ_APPROVAL_UI', JSON.stringify(out))
// 不强制 exit 1：证据优先；门控在报告里诚实写
if (!out?.ui_approve_proven) process.exit(2)

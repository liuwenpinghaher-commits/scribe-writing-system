// 为已 ready 的冻结质量作业补齐作者十维裁决。所有写入只经网页控件；API 仅回读。
import { chromium } from 'playwright'

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const work = process.env.E2E_WORK
if (!work) throw new Error('E2E_WORK 必填')

const dimensions = [
  '连贯性与因果', '人物真实性', '场景必要性', '结构与节奏', '悬念与兑现',
  '情绪效力', '阅读体验', '语言与声音', '主题与潜台词', '原创性',
]

async function read(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`只读回查失败: ${response.status} ${path}`)
  return response.json()
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  const opener = page.locator(`[data-work-slug="${work}"]`)
  if (await opener.count() !== 1) {
    await page.locator('[data-testid="app-rail"] button[title="切换 / 选择作品"]').click()
    await opener.waitFor({ state: 'visible', timeout: 20000 })
  }
  await opener.click()
  await page.getByRole('button', { name: '参考作品', exact: true }).click()
  await page.getByRole('button', { name: '质量审阅', exact: true }).click()
  // 质量审阅是作品级入口，未从章节详情进入时没有初始 seq；显式填入目标章会触发
  // 既有 ready 作业的只读加载，不能把“创建评价”表单误当成无评价。
  await page.getByLabel('章节号').fill('1')
  await page.getByText('第 1 章 · 10 维', { exact: true }).waitFor({ state: 'visible', timeout: 30000 })

  for (const [index, title] of dimensions.entries()) {
    const score = page.getByRole('spinbutton', { name: `${title} 作者评分` })
    await score.waitFor({ state: 'visible', timeout: 15000 })
    await score.fill(index === 0 ? '5' : '4')
    await page.getByLabel(`${title} 作者裁决`).selectOption(index === 0 ? 'revise' : 'accept')
    await page.getByLabel(`${title} 裁决理由`).fill(
      `作者对「${title}」的裁决：保留有效证据，下一稿强化具体行动的后果。`,
    )
    const card = score.locator("xpath=ancestor::div[contains(@class, 'rounded-lg')][1]")
    if (index === 0) {
      const counter = card.getByRole('checkbox').first()
      if (await counter.count()) await counter.check()
    }
    const submitted = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname.replace(/^\/api/, '') === '/quality/author-judgment'
    ), { timeout: 30000 })
    await card.getByRole('button', { name: '提交裁决', exact: true }).click()
    if ((await submitted).status() !== 201) throw new Error(`${title} 作者裁决提交失败`)
  }

  const evaluation = await read(`/quality/evaluation?seq=1&work=${encodeURIComponent(work)}`)
  if (!evaluation.dimensions?.every((item) => item.author?.reason && item.author?.decision && item.decision_index != null)) {
    throw new Error('十维作者评分、裁决、理由或决策指数未完整回读')
  }
  console.log(`AUTHOR_VERDICTS_UI_SUBMITTED ${JSON.stringify({ dimensions: evaluation.dimensions.length })}`)
} finally {
  await browser.close()
}

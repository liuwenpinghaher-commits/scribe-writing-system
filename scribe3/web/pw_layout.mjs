// 四栏钻取走查(只读):node pw_layout.mjs <v2|old> [书名] [入口文字]
// v2 验证真四栏钻取:入口→目录(常驻)→点条目→详情出现且目录仍在(用户"母题挤一栏"的根治)。
// old 验证旧三栏未被破坏(flag 关仍完好)。只读:仅点入口/目录条目,绝不碰写/存/删。
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:3311'
const SHOTS = '/tmp/goal_shots'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const MODE = process.argv[2] || 'v2'
const TITLE = process.argv[3] || '纸命'
const ENTRY = process.argv[4] || '角色'
const V2 = MODE === 'v2'
const tag = V2 ? 'v2' : 'old'
const VIEW_ENTRIES = new Set(['图谱', '时间线', '仪表盘'])
const SKIP_ITEM = /新建|全部忽略|忽略|接受为角色|网络|导入|北极星|未设作品意图|卡片墙|大纲表|列表|色彩|返回|^\+/
const hasChiefDock = async () => (await p.locator('[data-testid="chief-ctx"], button[aria-label="主编"]').count()) > 0

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1600, height: 950 } })
const errs = []
p.on('pageerror', (e) => errs.push('PAGEERR ' + e.message))
p.on('console', (m) => { if (m.type() === 'error') { const t = m.text(); if (!/ERR_CONNECTION_CLOSED|favicon/.test(t)) errs.push('CONSOLE ' + t.slice(0, 160)) } })

await p.addInitScript((v) => { try { if (v) localStorage.setItem('s3.layout.v2', '1'); else localStorage.removeItem('s3.layout.v2') } catch {} }, V2)

const out = { mode: V2 ? 'v2-四栏' : '旧三栏', title: TITLE, entry: ENTRY }
try {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(1000)
  await p.getByText(TITLE, { exact: false }).first().click()
  await sleep(2600)

  if (!V2) {
    // 旧三栏:应有项目树 treeitem、无 four-col
    await p.waitForSelector('[role="treeitem"]', { timeout: 8000 }).catch(() => {})
    out.hasFourCol = await p.locator('[data-testid="four-col"]').count() > 0
    out.treeitems = await p.locator('[role="treeitem"]').count()
    out.hasChief = await hasChiefDock()
    await p.screenshot({ path: `${SHOTS}/layout_old.png` })
    out.ok = true
  } else {
    // 四栏:验证 four-col + entry-rail
    await p.waitForSelector('[data-testid="four-col"]', { timeout: 8000 })
    out.hasFourCol = true
    out.entryButtons = await p.locator('[data-testid="entry-rail"] button').count()
    await p.screenshot({ path: `${SHOTS}/four_1_open.png` })

    // 1) 点一级入口(如"角色")→ 栏2 目录应出现列表
    await p.locator('[data-testid="entry-rail"] button', { hasText: ENTRY }).first().click()
    await sleep(1500)
    if (VIEW_ENTRIES.has(ENTRY)) {
      out.afterEntry = {
        hasDirectory: await p.locator('[data-testid="col-directory"]').count() > 0,
        hasDetail: await p.locator('[data-testid="detail"]').count() > 0,
        detailText: (await p.locator('[data-testid="detail"]').first().innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 90),
        hasChief: await hasChiefDock(),
      }
      await p.screenshot({ path: `${SHOTS}/four_view_${ENTRY}.png` })
      out.ok = out.afterEntry.hasDetail && !out.afterEntry.hasDirectory
      out.errs = errs
      await b.close()
      console.log(JSON.stringify(out, null, 2))
      process.exit(out.ok ? 0 : 1)
    }
    out.afterEntry = {
      hasDirectory: await p.locator('[data-testid="col-directory"]').count() > 0,
      dirButtons: await p.locator('[data-testid="col-directory"] button').count(),
    }
    await p.screenshot({ path: `${SHOTS}/four_2_directory.png` })

    // 2) 点目录里第一个条目 → 栏3 详情出现,且栏2 目录仍在(关键)
    const dirBtns = p.locator('[data-testid="col-directory"] button')
    const n = await dirBtns.count()
    // 点第一个"可见的真实条目":跳过隐藏控制按钮(全部忽略/→/+新建 等)
    let clicked = false
    for (let i = 0; i < n; i++) {
      const btn = dirBtns.nth(i)
      if (!(await btn.isVisible().catch(() => false))) continue
      const txt = ((await btn.innerText().catch(() => '')) || '').trim()
      if (!txt || SKIP_ITEM.test(txt)) continue
      await btn.click(); clicked = true; out.clickedItemText = txt.slice(0, 40); break
    }
    out.clickedItem = clicked
    await sleep(2000)
    out.afterItem = {
      directoryStillThere: await p.locator('[data-testid="col-directory"]').count() > 0,  // ← 核心:目录常驻
      hasDetail: await p.locator('[data-testid="detail"]').count() > 0,
      detailText: (await p.locator('[data-testid="detail"]').first().innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 90),
      hasChief: await hasChiefDock(),
    }
    await p.screenshot({ path: `${SHOTS}/four_3_detail.png` })
    out.ok = true
  }
} catch (e) {
  out.ok = false; out.err = e.message
  try { await p.screenshot({ path: `${SHOTS}/layout_${tag}_error.png` }) } catch {}
}
out.errs = errs
await b.close()
console.log(JSON.stringify(out, null, 2))

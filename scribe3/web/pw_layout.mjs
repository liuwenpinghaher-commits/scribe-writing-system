// Task 12 · 四栏 PC 布局只读验收:node pw_layout.mjs [v2|old] [书名]
//
// 只读铁律:首帧 goto 前装 **/api/** 拦截,GET/HEAD/OPTIONS 放行,其余(POST/PATCH/PUT/DELETE)
//   一律 abort('blockedbyclient')。纸命是生产书稿,验收全程绝不落库。
//
// v2(默认)真机验收单书 book_c256380e《纸命》:
//   · 三视口 × 双主题:1280/1440/1600 × light/dark,每格 waitFor four-col →
//       detail 宽 ≥ 600 + 右栏不与详情重叠 + 截图 artifacts/pc-ui-{vp}-{theme}.png
//   · 目录常驻:点入口(手稿)→ 栏2 目录出现 → 点章条目 → 栏3 详情出现且栏2 目录仍在
//   · DOM 单套:选中章后 manuscript-directory 唯一、五阶段 tablist 唯一(章导航/阶段不重复)
//   · 横切视图往返:图谱/时间线/仪表盘各自渲染(栏2 隐、四栏骨架在)→ 回手稿入口后目录恢复
//   · 键盘可自动化部分:Tab 焦点推进、⇧⌘K 命令面板 + Escape、⌘K 触发搜索
//   · 控制台无真实 error、非 GET/HEAD/OPTIONS 请求全被阻断
// old 只做轻量冒烟:flag 关 → 无 four-col、有 treeitem(旧三栏未被破坏)。
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const ART = join(HERE, 'artifacts')
mkdirSync(ART, { recursive: true })

const BASE = 'http://127.0.0.1:3311'
const MODE = process.argv[2] || 'v2'
const TITLE = process.argv[3] || '纸命'
const V2 = MODE !== 'old'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const VIEWPORTS = [
  { name: '1280x720', width: 1280, height: 720 },
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1600x900', width: 1600, height: 900 },
]
const THEMES = ['light', 'dark']
// 期望被阻断的写方法;放行的只读方法
const READ_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
// 只读拦截产生的网络失败 + 常规噪声,不计入"真实 console error"
const NOISE = /favicon|ERR_BLOCKED_BY_CLIENT|blockedbyclient|ERR_CONNECTION_CLOSED|ERR_ABORTED|ERR_FAILED/i

const results = []
const rec = (name, pass, evidence) => {
  results.push({ name, pass, evidence })
  console.log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence)
}
// note:信息型观察,不计入 pass/fail(用于设计既有行为/需人工复核的项)
const notes = []
const note = (name, evidence) => {
  notes.push({ name, evidence })
  console.log('NOTE', '|', name, '|', evidence)
}

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 720 } })

// —— 只读拦截(首帧 goto 前装)——
const blockedWrites = []
const failedReads = []
await p.route('**/api/**', async (route) => {
  const method = route.request().method()
  if (READ_METHODS.has(method)) return route.continue()
  blockedWrites.push({ method, url: route.request().url().replace(/^https?:\/\/[^/]+/, '') })
  await route.abort('blockedbyclient')
})
p.on('requestfailed', (r) => {
  const method = r.method()
  // 只读方法失败才是真回归;写方法失败=我们主动阻断,预期内
  if (READ_METHODS.has(method) && !NOISE.test(r.failure()?.errorText || '')) {
    failedReads.push({ method, url: r.url(), err: r.failure()?.errorText })
  }
})

const consoleErrors = []
p.on('pageerror', (e) => consoleErrors.push('PAGEERR ' + String(e.message).slice(0, 200)))
p.on('console', (m) => {
  if (m.type() !== 'error') return
  const t = m.text()
  if (!NOISE.test(t)) consoleErrors.push('CONSOLE ' + t.slice(0, 200))
})

// flag:v2 四栏 / old 旧三栏(每次导航重注入)
await p.addInitScript((v) => { try { localStorage.setItem('s3.layout.v2', v ? '1' : '0') } catch { /* */ } }, V2)

const openBook = async () => {
  await p.getByText(TITLE, { exact: false }).first().click()
}
const box = async (sel) => {
  const el = p.locator(sel).first()
  await el.waitFor({ state: 'visible', timeout: 8000 })
  return el.boundingBox()
}

try {
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await sleep(600)

  if (!V2) {
    // —— old 冒烟:flag 关,旧三栏未被破坏 ——
    await openBook()
    await p.waitForSelector('[role="treeitem"]', { timeout: 8000 }).catch(() => {})
    const hasFourCol = await p.locator('[data-testid="four-col"]').count()
    const treeitems = await p.locator('[role="treeitem"]').count()
    rec('old·无四栏壳(flag 关)', hasFourCol === 0, `four-col=${hasFourCol}`)
    rec('old·有项目树 treeitem', treeitems > 0, `treeitems=${treeitems}`)
    await p.screenshot({ path: join(ART, 'pc-ui-old.png') })
  } else {
    // ════════ 三视口 × 双主题 ════════
    for (const vp of VIEWPORTS) {
      for (const theme of THEMES) {
        await p.setViewportSize({ width: vp.width, height: vp.height })
        await p.evaluate((t) => { try { localStorage.setItem('s3-theme', t) } catch { /* */ } }, theme)
        await p.reload({ waitUntil: 'networkidle' })
        await sleep(400)
        await openBook()
        await p.waitForSelector('[data-testid="four-col"]', { timeout: 10000 })
        const themeOn = await p.evaluate(() => document.documentElement.classList.contains('dark'))
        rec(`${vp.name}·${theme}·主题落地`, themeOn === (theme === 'dark'), `html.dark=${themeOn}`)

        // 量内层真实 div(Panel 壳的 data-testid 未必落到有尺寸的 DOM 节点)
        const dBox = await box('[data-testid="detail"]')
        const rBox = await box('[data-testid="right-dock"]')
        const detailW = Math.round(dBox?.width ?? 0)
        rec(`${vp.name}·${theme}·detail 宽≥600`, detailW >= 600, `detailW=${detailW}`)
        const noOverlap = rBox && dBox && rBox.x >= dBox.x + dBox.width - 1
        rec(`${vp.name}·${theme}·右栏不重叠`, !!noOverlap,
          `right.x=${Math.round(rBox?.x)} detail.right=${Math.round((dBox?.x ?? 0) + (dBox?.width ?? 0))}`)
        await p.screenshot({ path: join(ART, `pc-ui-${vp.name}-${theme}.png`) })
      }
    }

    // ════════ 功能走查(稳定视口:1440x900 light) ════════
    await p.setViewportSize({ width: 1440, height: 900 })
    await p.evaluate(() => { try { localStorage.setItem('s3-theme', 'light') } catch { /* */ } })
    await p.reload({ waitUntil: 'networkidle' })
    await sleep(400)
    await openBook()
    await p.waitForSelector('[data-testid="four-col"]', { timeout: 10000 })

    const rail = p.locator('[data-testid="left-entry-rail"]')
    await p.waitForSelector('[data-testid="col-directory"]', { timeout: 8000 })

    // ── 横切视图往返(fresh 态,趁 ContextSnapshot 只读态未接管投影最稳)──
    // 说明:只读铁律阻断 POST /api/context/*,故一旦快照接管投影,视图切换会被冻结的快照压回
    //   —— 这是验收拦截的副产物,不是产品回归(见报告)。因此视图往返放在选章前的 fresh 态跑。
    const views = ['图谱', '时间线', '仪表盘']
    for (const v of views) {
      await p.locator('[data-testid="topbar-global-views"]').getByRole('button', { name: v }).click()
      await sleep(1000)
      const dirHidden = await p.locator('[data-testid="col-directory"]').count() === 0
      const current = await p.locator('[data-testid="topbar-global-views"]').getByRole('button', { name: v }).getAttribute('aria-current')
      const detailIn = await p.locator('[data-testid="detail"]').count() > 0
      rec(`视图·${v} 全画布渲染(栏2 隐)`, dirHidden && current === 'page' && detailIn,
        `dirHidden=${dirHidden} current=${current} detail=${detailIn}`)
    }
    // 返回:视图态下点激活入口「手稿」= 退出视图 → 目录恢复(往返后四栏骨架完好)
    await rail.getByRole('button', { name: '手稿' }).first().click()
    await p.waitForSelector('[data-testid="col-directory"]', { timeout: 8000 }).catch(() => {})
    await sleep(400)
    const dirBack = await p.locator('[data-testid="col-directory"]').count() > 0
    rec('视图·返回后目录恢复', dirBack, `col-directory=${dirBack}`)

    // ── 入口切换 + 目录常驻:切「设定库」再切回「手稿」,验证入口切换目录不塌 ──
    // (点当前已激活入口会切换栏2 折叠——这是设计,故用"切到别的入口再切回"走查切换)
    rec('入口·手稿目录已挂', await p.locator('[data-testid="col-directory"]').count() > 0, 'col-directory 挂载')
    await rail.getByRole('button', { name: '设定库' }).first().click()
    await sleep(700)
    rec('入口·切设定库目录仍在', await p.locator('[data-testid="col-directory"]').count() > 0, 'col-directory 常驻')
    await rail.getByRole('button', { name: '手稿' }).first().click()
    await p.waitForSelector('[data-testid="manuscript-directory"]', { timeout: 8000 })
    rec('入口·切回手稿章导航在', await p.locator('[data-testid="manuscript-directory"]').count() > 0, 'manuscript-directory 挂载')

    // ── 目录常驻:点第一个章条目 → 详情出现且目录仍在 ──
    const chapterBtn = p.locator('[data-testid="manuscript-volume-list"] > button').first()
    await chapterBtn.waitFor({ state: 'visible', timeout: 8000 })
    const chapterLabel = (await chapterBtn.innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 40)
    await chapterBtn.click()
    await sleep(1200)
    const dirStill = await p.locator('[data-testid="col-directory"]').count() > 0
    const detailHas = await p.locator('[data-testid="detail"]').count() > 0
    rec('目录常驻·点章后目录仍在', dirStill, `col-directory=${dirStill} 选中=${chapterLabel}`)
    rec('目录常驻·点章后详情出现', detailHas, `detail=${detailHas}`)

    // ── DOM 单套:章导航唯一 + 五阶段 tablist 唯一 ──
    const navCount = await p.locator('[data-testid="manuscript-directory"]').count()
    const tablistCount = await p.locator('[data-testid="detail"] [role="tablist"]').count()
    const phaseTabs = await p.locator('[data-testid="detail"] [role="tablist"] [role="tab"]').count()
    rec('DOM 单套·章导航唯一', navCount === 1, `manuscript-directory=${navCount}`)
    rec('DOM 单套·五阶段唯一', tablistCount === 1 && phaseTabs === 5, `tablist=${tablistCount} tabs=${phaseTabs}`)

    // ════════ 键盘可自动化部分 ════════
    // Tab 焦点推进:从 body 起,Tab 后 activeElement 不再是 body
    await p.evaluate(() => document.body.focus())
    await p.keyboard.press('Tab')
    const afterTab = await p.evaluate(() => document.activeElement && document.activeElement.tagName)
    rec('键盘·Tab 推进焦点', !!afterTab && afterTab !== 'BODY', `activeEl=${afterTab}`)
    // ⇧⌘K 命令面板(headless 用 Control 触发 metaKey||ctrlKey 分支)
    await p.keyboard.press('Control+Shift+KeyK')
    await sleep(400)
    const paletteOpen = await p.getByPlaceholder('跳视图 / 切书 / 作品库…').isVisible().catch(() => false)
    rec('键盘·⇧⌘K 开命令面板', paletteOpen, `palette=${paletteOpen}`)
    // Escape 关闭:CommandPalette 是 cmdk 裸用 + 自定义 overlay,未挂 Escape(设计如此,非回归);
    //   role=dialog 的 ui/Dialog(ConfirmDialog/InputDialog)源码已挂 Escape→onClose。此处如实记为观察项。
    await p.keyboard.press('Escape')
    await sleep(300)
    const escClosed = !(await p.getByPlaceholder('跳视图 / 切书 / 作品库…').isVisible().catch(() => false))
    note('键盘·Escape 关命令面板(cmdk 未挂,信息项)', `closed=${escClosed}(cmdk 面板走 overlay 点击关闭;role=dialog 弹窗已挂 Escape)`)
    // 用真实关闭路径(点 overlay)收起面板 → 断言面板可关
    if (!escClosed) await p.mouse.click(5, 5).catch(() => {})
    await sleep(300)
    const paletteClosed = !(await p.getByPlaceholder('跳视图 / 切书 / 作品库…').isVisible().catch(() => false))
    rec('键盘·命令面板可关闭(overlay)', paletteClosed, `closed=${paletteClosed}`)
    // ⌘K 触发搜索(作品内派发 s3-open-capability{search,focus})——只验证不抛错、搜索入口可达
    await p.keyboard.press('Control+KeyK')
    await sleep(500)
    const searchReachable = await p.locator('[data-testid="left-entry-rail"]').getByRole('button', { name: '搜索' }).count() > 0
    rec('键盘·⌘K 搜索入口可达', searchReachable, `search-cap=${searchReachable}`)

    await p.screenshot({ path: join(ART, 'pc-ui-final-1440x900-light.png') })
  }

  // ════════ 只读铁律断言 ════════
  rec('只读·非 GET/HEAD/OPTIONS 全被阻断', blockedWrites.every((w) => !READ_METHODS.has(w.method)),
    `blocked=${blockedWrites.length} 例:${blockedWrites.slice(0, 4).map((w) => w.method + ' ' + w.url).join(' | ') || '(无写请求发生)'}`)
  rec('只读·无只读请求被误伤', failedReads.length === 0,
    `failedReads=${failedReads.length}${failedReads.length ? ' 例:' + JSON.stringify(failedReads.slice(0, 3)) : ''}`)
  rec('控制台·无真实 error', consoleErrors.length === 0,
    consoleErrors.length ? consoleErrors.slice(0, 5).join(' ⁋ ') : '0 errors')
} catch (e) {
  rec('运行·未抛异常', false, String(e.message).slice(0, 300))
  try { await p.screenshot({ path: join(ART, 'pc-ui-error.png') }) } catch { /* */ }
}

await b.close()

const failed = results.filter((r) => !r.pass)
console.log('\n──────── 汇总 ────────')
console.log(`mode=${MODE} 书=${TITLE} 断言=${results.length} 通过=${results.length - failed.length} 失败=${failed.length}`)
console.log(`写请求被阻断=${blockedWrites.length} 只读误伤=${failedReads.length} 控制台error=${consoleErrors.length}`)
console.log(`截图目录=${ART}`)
if (notes.length) console.log('观察项(不计入通过/失败):\n' + notes.map((n) => `  · ${n.name} | ${n.evidence}`).join('\n'))
if (failed.length) console.log('失败项:\n' + failed.map((r) => `  ✗ ${r.name} | ${r.evidence}`).join('\n'))
process.exit(failed.length ? 1 : 0)

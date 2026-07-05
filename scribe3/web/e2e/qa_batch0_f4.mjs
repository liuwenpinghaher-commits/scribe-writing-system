// ── e2e · 批0-F4:设定私密掩码占位符不回传销毁真值(彻查 F-1/F-2 前端防线) ──────────
// 运行:cd scribe3/web && node e2e/qa_batch0_f4.mjs(需 dev :3311 + 后端 :3321 在跑)
// 数据纪律:全程只用「临时 work」(REST 建角色/势力设真实私密值),用后 DELETE 整个 work,零残留。
//
// 复现的 bug:角色/势力勾私密后 GET 返回掩码 `🔒 私密`;DetailView `save=(k,v)=>onUpdate({...row,[k]:v})`
// 整行回传含掩码值 → 编辑任一非私密字段即把 `🔒 私密` 写回 → 真实前史/势力运作被永久覆盖销毁。
//
// 断言(修前必须 FAIL,修后 PASS):
//   ① 角色改「恐惧」→ PATCH /characters 请求体不含掩码值(前端防线)
//   ② 改非私密字段后 GET ?reveal_secret=true 前史仍为真值(角色 PATCH 路径:缺字段=不更新)
//   ③ 取消勾选私密后(不 reveal)前史即真值(未被销毁)
//   ④ 势力改「意识形态」→ POST /factions 请求体不含掩码值(前端防线)
//   ④b 势力 reveal 私下运作不是掩码(掩码未被持久化;注:add_faction 是 DELETE+CREATE,
//        standalone 下缺字段→None,真值存活需后端 B4「读回旧值 on missing」,见报告遗留)
import { chromium } from 'playwright'

const API = 'http://127.0.0.1:3321'
const FRONT = 'http://127.0.0.1:3311'
const MASK = '🔒 私密'                       // 与后端 app.py `_mask_field` / _SECRET_MASK 同源
const ts = Date.now()
const TITLE = `F4临时书-${ts}`
const CHAR = `F4角色-${ts}`
const FAC = `F4势力-${ts}`
const REAL_BS = `真实前史XYZ-${ts}`
const REAL_PO = `真实运作ABC-${ts}`

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qaF4]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const jpost = (p, b) => fetch(`${API}${p}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then((r) => r.json())
const jget = (p) => fetch(`${API}${p}`).then((r) => r.json())
const jdel = (p) => fetch(`${API}${p}`, { method: 'DELETE' }).then((r) => r.json()).catch(() => ({}))

const run = async () => {
  // —— 建临时 work + 私密角色 + 私密势力(真实值)——
  const cw = await jpost('/works', { title: TITLE })
  const SLUG = cw.slug
  log('temp work:', SLUG)
  await jpost(`/characters?work=${SLUG}`, { name: CHAR, backstory: REAL_BS, backstory_secret: true })
  await jpost(`/factions?work=${SLUG}`, { name: FAC, ideology: '旧意识形态', private_operation: REAL_PO, private_operation_secret: true })

  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
    page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

    // 捕获写请求体:前端防线核心 —— 掩码绝不出现在 payload
    let charPatch = null, facPost = null
    page.on('request', (req) => {
      try {
        if (req.method() === 'PATCH' && req.url().includes('/characters/')) charPatch = req.postDataJSON()
        if (req.method() === 'POST' && req.url().includes('/factions')) facPost = req.postDataJSON()
      } catch { /* 非 JSON 体忽略 */ }
    })

    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: new RegExp(`F4临时书-${ts}`) }).first().click()

    const left = page.getByTestId('left')      // 项目树栏
    const detail = page.getByTestId('detail')  // 中间详情栏(CodexDetail/DetailView)

    // —— 展开「角色」分类 → 点角色叶(codex_root 默认展开,分类需点开)——
    await left.getByRole('button', { name: /^角色/ }).first().click()
    const charLeaf = left.getByRole('button', { name: new RegExp(CHAR) })
    await charLeaf.waitFor({ timeout: 10000 })
    await charLeaf.click()

    // DetailView 就绪:前史字段显示掩码占位符
    await detail.getByText(MASK, { exact: true }).first().waitFor({ timeout: 8000 })
    rec('前史字段 UI 显示掩码占位符', true, `见 "${MASK}"`)

    // —— 编辑「恐惧」(非私密字段)——
    await detail.getByRole('button', { name: '+ 添加恐惧' }).click()
    const fearInput = detail.getByPlaceholder('角色最怕什么')
    await fearInput.fill(`新恐惧-${ts}`)
    await fearInput.press('Enter')
    await page.waitForTimeout(900)

    // ① 前端防线:PATCH 请求体不含掩码值
    const patchMaskKeys = charPatch ? Object.entries(charPatch).filter(([, v]) => v === MASK).map(([k]) => k) : []
    rec('① 角色改「恐惧」→ PATCH 请求体不含掩码',
      !!charPatch && patchMaskKeys.length === 0,
      `sent backstory=${JSON.stringify(charPatch?.backstory)} fear=${JSON.stringify(charPatch?.fear)} maskKeys=${JSON.stringify(patchMaskKeys)}`)

    // ② 端到端:reveal 前史仍为真值
    const cReveal = (await jget(`/entities?work=${SLUG}&reveal_secret=true`)).find((e) => e.name === CHAR)
    rec('② 改非私密字段后 reveal 前史仍为真值',
      cReveal?.backstory === REAL_BS,
      `reveal backstory=${JSON.stringify(cReveal?.backstory)} 期望=${JSON.stringify(REAL_BS)}`)

    // ③ 取消勾选私密 → 不 reveal 也见真值(未被销毁)。用 click 触发一次 onChange
    //   (受控 checkbox 由 row 驱动,uncheck 会与 reload 重渲染竞态)。
    await detail.locator('#backstory_secret_cb').click()
    await page.waitForTimeout(1000)
    const cPlain = (await jget(`/entities?work=${SLUG}`)).find((e) => e.name === CHAR)   // 不 reveal
    rec('③ 取消勾选私密后(不 reveal)前史即真值',
      cPlain?.backstory_secret === false && cPlain?.backstory === REAL_BS,
      `secret=${cPlain?.backstory_secret} backstory=${JSON.stringify(cPlain?.backstory)}`)

    // —— 势力:改「意识形态」(非私密字段)——
    await left.getByRole('button', { name: /^势力/ }).first().click()
    const facLeaf = left.getByRole('button', { name: new RegExp(FAC) })
    await facLeaf.waitFor({ timeout: 10000 })
    await facLeaf.click()
    const ideoBox = detail.getByText('旧意识形态', { exact: true }).first()
    await ideoBox.waitFor({ timeout: 8000 })
    await ideoBox.click()
    const ideoInput = detail.getByPlaceholder('输入意识形态...')
    await ideoInput.fill(`新意识形态-${ts}`)
    await ideoInput.evaluate((el) => el.blur())
    await page.waitForTimeout(900)

    // ④ 前端防线:POST 请求体不含掩码值
    const facMaskKeys = facPost ? Object.entries(facPost).filter(([, v]) => v === MASK).map(([k]) => k) : []
    rec('④ 势力改「意识形态」→ POST 请求体不含掩码',
      !!facPost && facMaskKeys.length === 0,
      `sent private_operation=${JSON.stringify(facPost?.private_operation)} ideology=${JSON.stringify(facPost?.ideology)} maskKeys=${JSON.stringify(facMaskKeys)}`)

    // ④b 势力:持久化值不是掩码(掩码未落库;standalone→None,真值存活需后端 B4)
    const fReveal = (await jget(`/factions?work=${SLUG}&reveal_secret=true`)).find((f) => f.name === FAC)
    rec('④b 势力 reveal 私下运作非掩码(真值未被掩码覆盖;standalone→None,需后端 B4 保真)',
      fReveal && fReveal.private_operation !== MASK,
      `reveal private_operation=${JSON.stringify(fReveal?.private_operation)} 真值=${JSON.stringify(REAL_PO)}`)

    rec('零 console error', consoleErrors.length === 0, consoleErrors.length ? consoleErrors.join(' ;; ') : 'clean')
  } finally {
    await browser.close()
    // —— 数据纪律:删整个临时 work,零残留 ——
    await jdel(`/works/${SLUG}`)
    const works = await jget('/works').catch(() => [])
    const residual = Array.isArray(works) && works.some((w) => w.slug === SLUG)
    rec('数据纪律:临时 work 已删除零残留', !residual, `residual=${residual} slug=${SLUG}`)
  }

  const fails = results.filter((r) => !r.pass)
  console.log(`\n==== SUMMARY: ${results.length - fails.length}/${results.length} PASS ====`)
  if (fails.length) { fails.forEach((f) => console.log('FAIL:', f.name, '|', f.evidence)); process.exitCode = 2 }
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })

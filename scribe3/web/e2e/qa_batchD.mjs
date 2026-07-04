// ── e2e · 批D 能力接线(P1-4 命题/secret 生产入口 + B-5 角色关系入口)──
// 运行:cd scribe3/web && node e2e/qa_batchD.mjs
// 数据纪律:全程在【临时 work】上做(POST /works 建 → 末尾 DELETE /works 删),零残留,不碰任何真书。
// 验证链:
//   件1 ① 项目树设定支出现「命题」分类;② 新建命题 UI → POST /facts 带 secret+leak_markers;
//        ③ GET /facts 落库(is_secret,value 屏蔽);④ find_leaks(POST /check)检出该私密命题泄露。
//   件2 ① 角色详情有「角色关系」区+建立入口;② 建立关系 UI → POST /character-relations;
//        ③ 关系 tab 显示;④ GET /character-relations 返回。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const TITLE = `批D验证-${ts}`
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log(pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }
const jget = (path, work) => fetch(`${API}${path}${path.includes('?') ? '&' : '?'}work=${work}`).then((r) => r.json())
const jpost = (path, body, work) => fetch(`${API}${path}${path.includes('?') ? '&' : '?'}work=${work}`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
}).then((r) => r.json())

let slug = null
const captured = { facts: [], supersede: [], relations: [] }

const run = async () => {
  // ── API setup:临时 work + 2 角色 + 第1章 ──
  const w = await fetch(`${API}/works`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: TITLE }) }).then((r) => r.json())
  slug = w.slug
  console.log('临时 work:', slug, '标题:', TITLE)
  await jpost('/characters', { name: '甲测' }, slug)
  await jpost('/characters', { name: '乙测' }, slug)
  await jpost('/save-chapter', { seq: 1, prose: '', title: '第1章', focalizer: 'role:甲测' }, slug)

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  const consoleErrors = []
  page.on('console', (m) => { if (m.type() === 'error') { const t = m.text(); if (!/favicon|ERR_CONNECTION/.test(t)) consoleErrors.push(t.slice(0, 200)) } })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 200)))
  page.on('request', (req) => {
    const u = req.url(), m = req.method()
    if (m === 'POST' && /\/facts(\?|$)/.test(u) && !/supersede/.test(u)) captured.facts.push(req.postData())
    if (m === 'POST' && /\/facts\/supersede/.test(u)) captured.supersede.push(req.postData())
    if (m === 'POST' && /\/character-relations(\?|$)/.test(u) && !/evolve|end/.test(u)) captured.relations.push(req.postData())
  })

  // ── 进临时书 ──
  await page.goto(FRONT, { waitUntil: 'networkidle' }); await sleep(900)
  await page.getByText(TITLE, { exact: false }).first().click(); await sleep(2600)
  await page.waitForSelector('[role="treeitem"]', { timeout: 10000 }).catch(() => {})
  const left = page.getByTestId('left')
  const detail = page.getByTestId('detail')

  // ════ 件1 ① 命题分类出现在项目树 ════
  // 树行 button 的 accessible name 含 count 角标(如「命题 0」),故用 regex 而非 exact。
  const treeText = (await left.innerText().catch(() => '')).replace(/\s+/g, ' ')
  const propCat = left.getByRole('button', { name: /命题/ }).first()
  const catVisible = await propCat.isVisible().catch(() => false)
  rec('件1① 项目树设定支出现「命题」分类', catVisible, `命题分类可见=${catVisible} | 树文本="${treeText.slice(0, 200)}"`)
  await propCat.click(); await sleep(1000)

  // 新建命题(空态「点此新建」,否则「新建」)
  if (await detail.getByText('点此新建').count()) await detail.getByText('点此新建').first().click()
  else await detail.getByRole('button', { name: '新建', exact: true }).first().click()
  await sleep(1000)

  // 填表:文本字段 +添加X→输入→Enter 提交;textarea(值)靠 Tab 失焦提交(Enter 不提交、Escape 取消)。
  // 关键:每个字段独立提交后再开下一个,避免「上字段失焦 commit→setDraft 重渲染」把刚打开的下字段输入框冲掉。
  const addField = async (labelRe, val, commit = 'enter') => {
    const btn = detail.getByRole('button', { name: labelRe }).first()
    await btn.click(); await sleep(420)
    await page.keyboard.type(val); await sleep(180)
    await page.keyboard.press(commit === 'tab' ? 'Tab' : 'Enter'); await sleep(400)
  }
  await addField(/添加主体/, 'role:乙测')
  await addField(/添加属性/, '真身')
  await addField(/添加值/, '狐妖真身', 'tab')       // value 是 textarea → Tab 失焦提交
  await addField(/添加泄露标记词/, '狐尾')          // array_csv(text)→ Enter 提交
  await detail.getByText(/命题私密/).first().click(); await sleep(400)   // 勾选 secret
  await detail.getByRole('button', { name: '创建' }).click(); await sleep(1800)
  const errText = await detail.locator('.text-danger').first().innerText().catch(() => '')
  if (errText) console.log('创建错误:', errText)

  const factBody = captured.facts.map((b) => { try { return JSON.parse(b) } catch { return {} } }).slice(-1)[0] || {}
  rec('件1② 新建命题 POST /facts 带 secret=true', factBody.secret === true, `body.secret=${factBody.secret}`)
  rec('件1③ 新建命题 POST /facts 带 leak_markers=[狐尾]', Array.isArray(factBody.leak_markers) && factBody.leak_markers.includes('狐尾'), `leak_markers=${JSON.stringify(factBody.leak_markers)} entity=${factBody.entity} attr=${factBody.attribute}`)

  // GET /facts 落库验证(私密 → is_secret=true,value 屏蔽为 null)
  const facts = await jget('/facts?chapter=1', slug)
  const mine = (facts || []).find((f) => f.entity === 'role:乙测' && f.attribute === '真身')
  rec('件1④ 命题落库(GET /facts is_secret=true,value 被屏蔽)', !!mine && mine.is_secret === true && mine.value === null, `found=${!!mine} is_secret=${mine?.is_secret} value=${JSON.stringify(mine?.value)}`)

  // ── find_leaks 可用:POST /check 扫含 leak_marker 的散文 ──
  const prose = '夜里巷子空无一人,他分明看见那人身后垂着一条狐尾,拖在青石板上。'
  const chk = await jpost('/check?seq=1', { prose, focalizer: 'role:甲测' }, slug)
  const leakHit = (chk.leaks || []).some((l) => l.marker === '狐尾')
  rec('件1⑤ find_leaks 检出 UI 建的私密命题泄露(marker=狐尾)', leakHit, `leaks=${JSON.stringify(chk.leaks)}`)

  // ── 件1⑥ 命题详情页动作:创建后中区即 PropositionDetail;驱动「超越(改值)」→ POST /facts/supersede ──
  const propDetail = detail.getByTestId('proposition-detail')
  const detailVisible = await propDetail.isVisible().catch(() => false)
  const hasActions = detailVisible
    && await propDetail.getByRole('button', { name: /超越/ }).count() > 0
    && await propDetail.getByRole('button', { name: /让读者遗忘/ }).count() > 0
    && await propDetail.getByRole('button', { name: /删除命题/ }).count() > 0
  rec('件1⑥ 命题详情块渲染(超越/遗忘/删除 动作齐备)', hasActions, `detail可见=${detailVisible} 动作齐=${hasActions}`)
  if (detailVisible) {
    await propDetail.getByRole('button', { name: /超越/ }).first().click(); await sleep(400)
    await propDetail.locator('textarea').first().fill('已被识破的假身'); await sleep(200)
    await propDetail.locator('input[type="number"]').first().fill('3'); await sleep(200)
    await propDetail.getByRole('button', { name: '确认超越' }).click(); await sleep(1400)
    const supBody = captured.supersede.map((b) => { try { return JSON.parse(b) } catch { return {} } }).slice(-1)[0] || {}
    rec('件1⑦ 超越动作 POST /facts/supersede(entity_id/attribute/value/since_chapter)',
      supBody.entity_id === 'role:乙测' && supBody.attribute === '真身' && supBody.value === '已被识破的假身' && supBody.since_chapter === 3,
      `body=${JSON.stringify(supBody)}`)
  }

  // ════ 件2 角色关系 ════
  await left.getByRole('button', { name: /^角色/ }).first().click(); await sleep(800)
  await detail.getByText('甲测', { exact: false }).first().click(); await sleep(1500)

  const relSection = detail.getByTestId('dynamic-relations')
  const relVisible = await relSection.isVisible().catch(() => false)
  rec('件2① 角色详情含「角色关系」区(带建立入口)', relVisible, `关系区可见=${relVisible}`)

  await detail.getByRole('button', { name: /建立关系/ }).click(); await sleep(700)
  const dstSel = relSection.locator('select').first()
  await dstSel.selectOption({ label: '乙测' }).catch(async () => {
    const v = await dstSel.locator('option', { hasText: '乙测' }).first().getAttribute('value').catch(() => null)
    if (v) await dstSel.selectOption(v)
  }); await sleep(350)
  await relSection.locator('select').nth(1).selectOption('师徒').catch(() => {}); await sleep(250)
  await relSection.locator('input[placeholder="建立章"]').fill('1'); await sleep(250)
  await relSection.getByRole('button', { name: '保存', exact: true }).click(); await sleep(1600)

  const relBody = captured.relations.map((b) => { try { return JSON.parse(b) } catch { return {} } }).slice(-1)[0] || {}
  rec('件2② 建立关系 POST /character-relations 带 src/dst/relation/since', relBody.src === 'role:甲测' && relBody.dst === 'role:乙测' && relBody.relation === '师徒' && relBody.since_chapter === 1, `body=${JSON.stringify(relBody)}`)

  await sleep(700)
  const tabText = (await relSection.innerText().catch(() => '')).replace(/\s+/g, ' ')
  rec('件2③ 关系 tab 显示新建关系(乙测 · 师徒)', tabText.includes('乙测') && tabText.includes('师徒'), `tab="${tabText.slice(0, 160)}"`)

  const rels = await jget('/character-relations?chapter=9999', slug)
  const relHit = (rels || []).some((r) => (r.src === '甲测' || r.dst === '甲测') && r.relation === '师徒')
  rec('件2④ GET /character-relations 返回新建关系', relHit, `rels=${JSON.stringify(rels).slice(0, 200)}`)

  rec('零 console/page 错误', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' || ') || '(零错误)')

  await browser.close()

  // ── cleanup:删除临时 work(零残留)──
  const del = await fetch(`${API}/works/${slug}`, { method: 'DELETE' }).then((r) => r.json()).catch((e) => ({ err: String(e) }))
  console.log('清理:删除临时 work', slug, JSON.stringify(del))
  const works = await fetch(`${API}/works`).then((r) => r.json())
  const stillThere = (works || []).some((x) => x.slug === slug)
  rec('数据恢复:临时 work 已删除(零残留,未碰真书)', !stillThere, `slug ${slug} 仍存在=${stillThere}`)

  console.log('\n==== RESULTS ====')
  for (const x of results) console.log(`${x.pass ? 'PASS' : 'FAIL'} | ${x.name} | ${x.ev}`)
  if (results.some((x) => !x.pass)) process.exitCode = 2
}

run().catch(async (e) => {
  console.error('FATAL', e)
  if (slug) { try { await fetch(`${API}/works/${slug}`, { method: 'DELETE' }) } catch { /* */ } }
  process.exit(1)
})

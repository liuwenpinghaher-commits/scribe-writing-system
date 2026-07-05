// ── e2e · 批D-P1-11:声音后半环 UI(角色详情「声音演变」区)────────────────────
// 运行:cd scribe3/web && node e2e/qa_p1_11_voice.mjs(需 dev :3311 + 后端 :3321 在跑)
//
// 声音演变消费端闭环:voice_evolution_flag(待折叠)+ 一键折叠 → voice_profile(声线指纹)。
//
// Part A — 后端真机往返(临时 work,真写但自清理,零残留、不碰任何真书):
//   造角色 → 两条 affects_voice 质变(生成 2 条 flag)→ GET /voice-flags → fold(LLM 演化)
//   → 断言 folded>0 + profile 返回 + open flag 清零 → DELETE work。
// Part B — 前端 UI 渲染/交互(主书『乱世铜炉』,route 注入,零后端写):
//   ① 角色 A(注入 flag 属别的角色)→ 空态「暂无声音演变记录」(验证按角色过滤 + 空态)
//   ② 角色 B(注入 2 条 flag)→ flags 列表渲染(第N章 + reason)+「N 条待折叠」+ 折叠按钮可用
//   ③ 单条 resolve(点 X)→ 命中 /voice-flags/{id}/resolve + 该行移除
//   ④ 一键折叠 → 命中 /voice-flags/fold + 声线指纹(voice-profile)渲染 + flags 列表清空
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()

const results = []
const consoleErrors = []
const log = (...a) => console.log('[p1-11]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }
const jfetch = (url, opts) => fetch(url, opts).then(async (r) => ({ ok: r.ok, status: r.status, body: await r.json().catch(() => null) }))

// ═══════════════════ Part A — 后端真机往返(临时 work) ═══════════════════
async function backendRoundTrip() {
  let slug = ''
  try {
    const w = await jfetch(`${API}/works`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: `p1-11-e2e-${ts}` }) })
    slug = w.body?.slug || ''
    rec('A0 建临时 work', !!slug, `slug=${slug}`)
    if (!slug) return

    await jfetch(`${API}/characters?work=${slug}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name: '声测郎', backstory: 'P1-11 e2e 临时角色', importance: 'minor' }) })
    const cid = 'role:声测郎'
    for (const [ch, reason] of [[3, '历经背叛后从温和书生转为冷硬多疑,说话短促带刺。'], [5, '复仇得手后陷入空茫,语气疲惫疏离,常自言自语。']]) {
      await jfetch(`${API}/char-states?work=${slug}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ character_id: cid, chapter: ch, change_type: 'personality', summary: reason, affects_voice: true, confidence: 'confirmed' }) })
    }
    const before = await jfetch(`${API}/voice-flags?work=${slug}`)
    const beforeN = Array.isArray(before.body) ? before.body.length : -1
    rec('A1 affects_voice 质变生成 open voice flags', beforeN === 2, `open flags=${beforeN}`)

    // fold(LLM,较慢)
    const fold = await jfetch(`${API}/voice-flags/fold?work=${slug}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ character_id: cid }) })
    const folded = fold.body?.folded
    const prof = fold.body?.profile
    const profKeys = prof ? Object.keys(prof).filter((k) => prof[k] != null && (Array.isArray(prof[k]) ? prof[k].length : String(prof[k]).trim())) : []
    rec('A2 fold 折叠 flags → 返回演化后 voice_profile', folded > 0 && !!prof && profKeys.length > 0,
      `folded=${folded} degraded=${fold.body?.degraded} profileFields=[${profKeys.join(',')}]`)

    const after = await jfetch(`${API}/voice-flags?work=${slug}`)
    const afterN = Array.isArray(after.body) ? after.body.length : -1
    rec('A3 fold 后 open flags 清零(已 resolve)', folded > 0 ? afterN === 0 : true, `open flags after=${afterN}`)
  } catch (e) {
    rec('A* 后端往返异常', false, String(e).slice(0, 160))
  } finally {
    if (slug) {
      const del = await jfetch(`${API}/works/${slug}`, { method: 'DELETE' })
      const works = await jfetch(`${API}/works`)
      const gone = Array.isArray(works.body) && !works.body.some((x) => x.slug === slug)
      rec('A4 数据恢复:临时 work 已删除(零残留)', del.ok && gone, `del.ok=${del.ok} gone=${gone}`)
    }
  }
}

// ═══════════════════ Part B — 前端 UI(主书,route 注入,零写) ═══════════════════
async function frontendUI() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  // 注入态(可变):初始 2 条 flag 属「二师兄」;fold 命中后置空(模拟后端 resolve)。
  let flagsPayload = [
    { id: 'p11a', character: 'role:二师兄', trigger_chapter: 4, reason: '经历师门变故后语气转冷,话锋短促带刺。' },
    { id: 'p11b', character: 'role:二师兄', trigger_chapter: 7, reason: '一战成名后自负,常用反问句压人。' },
  ]
  let resolveHit = false, foldHit = false

  try {
    // 路由用 URL 谓词精确匹配(避免 glob 的 `?` 单字符通配误伤 /fold)
    await page.route((u) => new URL(u).pathname === '/voice-flags', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(flagsPayload) }))
    await page.route((u) => new URL(u).pathname === '/voice-flags/fold', (route) => {
      foldHit = true
      flagsPayload = []   // 模拟后端 resolve:折叠后该角色不再有 open flag
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ folded: 2, profile: { style_summary: '冷硬短促、反问压人的自负腔调', catchphrases: ['哼', '也配?'], tone_rules: ['多用反问句', '句子短促收尾'], version: 2 } }) })
    })
    await page.route((u) => /^\/voice-flags\/[^/]+\/resolve$/.test(new URL(u).pathname), (route) => {
      resolveHit = true
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
    })

    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: /乱世铜炉/ }).first().click()
    const left = () => page.getByTestId('left')
    await left().getByRole('button', { name: '素材', exact: true }).waitFor({ timeout: 10000 })

    const voice = () => page.locator('[data-testid="char-voice"]')
    // codex_root「素材」默认已展开;只需展开「角色」分类露出角色叶(默认折叠)。幂等:确保 二师兄 叶可见。
    const leafVisible = () => left().getByRole('button', { name: '二师兄', exact: true }).first().isVisible().catch(() => false)
    for (let i = 0; i < 2 && !(await leafVisible()); i++) {
      await left().getByRole('button', { name: /角色/ }).first().click()
      await page.waitForTimeout(400)
    }
    const openChar = async (name) => {
      await left().getByRole('button', { name, exact: true }).first().click()
      await voice().waitFor({ timeout: 10000 })
    }

    // ① 空态 + 按角色过滤:开「于老头」(注入 flag 属二师兄,应被过滤 → 空态)
    await openChar('于老头')
    const emptyTxt = await voice().innerText().catch(() => '')
    rec('B① 声音区渲染 + 别角色的 flag 被过滤 → 空态', emptyTxt.includes('声音演变') && emptyTxt.includes('暂无声音演变记录'),
      `voiceText="${emptyTxt.replace(/\s+/g, ' ').slice(0, 80)}"`)

    // ② 开「二师兄」→ 2 条 flag 渲染 + 折叠按钮
    await openChar('二师兄')
    const vtxt = await voice().innerText().catch(() => '')
    const flagsShown = vtxt.includes('第4章') && vtxt.includes('语气转冷') && vtxt.includes('第7章') && vtxt.includes('反问句压人')
    rec('B② open flags 列表渲染(第N章 + 触发事件)', flagsShown && vtxt.includes('2 条待折叠'),
      `hasCh4=${vtxt.includes('第4章')} hasCh7=${vtxt.includes('第7章')} badge=${vtxt.includes('2 条待折叠')}`)
    const foldBtn = voice().getByRole('button', { name: /一键折叠/ })
    rec('B②b 一键折叠按钮存在且启用', await foldBtn.isEnabled().catch(() => false), `enabled=${await foldBtn.isEnabled().catch(() => false)}`)

    // ③ 单条 resolve:点第一条的忽略(X)→ 命中 resolve 端点 + 该行移除
    await voice().locator('button[title^="忽略此条"]').first().click()
    await page.waitForTimeout(500)
    const afterResolve = await voice().innerText().catch(() => '')
    rec('B③ 单条 resolve:命中 /voice-flags/{id}/resolve + 行移除',
      resolveHit && !afterResolve.includes('语气转冷') && afterResolve.includes('反问句压人'),
      `resolveHit=${resolveHit} ch4Gone=${!afterResolve.includes('语气转冷')} ch7Kept=${afterResolve.includes('反问句压人')}`)

    // ④ 一键折叠 → 命中 fold + 声线指纹渲染 + flags 列表清空
    await voice().getByRole('button', { name: /一键折叠/ }).click()
    await page.locator('[data-testid="voice-profile"]').waitFor({ timeout: 8000 }).catch(() => {})
    await page.waitForTimeout(600)
    const foldedTxt = await voice().innerText().catch(() => '')
    const profileShown = foldedTxt.includes('声线指纹') && foldedTxt.includes('风格速写') && foldedTxt.includes('反问压人') && foldedTxt.includes('口头禅') && foldedTxt.includes('语气规则')
    // fold 成功后有 profile,故不显示空态文案;列表清空 = flag reason 与「待折叠」提示均消失。
    const listCleared = !foldedTxt.includes('反问句压人') && !foldedTxt.includes('语气转冷') && !foldedTxt.includes('待折叠')
    rec('B④ fold 往返:命中 /voice-flags/fold + 声线指纹展示 + 列表清空',
      foldHit && profileShown && listCleared,
      `foldHit=${foldHit} profileShown=${profileShown} listCleared=${listCleared}`)
  } catch (e) {
    rec('B* 前端 UI 异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
  }
}

const run = async () => {
  await backendRoundTrip()
  await frontendUI()

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })

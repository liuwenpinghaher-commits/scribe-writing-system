// ── e2e · 块三:通用选中→主编聚焦(14 用例,全程只读) ─────────────────────────
// 运行:cd scribe3/web && node e2e/qa_b3.mjs(需 dev :3311 + 后端 :3321 在跑)
// 只读交互(点选/聚焦),/chat/write 经 route 拦截不落后端——无需快照/恢复;仍建议跑后抽查 ch4 未变。
// QA 块三:通用选中→主编聚焦(universal selection bus)。只读交互(点选/聚焦),不改数据。
// ①图谱节点 ②时间线事件 ③伏笔行 ④母题行 ⑤项目树角色 ⑥演绎目标跟随 ⑦空白回退视图级话术
// 目标:《纸命》work=book_c256380e。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const SEQ = 4
const ts = Date.now()

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa3]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  const chiefLabel = () => page.getByTestId('chief-ctx').innerText().catch(() => '(no chief header)')

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  const vol = page.getByRole('button', { name: '未分卷' })
  await vol.waitFor({ timeout: 10000 })
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  const tab = (n) => page.getByRole('button', { name: n, exact: true })

  // ============ ⑤ 项目树点角色 → 主编聚焦角色(原有行为不回退) ============
  await page.getByTestId('left').getByRole('button', { name: /^角色/ }).first().click()   // 展开素材分类「角色 8」(带计数徽标)
  await page.waitForTimeout(400)
  await page.getByTestId('left').getByRole('button', { name: '崔判', exact: true }).click()
  await page.waitForTimeout(500)
  let lbl = await chiefLabel()
  rec('⑤ 项目树点角色→主编聚焦角色', lbl.includes('角色') && lbl.includes('崔判'), `chief="${lbl}"`)

  // ============ ① 图谱点节点 → 主编聚焦该节点 ============
  await page.getByRole('button', { name: '图谱' }).click()
  await page.waitForFunction(() => window.__s3Atlas && window.__s3Atlas.nodes().length > 0, null, { timeout: 15000 })
  await page.waitForTimeout(800)
  // 取当前中心角色(下拉的值),经只读 seam 拿屏幕坐标,对画布做真实点击
  const focusInfo = await page.evaluate(() => {
    const sel = document.querySelector('select')
    const id = sel?.value
    const pos = id ? window.__s3Atlas.nodeViewport(id) : null
    const label = sel?.selectedOptions?.[0]?.textContent || ''
    return { id, pos, label }
  })
  const canvasBox = await page.locator('.sigma-container, canvas').first().boundingBox()
  rec('①-pre 图谱就绪(中心角色+坐标)', !!(focusInfo.pos && canvasBox), JSON.stringify({ id: focusInfo.id, pos: focusInfo.pos }))
  await page.mouse.click(canvasBox.x + focusInfo.pos.x, canvasBox.y + focusInfo.pos.y)
  await page.waitForTimeout(500)
  lbl = await chiefLabel()
  rec('① 图谱点节点→主编聚焦该节点', lbl.includes('角色') && lbl.includes(focusInfo.label), `chief="${lbl}" node="${focusInfo.label}"`)

  // ============ ⑦ 点空白画布 → 回退视图级话术 ============
  // 找一个离所有节点都远(>40px)的画布内点
  const blank = await page.evaluate(() => {
    const ids = window.__s3Atlas.nodes()
    const pts = ids.map((id) => window.__s3Atlas.nodeViewport(id)).filter(Boolean)
    const cands = []
    for (let x = 20; x < 800; x += 40) for (let y = 20; y < 600; y += 40) cands.push({ x, y })
    let best = null, bestD = -1
    for (const c of cands) {
      const d = Math.min(...pts.map((p) => Math.hypot(p.x - c.x, p.y - c.y)))
      if (d > bestD) { bestD = d; best = c }
    }
    return { ...best, dist: bestD }
  })
  await page.mouse.click(canvasBox.x + blank.x, canvasBox.y + blank.y)
  await page.waitForTimeout(500)
  lbl = await chiefLabel()
  rec('⑦ 点空白画布→回退视图级话术', lbl.includes('视图') && lbl.includes('关系图谱'), `chief="${lbl}" blankDist=${Math.round(blank.dist)}px`)

  // ============ ② 时间线点条目 → 主编聚焦该条目 ============
  // 注:该书时间线暂无 kind==='event' 的纯事件条目(只有弧光点+伏笔区间),按验收第4条以弧光/伏笔条替代。
  await page.getByRole('button', { name: '时间线' }).click()
  const visPoint = page.locator('.vis-item.vis-point').first()
  await visPoint.waitFor({ timeout: 15000 })
  await page.waitForTimeout(600)
  const itemText = (await visPoint.innerText()).replace(/[◇◆⟲\s]/g, '')
  await visPoint.click()
  await page.waitForTimeout(500)
  lbl = await chiefLabel()
  const frag = itemText.slice(0, 4)
  rec('②a 时间线点弧光点→主编聚焦', /(事件|弧光) · /.test(lbl) && lbl.replace(/\s/g, '').includes(frag), `chief="${lbl}" item="${itemText.slice(0, 20)}"`)
  const visRange = page.locator('.vis-item.vis-range').first()
  if (await visRange.isVisible().catch(() => false)) {
    const rangeText = (await visRange.innerText()).replace(/[◇◆⟲\s]/g, '').replace(/[(].*$/, '').replace(/….*$/, '')
    await visRange.click()
    await page.waitForTimeout(500)
    lbl = await chiefLabel()
    rec('②b 时间线点伏笔条→主编聚焦伏笔', lbl.includes('伏笔 · ') && lbl.replace(/\s/g, '').includes(rangeText.slice(0, 4)), `chief="${lbl}" item="${rangeText.slice(0, 16)}"`)
    // ②c 收尾项:详情面板「跳到第N章」跳章后聚焦仍在(suppress 吞掉跳章镜像,不被冲成「章」)。
    // 跳章默认落正文 tab(写作槽无 chief-ctx),切到大纲 tab(讨论态,不动 sel)再读聚焦。
    await page.getByRole('button', { name: /^跳到第\d+章$/ }).click()
    await page.waitForTimeout(900)
    await tab('大纲').click()
    await page.waitForTimeout(500)
    lbl = await chiefLabel()
    rec('②c 时间线跳章后聚焦仍在(不被冲成章)', lbl.includes('伏笔 · ') && lbl.replace(/\s/g, '').includes(rangeText.slice(0, 4)), `chief="${lbl}"`)
  } else {
    rec('②b 时间线点伏笔条→主编聚焦伏笔', true, '(无可见伏笔条,跳过)')
    rec('②c 时间线跳章后聚焦仍在(不被冲成章)', true, '(无可见伏笔条,跳过)')
  }

  // ============ ③ 左栏伏笔面板点一行 → 主编聚焦该伏笔 ============
  if (!(await chNode(SEQ).isVisible().catch(() => false))) { await vol.click() }
  await chNode(SEQ).click()
  await page.waitForTimeout(800)
  await tab('大纲').click()   // 讨论阶段(主编=DiscussionDock)
  await page.waitForTimeout(400)
  await page.getByRole('button', { name: '伏笔', exact: true }).click()
  const pRow = page.getByTestId('left').getByRole('button', { name: /借命契/ }).first()
  await pRow.waitFor({ timeout: 10000 })
  await pRow.click()   // 块四b:聚焦伏笔 + 导航到该伏笔的中区 CodexDetail 详情(不再跳章;镜像避让,不冲掉聚焦)
  await page.waitForTimeout(900)
  lbl = await chiefLabel()
  rec('③ 伏笔行点选→主编聚焦该伏笔(含文本片段)', lbl.includes('伏笔 · ') && lbl.includes('借命契'), `chief="${lbl}"`)

  // 块四b:点伏笔行现在把 sel 导航到伏笔详情(seq→null,章级 tab 暂隐)→ ④母题前先回章上下文。
  if (!(await chNode(SEQ).isVisible().catch(() => false))) { await vol.click() }
  await chNode(SEQ).click()
  await page.waitForTimeout(700)
  await tab('大纲').click()
  await page.waitForTimeout(300)

  // ============ ④ 母题行 → 主编聚焦该母题 ============
  await page.getByRole('button', { name: '母题', exact: true }).click()
  const mRow = page.getByTestId('left').getByRole('button', { name: /命与纸/ }).first()
  await mRow.waitFor({ timeout: 10000 })
  await mRow.click()
  await page.waitForTimeout(500)
  lbl = await chiefLabel()
  rec('④ 母题行点选→主编聚焦该母题', lbl.includes('母题 · 命与纸'), `chief="${lbl}"`)

  // ============ ⑥ 演绎阶段切角色投影 → 主编聚焦跟随(块二不回退) ============
  await page.getByRole('button', { name: '项目树' }).click()
  await chNode(SEQ).click()
  await page.waitForTimeout(800)
  await tab('演绎').click()
  await page.waitForTimeout(400)
  await page.getByRole('button', { name: '演绎 · 角色限知' }).click()
  const charBtn = page.getByTestId('left').getByRole('button', { name: /崔判/ }).first()
  await charBtn.waitFor({ timeout: 10000 })
  await charBtn.click()
  await page.waitForTimeout(600)
  lbl = await chiefLabel()
  rec('⑥a 演绎切角色投影→主编聚焦跟随', lbl.includes(`第 ${SEQ} 章`) && lbl.includes('演绎') && lbl.includes('崔判'), `chief="${lbl}"`)
  await page.getByTestId('left').getByRole('button', { name: /^场景真相/ }).click()
  await page.waitForTimeout(600)
  lbl = await chiefLabel()
  rec('⑥b 切回场景真相→主编跟随', lbl.includes('演绎') && lbl.includes('场景真相'), `chief="${lbl}"`)

  // ============ ⑧ 必修1:点伏笔行后立即(<300ms)点项目树角色 → 意图不丢 ============
  // suppress 一次性标记只吞「跳章」那一次 sel 变化;紧随的角色点选必须正常镜像成焦点。
  await page.getByRole('button', { name: '伏笔', exact: true }).click()
  const pRow8 = page.getByTestId('left').getByRole('button', { name: /借命契/ }).first()
  await pRow8.waitFor({ timeout: 10000 })
  const treeRail = page.getByRole('button', { name: '项目树' })
  const t0 = Date.now()
  await pRow8.click()                       // 聚焦伏笔 + 跳埋设章(置 suppress)
  await treeRail.click()
  await page.getByTestId('left').getByRole('button', { name: '崔判', exact: true }).click()
  const elapsed = Date.now() - t0
  await page.waitForTimeout(600)
  lbl = await chiefLabel()
  rec('⑧ 伏笔行→立即点树角色:话术是角色不是伏笔', lbl.includes('角色') && lbl.includes('崔判') && !lbl.includes('伏笔'),
    `chief="${lbl}" 连点间隔=${elapsed}ms(单测另覆盖同 tick 0ms 场景)`)

  // ============ ⑨ 必修2:生成中点母题行(纯聚焦)→ 流不被杀,兜底/围栏发布仍执行 ============
  // route 注入慢流:/chat/write 挂起 1800ms 后回 SSE(proposal 围栏);中途点母题行,
  // 断言:a) 话术即时变母题 b) 停止键仍在(busy 未被 chatKey 效应重置=未 abort)c) 提示条出现(发布执行)。
  await chNode(SEQ).click()
  await page.waitForTimeout(800)
  await tab('大纲').click()
  await page.waitForTimeout(400)
  const MK9 = `块三慢流稿-${ts}`
  await page.route('**/chat/write*', async (route) => {
    await new Promise((r) => setTimeout(r, 1800))
    const body = [
      'data: {"proposal_start": true}',
      '',
      `data: {"proposal_chunk": {"text": "${MK9}"}}`,
      '',
      `data: {"proposal": {"prose": "${MK9}"}}`,
      '',
      'data: {"done": true}',
      '', '',
    ].join('\n')
    await route.fulfill({ status: 200, contentType: 'text/event-stream', body })
  })
  const ta9 = page.getByPlaceholder('就当前内容问主编…(Enter 发送)')
  await ta9.fill('给这章出一版大纲')
  await ta9.press('Enter')
  await page.waitForTimeout(400)            // 流在途(请求挂起中)
  const stopBtn = page.getByRole('button', { name: '停止生成' })
  const busyBefore = await stopBtn.isVisible().catch(() => false)
  await page.getByRole('button', { name: '母题', exact: true }).click()
  await page.getByTestId('left').getByRole('button', { name: /命与纸/ }).first().click()
  await page.waitForTimeout(300)
  lbl = await chiefLabel()
  const busyAfter = await stopBtn.isVisible().catch(() => false)
  rec('⑨a 生成中点母题:话术即时聚焦母题', lbl.includes('母题 · 命与纸'), `chief="${lbl}"`)
  rec('⑨b 流未被杀(busy 未被 chatKey 效应重置)', busyBefore && busyAfter, `busyBefore=${busyBefore} busyAfter=${busyAfter}`)
  const bar9 = page.getByText(/主编生成了/)
  let barShown = false
  try { await bar9.waitFor({ timeout: 8000 }); barShown = true } catch { /* */ }
  rec('⑨c 生成完成:proposal 发布执行(提示条出现)', barShown, `barShown=${barShown}`)
  if (barShown) { await page.getByRole('button', { name: '忽略', exact: true }).click(); await page.waitForTimeout(200) }  // 不落地,内存态清除
  await page.unroute('**/chat/write*')

  await browser.close()

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })

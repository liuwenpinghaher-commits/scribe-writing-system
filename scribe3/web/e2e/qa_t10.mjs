// ── e2e · Task10 工艺引擎露出 真机验收 ──────────────────────────────────────
// 运行:cd scribe3/web && node e2e/qa_t10.mjs(需 dev :3311 + 后端 :3321 在跑)
// 覆盖:章前简报面板 / 角色弧光锚编辑往返 / lie_belief 曲线 / tier 选择器落库 / 张力检查。
// 数据纪律:对《纸命》(book_c256380e)——测前快照 苏纸鸢 anchors;写入均在 finally 精确回滚
//   (锚恢复 null、arc-beats 按 id 删、tier 用新建即删的测试伏笔,不碰既有伏笔)。零残留。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const CHAR = 'role:苏纸鸢'
const enc = encodeURIComponent
const ts = Date.now()
const TEST_PROM = `T10-tier测试伏笔-${ts}`

const results = []
const consoleErrors = []
const rec = (n, p, e) => { results.push({ n, p, e }); console.log(p ? 'PASS' : 'FAIL', '|', n, '|', e) }
const ww = (p) => `${API}${p}${p.includes('?') ? '&' : '?'}work=${WORK}`
const aGet = (p) => fetch(ww(p)).then((r) => r.json())
const aPost = (p, b) => fetch(ww(p), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: b ? JSON.stringify(b) : undefined }).then((r) => r.json())
const aPatch = (p, b) => fetch(ww(p), { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then((r) => r.json())
const aDel = (p) => fetch(ww(p), { method: 'DELETE' }).then((r) => r.json())

let beatIds = []
let testPid = null

async function run() {
  // ── 快照 ──
  const anchorsBefore = await aGet(`/char-anchors?character_id=${enc(CHAR)}`)
  console.log('[snapshot] anchorsBefore.anchors =', JSON.stringify(anchorsBefore.anchors))
  console.log('[snapshot] arc_plan len =', (anchorsBefore.arc_plan || []).length)

  // ── API-1 弧光锚 PATCH → GET 往返 ──
  await aPatch('/char-anchors', { character_id: CHAR, anchors: { ghost: 'T10测试心魔', lie: 'T10测试谎言', arc_type: 'fall', private_agenda: 'T10私密日程' } })
  const a1 = await aGet(`/char-anchors?character_id=${enc(CHAR)}`)
  rec('API-1 弧光锚落库', a1.anchors?.ghost === 'T10测试心魔' && a1.anchors?.lie === 'T10测试谎言' && a1.anchors?.arc_type === 'fall',
    `ghost=${a1.anchors?.ghost} arc_type=${a1.anchors?.arc_type}`)

  // ── API-2 arc-beats(带 lie_belief_target,喂 lie_belief 曲线的计划轨迹)──
  for (const [nm, ch, lbt] of [['开场谎言', 1, 80], ['动摇', 3, 50], ['识破', 5, 20]]) {
    await aPost('/arc-beats', { character_id: CHAR, beat_name: nm, target_chapter: ch, lie_belief_target: lbt, trigger_event: '' })
  }
  const a2 = await aGet(`/char-anchors?character_id=${enc(CHAR)}`)
  beatIds = (a2.arc_plan || []).map((b) => b.id)
  const withLbt = (a2.arc_plan || []).filter((b) => typeof b.lie_belief_target === 'number')
  rec('API-2 arc-beats 落库(3拍带信奉度)', withLbt.length === 3, `arc_plan=${(a2.arc_plan || []).length} 带信奉度=${withLbt.length}`)

  // ── API-3 tier 选择器落库(新建 book → 改 arc → 删,不碰既有伏笔)──
  await aPost('/promises-new', { text: TEST_PROM, setup_chapter: 1, tier: 'book' })
  let proms = await aGet('/promises')
  let tp = proms.find((p) => p.text === TEST_PROM)
  testPid = tp?.id
  rec('API-3a 伏笔按 tier=book 新建落库', tp?.tier === 'book', `tier=${tp?.tier} pid=${testPid}`)
  if (testPid) {
    await aPatch(`/promises/${enc(testPid)}`, { text: TEST_PROM, setup_chapter: 1, promise_kind: 'promise', tier: 'arc' })
    proms = await aGet('/promises')
    tp = proms.find((p) => p.id === testPid)
    rec('API-3b PATCH 改 tier=arc 落库', tp?.tier === 'arc', `tier=${tp?.tier}`)
  }

  // ── API-4 章前简报有内容(纸命有超期伏笔账台)──
  const brief5 = await aGet(`/chapter-brief?seq=5`)
  const dec = brief5?.sections?.promises?.decisions || []
  rec('API-4 /chapter-brief?seq=5 含待决策', dec.length > 0, `decisions=${dec.length} loops.weighted=${brief5?.sections?.loops?.weighted}`)

  // ── UI 真机 ──
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.setDefaultTimeout(12000)   // 全局动作上限,杜绝任一选择器 30s 挂起
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  const vol = page.getByRole('button', { name: '未分卷' })
  await vol.waitFor({ timeout: 10000 })
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  if (!(await chNode(4).isVisible().catch(() => false))) await vol.click()
  await chNode(4).click()
  await page.waitForTimeout(1000)

  // ── UI-1 简报 tab ──
  await page.getByRole('button', { name: '简报', exact: true }).click()
  await page.waitForTimeout(900)
  const briefTitleSeen = await page.getByText('章前简报').first().isVisible().catch(() => false)
  const notEmpty = !(await page.getByText('本章暂无简报项').isVisible().catch(() => false))
  const actionSeen = await page.getByRole('button', { name: '立即兑现' }).first().isVisible().catch(() => false)
  rec('UI-1 简报面板渲染(标题+非空+决策按钮)', briefTitleSeen && notEmpty && actionSeen, `title=${briefTitleSeen} notEmpty=${notEmpty} 立即兑现=${actionSeen}`)

  // ── 切回项目树 tab(简报 tab 已占据左栏,codex 导航需先恢复树)──
  await page.getByRole('button', { name: '项目树', exact: true }).click().catch(() => {})
  await page.waitForTimeout(500)

  // ── UI-2 角色弧光锚:导航 codex → 角色 → 苏纸鸢 ──
  const treeBtn = (nm) => page.getByRole('button', { name: nm, exact: true })
  const clickTree = async (nm) => { const b = treeBtn(nm).first(); if (await b.isVisible().catch(() => false)) { await b.click().catch(() => {}); await page.waitForTimeout(350) } }
  // 展开 codex 根「素材」→ 分类「角色」→ 选「苏纸鸢」
  if (!(await treeBtn('角色').isVisible().catch(() => false))) await clickTree('素材')
  await clickTree('角色')
  await clickTree('苏纸鸢')
  await page.waitForTimeout(900)
  const arcSecSeen = await page.getByText('弧光锚 · 角色内核').isVisible().catch(() => false)
  const ghostVal = await page.getByPlaceholder('过去某件事在角色心里留下的阴影').inputValue().catch(() => '(未见)')
  rec('UI-2a 弧光锚区渲染 + 载入已存锚', arcSecSeen && ghostVal === 'T10测试心魔', `sec=${arcSecSeen} ghost="${ghostVal}"`)

  // ── UI-3 lie_belief 曲线(arc-beats 计划轨迹已注入)──
  const curveSeen = await page.locator('svg[aria-label="信奉度曲线"]').isVisible().catch(() => false)
  rec('UI-3 lie_belief 曲线渲染', curveSeen, `svg=${curveSeen}`)

  // ── UI-2b UI 编辑锚 → 保存 → 后端往返 ──
  const truthTa = page.getByPlaceholder('角色最终须领悟的、与 Lie 相对的真相')
  if (await truthTa.isVisible().catch(() => false)) {
    await truthTa.fill('T10-UI真相往返').catch(() => {})
    await page.getByRole('button', { name: '保存弧光锚' }).click().catch(() => {})
    await page.waitForTimeout(900)
    const a3 = await aGet(`/char-anchors?character_id=${enc(CHAR)}`)
    rec('UI-2b UI 编辑锚保存落库', a3.anchors?.truth === 'T10-UI真相往返', `truth=${a3.anchors?.truth}`)
  } else rec('UI-2b UI 编辑锚保存落库', false, 'truth 输入框未见')

  // ── UI-4 tier 选择器在伏笔详情渲染 ──
  await clickTree('伏笔')
  const firstProm = page.getByRole('button', { name: /续命者一栏为何空着/ }).first()
  if (await firstProm.isVisible().catch(() => false)) { await firstProm.click().catch(() => {}); await page.waitForTimeout(900) }
  const tierSeen = await page.getByText('兑现层级').isVisible().catch(() => false)
  const tierSelVal = await page.locator('select').filter({ has: page.locator('option', { hasText: '章级' }) }).first().inputValue().catch(() => '(未见)')
  rec('UI-4 伏笔详情 tier 选择器渲染', tierSeen, `兑现层级label=${tierSeen} 当前值=${tierSelVal}`)

  await browser.close()
}

async function cleanup() {
  console.log('\n[cleanup] 回滚《纸命》测试写入…')
  try {
    // 锚恢复 null(原始全 null)
    await aPatch('/char-anchors', { character_id: CHAR, anchors: { ghost: null, lie: null, truth: null, want: null, need: null, arc_type: null, private_agenda: null } })
    // arc-beats 按 id 删
    for (const id of beatIds) await aDel(`/arc-beats/${enc(id)}`)
    // 测试伏笔删
    if (testPid) await aDel(`/promises/${enc(testPid)}`)
  } catch (e) { console.log('[cleanup] 异常', String(e).slice(0, 200)) }
  // 复核
  const a = await aGet(`/char-anchors?character_id=${enc(CHAR)}`)
  const anchorsClean = Object.values(a.anchors || {}).every((v) => v == null)
  const planClean = (a.arc_plan || []).length === 0
  const proms = await aGet('/promises')
  const promGone = !proms.some((p) => p.text === TEST_PROM)
  rec('CLEANUP 锚恢复null+里程碑清空+测试伏笔删除', anchorsClean && planClean && promGone,
    `anchorsNull=${anchorsClean} plan=${(a.arc_plan || []).length} 伏笔已删=${promGone}`)
}

; (async () => {
  try { await run() }
  catch (e) { console.error('FATAL', e); rec('RUN', false, String(e).slice(0, 200)) }
  finally { await cleanup() }
  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.p ? 'PASS' : 'FAIL'} | ${r.n} | ${r.e}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.p === false) || consoleErrors.length) process.exitCode = 2
})()

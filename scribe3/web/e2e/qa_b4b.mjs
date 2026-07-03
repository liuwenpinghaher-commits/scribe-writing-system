// ── e2e · 块四b:伏笔面板 IA + SynopsisCell 压平修复 ──────────────────────────
// 运行:cd scribe3/web && node e2e/qa_b4b.mjs(需 dev :3311 + 后端 :3321 在跑)
// 目标书《纸命》work=book_c256380e。
//  ① 点伏笔行 → 中区出 CodexDetail 伏笔详情(埋/收/线索/编辑)+ 主编聚焦该伏笔(不再只跳章)——只读。
//  ② 窄栏折叠:「障眼法/已了结/无关」默认强折叠(可点开);「本章相关」默认展开
//     —— 经 route 注入合成 ledger(不写后端),验证纯渲染 IA,只读。
//  ③ SynopsisCell 多行不压平:多段 synopsis inline 编辑用 textarea,Enter 换行不提交、
//     内部换行完整保留 —— 真机编辑纸命 ch1,先快照后恢复(finally 保证零残留)。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'   // 纸命
const ts = Date.now()

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa4b]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const getChapter = (seq) => fetch(`${API}/chapter?seq=${seq}&work=${WORK}`).then((r) => r.json())
const patchSynopsis = (seq, synopsis) => fetch(`${API}/chapters/${seq}?work=${WORK}`, {
  method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ synopsis }),
}).then((r) => r.json())

// ② 合成 ledger:1 超期(展开)+ 1 障眼法(折叠)+ 1 已了结(折叠)。seq=3 时后两者进「其它」折叠区。
const FAKE_LEDGER = {
  threshold: 3, max_chapter: 18,
  open: [{ id: 'qab4b_over', text: '块四b注入·超期未收EXP', kind: 'promise', status: 'open', setup_chapter: 1, payoff_chapter: null, overdue: true, clues: [], chapters_open: 17 }],
  closed: [{ id: 'qab4b_closed', text: '块四b注入·已了结FOLD', kind: 'promise', status: 'closed', setup_chapter: 2, payoff_chapter: 99, overdue: false, clues: [], span: 97 }],
  red_herring: [{ id: 'qab4b_herring', text: '块四b注入·障眼法FOLD', kind: 'red_herring', status: 'open', setup_chapter: 1, payoff_chapter: null, overdue: false, clues: [], chapters_open: 17 }],
  audit: { balanced: false, overdue_count: 1, payoff_without_setup: [], closed_without_setup: [], never_paid: 1 },
}

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  const chiefLabel = () => page.getByTestId('chief-ctx').innerText().catch(() => '(no chief header)')
  const left = () => page.getByTestId('left')
  const detail = () => page.getByTestId('detail')
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  const tab = (n) => page.getByRole('button', { name: n, exact: true })

  // 快照 ch1 synopsis(finally 恢复)
  const orig = (await getChapter(1)).synopsis || ''
  const origNL = (orig.match(/\n/g) || []).length

  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: /纸命/ }).first().click()
    await page.getByRole('button', { name: '未分卷' }).waitFor({ timeout: 10000 })

    // ════════════ ① 点伏笔行 → 中区 CodexDetail 详情 + 主编聚焦(不再只跳章) ════════════
    if (!(await chNode(4).isVisible().catch(() => false))) { await page.getByRole('button', { name: '未分卷' }).click() }
    await chNode(4).click()
    await page.waitForTimeout(700)
    await tab('大纲').click()               // 讨论阶段(主编=DiscussionDock,读 chief-ctx)
    await page.waitForTimeout(300)
    await tab('伏笔').click()
    const pRow = left().getByRole('button', { name: /承影斋经手的那张借命契/ }).first()
    await pRow.waitFor({ timeout: 10000 })
    await pRow.click()
    await page.waitForTimeout(1000)
    const lbl = await chiefLabel()
    rec('①a 点伏笔行→主编聚焦该伏笔(panel focusTalk 保留)', lbl.includes('伏笔 · ') && lbl.includes('承影斋'), `chief="${lbl}"`)
    const dtxt = await detail().innerText().catch(() => '')
    const detailOk = dtxt.includes('承影斋经手的那张借命契') && (dtxt.includes('埋于') || dtxt.includes('兑现层级') || dtxt.includes('伏笔内容'))
    rec('①b 中区出 CodexDetail 伏笔详情(埋/收/线索/编辑)', detailOk, `detailHead="${dtxt.replace(/\s+/g, ' ').slice(0, 90)}"`)

    // ════════════ ② 窄栏折叠:本章相关展开 / 障眼法·已了结·无关强折叠 ════════════
    await page.route('**/promises/ledger*', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_LEDGER) }))
    // 回到章上下文并切到未访问过的 ch3 → 触发 LeftDock 的 [seq] ledger 重取(命中注入)
    await tab('项目树').click().catch(() => {})
    await page.getByRole('button', { name: '项目树' }).click().catch(() => {})
    if (!(await chNode(3).isVisible().catch(() => false))) { await page.getByRole('button', { name: '未分卷' }).click() }
    await chNode(3).click()
    await page.waitForTimeout(700)
    await tab('大纲').click()
    await page.waitForTimeout(200)
    await tab('伏笔').click()
    await page.waitForTimeout(500)
    // 展开组:超期 EXP 直接可见
    const expVisible = await left().getByText('块四b注入·超期未收EXP').isVisible().catch(() => false)
    rec('②a 本章相关(超期)默认展开可见', expVisible, `expVisible=${expVisible}`)
    // 折叠区 <details> 存在、默认闭合、summary 计数=2
    const foldInfo = await page.evaluate(() => {
      const l = document.querySelector('[data-testid="left"]')
      const ds = [...l.querySelectorAll('details')]
      const d = ds.find((x) => /障眼法/.test(x.querySelector('summary')?.textContent || ''))
      return d ? { open: d.open, summary: d.querySelector('summary').textContent.trim() } : null
    })
    rec('②b 障眼法/已了结/无关 默认强折叠(details 闭合)', !!foldInfo && foldInfo.open === false && /· 2$/.test(foldInfo.summary),
      `fold=${JSON.stringify(foldInfo)}`)
    // 折叠时:障眼法/已了结 行不可见
    const herringHiddenBefore = !(await left().getByText('块四b注入·障眼法FOLD').isVisible().catch(() => false))
    const closedHiddenBefore = !(await left().getByText('块四b注入·已了结FOLD').isVisible().catch(() => false))
    rec('②c 折叠时障眼法/已了结行不占窄栏(不可见)', herringHiddenBefore && closedHiddenBefore,
      `herringHidden=${herringHiddenBefore} closedHidden=${closedHiddenBefore}`)
    // 点开 → 两行可见
    await left().getByText(/障眼法 \/ 已了结 \/ 无关/).click()
    await page.waitForTimeout(300)
    const herringShown = await left().getByText('块四b注入·障眼法FOLD').isVisible().catch(() => false)
    const closedShown = await left().getByText('块四b注入·已了结FOLD').isVisible().catch(() => false)
    rec('②d 点开折叠 → 障眼法/已了结行可见', herringShown && closedShown, `herringShown=${herringShown} closedShown=${closedShown}`)
    await page.unroute('**/promises/ledger*')

    // ════════════ ③ SynopsisCell 多行不压平(真机编辑 ch1,快照后恢复) ════════════
    await page.getByRole('button', { name: '项目树' }).click()
    await page.getByRole('button', { name: '手稿', exact: true }).click()   // 手稿根 → ContainerOutline
    await page.waitForTimeout(600)
    await page.getByRole('button', { name: '大纲表' }).click()               // Outliner 表模式
    await page.waitForTimeout(500)
    // 用 ch1 synopsis 首片段唯一定位其梗概单元格
    const frag = orig.replace(/\s+/g, '').slice(0, 5)
    const cell = detail().locator('[title^="点击编辑"]').filter({ hasText: frag }).first()
    await cell.waitFor({ timeout: 10000 })
    await cell.click()
    await page.waitForTimeout(300)
    const editorTag = await page.evaluate(() => document.activeElement?.tagName)
    const editorVal = await page.evaluate(() => document.activeElement?.value ?? '')
    rec('③a inline 编辑控件是多行 textarea(非单行 input)', editorTag === 'TEXTAREA', `activeEl=${editorTag}`)
    rec('③b 多段 synopsis 载入即含换行(不被压平)', (editorVal.match(/\n/g) || []).length === origNL && origNL > 0,
      `载入换行数=${(editorVal.match(/\n/g) || []).length} 原始=${origNL}`)
    // 光标在末尾 → Enter 追加新行(不提交)+ 文本;⌘/Ctrl+Enter 提交
    const MARK = `第五段-块四b测试${ts}`
    await page.keyboard.press('End')
    await page.keyboard.press('Enter')          // 换行(不提交)
    await page.keyboard.type(MARK)
    await page.waitForTimeout(150)
    const stillEditing = (await page.evaluate(() => document.activeElement?.tagName)) === 'TEXTAREA'
    rec('③c Enter=换行不提交(仍在编辑)', stillEditing, `activeEl=${await page.evaluate(() => document.activeElement?.tagName)}`)
    await page.keyboard.press('ControlOrMeta+Enter')   // 提交
    await page.waitForTimeout(1000)
    const after = (await getChapter(1)).synopsis || ''
    const afterNL = (after.match(/\n/g) || []).length
    const notFlattened = after === `${orig}\n${MARK}` && afterNL === origNL + 1
    rec('③d 提交后内部换行完整保留(不压平)', notFlattened,
      `afterNL=${afterNL}(期望${origNL + 1}) 末尾含标记=${after.endsWith(MARK)} 等于原文+新行=${after === `${orig}\n${MARK}`}`)
  } finally {
    // 无条件恢复 ch1 synopsis 到快照原文(零残留)
    try {
      await patchSynopsis(1, orig)
      const restored = (await getChapter(1)).synopsis || ''
      rec('③e 数据恢复:ch1 synopsis 已还原为快照原文', restored === orig,
        `restoredNL=${(restored.match(/\n/g) || []).length} origNL=${origNL} equal=${restored === orig}`)
    } catch (e) { rec('③e 数据恢复', false, 'restore error: ' + String(e).slice(0, 120)) }
    await browser.close()
  }

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })

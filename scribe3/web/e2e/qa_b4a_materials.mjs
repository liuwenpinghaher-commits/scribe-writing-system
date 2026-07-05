// ── e2e · 块四a-1 素材库全链真机验收 ────────────────────────────────────────
// 运行:cd scribe3/web && node e2e/qa_b4a_materials.mjs(需 dev :3311 + 重启后的后端 :3321)
// ①树第三支「素材库」 ②建素材(UI建1条+API补4类)分类正确 ③详情编辑保存
// ④搜索过滤 ⑤插入到草稿(stageProposal→草稿提示条→追加落编辑器) ⑥点素材→主编聚焦话术
// ⑦删除素材 ⑧数据纪律:测试素材全删零残留 + 草稿恢复快照 ⑨负验证:ingest(/facts、/graph)零感知
// 目标:《纸命》work=book_c256380e;全程 console error 必须为 0。
import { chromium } from 'playwright'

const API = 'http://127.0.0.1:3321'
const FRONT = 'http://127.0.0.1:3311'
const WORK = 'book_c256380e'
const SEQ = 4
const ts = Date.now()
const MARK = `插入标记-${ts}`

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa4a]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const jget = (p) => fetch(`${API}${p}${p.includes('?') ? '&' : '?'}work=${WORK}`).then((r) => r.json())
const jpost = (p, b) => fetch(`${API}${p}${p.includes('?') ? '&' : '?'}work=${WORK}`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b),
}).then((r) => r.json())
const jdel = (p) => fetch(`${API}${p}?work=${WORK}`, { method: 'DELETE' })

const run = async () => {
  // ——— 前置快照(数据纪律):素材基线 + 第4章草稿快照 + ingest 表观测基线 ———
  const baseIds = new Set((await jget('/materials')).map((m) => m.id))
  const draftSnap = await jget(`/latest-draft?seq=${SEQ}`)
  const factsBefore = (await jget('/facts?chapter=1')).length
  const graphBefore = await jget('/graph?limit=2000')
  log('baseline:', `materials=${baseIds.size} draftLen=${(draftSnap?.prose || '').length} facts@1=${factsBefore} graph=${graphBefore.nodes.length}n/${graphBefore.edges.length}e`)

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))
  const chiefLabel = () => page.getByTestId('chief-ctx').innerText().catch(() => '(no chief header)')

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()

  // ============ ① 项目树第三支「素材库」 ============
  const matRoot = page.getByRole('button', { name: /^素材库/ })
  await matRoot.waitFor({ timeout: 10000 })
  rec('① 项目树出现第三支「素材库」根', true, 'button 素材库 visible')

  // ============ ② 建素材:UI 建 research 1 条 ============
  await matRoot.click()
  await page.getByRole('heading', { name: '素材库' }).waitFor({ timeout: 5000 })
  await page.getByRole('button', { name: '新建', exact: true }).click()
  await page.getByLabel('素材标题').fill(`e2e研究素材-${ts}`)
  await page.getByLabel('素材分类').selectOption('research')
  await page.getByLabel('素材标签').fill('e2e, 考据')
  await page.getByLabel('素材来源').fill('e2e县志影印本')
  await page.getByRole('textbox', { name: '素材正文' }).click()
  await page.keyboard.type(`竹篾骨架,纸人吃墨。${MARK}`)
  await page.getByRole('button', { name: '创建', exact: true }).click()
  // 创建后进详情
  await page.getByRole('button', { name: '保存', exact: true }).waitFor({ timeout: 8000 })
  const created = (await jget('/materials?kind=research')).filter((m) => !baseIds.has(m.id))
  rec('② UI 建素材(research)落库', created.length === 1 && created[0].title === `e2e研究素材-${ts}`,
    `research 新增=${created.length} title=${created[0]?.title} tags=${JSON.stringify(created[0]?.tags)}`)

  // ============ ⑥ 点素材 → 主编聚焦话术含素材标题 ============
  await page.waitForTimeout(600)
  let lbl = await chiefLabel()
  rec('⑥ 素材详情→主编聚焦话术含标题', lbl.includes('素材') && lbl.includes(`e2e研究素材-${ts}`.slice(0, 12)), `chief="${lbl}"`)

  // ============ ② 续:API 补其余 4 kind,树分类正确 ============
  const apiIds = []
  for (const [kind, label] of [['reference', '参考'], ['snippet', '片段'], ['inspiration', '灵感'], ['note', '笔记']]) {
    const r = await jpost('/materials', { title: `e2e${label}素材-${ts}`, body: `${label}正文`, kind, tags: ['e2e'] })
    apiIds.push(r.id)
  }
  await page.waitForTimeout(1500)   // SSE 防抖 600ms → 树重拉
  // 素材库根开合态不确定(点击会 toggle):分类行不可见就点根展开
  const ensureMatOpen = async () => {
    const vis = await page.getByRole('button', { name: /^研究/ }).last().isVisible().catch(() => false)
    if (!vis) { await matRoot.click(); await page.waitForTimeout(400) }
  }
  await ensureMatOpen()
  // 树上五分类逐一核验(展开分类看叶子)
  let catOk = true, catEv = []
  for (const [label, title] of [['研究', `e2e研究素材-${ts}`], ['参考', `e2e参考素材-${ts}`], ['片段', `e2e片段素材-${ts}`], ['灵感', `e2e灵感素材-${ts}`], ['笔记', `e2e笔记素材-${ts}`]]) {
    const cat = page.getByTestId('left').getByRole('button', { name: new RegExp(`^${label}`) }).last()
    await cat.click()   // 展开
    const leaf = page.getByTestId('left').getByRole('button', { name: title })
    const visible = await leaf.isVisible().catch(() => false)
    if (!visible) { catOk = false }
    catEv.push(`${label}:${visible ? 'ok' : 'MISS'}`)
    await cat.click()   // 收回,避免树太长
  }
  rec('② 树第三支五分类正确(各 kind 至少 1)', catOk, catEv.join(' '))

  // ============ ③ 详情编辑保存 ============
  await ensureMatOpen()
  const noteCat = page.getByTestId('left').getByRole('button', { name: /^笔记/ }).last()
  await noteCat.click()
  await page.getByTestId('left').getByRole('button', { name: `e2e笔记素材-${ts}` }).click()
  await page.getByRole('button', { name: '保存', exact: true }).waitFor({ timeout: 8000 })
  await page.getByLabel('素材标题').fill(`e2e笔记素材改-${ts}`)
  await page.getByLabel('素材来源').fill('e2e改来源')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForTimeout(800)
  const noteRow = (await jget('/materials?kind=note')).find((m) => !baseIds.has(m.id))
  rec('③ 详情编辑保存(标题+来源改动落库)', noteRow?.title === `e2e笔记素材改-${ts}` && noteRow?.source === 'e2e改来源',
    `title=${noteRow?.title} source=${noteRow?.source}`)

  // ============ ④ 搜索过滤(标题/正文/tag) ============
  await matRoot.click()   // 树根被上一次点击收起过?先保证选中素材库根
  await page.getByRole('heading', { name: '素材库' }).waitFor({ timeout: 5000 })
  const search = page.getByLabel('搜索素材')
  await search.fill('e2e参考')
  await page.waitForTimeout(300)
  const listBtns = page.locator('main button', { hasText: `e2e` })
  const visTitles = await listBtns.allInnerTexts()
  const onlyRef = visTitles.some((t) => t.includes(`e2e参考素材-${ts}`)) && !visTitles.some((t) => t.includes(`e2e研究素材-${ts}`))
  await search.fill('考据')   // tag 过滤
  await page.waitForTimeout(300)
  const tagHit = await page.locator('main').getByRole('button', { name: new RegExp(`e2e研究素材-${ts}`) }).isVisible().catch(() => false)
  rec('④ 搜索过滤(标题命中+tag命中)', onlyRef && tagHit, `title过滤=${onlyRef} tag过滤=${tagHit}`)

  // ============ ⑤ 插入到草稿:stageProposal → 草稿提示条 → 追加落编辑器 ============
  await search.fill('')
  await page.locator('main').getByRole('button', { name: new RegExp(`e2e研究素材-${ts}`) }).first().click()
  await page.getByRole('button', { name: /插入到草稿/ }).waitFor({ timeout: 8000 })
  await page.getByRole('button', { name: /插入到草稿/ }).click()
  await page.getByPlaceholder('章号,如 4').fill(String(SEQ))
  await page.getByRole('button', { name: '发布', exact: true }).click()
  await page.waitForTimeout(400)
  // 打开第4章 → 草稿 tab
  await page.getByRole('button', { name: `${SEQ} 第${SEQ}章` }).click()
  await page.getByRole('button', { name: '草稿', exact: true }).click()
  const bar = page.getByText(/主编生成了本章草稿/)
  await bar.waitFor({ timeout: 8000 })
  rec('⑤a 草稿阶段提示条出现', true, await bar.innerText())
  await page.getByRole('button', { name: '追加到草稿', exact: true }).click()
  await page.waitForTimeout(500)
  const draftEditor = page.getByRole('textbox', { name: '草稿正文' })
  const draftText = await draftEditor.innerText()
  rec('⑤b 追加落进草稿编辑器', draftText.includes(MARK), `editor 含标记=${draftText.includes(MARK)}`)

  // ============ ⑦ 删除素材(UI) ============
  await ensureMatOpen()
  const infCat = page.getByTestId('left').getByRole('button', { name: /^灵感/ }).last()
  await infCat.click()
  await page.getByTestId('left').getByRole('button', { name: `e2e灵感素材-${ts}` }).click()
  await page.getByRole('button', { name: '删除', exact: true }).waitFor({ timeout: 8000 })
  await page.getByRole('button', { name: '删除', exact: true }).click()
  // ConfirmDialog 内的确认「删除」
  await page.getByRole('dialog').getByRole('button', { name: '删除', exact: true }).click()
  await page.waitForTimeout(800)
  const infLeft = (await jget('/materials?kind=inspiration')).filter((m) => !baseIds.has(m.id))
  rec('⑦ UI 删除素材', infLeft.length === 0, `inspiration 残留=${infLeft.length}`)

  // ============ ⑧ 数据纪律:清光测试素材 + 恢复草稿 ============
  const leftovers = (await jget('/materials')).filter((m) => !baseIds.has(m.id))
  for (const m of leftovers) await jdel(`/materials/${m.id}`)
  const after = (await jget('/materials')).map((m) => m.id)
  const zeroLeft = after.length === baseIds.size && after.every((id) => baseIds.has(id))
  rec('⑧a 测试素材全删零残留', zeroLeft, `now=${after.length} baseline=${baseIds.size}`)
  // 草稿恢复(追加在切走时已自动落库 → 回写快照)
  await page.getByRole('button', { name: /^素材库/ }).click()   // 切走触发草稿 flush
  await page.waitForTimeout(800)
  await jpost(`/save-draft?seq=${SEQ}`, { prose: draftSnap?.prose || '', summary: draftSnap?.summary || '' })
  const dNow = await jget(`/latest-draft?seq=${SEQ}`)
  const draftRestored = (dNow?.prose || '') === (draftSnap?.prose || '') && !(dNow?.prose || '').includes(MARK)
  rec('⑧b 草稿恢复快照(零标记残留)', draftRestored, `len=${(dNow?.prose || '').length} vs snap=${(draftSnap?.prose || '').length}`)

  // ============ ⑨ 负验证:ingest/图谱对素材零感知 ============
  const factsAfter = (await jget('/facts?chapter=1')).length
  const graphAfter = await jget('/graph?limit=2000')
  rec('⑨ ingest 零感知(facts/graph 前后一致)',
    factsAfter === factsBefore && graphAfter.nodes.length === graphBefore.nodes.length && graphAfter.edges.length === graphBefore.edges.length,
    `facts ${factsBefore}→${factsAfter} graph ${graphBefore.nodes.length}n/${graphBefore.edges.length}e→${graphAfter.nodes.length}n/${graphAfter.edges.length}e`)

  // ============ console error ============
  rec('零 console error', consoleErrors.length === 0, consoleErrors.length ? consoleErrors.join(' ;; ') : 'clean')

  await browser.close()
  const fails = results.filter((r) => !r.pass)
  console.log(`\n==== SUMMARY: ${results.length - fails.length}/${results.length} PASS ====`)
  if (fails.length) { fails.forEach((f) => console.log('FAIL:', f.name, '|', f.evidence)); process.exitCode = 2 }
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })

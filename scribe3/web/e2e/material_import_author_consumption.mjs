// 素材 Gate：真实 UI 导入→三通道召回→作者填入草稿→双向溯源。
// 写正典章节只经 Hermes/MCP 审批；素材导入与作者采纳均操作真实浏览器 UI，
// REST 只用于只读回查，不能用来伪造素材或引用。
import { withPage } from './lib.mjs'
import { approveAllPending, chiefSay } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { compactDiagnostic, writeJsonArtifact } from './result_artifact.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const BOOK = process.env.E2E_BOOK_TITLE || `素材作者消费验收·${Date.now().toString(36)}`
const WORK = process.env.E2E_WORK || null
const CHAPTER_SEQ = Number(process.env.E2E_CHAPTER_SEQ || 1)
const CHAPTER = '雾港草稿章'
const CASE = process.env.E2E_CASE || `material-${Date.now().toString(36)}`
const MARKER = `雾港冷灯-${CASE}`
const SOURCE = `素材记忆：${MARKER}。写码头夜景时，让冷灯在退潮后的黑水上摇晃；用短句和触觉制造逼仄，不复写原句。`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}: ${await response.text()}`)
  return response.json()
}

async function waitFor(read, predicate, label, attempts = 120) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}: ${compactDiagnostic(value)}`)
}

async function approveChapterThroughUi(page, work) {
  const chief = await chiefSay(page,
    `请仅调用 s3_add_chapter，在作品 ${work} 新建第${CHAPTER_SEQ}章，title=${CHAPTER}；等待我批准，未获批准不得声称已落库。`,
    { preferWrite: false, maxMs: 180000, bookTitle: BOOK },
  )
  await waitFor(async () => {
    await approveAllPending(page, { maxRounds: 5, settleMs: 800 })
    const rows = await json(`/chapters?work=${encodeURIComponent(work)}`)
    const chapters = Array.isArray(rows) ? rows : rows.chapters || []
    return chapters.find((row) => Number(row.seq) === CHAPTER_SEQ && row.title === CHAPTER)
  }, Boolean, `MCP 审批后章节未落库; chief=${compactDiagnostic(chief, 600)}`)
  return chief.run?.id || ''
}

async function enterMaterialLibrary(page) {
  await page.getByRole('button', { name: '素材库', exact: true }).click()
  await page.getByTestId('material-workbench').waitFor({ state: 'visible', timeout: 30000 })
}

const result = await withPage(async (page) => {
  const failedResponses = []
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() })
  })
  // Vite 会维持 HMR/SSE 连接，networkidle 不是可交互的可靠信号；具体控件的
  // 可见性等待才是此真人旅程的页面就绪条件。
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  let work = WORK
  let chapterRunId = ''
  if (!WORK) {
    const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
    await title.fill(BOOK)
    await page.getByRole('button', { name: '建', exact: true }).first().click()
    await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
    const works = await json('/works')
    work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
    assert(work, '无法解析隔离作品 slug')
    chapterRunId = await approveChapterThroughUi(page, work)
  } else {
    const opener = page.locator(`[data-work-slug="${work}"]`)
    if (await opener.count() !== 1) {
      await page.locator('[data-testid="app-rail"] button[title="切换 / 选择作品"]').click()
      await opener.waitFor({ state: 'visible', timeout: 20000 })
    }
    assert(await opener.count() === 1, `配置的作品不存在或不唯一: ${work}`)
    await opener.click({ timeout: 20000 })
    await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  }

  // 导入必须从浏览器 MaterialImport 做，不可用 /materials 或 import REST 旁路伪造。
  await enterMaterialLibrary(page)
  await page.getByRole('button', { name: '导入', exact: true }).click()
  await page.getByRole('button', { name: '粘贴文本', exact: true }).click()
  await page.getByRole('textbox', { name: '粘贴要导入的文本' }).fill(SOURCE)
  await page.getByRole('button', { name: '开始导入', exact: true }).click()
  await page.getByRole('button', { name: /确认导入/ }).waitFor({ state: 'visible', timeout: 180000 })
  await page.getByRole('button', { name: /确认导入/ }).click()
  await page.getByTestId('material-workbench').waitFor({ state: 'visible', timeout: 30000 })

  const imported = await waitFor(async () => {
    const rows = await json(`/materials?work=${encodeURIComponent(work)}&limit=200`)
    const items = Array.isArray(rows) ? rows : rows.items || []
    const importedRows = items.filter((row) => row.origin === 'import')
    return importedRows.length ? importedRows : null
  }, Boolean, 'UI 确认导入后素材未落库')
  // 导入器按语义切分、改写为多条素材，不能机械要求验收标记逐字保留；
  // 隔离作品 + import origin 保证本轮身份，内容信号证明解析没有产出无关空条目。
  const material = imported.find((row) => /雾港|码头|冷灯|短句/.test(`${row.title}\n${row.body}\n${row.summary}`)) || imported[0]
  assert(material.origin === 'import', `素材来源不正确: ${material.origin}`)
  assert(String(material.summary || material.body || '').trim(), '导入素材缺少正文或摘要')

  // 在真实素材工作台通过搜索触发 material_recall，而不是把刚才的 GET 回读冒充召回。
  const search = page.getByPlaceholder('标题 / 正文 / 标签')
  await search.fill('雾港')
  const materialRow = page.getByRole('button', { name: material.title, exact: true })
  await materialRow.waitFor({ state: 'visible', timeout: 30000 })
  await materialRow.click()
  await page.getByTestId('material-insert-other').waitFor({ state: 'visible', timeout: 30000 })

  // 发布只是待采纳提案；此刻不得产生 material_reference。
  await page.getByTestId('material-insert-other').click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('textbox').fill(String(CHAPTER_SEQ))
  await dialog.getByRole('button', { name: '发布', exact: true }).click()
  const beforeAccept = await json(`/materials/${encodeURIComponent(material.id)}/refs?work=${encodeURIComponent(work)}`)
  assert(!beforeAccept.some((row) => Number(row.chapter) === CHAPTER_SEQ), '未填入草稿前就被伪记为已引用')

  // 作者切回本章草稿并明确点“填入”，才形成正文消费与反向溯源。
  await page.getByRole('button', { name: '手稿', exact: true }).click()
  const chapterButton = page.getByRole('button', { name: new RegExp(`^${CHAPTER_SEQ}\\s`) }).first()
  await chapterButton.waitFor({ state: 'visible', timeout: 30000 })
  await chapterButton.click()
  await page.getByRole('tab', { name: '草稿', exact: true }).click()
  const fillDraft = page.getByRole('button', { name: '填入草稿框', exact: true })
  await fillDraft.waitFor({ state: 'visible', timeout: 30000 })
  await fillDraft.click()
  const consumedExcerpt = String(material.body || material.summary).trim().slice(0, 20)
  assert(consumedExcerpt, '素材没有可供作者填入的正文')
  const draft = page.locator('[aria-label="草稿正文"]').first()
  const draftText = await waitFor(async () => (await draft.count()) ? await draft.innerText() : '',
    (value) => String(value).includes(consumedExcerpt), '作者填入后草稿没有消费素材内容', 30)
  const refs = await waitFor(
    () => json(`/materials/${encodeURIComponent(material.id)}/refs?work=${encodeURIComponent(work)}`),
    (rows) => rows.filter((row) => Number(row.chapter) === CHAPTER_SEQ && row.via === 'manual_insert').length === 1,
    '作者填入草稿后未形成唯一 material_reference',
  )
  return {
    work,
    materialId: material.id,
    materialTitle: material.title,
    marker: MARKER,
    consumedExcerpt,
    draft: String(draftText).slice(0, 260),
    refs: refs.filter((row) => Number(row.chapter) === CHAPTER_SEQ),
    runIds: chapterRunId ? [chapterRunId] : [],
    failedResponses,
  }
})

if (!result.ok || result.errs.length || result.failedResponses?.length) {
  console.error('MATERIAL_IMPORT_AUTHOR_CONSUMPTION FAIL', JSON.stringify(result))
  if (process.env.E2E_RESULT_FILE) await writeJsonArtifact(process.env.E2E_RESULT_FILE, { ok: false, ...result })
  process.exitCode = 1
} else if (process.env.E2E_RESULT_FILE) {
  await writeJsonArtifact(process.env.E2E_RESULT_FILE, { ok: true, ...result })
}

console.log('MATERIAL_IMPORT_AUTHOR_CONSUMPTION OK', JSON.stringify(result))

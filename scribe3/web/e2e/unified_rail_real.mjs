import { chromium } from 'playwright'

const base = process.env.SCRIBE3_E2E_BASE || 'http://127.0.0.1:3311'
const work = process.env.SCRIBE3_E2E_WORK

if (!work) throw new Error('SCRIBE3_E2E_WORK is required')

const sizes = [
  { width: 2048, height: 1280 },
  { width: 1440, height: 1000 },
  { width: 1024, height: 900 },
  { width: 1440, height: 640 },
]

const chapterEntries = [
  '选择环 · 轻选/重选',
  '存档',
  'Pilot · 主编驾驶',
]
const collaborationEntries = ['主编', ...chapterEntries, '收件箱 · 等你决策']
const switchOrder = [...chapterEntries, '收件箱 · 等你决策', '主编']
const writeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function isNonCanonicalSessionWrite(request) {
  if (request.method !== 'POST') return false
  const url = new URL(request.url)
  return url.pathname === '/api/context/sessions'
    || /^\/api\/context\/sessions\/[^/]+\/navigate$/.test(url.pathname)
}

function workSelector(slug) {
  const escaped = slug.replaceAll('\\', '\\\\').replaceAll('"', '\\"')
  return `[data-work-slug="${escaped}"]`
}

async function capabilityEvidence(page, name) {
  const rightContent = page.getByTestId('right-dock-content')
  if (name === '主编') {
    await rightContent.getByTestId('chief-chat-shell').waitFor({ state: 'visible' })
    return 'chief-chat-shell'
  }
  if (name === '选择环 · 轻选/重选') {
    await rightContent.getByTestId('selection-panel').waitFor({ state: 'visible' })
    return 'selection-panel'
  }
  if (name === '存档') {
    const state = rightContent.getByText(/加载存档|存档列表加载失败|还没有存档点|回看/).first()
    await state.waitFor({ state: 'visible' })
    return (await state.textContent())?.trim() || '存档状态已渲染'
  }
  if (name === 'Pilot · 主编驾驶') {
    const title = rightContent.getByText('Pilot · 主编驾驶', { exact: true }).first()
    await title.waitFor({ state: 'visible' })
    return (await title.textContent())?.trim() || 'Pilot · 主编驾驶'
  }
  if (name === '收件箱 · 等你决策') {
    const state = rightContent.getByText(/加载收件箱|收件箱拉取失败|这页没有等你的事项|没有等你的事项|决策收件箱/).first()
    await state.waitFor({ state: 'visible' })
    return (await state.textContent())?.trim() || '收件箱状态已渲染'
  }
  throw new Error(`missing capability-specific assertion for ${name}`)
}

const browser = await chromium.launch({ headless: true })
const results = []

try {
  for (const size of sizes) {
    const context = await browser.newContext({ viewport: size })
    const page = await context.newPage()
    const consoleMessages = []
    const pageErrors = []
    const requests = []
    const errorResponses = []
    const screenshot = `/tmp/scribe3-unified-rail-${size.width}x${size.height}.png`
    const capabilityContents = {}
    let railRects = null
    let draftPrefill = null
    let failure = null

    page.on('console', (message) => {
      consoleMessages.push({ type: message.type(), text: message.text() })
    })
    page.on('pageerror', (error) => {
      pageErrors.push(error.message)
    })
    page.on('request', (request) => {
      requests.push({ method: request.method(), url: request.url() })
    })
    page.on('response', (response) => {
      if (response.status() >= 400) {
        errorResponses.push({ status: response.status(), method: response.request().method(), url: response.url() })
      }
    })

    try {
      await page.goto(base, { waitUntil: 'networkidle' })
      const workCard = page.locator(workSelector(work))
      assert(await workCard.count() === 1, `expected exactly one work card for ${work}`)
      await workCard.click()

      const rail = page.getByTestId('unified-entry-rail')
      const collaborationRail = page.getByTestId('collaboration-rail')
      await collaborationRail.waitFor()

      assert(await rail.count() === 1, `expected one unified rail, got ${await rail.count()}`)
      await collaborationRail.getByRole('button', { name: '主编', exact: true }).waitFor()
      await collaborationRail.getByRole('button', { name: '收件箱 · 等你决策', exact: true }).waitFor()
      for (const name of chapterEntries) {
        assert(
          await collaborationRail.getByRole('button', { name, exact: true }).count() === 0,
          `${name} visible before selecting a chapter`,
        )
      }

      await page.getByTestId('manuscript-volume-list')
        .getByRole('button', { name: /^(?:第\s*)?1(?:\s*章)?(?:\s|$)/ })
        .first()
        .click()

      for (const name of collaborationEntries) {
        await collaborationRail.getByRole('button', { name, exact: true }).waitFor()
      }

      const railGeometry = await rail.evaluate((element) => {
        const rect = element.getBoundingClientRect()
        return { width: rect.width, left: rect.left, right: rect.right }
      })
      assert(Math.abs(railGeometry.width - 56) <= 1, `unified rail is not 56px: ${JSON.stringify(railGeometry)}`)

      const widthUse = await page.getByTestId('right-panel').evaluate((panel) => {
        const content = panel.querySelector('[data-testid="right-dock-content"]')
        return {
          panel: panel.clientWidth,
          content: content?.clientWidth ?? -1,
          overflow: panel.scrollWidth > panel.clientWidth,
        }
      })
      assert(
        Math.abs(widthUse.panel - widthUse.content) <= 1 && !widthUse.overflow,
        `right content does not reclaim rail width: ${JSON.stringify(widthUse)}`,
      )

      const placement = await rail.evaluate((element) => {
        const collaboration = element.querySelector('[data-testid="collaboration-rail"]')
        const outer = element.getBoundingClientRect()
        const inner = collaboration.getBoundingClientRect()
        return {
          bottomGap: Math.abs(outer.bottom - inner.bottom),
          overlap: inner.top < outer.top,
          flexDirection: getComputedStyle(collaboration).flexDirection,
        }
      })
      assert(
        placement.bottomGap <= 1 && !placement.overlap,
        `collaboration tools are not pinned at the bottom: ${JSON.stringify(placement)}`,
      )
      assert(placement.flexDirection === 'column', `collaboration tools are not vertical: ${JSON.stringify(placement)}`)

      railRects = await page.evaluate(() => {
        const primary = document.querySelector('[data-testid="primary-rail-scroll"]')?.getBoundingClientRect()
        const collaboration = document.querySelector('[data-testid="collaboration-rail"]')?.getBoundingClientRect()
        if (!primary || !collaboration) return null
        const pack = (rect) => ({ top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left })
        return {
          primary: pack(primary),
          collaboration: pack(collaboration),
          intersects: primary.left < collaboration.right
            && primary.right > collaboration.left
            && primary.top < collaboration.bottom
            && primary.bottom > collaboration.top,
        }
      })
      assert(railRects && !railRects.intersects, `primary and collaboration rail rectangles overlap: ${JSON.stringify(railRects)}`)

      for (const name of switchOrder) {
        const button = collaborationRail.getByRole('button', { name, exact: true })
        await button.scrollIntoViewIfNeeded()
        assert(await button.isVisible(), `${name} is not reachable`)
        await button.click()
        assert(await button.getAttribute('aria-pressed') === 'true', `${name} did not become active`)
        capabilityContents[name] = await capabilityEvidence(page, name)
      }

      const chiefButton = collaborationRail.getByRole('button', { name: '主编', exact: true })
      await chiefButton.click()
      assert(
        await page.getByTestId('right-panel').getAttribute('data-collapsed') === '1',
        'right panel did not collapse',
      )
      assert(await chiefButton.isVisible(), 'active entry disappeared after collapse')

      const draftTab = page.getByRole('tab', { name: '草稿', exact: true })
      await draftTab.scrollIntoViewIfNeeded()
      await draftTab.click()
      const draft = page.getByTestId('chapter-workbench-shell')
      await draft.waitFor({ state: 'visible' })
      assert(await draft.getAttribute('data-phase') === 'draft', 'chapter did not switch to draft phase')
      await draft.getByRole('button', { name: '让主编生成', exact: true }).click()

      assert(
        await page.getByTestId('right-panel').getAttribute('data-collapsed') === '0',
        'draft CTA did not reopen the right panel',
      )
      assert(await chiefButton.getAttribute('aria-pressed') === 'true', 'draft CTA did not activate chief')
      await page.getByTestId('chief-chat-shell').waitFor({ state: 'visible' })
      const composer = page.getByTestId('chief-chat-composer').locator('textarea')
      await composer.waitFor({ state: 'visible' })
      draftPrefill = await composer.inputValue()
      assert(
        draftPrefill.includes('据大纲和节拍给第 1 章写一版草稿'),
        `draft CTA did not prefill chief composer: ${JSON.stringify(draftPrefill)}`,
      )

      const overflow = await collaborationRail.evaluate((element) => ({
        scrollHeight: element.scrollHeight,
        clientHeight: element.clientHeight,
        overflowY: getComputedStyle(element).overflowY,
      }))
      assert(
        overflow.scrollHeight <= overflow.clientHeight || ['auto', 'scroll'].includes(overflow.overflowY),
        `collaboration rail clips controls: ${JSON.stringify(overflow)}`,
      )
      const inboxButton = collaborationRail.getByRole('button', { name: '收件箱 · 等你决策', exact: true })
      await inboxButton.scrollIntoViewIfNeeded()
      assert(await inboxButton.isVisible(), 'inbox is not reachable')

      const horizontalOverflow = await page.locator('html').evaluate((element) => ({
        scrollWidth: element.scrollWidth,
        clientWidth: element.clientWidth,
      }))
      assert(
        horizontalOverflow.scrollWidth <= horizontalOverflow.clientWidth,
        `page has horizontal overflow: ${JSON.stringify(horizontalOverflow)}`,
      )
    } catch (error) {
      failure = error instanceof Error ? error.message : String(error)
    } finally {
      await page.screenshot({ path: screenshot })
      const writeRequests = requests.filter((request) => writeMethods.has(request.method))
      const canonicalWriteRequests = writeRequests.filter((request) => !isNonCanonicalSessionWrite(request))
      const consoleErrors = consoleMessages.filter((message) => message.type === 'error')

      if (!failure && canonicalWriteRequests.length) {
        failure = `canonical REST write requests observed: ${JSON.stringify(canonicalWriteRequests)}`
      }
      if (!failure && pageErrors.length) {
        failure = `page errors observed: ${JSON.stringify(pageErrors)}`
      }
      results.push({
        viewport: size,
        status: failure ? 'FAIL' : 'PASS',
        failure,
        screenshot,
        capabilityContents,
        railRects,
        draftPrefill,
        requestMethods: [...new Set(requests.map((request) => request.method))],
        writeRequests,
        canonicalWriteRequests,
        consoleMessages,
        consoleErrors,
        pageErrors,
        errorResponses,
      })
      await context.close()
    }
  }
} finally {
  await browser.close()
}

console.log(JSON.stringify(results, null, 2))
if (results.some((result) => result.status !== 'PASS')) process.exitCode = 1

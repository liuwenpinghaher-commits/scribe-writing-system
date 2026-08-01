// Node 原生测试：断言决策选择器契约（防止 testid 漂移导致「点不到」）
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import {
  DECISION_SELECTORS,
  ensureChiefVisible,
  resolveComposer,
  shouldFinishChiefWait,
  isTerminalHermesRunStatus,
  fetchRunStatusWithTimeout,
  runWithDeadline,
  submitComposerWithDeadline,
  adoptDraftAsFinal,
  workEntryAccessibleName,
  resolveRunWork,
} from './author_decisions.mjs'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('DECISION_SELECTORS contract', () => {
  it('ships a dedicated quality real journey that requires Qwen provider evidence', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /provider\s*===\s*['"]qwen['"]/)
    assert.match(journey, /qwen3\.8-max-preview/)
    assert.match(journey, /provider_request_id/)
    assert.match(journey, /reference_craft_use/)
    assert.match(journey, /作者裁决/)
  })

  it('Makefile exposes the quality real journey as a local true-provider gate', () => {
    const makefile = readFileSync(join(root, '..', '..', 'Makefile'), 'utf8')
    assert.match(makefile, /^e2e-quality-real:/m)
    assert.match(makefile, /quality_reference_author_journey\.mjs/)
  })

  it('quality journey tolerates direct reference workspace rendering without a second open click', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /参考作品标题[\s\S]*isVisible/)
  })

  it('quality journey opens its configured work by immutable slug, not an ambiguous title', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /data-work-slug/)
    assert.match(journey, /configured work .*not unique|目标作品.*不唯一/i)
  })

  it('quality journey creates an isolated work and its configured first chapter when no work is supplied', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /let work = process\.env\.E2E_WORK \|\| null/)
    assert.match(journey, /新建隔离书/)
    assert.match(journey, /新建第\$\{CHAPTER_SEQ\}章/)
    assert.doesNotMatch(journey, /book_df597347/)
  })

  it('quality journey defaults to the documented local frontend port', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /const BASE = process\.env\.E2E_BASE \|\| 'http:\/\/127\.0\.0\.1:3311'/)
  })

  it('质量旅程同时识别目录中的序号前缀和“第N章”真实标签', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /new RegExp\(`\^\(\?:\$\{CHAPTER_SEQ\}/)
    assert.ok(journey.includes('第\\\\s*${CHAPTER_SEQ}\\\\s*章'))
    assert.doesNotMatch(journey, /name:\s*['"]1 第1章['"]/)
  })

  it('质量旅程在目录折叠时会先通过真实恢复按钮展开目录', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    const stageSelector = journey.indexOf('async function selectChapterStage')
    const chapterLocator = journey.indexOf("const chapter = page.getByRole('button'")
    assert.ok(stageSelector >= 0 && chapterLocator > stageSelector, '缺少章节选择流程')
    const section = journey.slice(stageSelector, chapterLocator)
    assert.match(section, /directory-restore-button/)
    assert.match(section, /getByTestId\('manuscript-directory'\)/)
  })

  it('quality journey waits for its own snapshot POST before accepting ten-dimension UI as fresh evidence', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /waitForResponse/)
    assert.match(journey, /\/quality\/snapshot/)
    assert.match(journey, /evaluationResponse\.status\(\) === 202/)
  })

  it('质量旅程等待后台作业 ready，并在作者裁决前核验二十条执行证据', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /qualityJobStatus/)
    assert.match(journey, /status === 'ready'/)
    assert.match(journey, /traces\.length === 20/)
  })

  it('craft journey repairs individual Gate A gaps through MCP instead of API seeding', () => {
    const journey = readFileSync(join(root, 'e2e/craft_first_journey.mjs'), 'utf8')
    assert.match(journey, /gateARepairPrompts/)
    assert.match(journey, /Gate-A repair/)
    assert.match(journey, /s3_add_character_relation/)
  })

  it('质量旅程在接受正文前经 MCP 补齐 Gate A，而不是把工艺门当作可跳过的障碍', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /prepareCraftReadiness/)
    assert.match(journey, /\/craft-gates\?work=/)
    assert.match(journey, /s3_set_intent/)
    assert.match(journey, /s3_add_character_relation/)
    assert.match(journey, /s3_plant_promise/)
    assert.ok(
      journey.indexOf('await prepareCraftReadiness(page)') < journey.indexOf('await ensureOriginalProse(page, approvedFingerprint)'),
      '必须先补齐书级工艺准备，再允许作者接受正文提案',
    )
  })

  it('质量旅程在接受正文前经 MCP 完成大纲、节拍和限知演绎脚手架', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /prepareChapterScaffold/)
    assert.match(journey, /s3_patch_chapter_plan/)
    assert.match(journey, /involved_characters/)
    assert.match(journey, /deductions/)
    assert.match(journey, /stage: '大纲'/)
    assert.match(journey, /stage: '演绎'/)
    assert.match(journey, /selectChapterStage\(page, prompt\.stage\)/)
    assert.ok(
      journey.indexOf('await prepareChapterScaffold(page)') < journey.indexOf('await ensureOriginalProse(page, approvedFingerprint)'),
      '必须先写入并回读章节脚手架，再允许作者接受正文提案',
    )
  })

  it('质量旅程不会把旧正文冒充为当前批准参考已经消费的正文', () => {
    const journey = readFileSync(join(root, 'e2e/quality_reference_author_journey.mjs'), 'utf8')
    assert.match(journey, /ensureOriginalProse\(page, approvedFingerprint\)/)
    assert.match(journey, /reference-craft-uses/)
  })

  it('craft journey must repair a failed chapter-quality review through MCP before declaring failure', () => {
    const journey = readFileSync(join(root, 'e2e/craft_first_journey.mjs'), 'utf8')
    assert.match(journey, /QUALITY repair/)
    assert.match(journey, /s3_get_chapter/)
    assert.match(journey, /s3_save_chapter/)
    assert.match(journey, /qualityReview/)
  })

  it('exports stable playwright hooks for approve/accept', () => {
    assert.equal(DECISION_SELECTORS.runApprove, '[data-testid="run-approve"]')
    assert.equal(DECISION_SELECTORS.draftAccept, '[data-testid="draft-accept"]')
    assert.equal(DECISION_SELECTORS.draftUseCandidate, '[data-testid="draft-use-candidate"]')
    assert.equal(DECISION_SELECTORS.runApproveStale, '[data-testid="run-approve-stale"]')
    assert.ok(DECISION_SELECTORS.writeComposer.includes('提思路'))
    assert.ok(DECISION_SELECTORS.chiefComposer.includes('问主编'))
    assert.ok(DECISION_SELECTORS.chiefComposer.includes('^='), 'prefix match for @-suffix placeholders')
    assert.equal(DECISION_SELECTORS.stageFill, '[data-testid="stage-fill"]')
  })

  it('ChiefSlotContext ProposalBar ships stage-fill testid wiring', () => {
    const src = readFileSync(join(root, 'src/ChiefSlotContext.jsx'), 'utf8')
    assert.match(src, /stage-fill/)
  })

  it('DraftCard.jsx ships data-testid draft-accept / draft-use-candidate', () => {
    const src = readFileSync(join(root, 'src/editor/DraftCard.jsx'), 'utf8')
    assert.match(src, /data-testid="draft-accept"/)
    assert.match(src, /data-testid="draft-use-candidate"/)
    assert.match(src, /data-testid="draft-reject"/)
  })

  it('ChiefDock and WriteChat ship data-testid run-approve', () => {
    const chief = readFileSync(join(root, 'src/ChiefDock.jsx'), 'utf8')
    const write = readFileSync(join(root, 'src/WriteChat.jsx'), 'utf8')
    assert.match(chief, /data-testid="run-approve"/)
    assert.match(write, /data-testid="run-approve"/)
  })

  it('exports ensureChiefVisible for collapsed-dock recovery', () => {
    assert.equal(typeof ensureChiefVisible, 'function')
  })

  it('exports resolveComposer so reliability journeys share the production-tested fallback order', () => {
    assert.equal(typeof resolveComposer, 'function')
  })

  it('chiefSay returns its observed Hermes Run identity for caller-side failure diagnosis', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.match(src, /run: \{ id: runId, work: runWork, terminal: runTerminal, status: runStatus \}/)
  })

  it('Hermes Run 轮询从 POST 载荷保留隔离作品 work，避免缺 work 时被后端拒绝', () => {
    assert.equal(
      resolveRunWork('http://127.0.0.1:3311/api/ai/runs', JSON.stringify({ work: 'book_isolated' })),
      'book_isolated',
    )
    assert.equal(
      resolveRunWork('http://127.0.0.1:3311/api/ai/runs?work=book_query', ''),
      'book_query',
    )
    assert.equal(resolveRunWork('http://127.0.0.1:3311/api/ai/runs', '{bad json'), '')
  })

  it('ensureChiefVisible must not re-click pressed 主编 (Rail re-click = collapse)', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.match(src, /aria-pressed/)
    assert.match(src, /pressed === 'true'/)
    assert.match(src, /禁止再点已激活/)
  })

  it('exports ensureInBook for library re-entry after four-col lost', async () => {
    const mod = await import('./author_decisions.mjs')
    assert.equal(typeof mod.ensureInBook, 'function')
  })

  it('作品库重入使用完整作品卡可访问名，避免批量验收书同前缀时误开其它书', () => {
    assert.equal(
      workEntryAccessibleName('跨会话记忆验收·ms5ppy85'),
      '打开跨会话记忆验收·ms5ppy85',
    )
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    const section = src.slice(src.indexOf('export async function ensureInBook'), src.indexOf('export async function ensureChiefVisible'))
    assert.match(section, /getByRole\('button', \{ name: workEntryAccessibleName\(bookTitle\), exact: true \}\)/)
    assert.match(src, /card\.isVisible\(\)/)
    assert.doesNotMatch(section, /slice\(0, 12\)/)
  })

  it('硬导航后若应用已从本地当前作品恢复目标书，重入不得再空等库页书卡', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    const section = src.slice(src.indexOf('export async function ensureInBook'), src.indexOf('export async function ensureChiefVisible'))
    assert.match(section, /waitForBookShellOrLibraryCard\(page, card\)/)
    assert.match(src, /async function waitForBookShellOrLibraryCard/)
  })

  it('作品内恢复以当前 FourPane 根壳为主，并兼容右坞/主编槽的折叠态', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.match(src, /\[data-testid="four-col"\]/)
    assert.match(src, /\[data-testid="right-dock"\]/)
    assert.match(src, /\[data-testid="chief-chat-shell"\]/)
  })

  it('工具写入型 Run 无文本 delta 但已空闲时必须结束等待', () => {
    assert.equal(shouldFinishChiefWait({ busy: true, sawBusy: false, text: '', previousText: '' }), false)
    assert.equal(shouldFinishChiefWait({ busy: false, sawBusy: false, text: '', previousText: '' }), false)
    assert.equal(shouldFinishChiefWait({ busy: false, sawBusy: false, requestSeen: true, text: '', previousText: '' }), false)
    assert.equal(shouldFinishChiefWait({ busy: false, sawBusy: false, requestSeen: true, isHermesRun: true, runTerminal: true, text: '', previousText: '' }), true)
    assert.equal(shouldFinishChiefWait({ busy: false, sawBusy: true, requestSeen: true, isHermesRun: true, runTerminal: false }), false)
    assert.equal(shouldFinishChiefWait({ busy: false, sawBusy: true, text: '', previousText: '' }), false)
    assert.equal(shouldFinishChiefWait({ busy: false, text: '主编已经完成本轮分析', previousText: '主编已经完成本轮分析' }), false)
  })

  it('Hermes Run 已由后端确认终态时，不得被无关可见加载动画拖到超时', () => {
    assert.equal(shouldFinishChiefWait({
      busy: true,
      requestSeen: true,
      isHermesRun: true,
      runTerminal: true,
    }), true)
  })

  it('remote_completed_pending_audit 是 Hermes 远端已结束的终态，不能让真人验收空等超时', () => {
    assert.equal(isTerminalHermesRunStatus('remote_completed_pending_audit'), true)
    assert.equal(isTerminalHermesRunStatus('completed'), true)
    assert.equal(isTerminalHermesRunStatus('streaming'), false)
  })

  it('Run 状态轮询超时后必须释放本轮等待，不能越过 chiefSay 总时限', async () => {
    let aborted = false
    const neverRespondingFetch = (_url, { signal }) => new Promise((_, reject) => {
      signal.addEventListener('abort', () => {
        aborted = true
        reject(new DOMException('aborted', 'AbortError'))
      }, { once: true })
    })

    const status = await fetchRunStatusWithTimeout(neverRespondingFetch, 'http://run.test/status', 15)

    assert.equal(status, null)
    assert.equal(aborted, true)
  })

  it('Run 状态已响应但 JSON body 永不结束时也必须在总时限内释放', async () => {
    const responseWithStalledBody = async () => ({
      ok: true,
      json: () => new Promise(() => {}),
    })

    const outcome = await Promise.race([
      fetchRunStatusWithTimeout(responseWithStalledBody, 'http://run.test/status', 20),
      new Promise((resolve) => setTimeout(() => resolve('outer-timeout'), 80)),
    ])

    assert.notEqual(outcome, 'outer-timeout')
    assert.equal(outcome, null)
  })

  it('主编交互的总时限必须覆盖前置 Playwright 操作，而非只覆盖轮询循环', async () => {
    const outcome = await runWithDeadline(
      () => new Promise(() => {}),
      { timeoutMs: 20, label: '主编交互' },
    )

    assert.equal(outcome.timedOut, true)
    assert.match(outcome.error.message, /主编交互超时/)
  })

  it('正文输入框在阶段切换后失效时也必须在发送时限内退出，不能无限等待 fill', async () => {
    const composer = {
      fill: () => new Promise(() => {}),
      press: async () => { throw new Error('fill 未超时就不应按 Enter') },
    }

    await assert.rejects(
      submitComposerWithDeadline(composer, '只输出正文', { timeoutMs: 20 }),
      /正文发送超时/,
    )
  })

  it('作者接受正文提案同时支持 DraftCard 与草稿阶段的填入决策条', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    const section = src.slice(src.indexOf('export async function acceptDraftProposal'), src.indexOf('export async function ensureInBook'))
    assert.match(section, /DECISION_SELECTORS\.stageFill/)
    assert.match(section, /kind: 'stage'/)
  })

  it('草稿填入后仍要求作者显式采用为正文', async () => {
    let clicks = 0
    const adopt = {
      first: () => adopt,
      waitFor: async ({ state, timeout }) => {
        assert.equal(state, 'visible')
        assert.ok(timeout > 0)
      },
      isDisabled: async () => false,
      click: async () => { clicks++ },
    }
    const page = {
      getByRole: (role, options) => {
        assert.equal(role, 'button')
        assert.deepEqual(options, { name: '采用为正文', exact: true })
        return adopt
      },
    }

    assert.deepEqual(await adoptDraftAsFinal(page, { timeoutMs: 100 }), { kind: 'adopt', clicks: 1 })
    assert.equal(clicks, 1)
  })

  it('chiefSay 必须复用正文发送截止时间，不能在 fill 或 Enter 前无界等待', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    const section = src.slice(src.indexOf('async function chiefSayWithinDeadline'))
    assert.match(section, /await submitComposerWithDeadline\(ta, msg/)
    assert.doesNotMatch(section, /await ta\.click\(/)
  })

  it('chiefSay 对主编栏恢复和输入框解析也必须设置独立截止时间', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    const section = src.slice(src.indexOf('async function chiefSayWithinDeadline'))
    assert.match(section, /label: '恢复主编栏'/)
    assert.match(section, /label: '解析主编输入框'/)
  })

  it('chiefSay 可向真人旅程报告恢复、解析和提交的精确阶段', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.match(src, /onProgress\?\.\('开始恢复主编栏'\)/)
    assert.match(src, /onProgress\?\.\('开始解析主编输入框'\)/)
    assert.match(src, /onProgress\?\.\('开始提交主编输入'\)/)
  })

  it('完成判定只观察可见加载动画，不能被隐藏写作槽的文字误卡住', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.doesNotMatch(src, /bodyBusy\s*=\s*\/书写中\|主编在思考\/\.test\(document\.body\.innerText/)
    assert.match(src, /\.animate-spin/)
  })
})

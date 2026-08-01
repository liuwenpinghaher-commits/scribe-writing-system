// 全量真人作者验收总控：仅编排隔离作品的真实 UI 旅程；不直接写任何正典。
// 每项子旅程自己的断言负责业务回读，本文件只汇总可复现 artifact 与模型证据。
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildAcceptanceReport } from './full_author_acceptance_result.mjs'
import { waitForHermesRunEvidence } from './hermes_run_audit.mjs'

const ROOT = dirname(fileURLToPath(import.meta.url))
const STAMP = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
const ARTIFACT_ROOT = process.env.E2E_ARTIFACT_ROOT
  || join(ROOT, '../../../artifacts/e2e-current', `full-author-acceptance-${STAMP}`)
const INCLUDE_LONG = process.env.E2E_INCLUDE_LONG === '1'
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const HERMES_HOME = process.env.E2E_HERMES_HOME || join(homedir(), '.hermes')

const SHORT_JOURNEYS = [
  { id: 'profile', script: 'codex_complete_profile_approval.mjs' },
  { id: 'graph', script: 'graph_semantics_approval.mjs', depends_on: 'profile' },
  { id: 'faction', script: 'codex_complete_faction_approval.mjs' },
  { id: 'registry-item', script: 'codex_complete_simple_registry_approval.mjs', env: { E2E_KIND: 'item' } },
  { id: 'registry-term', script: 'codex_complete_simple_registry_approval.mjs', env: { E2E_KIND: 'term' } },
  { id: 'registry-rule', script: 'codex_complete_simple_registry_approval.mjs', env: { E2E_KIND: 'world_rule' } },
  { id: 'deduce', script: 'deduce_preview_approval.mjs' },
  { id: 'materials', script: 'material_import_author_consumption.mjs' },
  { id: 'memory', script: 'cross_session_memory_recall.mjs' },
  { id: 'stream-recovery', script: 'stream_stop_partial_recovery.mjs' },
  { id: 'quality-reference', script: 'quality_reference_author_journey.mjs' },
]

const LONG_JOURNEY = { id: 'longform-50k', script: 'hq_wordcount_push.mjs' }

function digest(text) {
  return createHash('sha256').update(text).digest('hex')
}

async function runNode(script, env) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [join(ROOT, script)], {
      cwd: join(ROOT, '..'),
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (chunk) => { stdout += chunk })
    child.stderr.on('data', (chunk) => { stderr += chunk })
    child.on('error', (error) => resolve({ exitCode: -1, stdout, stderr: `${stderr}\n${error.message}` }))
    child.on('close', (code) => resolve({ exitCode: Number.isInteger(code) ? code : -1, stdout, stderr }))
  })
}

async function loadResult(path) {
  try {
    return JSON.parse(await readFile(path, 'utf8'))
  } catch {
    return null
  }
}

function collectRunIds(value, ids = new Set()) {
  if (Array.isArray(value)) {
    for (const item of value) collectRunIds(item, ids)
    return ids
  }
  if (!value || typeof value !== 'object') return ids
  for (const [key, item] of Object.entries(value)) {
    if (/run_?ids?$/i.test(key)) {
      const candidates = Array.isArray(item) ? item : [item]
      for (const candidate of candidates) {
        if (typeof candidate === 'string' && /^run_[a-z0-9]+$/i.test(candidate)) ids.add(candidate)
      }
    }
    if (item && typeof item === 'object') collectRunIds(item, ids)
  }
  return ids
}

async function collectHermesRunEvidence(childResult) {
  const work = childResult?.work
  if (typeof work !== 'string' || !work) return []
  const evidence = []
  for (const runId of collectRunIds(childResult)) {
    try {
      const parsed = await waitForHermesRunEvidence({
        runId,
        readTrace: async () => {
          const response = await fetch(`${API}/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(work)}`)
          if (!response.ok) throw new Error(`trace ${response.status}`)
          return response.json()
        },
        readLog: async (trace) => {
          const profile = trace?.response?.model
          if (typeof profile !== 'string' || !profile) throw new Error('trace 缺少 Hermes profile')
          const logPath = join(HERMES_HOME, 'profiles', profile, 'logs', 'agent.log')
          return readFile(logPath, 'utf8')
        },
      })
      if (parsed) evidence.push(parsed)
    } catch {
      // 审计数据缺失必须使总控拒绝本专项；这里不把 I/O 或网关异常伪装成 Qwen 证据。
    }
  }
  return evidence
}

async function execute(spec, inheritedEnv = {}) {
  const artifact = join(ARTIFACT_ROOT, `${spec.id}.json`)
  const logArtifact = join(ARTIFACT_ROOT, `${spec.id}.log.json`)
  const run = await runNode(spec.script, {
    ...process.env,
    ...inheritedEnv,
    ...spec.env,
    E2E_RESULT_FILE: artifact,
    GOAL_SCRATCH: ARTIFACT_ROOT,
  })
  const childResult = await loadResult(artifact)
  // stdout/stderr 可能含有作者输入或供应商文本，artifact 只保留摘要与 hash，不复制正文。
  await writeFile(logArtifact, JSON.stringify({
    exitCode: run.exitCode,
    stdout_sha256: digest(run.stdout),
    stderr_sha256: digest(run.stderr),
    stdout_bytes: Buffer.byteLength(run.stdout),
    stderr_bytes: Buffer.byteLength(run.stderr),
  }, null, 2))
  const directEvidence = Array.isArray(childResult?.model_evidence) ? childResult.model_evidence : []
  const hermesEvidence = await collectHermesRunEvidence(childResult)
  const evidence = [...directEvidence, ...hermesEvidence]
  if (childResult && typeof childResult === 'object') {
    childResult.model_evidence = evidence
    await writeFile(artifact, JSON.stringify(childResult, null, 2))
  }
  return {
    id: spec.id,
    exitCode: run.exitCode,
    artifact,
    result: {
      ok: childResult?.ok === true,
      evidence,
    },
    childResult,
  }
}

await mkdir(ARTIFACT_ROOT, { recursive: true })
const executed = []
let stoppedAt = null
for (const spec of SHORT_JOURNEYS) {
  let inheritedEnv = {}
  if (spec.depends_on) {
    const dependency = executed.find((step) => step.id === spec.depends_on)?.childResult
    if (!dependency?.work || !dependency?.book) {
      executed.push({ id: spec.id, exitCode: -1, artifact: '', result: { ok: false, evidence: [] } })
      stoppedAt = spec.id
      break
    }
    inheritedEnv = { E2E_WORK: dependency.work, E2E_BOOK_TITLE: dependency.book }
  }
  const step = await execute(spec, inheritedEnv)
  executed.push(step)
  if (step.exitCode !== 0 || step.result.ok !== true) {
    stoppedAt = spec.id
    break
  }
}

const required = SHORT_JOURNEYS.map((spec) => spec.id)
let longRun = { status: 'not_run', reason: 'E2E_INCLUDE_LONG!=1' }
if (INCLUDE_LONG) {
  if (!process.env.E2E_LONG_WORK) {
    longRun = { status: 'not_run', reason: 'E2E_LONG_WORK is required for longform-50k' }
  } else if (!stoppedAt) {
    const step = await execute({ ...LONG_JOURNEY, env: { E2E_WORK: process.env.E2E_LONG_WORK } })
    executed.push(step)
    required.push(LONG_JOURNEY.id)
    longRun = { status: step.exitCode === 0 && step.result.ok ? 'executed' : 'failed', artifact: step.artifact }
  } else {
    longRun = { status: 'not_run', reason: `short journey failed at ${stoppedAt}` }
  }
}

const report = {
  ...buildAcceptanceReport({ required, steps: executed }),
  created_at: new Date().toISOString(),
  artifact_root: ARTIFACT_ROOT,
  stopped_at: stoppedAt,
  longform_50k: longRun,
}
await writeFile(join(ARTIFACT_ROOT, 'summary.json'), JSON.stringify(report, null, 2))
console.log('FULL_AUTHOR_ACCEPTANCE', JSON.stringify({
  ok: report.ok,
  failed_ids: report.failed_ids,
  stopped_at: report.stopped_at,
  longform_50k: report.longform_50k,
  artifact_root: report.artifact_root,
}))
if (!report.ok) process.exitCode = 1

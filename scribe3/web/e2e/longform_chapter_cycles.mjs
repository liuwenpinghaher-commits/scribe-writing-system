// 逐章长程控制器：每一章均执行同一真实 UI/MCP/质量闭环；它不直接写正典。
import { spawn } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildChapterCycleReport, chapterSequence } from './longform_chapter_cycles_result.mjs'

const ROOT = dirname(fileURLToPath(import.meta.url))
const WORK = process.env.E2E_WORK || ''
const BOOK = process.env.E2E_BOOK_TITLE || ''
const START = Number(process.env.E2E_CHAPTER_START || 1)
const END = Number(process.env.E2E_CHAPTER_END || 20)
const RESULT_FILE = process.env.E2E_RESULT_FILE || ''
const ARTIFACT_ROOT = process.env.E2E_ARTIFACT_ROOT || join(ROOT, '../../../artifacts/e2e-current', `longform-cycles-${Date.now()}`)

if (!WORK || !BOOK) throw new Error('必须提供 E2E_WORK 与 E2E_BOOK_TITLE')

async function runNode(seq, artifact) {
  const child = spawn(process.execPath, [join(ROOT, 'quality_reference_author_journey.mjs')], {
    cwd: join(ROOT, '..'),
    env: {
      ...process.env,
      E2E_WORK: WORK,
      E2E_BOOK_TITLE: BOOK,
      E2E_CHAPTER_SEQ: String(seq),
      E2E_RESULT_FILE: artifact,
    },
    stdio: 'inherit',
  })
  return new Promise((resolve) => child.on('close', (code) => resolve(Number.isInteger(code) ? code : -1)))
}

async function load(path) {
  try { return JSON.parse(await readFile(path, 'utf8')) } catch { return null }
}

await mkdir(ARTIFACT_ROOT, { recursive: true })
const requested = chapterSequence(START, END)
const steps = []
for (const seq of requested) {
  const artifact = join(ARTIFACT_ROOT, `chapter-${seq}.json`)
  const exitCode = await runNode(seq, artifact)
  const result = await load(artifact)
  steps.push({ seq, exitCode, artifact, result })
  if (exitCode !== 0 || result?.ok !== true || Number(result?.chapter_seq) !== seq) break
}
const report = {
  ...buildChapterCycleReport({ requested, steps }),
  work: WORK,
  artifact_root: ARTIFACT_ROOT,
  created_at: new Date().toISOString(),
}
if (RESULT_FILE) {
  await mkdir(dirname(RESULT_FILE), { recursive: true })
  await writeFile(RESULT_FILE, JSON.stringify(report, null, 2))
}
console.log('LONGFORM_CHAPTER_CYCLES', JSON.stringify({ ok: report.ok, failed_sequences: report.failed_sequences, artifact_root: ARTIFACT_ROOT }))
if (!report.ok) process.exitCode = 1

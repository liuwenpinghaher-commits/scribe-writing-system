import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { compactDiagnostic, writeJsonArtifact, captureJourneyResult } from './result_artifact.mjs'

test('未得到轮询值时仍保留可诊断文本', () => {
  assert.equal(compactDiagnostic(undefined), 'undefined')
  assert.equal(compactDiagnostic({ ok: false }, 8), '{"ok":fa')
})

test('写入真人验收报告时自动创建父目录', async () => {
  const root = await mkdtemp(join(tmpdir(), 'scribe3-e2e-artifact-'))
  const target = join(root, 'nested', 'report.json')
  try {
    await writeJsonArtifact(target, { ok: false, err: '原始失败' })
    assert.deepEqual(JSON.parse(await readFile(target, 'utf8')), { ok: false, err: '原始失败' })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('旅程异常必须成为结构化失败结果，而不是只剩进程 stderr', async () => {
  assert.equal(typeof captureJourneyResult, 'function')
  const result = await captureJourneyResult(async () => {
    throw new Error('世界规则字段 scope 回读不一致')
  })

  assert.deepEqual(result, {
    ok: false,
    error: '世界规则字段 scope 回读不一致',
  })
})

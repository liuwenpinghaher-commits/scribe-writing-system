#!/usr/bin/env node
/**
 * 铜炉 / Scribe3 · 5 万字 Linux CLI + Playwright 全程验收入口
 *
 * 用法（在 scribe3/web 目录或任意目录）：
 *   E2E_ALLOW_DEPLOYED=1 \
 *   E2E_BASE=http://127.0.0.1:3311 \
 *   E2E_API=http://127.0.0.1:3321 \
 *   node e2e/acceptance_50k/run_50k_acceptance.mjs [--resume]
 *
 * 约束：
 *   - 正文/设定写入只经 Playwright UI → chiefSay / 提案卡 / 批准
 *   - 只读 API 用于断言回查
 *   - 闸绿 ≠ 质量通过（每章 qualityReview）
 */
import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { withPage } from '../lib.mjs'
import { resolveEnv, assertSafeEnvironment } from './env_guard.mjs'
import { loadCheckpoint, saveCheckpoint, emptyCheckpoint } from './checkpoint.mjs'
import { log, flushLogFile, writeJson, getLogLines } from './log.mjs'
import {
  phase1Bootstrap,
  phase2Wcg,
  phase34WriteAll,
  phase5Advanced,
  phase6FinalAudit,
} from './phases.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO = join(HERE, '../../../..')

async function main() {
  const env = resolveEnv()
  process.env.E2E_BOOK_TITLE = env.BOOK
  if (env.WORK) process.env.E2E_WORK = env.WORK

  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 8)
  const artDir = env.ART || join(
    REPO,
    'artifacts',
    `e2e-50k-${stamp}-${env.WORK || 'new'}`,
  )
  mkdirSync(artDir, { recursive: true })
  mkdirSync(`${artDir}/chapters`, { recursive: true })
  mkdirSync(`${artDir}/quality`, { recursive: true })
  mkdirSync(`${artDir}/evidence/memory-recalls`, { recursive: true })
  mkdirSync(`${artDir}/evidence/run-traces`, { recursive: true })
  mkdirSync(`${artDir}/errors`, { recursive: true })

  const L = (m) => log(m, { artDir })
  L(`START art=${artDir}`)
  L(`BOOK=${env.BOOK} TARGET_WORDS=${env.WORD_TARGET} CHAPTERS=${env.TARGET_CHAPTERS}`)

  await assertSafeEnvironment(env)

  let cp = env.RESUME ? loadCheckpoint(artDir) : null
  if (!cp) {
    // 允许从 E2E_ART 旧目录 --resume
    cp = emptyCheckpoint(env)
  } else {
    L(`RESUME from phase=${cp.phase} lastCh=${cp.lastCompletedChapter} work=${cp.work}`)
    if (cp.work) {
      process.env.E2E_WORK = cp.work
      env.WORK = cp.work
    }
    if (cp.book) {
      process.env.E2E_BOOK_TITLE = cp.book
      env.BOOK = cp.book
    }
  }
  // 修正 art 目录名含 work
  let activeArt = artDir
  if (cp.work && artDir.includes('-new')) {
    activeArt = join(REPO, 'artifacts', `e2e-50k-${stamp}-${cp.work}`)
    mkdirSync(activeArt, { recursive: true })
  }
  saveCheckpoint(activeArt, cp)

  const pageResult = await withPage(async (page) => {
    // Phase 1
    if (!['wcg_done', 'writing', 'advanced', 'final', 'done', 'final_failed'].includes(cp.phase)
      || !cp.work) {
      cp = await phase1Bootstrap(page, env, cp, activeArt)
    } else {
      L(`skip phase1 phase=${cp.phase}`)
    }

    // 更新 artifact 路径到真实 slug
    if (cp.work && activeArt.includes('-new')) {
      const next = join(REPO, 'artifacts', `e2e-50k-${stamp}-${cp.work}`)
      mkdirSync(next, { recursive: true })
      activeArt = next
      saveCheckpoint(activeArt, cp)
    }

    // Phase 2
    if (!['writing', 'advanced', 'final', 'done', 'final_failed'].includes(cp.phase)
      || cp.phase === 'settings_done' || cp.phase === 'wcg_done') {
      if (cp.phase !== 'writing' && cp.phase !== 'advanced' && cp.phase !== 'final' && cp.phase !== 'done') {
        cp = await phase2Wcg(page, env, cp, activeArt)
      }
    }

    // Phase 3+4
    if (!['advanced', 'final', 'done', 'final_failed'].includes(cp.phase)
      || cp.phase === 'wcg_done' || cp.phase === 'writing') {
      cp = await phase34WriteAll(page, env, cp, activeArt)
    }

    // Phase 5
    if (!['final', 'done', 'final_failed'].includes(cp.phase) || cp.phase === 'writing' || cp.phase === 'advanced') {
      if (cp.phase !== 'final' && cp.phase !== 'done') {
        cp = await phase5Advanced(page, env, cp, activeArt)
      }
    }

    return { work: cp.work, book: cp.book }
  })

  if (!pageResult.ok) {
    L(`withPage FAIL: ${pageResult.err}`)
    writeJson(`${activeArt}/errors/withpage.json`, pageResult)
    flushLogFile(activeArt)
    console.error('50K_ACCEPTANCE_FAIL', pageResult.err)
    process.exitCode = 1
    // 仍尝试只读终审
  }

  // Phase 6 纯 API，不依赖浏览器
  let summary
  try {
    summary = await phase6FinalAudit(env, cp, activeArt)
  } catch (e) {
    L(`phase6 error: ${e.message}`)
    summary = { ok: false, error: e.message }
    writeJson(`${activeArt}/summary.json`, summary)
  }

  writeJson(`${activeArt}/journey-meta.json`, {
    page_ok: pageResult.ok,
    page_err: pageResult.err,
    errs: pageResult.errs,
    log_lines: getLogLines().length,
  })
  flushLogFile(activeArt)

  console.log('50K_ACCEPTANCE', JSON.stringify({
    ok: summary?.ok === true,
    work: cp.work,
    word_count: summary?.word_count,
    chapter_count: summary?.chapter_count,
    must_all: summary?.must_all,
    art: activeArt,
  }))

  if (summary?.ok !== true) process.exitCode = 1
}

main().catch((e) => {
  console.error('50K_ACCEPTANCE_FATAL', e)
  process.exit(2)
})

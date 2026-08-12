// 断点续传：每章完成后写 checkpoint.json
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname } from 'node:path'

export function checkpointPath(artDir) {
  return `${artDir}/checkpoint.json`
}

export function loadCheckpoint(artDir) {
  const p = checkpointPath(artDir)
  if (!existsSync(p)) return null
  try {
    return JSON.parse(readFileSync(p, 'utf8'))
  } catch {
    return null
  }
}

/**
 * @param {string} artDir
 * @param {object} state
 */
export function saveCheckpoint(artDir, state) {
  mkdirSync(artDir, { recursive: true })
  const payload = {
    ...state,
    updated: new Date().toISOString(),
  }
  writeFileSync(checkpointPath(artDir), JSON.stringify(payload, null, 2))
  return payload
}

export function emptyCheckpoint(env) {
  return {
    phase: 'init',
    work: env.WORK || '',
    book: env.BOOK || '',
    lastCompletedChapter: 0,
    lastCompletedPhase: null,
    run_ids: [],
    must: {},
    should: {},
    could: {},
    chapter_results: {},
    started_at: new Date().toISOString(),
  }
}

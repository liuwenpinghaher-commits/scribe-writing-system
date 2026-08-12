// 统一日志：ISO 时间戳 + 可选落盘
import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'

const lines = []

export function log(msg, { artDir } = {}) {
  const s = `[${new Date().toISOString()}] ${msg}`
  console.log(s)
  lines.push(s)
  if (artDir) {
    try {
      mkdirSync(artDir, { recursive: true })
      appendFileSync(`${artDir}/journey.log`, s + '\n')
    } catch { /* 日志失败不阻塞 */ }
  }
  return s
}

export function getLogLines() {
  return [...lines]
}

export function flushLogFile(artDir) {
  if (!artDir) return
  try {
    mkdirSync(artDir, { recursive: true })
    writeFileSync(`${artDir}/journey.log`, lines.join('\n') + '\n')
  } catch { /* */ }
}

export function writeJson(path, obj) {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, JSON.stringify(obj, null, 2))
}

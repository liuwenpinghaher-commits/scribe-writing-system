import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const files = []
const walk = (dir) => {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    const stat = fs.statSync(full)
    if (stat.isDirectory() && name !== '__tests__') walk(full)
    if (stat.isFile() && /\.(jsx|js)$/.test(name) && !/\.test\./.test(name)) files.push(full)
  }
}
walk(root)

// 结构性 emoji 黑名单(锁/定位/火/警告/关闭符),用显式码点避免 X 型字符混淆:
//   U+1F512 🔒 · U+1F4CD 📍 · U+1F525 🔥 · U+26A0 ⚠ · U+2715 ✕(关闭/删除结构符)
// 刻意不含 U+00D7(×)——那是正当数学乘号(如「13 周 × 7 天」「<0.5×」),非结构性 emoji,禁它会误伤。
const STRUCTURAL_EMOJI = /[\u{1F512}\u{1F4CD}\u{1F525}\u{26A0}\u{2715}]/u
const SMALL_FONT = /text-f10|text-f11/

// 命中定位:违规文件 → 「相对路径:行号 → 命中片段」,失败时能直接跳到行修复(而非只报文件名)。
const locate = (re) => {
  const hits = []
  for (const file of files) {
    const lines = fs.readFileSync(file, 'utf8').split('\n')
    lines.forEach((line, i) => {
      const m = line.match(re)
      if (m) hits.push(`${path.relative(root, file)}:${i + 1} → ${m[0]}`)
    })
  }
  return hits
}

describe('PC UI static contract', () => {
  it('contains no 10px or 11px utility in production JSX', () => {
    expect(locate(SMALL_FONT)).toEqual([])
  })
  it('contains no structural emoji', () => {
    expect(locate(STRUCTURAL_EMOJI)).toEqual([])
  })
})

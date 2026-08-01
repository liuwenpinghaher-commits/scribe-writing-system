import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('写作台不依赖 Google Fonts 等外部字体资源，离线和受限网络下也不能产生字体请求失败', () => {
  const css = readFileSync(new URL('../src/index.css', import.meta.url), 'utf8')

  assert.doesNotMatch(css, /fonts\.googleapis\.com|fonts\.gstatic\.com/i)
})

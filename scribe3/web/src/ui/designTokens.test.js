// @vitest-environment node

import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

const css = fs.readFileSync(new URL('../index.css', import.meta.url), 'utf8')
const hex = (name, block) => {
  const match = block.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`))
  if (!match) throw new Error(`missing color token: ${name}`)
  return match[1]
}
const lum = (value) => {
  const channels = value.match(/[0-9a-f]{2}/gi).map((part) => parseInt(part, 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}
const contrast = (a, b) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05)

describe('PC UI color tokens', () => {
  it('keeps every normal text token at 4.5:1 on canvas', () => {
    const light = css.match(/:root\s*\{([\s\S]*?)\}/)[1]
    for (const name of ['ink', 'muted', 'faint', 'brand', 'ok', 'warn', 'danger']) {
      expect(contrast(hex(name, light), hex('canvas', light)), name).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('keeps dark theme normal text tokens at 4.5:1 on canvas', () => {
    const dark = css.match(/\.dark\s*\{([\s\S]*?)\}/)[1]
    for (const name of ['ink', 'muted', 'faint', 'brand', 'ok', 'warn', 'danger']) {
      expect(contrast(hex(name, dark), hex('canvas', dark)), name).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('defines semantic type roles and never maps them below 12px', () => {
    for (const name of ['meta', 'helper', 'body', 'object-title', 'section-title', 'page-title']) {
      const match = css.match(new RegExp(`--text-${name}:\\s*([0-9.]+)px`))
      expect(match, name).not.toBeNull()
      expect(Number(match[1]), name).toBeGreaterThanOrEqual(12)
    }
  })
})

describe('PC UI layout tokens', () => {
  it('shares one frozen set of default PC dimensions', async () => {
    const { CX, PC_LAYOUT, T } = await import('../layout/tokens.js')

    expect(PC_LAYOUT).toEqual({
      topbar: 44,
      rail: 56,
      directory: { min: 240, ideal: 264, max: 320 },
      detail: { min: 600 },
      right: { min: 300, ideal: 336, max: 380 },
    })
    expect(Object.isFrozen(PC_LAYOUT)).toBe(true)
    expect(T).toBeDefined()
    expect(T.color.brand).toBe('var(--color-brand)')
    expect(T.h.rail).toBe('56px')
    expect(CX).toBeDefined()
    expect(CX.input).toBe('w-full rounded-lg border border-line bg-canvas px-3 h-9 text-f13 text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60')
    expect(CX.textarea).toBe('w-full rounded-lg border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 resize-y')
  })
})

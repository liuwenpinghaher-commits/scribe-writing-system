import { describe, it, expect, vi, beforeEach } from 'vitest'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'

// BinderLayout 的 handleVolumeRename 合同:不调用 patchVolume,只走主编种子。
// 这里直接测 shipped helper 与源码静态契约(避免挂载整棵四栏树)。
import { readFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('BinderLayout volume rename seed contract', () => {
  beforeEach(() => sessionStorage.clear())

  it('source uses seedChiefNarrativeWrite and does not call patchVolume in rename handler', () => {
    const src = readFileSync(join(root, 'BinderLayout.jsx'), 'utf8')
    expect(src).toMatch(/seedChiefNarrativeWrite/)
    // rename handler block must not contain patchVolume
    const m = src.match(/handleVolumeRename[\s\S]{0,280}/)
    expect(m).toBeTruthy()
    expect(m[0]).not.toMatch(/patchVolume/)
    expect(m[0]).toMatch(/seedChiefNarrativeWrite/)
  })

  it('volume title seed focuses chief', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    seedChiefNarrativeWrite('volume', '分卷 v1', '请将卷名更新为: 新名')
    expect(tabs).toContain('chief')
    expect(sessionStorage.getItem('s3.chief.seed')).toMatch(/新名/)
  })
})

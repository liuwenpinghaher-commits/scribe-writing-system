import { describe, it, expect } from 'vitest'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('shouldUseHermesRun', () => {
  it('routes north-star intent write to Hermes Run', () => {
    expect(shouldUseHermesRun(
      '请登记/更新本书北极星意图并写入落库(需我审批):\n读者感受:…\n必须用 s3_set_intent')).toBe(true)
  })

  it('routes character appearance correction to Hermes Run', () => {
    expect(shouldUseHermesRun(
      '请更新角色沈砚的外貌档案:改为右手茧。用 s3_patch_character 写入落库。')).toBe(true)
  })

  it('keeps pure prose generation off Hermes Run', () => {
    expect(shouldUseHermesRun('请直接写第1章完整正文草稿，约800字')).toBe(false)
  })
})

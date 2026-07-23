import { describe, it, expect } from 'vitest'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('shouldUseHermesRun', () => {
  it('force: s3_ tools and 写入提案 seeds go to Hermes Run', () => {
    expect(shouldUseHermesRun(
      '请用 s3_add_volume 创建卷 title=潮生。未获批准不得声称已落库。')).toBe(true)
    expect(shouldUseHermesRun(
      '使用工具 s3_reorder_chapters: volume_id="v1", order=[2,1]')).toBe(true)
    expect(shouldUseHermesRun(
      '使用工具 s3_delete_volume(volume_id="v1")')).toBe(true)
    expect(shouldUseHermesRun(
      '使用工具 s3_add_material(title, body);提交写入提案供我批准。')).toBe(true)
    expect(shouldUseHermesRun(
      '请新建设定「甲」(类型:character)并写入落库(需我审批)。使用工具 s3_add_character')).toBe(true)
    expect(shouldUseHermesRun(
      '请更新/更正「第3章大纲」(outline)并提交写入提案供我批准。')).toBe(true)
  })

  it('north star / character patch force', () => {
    expect(shouldUseHermesRun(
      '请登记/更新本书北极星意图并写入落库')).toBe(true)
    expect(shouldUseHermesRun(
      '请更新/更正角色「甲」的档案并写入落库(需我审批)')).toBe(true)
  })

  it('prose generation stays on write stream, not world-write Run', () => {
    expect(shouldUseHermesRun('请直接写第1章完整正文草稿，约800字')).toBe(false)
  })

  it('plain discussion without mutation stays false', () => {
    expect(shouldUseHermesRun('这一章节奏如何？')).toBe(false)
  })
})

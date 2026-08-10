/**
 * 卷结构写入的主编种子（纯字符串 · 可单测）。
 * 正式卷改纲必须点名 s3_patch_volume + volume_id（KD-VOL-14 / S4）。
 * 无 form-wall REST 落库。
 */

export function buildPatchVolumeSeed({
  volumeId,
  title = '',
  intro = '',
  color = '',
  sort_order = 0,
} = {}) {
  const vid = String(volumeId ?? '').trim()
  if (!vid) {
    throw new Error('buildPatchVolumeSeed: volumeId required')
  }
  const lines = [
    `请用 s3_patch_volume 更新卷 volume_id=${vid}（需我审批）。`,
    `只传要改的字段（MERGE）:`,
    `- title=${title || '（保持或清空请说明）'}`,
    `- color=${color || '（空）'}`,
    `- sort_order=${sort_order}`,
    `- intro 如下:`,
    intro?.trim() ? intro.trim() : '（空 · 空则写路径不注入 volume_intro）',
    '未获批准不得声称已落库。',
  ]
  return lines.join('\n')
}

export function buildAddVolumeSeed({
  title,
  intro = '',
  color = '',
  sort_order = 1,
  chapterSeqs = [],
} = {}) {
  const t = String(title || '').trim()
  if (!t) throw new Error('buildAddVolumeSeed: title required')
  const ch = (chapterSeqs || []).filter((n) => n != null).join(', ')
  return [
    `请用 s3_add_volume 创建卷 title=${t}, sort_order=${sort_order}`
      + (color ? `, color=${color}` : '')
      + (intro?.trim() ? `, intro 如下:\n${intro.trim()}` : '。'),
    ch
      ? `创建后请将未分卷章节 [${ch}] 归入该卷(可用 s3_patch_chapter_meta)。`
      : '',
    '未获批准不得声称已落库。',
  ].filter(Boolean).join('\n')
}

/**
 * 卷结构写入的主编种子（纯字符串 · 可单测）。
 * 正式卷改纲必须点名 s3_patch_volume + volume_id（KD-VOL-14 / S4）。
 * 无 form-wall REST 落库。
 */

function chapterAccountSeedLines(chapters = []) {
  const rows = (chapters || []).filter(Boolean)
  if (!rows.length) {
    return [
      '章壳补齐后，把每一章各办哪一件补进卷纲。现在不要发明还不存在的章夜。',
    ]
  }
  const body = rows.map((c) => {
    const title = String(c.title || '').trim() || `第${c.seq}章`
    const syn = String(c.synopsis || '').trim() || '这章还没立要办的事'
    return `- 第${c.seq}章《${title}》：${syn}`
  })
  return [
    '按本卷每一章各写一笔账，禁止只写其中一章的夜。本卷已有章：',
    ...body,
  ]
}

export function buildPatchVolumeSeed({
  volumeId,
  title = '',
  intro,
  color = '',
  sort_order = 0,
  chapters = [],
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
  ]
  if (intro !== undefined) {
    lines.push('- intro 如下（按本卷每一章各写一笔账，禁止只写其中一章的夜。没改卷纲就不要带 intro）:')
    lines.push(intro?.trim() ? intro.trim() : '（空 · 空则写路径不注入 volume_intro）')
  }
  lines.push(...chapterAccountSeedLines(chapters))
  lines.push('未获批准不得声称已落库。')
  return lines.join('\n')
}

export function buildAddVolumeSeed({
  title,
  intro = '',
  color = '',
  sort_order = 1,
  chapterSeqs = [],
  chapters = [],
} = {}) {
  const t = String(title || '').trim()
  if (!t) throw new Error('buildAddVolumeSeed: title required')
  const ch = (chapterSeqs || []).filter((n) => n != null).join(', ')
  return [
    `请用 s3_add_volume 创建卷 title=${t}, sort_order=${sort_order}`
      + (color ? `, color=${color}` : '')
      + (intro?.trim() ? `, intro 如下:\n${intro.trim()}` : '。'),
    '按本卷每一章各写一笔账，禁止只写其中一章的夜。',
    ...chapterAccountSeedLines(chapters),
    ch
      ? `创建后请将未分卷章节 [${ch}] 归入该卷(可用 s3_patch_chapter_meta)。`
      : '',
    '未获批准不得声称已落库。',
  ].filter(Boolean).join('\n')
}

// title 与"第N章"同义时只显示一次,否则"第N章 · 小标题"。
export function chapterLabel(seq, title) {
  const def = `第${seq}章`
  return (!title || title.trim() === def) ? def : `${def} · ${title}`
}

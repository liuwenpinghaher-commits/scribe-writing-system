// 把主编提案应用到正文。selection 用选区偏移精确替换;原文漂移则拒绝(不静默追加)。
// 偏移语义:to 是固定锚点,实际起始由 to - text.length 推导,防止 from 因编辑漂移。
// 返回 { next, ok, drifted? }。
export function applyProposal(prose, proposal, sel) {
  const p = proposal?.prose ?? ''
  if (proposal?.scope === 'chapter') return { next: p, ok: true }
  if (proposal?.scope === 'append') {
    return { next: (prose ? prose + '\n\n' : '') + p, ok: true }
  }
  // selection:需要有效选区偏移
  if (sel && Number.isInteger(sel.from) && Number.isInteger(sel.to)) {
    // 用 to 锚点 + text.length 推导真实起始,避免 from 因前文编辑漂移
    const actualFrom = sel.to - (sel.text?.length ?? 0)
    if (actualFrom >= 0 && prose.slice(actualFrom, sel.to) === sel.text) {
      return { next: prose.slice(0, actualFrom) + p + prose.slice(sel.to), ok: true }
    }
    return { next: prose, ok: false, drifted: true }   // 漂移:交给 UI 提示作者
  }
  // 无偏移信息:退化成追加(不猜测位置)
  return { next: (prose ? prose + '\n\n' : '') + p, ok: true }
}

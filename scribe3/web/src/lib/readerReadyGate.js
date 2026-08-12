/**
 * dual-lamp 前端纯函数：中文双状态（可开写 / 可给读者）
 * 不把 lamps.reader.ok 单独渲染成「可连载」。
 */

export function phaseLabel(phase) {
  switch (phase) {
    case 'green':
      return '可读：已确认'
    case 'yellow':
      return '可读：机判过关，请通读确认'
    case 'red':
    default:
      return '可读：未过关'
  }
}

export function scaffoldLabel(ok) {
  if (ok === true) return '可开写'
  if (ok === false) return '材料未齐'
  return '可开写：未知'
}

/**
 * @param {object|null} readerReady post-check / reader_ready 载荷
 * @returns {{ scaffoldChip: string, readerChip: string, mayClaimReadable: boolean, phase: string }}
 */
export function dualLampChips(readerReady) {
  const rr = readerReady || {}
  const lamps = rr.lamps || {}
  const sc = lamps.scaffold || {}
  const rd = lamps.reader || {}
  const claims = rr.claims || {}
  const phase = rd.phase || (rd.ok ? 'yellow' : 'red')
  return {
    scaffoldChip: scaffoldLabel(sc.ok),
    readerChip: phaseLabel(phase),
    mayClaimReadable: Boolean(claims.may_claim_readable),
    phase,
    blocking: rd.blocking || [],
  }
}

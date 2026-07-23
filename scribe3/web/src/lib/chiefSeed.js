/**
 * 主编种子 + 右栏聚焦（统一作者「让主编写入」合同）。
 * 与 WriteLayout / studioDocks 一致：sessionStorage + s3-chief-seed + s3-right-tab。
 */

export function focusChiefWithSeed(text) {
  const payload = String(text ?? '')
  try { sessionStorage.setItem('s3.chief.seed', payload) } catch { /* */ }
  try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: payload })) } catch { /* */ }
  try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
  return payload
}

/** 设定库档案补全/更正（Codex 主路径） */
export function seedChiefCodexWrite(type, row = {}, hint = '') {
  const name = row.name || row.text || row.id || type
  const lines = type === 'chars'
    ? [
      `请更新/更正角色「${name}」的档案并写入落库(需我审批):`,
      '可补全或修正:外貌/性格/前史/目标/恐惧/首次出场等。',
      '必须先用只读工具核实,再用 s3_patch_character(或对应写工具)写入。',
      '未获批准不得声称已落库。',
    ]
    : [
      `请根据本书上下文补全/更正设定「${name}」(类型:${type})并提交写入提案供我批准。`,
      '先只读核实当前库内事实,再调用对应 s3_ 写工具;未获批准不得声称已落库。',
    ]
  if (hint) lines.push(String(hint))
  return focusChiefWithSeed(lines.join('\n'))
}

/**
 * 通用叙事元数据种子（大纲/节拍/演绎/卷纲/章信息/意图/伏笔决策等）。
 * @param {string} scope 简短域标签
 * @param {string} target 对象描述（如「第 3 章大纲」）
 * @param {string} [hint] 具体意图
 */
export function seedChiefNarrativeWrite(scope, target, hint = '') {
  const lines = [
    `请更新/更正「${target}」(${scope})并提交写入提案供我批准。`,
    '先用只读工具核实当前库内内容,再调用对应 s3_ 写工具;未获批准不得声称已落库。',
  ]
  if (hint) lines.push(String(hint))
  return focusChiefWithSeed(lines.join('\n'))
}

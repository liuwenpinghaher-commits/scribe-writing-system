const roleKeys = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return []
  const bare = raw.split(':', 2).at(-1)
  return [raw, bare, `role:${bare}`]
}

/**
 * 返回有出场角色但没有可消费限知投影的规范角色 ID。
 * 供真人 E2E 在演绎阶段写后回读，避免一次工具调用显示成功却留下 B5 缺口。
 */
export function missingDeductionProjections(chapter = {}) {
  const involved = Array.isArray(chapter.involved_characters)
    ? chapter.involved_characters.filter(Boolean).map(String)
    : []
  const projected = new Set()
  for (const deduction of Array.isArray(chapter.deductions) ? chapter.deductions : []) {
    if (!deduction || !String(deduction.prose || '').trim()) continue
    for (const key of roleKeys(deduction.character_id || deduction.character || deduction.role)) {
      projected.add(key)
    }
  }
  return involved.filter((id) => !roleKeys(id).some((key) => projected.has(key)))
}

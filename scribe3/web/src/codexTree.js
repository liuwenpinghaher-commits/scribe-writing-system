// 批D 件1:世界真相(引擎 proposition)项目树分类的纯投影。
// 后端 /project-tree 已含该分类时 BinderLayout 不重复注入；仅作缺失时兜底。
// GET /facts 的行:{ id:'fact:xxxx', entity, attribute, is_secret, value }
//   —— 私密命题 value 被后端屏蔽为 null(_facts,reveal_secret=False),叶不露值、只挂 secret 角标。
// 单独成文件(不经 BinderLayout → sigma/WebGL 的重导入链),便于纯函数单测。
// Must 滤噪真源在后端 project_tree；本兜底仍滤 获知/行动（无 source 时无法藏 bridge）。

const localOf = (oid) => (oid || '').split(':').pop()

const NOISE_ATTRS = new Set(['获知', '行动', 'from_knowledge'])

export function buildPropositionCategory(facts) {
  const leaves = (facts || [])
    .filter((f) => !NOISE_ATTRS.has(String(f.attribute || '').trim()))
    .map((f) => {
    const local = localOf(f.id)
    const ent = localOf(f.entity)
    // 私密命题不露值(value=null),只显 实体·属性 + 锁角标;公开命题追加 = 值
    const shownVal = f.is_secret ? '' : (f.value ? ` = ${f.value}` : '')
    const label = (ent ? `${ent}·` : '') + (f.attribute || '—') + shownVal
    const leaf = { id: `proposition:${local}`, type: 'proposition', ref: local, label }
    if (f.is_secret) leaf.badges = [{ kind: 'secret', tone: 'faint' }]
    return leaf
  })
  return {
    id: 'cat:proposition', type: 'codex_category', ref: 'proposition',
    label: '世界真相',
    meta: { hint: '全库时态账本 · 日常请打开角色卡', advanced: true },
    badges: [{ kind: 'count', value: leaves.length }], children: leaves,
  }
}

// 批D 件1:命题(proposition)项目树分类的纯投影。
// 后端 /project-tree 不含命题分类(命题是章级时态数据,非命名条目),故前端注入。
// GET /facts 的行:{ id:'fact:xxxx', entity, attribute, is_secret, value }
//   —— 私密命题 value 被后端屏蔽为 null(_facts,reveal_secret=False),叶不露值、只挂 secret 角标。
// 单独成文件(不经 BinderLayout → sigma/WebGL 的重导入链),便于纯函数单测。

const localOf = (oid) => (oid || '').split(':').pop()

export function buildPropositionCategory(facts) {
  const leaves = (facts || []).map((f) => {
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
    id: 'cat:proposition', type: 'codex_category', ref: 'proposition', label: '命题',
    badges: [{ kind: 'count', value: leaves.length }], children: leaves,
  }
}

// 对象类型注册表(spec §4 系统地基):一套契约统治所有对象类型。
// 新对象类型(事件/伏笔…)只需在此登记一条,四区布局的顶栏tab/详情/右侧辅助自动适配,
// 不用再为它单独设计一套布局。这是"从整体"最高体现——一套规则统治所有。
export const registry = {
  chapter: {
    crumb: (o) => `${o.volume || '卷'} › ${o.title || `第${o.seq}章`}`,
    tabs: ['大纲', '节拍', '演绎', '草稿', '正文'],
    status: (o) => `${((o.word_count || 0) / 1000).toFixed(1)}k · 已存`,
    auxTabs: ['参考', '校验', '存档'],
  },
  character: {
    crumb: (o) => `设定库 › 角色 › ${o.name || '—'}`,
    tabs: ['档案', '弧光', '关系'],
    status: (o) => `首现第${o.first_chapter || '?'}章`,
    auxTabs: ['关系图', '被引用'],
  },
  material: {
    crumb: (o) => `素材库 › ${(o.ref_tags || [])[0] || '素材'} › ${o.title || '—'}`,
    tabs: ['正文', '关键词'],
    status: (o) => `被参考${o.recall_count || 0}次`,
    auxTabs: ['联想', '用在哪'],
  },
}

// 纯函数:给类型+对象,算出模板四要素(crumb/tabs/status/auxTabs)。未知类型返回 null。
export function getObjectMeta(type, obj) {
  const r = registry[type]
  if (!r) return null
  return { crumb: r.crumb(obj), tabs: r.tabs, status: r.status(obj), auxTabs: r.auxTabs }
}

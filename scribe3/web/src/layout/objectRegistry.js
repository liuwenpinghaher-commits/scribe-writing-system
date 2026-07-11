// 对象呈现契约(spec §4 系统地基):给一个项目树节点,算出「对象外框」头部的基础呈现数据。
//
// 旧版本这里是 type/obj 风格的 registry + getObjectMeta(ObjectFrame 自己反查注册表)。
// 已整体替换:ObjectFrame 改为纯外部呈现接口(props 直传),不再认注册表;呈现数据统一由本函数从
// 节点(node)算出。这样「谁决定套外框、套什么头部」只有一处真相,不再一处查表一处传 props 的双头。
//
// 仅 chapter / character / material 三类返回呈现数据;其余类型(容器/横切视图/创建表单/能力详情/命题…)
// 返回 null,调用方(DetailPane)据此决定「不包对象外框」,让这些分支保持既有渲染不变。
export function presentationForNode(node) {
  if (!node) return null
  // title 兜底用 ref:label 缺省时也不产生空标题(<h1> 恒有可读名)。
  const title = node.label || (node.ref != null ? String(node.ref) : '')
  switch (node.type) {
    case 'chapter':
      // 章的阶段 tab 与状态徽章留给 Task 7 接;此处只给最小头部(面包屑 + 标题)。
      return { breadcrumb: '手稿', title }
    case 'character':
      return { breadcrumb: '设定库 / 角色', title }
    case 'material':
      return { breadcrumb: '素材库', title }
    default:
      return null
  }
}

// 块三:通用选中 focus → 主编聚焦话术(纯函数,便于单测)。
//
// focusTalk(focus) 返回 { label, prefix, suggests } 或 null。null = 调用方回退既有 selContext:
//  - focus 为空 / origin==='sel' 镜像 → 视图级与项目树级话术保持现状(验收⑤⑦不回退);
//  - type==='deduction' → 演绎话术由 selContext 演绎分支按 live 演绎目标生成(块二验收⑥不回退)。

const KIND_NAME = {
  chapter: '章', scene: '场景', character: '角色', faction: '势力', item: '物品', term: '术语',
  world_rule: '世界规则', promise: '伏笔', motif: '母题', event: '事件', frame_fact: '命题', view: '视图',
}

const short = (s, n = 24) => { const t = String(s || ''); return t.length > n ? t.slice(0, n - 1) + '…' : t }

export function focusTalk(focus) {
  if (!focus || focus.origin === 'sel' || focus.type === 'deduction') return null
  const p = focus.payload || {}
  const name = String(focus.label || focus.id || '')
  switch (focus.type) {
    case 'promise': {
      const setup = p.setup_chapter != null ? `第${p.setup_chapter}章埋` : '埋点未知'
      const payoff = p.payoff_chapter != null ? `第${p.payoff_chapter}章收` : '待收'
      return {
        label: `伏笔 · ${short(name)}`,
        prefix: `【当前聚焦:伏笔「${name}」(${setup},${payoff}${p.overdue ? ',已超期' : ''})】\n`,
        suggests: [`这条伏笔「${short(name, 16)}」接下来该怎么推进或回收?`, '围绕这条伏笔,还能埋哪些呼应线索?'],
      }
    }
    case 'motif':
      return {
        label: `母题 · ${short(name)}`,
        prefix: `【当前聚焦:母题「${name}」${p.theme ? `(主题:${p.theme})` : ''}${p.evidence ? `;本章触及:「${p.evidence}」` : ''}】\n`,
        suggests: [`母题「${short(name, 16)}」在后文还能怎么变奏?`, '这个母题现在会不会用得太满/太直白?'],
      }
    case 'event': {
      const catName = { event: '事件', arc: '弧光', relation: '关系' }[p.cat] || '事件'
      return {
        label: `${catName} · ${short(name)}`,
        prefix: `【当前聚焦:时间线${catName}「${name}」${p.chapter != null ? `(第${p.chapter}章)` : ''}】\n`,
        suggests: [`把「${short(name, 16)}」的前因后果理一理?`, `这个${catName}对后文有什么牵动?`],
      }
    }
    case 'frame_fact': {
      if (p.secret) return {
        label: '命题 · 🔒 私密',
        prefix: '【当前聚焦:一条私密命题(内容不展示明文,讨论时请勿泄露)】\n',
        suggests: ['这条私密命题的知情面现在铺得对吗?', '围绕它的戏剧反讽还能怎么用?'],
      }
      return {
        label: `命题 · ${short(name)}`,
        prefix: `【当前聚焦:命题/已知事实「${name}」】\n`,
        suggests: [`「${short(name, 16)}」现在谁知道谁不知道,信息差够吗?`, '这条事实对当前剧情有什么可用张力?'],
      }
    }
    default: {
      const kindName = KIND_NAME[focus.type] || focus.type
      return {
        label: `${kindName} · ${short(name)}`,
        prefix: `【当前聚焦:${kindName}「${name}」】\n`,
        suggests: [`聊聊${kindName}「${name}」,有什么可以深挖/校验的?`, `「${short(name, 16)}」和已有设定有冲突吗?`],
      }
    }
  }
}

/** focus 参与主编 chat 历史 key 的判别段:显式聚焦各自成串;镜像/演绎不改 key
 *  (演绎生成中切目标绝不能因 chatKey 变化而中止在途流——块二口径)。 */
export function focusChatKey(focus) {
  if (!focus || focus.origin === 'sel' || focus.type === 'deduction') return ''
  return `:focus:${focus.type}:${focus.id}`
}

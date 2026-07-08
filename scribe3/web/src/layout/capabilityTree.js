export const CAPABILITY_TREE = {
  deduce: {
    title: '演绎',
    badge: '当前章',
    current: (seq) => seq != null ? `第 ${seq} 章` : '未选章',
    subtitle: '场景真相 / 角色限知',
    inputPlaceholder: '切章 / 搜角色',
    primaryAction: '同步',
    chips: ['同步当前章', '场景真相', '角色限知'],
    groups: [
      {
        id: 'truth',
        label: '场景基础',
        meta: '全知',
        tone: 'brand',
        meaning: '先整理本章客观真相,作为所有角色限知投影的共同来源。',
        constraint: '场景真相可以含隐藏机制,但不能直接等同于正文里某个角色知道的内容。',
        scope: '第 {seq} 章演绎底座',
        actions: ['查看真相草稿', '同步角色投影', '问主编补全'],
        related: [['三栏详情', '场景真相编辑器'], ['主编上下文', '演绎阶段']],
        rows: [
          { id: 'deduce:truth', label: '场景真相', type: 'deduce_view', ref: { view: 'truth' }, meta: '3' },
        ],
      },
      {
        id: 'limited',
        label: '限知分类',
        meta: '角色',
        tone: 'danger',
        meaning: '按当前章角色视角分出可写、禁写、误判和公开信息。',
        constraint: '角色限知不能越过场景真相;先看分类总览,再进入具体角色或冲突项。',
        scope: '第 {seq} 章角色限知',
        actions: ['查看全部命中正文', '校验本章泄露', '问主编怎么改'],
        related: [['角色限知', '角色投影'], ['冲突', '误判/泄露检查'], ['公开信息', '读者已知']],
        rows: [
          { id: 'deduce:roles', label: '角色限知', type: 'deduce_view', ref: { view: 'roles' }, meta: '角色' },
          { id: 'deduce:conflict', label: '冲突与误判', type: 'deduce_view', ref: { view: 'conflict' }, meta: '2' },
          { id: 'deduce:public', label: '可公开信息', type: 'deduce_view', ref: { view: 'public' }, meta: '6' },
        ],
      },
    ],
  },
  promise: {
    title: '伏笔',
    badge: '台账',
    current: () => '本章要收',
    subtitle: '埋设 / 回收 / 超期',
    inputPlaceholder: '过滤伏笔',
    primaryAction: '刷新',
    chips: ['本章', '全书', '超期', '仍悬'],
    groups: [
      {
        id: 'chapter',
        label: '本章关联',
        meta: '埋设/回收',
        tone: 'brand',
        meaning: '汇总本章应该新埋或回收的叙事承诺。',
        constraint: '先确认本章承担哪类承诺,再进入具体伏笔台账核对状态。',
        scope: '第 {seq} 章伏笔闭环',
        actions: ['查看本章伏笔', '校验回收窗口', '问主编安排'],
        related: [['本章要收', 'payoff'], ['本章新埋', 'setup']],
        rows: [
          { id: 'promise:payoff', label: '本章要收', type: 'promise_view', ref: 'payoff', meta: '3' },
          { id: 'promise:setup', label: '本章新埋', type: 'promise_view', ref: 'setup', meta: '2' },
        ],
      },
      {
        id: 'risk',
        label: '风险状态',
        meta: '超期/仍悬',
        tone: 'warn',
        meaning: '按风险状态扫描仍未闭环的伏笔。',
        constraint: '超期和仍悬要优先处理,避免正文继续推进时承诺失焦。',
        scope: '全书伏笔风险',
        actions: ['查看风险伏笔', '标记处理策略', '问主编排序'],
        related: [['超期未收', 'overdue'], ['仍悬', 'open'], ['已回收', 'done']],
        rows: [
          { id: 'promise:overdue', label: '超期未收', type: 'promise_view', ref: 'overdue', meta: '4' },
          { id: 'promise:open', label: '仍悬', type: 'promise_view', ref: 'open', meta: '7' },
          { id: 'promise:done', label: '已回收', type: 'promise_view', ref: 'done', meta: '19' },
        ],
      },
    ],
  },
  motif: {
    title: '母题',
    badge: '证据',
    current: () => '本章触及',
    subtitle: '出现章节 / 证据片段',
    inputPlaceholder: '过滤母题',
    primaryAction: '刷新',
    chips: ['本章触及', '本卷', '全书', '证据不足'],
    groups: [
      {
        id: 'evidence',
        label: '章级证据',
        meta: '本章/本卷',
        tone: 'brand',
        meaning: '查看本章或本卷母题是否有真实文本证据支撑。',
        constraint: '母题不能只停留在标签,必须能回到正文证据或章级台账。',
        scope: '第 {seq} 章母题证据',
        actions: ['查看命中正文', '校验证据密度', '问主编强化'],
        related: [['本章触及', 'chapter'], ['本卷主母题', 'volume']],
        rows: [
          { id: 'motif:chapter', label: '本章触及', type: 'motif_view', ref: 'chapter', meta: '4' },
          { id: 'motif:volume', label: '本卷主母题', type: 'motif_view', ref: 'volume', meta: '3' },
        ],
      },
      {
        id: 'book',
        label: '全书结构',
        meta: '全书/异常',
        tone: 'warn',
        meaning: '从全书层面检查母题是否过薄、过度重复或偏离北极星。',
        constraint: '全书母题应服务主题推进,不应变成重复意象堆叠。',
        scope: '全书母题结构',
        actions: ['查看全书母题', '检查重复风险', '问主编收敛'],
        related: [['全书母题', 'book'], ['证据不足', 'thin'], ['过度重复', 'repeat']],
        rows: [
          { id: 'motif:book', label: '全书母题', type: 'motif_view', ref: 'book', meta: '11' },
          { id: 'motif:thin', label: '证据不足', type: 'motif_view', ref: 'thin', meta: '2' },
          { id: 'motif:repeat', label: '过度重复', type: 'motif_view', ref: 'repeat', meta: '1' },
        ],
      },
    ],
  },
}

export function capabilityGroups(capability) {
  return CAPABILITY_TREE[capability]?.groups || []
}

export function capabilityGroup(capability, groupId) {
  return capabilityGroups(capability).find((group) => group.id === groupId) || null
}

export function capabilityConfig(capability) {
  return CAPABILITY_TREE[capability] || null
}

export function formatScope(text, seq) {
  return String(text || '').replace('第 {seq} 章', seq != null ? `第 ${seq} 章` : '当前章')
    .replace('{seq}', seq ?? '当前')
}

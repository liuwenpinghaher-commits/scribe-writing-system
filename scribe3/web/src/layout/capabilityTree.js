// 能力上下文树 —— 只承载「结构性文案」:能力标题、分组的 id/label/meta 描述/含义/
// 约束/范围模板,以及分组下的固定视图入口(rows:每行都路由到真实详情面板,
// 是导航结构,不是业务数据行)。
//
// Task 10 铁律:业务数量、related 关联数据、动作按钮一律来自 API 的 live payload;
// 配置里绝不写 demo 数字(旧版曾写死 超期4/仍悬7/已回收19 等假计数)或无 handler 的
// 假动作。消费方(CapabilityDirectories/CapabilityDetailPanes)在值不存在时直接
// 不渲染数量与按钮,而不是渲染 0 或占位数字。
// (顶层 badge/current/subtitle/chips/inputPlaceholder/primaryAction 为 T4 审查
//  确认的零消费死字段,已删。)
export const CAPABILITY_TREE = {
  deduce: {
    title: '演绎',
    groups: [
      {
        id: 'truth',
        label: '场景基础',
        meta: '全知',
        tone: 'brand',
        meaning: '先整理本章客观真相,作为所有角色限知投影的共同来源。',
        constraint: '场景真相可以含隐藏机制,但不能直接等同于正文里某个角色知道的内容。',
        scope: '第 {seq} 章演绎底座',
        rows: [
          { id: 'deduce:truth', label: '场景真相', type: 'deduce_view', ref: { view: 'truth' } },
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
        rows: [
          { id: 'deduce:roles', label: '角色限知', type: 'deduce_view', ref: { view: 'roles' } },
          { id: 'deduce:conflict', label: '冲突与误判', type: 'deduce_view', ref: { view: 'conflict' } },
          { id: 'deduce:public', label: '可公开信息', type: 'deduce_view', ref: { view: 'public' } },
        ],
      },
    ],
  },
  promise: {
    title: '伏笔',
    groups: [
      {
        id: 'chapter',
        label: '本章关联',
        meta: '埋设/回收',
        tone: 'brand',
        meaning: '汇总本章应该新埋或回收的叙事承诺。',
        constraint: '先确认本章承担哪类承诺,再进入具体伏笔台账核对状态。',
        scope: '第 {seq} 章伏笔闭环',
        rows: [
          { id: 'promise:payoff', label: '本章要收', type: 'promise_view', ref: 'payoff' },
          { id: 'promise:setup', label: '本章新埋', type: 'promise_view', ref: 'setup' },
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
        rows: [
          { id: 'promise:overdue', label: '超期未收', type: 'promise_view', ref: 'overdue' },
          { id: 'promise:open', label: '仍悬', type: 'promise_view', ref: 'open' },
          { id: 'promise:done', label: '已回收', type: 'promise_view', ref: 'done' },
        ],
      },
    ],
  },
  motif: {
    title: '母题',
    groups: [
      {
        id: 'evidence',
        label: '章级证据',
        meta: '本章/本卷',
        tone: 'brand',
        meaning: '查看本章或本卷母题是否有真实文本证据支撑。',
        constraint: '母题不能只停留在标签,必须能回到正文证据或章级台账。',
        scope: '第 {seq} 章母题证据',
        rows: [
          { id: 'motif:chapter', label: '本章触及', type: 'motif_view', ref: 'chapter' },
          { id: 'motif:volume', label: '本卷主母题', type: 'motif_view', ref: 'volume' },
        ],
      },
      {
        id: 'book',
        label: '全书结构',
        meta: '全书/异常',
        tone: 'warn',
        meaning: '从全书层面检查母题是否过薄、过度重复或偏离作品意图。',
        constraint: '全书母题应服务主题推进,不应变成重复意象堆叠。',
        scope: '全书母题结构',
        rows: [
          { id: 'motif:book', label: '全书母题', type: 'motif_view', ref: 'book' },
          { id: 'motif:thin', label: '证据不足', type: 'motif_view', ref: 'thin' },
          { id: 'motif:repeat', label: '过度重复', type: 'motif_view', ref: 'repeat' },
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

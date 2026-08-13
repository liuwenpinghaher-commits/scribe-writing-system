/** System Hub planes + living-map default (KD-M2). */
export const PLANES = [
  {
    id: 'writing',
    label: '写作系统',
    sections: [
      { id: 'map', label: '总览地图', needsWork: false },
      { id: 'book', label: '本书与目标', needsWork: true },
      { id: 'prefs', label: '个人偏好', needsWork: false },
      { id: 'tasks', label: '任务旋钮', needsWork: false },
      { id: 'skills', label: '技法与招式', needsWork: false },
      { id: 'mcp', label: '能力注册表', needsWork: false },
      { id: 'craft', label: '工艺与记忆', needsWork: false },
      { id: 'health', label: '写路径健康', needsWork: false },
      { id: 'evolution', label: '经验与自进化', needsWork: true },
    ],
  },
  {
    id: 'runtime',
    label: '运行时 · 数据',
    sections: [
      { id: 'hermes', label: 'Hermes 运行时', needsWork: false },
      { id: 'models', label: '模型与服务', needsWork: false },
      { id: 'surreal', label: 'Surreal 数据面', needsWork: true },
    ],
  },
  {
    id: 'ops',
    label: '运维 · 危险',
    adminOnly: true,
    sections: [
      { id: 'connection', label: '连接与密钥', needsWork: false },
      { id: 'flags', label: '灰度与紧急开关', needsWork: false },
      { id: 'accounts', label: '账号与书籍', needsWork: false },
      { id: 'run-logs', label: '运行链路', needsWork: false },
      { id: 'audit', label: '变更审计', needsWork: false },
    ],
  },
]

export const CRAFT_COMMON_KEYS = new Set([
  'craft.banned_density_per_k',
  'craft.near_dup_sim',
  'craft.adverb_per_k_max',
  'memory.weight_structured',
  'memory.weight_vector',
  'memory.half_life_episodic',
])

export const IMPACT_HINTS = {
  'craft.banned_density_per_k': '提高则更少禁词告警；降低更严',
  'craft.near_dup_sim': '相似度越高越容易判重复',
  'craft.adverb_per_k_max': '副词密度上限',
  'memory.weight_structured': '正典直查权重',
  'memory.weight_vector': '向量检索权重',
  'memory.weight_bm25': 'BM25 权重',
  'memory.half_life_working': '工作记忆半衰期',
  'memory.half_life_episodic': '情节记忆半衰期',
  'memory.half_life_procedural': '程序记忆半衰期',
  'memory.half_life_reference': '参考记忆半衰期',
  'memory.half_life_uncertainty': '不确定记忆半衰期',
  'llm.model': '影响补全与讨论所用模型',
  'llm.timeout_seconds': '请求超时（秒）',
  'llm.max_retries': '瞬时错误重试次数',
  'SCRIBE3_DAILY_CALL_CAP': '日调用上限（管理员）',
  'HERMES_API': '速答网关地址（管理员）',
}

export const GATE_LABEL = {
  world_write_gated: '世界写·须审批',
  manuscript_save: '存稿通道',
  ingest: '入库分析',
  read: '只读/召回',
  ungated_write: '未分类写',
}

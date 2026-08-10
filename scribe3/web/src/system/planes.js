/** System Hub 三平面 IA（设计 KD-2） */
export const PLANES = [
  {
    id: 'writing',
    label: '写作系统',
    sections: [
      { id: 'book', label: '本书与目标', needsWork: true },
      { id: 'prefs', label: '个人偏好', needsWork: false },
      { id: 'skills', label: '技能与技法', needsWork: false },
      { id: 'mcp', label: '能力地图（MCP）', needsWork: false },
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
  'llm.model': '影响补全与讨论所用模型',
  'SCRIBE3_DAILY_CALL_CAP': '日调用上限（管理员）',
  'HERMES_API': '速答网关地址（管理员·重启生效）',
}

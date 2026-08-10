/** Living-map graph: clicks stay in System Hub config, never jump to app. */
export const NODES = [
  { id: 'studio', label: '写作台', x: 40, y: 80, configSection: 'book', configPlane: 'writing' },
  { id: 'chief', label: '主编', x: 200, y: 80, configSection: 'hermes', configPlane: 'runtime' },
  { id: 'assemble', label: '写路径组装', x: 360, y: 80, configSection: 'craft', configPlane: 'writing' },
  { id: 'story', label: '故事库', x: 360, y: 200, configSection: 'surreal', configPlane: 'runtime' },
  { id: 'registry', label: '能力注册表', x: 200, y: 200, configSection: 'mcp', configPlane: 'writing' },
  { id: 'policy', label: '策略配置', x: 40, y: 200, configSection: 'tasks', configPlane: 'writing' },
]

export const EDGES = [
  ['studio', 'chief'],
  ['chief', 'assemble'],
  ['assemble', 'story'],
  ['chief', 'registry'],
  ['policy', 'assemble'],
  ['registry', 'chief'],
]

/** Sequence chips: stay in hub; map to config sections only. */
export const SEQ_STEPS = [
  { id: 'pick', label: '选章说明', action: 'section', section: 'book', plane: 'writing' },
  { id: 'outline', label: '大纲/契约', action: 'section', section: 'book', plane: 'writing' },
  { id: 'assemble', label: '组装阈值', action: 'section', section: 'craft', plane: 'writing' },
  { id: 'approve', label: '审批写', action: 'section', section: 'mcp', plane: 'writing', filter: 'world_write_gated' },
  { id: 'save', label: '存稿说明', action: 'section', section: 'mcp', plane: 'writing', filter: 'manuscript_save' },
  { id: 'ingest', label: '入库说明', action: 'section', section: 'mcp', plane: 'writing', filter: 'ingest' },
  { id: 'observe', label: '观测/健康', action: 'section', section: 'health', plane: 'writing' },
]

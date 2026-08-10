/** Living-map graph single source (KD-M4). */
export const NODES = [
  { id: 'studio', label: '写作台', x: 40, y: 80, section: null, exit: true },
  { id: 'chief', label: '主编', x: 200, y: 80, section: null, exit: true },
  { id: 'assemble', label: '写路径组装', x: 360, y: 80, section: 'craft' },
  { id: 'story', label: '故事库', x: 360, y: 200, section: 'surreal' },
  { id: 'registry', label: '能力注册表', x: 200, y: 200, section: 'mcp' },
  { id: 'policy', label: '策略配置', x: 40, y: 200, section: 'craft' },
]

export const EDGES = [
  ['studio', 'chief'],
  ['chief', 'assemble'],
  ['assemble', 'story'],
  ['chief', 'registry'],
  ['policy', 'assemble'],
  ['registry', 'chief'],
]

export const SEQ_STEPS = [
  { id: 'pick', label: '选章', action: 'exit' },
  { id: 'outline', label: '大纲/节拍', action: 'exit' },
  { id: 'assemble', label: '组装', action: 'section', section: 'craft' },
  { id: 'approve', label: '审批写', action: 'section', section: 'mcp', filter: 'world_write_gated' },
  { id: 'save', label: '存稿', action: 'module', module: 'studio' },
  { id: 'ingest', label: '入库', action: 'module', module: 'assemble' },
  { id: 'observe', label: '观测', action: 'section', section: 'health' },
]

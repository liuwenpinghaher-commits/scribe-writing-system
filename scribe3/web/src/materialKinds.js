// 素材分类(独立文件:破 Materials ↔ MaterialImport 的循环 import,防 MATERIAL_KINDS TDZ 崩)。
// 与后端 store.py MATERIAL_KINDS 同步(6 类,含 emotion_module,修前后端割裂)。
export const MATERIAL_KINDS = [
  { key: 'research', label: '研究' },
  { key: 'reference', label: '参考' },
  { key: 'snippet', label: '片段' },
  { key: 'inspiration', label: '灵感' },
  { key: 'note', label: '笔记' },
  { key: 'emotion_module', label: '情绪卡' },
]

export const KIND_LABEL = Object.fromEntries(MATERIAL_KINDS.map((k) => [k.key, k.label]))

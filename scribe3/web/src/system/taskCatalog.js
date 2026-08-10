/** Task knobs — exact REGISTRY keys only (KD-M8). */
export const TASKS = [
  {
    id: 'write_stable',
    label: '写得更稳（少禁词/重复）',
    keys: [
      'craft.banned_density_per_k',
      'craft.near_dup_sim',
      'craft.adverb_per_k_max',
    ],
  },
  {
    id: 'memory_canon',
    label: '检索偏正典',
    keys: [
      'memory.weight_structured',
      'memory.weight_vector',
      'memory.weight_bm25',
    ],
  },
  {
    id: 'memory_half_life',
    label: '记忆半衰期',
    keys: [
      'memory.half_life_working',
      'memory.half_life_episodic',
      'memory.half_life_procedural',
      'memory.half_life_reference',
      'memory.half_life_uncertainty',
    ],
  },
  {
    id: 'model',
    label: '模型与超时',
    keys: ['llm.model', 'llm.timeout_seconds', 'llm.max_retries'],
  },
]

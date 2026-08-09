function targetObject(raw) {
  if (!raw) return null
  if (typeof raw === 'string') return { id: raw }
  if ((raw.type || raw.id) && typeof raw === 'object') return raw
  if (raw.target_node && typeof raw.target_node === 'object') return raw.target_node
  return raw
}

function refFromChapter(target) {
  if (target.ref != null) return Number(target.ref)
  if (target.chapter != null) return Number(target.chapter)
  const m = String(target.id || '').match(/^ch:(\d+)$/)
  return m ? Number(m[1]) : null
}

function localRoleId(id) {
  return String(id || '').replace(/^role:/, '').replace(/^character:/, '')
}

function normalizedId(prefix, id) {
  const s = String(id || '')
  if (!s) return prefix
  return s.startsWith(`${prefix}:`) ? s : `${prefix}:${s.replace(/^[^:]+:/, '')}`
}

function chapterNode(target) {
  const seq = refFromChapter(target)
  if (seq == null || Number.isNaN(seq)) return null
  return {
    id: `ch:${seq}`,
    type: 'chapter',
    ref: seq,
    label: target.label || target.title || `第 ${seq} 章`,
    phase: target.phase || 'outline',
  }
}

function issueNode(target) {
  const ch = target.chapter ?? target.ref ?? target.target_node?.ref
  const id = target.id || (ch != null ? `issue:weak:${ch}` : 'review:summary')
  const issue = {
    id,
    source: target.source || 'dashboard',
    severity: target.severity || 'warning',
    title: target.title || target.label || (ch != null ? `第 ${ch} 章诊断` : '校验命中'),
    reason: target.reason || target.excerpt || '从横切视图定位到的校验项。',
    chapter: ch,
    range: Array.isArray(target.range) ? target.range : [0, 0],
    status: target.status || 'open',
    suggested_action: target.suggested_action,
    target_node: target.target_node || (ch != null ? { id: `ch:${ch}`, type: 'chapter', ref: Number(ch), label: `第 ${ch} 章` } : null),
  }
  return {
    id,
    type: 'review_issue',
    label: issue.title,
    payload: issue,
    target_node: issue.target_node,
  }
}

function codexNode(target) {
  const rawId = target.id || target.ref || target.label || ''
  const type = target.type
  const panel = target.panel || target.meta?.panel
  const withPanel = (node) => (panel ? { ...node, panel, meta: { ...(node.meta || {}), panel } } : node)
  if (type === 'character' || type === 'role' || String(rawId).startsWith('role:')) {
    const local = localRoleId(rawId)
    return withPanel({ id: `character:${local}`, type: 'character', ref: local, label: target.label || local })
  }
  if (type === 'faction' || String(rawId).startsWith('faction:')) {
    const local = String(rawId).replace(/^faction:/, '')
    return withPanel({ id: `faction:${local}`, type: 'faction', ref: local, label: target.label || local })
  }
  if (type === 'item' || String(rawId).startsWith('item:')) {
    const local = String(rawId).replace(/^item:/, '')
    return withPanel({ id: `item:${local}`, type: 'item', ref: local, label: target.label || local })
  }
  if (type === 'proposition' || type === 'fact' || type === 'frame_fact' || String(rawId).startsWith('fact:')) {
    const local = String(rawId).replace(/^(fact|proposition):/, '')
    return withPanel({ id: `proposition:${local}`, type: 'proposition', ref: local, label: target.label || local })
  }
  if (type === 'relation' || type === 'character_relation') {
    return { id: 'cat:character_relation', type: 'codex_category', ref: 'character_relation', label: '角色关系' }
  }
  return withPanel({
    id: normalizedId(type || 'codex', rawId),
    type: type || 'codex_category',
    ref: target.ref ?? rawId,
    label: target.label || String(rawId || '设定项'),
  })
}

export function targetNodeToSelection(raw) {
  const target = targetObject(raw)
  if (!target) return null
  const id = String(target.id || '')
  const type = target.type || ''

  if (type === 'weak_chapter' || type === 'issue' || type === 'review_issue' || id.startsWith('issue:')) {
    return { entry: 'review', node: type === 'review_issue' ? target : issueNode(target) }
  }

  if (type === 'chapter' || type === 'scene' || type === 'event' || id.startsWith('ch:')) {
    const node = type === 'chapter' && target.ref != null ? target : chapterNode(target)
    return node ? { entry: 'manuscript', node } : null
  }

  if (type === 'material' || id.startsWith('material:')) {
    return {
      entry: 'materials',
      node: {
        id: id || `material:${target.ref}`,
        type: 'material',
        ref: target.ref ?? id.replace(/^material:/, ''),
        label: target.label || target.title || String(target.ref ?? id),
        meta: target.meta,
      },
    }
  }

  if (type === 'promise' || type === 'promise_view' || id.startsWith('promise:')) {
    return {
      entry: 'promise',
      node: {
        id: id || `promise:${target.ref || target.label || 'open'}`,
        type: 'promise_view',
        ref: target.ref || 'open',
        label: target.label || target.title || '伏笔详情',
        payload: target,
        meta: { seq: target.chapter ?? target.seq },
      },
    }
  }

  if (type === 'motif' || type === 'motif_view' || id.startsWith('motif:')) {
    // 能力分组(本章触及/全书/证据不足…)或显式 motif_view → MotifDetailPane
    // type=motif 具体叶(设定库/搜索/左栏) → CodexDetail 可编辑
    const VIEW = new Set(['chapter', 'thin', 'volume', 'book', 'repeat'])
    let ref = target.ref
    if (ref == null && id.startsWith('motif:')) {
      ref = id.slice('motif:'.length)
    }
    const refIsGroup = VIEW.has(String(ref ?? ''))
    if (type === 'motif_view' || refIsGroup) {
      // motif_view 可带分组键或具体 id;无 ref 时默认全书
      const viewRef = refIsGroup ? ref : (ref != null && ref !== '' ? ref : 'book')
      return {
        entry: 'motif',
        node: {
          id: id || `motif:${viewRef}`,
          type: 'motif_view',
          ref: viewRef,
          label: target.label || target.title || '母题详情',
          payload: target,
          meta: { seq: target.chapter ?? target.seq },
        },
      }
    }
    const local = String(ref ?? '').replace(/^motif:/, '')
    return {
      entry: 'codex',
      node: {
        id: `motif:${local}`,
        type: 'motif',
        ref: local,
        label: target.label || target.title || local,
        meta: { seq: target.chapter ?? target.seq },
      },
    }
  }

  if (['character', 'role', 'fact', 'frame_fact', 'proposition', 'relation', 'character_relation', 'faction', 'item', 'term', 'world_rule'].includes(type)
      || id.startsWith('role:') || id.startsWith('fact:') || id.startsWith('proposition:')) {
    return { entry: 'codex', node: codexNode(target) }
  }

  // 横切视图(图谱等):从设定详情「在图谱中打开」等入口进入
  if (type === 'view' || type === 'atlas' || id.startsWith('view:')) {
    const viewKey = target.viewKey
      || (type === 'atlas' ? 'atlas' : '')
      || id.replace(/^view:/, '')
      || 'atlas'
    const atlasFocus = target.focus || target.meta?.focus || null
    return {
      viewKey,
      atlasFocus,
      node: { type: 'view', id: `view:${viewKey}`, viewKey },
    }
  }

  return null
}

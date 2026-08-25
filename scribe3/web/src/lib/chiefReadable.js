/**
 * 主编可读面：发送种类、空态、待批、种子来源。
 * 不碰分流。主编只回答「现在在谈什么、会不会改库」。
 */
import { shouldUseHermesRun } from './hermesRunIntent.js'

export function chiefSendKind(text) {
  const value = String(text || '').trim()
  if (!value) return 'empty'
  if (value.startsWith('#想法')) return 'idea'
  if (shouldUseHermesRun(value)) return 'write'
  return 'discuss'
}

export function chiefSendHint(kind) {
  if (kind === 'write') return '这句会改库，要你批'
  if (kind === 'discuss') return '这句只讨论'
  if (kind === 'idea') return '这句进想法收件箱'
  return ''
}

/** kind: no_work | no_thread | awaiting | continued | fresh | empty_ask | null */
export function chiefEmptyKind({ work, msgs, pending, threadMode, threadId, threadMeta } = {}) {
  if (!work) return 'no_work'
  if (threadMode && !threadId) return 'no_thread'
  if (Array.isArray(msgs) && msgs.length > 0) return null
  if (pending) return 'awaiting'
  if (threadMode && threadMeta?.parent_thread_id) return 'continued'
  if (threadMode && threadMeta && !threadMeta.parent_thread_id) return 'fresh'
  return 'empty_ask'
}

export function chiefEmptyCopy(kind) {
  if (kind === 'no_work') {
    return { title: '还没选书', body: '先打开一本书，再跟主编说话。' }
  }
  if (kind === 'no_thread') {
    return { title: '还没线程', body: '点会话下拉开一条，或直接在下面问。' }
  }
  if (kind === 'awaiting') {
    return { title: '在等你批', body: '改库提案还没点。滚到那张卡批准或拒绝。' }
  }
  if (kind === 'continued') {
    return { title: '延续上一会话', body: '近窗和摘要还在。这只是界面分组，不是失忆。' }
  }
  if (kind === 'fresh') {
    return { title: '空会话可以问', body: '不带对话历史。设定和伏笔还在。' }
  }
  return { title: '空会话可以问', body: '就当前打开的这本书问。主编会自己翻书。' }
}

export function pendingApprovalOf(msgs) {
  const list = Array.isArray(msgs) ? msgs : []
  for (let i = list.length - 1; i >= 0; i -= 1) {
    const row = list[i]
    if (row?.role !== 'assistant') continue
    for (const ap of row.approvals || []) {
      const st = ap?.status
      if (!st || st === 'pending' || st === 'submitting') return ap
    }
  }
  return null
}

export function seedOrigin(text) {
  const value = String(text || '')
  if (value.includes('【时间线】')) return 'timeline'
  if (value.includes('【仪表盘】')) return 'insight'
  if (value.includes('【图谱')) return 'atlas'
  return null
}

export function seedOriginLabel(origin) {
  if (origin === 'timeline') return '来自时间线'
  if (origin === 'insight') return '来自仪表盘'
  if (origin === 'atlas') return '来自图谱'
  return ''
}

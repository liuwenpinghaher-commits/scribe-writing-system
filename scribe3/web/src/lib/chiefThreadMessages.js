// 主编线程历史与当前 UI 回合的合并规则。
// 历史请求是一个时间点快照，不能在响应较晚到达时覆盖该时间点之后新发出的本地回合。

export function normalizeThreadMessages(rows) {
  return (rows || []).map((message) => ({
    id: message.id ?? null,
    role: message.role,
    content: message.text ?? message.content ?? '',
    tools: message.tools || [],
    toolOutputs: message.toolOutputs || [],
    approvals: message.approvals || [],
    focus: message.focus || null,
    context_revision: message.context_revision ?? null,
    ts: message.ts ?? null,
  }))
}

function messageKey(message) {
  if (message?.id) return `id:${message.id}`
  return [
    message?.role || '',
    message?.content || '',
    message?.context_revision ?? '',
    JSON.stringify(message?.focus || null),
  ].join('|')
}

// 保留请求发出后产生的本地消息；同一条已由历史返回的消息只显示一次。
export function mergeThreadHistory(history, current) {
  const normalizedHistory = history || []
  const historyKeys = new Set(normalizedHistory.map(messageKey))
  const pending = (current || []).filter((message) => !historyKeys.has(messageKey(message)))
  return [...normalizedHistory, ...pending]
}

// Run/SSE 可在历史快照之后到达。若快照中尚没有本轮 assistant 气泡，创建一个，
// 而不是把事件写到 undefined 或错误地覆盖作者消息。
export function mutateLatestAssistantMessage(messages, mutate) {
  const next = [...(messages || [])]
  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index]?.role === 'assistant') {
      next[index] = mutate(next[index])
      return next
    }
  }
  const assistant = { role: 'assistant', content: '', tools: [] }
  next.push(mutate(assistant))
  return next
}

// 真实浏览器 ai/runs 创建响应的最小身份捕获：只读取 run_id 和 URL 的 work，
// 不读取输入、指令、SSE 文本或任何业务正文。
export function attachRunIdentityCapture(page, onIdentity) {
  const handler = async (response) => {
    if (response.status() < 200 || response.status() >= 300) return
    const request = response.request()
    if (request.method() !== 'POST') return
    let url
    try {
      url = new URL(response.url())
      if (!/^\/api\/ai\/runs\/?$/.test(url.pathname) && url.pathname !== '/ai/runs') return
    } catch {
      return
    }
    try {
      const payload = await response.json()
      const id = payload?.run_id || payload?.id
      if (typeof id !== 'string' || !id) return
      const work = url.searchParams.get('work') || ''
      onIdentity({ id, work })
    } catch {
      // 创建响应不可读时，原有请求级回退仍会尝试；不能让观测失败影响作者操作。
    }
  }
  page.on('response', handler)
  return () => page.off?.('response', handler)
}

// 只接受浏览器实际收到的 GET /ai/runs/{id} completed 响应。completed_unverified、
// remote_completed_pending_audit 及任何失败态都不能作为 SSE 主动收束的豁免证据。
export function attachCompletedRunCapture(page, onCompleted) {
  const handler = async (response) => {
    if (response.status() < 200 || response.status() >= 300) return
    const request = response.request()
    if (request.method() !== 'GET') return
    let url
    try {
      url = new URL(response.url())
    } catch {
      return
    }
    const match = /^\/(?:api\/)?ai\/runs\/([^/]+)$/.exec(url.pathname)
    if (!match) return
    try {
      const payload = await response.json()
      const id = payload?.run_id || payload?.id || decodeURIComponent(match[1])
      if (payload?.status === 'completed' && typeof id === 'string' && id) {
        onCompleted({ id, work: url.searchParams.get('work') || '' })
      }
    } catch {
      // 观测失败不影响真人操作；没有明确 completed 证据时，SSE 失败保持未豁免。
    }
  }
  page.on('response', handler)
  return () => page.off?.('response', handler)
}

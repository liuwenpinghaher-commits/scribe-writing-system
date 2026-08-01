// 真人浏览器验收的最小网络故障证据。仅保留 HTTP 元数据，严禁读取响应体、查询参数、
// prompt、正文或任何凭证；用于把浏览器 console 的笼统 404 还原为可修复的路径。
export function attachBrowserErrorTrace(page) {
  const trace = []
  // 保持原数组返回契约；请求失败使用具名附属字段，避免与 HTTP 404 混淆。
  Object.defineProperty(trace, 'failed_requests', {
    value: [],
    enumerable: false,
  })
  const onResponse = (response) => {
    if (response.status() !== 404) return
    let path
    try {
      path = new URL(response.url()).pathname
    } catch {
      path = '[invalid-url]'
    }
    const request = response.request()
    trace.push({
      method: request.method(),
      path,
      resource_type: request.resourceType(),
      status: 404,
    })
  }
  const onRequestFailed = (request) => {
    let path
    try {
      path = new URL(request.url()).pathname
    } catch {
      path = '[invalid-url]'
    }
    trace.failed_requests.push({
      method: request.method(),
      path,
      resource_type: request.resourceType(),
      error: request.failure()?.errorText || 'unknown',
    })
  }
  page.on('response', onResponse)
  page.on('requestfailed', onRequestFailed)
  Object.defineProperty(trace, 'detach', {
    value: () => {
      page.off?.('response', onResponse)
      page.off?.('requestfailed', onRequestFailed)
    },
    enumerable: false,
  })
  return trace
}

// EventSource 在前端已经观察到同一 Run 的 completed 终态后由客户端主动 close，
// Chromium 会将该主动收束报告为 ERR_ABORTED。它不是服务端或网络失败；但只有同时
// 满足精确路径、精确错误码、且 Run 已被实际浏览器状态响应证实为 completed 时才可归类。
// 其余请求失败一律保留为 unexpected，禁止按资源类型或错误码宽泛豁免。
export function partitionVerifiedTerminalSseAborts(failures, verifiedCompletedRunIds) {
  const controlled_closures = []
  const unexpected_failures = []
  for (const failure of failures || []) {
    const matched = typeof failure?.path === 'string'
      && /^\/api\/ai\/runs\/([^/]+)\/events$/.exec(failure.path)
    const runId = matched ? decodeURIComponent(matched[1]) : ''
    if (failure?.method === 'GET'
      && failure?.resource_type === 'eventsource'
      && failure?.error === 'net::ERR_ABORTED'
      && runId
      && verifiedCompletedRunIds?.has(runId)) {
      controlled_closures.push({
        ...failure,
        run_id: runId,
        reason: 'client_closed_after_verified_completed_run',
      })
    } else {
      unexpected_failures.push(failure)
    }
  }
  return { controlled_closures, unexpected_failures }
}

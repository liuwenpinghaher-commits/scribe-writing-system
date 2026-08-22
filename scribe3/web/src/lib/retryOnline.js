/** SYS-09：网关重启后轮询探活，避免启动中被当成离线。 */
export async function retryUntilOnline(probe, { tries = 3, waitMs = 2000 } = {}) {
  let last = null
  const n = Math.max(1, Number(tries) || 3)
  for (let i = 0; i < n; i++) {
    try {
      last = await probe()
    } catch (e) {
      last = { online: false, error: e }
    }
    if (last && last.online) return last
    if (i < n - 1 && waitMs > 0) {
      await new Promise((r) => setTimeout(r, waitMs))
    }
  }
  return last
}

// 工艺优先门闩:调后端 GET /craft-gates(与 verify_craft_compliance 同源)
// 供 fused / hq / craft_first 旅程在 exit 前强制校验。
// 字数/form_fill 不得单独构成 PASS。

const API = process.env.E2E_API || 'http://127.0.0.1:3321'

/**
 * @param {{ work: string, seq?: number }} opts
 * @returns {Promise<{ ok: boolean, body: any, status: number }>}
 */
export async function fetchCraftGates({ work, seq } = {}) {
  const w = work || process.env.E2E_WORK || 'main'
  const qs = new URLSearchParams({ work: w })
  if (seq != null) qs.set('seq', String(seq))
  const res = await fetch(`${API}/craft-gates?${qs}`)
  let body = null
  try { body = await res.json() } catch { body = { raw: await res.text() } }
  return { ok: !!body?.ok && res.ok, body, status: res.status }
}

/**
 * 旅程结束门控。失败 process.exit(code)。
 * @param {{ work: string, seqs?: number[], requireA?: boolean, label?: string }} opts
 */
export async function assertCraftGatesOrExit(opts = {}) {
  const work = opts.work || process.env.E2E_WORK || 'main'
  const requireA = opts.requireA !== false
  const label = opts.label || 'CRAFT_GATE'
  const seqs = opts.seqs || []

  const a = await fetchCraftGates({ work })
  console.log(`${label} GATE-A ok=${a.body?.gate_a?.ok} status=${a.status}`)
  if (requireA && !a.body?.gate_a?.ok) {
    console.error(`${label} FAIL: GATE-A`, JSON.stringify(a.body?.gate_a?.blocking || a.body?.gate_a, null, 2))
    process.exit(10)
  }

  for (const seq of seqs) {
    const g = await fetchCraftGates({ work, seq })
    console.log(`${label} ch${seq} ok=${g.ok} B=${g.body?.gate_b?.ok} C=${g.body?.gate_c_det?.ok}`)
    if (!g.ok) {
      console.error(`${label} FAIL: chapter ${seq}`, JSON.stringify({
        blocking_b: g.body?.gate_b?.blocking,
        blocking_c: g.body?.gate_c_det?.blocking,
        rc: g.body?.gate_b?.rc_hints || g.body?.gate_c_det?.rc_hints,
      }, null, 2))
      process.exit(11)
    }
  }

  return { gate_a: a.body?.gate_a, chapters: seqs }
}

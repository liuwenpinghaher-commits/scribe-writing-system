// ── e2e · 块一-B 快照恢复:回写 .snapshots/b1b_ch4_*.json 并逐字段复核 ──────
// 运行:cd scribe3/web && node e2e/qa_b1b_restore.mjs(需后端 :3321;快照须先由 snapshot_ch4.mjs b1b 生成)
// 恢复《纸命》第4章快照(synopsis/beats/scene_truth/deductions + latest draft)并复核一致
import fs from 'node:fs'

const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const SEQ = 4
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const SP = path.join(path.dirname(fileURLToPath(import.meta.url)), '.snapshots')

const snap = JSON.parse(fs.readFileSync(`${SP}/b1b_ch4_snapshot.json`, 'utf8'))
const dsnap = JSON.parse(fs.readFileSync(`${SP}/b1b_ch4_draft_snapshot.json`, 'utf8'))

const run = async () => {
  const body = {
    synopsis: snap.synopsis || '',
    beats: snap.beats || [],
    scene_truth: snap.scene_truth || '',
    deductions: snap.deductions || [],
  }
  let r = await fetch(`${API}/chapters/${SEQ}?work=${WORK}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  console.log('PATCH chapters:', r.status)
  r = await fetch(`${API}/save-draft?seq=${SEQ}&work=${WORK}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prose: (dsnap && dsnap.prose) || '', summary: (dsnap && dsnap.summary) || '' }),
  })
  console.log('POST save-draft:', r.status)

  // 复核
  const ch = await (await fetch(`${API}/chapter?seq=${SEQ}&work=${WORK}`)).json()
  const d = await (await fetch(`${API}/latest-draft?seq=${SEQ}&work=${WORK}`)).json()
  const eq = (a, b) => JSON.stringify(a ?? '') === JSON.stringify(b ?? '')
  const checks = {
    synopsis: eq(ch.synopsis || '', snap.synopsis || ''),
    beats: eq(ch.beats || [], snap.beats || []),
    scene_truth: eq(ch.scene_truth || '', snap.scene_truth || ''),
    deductions: eq(ch.deductions || [], snap.deductions || []),
    draft_prose: eq((d && d.prose) || '', (dsnap && dsnap.prose) || ''),
    draft_summary: eq((d && d.summary) || '', (dsnap && dsnap.summary) || ''),
    prose_untouched: eq(ch.prose || '', snap.prose || ''),
  }
  console.log('==== RESTORE VERIFY ====')
  let ok = true
  for (const [k, v] of Object.entries(checks)) { console.log(v ? 'OK ' : 'DIFF', k); if (!v) ok = false }
  // 无测试标记残留
  const blob = JSON.stringify(ch) + JSON.stringify(d)
  const leftover = /大纲标记-|阶段标题-|加粗词-|节拍新增-|节拍改-|演绎A-|演绎B1-|演绎B2-|草稿标记-|QA复验/.test(blob)
  console.log(leftover ? 'DIFF leftover-markers' : 'OK  no-leftover-markers')
  if (!ok || leftover) process.exitCode = 2
}
run().catch((e) => { console.error('FATAL', e); process.exit(1) })

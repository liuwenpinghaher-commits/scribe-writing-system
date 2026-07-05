// ── e2e · 快照工具:拍《纸命》第4章(chapter 全量 + latest draft)到 .snapshots/ ──
// 运行:cd scribe3/web && node e2e/snapshot_ch4.mjs <prefix>(prefix=b1b|b2,对应各 restore 脚本读取的文件名)
// 数据纪律:任何会写数据的 e2e(qa_b1b/qa_b2)跑之前必须先拍快照,跑完用对应 *_restore.mjs 恢复。
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const SEQ = 4
const prefix = process.argv[2] || 'b2'
const SP = path.join(path.dirname(fileURLToPath(import.meta.url)), '.snapshots')
fs.mkdirSync(SP, { recursive: true })

const run = async () => {
  const ch = await (await fetch(`${API}/chapter?seq=${SEQ}&work=${WORK}`)).json()
  const d = await (await fetch(`${API}/latest-draft?seq=${SEQ}&work=${WORK}`)).json()
  fs.writeFileSync(path.join(SP, `${prefix}_ch4_snapshot.json`), JSON.stringify(ch))
  fs.writeFileSync(path.join(SP, `${prefix}_ch4_draft_snapshot.json`), JSON.stringify(d || {}))
  console.log(`snapshot ok → ${prefix}_ch4_*.json | synopsis len ${(ch.synopsis || '').length} | beats ${(ch.beats || []).length} | draft len ${((d && d.prose) || '').length}`)
}
run().catch((e) => { console.error('FATAL', e); process.exit(1) })

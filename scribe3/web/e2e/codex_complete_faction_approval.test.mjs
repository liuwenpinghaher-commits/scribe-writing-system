import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('势力验收将远端已完成且工具 written 的 pending-audit trace 视为已审计写入', async () => {
  const script = await readFile(new URL('./codex_complete_faction_approval.mjs', import.meta.url), 'utf8')

  assert.match(script, /import \{ isCompletedWrittenTrace \} from '\.\/full_author_acceptance_result\.mjs'/)
  assert.match(script, /\(value\) => isCompletedWrittenTrace\(value, 's3_add_faction'\)/)
})

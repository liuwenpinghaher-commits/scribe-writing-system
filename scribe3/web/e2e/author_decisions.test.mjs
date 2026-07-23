// Node 原生测试：断言决策选择器契约（防止 testid 漂移导致「点不到」）
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { DECISION_SELECTORS, ensureChiefVisible } from './author_decisions.mjs'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('DECISION_SELECTORS contract', () => {
  it('exports stable playwright hooks for approve/accept', () => {
    assert.equal(DECISION_SELECTORS.runApprove, '[data-testid="run-approve"]')
    assert.equal(DECISION_SELECTORS.draftAccept, '[data-testid="draft-accept"]')
    assert.equal(DECISION_SELECTORS.draftUseCandidate, '[data-testid="draft-use-candidate"]')
    assert.equal(DECISION_SELECTORS.runApproveStale, '[data-testid="run-approve-stale"]')
    assert.ok(DECISION_SELECTORS.writeComposer.includes('提思路'))
    assert.ok(DECISION_SELECTORS.chiefComposer.includes('问主编'))
    assert.ok(DECISION_SELECTORS.chiefComposer.includes('^='), 'prefix match for @-suffix placeholders')
    assert.equal(DECISION_SELECTORS.stageFill, '[data-testid="stage-fill"]')
  })

  it('ChiefSlotContext ProposalBar ships stage-fill testid wiring', () => {
    const src = readFileSync(join(root, 'src/ChiefSlotContext.jsx'), 'utf8')
    assert.match(src, /stage-fill/)
  })

  it('DraftCard.jsx ships data-testid draft-accept / draft-use-candidate', () => {
    const src = readFileSync(join(root, 'src/editor/DraftCard.jsx'), 'utf8')
    assert.match(src, /data-testid="draft-accept"/)
    assert.match(src, /data-testid="draft-use-candidate"/)
    assert.match(src, /data-testid="draft-reject"/)
  })

  it('ChiefDock and WriteChat ship data-testid run-approve', () => {
    const chief = readFileSync(join(root, 'src/ChiefDock.jsx'), 'utf8')
    const write = readFileSync(join(root, 'src/WriteChat.jsx'), 'utf8')
    assert.match(chief, /data-testid="run-approve"/)
    assert.match(write, /data-testid="run-approve"/)
  })

  it('exports ensureChiefVisible for collapsed-dock recovery', () => {
    assert.equal(typeof ensureChiefVisible, 'function')
  })

  it('ensureChiefVisible must not re-click pressed 主编 (Rail re-click = collapse)', () => {
    const src = readFileSync(join(root, 'e2e/author_decisions.mjs'), 'utf8')
    assert.match(src, /aria-pressed/)
    assert.match(src, /pressed === 'true'/)
    assert.match(src, /禁止再点已激活/)
  })
})

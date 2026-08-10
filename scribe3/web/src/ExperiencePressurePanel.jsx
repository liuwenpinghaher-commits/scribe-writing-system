import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { Btn } from './ui.jsx'
import { uiStatusLabel, LETTER_STATUS_CN } from './lib/statusLabels'

const GRID_CELLS = [
  ['goal', '目标'],
  ['conflict', '冲突'],
  ['disaster', '灾难'],
  ['reaction', '反应'],
  ['dilemma', '两难'],
  ['decision', '决定'],
]

const emptyGrid = () => Object.fromEntries(GRID_CELLS.map(([k]) => [k, '']))

/**
 * 经验复盘 UI(产品名锁定「经验复盘」· IA KD-IA-3/7):
 * 问诊信 + Scene–Sequel 六格 + 续写重读。≠ 写路径力学合同 pressure_drive。
 * 全部走 api.js 真实后端路径。
 */
export function ExperiencePressurePanel({ seq }) {
  const [letter, setLetter] = useState(null)
  const [grid, setGrid] = useState(emptyGrid)
  const [gridIssues, setGridIssues] = useState([])
  const [snap, setSnap] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState('')
  const [noteDraft, setNoteDraft] = useState({})

  const loadAll = useCallback(async () => {
    setErr('')
    try {
      const [L, G, S] = await Promise.all([
        api.revisionLetter(),
        seq != null ? api.getSceneGrid(seq) : Promise.resolve(null),
        seq != null ? api.continueSnapshot(seq) : Promise.resolve(null),
      ])
      setLetter(L)
      const g = G?.grid
      setGrid(g ? {
        goal: g.goal || '', conflict: g.conflict || '', disaster: g.disaster || '',
        reaction: g.reaction || '', dilemma: g.dilemma || '', decision: g.decision || '',
      } : emptyGrid())
      setGridIssues(Array.isArray(G?.issues) ? G.issues : [])
      setSnap(S)
    } catch (e) {
      setErr(e?.message || '加载失败')
    }
  }, [seq])

  useEffect(() => { loadAll() }, [loadAll])

  const onWaive = async (itemId, status) => {
    setBusy(`letter:${itemId}`)
    setErr('')
    try {
      const body = {
        status,
        author_note: (noteDraft[itemId] || '').trim() || (status === 'waived' ? '作者豁免' : '已读'),
      }
      const res = await api.updateLetterItem(itemId, body)
      setLetter(res.letter || res)
    } catch (e) {
      setErr(e?.message || '更新问诊项失败')
    } finally {
      setBusy('')
    }
  }

  const onSaveGrid = async () => {
    if (seq == null) return
    setBusy('grid')
    setErr('')
    try {
      const res = await api.putSceneGrid(seq, { ...grid, source: 'author' })
      setGrid({
        goal: res.grid?.goal || '', conflict: res.grid?.conflict || '',
        disaster: res.grid?.disaster || '', reaction: res.grid?.reaction || '',
        dilemma: res.grid?.dilemma || '', decision: res.grid?.decision || '',
      })
      setGridIssues(Array.isArray(res.issues) ? res.issues : [])
    } catch (e) {
      setErr(e?.message || '保存六格失败')
    } finally {
      setBusy('')
    }
  }

  const onAckReread = async () => {
    if (seq == null) return
    setBusy('ack')
    setErr('')
    try {
      await api.ackReread(seq)
      const S = await api.continueSnapshot(seq)
      setSnap(S)
    } catch (e) {
      setErr(e?.message || '确认重读失败')
    } finally {
      setBusy('')
    }
  }

  const onToggleRequire = async (enabled) => {
    setBusy('require')
    setErr('')
    try {
      await api.setRequireReread(enabled)
      if (seq != null) {
        const S = await api.continueSnapshot(seq)
        setSnap(S)
      }
    } catch (e) {
      setErr(e?.message || '切换重读要求失败')
    } finally {
      setBusy('')
    }
  }

  const items = Array.isArray(letter?.items) ? letter.items : []

  /** PR-7：从本章 beats GCD 单向填充六格（不写回 beats） */
  const onFillFromGcd = async () => {
    if (seq == null) return
    setBusy('fill-gcd')
    setErr('')
    try {
      const ch = await api.chapter(seq)
      const beats = Array.isArray(ch?.beats) ? ch.beats : []
      const next = emptyGrid()
      for (const b of beats) {
        if (!b || typeof b !== 'object') continue
        if (b.goal && !next.goal) next.goal = String(b.goal)
        if (b.conflict && !next.conflict) next.conflict = String(b.conflict)
        if ((b.turn || b.disaster) && !next.disaster) next.disaster = String(b.turn || b.disaster)
        if (b.reaction && !next.reaction) next.reaction = String(b.reaction)
        if (b.dilemma && !next.dilemma) next.dilemma = String(b.dilemma)
        if ((b.decision || b.cost) && !next.decision) next.decision = String(b.decision || b.cost)
      }
      setGrid(next)
      // 只更新本地面板；作者需点「保存六格」才 putSceneGrid——绝不 patchChapter(beats)
    } catch (e) {
      setErr(e?.message || '从节拍填充失败')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-6 text-ink" data-testid="experience-pressure-panel">
      <p className="text-meta text-faint">
        经验复盘（问诊/六格/续写）· 写路径力学合同见工艺侧 pressure_drive，二者不同源
      </p>
      {err && (
        <div className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-meta text-danger" role="alert">
          {err}
        </div>
      )}

      {/* 问诊信 */}
      <section data-testid="exp-letter-section" aria-labelledby="exp-letter-h">
        <h3 id="exp-letter-h" className="mb-2 text-f14 font-medium">
          修订问诊信{letter?.item_count != null ? ` · ${letter.item_count}` : ''}
        </h3>
        {letter?.note && <p className="mb-2 text-meta text-faint">{letter.note}</p>}
        {!items.length && <p className="text-meta text-faint">暂无问诊项(或未加载)。</p>}
        <ul className="space-y-2">
          {items.map((it) => (
            <li
              key={it.id}
              className="rounded-md border border-line/60 bg-soft/40 px-3 py-2"
              data-testid={`exp-letter-item-${it.id}`}
            >
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-meta uppercase tracking-wide text-faint">{uiStatusLabel(it.kind)}</span>
                <span className="text-meta text-faint">· {uiStatusLabel(it.status || 'open', LETTER_STATUS_CN)}</span>
              </div>
              <div className="mt-1 text-f13 leading-snug">{it.question || it.summary || it.title || it.text || it.id}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  className="h-7 min-w-[8rem] flex-1 rounded border border-line bg-canvas px-2 text-meta"
                  placeholder="作者备注"
                  value={noteDraft[it.id] || ''}
                  onChange={(e) => setNoteDraft((d) => ({ ...d, [it.id]: e.target.value }))}
                  aria-label={`问诊项 ${it.id} 备注`}
                />
                <Btn
                  size="sm"
                  variant="ghost"
                  disabled={busy === `letter:${it.id}`}
                  onClick={() => onWaive(it.id, 'acknowledged')}
                >
                  已读
                </Btn>
                <Btn
                  size="sm"
                  variant="ghost"
                  disabled={busy === `letter:${it.id}`}
                  onClick={() => onWaive(it.id, 'waived')}
                >
                  豁免
                </Btn>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Scene–Sequel 六格 */}
      <section data-testid="exp-scene-grid-section" aria-labelledby="exp-grid-h">
        <h3 id="exp-grid-h" className="mb-2 text-f14 font-medium">
          本章 Scene–Sequel 六格{seq != null ? ` · 第 ${seq} 章` : ''}
        </h3>
        {seq == null ? (
          <p className="text-meta text-faint">未选中章,无法编辑六格。</p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {GRID_CELLS.map(([key, label]) => (
                <label key={key} className="block text-meta">
                  <span className="mb-0.5 block text-faint">{label}</span>
                  <textarea
                    className="min-h-[3.5rem] w-full rounded border border-line bg-canvas px-2 py-1 text-f13 text-ink"
                    value={grid[key] || ''}
                    onChange={(e) => setGrid((g) => ({ ...g, [key]: e.target.value }))}
                    data-testid={`exp-grid-${key}`}
                  />
                </label>
              ))}
            </div>
            {!!gridIssues.length && (
              <ul className="mt-2 space-y-1 text-meta text-warn" data-testid="exp-grid-issues">
                {gridIssues.map((iss, i) => (
                  <li key={i}>{iss.code || iss.message || JSON.stringify(iss)}</li>
                ))}
              </ul>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              <Btn size="sm" variant="ghost" disabled={busy === 'fill-gcd'} onClick={onFillFromGcd}
                data-testid="exp-fill-from-gcd"
                title="从节拍 GCD 单向建议填充；不写回 chapter.beats">
                {busy === 'fill-gcd' ? '填充中…' : '从节拍 GCD 填充'}
              </Btn>
              <Btn size="sm" disabled={busy === 'grid'} onClick={onSaveGrid}>
                {busy === 'grid' ? '保存中…' : '保存六格'}
              </Btn>
            </div>
          </>
        )}
      </section>

      {/* 续写重读仪式 */}
      <section data-testid="exp-continue-section" aria-labelledby="exp-cont-h">
        <h3 id="exp-cont-h" className="mb-2 text-f14 font-medium">
          续写前重读
        </h3>
        {seq == null ? (
          <p className="text-meta text-faint">未选中章。</p>
        ) : (
          <>
            <div className="mb-2 flex flex-wrap items-center gap-2 text-meta">
              <span>
                要求重读: {snap?.require_reread ? '开' : '关'}
              </span>
              <span>
                本章已确认: {snap?.acked ? '是' : '否'}
              </span>
              <span>
                生成门闩: {snap?.generate_gate?.allowed === false ? '拦截' : '放行'}
              </span>
            </div>
            {snap?.snapshot && (
              <pre
                className="mb-2 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-line/50 bg-soft/30 p-2 text-meta leading-snug"
                data-testid="exp-continue-snapshot"
              >
                {typeof snap.snapshot === 'string'
                  ? snap.snapshot
                  : [
                      snap.snapshot.focalizer && `视角: ${snap.snapshot.focalizer}`,
                      snap.snapshot.last_prose_tail && `正文尾: ${snap.snapshot.last_prose_tail}`,
                      (snap.snapshot.open_promises || []).length
                        && `开放伏笔: ${(snap.snapshot.open_promises || []).map((p) => p.text || p).join('；')}`,
                      (snap.snapshot.overdue_promises || []).length
                        && `超期: ${(snap.snapshot.overdue_promises || []).map((p) => p.text || p).join('；')}`,
                    ].filter(Boolean).join('\n') || JSON.stringify(snap.snapshot, null, 2)}
              </pre>
            )}
            <div className="flex flex-wrap gap-2">
              <Btn
                size="sm"
                variant="ghost"
                disabled={busy === 'require'}
                onClick={() => onToggleRequire(!snap?.require_reread)}
              >
                {snap?.require_reread ? '关闭强制重读' : '开启强制重读'}
              </Btn>
              <Btn size="sm" disabled={busy === 'ack' || snap?.acked} onClick={onAckReread}>
                {snap?.acked ? '已确认重读' : '确认已重读本章'}
              </Btn>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

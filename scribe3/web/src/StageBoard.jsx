/**
 * 五阶段进度板（H4 · 与后端 chapter stage API 对齐 · advisory）
 * 挂 ChapterStudio 顶栏旁或章工作台内。
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { Btn } from './ui.jsx'

const DEFAULT_PHASES = ['outline', 'beats', 'deduce', 'draft', 'final']
const PHASE_LABEL = {
  outline: '大纲',
  beats: '节拍',
  design: '章设计',
  deduce: '演绎',
  draft: '草稿',
  final: '正文',
}

export function StageBoard({
  seq,
  work,
  localPhase,
  onPhaseChange,
  className = '',
}) {
  const [remote, setRemote] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    if (seq == null || typeof api.chapterStage !== 'function') return
    api.chapterStage(seq, work)
      .then((r) => setRemote(r || null))
      .catch(() => setRemote(null))
  }, [seq, work])

  useEffect(() => { load() }, [load])

  const phases = (remote?.phases?.length ? remote.phases : DEFAULT_PHASES)
  const current = localPhase || remote?.phase || 'outline'
  const idx = Math.max(0, phases.indexOf(current))

  const advance = async () => {
    if (typeof api.chapterStageAdvance !== 'function') {
      setErr('阶段 API 不可用')
      return
    }
    setBusy(true)
    setErr('')
    try {
      const r = await api.chapterStageAdvance(seq, { action: 'advance', current }, work)
      if (r?.blocked) {
        setErr(r.reason || '还不能推进到下一阶段（材料未齐或被拦住）')
      } else if (r?.next) {
        setRemote((prev) => ({ ...(prev || {}), phase: r.next }))
        onPhaseChange?.(r.next)
      }
      load()
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '推进失败')
    } finally {
      setBusy(false)
    }
  }

  /** soft set：把当前本地 phase 同步到服务端 stage_state */
  const syncLocalToServer = async () => {
    if (typeof api.chapterStageAdvance !== 'function') {
      setErr('阶段 API 不可用')
      return
    }
    const phase = localPhase || current
    if (!phase) return
    setBusy(true)
    setErr('')
    try {
      const r = await api.chapterStageAdvance(seq, { action: 'set', phase, current: remote?.phase }, work)
      if (r?.blocked) {
        setErr(r.reason || '同步被拦')
      } else {
        setRemote((prev) => ({ ...(prev || {}), phase: r?.next || phase }))
        load()
      }
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '同步失败')
    } finally {
      setBusy(false)
    }
  }

  const adoptServer = () => {
    if (remote?.phase) onPhaseChange?.(remote.phase)
  }

  const localVsServer =
    localPhase && remote?.phase && localPhase !== remote.phase

  return (
    <div
      className={`flex flex-col gap-1.5 ${className}`}
      data-testid="stage-board"
      data-phase={current}
    >
      <div className="flex items-center gap-1 flex-wrap" role="list" aria-label="章五阶段">
        {phases.map((p, i) => {
          const done = i < idx
          const active = p === current
          return (
            <button
              key={p}
              type="button"
              role="listitem"
              data-testid={`stage-board-${p}`}
              onClick={() => onPhaseChange?.(p)}
              className={[
                'h-6 px-2 rounded-md text-f11 border cursor-pointer transition-colors',
                active
                  ? 'bg-brand/15 border-brand/40 text-brand font-medium'
                  : done
                    ? 'bg-ok/10 border-ok/30 text-ink'
                    : 'bg-canvas border-line text-faint hover:text-ink',
              ].join(' ')}
            >
              {PHASE_LABEL[p] || p}
            </button>
          )
        })}
        <Btn
          size="sm"
          disabled={busy || current === 'final'}
          onClick={advance}
          data-testid="stage-board-advance"
          title="推进到下一阶段（默认不硬拦，仅提示）"
        >
          {busy ? '…' : '推进'}
        </Btn>
        {localVsServer && (
          <>
            <Btn size="sm" variant="ghost" disabled={busy} onClick={adoptServer} data-testid="stage-adopt-server">
              采用服务端
            </Btn>
            <Btn size="sm" variant="ghost" disabled={busy} onClick={syncLocalToServer} data-testid="stage-sync-local">
              同步本地到服务端
            </Btn>
          </>
        )}
      </div>
      {localVsServer && (
        <div className="text-f11 text-warn" data-testid="stage-conflict">
          本地 {localPhase} ≠ 服务端 {remote.phase}
        </div>
      )}
      {err && (
        <div className="text-f11 text-warn" data-testid="stage-board-err">{err}</div>
      )}
      {remote && !remote.enabled && (
        <div className="text-f11 text-faint">阶段机旗关 · 仅本地导航</div>
      )}
    </div>
  )
}

export default StageBoard

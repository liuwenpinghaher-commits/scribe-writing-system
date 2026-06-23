import { Check, X, Sparkles, Loader2 } from 'lucide-react'

const LABEL = { chapter: '整章改写', selection: '改这段', append: '续写' }

// 主编改写提议草稿卡:显示在中区,接受→应用进手稿,弃用→原文不动。
export function DraftCard({ proposal, streaming, onAccept, onReject }) {
  if (!proposal) return null
  return (
    <div className="my-3 rounded-xl border border-brand/40 bg-brand/[.04] overflow-hidden shadow-[var(--shadow-card)]">
      <div className="flex items-center gap-2 px-3 h-9 border-b border-brand/20 bg-brand/[.06]">
        <Sparkles size={14} className="text-brand" />
        <span className="text-[12px] font-medium text-brand">主编提议 · {LABEL[proposal.scope] || '改写'}</span>
        {streaming && <span className="text-[11px] text-faint inline-flex items-center gap-1"><Loader2 size={11} className="animate-spin" />书写中…</span>}
        <div className="ml-auto flex gap-1.5">
          <button onClick={onReject} className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[12px] text-faint hover:bg-soft cursor-pointer transition-colors"><X size={13} />弃用</button>
          <button onClick={onAccept} disabled={streaming} className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[12px] bg-brand text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-default cursor-pointer transition-opacity"><Check size={13} />接受</button>
        </div>
      </div>
      <div className="manuscript px-4 py-3 text-[15px] leading-[1.85] whitespace-pre-wrap text-ink max-h-[42vh] overflow-y-auto">{proposal.prose || '​'}</div>
    </div>
  )
}

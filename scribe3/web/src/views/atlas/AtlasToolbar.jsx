import { Eye, Crosshair, Lock, Network } from 'lucide-react'

export function AtlasToolbar({
  focus,
  focusLabel,
  chars,
  hop,
  sliceChapter,
  maxChapter,
  stat,
  showCanvas,
  onFocus,
  onHop,
  onSlice,
  onToggleCanvas,
}) {
  return (
    <div className="h-11 shrink-0 border-b border-line/60 bg-surface/95 backdrop-blur-sm flex items-center gap-2.5 px-4 overflow-x-auto">
      <Eye size={15} className="text-brand shrink-0" />
      <span className="text-f13 font-semibold tracking-tight text-ink shrink-0">谁知道什么</span>
      {focusLabel && (
        <span className="text-f12 text-faint tnum inline-flex items-center gap-1 shrink-0">
          <Crosshair size={12} className="text-brand" />{focusLabel}
          {stat ? ` · ${stat.c}角 · ${stat.p}题` : ''}
        </span>
      )}
      <select
        value={focus}
        onChange={(e) => onFocus?.(e.target.value)}
        aria-label="图中心"
        className="h-7 rounded-md border-0 bg-soft/80 px-2.5 text-f13 outline-none focus:ring-2 focus:ring-brand/20 cursor-pointer"
      >
        {chars.map((c) => (
          <option key={c.id} value={c.id}>{c.label}</option>
        ))}
      </select>
      <div className="inline-flex items-center gap-0.5 rounded-md bg-soft/80 p-0.5 text-f12 shrink-0">
        <span className="px-1.5 text-meta text-faint">跳数</span>
        {[1, 2, 3].map((h) => (
          <button
            key={h}
            type="button"
            onClick={() => onHop?.(h)}
            className={`min-w-7 h-6 px-1.5 rounded-lg text-meta transition-colors cursor-pointer ${hop === h ? 'bg-surface text-brand font-medium shadow-sm' : 'text-faint hover:text-ink'}`}
          >{h}</button>
        ))}
      </div>
      {maxChapter > 0 && (
        <div className="inline-flex items-center gap-1.5 text-f12 text-faint shrink-0">
          <label htmlFor="atlas-chapter-slice" className="shrink-0">截至</label>
          <select
            id="atlas-chapter-slice"
            aria-label="章切片"
            value={sliceChapter == null ? '' : String(sliceChapter)}
            onChange={(e) => {
              const v = e.target.value
              onSlice?.(v === '' ? null : Number(v))
            }}
            className="h-7 rounded-md border-0 bg-soft/80 px-2.5 text-f13 tnum outline-none focus:ring-2 focus:ring-brand/20 cursor-pointer"
          >
            <option value="">全书</option>
            {Array.from({ length: maxChapter }, (_, i) => i + 1).map((ch) => (
              <option key={ch} value={String(ch)}>第{ch}章</option>
            ))}
          </select>
        </div>
      )}
      <button
        type="button"
        data-testid="atlas-toggle-canvas"
        aria-pressed={!!showCanvas}
        onClick={onToggleCanvas}
        className={`ml-auto h-7 px-2 rounded-md text-f12 inline-flex items-center gap-1 shrink-0 cursor-pointer ${showCanvas ? 'bg-soft text-ink' : 'text-faint hover:text-ink hover:bg-soft'}`}
      >
        <Network size={13} />{showCanvas ? '收起图' : '看图'}
      </button>
      <span className="inline-flex items-center gap-1.5 text-meta text-faint shrink-0">
        <i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-brand)' }} />人
        <i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-irony)' }} />知情
        <Lock size={11} />私密
      </span>
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Gauge, Loader2, Quote } from 'lucide-react'
import { api } from '../api'
import { Btn, Card, Empty, SectionTitle, Tag } from '../ui.jsx'
import { AsyncState } from '../ui/AsyncState.jsx'

const STATE_LABEL = {
  evaluable: '可评价', insufficient: '证据不足', degraded: '降级',
  conflicted: '分歧', not_applicable: '不适用',
}
const STATE_TONE = {
  evaluable: 'ok', insufficient: 'faint', degraded: 'danger',
  conflicted: 'danger', not_applicable: 'faint',
}

function ScoreInput({ value, onChange, onCommit, label, path }) {
  return (
    <input
      type="number" min="1" max="5" step="1"
      role="spinbutton"
      aria-label={label}
      data-field-path={path}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
      onBlur={() => onCommit(value)}
      className="w-14 h-8 rounded-md border border-line bg-canvas px-2 text-f13 text-ink text-center outline-none transition-colors focus:border-brand"
    />
  )
}

function DimensionRow({ dim, chapter, authorScores, onAuthorScore, onAuthorCommit, onLocateEvidence }) {
  const sys = dim.system
  const ref = dim.reference
  const author = authorScores[dim.dimension] ?? dim.author?.score ?? null
  const threeAxesPresent = author != null && sys != null && ref != null
  return (
    <div className="rounded-lg border border-line bg-canvas p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-f14 font-semibold text-ink">{dim.dimension}</span>
        <Tag tone={STATE_TONE[dim.state] || 'faint'}>{STATE_LABEL[dim.state] || dim.state}</Tag>
        {dim.conflicted && <Tag tone="danger"><AlertTriangle size={10} className="mr-0.5 inline" />分歧</Tag>}
        {sys && <span className="text-meta text-faint">系统 <b className="text-ink tnum">{sys.score}</b></span>}
        {ref && <span className="text-meta text-faint">参考 <b className="text-ink tnum">{ref.score}</b></span>}
        {author != null && <span className="text-meta text-faint">作者 <b className="text-ink tnum">{author}</b></span>}
        {threeAxesPresent && dim.decision_index != null && (
          <span className="ml-auto inline-flex items-center gap-1 text-meta text-brand" data-field-path={`dimension.${dim.dimension}.decision_index`}>
            <Gauge size={11} />决策指数 <b className="tnum">{Number(dim.decision_index).toFixed(1)}</b>
          </span>
        )}
      </div>
      {sys?.mechanism && <div className="text-meta text-muted" data-field-path={`dimension.${dim.dimension}.mechanism`}>{sys.mechanism}</div>}
      {Array.isArray(sys?.evidence) && sys.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {sys.evidence.map((ev, i) => (
            <button
              key={i}
              onClick={() => onLocateEvidence?.({ chapter, quote: ev.quote, start_utf16: ev.start_utf16, end_utf16: ev.end_utf16 })}
              className="inline-flex items-center gap-1 rounded border border-line bg-soft px-1.5 py-0.5 text-meta text-faint transition-colors hover:text-ink hover:border-faint/50 cursor-pointer"
              title="点击定位证据"
            >
              <Quote size={10} />{ev.quote}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 pt-0.5">
        <span className="text-meta text-faint">作者评分</span>
        <ScoreInput
          value={author}
          label={`${dim.dimension} 作者评分`}
          path={`dimension.${dim.dimension}.author_score`}
          onChange={(v) => onAuthorScore(dim.dimension, v)}
          onCommit={(v) => onAuthorCommit(dim.dimension, v)}
        />
        <span className="text-meta text-faint/60">1–5</span>
      </div>
    </div>
  )
}

export function QualityReview({ work, seq, onLocateEvidence }) {
  const [evaluation, setEvaluation] = useState(null)
  const [state, setState] = useState('loading')
  const [authorScores, setAuthorScores] = useState({})

  const load = useCallback(() => {
    setState('loading')
    api.qualityEvaluation(seq)
      .then((ev) => { setEvaluation(ev); setState('ready') })
      .catch(() => setState('error'))
  }, [seq])

  useEffect(() => { load() }, [load])

  const commitAuthorScore = async (dimension, score) => {
    if (score == null) return
    setAuthorScores((prev) => ({ ...prev, [dimension]: score }))
    try {
      await api.qualityAuthorJudgment({ work, seq, dimension, score })
      load()
    } catch {
      load()
    }
  }

  const handleAuthorScore = (dimension, value) => {
    setAuthorScores((prev) => ({ ...prev, [dimension]: value }))
  }

  if (state === 'loading') {
    return <div className="p-6 flex items-center gap-2 text-faint"><Loader2 size={16} className="animate-spin" />加载质量评价…</div>
  }
  if (state === 'error') {
    return <div className="p-4"><AsyncState state="error" title="质量评价加载失败" onRetry={load} /></div>
  }
  if (!evaluation || !Array.isArray(evaluation.dimensions) || evaluation.dimensions.length === 0) {
    return <div className="p-6"><Empty>暂无质量评价。先为章节创建快照并启动评价。</Empty></div>
  }

  const chapter = evaluation.chapter ?? seq
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5 space-y-4">
        <SectionTitle icon={Gauge} right={`第 ${chapter} 章 · ${evaluation.dimensions.length} 维`}>质量审阅</SectionTitle>
        <div className="space-y-3">
          {evaluation.dimensions.map((dim) => (
            <DimensionRow
              key={dim.dimension}
              dim={dim}
              chapter={chapter}
              authorScores={authorScores}
              onAuthorScore={handleAuthorScore}
              onAuthorCommit={commitAuthorScore}
              onLocateEvidence={onLocateEvidence}
            />
          ))}
        </div>
        <div className="text-meta text-faint/70 pb-4">维度指数仅用于同一维度内排序,不跨维度求和。</div>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from '../../api'
import { breathDefaultSeq } from '../../lib/insightReadable.js'

export function DiscourseBreathPanel({ work, onJumpChapter, chapter = null, lastSeq = 1 }) {
  const defaultSeq = breathDefaultSeq(chapter, lastSeq)
  const [seq, setSeq] = useState(defaultSeq)
  useEffect(() => { setSeq(defaultSeq) }, [defaultSeq])
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = async () => {
    setBusy(true)
    setErr('')
    try {
      let r
      if (typeof api.discourseSoft === 'function') {
        r = await api.discourseSoft({ seq: Number(seq) }, work)
      } else {
        r = await api.post('/soft/discourse', { seq: Number(seq) }, work)
      }
      setData(r)
    } catch (e) {
      setErr(e?.message || '加载失败')
      setData(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-8 pt-6 border-t border-line/60" data-testid="insight-discourse-breath">
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="text-f13 font-medium text-ink">正文呼吸（参考）</span>
        <span className="text-meta text-faint">与章信息 · 话语/呼吸卡同源 · 不是打分</span>
      </div>
      <p className="text-f12 text-faint mb-2">
        详细改写提示请在打开对应章后使用 soft 卡「话语/呼吸」。此处只读摘要。
      </p>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <label className="text-f12 text-faint">
          章号
          <input
            type="number"
            min={1}
            className="ml-1 w-16 rounded border border-line bg-canvas px-1.5 py-0.5 text-f13 text-ink"
            value={seq}
            onChange={(e) => setSeq(Number(e.target.value) || 1)}
            data-testid="insight-discourse-seq"
          />
        </label>
        <button
          type="button"
          className="h-7 px-2 rounded-md border border-line text-f12 text-ink hover:bg-soft cursor-pointer"
          disabled={busy}
          onClick={load}
          data-testid="insight-discourse-run"
        >
          {busy ? '…' : '查看'}
        </button>
        <button
          type="button"
          className="h-7 px-2 rounded-md text-f12 text-brand hover:underline cursor-pointer"
          onClick={() => onJumpChapter?.(Number(seq))}
        >
          打开该章
        </button>
      </div>
      {err && <div className="text-f12 text-danger mb-1">{err}</div>}
      {data && (
        <div className="text-f12 text-ink space-y-1 rounded-md border border-line/50 bg-soft/20 px-3 py-2">
          <div className="text-faint">
            状态 {data.status || '—'}
            {data.breath?.tight ? ' · 呼吸偏紧' : ''}
            {data.breath?.telling_count != null ? ` · 贴标 ${data.breath.telling_count}` : ''}
          </div>
          {(data.breath?.tips || []).slice(0, 3).map((t, i) => (
            <div key={i}>· {t.product_label || t.family}：{t.tip || ''}</div>
          ))}
          {(data.findings || []).slice(0, 3).map((f, i) => (
            <div key={`f${i}`} className="text-warn">· {f.message || f.type}</div>
          ))}
        </div>
      )}
    </div>
  )
}

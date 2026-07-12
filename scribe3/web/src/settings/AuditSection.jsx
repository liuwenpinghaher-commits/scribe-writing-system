import { useEffect, useState } from 'react'
import { api } from '../api'

const PAGE = 50

// 变更历史:只读审计表,读 /settings/audit(后端固定每页 50,offset 翻页)。
// 「加载更多」在返回不足一页时隐藏——不足一页即已到底,再点只会拿回空结果。
export function AuditSection() {
  const [rows, setRows] = useState([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = (off, append) => {
    setLoading(true)
    api.settingsAudit(off).then((r) => {
      const got = r?.rows || []
      setRows((prev) => (append ? [...prev, ...got] : got))
      setHasMore(got.length >= PAGE)
      setOffset(off)
      setError(null)
    }).catch((e) => setError(e?.body?.detail || e.message || '变更历史加载失败'))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load(0, false) }, [])

  return (
    <div data-testid="audit-section">
      <div className="text-f13 font-medium text-ink mb-3">设置变更历史</div>
      {error && (
        <div className="text-f13 text-red-500 mb-3" role="alert">
          {error} <button className="text-brand cursor-pointer" onClick={() => load(offset, false)}>重试</button>
        </div>
      )}
      {!error && !loading && rows.length === 0 && <div className="text-f13 text-faint">暂无变更记录</div>}
      {rows.length > 0 && (
        <table className="w-full text-f13">
          <thead>
            <tr className="text-left text-meta text-faint border-b border-line">
              <th className="py-1.5 font-normal">时间</th>
              <th className="py-1.5 font-normal">项</th>
              <th className="py-1.5 font-normal">旧值 → 新值</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.key}-${r.ts}-${i}`} className="border-b border-line/50 last:border-0">
                <td className="py-1.5 text-faint whitespace-nowrap">{r.ts}</td>
                <td className="py-1.5 text-ink">{r.key}</td>
                <td className="py-1.5 text-ink tnum">{String(r.old)} → {String(r.new)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {hasMore && !error && (
        <button className="mt-3 text-meta text-brand cursor-pointer disabled:opacity-50" disabled={loading}
          onClick={() => load(offset + PAGE, true)}>{loading ? '加载中…' : '加载更多'}</button>
      )}
    </div>
  )
}

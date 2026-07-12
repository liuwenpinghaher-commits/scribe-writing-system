import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Textarea } from '../ui.jsx'

// 与 NorthStarBar.jsx 的 FIELDS 保持同一套字段/标签,顶栏北极星条与设置中心「本书设置」
// 两处编辑同一份 /intent,标签不一致会让作者以为是两份数据。
const TEXT_FIELDS = [
  ['reader_feeling', '读者感受'],
  ['emotional_arc', '情感弧'],
  ['red_lines', '红线'],
]
const NUM_FIELDS = [
  ['total_word_goal', '整稿目标字数'],
  ['daily_word_goal', '每日目标字数'],
  ['overdue_threshold', '逾期阈值(天)'],
]

// 本书设置:挂载拉 /intent,失焦逐字段 PUT(后端 MERGE 语义,只传变更字段——不把
// 整份 intent 回传,防止多个编辑入口(此处/NorthStarBar)并发编辑时互相覆盖对方字段)。
export function BookSection({ work }) {
  const [intent, setIntent] = useState(null)
  const [err, setErr] = useState(null)
  const baseline = useRef({})

  const load = () => {
    setErr(null)
    api.intent().then((r) => {
      setIntent(r || {})
      baseline.current = r || {}
    }).catch((e) => setErr(e?.body?.detail || e.message || '本书设置加载失败'))
  }
  useEffect(() => { load() }, [work])

  if (!intent) {
    return (
      <div data-testid="book-section">
        {err
          ? <div className="text-f13 text-red-500" role="alert">{err} <button className="text-brand cursor-pointer" onClick={load}>重试</button></div>
          : <div className="text-f13 text-faint">加载中…</div>}
      </div>
    )
  }

  const set = (k, v) => setIntent((i) => ({ ...i, [k]: v }))

  const commit = async (k, v) => {
    try {
      await api.putIntent({ [k]: v })
      baseline.current = { ...baseline.current, [k]: v }
      setErr(null)
    } catch (e) {
      setErr(e?.body?.detail || e.message || '保存失败')
    }
  }

  const blurText = (k) => {
    const v = intent[k] || ''
    if (v === (baseline.current[k] || '')) return
    commit(k, v)
  }

  const blurNum = (k) => {
    const raw = intent[k]
    if (raw === '' || raw == null) {
      if ((baseline.current[k] ?? null) === null) return
      // 后端 set_intent 对数字字段的 None 视为「未传」(MERGE 直接跳过),清空
      // 永远落不了库——发 PUT 假装保存成功只会误导用户。恢复旧值 + 如实提示。
      set(k, baseline.current[k])
      setErr('数字字段不支持清空,已恢复原值')
      return
    }
    const n = parseInt(raw, 10)
    if (!Number.isFinite(n)) { setErr('请输入有效数字'); return }
    if (n === (baseline.current[k] ?? null)) return
    commit(k, n)
  }

  return (
    <div data-testid="book-section">
      {err && <div className="text-f13 text-red-500 mb-3" role="alert">{err}</div>}
      <div className="grid gap-3 mb-5">
        {TEXT_FIELDS.map(([k, label]) => (
          <div key={k}>
            <label htmlFor={`book-${k}`} className="block text-meta text-faint mb-1">{label}</label>
            <Textarea id={`book-${k}`} rows={2} value={intent[k] || ''}
              onChange={(e) => set(k, e.target.value)} onBlur={() => blurText(k)} />
          </div>
        ))}
      </div>
      <div className="grid sm:grid-cols-3 gap-3">
        {NUM_FIELDS.map(([k, label]) => (
          <div key={k}>
            <label htmlFor={`book-${k}`} className="block text-meta text-faint mb-1">{label}</label>
            <input id={`book-${k}`} type="number"
              className="w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-f13 tnum"
              value={intent[k] ?? ''} onChange={(e) => set(k, e.target.value)} onBlur={() => blurNum(k)} />
          </div>
        ))}
      </div>
    </div>
  )
}

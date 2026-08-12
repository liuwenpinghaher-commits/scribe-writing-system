import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Input } from '../ui.jsx'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { ReadOnlyText } from '../ui/EditableText.jsx'

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

// 本书设置:叙事意图只读 + 主编种子;数字配额仍可表单 PUT(工程配额例外)。
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
          ? <div className="text-f13 text-danger" role="alert">{err} <button type="button" className="text-brand cursor-pointer" onClick={load}>重试</button></div>
          : <div className="text-f13 text-faint">加载中…</div>}
      </div>
    )
  }

  const set = (k, v) => setIntent((i) => ({ ...i, [k]: v }))

  const commitNum = async (k, v) => {
    try {
      // 工程配额走 /intent-goals(不经世界闸);禁止 putIntent 整包叙事字段
      await api.putIntentGoals({ [k]: v })
      baseline.current = { ...baseline.current, [k]: v }
      setErr(null)
    } catch (e) {
      setErr(e?.body?.detail || e.message || '保存失败')
    }
  }

  const blurNum = (k) => {
    const raw = intent[k]
    if (raw === '' || raw == null) {
      if ((baseline.current[k] ?? null) === null) return
      set(k, baseline.current[k])
      setErr('数字字段不支持清空,已恢复原值')
      return
    }
    const n = parseInt(raw, 10)
    if (!Number.isFinite(n)) { setErr('请输入有效数字'); return }
    if (n === (baseline.current[k] ?? null)) return
    commitNum(k, n)
  }

  return (
    <div data-testid="book-section">
      {err && <div className="text-f13 text-danger mb-3" role="alert">{err}</div>}
      <div className="grid gap-3 mb-5">
        <div className="text-f12 text-faint rounded-lg bg-soft/50 px-3 py-2">
          读者感受 / 情感弧 / 红线与顶栏「作品意图」同一份 intent，禁止表单直填——请用主编审批写入。
        </div>
        {TEXT_FIELDS.map(([k, label]) => (
          <div key={k} data-testid={`book-narrative-${k}`}>
            <ReadOnlyText
              label={label}
              value={intent[k] || ''}
              emptyHint="（空 · 由主编审批写入）"
              entityLabel="作品意图"
              fieldKey={k}
              emptyAskLabel="聊聊怎么写"
            />
            <button
              type="button"
              className="mt-1 text-meta text-brand hover:underline cursor-pointer"
              onClick={() => seedChiefNarrativeWrite(
                'intent',
                `作品意图·${label}`,
                `请更新 intent.${k}（${label}）。当前值: ${intent[k] || '（空）'}。用 s3_set_intent 等写工具提交提案。`,
              )}
            >
              让主编写入{label}
            </button>
          </div>
        ))}
      </div>
      {intent.total_word_goal == null || intent.total_word_goal === '' ? (
        <div
          className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-f13"
          data-testid="book-word-goal-missing"
          role="status"
        >
          <span className="text-ink/90">尚未设定全书目标字数（craft-loop 北极星建议 4–6 万）。</span>
          <button
            type="button"
            className="ml-2 text-brand hover:underline cursor-pointer"
            data-testid="book-word-goal-default-45k"
            onClick={() => {
              set('total_word_goal', 45000)
              commitNum('total_word_goal', 45000)
            }}
          >
            一键设为 45000
          </button>
        </div>
      ) : null}
      <div className="grid sm:grid-cols-3 gap-3">
        {NUM_FIELDS.map(([k, label]) => (
          <div key={k}>
            <label htmlFor={`book-${k}`} className="block text-meta text-faint mb-1">{label}</label>
            <Input variant="bordered" id={`book-${k}`} type="number" aria-label={label}
              value={intent[k] ?? ''} onChange={(e) => set(k, e.target.value)} onBlur={() => blurNum(k)} />
          </div>
        ))}
      </div>
    </div>
  )
}

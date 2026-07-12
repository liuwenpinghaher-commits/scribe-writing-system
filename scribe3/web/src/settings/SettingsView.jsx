import { useEffect, useState } from 'react'
import { api } from '../api'
import { SettingField } from './SettingField'
import { GatewaySection } from './GatewaySection'
import { BookSection } from './BookSection'
import { PrefsSection } from './PrefsSection'
import { AuditSection } from './AuditSection'

// 七分区 + 审计:connection/llm/craft/flags/gateway 由 /settings 元数据驱动;
// book/prefs/audit 为前端本地分区(Task 15 充实)。
const SECTIONS = [
  { key: 'connection', label: '连接与服务' },
  { key: 'llm', label: 'LLM 与用量' },
  { key: 'craft', label: '工艺阈值' },
  { key: 'flags', label: '灰度开关' },
  { key: 'gateway', label: 'Hermes 网关' },
  { key: 'book', label: '本书设置' },
  { key: 'prefs', label: '个人偏好' },
  { key: 'audit', label: '变更历史' },
]

// llm 分区顶部用量卡:今日已用/日帽,拉取失败静默隐藏(用量是辅助信息,不应阻断设置分区)。
// 日帽为全系统共享台账,与当前书无关,故不接收/不依赖 work。
function UsageCard() {
  const [usage, setUsage] = useState(null)
  useEffect(() => {
    let alive = true
    api.aiUsage().then((r) => { if (alive) setUsage(r) }).catch(() => { if (alive) setUsage(null) })
    return () => { alive = false }
  }, [])
  if (!usage?.cap) return null
  const { cap, used_today } = usage.cap
  const pct = cap > 0 ? Math.min(100, Math.round((used_today / cap) * 100)) : 0
  return (
    <div className="mb-4 rounded-md border border-line bg-surface/60 p-3">
      <div className="flex items-center justify-between text-f13 text-ink">
        <span>今日已用 {used_today} / 日帽 {cap}</span>
        <span className="text-meta text-muted">{pct}%</span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-soft overflow-hidden">
        <div className="h-full rounded-full bg-brand" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function SettingsView({ work }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [section, setSection] = useState('llm')
  const reload = () => api.settings().then((r) => { setItems(r.settings); setError(null) }).catch((e) => setError(e))
  useEffect(() => { reload() }, [])
  if (error) return (
    <div className="h-full grid place-items-center text-f13 text-faint" data-testid="settings-view">
      <div>设置加载失败 <button className="text-brand cursor-pointer" onClick={reload}>重试</button></div>
    </div>
  )
  const byCat = (c) => (items || []).filter((i) => i.category === c)
  return (
    <div className="flex h-full min-h-0" data-testid="settings-view">
      <nav className="w-44 shrink-0 border-r border-line bg-surface/60 p-2 overflow-auto" aria-label="设置分区">
        {SECTIONS.map((s) => (
          <button key={s.key} onClick={() => setSection(s.key)}
            className={`block w-full text-left rounded-md px-3 py-2 text-f13 cursor-pointer ${
              section === s.key ? 'bg-soft text-brand' : 'text-ink hover:bg-soft'}`}>
            {s.label}
          </button>
        ))}
      </nav>
      <div className="flex-1 min-w-0 overflow-auto p-6">
        <div className="mx-auto max-w-3xl">
          {section === 'gateway' && <GatewaySection items={byCat('gateway')} onChanged={reload} />}
          {section === 'book' && <BookSection work={work} />}
          {section === 'prefs' && <PrefsSection work={work} />}
          {section === 'audit' && <AuditSection />}
          {section === 'llm' && <UsageCard />}
          {['connection', 'llm', 'craft', 'flags'].includes(section) &&
            byCat(section).map((it) => <SettingField key={it.key} item={it} onChanged={reload} />)}
        </div>
      </div>
    </div>
  )
}

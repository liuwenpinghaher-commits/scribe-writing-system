/**
 * Agent Cron 面板（H7 · 列表 + enable 开关 · schedule 只读）
 */
import { useEffect, useState } from 'react'
import { api } from '../api'
import { Btn } from '../ui.jsx'

export function CronPanel() {
  const [jobs, setJobs] = useState([])
  const [err, setErr] = useState('')
  const [flag, setFlag] = useState(true)
  const [busy, setBusy] = useState('')
  const [hermes, setHermes] = useState(null)
  const [noteZh, setNoteZh] = useState('')

  const load = async () => {
    setErr('')
    try {
      let r
      if (typeof api.agentCrons === 'function') {
        r = await api.agentCrons()
      } else {
        r = await api.get('/agent-crons')
      }
      setJobs(r?.jobs || [])
      setFlag(r?.enabled_flag !== false)
      setHermes(r?.hermes_cron || null)
      setNoteZh(r?.note_zh || '')
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '加载 cron 失败')
    }
  }

  useEffect(() => { load() }, [])

  const toggle = async (name, enabled) => {
    setBusy(name)
    try {
      if (typeof api.agentCronEnable === 'function') {
        await api.agentCronEnable(name, { enabled })
      } else {
        await api.post(`/agent-crons/${encodeURIComponent(name)}/enable`, { enabled })
      }
      await load()
    } catch (e) {
      setErr(e?.message || '切换失败')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-3 p-3" data-testid="cron-panel">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-f13 font-medium">Agent Cron</h3>
          <p className="text-f11 text-faint">
            启停覆盖落盘；schedule/script 真源仍是 crons.yaml / provision_hermes。
            不改 Hermes timer。{!flag && '（产品旗 SCRIBE3_AGENT_CRON_UI 关）'}
          </p>
        </div>
        <Btn size="sm" onClick={load}>刷新</Btn>
      </div>
      {noteZh && <div className="text-f11 text-faint" data-testid="cron-note-zh">{noteZh}</div>}
      {hermes && (
        <div className="rounded-md border border-line bg-soft/40 px-2 py-1.5 text-f11" data-testid="cron-hermes-agg">
          Hermes 聚合：
          {hermes.checked ? '已检查' : '未检查'}
          {hermes.gateway_running != null && ` · gateway ${hermes.gateway_running ? '运行' : '未运行'}`}
          {hermes.active_jobs != null && ` · active ${hermes.active_jobs}`}
          {hermes.scribe3_qc?.present && ` · 体检 present${hermes.scribe3_qc?.active ? '/active' : ''}`}
          {hermes.note && <span className="text-faint"> · {hermes.note}</span>}
        </div>
      )}
      {err && <div className="text-warn text-f12">{err}</div>}
      <ul className="divide-y divide-line border border-line rounded-lg">
        {(jobs || []).length === 0 && (
          <li className="px-3 py-2 text-f12 text-faint">无 jobs（检查 crons.yaml 路径）</li>
        )}
        {(jobs || []).map((j) => (
          <li key={j.name} className="px-3 py-2 flex items-center gap-3 text-f12">
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{j.name}</div>
              <div className="text-f11 text-faint truncate">
                {j.schedule || '—'} · {j.script || ''}
              </div>
              {j.hermes && (
                <div className="text-f11 text-faint" data-testid={`cron-hermes-${j.name}`}>
                  Hermes：
                  {j.hermes.present ? '在册' : '未在册'}
                  {j.hermes.present && (j.hermes.active ? ' · 活跃' : ' · 非活跃')}
                  {j.hermes.last_status && ` · last ${j.hermes.last_status}`}
                  {j.hermes.match === 'fuzzy' && j.hermes.matched_name && (
                    <span> · 匹配 {j.hermes.matched_name}</span>
                  )}
                </div>
              )}
            </div>
            <label className="flex items-center gap-1.5 shrink-0 cursor-pointer">
              <input
                type="checkbox"
                checked={j.enabled !== false}
                disabled={!!busy || !flag}
                onChange={(e) => toggle(j.name, e.target.checked)}
                data-testid={`cron-enable-${j.name}`}
              />
              <span className="text-f11">{j.enabled !== false ? '开' : '关'}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default CronPanel

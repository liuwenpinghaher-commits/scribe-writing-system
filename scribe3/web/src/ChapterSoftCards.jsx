/**
 * 章侧 soft 卡片：precheck / literary distill / storyline inject 预览（H5）
 */
import { useState } from 'react'
import { api } from './api'
import { Btn } from './ui.jsx'

function Card({ title, children, testId }) {
  return (
    <div
      className="rounded-lg border border-line bg-canvas p-3 space-y-2"
      data-testid={testId}
    >
      <div className="text-f12 font-medium text-ink">{title}</div>
      {children}
    </div>
  )
}

export function ChapterSoftCards({ seq, work, synopsis, beats }) {
  const [precheck, setPrecheck] = useState(null)
  const [distill, setDistill] = useState(null)
  const [inject, setInject] = useState(null)
  const [eventLed, setEventLed] = useState(null)
  const [discourse, setDiscourse] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const runPrecheck = async () => {
    setBusy('precheck')
    setErr('')
    try {
      const body = {
        seq: Number(seq),
        synopsis: synopsis || '',
        beats: beats || [],
      }
      let r
      if (typeof api.softPrecheck === 'function') {
        r = await api.softPrecheck(body, work)
      } else {
        r = await api.post('/soft-precheck', body)
      }
      setPrecheck(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || 'precheck 失败')
    } finally {
      setBusy('')
    }
  }

  const runDistill = async () => {
    setBusy('distill')
    setErr('')
    try {
      const text = synopsis || ''
      let r
      if (typeof api.literaryDistill === 'function') {
        r = await api.literaryDistill({ text, seq: Number(seq) }, work)
      } else {
        r = await api.post('/literary-distill', { text, seq: Number(seq) })
      }
      setDistill(r)
    } catch (e) {
      // 端点可能未挂：本地启发式降级
      const t = String(synopsis || '').trim()
      setDistill({
        surface: 'local_fallback',
        summary: t ? t.slice(0, 200) + (t.length > 200 ? '…' : '') : '（无梗概可蒸馏）',
        note: e?.message || 'API 不可用 · 本地截断',
      })
    } finally {
      setBusy('')
    }
  }

  const runEventLed = async (includeLlm = false) => {
    setBusy(includeLlm ? 'event-led-llm' : 'event-led')
    setErr('')
    try {
      const body = {
        seq: Number(seq),
        include_llm: !!includeLlm,
        synopsis: synopsis || '',
      }
      let r
      if (typeof api.softEventLed === 'function') {
        r = await api.softEventLed(body, work)
      } else {
        r = await api.post('/soft/event-led', body)
      }
      setEventLed(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || 'event-led 失败')
    } finally {
      setBusy('')
    }
  }

  const runInject = async () => {
    setBusy('inject')
    setErr('')
    try {
      // SL2：use_store=1 与写路径同源 feed（窗口 + craft_only + omit）
      const body = {
        focus_seq: Number(seq),
        use_store: 1,
        promise_mode: 'omit',
        chapters: [{ seq: Number(seq), synopsis: synopsis || '' }],
      }
      let r
      if (typeof api.storylineInjectPreview === 'function') {
        r = await api.storylineInjectPreview(body, work)
      } else {
        r = await api.post('/storyline/inject-preview', body)
      }
      setInject(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || 'inject 预览失败')
    } finally {
      setBusy('')
    }
  }

  const runDiscourse = async () => {
    setBusy('discourse')
    setErr('')
    try {
      // G2：只传 seq + work；服务端取 prose|draft
      const body = { seq: Number(seq) }
      let r
      if (typeof api.discourseSoft === 'function') {
        r = await api.discourseSoft(body, work)
      } else {
        r = await api.post('/soft/discourse', body, work)
      }
      setDiscourse(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '话语/呼吸检查失败')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-2" data-testid="chapter-soft-cards">
      <div className="text-f12 font-medium text-faint">质量助手 · 开写前检查 / 话语呼吸 / 弧意图预览</div>
      {err && <div className="text-f11 text-warn">{err}</div>}
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <Card title="开写前检查" testId="soft-card-precheck">
          <Btn size="sm" disabled={!!busy} onClick={runPrecheck} data-testid="soft-precheck-run">
            {busy === 'precheck' ? '…' : '运行'}
          </Btn>
          {precheck && (
            <pre className="text-f11 text-faint whitespace-pre-wrap max-h-32 overflow-auto">
              {JSON.stringify(precheck, null, 0).slice(0, 600)}
            </pre>
          )}
        </Card>
        <Card title="文学蒸馏" testId="soft-card-distill">
          <Btn size="sm" disabled={!!busy} onClick={runDistill} data-testid="soft-distill-run">
            {busy === 'distill' ? '…' : '近章梗概'}
          </Btn>
          {distill && (
            <div className="text-f11 text-ink leading-relaxed">
              {distill.summary || distill.text || distill.distill || JSON.stringify(distill).slice(0, 300)}
            </div>
          )}
        </Card>
        <Card title="弧意图注入预览" testId="soft-card-inject">
          <Btn size="sm" disabled={!!busy} onClick={runInject} data-testid="soft-inject-run">
            {busy === 'inject' ? '…' : '预览'}
          </Btn>
          {inject && (
            <pre className="text-f11 text-faint whitespace-pre-wrap max-h-32 overflow-auto">
              {(inject.text || inject.segment || JSON.stringify(inject)).toString().slice(0, 600)}
            </pre>
          )}
        </Card>
        <Card title="事件是否写进正文" testId="soft-card-event-led">
          <div className="flex flex-wrap gap-1">
            <Btn size="sm" disabled={!!busy} onClick={() => runEventLed(false)} data-testid="soft-event-led-run">
              {busy === 'event-led' ? '…' : 'L0'}
            </Btn>
            <Btn size="sm" disabled={!!busy} onClick={() => runEventLed(true)} data-testid="soft-event-led-llm">
              {busy === 'event-led-llm' ? '…' : '深评 L1'}
            </Btn>
          </div>
          {eventLed && (
            <pre className="text-f11 text-faint whitespace-pre-wrap max-h-32 overflow-auto">
              {JSON.stringify(eventLed.l0 || eventLed, null, 0).slice(0, 500)}
            </pre>
          )}
        </Card>
        <Card title="话语/呼吸" testId="soft-card-discourse">
          <Btn size="sm" disabled={!!busy} onClick={runDiscourse} data-testid="soft-discourse-run">
            {busy === 'discourse' ? '…' : '检查'}
          </Btn>
          {discourse && (
            <div className="text-f11 text-ink space-y-1 max-h-36 overflow-auto" data-testid="soft-discourse-result">
              <div className="text-faint">
                状态 {discourse.status || '—'}
                {discourse.breath?.tight ? ' · 呼吸偏紧' : ''}
              </div>
              {(discourse.breath?.tips || []).slice(0, 3).map((t, i) => (
                <div key={i}>· {t.product_label || t.family}：{t.tip || ''}</div>
              ))}
              {(discourse.findings || []).slice(0, 4).map((f, i) => (
                <div key={`f${i}`} className="text-warn">
                  · {f.message || f.type}
                </div>
              ))}
              {discourse.status === 'no_prose' && !(discourse.findings || []).length && (
                <div className="text-faint">尚无正文 · 仅计划侧提示（若有）</div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export default ChapterSoftCards
